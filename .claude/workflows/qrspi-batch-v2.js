export const meta = {
  name: 'qrspi-batch-v2',
  description: 'Drive every assigned Selected / Plan Approved Linear ticket through QRSPI by spawning the typed phase agents from the workflow script itself',
  whenToUse: 'After moving a batch of tickets to Selected or Plan Approved across any Linear project. Replaces qrspi-batch, which nested qrspi-work inside agent() and therefore could not spawn the phase agents.',
  phases: [
    { title: 'Query', detail: 'List Selected + Plan Approved tickets assigned to me' },
    { title: 'Setup', detail: 'Per-ticket worktree + ticket fetch (worker agent)' },
    { title: 'Planning', detail: 'Spawn qrspi-questions…worktree phase agents' },
    { title: 'Implementation', detail: 'Spawn qrspi-implement per slice + qrspi-pr' },
    { title: 'Finalize', detail: 'Commit, submit PR, transition Linear (worker agent)' },
    { title: 'Inline', detail: 'Non-spawning states handled by a worker agent' },
  ],
}

// ---------------------------------------------------------------------------
// Why this exists
// ---------------------------------------------------------------------------
// The old qrspi-batch ran `agent("…follow qrspi-work SKILL.md…")`. That subagent
// is a workflow-subagent, which is NOT provisioned the Agent (subagent-spawning)
// tool. qrspi-work's planning/implementation paths REQUIRE spawning the typed
// `.claude/agents/qrspi-*` phase agents. With no Agent tool, each subagent either
// (a) honestly reported a blocker and stalled, or (b) silently fabricated the six
// planning artifacts by hand and pushed them to Plan Review — bypassing the
// research firewall and every per-phase tool lockdown. Evidence: run wf_297251df
// processed RUS-22..30 all from Selected; RUS-23/RUS-27 stalled (blocker), the
// rest fabricated. Same env, same status, same run — pure model nondeterminism.
//
// The Workflow RUNNER, unlike a workflow-subagent, CAN spawn registered agent
// types via agent({ agentType }). So we lift the orchestration into this script:
// the script spawns the typed phase agents directly, and delegates only the
// Bash/git/Linear mechanics (which the script itself cannot run) to worker agents
// that follow the canonical qrspi-work SKILL.md sections.
// ---------------------------------------------------------------------------

const SKILL = '.claude/skills/qrspi-work/SKILL.md'

// --- schemas ---------------------------------------------------------------

const TICKETS_SCHEMA = {
  type: 'object',
  required: ['tickets'],
  properties: {
    tickets: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'status'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          status: { type: 'string' },
        },
      },
    },
  },
}

const PLAN_SETUP_SCHEMA = {
  type: 'object',
  required: ['ok', 'repoRoot', 'worktreeDir', 'ticketContent', 'existing'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    repoRoot: { type: 'string' },
    worktreeDir: { type: 'string' },
    ticketContent: { type: 'string' },
    existing: {
      type: 'object',
      required: ['questions', 'research', 'design', 'structure', 'plan', 'worktree'],
      properties: {
        questions: { type: 'boolean' },
        research: { type: 'boolean' },
        design: { type: 'boolean' },
        structure: { type: 'boolean' },
        plan: { type: 'boolean' },
        worktree: { type: 'boolean' },
      },
    },
  },
}

const FINALIZE_SCHEMA = {
  type: 'object',
  required: ['ok', 'newStatus', 'summary'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    newStatus: { type: 'string' },
    prUrl: { type: 'string' },
    summary: { type: 'string' },
  },
}

const IMPL_SETUP_SCHEMA = {
  type: 'object',
  required: ['ok', 'repoRoot', 'worktreeDir', 'slices'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    repoRoot: { type: 'string' },
    worktreeDir: { type: 'string' },
    slices: {
      type: 'array',
      items: {
        type: 'object',
        required: ['n', 'goal', 'structureSlice', 'planSlice', 'worktreeSession', 'alreadyCommitted'],
        properties: {
          n: { type: 'number' },
          goal: { type: 'string' },
          structureSlice: { type: 'string' },
          planSlice: { type: 'string' },
          worktreeSession: { type: 'string' },
          alreadyCommitted: { type: 'boolean' },
        },
      },
    },
  },
}

