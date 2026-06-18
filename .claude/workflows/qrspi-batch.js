export const meta = {
  name: 'qrspi-batch',
  description: 'Drive every assigned in-flight QRSPI ticket one PR-gated step forward by resolving each ticket\'s PR review state and spawning the typed phase agents from the workflow script itself',
  whenToUse: 'After assigning tickets and moving them to Selected, or after approving phase PRs. Runs the autonomously-runnable actions (run_design, advance, submit, land, automatic reset/discard, and revise — addressing a CHANGES_REQUESTED phase PR in place then re-requesting review); leaves not-yet-approved tickets (wait) untouched.',
  phases: [
    { title: 'Query', detail: 'List assigned Selected + in-flight (Design/Plan/Code Review) tickets, scoped to the mapped Linear project (input.ticket > input.allProjects > input.project > config linearProject > "QRSPI"); input.ticket fetches that one issue and skips the sweep' },
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
// that decision flip is the loop-safe termination signal, because review THREADS cannot be
// auto-RESOLVED here (only the reviewer resolves a thread), so threads are left for the
// reviewer. `revise` is the UNIFIED feedback action (it subsumes the former respond_comment,
// RUS-54): a phase PR carrying a formal change request AND/OR unaddressed reviewer COMMENTS is
// handled in one pass — each comment is engaged per-intent (answer/apply/decline) and replied
// to via scripts/qrspi_comment_reply.py, and review is re-requested only when a formal change
// request is present. gh comment writes succeed with the bot's classic PAT (the old
// cross-account write block is gone, see the gh-cross-account note); idempotency is
// structural (an observed bot reply removes the comment from the gather's unaddressed set).
// A PR whose ONLY outstanding signal is unresolved threads — no change request, no unaddressed
// comment — resolves to `wait`. Not-yet-approved `wait` tickets are skipped. Automatic
// downstream `reset`/discard IS performed (decision 10), then the ticket stops at the reset-to
// phase for its own (now autonomous) CHANGES_REQUESTED revise.
// ---------------------------------------------------------------------------

// ENGINE_ROOT — the directory the QRSPI ENGINE (this workflow + its scripts/ + skills/)
// lives in, as distinct from the HOST checkout the engine operates on. Every bare-relative
// `scripts/qrspi_*.py` invocation and the SKILL path are addressed THROUGH this constant so
// they survive the engine no longer being the worker's cwd (RUS-60 §Delta, Risk Register
// row 3). This is the INTERIM derived-engine-constant indirection: today the engine IS the
// main checkout the batch runs from, so it derives from the runner's cwd and resolves to the
// same paths the bare-relative strings used to (behavior-preserving). The
// `${CLAUDE_PLUGIN_ROOT}` carriage that lets the engine live in an installed plugin dir is
// sub-ticket 3 — wired here as the FIRST precedence so flipping to a plugin install is a
// one-line change. The `'.'` fallback keeps the deterministic engine==cwd behavior when
// neither the env var nor process.cwd() is available in the sandbox.
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) ||
  '.'

// engineCmd(rel) — prefix an engine-relative path (e.g. `scripts/qrspi_persist.py` or the
// SKILL md) with ENGINE_ROOT, so a worker addresses the engine file by an explicit root
// rather than assuming the engine is its cwd.
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`

// engineCmdFor(r, rel) — engine path for prompts that run in a WORKER cwd (a worktree),
// where engineCmd's `.` fallback is WRONG. ENGINE_ROOT resolves to the RUNNER's cwd (the
// main checkout) — or to a bare `.` when the sandbox does not expose process.cwd(). A `.`
// re-resolves against the *worker's* cwd, not the runner's: a finalize/submit/revise worker
// runs "in <worktree>", so `./scripts/...` looks inside the worktree. That misses whenever a
// ticket's branch has RELOCATED the engine scripts (RUS-62 git-mv's scripts/ → plugin/scripts/
// in its own HEAD), producing the "No such file or directory" hard stop.
//
// The anchor must be ABSOLUTE and reliably present. `r.repoRoot` is NOT reliable: it rides the
// weak resolve worker's verbatim-stdout echo and — unlike worktreeDir/decision, which
// parseResolveEnvelope VALIDATES — is silently dropped when the worker reshapes its output,
// leaving engineRootFor to fall back to the broken `.`. `r.worktreeDir` IS reliable: the parser
// REQUIRES it to be `<absolute-root>/.worktrees/<ticketId>`, so stripping that suffix yields the
// MAIN checkout root deterministically (the engine scripts live at <root>/scripts/ on trunk,
// present regardless of what a worktree's HEAD moved). Precedence: CLAUDE_PLUGIN_ROOT (the
// future plugin install, mirroring ENGINE_ROOT's first precedence) → host root derived from
// worktreeDir → ENGINE_ROOT.
const hostRootFromWorktree = (r) => {
  const wd = r && r.worktreeDir
  if (typeof wd !== 'string') return null
  const m = wd.match(/^(.*)\/\.worktrees\/[^/]+$/)
  return m ? m[1] : null
}
const engineRootFor = (r) =>
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  hostRootFromWorktree(r) ||
  ENGINE_ROOT
const engineCmdFor = (r, rel) => `${engineRootFor(r)}/${rel}`

// provisionStep(r, t) — the verbatim STEP 0 EVERY worktree-touching worker must run, in its
// OWN process, before ANY git/gt/gh command. The sandbox does NOT preserve a worktree's
// `.git/worktrees/<id>` admin metadata across the agent/process boundary (the `.worktrees/<id>`
// working dir survives — it lives in the working tree — but its admin dir is pruned/lost), so
// resolve's and restack's earlier provisioning is already undone by the time THIS later worker
// starts: without re-provisioning, the worker's first git/gt op dies with `fatal: not a git
// repository` (the exact failure that wedged submit/land). qrspi_provision.py self-heals in
// place, content-preservingly (any uncommitted artifacts a prior phase agent persisted survive).
// Mirrors qrspi_restack.py's in-process provision_worktree — the same window, closed for the
// finalize/revise/reset/land workers that lacked it. The script self-locates the repo root, so
// it runs correctly regardless of the worker's cwd.
const provisionStep = (r, t) =>
  `STEP 0 (MANDATORY — before ANY git/gt/gh command): (re-)provision the worktree IN THIS PROCESS by running EXACTLY, verbatim: \`python3 ${engineCmdFor(r, 'scripts/qrspi_provision.py')} --ticket ${t.id}\`. The worktree's git admin metadata does not survive the agent boundary, so this self-heal is REQUIRED or every git/gt op below dies with "fatal: not a git repository"; it preserves any uncommitted artifacts already persisted into the worktree. If it prints ok:false, return ok:false — HARD STOP (do NOT hand-run \`git worktree add\`/\`git worktree repair\` to work around it). On ok:true, proceed with the steps below.
`

const SKILL = engineCmd('.claude/skills/qrspi-work/SKILL.md')

// --- args ------------------------------------------------------------------
// Optional overrides: { statuses?: string[], ticket?: string, project?: string,
//                       allProjects?: boolean,
//                       reconcile?: boolean, reconcileDryRun?: boolean }
//
// PROJECT SCOPE (RUS-66, RUS-73): the Query sweep is scoped to ONE Linear project by
// default — the repo's mapped project — instead of every project the assignee
// touches. Scope is resolved at Query start through this precedence chain:
//   input.ticket > input.allProjects > input.project > config linearProject > "QRSPI"
//   0. input.ticket (RUS-73; truthy after trim) ⇒ SINGLE-TICKET scope: fetch THIS
//      one issue via mcp__linear__get_issue and skip project-scope resolution / the
//      list_issues sweep / the order step entirely. A not-found id aborts (fail loud).
//   1. input.allProjects === true  ⇒ ALL projects (the explicit opt-in; an
//      undefined/absent project no longer means "all projects").
//   2. input.project (truthy after trim; a blank/whitespace value is normalized
//      to unset and falls through) ⇒ that concrete project.
//   3. the config linearProject value (scripts/qrspi_config.py --key linearProject,
//      reading .qrspi/config.json) ⇒ that concrete project.
//   4. "QRSPI" (the helper's built-in default) ⇒ that concrete project.
// A concrete resolved scope that matches NO Linear project aborts the Query phase
// (fail loud, naming the unresolved project) rather than sweeping silently empty.
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
// Entry status (Selected) + the three reporting/review statuses where an approval
// may have landed that we can act on. *Approved states were dropped (approval lives
// in the PR), so we sweep the review statuses to detect approvals and auto-advance.
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
// All-projects is now an EXPLICIT opt-in (was: any falsy project ⇒ all projects).
const ALL_PROJECTS = input?.allProjects === true
// input.project, blank/whitespace normalized to unset (so a blank string falls
// through to config rather than meaning all-projects).
const PROJECT_ARG = (typeof input?.project === 'string' && input.project.trim() !== '')
  ? input.project.trim()
  : undefined
// input.ticket (RUS-73): single-ticket scope. When present (truthy after trim; a
// blank/whitespace value is normalized to unset), the Query phase fetches THIS one
// issue via mcp__linear__get_issue and skips project-scope resolution / the
// list_issues sweep / the ordering step entirely. It heads the scope precedence:
// input.ticket > input.allProjects > input.project > config linearProject > "QRSPI".
const TICKET_ARG = (typeof input?.ticket === 'string' && input.ticket.trim() !== '')
  ? input.ticket.trim()
  : undefined
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
        required: ['id', 'title', 'status', 'createdAt'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          status: { type: 'string' },
          createdAt: { type: 'string' },
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
//   { ok:boolean, error?:string, repoRoot, worktreeDir, ticketContentPath,
//     existing{ questions,research,design,structure,plan,worktree : boolean },
//     reviewers, teamReviewers,                 // comma-joined CSV, "" => omit flag
//     commentTargets[],                         // unaddressed reviewer comments (revise)
//     ciFailing:boolean, ciFailingChecks[],     // RUS-81: frontier CI is RED + failing checks
//     decision{ action, phase, nextPhase, resetToPhase, discardPhases[],
//               commentTargets[], changeRequested, ciFailing, reason } }
// action ∈ entry_blocked|run_design|advance|submit|wait|revise|reset|land.
const RESOLVE_ACTIONS = new Set(
  ['entry_blocked', 'run_design', 'advance', 'submit', 'wait', 'revise',
   'reset', 'land'])

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

// Scan for the first balanced top-level JSON ARRAY in text (qrspi_order_tickets.py emits
// a tickets ARRAY on stdout, not an object — so extractJsonObject does not apply). Mirrors
// the brace-matching of extractJsonObject for brackets.
function extractJsonArray(text) {
  const s = String(text == null ? '' : text)
  const start = s.indexOf('[')
  if (start < 0) return null
  let depth = 0, inStr = false, esc = false
  for (let i = start; i < s.length; i++) {
    const c = s[i]
    if (inStr) {
      if (esc) esc = false
      else if (c === '\\') esc = true
      else if (c === '"') inStr = false
    } else if (c === '"') inStr = true
    else if (c === '[') depth++
    else if (c === ']') { depth--; if (depth === 0) return s.slice(start, i + 1) }
  }
  return null
}

// Parse + validate the order worker's text into the SORTED tickets array (RUS-71). This is
// order-only: a garbled/mangled echo, a parse failure, or any drift from the input id-set
// returns null so the caller keeps the deduped (correct, just unsorted) queue — sorting is
// a nicety, never a gate, and must never add, drop, or mutate tickets. The returned array
// must be a permutation of the input (same multiset of ids) for the sort to be accepted.
function parseOrderedTickets(text, original) {
  const raw = extractJsonArray(text)
  if (!raw) return null
  let arr
  try { arr = JSON.parse(raw) } catch { return null }
  if (!Array.isArray(arr) || arr.length !== original.length) return null
  const want = original.map(t => t && t.id).sort()
  const got = arr.map(t => t && typeof t === 'object' ? t.id : undefined).sort()
  for (let i = 0; i < want.length; i++) if (want[i] !== got[i]) return null
  return arr
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

// Parse + validate the trunk-sync worker's text into the qrspi_sync_trunk.py envelope
// (SyncEnvelope { ok, repoRoot, updated, from, to, error? }). Same text-return + JS-parse
// shape as restack (no StructuredOutput). Validates `ok` is boolean and, on the ok path,
// that updated/from/to are present (the helper always emits them on its two ok tokens);
// fail-loud tokens carry a verbatim `error`. A garbled echo becomes a clean ok:false so the
// caller surfaces it and aborts the run (sync is a hard gate, not a skip).
function parseSyncTrunkEnvelope(text) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, error: 'sync-trunk: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `sync-trunk: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, error: 'sync-trunk: envelope missing ok flag' }
  if (env.ok && (typeof env.updated !== 'boolean' || !('from' in env) || !('to' in env))) {
    return { ok: false, error: 'sync-trunk: ok envelope missing updated/from/to' }
  }
  return env
}

// Parse + validate the cleanup worker's text into the qrspi_cleanup.py envelope
// ({ ok, repoRoot, decision, reason, removed{worktree,branches[],remotes[]},
// failedRemotes[], dryRun, error? }). Same text-return + JS-parse shape as resolve/restack
// (no StructuredOutput, which the weak local worker could not populate). A garbled echo
// becomes a clean ok:false so the caller logs it and moves on rather than acting on a
// corrupt verdict. `failedRemotes` (RUS-68) is an ADDITIVE field the parse passes through
// untouched: it is NOT validated/required here, so an older producer envelope that omits it
// parses cleanly (the consumer reads `env.failedRemotes` defensively as `?? []`).
function parseCleanupEnvelope(text) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, decision: 'skip', error: 'cleanup: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, decision: 'skip', error: `cleanup: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, decision: 'skip', error: 'cleanup: envelope missing ok flag' }
  if (typeof env.decision !== 'string') return { ok: false, decision: 'skip', error: 'cleanup: envelope missing decision' }
  return env
}

// Parse the LandVerdict JSON the qrspi_land_verify.py worker emits:
//   { status: "landed" | "incomplete", openBranches: string[] }
// A missing/unparseable/unknown verdict is treated as NOT landed (incomplete) so the
// Done gate fails closed — never project Done on an ambiguous land result.
function parseLandVerdict(text) {
  const raw = extractJsonObject(text)
  if (!raw) return { status: 'incomplete', openBranches: [], error: 'land-verify: no JSON verdict in worker output' }
  let v
  try { v = JSON.parse(raw) } catch (e) { return { status: 'incomplete', openBranches: [], error: `land-verify: unparseable verdict (${e.message})` } }
  if (v.status !== 'landed' && v.status !== 'incomplete') {
    return { status: 'incomplete', openBranches: [], error: 'land-verify: verdict missing/unknown status' }
  }
  return { status: v.status, openBranches: Array.isArray(v.openBranches) ? v.openBranches : [] }
}

// Parse + validate the config worker's text into the qrspi_config.py envelope
// ({ ok, key, value, error? }). Same text-return + JS-parse shape as resolve/restack
// (no StructuredOutput). A garbled echo or a non-ok/non-string value becomes a clean
// ok:false so the caller can decide (here: hard-fail the Query scope resolution rather
// than silently fall through to a wrong/empty sweep — see Slice 1 notes, RUS-66).
function parseConfigEnvelope(text, key) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, error: 'config: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `config: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, error: 'config: envelope missing ok flag' }
  if (!env.ok) return env  // helper reported a clean ok:false — pass it through verbatim
  if (env.key !== key) return { ok: false, error: `config: envelope key mismatch (want ${key}, got ${env.key})` }
  if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
  return env
}

