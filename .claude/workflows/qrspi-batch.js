export const meta = {
  name: 'qrspi-batch',
  description: 'Drive every assigned in-flight QRSPI ticket one PR-gated step forward by resolving each ticket\'s PR review state and spawning the typed phase agents from the workflow script itself',
  whenToUse: 'After assigning tickets and moving them to Selected, or after approving phase PRs. Runs the autonomously-runnable actions (run_design, advance, submit, land, automatic reset/discard, and revise — addressing a CHANGES_REQUESTED phase PR in place then re-requesting review); leaves not-yet-approved tickets (wait) untouched.',
  phases: [
    { title: 'Query', detail: 'List assigned Selected + in-flight (Design/Plan/Code Review) tickets' },
    { title: 'Resolve', detail: 'Per ticket: worktree + PR-state gather + tested resolver → decision (worker agent)' },
    { title: 'Restack', detail: 'Per ticket: restack the stack onto current trunk so drift/conflicts surface early (worker agent)' },
    { title: 'Design', detail: 'action=run_design → questions/research/design phase agents' },
    { title: 'Plan', detail: 'action=advance(plan) → structure/plan/worktree phase agents' },
    { title: 'Implementation', detail: 'action=advance(implementation) → qrspi-implement per slice + qrspi-pr' },
    { title: 'Finalize', detail: 'Commit/submit/reset/land + best-effort Linear projection (worker agent)' },
    { title: 'Reconcile', detail: 'Opt-in: reap stranded already-merged worktrees via qrspi_cleanup.py (dry-run by default)' },
  ],
}

// ---------------------------------------------------------------------------
// Why this exists
// ---------------------------------------------------------------------------
// A workflow-subagent is NOT provisioned the Agent (subagent-spawning) tool, but
// qrspi-work's design/plan/implementation paths REQUIRE spawning the typed
// `.claude/agents/qrspi-*` phase agents. The Workflow RUNNER (this script) CAN
// spawn registered agent types via agent({ agentType }). So orchestration is
// lifted into the script: it spawns the typed phase agents directly and delegates
// the git/gh/Linear/python mechanics (which the JS sandbox cannot run) to worker
// agents that follow the canonical qrspi-work SKILL.md.
//
// PR-GATED MODEL (see docs/qrspi-pr-gated-lifecycle-design.md):
// PR review state — not Linear status — decides what to do. The single source of
// truth for that decision is the tested resolver (scripts/qrspi_resolve_state.py).
// The JS sandbox cannot run python, so a worker agent runs
//   qrspi_pr_state.py | qrspi_resolve_state.py
// and returns the decision; this script branches on decision.action. We do NOT
// re-derive the decision logic in JS — that would drift from the tested resolver.
//
// Per run, each ticket advances at most ONE autonomous step (each step lands the
// ticket in a review-wait state). `revise` (addressing a formal CHANGES_REQUESTED on a
// frontier phase PR) IS now autonomous: the revise worker edits the phase's own
// artifacts/code in place, amends the phase commit keeping its subject, and re-requests
// review via `gt submit --rerequest-review`. Re-requesting flips the PR's reviewDecision
// back to REVIEW_REQUIRED, so the next pass resolves to `wait` instead of re-firing —
// that decision flip is the loop-safe termination signal, because review THREADS cannot
// be resolved here (GitHub thread mutations 403 on this cross-owned repo — see the
// gh-cross-account note), so threads are left for the reviewer and a thread-only PR (no
// change request) resolves to `wait`, never revise. Not-yet-approved `wait` tickets are
// skipped. Automatic downstream `reset`/discard IS performed (decision 10), then the
// ticket stops at the reset-to phase for its own (now autonomous) CHANGES_REQUESTED revise.
// ---------------------------------------------------------------------------

const SKILL = '.claude/skills/qrspi-work/SKILL.md'

// --- args ------------------------------------------------------------------
// Optional overrides: { statuses?: string[], project?: string,
//                       reconcile?: boolean, reconcileDryRun?: boolean }
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
// Entry status (Selected) + the three reporting/review statuses where an approval
// may have landed that we can act on. *Approved states were dropped (approval lives
// in the PR), so we sweep the review statuses to detect approvals and auto-advance.
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
const PROJECT = input?.project // undefined ⇒ all projects
// Reconciliation pass (RUS-52): reap already-merged-but-uncleaned tickets stranded in
// `.worktrees/` (the backlog the old per-land prose left behind on failure/skip). It is
// OPT-IN (default off — a normal batch run doesn't sweep the whole worktree dir) and
// DRY-RUN BY DEFAULT when enabled, so the first invocation only LISTS the backlog and
// touches nothing; pass reconcileDryRun:false to actually reap. The cleanup script is
// the safety gate — it reaps ONLY a fully-merged clean stack and skips everything else.
const RECONCILE = input?.reconcile === true
const RECONCILE_DRY_RUN = input?.reconcileDryRun !== false // default true

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

// The RESOLVE envelope is NOT a StructuredOutput schema (Option A). The weak local
// worker model could not populate the StructuredOutput tool — it emitted an empty {}
// and looped against schema validation, stalling the whole batch. So the resolve
// agent instead returns qrspi_resolve.py's JSON stdout as plain text, and we parse +
// validate it here with parseResolveEnvelope(). The envelope shape produced by the
// script (its single source of truth) is:
//   { ok:boolean, error?:string, repoRoot, worktreeDir, ticketContent,
//     existing{ questions,research,design,structure,plan,worktree : boolean },
//     reviewers, teamReviewers,                 // comma-joined CSV, "" => omit flag
//     decision{ action, phase, nextPhase, resetToPhase, discardPhases[], reason } }
// action ∈ entry_blocked|run_design|advance|submit|wait|revise|reset|land.
const RESOLVE_ACTIONS = new Set(
  ['entry_blocked', 'run_design', 'advance', 'submit', 'wait', 'revise', 'reset', 'land'])