const SLICE_COMMIT_SCHEMA = {
  type: 'object',
  required: ['ok', 'branch', 'notesForNext'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    branch: { type: 'string' },
    notesForNext: { type: 'string' },
  },
}

const INLINE_SCHEMA = {
  type: 'object',
  required: ['ticketId', 'newStatus', 'summary'],
  properties: {
    ticketId: { type: 'string' },
    newStatus: { type: 'string' },
    summary: { type: 'string' },
  },
}

// --- args ------------------------------------------------------------------
// Optional overrides: { statuses?: string[], project?: string }
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const STATUSES = input?.statuses ?? ['Plan Approved', 'Selected'] // Plan Approved first: further along
const PROJECT = input?.project // undefined ⇒ all projects

// --- helpers ---------------------------------------------------------------

const tpl = (worktreeDir, name) => `${worktreeDir}/.qrspi/templates/${name}`
const art = (worktreeDir, id, name) => `${worktreeDir}/.qrspi/${id}/${name}`

// Run one planning phase agent. Skips when the artifact already exists (resume).
// Returns true on success, false if the phase failed/was skipped by the user.
async function runPhase(name, agentType, prompt, ctx) {
  if (ctx.existing[name]) {
    log(`  ${ctx.id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${ctx.id}`, phase: 'Planning', agentType })
  if (res === null) {
    log(`  ${ctx.id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
  log(`  ${ctx.id}: ${name} → ${String(res).slice(0, 80)}`)
  return true
}

// ===========================================================================
// PLANNING PATH  (Backlog / Selected)
// ===========================================================================
async function runPlanning(t) {
  phase('Setup')
  const setup = await agent(
    `You are a setup worker for QRSPI ticket ${t.id}.

1. Fetch the ticket with mcp__linear-russelltsherman__get_issue (identifier ${t.id}). On failure, retry once; if it still fails, return ok:false with the exact error.
2. Read and follow the "Worktree Setup" section of ${SKILL} verbatim to create or reuse the git worktree for ${t.id}. REPO_ROOT is the main repo (where .git/ lives); the worktree is <REPO_ROOT>/.worktrees/${t.id}.
3. Detect which planning artifacts already exist AND are non-empty under <worktreeDir>/.qrspi/${t.id}/: questions.md, research.md, design.md, structure.md, plan.md, worktree.md.

Return:
- ok: true (false only on a hard error)
- repoRoot: absolute path to the main repo
- worktreeDir: absolute path to the ticket worktree
- ticketContent: the ticket title + description (verbatim)
- existing: { questions, research, design, structure, plan, worktree } booleans
Do NOT generate or modify any artifact. Do NOT change Linear status.`,
    { label: `setup:${t.id}`, phase: 'Setup', schema: PLAN_SETUP_SCHEMA }
  )

  if (!setup || !setup.ok) {
    log(`  ${t.id}: setup failed — ${setup?.error ?? 'no result'}`)
    return { ticketId: t.id, newStatus: t.status, summary: `Setup failed: ${setup?.error ?? 'unknown'}` }
  }

  const ctx = { id: t.id, worktreeDir: setup.worktreeDir, repoRoot: setup.repoRoot, existing: setup.existing }
  const wd = setup.worktreeDir

  phase('Planning')

  // Phase 1 — Questions  (gets TICKET_CONTENT)
  if (!await runPhase('questions', 'qrspi-questions',
    `TICKET_ID = ${t.id}
TICKET_CONTENT =
${setup.ticketContent}

ARTIFACT_PATH = ${art(wd, t.id, 'questions.md')}
TEMPLATE_PATH = ${tpl(wd, 'questions.md')}`, ctx)) return failTicket(t)

  // Phase 2 — Research  (RESEARCH FIREWALL: ticket content is intentionally absent)
  if (!await runPhase('research', 'qrspi-research',
    `TICKET_ID = ${t.id}
QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
TEMPLATE_PATH = ${tpl(wd, 'research.md')}
REPO_ROOT = ${wd}

Project scope: explore ONLY files under ${wd}. The ticket is intentionally hidden from you — do not seek it out.`, ctx)) return failTicket(t)

  // Phase 3 — Design  (gets TICKET_CONTENT + questions + research)
  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
TICKET_CONTENT =
${setup.ticketContent}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, ctx)) return failTicket(t)

  // Phase 4 — Structure
  if (!await runPhase('structure', 'qrspi-structure',
    `TICKET_ID = ${t.id}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
TEMPLATE_PATH = ${tpl(wd, 'structure.md')}`, ctx)) return failTicket(t)

  // Phase 5 — Plan
  if (!await runPhase('plan', 'qrspi-plan',
    `TICKET_ID = ${t.id}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
PLAN_PATH = ${art(wd, t.id, 'plan.md')}
TEMPLATE_PATH = ${tpl(wd, 'plan.md')}`, ctx)) return failTicket(t)

  // Phase 6 — Work tree (task DAG document; WORKTREE_PATH here is the ARTIFACT path)
  if (!await runPhase('worktree', 'qrspi-worktree',
    `TICKET_ID = ${t.id}
PLAN_PATH = ${art(wd, t.id, 'plan.md')}
WORKTREE_PATH = ${art(wd, t.id, 'worktree.md')}
TEMPLATE_PATH = ${tpl(wd, 'worktree.md')}`, ctx)) return failTicket(t)

  phase('Finalize')
  const fin = await agent(
    `You are the planning finalize worker for QRSPI ticket ${t.id}. Work inside ${wd}.

1. Verify all six artifacts exist and are non-empty under ${wd}/.qrspi/${t.id}/: questions.md, research.md, design.md, structure.md, plan.md, worktree.md. If any is missing/empty, return ok:false with which — do NOT commit or change Linear.
2. Follow ${SKILL} to commit the planning artifacts as a single planning commit (create it if absent, amend if it exists), submit the planning PR with Graphite, and transition the Linear ticket to "Plan Review" with a phase-transition comment.

Return: ok, newStatus (re-query with mcp__linear-russelltsherman__get_issue_status), prUrl, summary (1-2 sentences).`,
    { label: `finalize-plan:${t.id}`, phase: 'Finalize', schema: FINALIZE_SCHEMA }
  )

  if (!fin || !fin.ok) {
    log(`  ${t.id}: finalize failed — ${fin?.error ?? 'no result'} (artifacts NOT advanced; nothing fabricated)`)
    return { ticketId: t.id, newStatus: t.status, summary: `Planning finalize failed: ${fin?.error ?? 'unknown'}` }
  }
  return { ticketId: t.id, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }
}

function failTicket(t) {
  return { ticketId: t.id, newStatus: t.status, summary: 'A planning phase agent failed; ticket left untouched (no fabrication).' }
}

// ===========================================================================
// IMPLEMENTATION PATH  (Plan Approved)
// ===========================================================================
async function runImplementation(t) {
  phase('Setup')
  const setup = await agent(
    `You are an implementation setup worker for QRSPI ticket ${t.id}.

1. Read and follow the "Worktree Setup" section of ${SKILL} to reuse/create the worktree, and ensure you are on the ${t.id}/planning branch (or the latest slice branch if resuming).
2. Validate planning artifacts exist per the "Plan Approved → Run Implementation" Preflight in ${SKILL}. If structure.md / plan.md / worktree.md are missing or empty, return ok:false with the error (do NOT proceed).
3. Parse structure.md, plan.md, worktree.md and return one entry per vertical slice, in order. For each slice extract the inline text the qrspi-implement agent needs:
   - structureSlice: the Types + Contracts + "Slice N" sections from structure.md
   - planSlice: the "Slice N" section from plan.md
   - worktreeSession: the session for slice N from worktree.md
   - goal: the slice goal (one line)
   - alreadyCommitted: true if a ${t.id}/slice-N branch already has the code committed (resumability)

Return: ok, repoRoot, worktreeDir, slices[]. Do NOT implement anything. Do NOT change Linear.`,
    { label: `impl-setup:${t.id}`, phase: 'Setup', schema: IMPL_SETUP_SCHEMA }
  )

  if (!setup || !setup.ok) {
    log(`  ${t.id}: impl setup failed — ${setup?.error ?? 'no result'}`)
    return { ticketId: t.id, newStatus: t.status, summary: `Impl setup failed: ${setup?.error ?? 'unknown'}` }
  }

  const wd = setup.worktreeDir
  let previousNotes = ''

  phase('Implementation')
  // Slices are strictly sequential: slice N+1's branch parents off slice N.
  for (const s of setup.slices) {
    if (s.alreadyCommitted) {
      log(`  ${t.id}: slice ${s.n} already committed — skipping`)
      continue
    }

    const impl = await agent(
      `TICKET_ID = ${t.id}
SLICE_NUMBER = ${s.n}
WORKTREE_DIR = ${wd}
STRUCTURE_SLICE =
${s.structureSlice}

PLAN_SLICE =
${s.planSlice}

WORKTREE_SESSION =
${s.worktreeSession}

PREVIOUS_NOTES =
${previousNotes || '(none — this is the first slice)'}

IMPL_LOG_PATH = ${art(wd, t.id, 'impl-log.md')}
IMPL_LOG_TEMPLATE_PATH = ${tpl(wd, 'impl-log.md')}`,
      { label: `implement:${t.id}#${s.n}`, phase: 'Implementation', agentType: 'qrspi-implement' }
    )
    if (impl === null) {
      log(`  ${t.id}: slice ${s.n} implementation failed — stopping ticket (prior slices preserved)`)
      return { ticketId: t.id, newStatus: t.status, summary: `Slice ${s.n} failed; stopped without committing it.` }
    }

    // Commit worker: stage ALL changed files, create the slice branch, and return
    // the "Notes for next session" so the next slice gets PREVIOUS_NOTES.
    const commit = await agent(
      `You are the slice commit worker for QRSPI ticket ${t.id}, slice ${s.n}, in ${wd}.
Follow the "Slice execution" commit steps of ${SKILL}: stage EVERY changed/untracked file (the implementation code is the deliverable, not just .qrspi/), then create the ${t.id}/slice-${s.n} branch with Graphite parented on ${s.n === 1 ? `${t.id}/planning` : `${t.id}/slice-${s.n - 1}`}, commit message goal: "${s.goal}".
Then read the "Notes for next session" from this slice's impl-log.md entry.
Return: ok, branch, notesForNext (empty string if none).`,
      { label: `commit:${t.id}#${s.n}`, phase: 'Implementation', schema: SLICE_COMMIT_SCHEMA }
    )
    if (!commit || !commit.ok) {
      log(`  ${t.id}: slice ${s.n} commit failed — ${commit?.error ?? 'no result'}`)
      return { ticketId: t.id, newStatus: t.status, summary: `Slice ${s.n} commit failed.` }
    }
    previousNotes = commit.notesForNext || ''
    log(`  ${t.id}: slice ${s.n}/${setup.slices.length} committed (${commit.branch})`)
  }

  // PR summary agent (typed)
  await agent(
    `TICKET_ID = ${t.id}
IMPL_LOG_PATH = ${art(wd, t.id, 'impl-log.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
PR_SUMMARY_PATH = ${art(wd, t.id, 'pr-summary.md')}
TEMPLATE_PATH = ${tpl(wd, 'pr-summary.md')}
REPO_ROOT = ${wd}`,
    { label: `pr:${t.id}`, phase: 'Implementation', agentType: 'qrspi-pr' }
  )

  phase('Finalize')
  const fin = await agent(
    `You are the implementation finalize worker for QRSPI ticket ${t.id}, in ${wd}.
Follow the "Generate PR summary" amend + "Submit and transition" steps of ${SKILL}:
1. Verify ${wd}/.qrspi/${t.id}/pr-summary.md exists; amend it into the last slice commit.
2. Submit the entire stack with Graphite.
3. Set the pr-summary as the body of the slice-1 PR; set focused bodies on the rest.
4. Transition the Linear ticket to "Code Review".
Return: ok, newStatus (re-query to confirm), prUrl (slice-1 PR), summary.`,
    { label: `finalize-impl:${t.id}`, phase: 'Finalize', schema: FINALIZE_SCHEMA }
  )

  if (!fin || !fin.ok) {
    log(`  ${t.id}: impl finalize failed — ${fin?.error ?? 'no result'}`)
    return { ticketId: t.id, newStatus: t.status, summary: `Impl finalize failed: ${fin?.error ?? 'unknown'}` }
  }
  return { ticketId: t.id, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }
}