// Read the additive RUS-68 `failedRemotes` list off a parsed cleanup envelope, tolerating
// its absence (older producers) and any non-array junk. Non-empty ⇒ the prune attempted but
// some `<ticket>/*` origin refs are still present — a RETRIABLE partial failure (the run is
// still ok:true), NOT a hard stop. The next Reconcile pass re-attempts the prune.
function cleanupFailedRemotes(cl) {
  return Array.isArray(cl?.failedRemotes) ? cl.failedRemotes : []
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

// One peer-reviewer worker's result for a single reviewer comment (respondToComments).
// `applied` is true only when the worker chose APPLY and the amend+publish succeeded; a
// pure ANSWER/DECLINE reply is ok:true with applied:false (no commit was amended).
const COMMENT_REPLY_SCHEMA = {
  type: 'object',
  required: ['ok', 'summary'],
  properties: {
    ok: { type: 'boolean' },
    applied: { type: 'boolean' },
    error: { type: 'string' },
    prUrl: { type: 'string' },
    summary: { type: 'string' },
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
  const res = { ticketId: t.id, action: decision.action, summary: note }
  // RUS-83: surface the resolver's terminal give-up signal on the skip record. A
  // cap-reached red frontier resolves to `wait` with ciGaveUp=True (auto-revising gave
  // up; parked for manual diagnosis) — carry it through so the wait record / per-ticket
  // log is not silent about a PR that the loop stopped auto-fixing (Risk Register row 4).
  if (decision && decision.ciGaveUp) res.ciGaveUp = true
  return res
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

  python3 ${engineCmd('scripts/qrspi_persist.py')} --ticket ${id} --artifact ${name}

It moves the staged artifact into the ticket's worktree at the canonical path (which it
self-locates) and prints JSON { ok, dest, bytes, error? }. Parse that JSON and return it
verbatim. If it reports ok:false, return that as-is — HARD STOP, do NOT retry, do NOT
improvise alternative commands or paths.`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA }
  )
}

// Run one phase agent, then deterministically persist its staged artifact. Reuses an
// existing non-empty canonical artifact (resume). Returns true on success, false on
// failure/skip. The phase persists ungated — the autonomous batch runs no critics or
// node-checks (the design panel, N-select, coherence pass, and research citation check
// were all removed; the on-demand /review-* family is the surviving review path).
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
  // so qrspi_resolve.py emits this PATH (ticketContentPath) — never the body — and the
  // design agents Read it file->file. The fragile ticket text (Linear <issue> mention
  // tags etc.) thus never round-trips through the worker's stdout echo, where a model
  // HTML-escapes `>`->`&gt;` and corrupts the JSON the orchestrator parses (RUS-69).
  const ticketFile = `/tmp/phase-stage/${t.id}/ticket.md`
  // NO schema: the worker returns the script's JSON stdout as plain text; we parse it
  // with parseResolveEnvelope() (Option A — the StructuredOutput tool path stalled the
  // weak local worker, which emitted empty {} and looped).
  const out = await agent(
    `You are the RESOLVE worker for QRSPI ticket ${t.id}. Your cwd is the main repo root.

Do EXACTLY these steps — no exploration, no path guessing, no extra commentary:

1. Fetch the ticket: mcp__linear__get_issue (identifier ${t.id}, includeRelations: true).
   Read three things and retry once on failure:
     a. its status name;
     b. whether it is assigned (assignee non-null);
     c. its blockedBy relations — the issues this ticket is BLOCKED BY. Look in the returned
        relations for entries whose type is "blocks" pointing AT this ticket (i.e. this ticket
        is the blocked side), commonly surfaced as a "blockedBy" list. For EACH such blocker
        you need its identifier (e.g. RUS-99) AND its status TYPE (the workflow-state category:
        one of backlog / unstarted / started / completed / canceled / triage — NOT the display
        name). If the includeRelations payload does NOT carry each blocker's status type
        inline, do a per-blocker follow-up mcp__linear__get_issue (identifier = that blocker)
        and read its status type from there. (RD1: one call vs per-blocker read — adapt to what
        the live payload actually exposes; do not assume.)

   Classify each blocker: it is CLOSED only if its status type is exactly "completed" or
   "canceled". Treat EVERY other type — backlog, unstarted, started, triage, or any
   unrecognized/unreadable value — as OPEN (RD3: fail toward blocking). Collect the identifiers
   of all OPEN blockers into an open-blocker list.

2. Stage the ticket text (so the resolver embeds it — you never hand-assemble JSON): run
   Bash \`mkdir -p /tmp/phase-stage/${t.id}\`, then use the Write tool to write the ticket's
   title, then a blank line, then its full description — verbatim — to this token-free path:
     ${ticketFile}

3. Run this ONE command verbatim from your cwd (worktree setup + OWNER/REPO + the tested
   PR-state gather + decision + artifact detection + ticketContentPath emission, all in a single
   deterministic step — do NOT hand-derive any of it, do NOT substitute paths):

     python3 ${engineCmd('scripts/qrspi_resolve.py')} --ticket ${t.id} --linear-status "<status>" --ticket-content-file ${ticketFile}

   Replace <status> with the Linear status name from step 1. If (and only if) step 1 found the
   ticket assigned, also append the flag  --assigned  to that command.

   Blocker flags (append ONLY on positive detection — fail-safe): if and ONLY if the
   open-blocker list from step 1 has at least one entry, also append  --blocked-open  and one
   --blocked-by <id>  per open blocker (e.g.  --blocked-open --blocked-by RUS-99 --blocked-by
   RUS-100 ). If the open-blocker list is empty — no blockedBy relations, all blockers
   completed/canceled, or the relations were absent/empty/unreadable — append NEITHER flag (the
   script then resolves to run_design). Never invent blocker ids; pass only ids you actually
   read.

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

  python3 ${engineCmd('scripts/qrspi_restack.py')} --ticket ${t.id}

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
// SYNC-TRUNK — never build a dependent ticket on a stale local main (RUS-74).
// Fetches origin and FF-advances local `main` to `origin/main` in the MAIN checkout,
// failing loud on a non-`main` HEAD, divergence, a dirty tree, or a fetch failure.
// Called at run start (before any worktree is cut) and after every successful land,
// so a dependent ticket's worktree is always cut from a current trunk. The helper
// self-locates REPO_ROOT (resolves the MAIN checkout even when invoked from a worktree),
// takes no meaningful argv, and prints the SyncEnvelope { ok, repoRoot, updated, from,
// to, error? } on stdout (exit 0 when ok else 1). A non-ok envelope is FATAL: callers
// `throw` to abort the whole run rather than skip a ticket. Mirrors the restack-worker
// invocation shape (engineCmd + verbatim run + parse).
// ===========================================================================
async function syncTrunk(phaseLabel) {
  const out = await agent(
    `You are the TRUNK-SYNC worker for qrspi-batch. Your cwd is the main repo root.
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives,
no other git/gt commands:

  python3 ${engineCmd('scripts/qrspi_sync_trunk.py')}

It fetches origin and fast-forward-advances local \`main\` to \`origin/main\` in the main
checkout (self-locating; takes no arguments), and prints a JSON envelope
{ ok, repoRoot, updated, from, to, error? }. Output that JSON as your FINAL message,
exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT call any
structured-output tool. If it printed ok:false, still output that JSON verbatim (HARD
STOP — do NOT retry, do NOT run git fetch/merge/reset yourself or improvise paths).`,
    { label: 'sync-trunk', phase: phaseLabel }
  )
  const sy = parseSyncTrunkEnvelope(out)
  if (!sy.ok) log(`  trunk-sync FAILED — ${sy.error ?? 'unknown'}`)
  else if (sy.updated) log(`  trunk-sync: local main FF-advanced ${sy.from} → ${sy.to}`)
  else log(`  trunk-sync: local main already current (${sy.to})`)
  return sy
}