// Extract the outermost {...} from free text by brace-depth scan (string-aware, so
// braces inside JSON string values don't fool it). Returns the JSON substring or null.
function extractJsonObject(text) {
  const s = String(text == null ? '' : text)
  const start = s.indexOf('{')
  if (start < 0) return null
  let depth = 0, inStr = false, esc = false
  for (let i = start; i < s.length; i++) {
    const c = s[i]
    if (inStr) {
      if (esc) esc = false
      else if (c === '\\') esc = true
      else if (c === '"') inStr = false
    } else if (c === '"') inStr = true
    else if (c === '{') depth++
    else if (c === '}') { depth--; if (depth === 0) return s.slice(start, i + 1) }
  }
  return null
}

// Parse + validate the resolve worker's text into the envelope the orchestrator
// consumes. A garbled/mangled echo fails validation and becomes a clean ok:false
// (recorded as resolve_failed; the idempotent resolver reconciles on the next run)
// rather than driving a corrupted decision.
function parseResolveEnvelope(text, ticketId) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, error: 'resolve: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `resolve: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, error: 'resolve: envelope missing ok flag' }
  if (!env.ok) return env  // script reported a clean ok:false — pass it through verbatim
  // Validate every field the orchestrator will dereference, so a garbled echo cannot
  // act. worktreeDir must be the deterministic path for THIS ticket.
  if (typeof env.worktreeDir !== 'string' || !env.worktreeDir.endsWith(`/.worktrees/${ticketId}`))
    return { ok: false, error: `resolve: worktreeDir not <repo>/.worktrees/${ticketId} (got ${env.worktreeDir})` }
  if (!env.decision || !RESOLVE_ACTIONS.has(env.decision.action))
    return { ok: false, error: `resolve: unknown decision.action (${env.decision && env.decision.action})` }
  return env
}

// Parse + validate the restack worker's text into the qrspi_restack.py envelope
// ({ ok, restacked, error? }). Same text-return + JS-parse shape as resolve (no
// StructuredOutput). A garbled echo becomes a clean ok:false → the ticket is skipped.
function parseRestackEnvelope(text, ticketId) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, error: 'restack: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `restack: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, error: 'restack: envelope missing ok flag' }
  return env
}

// Parse + validate the cleanup worker's text into the qrspi_cleanup.py envelope
// ({ ok, repoRoot, decision, reason, removed{worktree,branches[],remotes[]}, dryRun,
// error? }). Same text-return + JS-parse shape as resolve/restack (no StructuredOutput,
// which the weak local worker could not populate). A garbled echo becomes a clean
// ok:false so the caller logs it and moves on rather than acting on a corrupt verdict.
function parseCleanupEnvelope(text) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, decision: 'skip', error: 'cleanup: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, decision: 'skip', error: `cleanup: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, decision: 'skip', error: 'cleanup: envelope missing ok flag' }
  if (typeof env.decision !== 'string') return { ok: false, decision: 'skip', error: 'cleanup: envelope missing decision' }
  return env
}

const WORKER_SCHEMA = {
  type: 'object',
  required: ['ok', 'summary'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    prUrl: { type: 'string' },
    newStatus: { type: 'string' },
    summary: { type: 'string' },
  },
}