// ===========================================================================
// INLINE PATH  (Plan Review / Code Review / Code Approved / Done)
// These states never spawn phase agents, so a single worker agent following
// qrspi-work handles them safely (the nesting limitation does not apply).
// ===========================================================================
async function runInline(t) {
  phase('Inline')
  const res = await agent(
    `You are executing qrspi-work for ticket ${t.id} (current Linear status: "${t.status}").
This status does NOT require spawning phase agents. Read ${SKILL} and follow the section matching the status verbatim — set up/reuse the worktree, address review feedback or perform cleanup as specified, and update Linear as instructed.
If the status unexpectedly routes to a planning/implementation path that requires spawning typed agents, STOP and return newStatus unchanged with a summary saying so (do not fabricate artifacts).
Return: ticketId "${t.id}", newStatus (re-query with mcp__linear-russelltsherman__get_issue_status), summary.`,
    { label: `inline:${t.id}`, phase: 'Inline', schema: INLINE_SCHEMA }
  )
  return res ?? { ticketId: t.id, newStatus: t.status, summary: 'Inline worker skipped/failed.' }
}

// ===========================================================================
// QUERY + DISPATCH
// ===========================================================================
phase('Query')

const batches = await parallel(
  STATUSES.map(status => () =>
    agent(
      `Use mcp__linear-russelltsherman__list_issues with:
- state: "${status}"
- assignee: "me"
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}

Return every ticket as { id, title, status } with id like "RUS-8" and status "${status}". Nothing else.`,
      { label: `list:${status.toLowerCase().replace(/\s+/g, '-')}`, phase: 'Query', schema: TICKETS_SCHEMA }
    )
  )
)

// Merge in STATUSES order (Plan Approved first), dedupe by id.
const seen = new Set()
const tickets = []
for (const b of batches) {
  if (!b) continue
  for (const t of b.tickets) {
    if (seen.has(t.id)) continue
    seen.add(t.id)
    tickets.push(t)
  }
}

log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
if (tickets.length === 0) {
  return { ticketsProcessed: 0, note: `No tickets in ${STATUSES.join(' / ')}` }
}

const PLANNING_STATES = new Set(['Selected', 'Backlog'])

// Sequential: tickets share one .git index, so worktree/Graphite ops must not race.
const results = []
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  log(`[${i + 1}/${tickets.length}] ${t.id} (${t.status}): ${t.title}`)
  let r
  if (PLANNING_STATES.has(t.status)) r = await runPlanning(t)
  else if (t.status === 'Plan Approved') r = await runImplementation(t)
  else r = await runInline(t)
  results.push(r)
  log(`[${i + 1}/${tickets.length}] ${t.id} → ${r.newStatus}`)
}

return { ticketsProcessed: results.length, results }