// ===========================================================================
// ACTION: run_design  (questions → research → design, then submit Design PR)
// ===========================================================================
async function doDesign(t, r) {
  const wd = r.worktreeDir
  phase('Design')

  // The autonomous batch runs no phase critics or node-checks; each phase persists ungated.
  if (!await runPhase('questions', 'qrspi-questions',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

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
TICKET_CONTENT_PATH = ${r.ticketContentPath}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design')) return failTicket(t)

  phase('Finalize')
  const fin = await agent(
    `${provisionStep(r, t)}You are the DESIGN-PHASE finalize worker for ${t.id}, in ${wd}. Follow the "action: run_design" commit+submit steps of ${SKILL}.
1. Verify questions.md, research.md, design.md exist and are non-empty under ${wd}/.qrspi/${t.id}/. If any missing/empty, return ok:false (do NOT commit/transition).
2. Stage ONLY those three artifacts; add them as the single commit (subject "${t.id} [QR]: Design — ${t.title}") on the pre-created ${t.id}/design branch with \`gt modify -c\` (the branch already exists from worktree setup — do NOT use \`gt create\`). Then submit the Design PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`${reviewerFlags(r) ? ' (the reviewer flag is required — it is what surfaces the PR in the reviewer\'s Graphite queue; submit it EXACTLY as written, do not drop or alter the reviewer)' : ''} (handle a stale closed-PR association per the SKILL "Resubmitting" steps).
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
    `${provisionStep(r, t)}You are the PLAN-PHASE finalize worker for ${t.id}, in ${wd}. Follow the "action: advance → nextPhase == plan" steps of ${SKILL}.
1. Verify structure.md, plan.md, worktree.md exist and are non-empty under ${wd}/.qrspi/${t.id}/. If any missing/empty, return ok:false.
2. gt checkout ${t.id}/design; stage ONLY those three artifacts; create the ${t.id}/plan branch STACKED on ${t.id}/design with \`gt create\` (single commit "${t.id} [SP]: Plan — ${t.title}"). Then submit the Plan PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`${reviewerFlags(r) ? ' (submit the reviewer flag EXACTLY as written — it is what surfaces the PR in the reviewer\'s Graphite queue)' : ''}.
3. BEST-EFFORT project Linear → "Plan Review" (WARN on failure, still ok:true if the PR was created).
Return: ok, prUrl, newStatus, summary.`,
    { label: `finalize-plan:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const out = finResult(t, fin, 'advance:plan')
  return out
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
    `${provisionStep(r, t)}You are the implementation finalize worker for ${t.id}, in ${wd}. Follow the SKILL "advance → implementation" submit steps. PR bodies are seeded at Graphite CREATION from the commit message (\`gt submit\` has no body flag and seeds the body at creation only), so author the body via the commit message as below — this is the deterministic default. A post-hoc body correction, if ever needed, uses \`gh api repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@<file>\` (NOT \`gh pr edit\`, which can abort on the Projects-classic GraphQL bug). Do:
1. Amend pr-summary.md into the last slice commit as the durable artifact (git add .qrspi/${t.id}/pr-summary.md && gt modify --no-interactive).
2. Splice pr-summary.md into the SLICE-1 commit MESSAGE (so the slice-1 PR body is the full summary at creation), BEFORE submitting, by running EXACTLY this one self-locating command verbatim — no path edits, no alternatives:
     python3 ${engineCmdFor(r, 'scripts/qrspi_pr_body.py')} --ticket ${t.id} --slice 1
   It preserves the slice-1 subject+trailer, splices the summary in between, amends via \`gt modify\` (auto-restacking the slices above), and prints JSON { ok, branch, subject, bytes, error? }. If it prints ok:false, return ok:false — HARD STOP: surface the splice failure honestly, do NOT paper over it (no gt body flag exists; do not substitute a gh body write to mask a failed splice).
3. Submit the entire stack PUBLISHED with Graphite (bodies already live in the commit messages, so --no-edit keeps them; slices 2..N carry their focused "Part N/total" body): \`gt submit --publish --stack${reviewerFlags(r)} --no-edit --no-interactive\`${reviewerFlags(r) ? ' (submit the reviewer flag EXACTLY as written — it surfaces the PRs in the reviewer\'s Graphite queue)' : ''}. The bodies are already seeded from the commit messages, so no gh body edit is needed here.
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
    `${provisionStep(r, t)}You are the submit worker for ${t.id} (active phase: ${r.decision.phase}), in ${r.worktreeDir}. Follow the "action: submit" steps of ${SKILL}: the phase branch exists but its PR was not opened. Verify the phase's artifacts are present+non-empty (if any are missing AND cannot be produced, return ok:false — never fabricate). This path CREATES the PR, and PR bodies are seeded at Graphite creation from the commit message (\`gt submit\` has no body flag and seeds the body at creation only) — the deterministic default; a post-hoc body correction, if needed, is \`gh api … pulls/<N> -X PATCH -F body=@<file>\`, not \`gh pr edit\`. If the active phase is IMPLEMENTATION, FIRST splice pr-summary.md into the slice-1 commit message by running EXACTLY, verbatim: \`python3 ${engineCmdFor(r, 'scripts/qrspi_pr_body.py')} --ticket ${t.id} --slice 1\` (if it prints ok:false, return ok:false — HARD STOP). Then submit the PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)} --no-edit --no-interactive\` (add --stack for implementation)${reviewerFlags(r) ? ' — submit the reviewer flag EXACTLY as written, it surfaces the PR in the reviewer\'s Graphite queue' : ''} and BEST-EFFORT project the matching Linear review status. (The body is seeded from the commit message at creation — no gh body edit is needed here.)
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
    `${provisionStep(r, t)}You are the RESET worker for ${t.id}, in ${r.worktreeDir}. A formal CHANGES_REQUESTED landed on the ${d.resetToPhase} PR, so discard the downstream phases [${(d.discardPhases || []).join(', ')}] AUTOMATICALLY per the "action: reset" steps of ${SKILL}:
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
// ACTION: revise  (UNIFIED feedback handler — subsumes the former respond_comment)
// ===========================================================================
// AUTONOMOUS. The resolver emits `revise` when a frontier phase PR carries a formal
// CHANGES_REQUESTED AND/OR >=1 unaddressed reviewer comment AND/OR a RED CI rollup on the
// frontier (RUS-81, under the configurable cap). The decision carries:
//   - r.commentTargets    the unaddressed reviewer comments to evaluate per-intent
//   - r.decision.changeRequested  whether a formal change request is present
//   - r.decision.ciFailing / r.ciFailing  whether the frontier CI is RED (a CI-driven revise)
//   - r.ciFailingChecks   the failing-check {name, detailsUrl} entries (RUS-81), [] otherwise
//   - r.ciRedBranches     the deterministic, ascending list of red branches to bump this
//                         pass (RUS-83) — each red slice for implementation, the single
//                         phase branch for a red design/plan frontier, [] for non-CI
// The worker runs coherent steps within ONE pass (this is the unification — comment AND CI
// handling no longer slip to separate later runs):
//   1. PER-COMMENT INTENT ENGINE — for each commentTarget, an honest peer-reviewer worker
//      ANSWERs / APPLYs (edit + amend in place) / DECLINEs, and posts an in-thread reply.
//   2. FORMAL CHANGE REQUEST and/or CI FAILURE — a worker addresses any remaining
//      change-request feedback (e.g. the review SUMMARY body, which is not a reply-able
//      thread comment) AND, when `ciFailing`, reads the REAL failing-check output before any
//      fix (honesty-bound), fixes ALL red slice PRs in one pass (OQ3), amends via
//      qrspi_revise_amend.py, then ALWAYS re-requests review. The worker NEVER touches the
//      `CI-Revise-Attempt` counter (RUS-83): the orchestrator owns it — after the worker
//      returns, doRevise itself advances it via the deterministic helper qrspi_ci_revise_bump.py
//      on the CI-failure path (once per still-red branch in r.ciRedBranches) and resets it to 0
//      via resetCiReviseTrailer on the non-CI path. Re-requesting flips reviewDecision back to
//      REVIEW_REQUIRED — the loop-safe termination signal that lets the next pass return `wait`.
// A comment-only PR (no formal change request, even when APPROVED) runs step 1 only and does
// NOT re-request review — replies are the whole job; the approved PR is left undisturbed.
// Thread RESOLUTION is always left to the reviewer (only they can mark a thread resolved); a
// thread the reviewer already resolved is excluded upstream (the gather drops resolved
// threads from commentTargets), so the worker never replies into an already-resolved thread.
async function doRevise(t, r) {
  phase('Finalize')
  const d = r.decision
  const targets = Array.isArray(r.commentTargets) ? r.commentTargets : []
  const changeRequested = !!(d && d.changeRequested)
  // RUS-81: the frontier CI is RED (under the cap) — the resolver folded ciFailing into the
  // decision and the envelope re-emitted it + the failing checks at top level. doRevise reads
  // r.ciFailing / r.ciFailingChecks directly (NOT decision.ciFailingChecks — the checks live
  // only at envelope top level per the re-emit contract).
  const ciFailing = !!(r.ciFailing || (d && d.ciFailing))
  const ciFailingChecks = Array.isArray(r.ciFailingChecks) ? r.ciFailingChecks : []

  if (!changeRequested && targets.length === 0 && !ciFailing) {
    // The resolver only emits revise with a change request, comment targets, and/or a red
    // frontier CI, so this is a defensive guard, not an expected path.
    return skip(t, d, 'revise with neither a change request, comment targets, nor a CI failure; nothing to do.')
  }

  // --- Step 1: per-comment intent engine (answer / apply+amend / decline + in-thread reply).
  let answered = []
  let failures = []
  if (targets.length) {
    log(`  ${t.id}: evaluating ${targets.length} reviewer comment(s) on the ${d.phase} PR`)
    const res = await respondToComments(t, r, d, targets)
    answered = res.answered
    failures = res.failures
  }
  const commentSummary = targets.length
    ? `evaluated ${answered.length}/${targets.length} reviewer comment(s)`
      + `${answered.some(a => a.applied) ? ` (${answered.filter(a => a.applied).length} applied as changes)` : ''}`
      + `${failures.length ? `, ${failures.length} failed` : ''}`
    : ''

  // --- Step 2a: comment-only path (no formal change request AND no CI failure) — replies are
  // the whole job. Do NOT re-request review: the PR may be APPROVED, and we must not disturb it.
  // (A red CI on a comment-only PR still falls through to step 2b — CI must be fixed and review
  // re-requested even with no formal change request.)
  if (!changeRequested && !ciFailing) {
    // RUS-81 writer-side reset: a comment APPLY amends the phase commit via qrspi_revise_amend.py,
    // which preserves the message verbatim — so a stale CI-Revise-Attempt trailer (left by a prior
    // CI-failure revise) would survive this NON-CI amend. Per the path-dependent trailer contract,
    // EVERY non-CI amend overwrites the trailer to 0. Only needed when a comment was actually
    // applied (an amend happened); pure ANSWER/DECLINE replies touch no commit. (The gather already
    // forces the EFFECTIVE count to 0 whenever ciState != "red", so this is durability/observability
    // hygiene on the committed head, not a correctness gate for the cap.)
    if (answered.some(a => a.applied)) {
      await resetCiReviseTrailer(t, r, d, answered)
    }
    const summary = `Responded to ${answered.length}/${targets.length} reviewer comment(s) on the ${d.phase} PR`
      + `${answered.some(a => a.applied) ? ` (${answered.filter(a => a.applied).length} applied as changes)` : ''}`
      + `${failures.length ? `; ${failures.length} failed` : ''}.`
    return { ticketId: t.id, action: 'revise', summary, prUrl: undefined }
  }

  // --- Step 2b: formal change request and/or CI failure — address the review summary /
  // remaining feedback AND (when ciFailing) read the real failing-check output, fix every red
  // slice, amend, then ALWAYS re-request review. The worker no longer writes the
  // CI-Revise-Attempt counter (RUS-83); doRevise advances/resets it AFTER the worker returns
  // (bumpCiReviseTrailers on the CI path; resetCiReviseTrailer on the green-CI change-request path).
  // The opening line is path-aware: it is NOT always a change request (a red frontier CI on an
  // otherwise-clean PR also reaches here).
  const trigger = changeRequested && ciFailing
    ? `A formal CHANGES_REQUESTED landed on the ${d.phase} PR AND its CI checks are RED.`
    : changeRequested
      ? `A formal CHANGES_REQUESTED landed on the ${d.phase} PR.`
      : `The ${d.phase} PR's CI checks are RED (no formal change request).`
  // The failing checks the gather surfaced (name + detailsUrl). The worker reads the REAL log
  // output before any fix — honesty-bound. Empty unless ciFailing.
  const checksBlock = ciFailing
    ? ciFailingChecks.length
      ? ciFailingChecks.map((c, i) => `   ${i + 1}. ${c && c.name ? c.name : '(unnamed check)'}${c && c.detailsUrl ? ` — ${c.detailsUrl}` : ''}`).join('\n')
      : '   (the gather reported a red rollup but no per-check detail; discover the failing checks yourself via `gh pr checks` / `gh pr view --json statusCheckRollup`)'
    : ''
  const fin = await agent(
    `${provisionStep(r, t)}You are the REVISE worker for ${t.id} (frontier phase: ${d.phase}), in ${r.worktreeDir}. ${trigger} ${targets.length ? `The reviewer's INLINE/TOP-LEVEL comments have ALREADY been engaged and replied to in a prior step — do NOT re-reply to them; focus on the review SUMMARY body and any change-request feedback not tied to a specific comment.` : ''} Address it AUTONOMOUSLY, following the "action: revise" steps of ${SKILL}, with these REQUIRED adaptations:
- DO NOT attempt to RESOLVE review threads (only the reviewer can mark a thread resolved). Reading feedback via \`gh pr view\`/\`gh api graphql\` queries is fine. Thread resolution is the reviewer's job — leave threads as-is.
- Stay WITHIN the ${d.phase} phase only — never edit a downstream phase's artifacts (that is \`reset\`, not revise).
- You are HONESTY-BOUND: never fabricate a fix, a log line, or a green result. Every fix must address a REAL failure you actually read.
Steps:
1. Identify the branch(es) to fix. For design/plan: \`gt checkout ${t.id}/${d.phase} --no-interactive\`. For implementation: query the ticket's slice PRs (\`gh pr list --head ${t.id}/slice-... \` or graphql) and address EVERY slice whose PR is CHANGES_REQUESTED${ciFailing ? ' OR whose CI is RED' : ''}, lowest slice number first (changes restack upward).${ciFailing ? `
2. DIAGNOSE CI (CI is RED — do this BEFORE any code edit; honesty-bound, read the REAL failing output). The gather reported these failing check(s):
${checksBlock}
   For each failing check, read its ACTUAL failure output with a READ-only query before fixing — e.g. \`gh pr checks <PR_NUMBER>\` to list checks + their run URLs, then \`gh run view <run-id> --log-failed\` (derive <run-id> from the check's detailsUrl / the \`gh pr checks\` run link), or open the detailsUrl. Do NOT guess the failure — base every fix on the log you read. For implementation, repeat for EVERY red slice PR (fix ALL red slices in this one invocation), lowest slice number first.` : ''}
${ciFailing ? '3' : '2'}. Read any change request: the CHANGES_REQUESTED review SUMMARY body AND any unresolved thread comments not already addressed (READ-only queries per the SKILL).${changeRequested ? '' : ' (There is no formal change request on this PR — there may be nothing here; the trigger is the red CI.)'}
${ciFailing ? '4' : '3'}. Fix the REAL problems by editing the phase's artifacts/code in ${r.worktreeDir}: the CI failure(s) you diagnosed${changeRequested ? ' and any remaining change-request feedback' : ''}. If the prior per-comment step already applied every needed change${ciFailing ? ' AND CI requires no further edit' : ''} and NOTHING further remains, do NOT invent an edit — skip to the re-request step.
${ciFailing ? '5' : '4'}. When you made edits, stage them AND amend the phase commit IN PLACE by running EXACTLY this one self-locating command verbatim (no path edits, no alternatives) — for design/plan run it once; for implementation run it once per affected slice branch, lowest slice number first:
   \`python3 ${engineCmdFor(r, 'scripts/qrspi_revise_amend.py')} --ticket ${t.id} --branch <BRANCH>\` where <BRANCH> = \`${t.id}/${d.phase}\` for design/plan, or \`${t.id}/slice-<N>\` for an implementation slice.
   The script checks out the branch, stages every edit you made (excluding caches), amends the commit with \`gt modify\` keeping its EXACT subject+trailers (it does NOT rename the subject), and VERIFIES the amend captured your changes — it FAILS if nothing was staged or the tree is left dirty. It prints JSON { ok, branch, oldOid, newOid, dirty, error? }. If ANY invocation prints ok:false, return ok:false — HARD STOP; do NOT hand-run \`gt modify\`/\`git add\`/\`git commit\`/\`git reset\` to work around it. Never run a bare \`gt modify --no-interactive\` here: without staging it amends an empty index and silently drops your edits. (If the prior step determined nothing further needs changing, SKIP the content amend — do not run the amend script with no staged edits.)
${ciFailing ? '6' : '5'}. Re-request review so any stale CHANGES_REQUESTED is cleared and the re-pushed head (with your fixes) re-enters review (ALWAYS do this, whether or not you amended content): \`gt submit --publish --no-edit --rerequest-review${reviewerFlags(r)}${d.phase === 'implementation' ? ' --stack' : ''} --no-interactive\`. (This pushes the new head to the PR. No gh body edit is involved here.) Do NOT touch the \`CI-Revise-Attempt\` trailer — the orchestrator owns that counter (it bumps it on the CI path via the deterministic helper and resets it on the non-CI path); you never write it.
${ciFailing ? '7' : '6'}. BEST-EFFORT keep Linear in the current review status (a failed Linear write is a WARN, still return ok:true if review was re-requested).
Return: ok, prUrl, newStatus, summary (name what you fixed${ciFailing ? ' — including the real CI failure(s) you read' : ''} — or state that the prior comment replies covered it and you only re-requested review — and confirm review was re-requested; if you could not address the failure/feedback, return ok:false with the verbatim reason — never fabricate a fix).`,
    { label: `revise:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const out = finResult(t, fin, `revise:${d.phase}`)
  if (out && commentSummary) {
    out.summary = `${out.summary || ''} Also ${commentSummary}.`.trim()
  }

  // --- RUS-83 path-dependent counter writes (orchestrator-owned; the worker no longer
  // touches the trailer). Exactly one writer per path: bump on the CI path, reset on the
  // non-CI path. These run AFTER the content worker returns, regardless of its `ok`.
  if (ciFailing) {
    // CI path: advance the CI-Revise-Attempt counter by 1 on EVERY still-red branch
    // (r.ciRedBranches), UNCONDITIONALLY — even when the worker reported failure / pushed no
    // content amend — so an unfixable red PR still marches toward the cap (AC1/AC6). This
    // fires for both the combined (changeRequested && ciFailing) and the pure-CI revise; do
    // NOT gate it on !changeRequested. A helper non-zero exit is a HARD failure surfaced on
    // the result (OQ1): a count that could not advance is never silent.
    const bump = await bumpCiReviseTrailers(t, r, d)
    if (out && !bump.ok) {
      const branches = bump.failures.map(f => f.branch).join(', ')
      out.ciReviseBumpFailed = true
      out.summary = `${out.summary || ''} CI-Revise-Attempt counter FAILED to advance on: ${branches} — the consecutive-red cap cannot make progress until this is resolved.`.trim()
    }
  } else if (changeRequested) {
    // Non-CI path (green-CI change request): re-home the reset the deleted worker step-6 used
    // to own. Call resetCiReviseTrailer UNCONDITIONALLY — it is idempotent (no-ops when the
    // trailer is absent or already 0), so no "did the worker amend?" detection is needed —
    // preserving the CLAUDE.md invariant "every non-CI amend overwrites the trailer to 0".
    await resetCiReviseTrailer(t, r, d, answered)
  }

  // --- RUS-83: surface ciGaveUp on the revise result for operator visibility. A revise
  // decision never carries ciGaveUp=True (give-up resolves to `wait`, not `revise`), but
  // we pass it through verbatim from the resolver so the field is uniform across records.
  if (out && d && d.ciGaveUp) out.ciGaveUp = true
  return out
}

// ---------------------------------------------------------------------------
// HELPER: respondToComments — the per-comment intent engine (RUS-54), invoked by the
// unified doRevise for both the comment-only and change-request paths.
// ---------------------------------------------------------------------------
// Iterates the unaddressed reviewer comments (comment-keyed multiplicity) and spawns one
// peer-reviewer worker PER comment. Each worker engages the comment honestly (AC2–AC4):
//   - ANSWER faithfully from the actual artifacts/code/PR state (honesty-bound — never
//     fabricate a fact or a fix), OR
//   - APPLY a sound suggested change, amend the phase commit in place via the same
//     self-locating qrspi_revise_amend.py mechanism the change-request path uses, and say
//     so, OR
//   - DECLINE with a concrete rationale.
// The rationale/answer lands ONLY in the in-thread reply (RQ5 — no artifact/impl-log
// duplication). The reply itself is posted by the tested, self-locating
// scripts/qrspi_comment_reply.py (inline → threaded review-comment reply; toplevel → a
// fresh PR comment), whose write SUCCEEDS on this repo with the bot's classic PAT (the old
// cross-account 403 is history — see the gh-cross-account note). Idempotency is structural:
// once a bot reply is observed in the thread (or a newer bot top-level comment exists), the
// gather's unaddressed_reviewer_comments no longer returns that target, so a second pass does
// NOT re-respond — we rely on that, never on local state. Returns { answered, failures }.
async function respondToComments(t, r, d, targets) {
  const answered = []
  const failures = []
  // One peer-reviewer worker per comment (comment-keyed multiplicity). Sequential:
  // tickets share one .git index, and an apply+amend on the phase branch must not race.
  for (let i = 0; i < targets.length; i++) {
    const ct = targets[i]
    // Token-free staging path for THIS comment's reply body (no "qrspi" token — the weak
    // local worker reproduces it intact; the comment-reply script reads it via --body-file
    // so the worker never quotes arbitrary markdown on a command line).
    const bodyFile = `/tmp/phase-stage/${t.id}/comment-reply-${i}.md`
    const fin = await agent(
      `${provisionStep(r, t)}You are the PEER-REVIEWER worker for ${t.id} (phase: ${d.phase}), in ${r.worktreeDir}. A reviewer left a comment on the ${d.phase} PR and the bot has NOT yet replied to it. Engage it as an honest peer reviewer — you may ANSWER it, APPLY a sound suggested change, or DECLINE it with a concrete rationale. You are HONESTY-BOUND: never fabricate a fact, a fix, or agreement; answer only from the actual artifacts/code/PR state.

The comment you are addressing:
- commentId: ${ct.commentId}
- author: ${ct.author}
- threadType: ${ct.threadType}    (inline = a review-thread line comment; toplevel = an issue-style PR comment)
- body:
"""
${ct.body == null ? '' : ct.body}
"""

Steps (do EXACTLY these; no extra git/gh mutations beyond the two self-locating scripts named below):
1. Resolve the ${d.phase} PR number for this ticket with a READ-only query, e.g.:
     gh pr list --head ${d.phase === 'implementation' ? `'${t.id}/slice-*'` : `${t.id}/${d.phase}`} --state open --json number,headRefName --jq '.[0].number'
   (For implementation, pick the slice PR the comment belongs to.) Reading PR/thread state via gh is fine.
2. Decide your response to the comment, choosing exactly ONE:
   (a) ANSWER — the comment is a question or concern you can address from the real state. Write a faithful answer.
   (b) APPLY — the comment requests a concrete, sound change WITHIN the ${d.phase} phase only (never edit a downstream phase — that is reset/revise, not this). Make the edit in ${r.worktreeDir}, then stage+amend the phase commit IN PLACE by running EXACTLY this one self-locating command verbatim (no path edits, no alternatives):
         python3 ${engineCmdFor(r, 'scripts/qrspi_revise_amend.py')} --ticket ${t.id} --branch ${d.phase === 'implementation' ? '<the affected slice branch, e.g. ' + t.id + '/slice-<N>>' : `${t.id}/${d.phase}`}
       It checks out the branch, stages your edits (excluding caches), amends with \`gt modify\` keeping the EXACT subject+trailers, and VERIFIES the amend captured a real change (it FAILS if nothing was staged or the tree is left dirty), printing JSON { ok, branch, oldOid, newOid, dirty, error? }. If it prints ok:false, do NOT hand-run git/gt to work around it — fall back to ANSWER or DECLINE and say so honestly. After a successful amend, re-publish the (re)stacked branch so the PR reflects the change: \`gt submit --publish --no-edit${d.phase === 'implementation' ? ' --stack' : ''} --no-interactive\`${reviewerFlags(r) ? ' ' + reviewerFlags(r).trim() : ''}.
   (c) DECLINE — the suggestion is wrong, out of scope, or unsound. Give a concrete, respectful rationale grounded in the actual state.
3. Write your in-thread reply text — your answer/what-you-applied/your-decline-rationale, and NOTHING duplicated into artifacts or the impl-log (the reply is the only place the rationale lives). Use the Write tool to write it verbatim to this token-free file:
     ${bodyFile}
4. Post the reply by running EXACTLY this one self-locating command verbatim (no path edits, no alternatives), choosing --reply-mode = the comment's threadType (${ct.threadType}):
     python3 ${engineCmdFor(r, 'scripts/qrspi_comment_reply.py')} --ticket ${t.id} --pr <PR_NUMBER> --comment-id ${ct.commentId} --reply-mode ${ct.threadType} --body-file ${bodyFile}
   It self-locates owner/repo and prints a ReplyEnvelope JSON { ok, replyId, inReplyToId, error? }. Read ok off its STDOUT (do NOT infer success from exit code alone). If it prints ok:false, return ok:false with the verbatim error — do NOT retry or improvise an alternative mutation (a genuine write failure here means the comment reply cannot be relied on; report it honestly so the wait sink stays correct).
Return: ok (true only if the reply posted), applied (true ONLY if you chose APPLY and the amend+publish succeeded), prUrl (the PR url if known, else ""), summary (1-2 sentences naming the comment and how you engaged it).`,
      { label: `respond-comment:${t.id}#${i}`, phase: 'Finalize', schema: COMMENT_REPLY_SCHEMA }
    )
    if (!fin || !fin.ok) {
      log(`  ${t.id}: comment ${ct.commentId} reply FAILED — ${fin?.error ?? 'no result'}`)
      failures.push({ commentId: ct.commentId, error: fin?.error ?? 'unknown' })
      continue
    }
    log(`  ${t.id}: comment ${ct.commentId} → ${fin.applied ? 'applied+replied' : 'replied'} (${String(fin.summary ?? '').slice(0, 60)})`)
    answered.push({ commentId: ct.commentId, applied: !!fin.applied, summary: fin.summary })
  }

  return { answered, failures }
}

// ---------------------------------------------------------------------------
// HELPER: resetCiReviseTrailer — writer-side reset of the CI-Revise-Attempt trailer to 0
// after a NON-CI amend (RUS-81). The comment-only APPLY path amends the phase commit via
// qrspi_revise_amend.py, which preserves the message verbatim — so a stale CI-Revise-Attempt
// trailer (from a prior CI-failure revise) survives. Per the path-dependent trailer contract,
// EVERY non-CI amend overwrites the trailer to 0. This spawns one worker to rewrite the head
// commit message of each amended branch, setting exactly one `CI-Revise-Attempt: 0` trailer
// and preserving the subject + every other trailer byte-for-byte, then re-publishing.
// Best-effort: a failure here does NOT fail the revise (the gather's read-side reset already
// forces the EFFECTIVE count to 0 while CI is not red; this only keeps the committed head tidy).
// ---------------------------------------------------------------------------
async function resetCiReviseTrailer(t, r, d, answered) {
  const branchHint = d.phase === 'implementation'
    ? `the slice branch(es) you amended (e.g. ${t.id}/slice-<N>) — reset EACH one you touched`
    : `${t.id}/${d.phase}`
  const fin = await agent(
    `${provisionStep(r, t)}You are the CI-TRAILER-RESET worker for ${t.id} (phase: ${d.phase}), in ${r.worktreeDir}. A prior step APPLIED reviewer-comment change(s) and amended the phase commit; this was a NON-CI amend, so the durable \`CI-Revise-Attempt\` counter (RUS-81) on the amended head commit(s) must be overwritten to 0. You are HONESTY-BOUND: change ONLY the trailer value; never touch any file or any other line of the message.
For EACH branch that was amended (${branchHint}) — checkout the branch first (\`gt checkout <branch> --no-interactive\`):
1. Read the head commit's FULL message verbatim: \`git log -1 --format=%B\` (subject + body + ALL trailers).
2. If there is NO \`CI-Revise-Attempt:\` line, there is nothing to reset — skip this branch (do NOT add one; absent already means 0).
3. If a \`CI-Revise-Attempt: N\` line is present and N is already 0, skip (no-op).
4. Otherwise rewrite the message with EXACTLY one \`CI-Revise-Attempt: 0\` line — replace the existing value in place. Preserve the subject and EVERY other line/trailer byte-for-byte; change ONLY that value. Apply it as a message-only amend (NO file changes — there is nothing to stage, so a bare \`gt modify\` is correct here): \`gt modify --no-interactive -m "<the full rewritten message>"\`. Confirm with \`git log -1 --format=%B\`.
5. Re-publish the (re)stacked branch so the PR head carries the reset trailer: \`gt submit --publish --no-edit${d.phase === 'implementation' ? ' --stack' : ''} --no-interactive\`. Do NOT --rerequest-review here (this is a comment-only path; we must not disturb an approved PR's review state).
Return: ok, summary (which branch(es) you reset, or that no trailer was present to reset). If you cannot complete it, return ok:false with the verbatim reason — never fabricate.`,
    { label: `ci-trailer-reset:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  if (!fin || !fin.ok) {
    log(`  ${t.id}: CI-Revise-Attempt trailer reset (comment-only amend) WARN — ${fin?.error ?? 'no result'} (effective count is already 0 via the gather's read-side reset)`)
  }
  return fin
}

// The JSON the deterministic increment helper qrspi_ci_revise_bump.py prints to stdout:
// { ok, branch, prior, new, error? }. The thin bump worker reads it off the script's
// STDOUT (NOT exit code alone) and returns it verbatim.
const CI_REVISE_BUMP_SCHEMA = {
  type: 'object',
  required: ['ok', 'branch'],
  properties: {
    ok: { type: 'boolean' },
    branch: { type: 'string' },
    prior: { type: 'number' },
    new: { type: 'number' },
    error: { type: 'string' },
  },
}

// ---------------------------------------------------------------------------
// HELPER: bumpCiReviseTrailers — orchestrator-owned advance of the CI-Revise-Attempt
// counter on the CI-FAILURE path (RUS-83). Replaces the deleted worker step-6 CI +1.
// ---------------------------------------------------------------------------
// The resolver pre-aggregates the EXACT red branches to bump into r.ciRedBranches (each
// red slice branch for implementation, ascending; the single phase branch for a red
// design/plan frontier), so the JS never re-derives per-slice CI nor delegates "which
// slices are red" to an LLM worker. For EACH such branch we spawn a thin worker that runs
// the one verbatim, self-locating `qrspi_ci_revise_bump.py --ticket --branch [--stack]`
// command (the sole increment authority: pure trailer rewrite + gt modify -m + gt submit
// publish + verify, fail-closed). The bump fires UNCONDITIONALLY after the content worker
// returns whenever ciFailing is true — regardless of the worker's ok and regardless of
// changeRequested — so a still-red pass that pushed no content amend STILL advances the
// counter toward the cap (the AC1/AC6 guarantee). A non-zero helper exit / ok:false is a
// HARD failure surfaced to the caller (OQ1): a count that could not advance is never silent.
// Returns { ok, bumped: [{branch, prior, new}], failures: [{branch, error}] }.
async function bumpCiReviseTrailers(t, r, d) {
  const branches = Array.isArray(r.ciRedBranches) ? r.ciRedBranches : []
  const stackFlag = d.phase === 'implementation' ? ' --stack' : ''
  const bumped = []
  const failures = []
  // Lowest-first (r.ciRedBranches is already ascending). Sequential: tickets share one
  // .git index and a gt modify/submit on a stacked branch must not race a sibling.
  for (const branch of branches) {
    const fin = await agent(
      `${provisionStep(r, t)}You are the CI-REVISE-BUMP worker for ${t.id} (phase: ${d.phase}), in ${r.worktreeDir}. The frontier CI is RED; the orchestrator owns the durable \`CI-Revise-Attempt\` counter (RUS-83) and advances it deterministically. Run EXACTLY this one self-locating command verbatim — no path edits, no alternatives, no extra git/gt mutations:

  python3 ${engineCmdFor(r, 'scripts/qrspi_ci_revise_bump.py')} --ticket ${t.id} --branch ${branch}${stackFlag}

It checks out ${branch}, reads the head commit message, increments the \`CI-Revise-Attempt\` trailer by 1 (absent ⇒ 1), applies it as a message-only amend, re-publishes the branch, VERIFIES exactly one trailer at the new value, and prints JSON { ok, branch, prior, new, error? }. Parse that JSON off its STDOUT (do NOT infer success from the exit code alone) and return it verbatim. If it prints ok:false, return that as-is — HARD STOP; do NOT hand-run \`gt modify\`/\`git commit\` to work around it.`,
      { label: `ci-revise-bump:${t.id}:${branch}`, phase: 'Finalize', schema: CI_REVISE_BUMP_SCHEMA }
    )
    if (!fin || !fin.ok) {
      const error = fin?.error ?? 'no result'
      log(`  ${t.id}: CI-Revise-Attempt bump FAILED on ${branch} — ${error} (counter did not advance — surfacing as a hard failure)`)
      failures.push({ branch, error })
      continue
    }
    log(`  ${t.id}: CI-Revise-Attempt bumped on ${branch} (${fin.prior ?? '?'} → ${fin.new ?? '?'})`)
    bumped.push({ branch, prior: fin.prior, new: fin.new })
  }
  return { ok: failures.length === 0, bumped, failures }
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

  python3 ${engineCmd('scripts/qrspi_cleanup.py')} --ticket ${ticketId}${dryFlag}

It computes the cleanup verdict and (unless --dry-run) reaps the ticket's worktree, local branches, and remote refs, printing a JSON envelope { ok, repoRoot, decision, reason, removed{worktree,branches[],remotes[]}, dryRun, error? }. Output that JSON as your FINAL message, exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT call any structured-output tool. If it printed ok:false, still output that JSON verbatim (HARD STOP — do NOT retry or improvise).`,
    { label: `cleanup:${ticketId}`, phase: phaseLabel }
  )
  return parseCleanupEnvelope(out)
}

// ===========================================================================
// LAND VERIFY — independent Done gate (RUS-70). After the land worker reports a
// successful merge, do NOT trust its self-report: run the deterministic, self-locating
// qrspi_land_verify.py, which re-gathers each slice branch's MERGED state and returns a
// LandVerdict { status, openBranches }. Only `landed` (every slice MERGED) clears the
// Done projection; `incomplete` names the OPEN slice branches (the RUS-70 half-landed
// tip) and is deferred to the next batch pass rather than retried in-pass. Runs from the
// MAIN repo root, like the verifier's siblings (it self-locates REPO_ROOT from __file__).
// ===========================================================================
async function runLandVerify(ticketId, phaseLabel) {
  const out = await agent(
    `You are the LAND-VERIFY worker for QRSPI ticket ${ticketId}. Your cwd is the MAIN repo root (the script self-locates REPO_ROOT from its own path).
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives, no other git/gt/gh mutations:

  python3 ${engineCmd('scripts/qrspi_land_verify.py')} ${ticketId}

It gathers each slice branch's MERGED state and prints a LandVerdict JSON { status: "landed" | "incomplete", openBranches: [...] } (exit 0 on landed, non-zero on incomplete). Output that JSON as your FINAL message, exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT call any structured-output tool. If it exits non-zero, still output the verbatim JSON it printed (do NOT retry or improvise).`,
    { label: `land-verify:${ticketId}`, phase: phaseLabel }
  )
  return parseLandVerdict(out)
}

// ===========================================================================
// ACTION: land  (all PRs approved+clean — merge the stack bottom-up, finalize)
// ===========================================================================
async function doLand(t, r) {
  phase('Finalize')
  // 1. Merge the stack bottom-up + best-effort Linear → Done (the land worker; it no
  //    longer does worktree/branch cleanup — that is the deterministic script below).
  const fin = await agent(
    `${provisionStep(r, t)}You are the LAND worker for ${t.id}, in ${r.worktreeDir}. Every PR in the stack is approved+clean. Follow the "action: land" steps of ${SKILL}: ensure the stack is current (gt submit --publish --stack), merge bottom-up (gt merge --no-interactive — NOT --confirm, which forces a prompt --no-interactive cannot satisfy), then BEST-EFFORT project Linear → "Done". Do NOT remove the worktree, delete branches, or run \`gt sync --force\` — a separate deterministic cleanup step (qrspi_cleanup.py) handles all reaping AFTER the merge. Treat any infrastructure/merge error as a HARD STOP (return ok:false, and put the VERBATIM conflict/merge reason in the \`error\` field — NOT only in \`summary\`; the orchestrator surfaces \`error\` to the operator).
Return: ok, error (the verbatim reason on failure), prUrl, newStatus, summary.`,
    { label: `land:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const res = finResult(t, fin, 'land')
  // 2. Only reap if the merge actually succeeded — never destroy a worktree behind a
  //    failed/partial land (the idempotent cleanup script will reap on a later run once
  //    the stack truly merged). The script itself re-verifies full-merge state, so a
  //    transient land result that lost its merge verdict still can't cause a bad reap.
  if (!fin || !fin.ok) return res
  // 2a. Done GATE (RUS-70): the land worker self-reports ok on a single `gt merge`, which
  //     on an N>1 stack lands only the bottom slice + downstack and leaves the tip slices
  //     OPEN. Independently re-verify EVERY slice reached MERGED before projecting Done.
  //     `incomplete` ⇒ stop with ok:false, name the OPEN slices, and defer to the next
  //     batch pass (no in-pass retry, no cleanup — the half-landed stack is left intact).
  const verdict = await runLandVerify(t.id, 'Finalize')
  if (verdict.status !== 'landed') {
    log(`  ${t.id}: land INCOMPLETE — slice(s) [${verdict.openBranches.join(', ')}] still OPEN${verdict.error ? ` (${verdict.error})` : ''}; not Done, deferring to next pass (no cleanup)`)
    res.action = 'land'
    res.ok = false
    res.landed = false
    res.openBranches = verdict.openBranches
    res.summary = `land incomplete: slice(s) [${verdict.openBranches.join(', ')}] still OPEN — deferred to next pass`
    return res
  }
  res.landed = true
  // Post-land trunk sync (RUS-74, AC3): a successful land merged this stack into
  // origin/main, so local `main` is now behind. FF-advance it before the next ticket's
  // worktree is cut, so a sibling/dependent ticket later in this same run never builds on
  // the pre-land trunk. Same disposition as the run-start sync: a non-ok envelope is FATAL
  // (OQ3-RESOLVED) — throw to abort the run with the verbatim reason.
  const postLandSync = await syncTrunk('Finalize')
  if (!postLandSync.ok) {
    throw new Error(`post-land trunk sync failed for ${t.id} — ${postLandSync.error ?? 'unknown'}; aborting run (refusing to leave local main stale after a land)`)
  }
  const cl = await runCleanup(t.id, /* dryRun */ false, 'Finalize')
  const stranded = cleanupFailedRemotes(cl)
  if (!cl.ok) {
    // ok:false is the ONLY hard-stop (genuine infra error: gt/git/gh unreachable). The
    // worktree is left for a later reconciliation pass — unchanged HARD-STOP semantics.
    log(`  ${t.id}: cleanup failed after land — ${cl.error ?? 'unknown'} (worktree left for a later reconciliation pass)`)
  } else if (cl.decision === 'destroy') {
    log(`  ${t.id}: cleaned up — worktree ${cl.removed?.worktree ? 'removed' : 'absent'}, branches [${(cl.removed?.branches ?? []).join(', ')}], remotes [${(cl.removed?.remotes ?? []).join(', ')}]` +
        (stranded.length ? `, STRANDED remotes [${stranded.join(', ')}] (still on origin — scheduling Reconcile retry)` : ''))
  } else {
    log(`  ${t.id}: cleanup decision=${cl.decision} — ${cl.reason ?? ''} (no reap)`)
  }
  // RUS-68: a partial remote-prune failure (ok:true + non-empty failedRemotes) is RETRIABLE,
  // not terminal. Flag the ticket so the main loop does NOT exclude it from this run's
  // Reconcile pass (which re-attempts the prune via origin-driven discovery); the origin
  // refs persist, so a later run's Reconcile pass would re-pick it up regardless.
  res.cleanup = { decision: cl.decision, ok: cl.ok, removed: cl.removed, failedRemotes: stranded }
  if (cl.ok && stranded.length) res.reconcileRetry = true
  return res
}

// --- result helpers --------------------------------------------------------
function failTicket(t) {
  return { ticketId: t.id, action: 'failed', summary: 'A phase agent failed; ticket left untouched (no fabrication).' }
}
function finResult(t, fin, action) {
  if (!fin || !fin.ok) {
    log(`  ${t.id}: ${action} finalize failed — ${fin?.error ?? fin?.summary ?? 'no result'} (nothing advanced)`)
    return { ticketId: t.id, action, summary: `${action} finalize failed: ${fin?.error ?? fin?.summary ?? 'unknown'}` }
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
    const stranded = cleanupFailedRemotes(cl)
    if (!cl.ok) {
      // ok:false is the ONLY hard-stop (genuine infra error) — logged and skipped, pass continues.
      log(`  ${id}: reconcile cleanup failed — ${cl.error ?? 'unknown'} (skipped; pass continues)`)
      reaped.push({ ticketId: id, decision: cl.decision ?? 'skip', ok: false, dryRun: RECONCILE_DRY_RUN, error: cl.error })
      continue
    }
    if (cl.decision === 'destroy') {
      // RUS-68: surface still-present origin refs. A non-empty failedRemotes here means the
      // prune ran but origin still holds the refs — the next Reconcile pass re-attempts it
      // (the refs persist on origin), so it stays in the retriable backlog, not a hard stop.
      log(`  ${id}: ${RECONCILE_DRY_RUN ? 'WOULD reap' : 'reaped'} — worktree ${cl.removed?.worktree ? (RECONCILE_DRY_RUN ? 'present' : 'removed') : 'absent'}, branches [${(cl.removed?.branches ?? []).join(', ')}], remotes [${(cl.removed?.remotes ?? []).join(', ')}]` +
          (stranded.length ? `, STRANDED remotes [${stranded.join(', ')}] (still on origin — left for a later Reconcile retry)` : ''))
    } else if (cl.decision === 'blocked') {
      // A dirty worktree — logged and SKIPPED, never forced; the pass proceeds (OQ2).
      log(`  ${id}: BLOCKED — ${cl.reason ?? 'dirty worktree'} (left untouched for a human; pass continues)`)
    } else {
      log(`  ${id}: skip — ${cl.reason ?? 'not fully merged'} (in-flight; left untouched)`)
    }
    reaped.push({ ticketId: id, decision: cl.decision, ok: cl.ok, dryRun: RECONCILE_DRY_RUN, removed: cl.removed, failedRemotes: stranded })
  }
  return reaped
}

// ===========================================================================
// QUERY + DISPATCH
// ===========================================================================
phase('Query')

// --- resolve project scope (RUS-66) ----------------------------------------
// Precedence: input.allProjects > input.project (trimmed) > config linearProject
// > "QRSPI". The JS sandbox cannot run python, so a one-line worker runs the
// self-locating helper verbatim and returns its JSON stdout, which we parse with
// the same text-return-then-JS-parse shape as resolve/restack. The config read
// only happens when scope is NOT already pinned by allProjects or input.project.
// A non-ok config read is a HARD FAILURE (per Slice 1 notes) — never a silent
// fall-through to a wrong/empty sweep.
// Scope→loop boundary (RUS-73): both arms below must leave `tickets` holding records
// of the existing { id, title, status, createdAt } shape so the unchanged loop body
// consumes them identically. The single-ticket arm (if TICKET_ARG) fetches ONE issue;
// the else arm is the existing scope-resolve + validate + sweep + order stretch,
// byte-for-byte unchanged.
let tickets = []
if (TICKET_ARG) {
  // --- single-ticket scope (input.ticket) ----------------------------------
  // Skip project-scope resolution / the list_issues sweep / the order step: fetch
  // exactly this one issue and run it through the identical loop body below. A
  // not-found fetch is a HARD FAILURE (fail loud) rather than an empty queue.
  log(`Project scope: single ticket (input.ticket=${TICKET_ARG})`)
  const oneOut = await agent(
    `You are the SINGLE-TICKET fetch worker for the QRSPI batch Query phase.
Use mcp__linear__get_issue to fetch the Linear issue whose identifier is EXACTLY
"${TICKET_ARG}".

Return that one ticket as a tickets array with a single element:
  { "tickets": [ { "id": "${TICKET_ARG}", "title": <the issue title>, "status": <the issue's current workflow state name, e.g. "Selected" / "Design Review">, "createdAt": <the issue's ISO-8601 creation timestamp> } ] }

Pin status to the issue's current workflow STATE NAME and createdAt to its ISO-8601
creation timestamp — both are required. Nothing else. If no issue with that exact
identifier exists, do NOT invent one and do NOT return an empty array: report that the
issue was not found (HARD STOP).`,
    { label: `get:${TICKET_ARG.toLowerCase()}`, phase: 'Query', schema: TICKETS_SCHEMA }
  )
  if (!oneOut || !Array.isArray(oneOut.tickets) || oneOut.tickets.length === 0) {
    // Fail loud: a single-ticket run for a nonexistent id must abort the whole run,
    // NOT fall through to an empty queue indistinguishable from "nothing to do".
    throw new Error(
      `qrspi-batch: single-ticket scope input.ticket="${TICKET_ARG}" resolved to no issue — ` +
      `aborting (fail loud) rather than producing an empty queue. Check the identifier.`
    )
  }
  const el = oneOut.tickets[0]
  tickets = [{ id: el.id, title: el.title, status: el.status, createdAt: el.createdAt }]
} else {
let PROJECT // the concrete resolved project name, or undefined when ALL_PROJECTS
if (!ALL_PROJECTS) {
  if (PROJECT_ARG !== undefined) {
    PROJECT = PROJECT_ARG
  } else {
    const cfgOut = await agent(
      `You are the CONFIG worker for the QRSPI batch. Your cwd is the main repo root.
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives:

  python3 ${engineCmd('scripts/qrspi_config.py')} --key linearProject

It reads the repo's .qrspi/config.json (self-locating) and prints a one-line JSON
envelope { "ok": true, "key": "linearProject", "value": "<project>" } to stdout
(falling back to "QRSPI" when no config is present). Output that JSON as your FINAL
message, exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT
call any structured-output tool. If it printed ok:false, still output that JSON verbatim
(HARD STOP — do NOT retry or improvise alternative commands/paths).`,
      { label: 'config:linearProject', phase: 'Query' }
    )
    const cfg = parseConfigEnvelope(cfgOut, 'linearProject')
    if (!cfg.ok) {
      // Fail loud rather than sweep the wrong/whole set: an unreadable config scope
      // resolution is unrecoverable for this run (Slice 1 notes — treat non-ok as a
      // hard failure, not a silent fall-through).
      throw new Error(`qrspi-batch: could not resolve project scope from config — ${cfg.error ?? 'unknown error'}`)
    }
    PROJECT = cfg.value
  }
}

log(`Project scope: ${ALL_PROJECTS ? 'all projects (input.allProjects)' : `"${PROJECT}"`}`)

// Fail loud on a non-matching concrete scope (Decision 4 / AC4b): a typo'd or
// otherwise unresolved project name must abort the run with an error naming the
// project, NOT fall through to a silent empty sweep that is indistinguishable from
// an empty queue. We validate the resolved name against the Linear project list
// before sweeping. The scope log() above fires first so the resolved project is
// visible. All-projects (the explicit opt-in) needs no validation.
if (!ALL_PROJECTS) {
  const matchOut = await agent(
    `You are the PROJECT-SCOPE validator for the QRSPI batch.
Use mcp__linear__list_projects to list the Linear projects in the authenticated
workspace. Determine whether a project whose name is EXACTLY "${PROJECT}" exists
(exact, case-sensitive name match — not a substring, not fuzzy).

Return ONLY a single-line JSON object, nothing else, no prose, no code fences:
  { "exists": true }  if such a project exists, otherwise  { "exists": false }`,
    { label: 'validate:project-scope', phase: 'Query' }
  )
  let matched = false
  try {
    const raw = extractJsonObject(matchOut)
    if (raw) matched = JSON.parse(raw).exists === true
  } catch { matched = false }
  if (!matched) {
    throw new Error(
      `qrspi-batch: resolved project scope "${PROJECT}" matches no Linear project — ` +
      `aborting rather than sweeping an empty set (check .qrspi/config.json linearProject, ` +
      `pass {"project":"..."} to override, or {"allProjects":true} to sweep all projects).`
    )
  }
}

const batches = await parallel(
  STATUSES.map(status => () =>
    agent(
      `Use mcp__linear__list_issues with:
- state: "${status}"
- assignee: "me"
- limit: 250${ALL_PROJECTS ? '\n(do not pass a project argument — include every project)' : `\n- project: "${PROJECT}"`}

Return every ticket as { id, title, status, createdAt } with id like "RUS-8", status "${status}", and createdAt the ticket's ISO-8601 creation timestamp. Nothing else (besides createdAt).`,
      { label: `list:${status.toLowerCase().replace(/\s+/g, '-')}`, phase: 'Query', schema: TICKETS_SCHEMA }
    )
  )
)

const seen = new Set()
tickets = []
for (const b of batches) {
  if (!b) continue
  for (const t of b.tickets) {
    if (seen.has(t.id)) continue
    seen.add(t.id)
    tickets.push(t)
  }
}

// RUS-71: deterministic within-phase ordering. After flatten+dedup, sort the queue by
// STATUSES (phase) order, then by createdAt ascending with id numeric-suffix tie-break,
// so tickets are processed in within-phase FIFO order. The pure comparator lives in the
// tested helper scripts/qrspi_order_tickets.py; the JS sandbox cannot run python (it
// delegates all python mechanics to worker agents — same pattern as qrspi_resolve.py),
// so a Query-phase worker runs the helper over the {tickets, statuses} envelope and
// returns the sorted tickets ARRAY as verbatim JSON, which we parse and reassign here.
// A non-empty queue is required for this step (the empty short-circuit below still runs
// when there are none); the sort is order-only and never adds/drops tickets.
if (tickets.length > 1) {
  const orderEnvelope = JSON.stringify({ tickets, statuses: STATUSES })
  const sortedOut = await agent(
    `You are the ORDER worker for the qrspi-batch Query phase. Run EXACTLY this command,
verbatim, from your cwd (the repo/worktree root) — do NOT hand-derive, re-implement, or
substitute paths. Pipe the JSON envelope below to its stdin on a single invocation:

  cat <<'QRSPI_ORDER_EOF' | python3 ${engineCmd('scripts/qrspi_order_tickets.py')}
${orderEnvelope}
QRSPI_ORDER_EOF

The helper reads the { "tickets": [...], "statuses": [...] } envelope from stdin and writes
the SORTED tickets ARRAY (grouped by statuses order, then createdAt ascending with id
tie-break) as JSON to stdout. Output that command's STDOUT — the JSON array — as your FINAL
message: exactly and verbatim, with NO surrounding prose, NO code fences, NO edits. Do NOT
call any structured-output tool; do NOT summarize. If the command errors or prints nothing,
output the verbatim error (HARD STOP — do NOT retry or improvise an alternative).`,
    { label: 'order:tickets', phase: 'Query' }
  )
  const sorted = parseOrderedTickets(sortedOut, tickets)
  if (sorted) tickets = sorted
}
} // end else (sweep/scope path) — RUS-73 single-ticket vs sweep branch

log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
if (tickets.length === 0) {
  // No in-flight queue, but the reconciliation backlog is independent of it — still
  // reap stranded merged worktrees when the pass is enabled.
  const reconciliation = RECONCILE ? await runReconciliation(new Set()) : undefined
  return { ticketsProcessed: 0, note: `No tickets in ${STATUSES.join(' / ')}`, reconciliation }
}

// Run-start trunk sync (RUS-74, AC2): FF-advance local `main` to `origin/main` BEFORE the
// per-ticket loop cuts any worktree, so no ticket — least of all a dependent one — is built
// on a stale trunk. A non-ok envelope (non-`main` HEAD, divergence, dirty tree, fetch
// failure) is FATAL: throw to abort the whole run loud with the verbatim reason rather than
// silently proceed on stale state. Runs only on a non-empty queue (the empty short-circuit
// above already returned).
phase('Sync')
const runStartSync = await syncTrunk('Sync')
if (!runStartSync.ok) {
  throw new Error(`run-start trunk sync failed — ${runStartSync.error ?? 'unknown'}; aborting run (refusing to build on a stale local main)`)
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
        // RUS-83: a cap-reached red frontier waits with ciGaveUp — make the park explicit
        // in the per-ticket log so a human sees it needs manual diagnosis (not just "wait").
        log(`  ${t.id}: skipped (${a})${r.decision.ciGaveUp ? ' — CI-revise cap reached, auto-revise GAVE UP; parked for manual diagnosis' : ''}`)
    }
    results.push(res)
    // RUS-68: a land whose cleanup left stranded origin refs (ok:true + non-empty
    // failedRemotes) requests a Reconcile RETRY rather than a halt — so we DON'T mark it
    // `processed`, which is the exact set runReconciliation excludes. Leaving it out lets
    // this run's Reconcile pass (when enabled) re-attempt the prune; otherwise the
    // (still-present) origin refs keep it in the backlog for a later run's pass.
    if (!res.reconcileRetry) processed.add(t.id)
    log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}${res.ciGaveUp ? ' (CI-revise cap reached — auto-revise gave up, manual diagnosis needed)' : ''}${res.ciReviseBumpFailed ? ' (CI-Revise-Attempt counter failed to advance)' : ''}${res.reconcileRetry ? ' (Reconcile retry scheduled — stranded remotes)' : ''}`)
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