const IMPL_SETUP_SCHEMA = {
  type: 'object',
  required: ['ok', 'worktreeDir', 'slices'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
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

const PERSIST_SCHEMA = {
  type: 'object',
  required: ['ok'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    dest: { type: 'string' },
    bytes: { type: 'number' },
  },
}

// --- helpers ---------------------------------------------------------------

const tpl = (wd, name) => `${wd}/.qrspi/templates/${name}`
const art = (wd, id, name) => `${wd}/.qrspi/${id}/${name}`

// Token-free staging path a phase agent writes its artifact to (Fix A). It carries
// NO "qrspi" token, so the weak local worker model reproduces it intact instead of
// mangling it (qrspi -> qrpii). Kept in sync with scripts/qrspi_persist.py STAGE_ROOT.
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`

function skip(t, decision, note) {
  return { ticketId: t.id, action: decision.action, summary: note }
}

// Build the reviewer flags for `gt submit` from the resolver envelope (r.reviewers /
// r.teamReviewers — comma-joined strings, "" when none). Returns a leading-space
// fragment to splice into a submit command, or '' to omit entirely. The username
// lives in env/config resolved by qrspi_resolve.py, never in this script.
function reviewerFlags(r) {
  const parts = []
  if (r && r.reviewers) parts.push(`--reviewers ${r.reviewers}`)
  if (r && r.teamReviewers) parts.push(`--team-reviewers ${r.teamReviewers}`)
  return parts.length ? ' ' + parts.join(' ') : ''
}

// Persist a staged artifact to its canonical worktree path via the deterministic,
// self-locating script (Fix A). The model never types the qrspi path — the script
// owns it — and the script verifies the staged file is non-empty before moving it,
// so a no-op or path-mangled agent is caught HERE rather than silently surfacing as
// a missing artifact in the finalize worker. Returns the parsed envelope (or null).
async function persistArtifact(id, name, phaseLabel) {
  return await agent(
    `You are the PERSIST worker for ${id} artifact "${name}". Your cwd is the main repo root.
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives:

  python3 scripts/qrspi_persist.py --ticket ${id} --artifact ${name}

It moves the staged artifact into the ticket's worktree at the canonical path (which it
self-locates) and prints JSON { ok, dest, bytes, error? }. Parse that JSON and return it
verbatim. If it reports ok:false, return that as-is — HARD STOP, do NOT retry, do NOT
improvise alternative commands or paths.`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA }
  )
}

// Run one phase agent, then deterministically persist its staged artifact. Reuses an
// existing non-empty canonical artifact (resume). Returns true on success, false on
// failure/skip.
async function runPhase(name, agentType, prompt, existing, id, phaseLabel) {
  if (existing && existing[name]) {
    log(`  ${id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
  // The agent wrote to a token-free staging path; move it to the canonical worktree
  // path deterministically. This is also the real success gate: an agent that
  // mangled its write path or wrote nothing leaves no staged file, so persist fails.
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
}

// ===========================================================================
// RESOLVE — worktree + PR-state gather + tested resolver (single source of truth)
// ===========================================================================
async function resolveTicket(t) {
  phase('Resolve')
  // Token-free staging path (no "qrspi" token) the worker writes the ticket text to,
  // so qrspi_resolve.py — not the model — folds it into the envelope as ticketContent.
  const ticketFile = `/tmp/phase-stage/${t.id}/ticket.md`
  // NO schema: the worker returns the script's JSON stdout as plain text; we parse it
  // with parseResolveEnvelope() (Option A — the StructuredOutput tool path stalled the
  // weak local worker, which emitted empty {} and looped).
  const out = await agent(
    `You are the RESOLVE worker for QRSPI ticket ${t.id}. Your cwd is the main repo root.

Do EXACTLY these steps — no exploration, no path guessing, no extra commentary:

1. Fetch the ticket: mcp__linear__get_issue (identifier ${t.id}). Read its status name and
   whether it is assigned (assignee non-null). Retry once on failure.

2. Stage the ticket text (so the resolver embeds it — you never hand-assemble JSON): run
   Bash \`mkdir -p /tmp/phase-stage/${t.id}\`, then use the Write tool to write the ticket's
   title, then a blank line, then its full description — verbatim — to this token-free path:
     ${ticketFile}

3. Run this ONE command verbatim from your cwd (worktree setup + OWNER/REPO + the tested
   PR-state gather + decision + artifact detection + ticketContent embedding, all in a single
   deterministic step — do NOT hand-derive any of it, do NOT substitute paths):

     python3 scripts/qrspi_resolve.py --ticket ${t.id} --linear-status "<status>" --ticket-content-file ${ticketFile}

   Replace <status> with the Linear status name from step 1. If (and only if) step 1 found the
   ticket assigned, also append the flag  --assigned  to that command.

4. Output the command's STDOUT — the JSON envelope — as your FINAL message: exactly and
   verbatim, with NO surrounding prose, NO code fences, NO edits. That JSON is your entire
   return value. Do NOT call any structured-output tool; do NOT summarize. If the command
   printed ok:false, still output that JSON verbatim (HARD STOP — do NOT retry or improvise
   alternative commands/paths). Do NOT generate/modify artifacts or change Linear.`,
    { label: `resolve:${t.id}`, phase: 'Resolve' }
  )
  return parseResolveEnvelope(out, t.id)
}

// ===========================================================================
// RESTACK — drift gate: every ticket that enters the queue is restacked onto current
// trunk, regardless of its decision (RUS-51). Run ONCE per ticket in the main loop
// right after resolve and before dispatch — NOT per action — so that long-lived
// review-stage branches (wait/revise) and land/reset, which never reach a build/submit
// handler, still get realigned and surface their conflicts EARLY instead of at the
// eventual `gt submit`/`gt merge`. When trunk advances, stacked branches drift to
// "(needs restack)" and a stale parent fails those ops. qrspi_restack.py runs
// `gt restack --downstack` deterministically and idempotently (no-op when already
// aligned); when a branch actually moves it force-pushes the realigned stack
// (`gt submit --publish --stack --force`) so the open PRs stop pointing at the
// pre-restack commits — a restack that only updates local branches would leave the
// remote stale and re-surface the same drift at the eventual submit/merge. A restack
// CONFLICT (or a push failure) comes back ok:false (on conflict the script `gt abort`s
// to keep the tree clean) and the loop surfaces + skips the ticket for the run. The
// worktree it operates on was already provisioned by resolve's setup_worktree, so this
// needs no pre-provisioning. Restacks onto LOCAL trunk only — never `gt sync` a held
// stack, never touch trunk.
// ===========================================================================
async function ensureRestacked(t, phaseLabel) {
  const out = await agent(
    `You are the RESTACK worker for QRSPI ticket ${t.id}. Your cwd is the main repo root.
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives,
no other git/gt commands:

  python3 scripts/qrspi_restack.py --ticket ${t.id}

It restacks the ticket's stack onto the current trunk (self-locating; idempotent) and,
when a branch moved, force-pushes the realigned stack to its PRs; it prints a JSON
envelope { ok, restacked, submitted, error? }. Output that JSON as your FINAL message,
exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT call any
structured-output tool. If it printed ok:false, still output that JSON verbatim (HARD
STOP — do NOT retry, do NOT run gt restack/abort/sync yourself or improvise paths).`,
    { label: `restack:${t.id}`, phase: phaseLabel }
  )
  const rs = parseRestackEnvelope(out, t.id)
  if (!rs.ok) log(`  ${t.id}: restack failed — ${rs.error ?? 'unknown'} (skipping; stack left clean)`)
  else if (rs.restacked) log(`  ${t.id}: restacked stack onto current trunk${rs.submitted ? ' and force-pushed to PRs' : ''}`)
  return rs
}

// ===========================================================================
// ACTION: run_design  (questions → research → design, then submit Design PR)
// ===========================================================================
async function doDesign(t, r) {
  const wd = r.worktreeDir
  phase('Design')

  if (!await runPhase('questions', 'qrspi-questions',
    `TICKET_ID = ${t.id}
TICKET_CONTENT =
${r.ticketContent}

OUTPUT_PATH = ${stg(t.id, 'questions')}
TEMPLATE_PATH = ${tpl(wd, 'questions.md')}`, r.existing, t.id, 'Design')) return failTicket(t)

  if (!await runPhase('research', 'qrspi-research',
    `TICKET_ID = ${t.id}
QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
OUTPUT_PATH = ${stg(t.id, 'research')}
TEMPLATE_PATH = ${tpl(wd, 'research.md')}
REPO_ROOT = ${wd}

Project scope: explore ONLY files under ${wd}. The ticket is intentionally hidden from you — do not seek it out.`, r.existing, t.id, 'Design')) return failTicket(t)

  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
TICKET_CONTENT =
${r.ticketContent}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design')) return failTicket(t)

  phase('Finalize')
  const fin = await agent(
    `You are the DESIGN-PHASE finalize worker for ${t.id}, in ${wd}. Follow the "action: run_design" commit+submit steps of ${SKILL}.
1. Verify questions.md, research.md, design.md exist and are non-empty under ${wd}/.qrspi/${t.id}/. If any missing/empty, return ok:false (do NOT commit/transition).
2. Stage ONLY those three artifacts; add them as the single commit (subject "${t.id} [QR]: Design") on the pre-created ${t.id}/design branch with \`gt modify -c\` (the branch already exists from worktree setup — do NOT use \`gt create\`); submit the Design PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`${reviewerFlags(r) ? ' (the reviewer flag is required — it is what surfaces the PR in the reviewer\'s Graphite queue; submit it EXACTLY as written, do not drop or alter the reviewer)' : ''} (handle a stale closed-PR association per the SKILL "Resubmitting" steps).
3. BEST-EFFORT project Linear → "Design Review" (a failed Linear write is a WARN, not a failure — still return ok:true with the PR created).
Return: ok, prUrl, newStatus, summary (1-2 sentences).`,
    { label: `finalize-design:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  return finResult(t, fin, 'run_design')
}

// ===========================================================================
// ACTION: advance → plan  (structure → plan → worktree, stacked on design)
// ===========================================================================
async function doPlan(t, r) {
  const wd = r.worktreeDir
  phase('Plan')

  if (!await runPhase('structure', 'qrspi-structure',
    `TICKET_ID = ${t.id}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
OUTPUT_PATH = ${stg(t.id, 'structure')}
TEMPLATE_PATH = ${tpl(wd, 'structure.md')}`, r.existing, t.id, 'Plan')) return failTicket(t)

  if (!await runPhase('plan', 'qrspi-plan',
    `TICKET_ID = ${t.id}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
OUTPUT_PATH = ${stg(t.id, 'plan')}
TEMPLATE_PATH = ${tpl(wd, 'plan.md')}`, r.existing, t.id, 'Plan')) return failTicket(t)

  if (!await runPhase('worktree', 'qrspi-worktree',
    `TICKET_ID = ${t.id}
PLAN_PATH = ${art(wd, t.id, 'plan.md')}
OUTPUT_PATH = ${stg(t.id, 'worktree')}
TEMPLATE_PATH = ${tpl(wd, 'worktree.md')}`, r.existing, t.id, 'Plan')) return failTicket(t)

  phase('Finalize')
  const fin = await agent(
    `You are the PLAN-PHASE finalize worker for ${t.id}, in ${wd}. Follow the "action: advance → nextPhase == plan" steps of ${SKILL}.
1. Verify structure.md, plan.md, worktree.md exist and are non-empty under ${wd}/.qrspi/${t.id}/. If any missing/empty, return ok:false.
2. gt checkout ${t.id}/design; stage ONLY those three artifacts; create the ${t.id}/plan branch STACKED on ${t.id}/design with \`gt create\` (single commit "${t.id} [SP]: Plan"); submit the Plan PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`${reviewerFlags(r) ? ' (submit the reviewer flag EXACTLY as written — it is what surfaces the PR in the reviewer\'s Graphite queue)' : ''}.
3. BEST-EFFORT project Linear → "Plan Review" (WARN on failure, still ok:true if the PR was created).
Return: ok, prUrl, newStatus, summary.`,
    { label: `finalize-plan:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  return finResult(t, fin, 'advance:plan')
}

// ===========================================================================
// ACTION: advance → implementation  (slice stack on plan, then land at the end)
// ===========================================================================
async function doImplementation(t, r) {
  phase('Implementation')

  const setup = await agent(
    `You are the implementation setup worker for ${t.id}. Follow the "action: advance → nextPhase == implementation" Preflight of ${SKILL}.
1. Reuse/create the worktree and ensure you are on ${t.id}/plan (or the latest slice branch if resuming).
2. Verify structure.md, plan.md, worktree.md exist+non-empty; if not, return ok:false.
3. Parse them and return one entry per vertical slice the PLAN defines, in order. EVERY planned slice is MANDATORY: do NOT omit, skip, merge, or collapse a slice because an artifact marks it optional, gated, conditional, or "pending OQx" — optionality is NOT honored here, so a plan with N \`## Slice\` headings MUST yield N entries. Fields per entry: structureSlice (Types+Contracts+"Slice N"), planSlice ("Slice N"), worktreeSession (session N), goal (one line), alreadyCommitted (true ONLY if a ${t.id}/slice-N branch already has its code committed — this is the SOLE legal per-slice skip, for resume; a slice being "gated"/"optional" is NOT a reason to set it).
Return: ok, worktreeDir, slices[]. Do NOT implement anything or change Linear.`,
    { label: `impl-setup:${t.id}`, phase: 'Implementation', schema: IMPL_SETUP_SCHEMA }
  )
  if (!setup || !setup.ok) {
    log(`  ${t.id}: impl setup failed — ${setup?.error ?? 'no result'}`)
    return skip(t, r.decision, `Impl setup failed: ${setup?.error ?? 'unknown'}`)
  }

  const wd = setup.worktreeDir
  let previousNotes = ''
  for (const s of setup.slices) {
    if (s.alreadyCommitted) { log(`  ${t.id}: slice ${s.n} already committed — skipping`); continue }

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
${previousNotes || '(none — first slice)'}

IMPL_LOG_PATH = ${art(wd, t.id, 'impl-log.md')}
IMPL_LOG_TEMPLATE_PATH = ${tpl(wd, 'impl-log.md')}`,
      { label: `implement:${t.id}#${s.n}`, phase: 'Implementation', agentType: 'qrspi-implement' }
    )
    if (impl === null) {
      log(`  ${t.id}: slice ${s.n} implementation failed — stopping (prior slices preserved)`)
      return skip(t, r.decision, `Slice ${s.n} failed; stopped without committing it.`)
    }

    const commit = await agent(
      `You are the slice commit worker for ${t.id} slice ${s.n}, in ${wd}. Follow the SKILL "advance → implementation" + "Staging" rules: stage EVERY changed/untracked file EXCEPT generated caches (never stage __pycache__/ or *.pyc) — code is the deliverable, not just .qrspi/ — then create ${t.id}/slice-${s.n} with Graphite parented on ${s.n === 1 ? `${t.id}/plan` : `${t.id}/slice-${s.n - 1}`}. The commit MESSAGE is the PR body Graphite seeds at creation (do NOT use gh to set PR bodies), so write it as: subject line "${t.id} [I] ${s.n}/${setup.slices.length}: ${s.goal}", a blank line, then the focused body "Part ${s.n}/${setup.slices.length} of ${t.id}. See the slice-1 PR for the full feature summary.", a blank line, then the Co-Authored-By trailer. Then read this slice's "Notes for next session" from impl-log.md.
Return: ok, branch, notesForNext (empty string if none).`,
      { label: `commit:${t.id}#${s.n}`, phase: 'Implementation', schema: SLICE_COMMIT_SCHEMA }
    )
    if (!commit || !commit.ok) {
      log(`  ${t.id}: slice ${s.n} commit failed — ${commit?.error ?? 'no result'}`)
      return skip(t, r.decision, `Slice ${s.n} commit failed.`)
    }
    previousNotes = commit.notesForNext || ''
    log(`  ${t.id}: slice ${s.n}/${setup.slices.length} committed (${commit.branch})`)
  }

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
    `You are the implementation finalize worker for ${t.id}, in ${wd}. Follow the SKILL "advance → implementation" submit steps. PR bodies are authored at Graphite CREATION via the commit message — there is NO \`gh pr edit\` step (the gh PAT cannot write PRs on this repo; it returns 403). Do:
1. Amend pr-summary.md into the last slice commit as the durable artifact (git add .qrspi/${t.id}/pr-summary.md && gt modify --no-interactive).
2. Splice pr-summary.md into the SLICE-1 commit MESSAGE (so the slice-1 PR body is the full summary at creation), BEFORE submitting, by running EXACTLY this one self-locating command verbatim — no path edits, no alternatives:
     python3 ${r.repoRoot}/scripts/qrspi_pr_body.py --ticket ${t.id} --slice 1
   It preserves the slice-1 subject+trailer, splices the summary in between, amends via \`gt modify\` (auto-restacking the slices above), and prints JSON { ok, branch, subject, bytes, error? }. If it prints ok:false, return ok:false — HARD STOP, do NOT fall back to gh pr edit or any gt body flag.
3. Submit the entire stack PUBLISHED with Graphite (bodies already live in the commit messages, so --no-edit keeps them; slices 2..N carry their focused "Part N/total" body): \`gt submit --publish --stack${reviewerFlags(r)} --no-edit --no-interactive\`${reviewerFlags(r) ? ' (submit the reviewer flag EXACTLY as written — it surfaces the PRs in the reviewer\'s Graphite queue)' : ''}. Do NOT run gh pr edit.
4. BEST-EFFORT project Linear → "Code Review" (WARN on failure).
Return: ok, prUrl (slice-1 PR), newStatus, summary.`,
    { label: `finalize-impl:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  return finResult(t, fin, 'advance:implementation')
}

// ===========================================================================
// ACTION: submit  (branch exists, PR missing — ensure artifacts then submit)
// ===========================================================================
async function doSubmit(t, r) {
  phase('Finalize')

  const fin = await agent(
    `You are the submit worker for ${t.id} (active phase: ${r.decision.phase}), in ${r.worktreeDir}. Follow the "action: submit" steps of ${SKILL}: the phase branch exists but its PR was not opened. Verify the phase's artifacts are present+non-empty (if any are missing AND cannot be produced, return ok:false — never fabricate). This path CREATES the PR, and PR bodies are authored at Graphite creation via the commit message (there is NO gh pr edit — the gh PAT 403s on PR writes). If the active phase is IMPLEMENTATION, FIRST splice pr-summary.md into the slice-1 commit message by running EXACTLY, verbatim: \`python3 ${r.repoRoot}/scripts/qrspi_pr_body.py --ticket ${t.id} --slice 1\` (if it prints ok:false, return ok:false — HARD STOP). Then submit the PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)} --no-edit --no-interactive\` (add --stack for implementation)${reviewerFlags(r) ? ' — submit the reviewer flag EXACTLY as written, it surfaces the PR in the reviewer\'s Graphite queue' : ''} and BEST-EFFORT project the matching Linear review status. Do NOT run gh pr edit.
Return: ok, prUrl, newStatus, summary.`,
    { label: `submit:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  return finResult(t, fin, 'submit')
}

// ===========================================================================
// ACTION: reset  (automatic downstream discard, return to resetToPhase)
// ===========================================================================
async function doReset(t, r) {
  phase('Finalize')
  const d = r.decision
  const fin = await agent(
    `You are the RESET worker for ${t.id}, in ${r.worktreeDir}. A formal CHANGES_REQUESTED landed on the ${d.resetToPhase} PR, so discard the downstream phases [${(d.discardPhases || []).join(', ')}] AUTOMATICALLY per the "action: reset" steps of ${SKILL}:
1. For each discarded phase (highest first — slices before plan): close its PR(s) and delete its branch(es) with gt delete --force --close.
2. gt checkout ${t.id}/${d.resetToPhase}; remove the now-stale downstream artifacts from the working tree (e.g. structure.md/plan.md/worktree.md when discarding plan) and git clean -fd .qrspi/${t.id}/ so the skip-if-exists resume logic sees them absent. Trunk is never touched (nothing was merged).
3. BEST-EFFORT project Linear → the ${d.resetToPhase} review status.
Do NOT address the ${d.resetToPhase} feedback — that is the manual revise path on a later invocation.
Return: ok, newStatus, summary (name what was discarded).`,
    { label: `reset:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  if (!fin || !fin.ok) return skip(t, d, `Reset failed: ${fin?.error ?? 'unknown'}`)
  return { ticketId: t.id, action: 'reset', newStatus: fin.newStatus, summary: fin.summary }
}

// ===========================================================================
// ACTION: revise  (a formal CHANGES_REQUESTED on a frontier phase PR — address the
// feedback in place, amend the phase commit, and re-request review)
// ===========================================================================
// AUTONOMOUS (per the user's decision). The resolver only emits `revise` when the frontier
// phase PR carries a formal CHANGES_REQUESTED (NOT for thread-only PRs — those route to
// `wait`, since their threads can't be cleared here). The worker:
//   - reads the change-request feedback (a READ via gh graphql/pr view — works fine),
//   - addresses it WITHIN the phase only (the cascade is bounded to the phase's own
//     artifacts; a design-level change that invalidates plan/impl is `reset`, not revise),
//   - amends the phase commit IN PLACE keeping its exact subject, then
//   - `gt submit --publish --no-edit --rerequest-review` (+ `--stack` for implementation).
// Re-requesting review (Graphite's write-capable App credential) flips reviewDecision back
// to REVIEW_REQUIRED, which is what lets the next batch pass return `wait` instead of looping.
// It NEVER attempts to resolve or reply to review threads: every authenticated gh PR-write
// mutation 403s on this cross-owned repo (see the gh-cross-account note), so thread
// resolution is left to the reviewer, exactly as for the rare thread-only `wait` PR.
async function doRevise(t, r) {
  phase('Finalize')
  const d = r.decision
  const fin = await agent(
    `You are the REVISE worker for ${t.id} (frontier phase: ${d.phase}), in ${r.worktreeDir}. A formal CHANGES_REQUESTED landed on the ${d.phase} PR. Address it AUTONOMOUSLY, following the "action: revise" steps of ${SKILL}, with these REQUIRED adaptations:
- DO NOT attempt to resolve or reply to review threads, and DO NOT run any \`gh pr\`/GraphQL mutation: every authenticated gh PR write 403s on this repo. Reading feedback via \`gh pr view\`/\`gh api graphql\` queries is fine. Thread resolution is the reviewer's job — leave threads as-is.
- Stay WITHIN the ${d.phase} phase only — never edit a downstream phase's artifacts (that is \`reset\`, not revise).
Steps:
1. Identify the branch(es) to fix. For design/plan: \`gt checkout ${t.id}/${d.phase} --no-interactive\`. For implementation: query the ticket's slice PRs (\`gh pr list --head ${t.id}/slice-... \` or graphql) and address EVERY slice whose PR is CHANGES_REQUESTED, lowest slice number first (changes restack upward).
2. Read the change request: the CHANGES_REQUESTED review body AND any unresolved thread comments (READ-only queries per the SKILL).
3. Address the feedback by editing the phase's artifacts/code in ${r.worktreeDir}.
4. Stage your edits AND amend the phase commit IN PLACE by running EXACTLY this one self-locating command verbatim (no path edits, no alternatives) — for design/plan run it once; for implementation run it once per CHANGES_REQUESTED slice branch, lowest slice number first:
   \`python3 ${r.repoRoot}/scripts/qrspi_revise_amend.py --ticket ${t.id} --branch <BRANCH>\` where <BRANCH> = \`${t.id}/${d.phase}\` for design/plan, or \`${t.id}/slice-<N>\` for an implementation slice.
   The script checks out the branch, stages every edit you made (excluding caches), amends the commit with \`gt modify\` keeping its EXACT subject+trailers (it does NOT rename the subject), and VERIFIES the amend captured your changes — it FAILS if nothing was staged (you made no real edit, or left edits unstaged — the original revise bug) or if the working tree is left dirty. It prints JSON { ok, branch, oldOid, newOid, dirty, error? }. If ANY invocation prints ok:false, return ok:false — HARD STOP; do NOT hand-run \`gt modify\`/\`git add\`/\`git commit\`/\`git reset\` to work around it. Never run a bare \`gt modify --no-interactive\` here: without staging it amends an empty index and silently drops your edits.
5. Re-request review so the stale CHANGES_REQUESTED is cleared: \`gt submit --publish --no-edit --rerequest-review${reviewerFlags(r)}${d.phase === 'implementation' ? ' --stack' : ''} --no-interactive\`. Do NOT run \`gh pr edit\`.
6. BEST-EFFORT keep Linear in the current review status (a failed Linear write is a WARN, still return ok:true if the changes were pushed and review re-requested).
Return: ok, prUrl, newStatus, summary (name what you changed and confirm review was re-requested; if you could not address the feedback, return ok:false with the verbatim reason — never fabricate a fix).`,
    { label: `revise:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  return finResult(t, fin, `revise:${d.phase}`)
}

// ===========================================================================
// CLEANUP — deterministic post-merge reap (RUS-52). Replaces the old unsafe
// `gt sync --force` / `git worktree remove --force 2>/dev/null` prose with a single
// verbatim invocation of the self-locating, tested qrspi_cleanup.py. The script
// derives REPO_ROOT from its own path, so it MUST run from the MAIN checkout (cwd =
// main repo root) for the destroy path to see the real `.worktrees/<id>` — run from
// inside the worktree, REPO_ROOT would be the worktree and the target absent → skip.
// It computes a classifier verdict (blocked > destroy > skip), reaps only on a
// fully-merged clean stack, and gates ALL destruction behind --dry-run. A dirty
// worktree comes back decision:"blocked" (logged + left for a human, never forced).
// Infra errors surface ONCE as ok:false and are never retried.
// ===========================================================================
async function runCleanup(ticketId, dryRun, phaseLabel) {
  const dryFlag = dryRun ? ' --dry-run' : ''
  const out = await agent(
    `You are the CLEANUP worker for QRSPI ticket ${ticketId}. Your cwd is the MAIN repo root (NOT a worktree — the script self-locates REPO_ROOT from its own path and must see the real .worktrees/${ticketId}).
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives, no other git/gt/gh commands, do NOT run \`gt sync --force\` or \`git worktree remove\` yourself:

  python3 scripts/qrspi_cleanup.py --ticket ${ticketId}${dryFlag}

It computes the cleanup verdict and (unless --dry-run) reaps the ticket's worktree, local branches, and remote refs, printing a JSON envelope { ok, repoRoot, decision, reason, removed{worktree,branches[],remotes[]}, dryRun, error? }. Output that JSON as your FINAL message, exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT call any structured-output tool. If it printed ok:false, still output that JSON verbatim (HARD STOP — do NOT retry or improvise).`,
    { label: `cleanup:${ticketId}`, phase: phaseLabel }
  )
  return parseCleanupEnvelope(out)
}

// ===========================================================================
// ACTION: land  (all PRs approved+clean — merge the stack bottom-up, finalize)
// ===========================================================================
async function doLand(t, r) {
  phase('Finalize')
  // 1. Merge the stack bottom-up + best-effort Linear → Done (the land worker; it no
  //    longer does worktree/branch cleanup — that is the deterministic script below).
  const fin = await agent(
    `You are the LAND worker for ${t.id}, in ${r.worktreeDir}. Every PR in the stack is approved+clean. Follow the "action: land" steps of ${SKILL}: ensure the stack is current (gt submit --publish --stack), merge bottom-up (gt merge --no-interactive — NOT --confirm, which forces a prompt --no-interactive cannot satisfy), then BEST-EFFORT project Linear → "Done". Do NOT remove the worktree, delete branches, or run \`gt sync --force\` — a separate deterministic cleanup step (qrspi_cleanup.py) handles all reaping AFTER the merge. Treat any infrastructure/merge error as a HARD STOP (return ok:false, verbatim error).
Return: ok, prUrl, newStatus, summary.`,
    { label: `land:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const res = finResult(t, fin, 'land')
  // 2. Only reap if the merge actually succeeded — never destroy a worktree behind a
  //    failed/partial land (the idempotent cleanup script will reap on a later run once
  //    the stack truly merged). The script itself re-verifies full-merge state, so a
  //    transient land result that lost its merge verdict still can't cause a bad reap.
  if (!fin || !fin.ok) return res
  const cl = await runCleanup(t.id, /* dryRun */ false, 'Finalize')
  if (!cl.ok) {
    log(`  ${t.id}: cleanup failed after land — ${cl.error ?? 'unknown'} (worktree left for a later reconciliation pass)`)
  } else if (cl.decision === 'destroy') {
    log(`  ${t.id}: cleaned up — worktree ${cl.removed?.worktree ? 'removed' : 'absent'}, branches [${(cl.removed?.branches ?? []).join(', ')}], remotes [${(cl.removed?.remotes ?? []).join(', ')}]`)
  } else {
    log(`  ${t.id}: cleanup decision=${cl.decision} — ${cl.reason ?? ''} (no reap)`)
  }
  res.cleanup = { decision: cl.decision, ok: cl.ok, removed: cl.removed }
  return res
}

// --- result helpers --------------------------------------------------------
function failTicket(t) {
  return { ticketId: t.id, action: 'failed', summary: 'A phase agent failed; ticket left untouched (no fabrication).' }
}
function finResult(t, fin, action) {
  if (!fin || !fin.ok) {
    log(`  ${t.id}: ${action} finalize failed — ${fin?.error ?? 'no result'} (nothing advanced)`)
    return { ticketId: t.id, action, summary: `${action} finalize failed: ${fin?.error ?? 'unknown'}` }
  }
  return { ticketId: t.id, action, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }
}

// ===========================================================================
// RECONCILIATION — reap already-merged-but-uncleaned tickets (RUS-52, AC4/AC5).
// Candidate finished tickets are enumerated from git/GitHub state — the live
// `.worktrees/<id>` directories — NOT a Linear `Done` sweep (ref: Q8, OQ1): Linear
// status is a best-effort projection and can lag/diverge from the real merged state,
// so the authoritative signal is "a worktree still exists on disk." Every candidate is
// then handed to qrspi_cleanup.py, which is the per-ticket safety gate: it independently
// classifies (blocked > destroy > skip) and reaps ONLY a fully-merged clean stack —
// an in-flight stack comes back `skip` (untouched), a dirty one `blocked` (logged and
// skipped, NEVER forced), so enumerating every worktree is safe. One blocked/failed
// ticket is logged and the pass proceeds to the rest (ref: OQ2).
// ===========================================================================
const RECONCILE_CANDIDATES_SCHEMA = {
  type: 'object',
  required: ['tickets'],
  properties: {
    tickets: { type: 'array', items: { type: 'string' } },
  },
}

async function reconcileCandidates() {
  const out = await agent(
    `You are the RECONCILE-ENUMERATE worker. Your cwd is the MAIN repo root.
Run EXACTLY these read-only commands (no destruction, no git/gt/gh mutations) to list the
candidate ticket ids whose worktree still exists on disk — the stranded backlog:

  ls -1 .worktrees 2>/dev/null

Each immediate subdirectory name of \`.worktrees/\` that looks like a ticket id (e.g. RUS-52,
matching ^[A-Z]+-[0-9]+$) is a candidate. Ignore any other entries (files, dotfiles, names
that don't match). Return ONLY the matching directory names.
Return a StructuredOutput with shape { tickets: string[] } — the deduplicated, sorted list of
candidate ticket ids. If \`.worktrees\` is absent or empty, return { tickets: [] }.`,
    { label: 'reconcile-enumerate', phase: 'Reconcile', schema: RECONCILE_CANDIDATES_SCHEMA }
  )
  if (!out || !Array.isArray(out.tickets)) return []
  // De-dup + keep only well-formed ticket ids (defensive — the worker is told to filter,
  // but a corrupt echo must not feed a junk id to the cleanup script).
  const valid = /^[A-Z]+-[0-9]+$/
  return [...new Set(out.tickets.filter(id => typeof id === 'string' && valid.test(id)))].sort()
}

async function runReconciliation(alreadyProcessed) {
  phase('Reconcile')
  const candidates = await reconcileCandidates()
  // Skip tickets the main loop already handled this run (a land just reaped them) so we
  // don't double-invoke cleanup on a worktree that's mid-reap or already gone.
  const pending = candidates.filter(id => !alreadyProcessed.has(id))
  log(`Reconciliation: ${candidates.length} worktree candidate(s)` +
      `${alreadyProcessed.size ? `, ${pending.length} after excluding this run's ${alreadyProcessed.size} processed` : ''}` +
      ` — ${RECONCILE_DRY_RUN ? 'DRY-RUN (listing only, touching nothing)' : 'REAPING for real'}`)
  if (pending.length === 0) return []
  const reaped = []
  // Sequential: tickets share one .git index, so worktree/branch reaps must not race.
  for (const id of pending) {
    const cl = await runCleanup(id, RECONCILE_DRY_RUN, 'Reconcile')
    if (!cl.ok) {
      log(`  ${id}: reconcile cleanup failed — ${cl.error ?? 'unknown'} (skipped; pass continues)`)
      reaped.push({ ticketId: id, decision: cl.decision ?? 'skip', ok: false, dryRun: RECONCILE_DRY_RUN, error: cl.error })
      continue
    }
    if (cl.decision === 'destroy') {
      log(`  ${id}: ${RECONCILE_DRY_RUN ? 'WOULD reap' : 'reaped'} — worktree ${cl.removed?.worktree ? (RECONCILE_DRY_RUN ? 'present' : 'removed') : 'absent'}, branches [${(cl.removed?.branches ?? []).join(', ')}], remotes [${(cl.removed?.remotes ?? []).join(', ')}]`)
    } else if (cl.decision === 'blocked') {
      // A dirty worktree — logged and SKIPPED, never forced; the pass proceeds (OQ2).
      log(`  ${id}: BLOCKED — ${cl.reason ?? 'dirty worktree'} (left untouched for a human; pass continues)`)
    } else {
      log(`  ${id}: skip — ${cl.reason ?? 'not fully merged'} (in-flight; left untouched)`)
    }
    reaped.push({ ticketId: id, decision: cl.decision, ok: cl.ok, dryRun: RECONCILE_DRY_RUN, removed: cl.removed })
  }
  return reaped
}

// ===========================================================================
// QUERY + DISPATCH
// ===========================================================================
phase('Query')

const batches = await parallel(
  STATUSES.map(status => () =>
    agent(
      `Use mcp__linear__list_issues with:
- state: "${status}"
- assignee: "me"
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}

Return every ticket as { id, title, status } with id like "RUS-8" and status "${status}". Nothing else.`,
      { label: `list:${status.toLowerCase().replace(/\s+/g, '-')}`, phase: 'Query', schema: TICKETS_SCHEMA }
    )
  )
)

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
  // No in-flight queue, but the reconciliation backlog is independent of it — still
  // reap stranded merged worktrees when the pass is enabled.
  const reconciliation = RECONCILE ? await runReconciliation(new Set()) : undefined
  return { ticketsProcessed: 0, note: `No tickets in ${STATUSES.join(' / ')}`, reconciliation }
}

// Sequential: tickets share one .git index, so worktree/Graphite ops must not race.
const results = []
// Tickets handled this run (a land already reaped these) — excluded from reconciliation.
const processed = new Set()
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  log(`[${i + 1}/${tickets.length}] ${t.id} (${t.status}): ${t.title}`)

  // Per-ticket isolation: a thrown phase agent (e.g. a finalize worker whose
  // StructuredOutput result is lost to a transient API/socket error — even after
  // its commit+PR side effects landed) must NOT abort the remaining tickets. Record
  // the error and continue; the idempotent resolver reconciles partial work on re-run.
  try {
    const r = await resolveTicket(t)
    if (!r || !r.ok) {
      log(`  ${t.id}: resolve failed — ${r?.error ?? 'no result'}`)
      results.push({ ticketId: t.id, action: 'resolve_failed', summary: r?.error ?? 'unknown' })
      continue
    }

    // Drift gate (RUS-51): restack EVERY queued ticket onto current trunk before we
    // dispatch its action — including wait/revise/land/reset, which never reach a
    // build/submit handler — so trunk-divergence conflicts surface here, early and
    // clean, instead of at the eventual gt submit/merge. A conflict comes back ok:false
    // (qrspi_restack.py already `gt abort`ed, leaving the tree clean); we record it and
    // skip the ticket for this run rather than driving an action onto a wedged stack.
    // The worktree was provisioned by resolve, so restack has something to operate on.
    phase('Restack')
    const rs = await ensureRestacked(t, 'Restack')
    if (!rs.ok) {
      log(`  ${t.id}: restack CONFLICT — ${rs.error ?? 'unknown'} (surfaced; not advanced this run; tree left clean)`)
      results.push({ ticketId: t.id, action: 'restack_conflict', summary: rs.error ?? 'restack conflict' })
      continue
    }

    const a = r.decision.action
    log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
    let res
    switch (a) {
      case 'run_design': res = await doDesign(t, r); break
      case 'advance':
        res = r.decision.nextPhase === 'plan' ? await doPlan(t, r)
            : r.decision.nextPhase === 'implementation' ? await doImplementation(t, r)
            : skip(t, r.decision, `advance to unknown phase ${r.decision.nextPhase}`)
        break
      case 'submit': res = await doSubmit(t, r); break
      case 'reset': res = await doReset(t, r); break
      case 'revise': res = await doRevise(t, r); break
      case 'land': res = await doLand(t, r); break
      case 'wait':         // not-yet-approved (or thread-only PR awaiting reviewer): nothing to do
      case 'entry_blocked':
      default:
        res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
        log(`  ${t.id}: skipped (${a})`)
    }
    results.push(res)
    processed.add(t.id)
    log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}`)
  } catch (err) {
    const summary = err?.message ?? String(err)
    log(`  ${t.id}: ERRORED — ${summary} (side effects may have partially landed; resolver reconciles on re-run)`)
    results.push({ ticketId: t.id, action: 'errored', summary })
  }
}

// Reconciliation pass (RUS-52): reap stranded already-merged worktrees the per-land
// path missed. Opt-in (RECONCILE) and dry-run by default; excludes this run's tickets.
const reconciliation = RECONCILE ? await runReconciliation(processed) : undefined

return { ticketsProcessed: results.length, results, reconciliation }
