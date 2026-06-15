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
//     decision{ action, phase, nextPhase, resetToPhase, discardPhases[],
//               commentTargets[], changeRequested, reason } }
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

// Parse the resolved per-phase critic config emitted by scripts/qrspi_critics_config.py — the
// single tested source of truth that replaces the former ~6 inline JS parsers/resolvers AND the
// two separate `--key critics` reads (the "single read discipline"). The script reads
// .qrspi/config.json ONCE and prints { ok, phases, warnings }; this extracts `phases` and logs
// each warning (the lens-drop / candidate-clamp notices the inline resolvers used to log()).
// Best-effort: ANY of no JSON, a parse failure, or a missing/non-object `phases` ⇒
// DEFAULT_CRITIC_PHASES, so a garbled critic config silently falls back to defaults and NEVER
// gates the run. Returns the full phases object — every phase resolved to { enabled, maxRounds,
// … } with the UNIFORM `enabled` flag (default ON for questions/research/design/structure/plan,
// OFF for the opt-in implementation seam). A present-but-partial envelope is shallow-merged over
// the defaults so every phase key is always present for the consumers below.
function parseCriticsEnvelope(text) {
  const raw = extractJsonObject(text)
  if (!raw) return DEFAULT_CRITIC_PHASES
  let env
  try { env = JSON.parse(raw) } catch { return DEFAULT_CRITIC_PHASES }
  const phases = env && typeof env === 'object' ? env.phases : undefined
  if (!phases || typeof phases !== 'object' || Array.isArray(phases)) return DEFAULT_CRITIC_PHASES
  if (Array.isArray(env.warnings)) for (const w of env.warnings) log(`  config: ${w}`)
  return { ...DEFAULT_CRITIC_PHASES, ...phases }
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

// The deterministic pre-critic node-check envelope (RUS-57 Decision 2). Today only the research
// phase carries a nodeCheck — the citation validator (scripts/qrspi_verify_citations.py) printing
// a single-line CitationCheckEnvelope { ok, unresolved, error? }. `ok:false` (an out-of-bounds
// citation, or an I/O error) fails the phase BEFORE persist, so nothing is written.
const NODECHECK_SCHEMA = {
  type: 'object',
  required: ['ok'],
  properties: {
    ok: { type: 'boolean' },
    unresolved: { type: 'array', items: { type: 'string' } },
    error: { type: 'string' },
  },
}

// The qrspi-critic agent's verdict (Decision 2 — schema'd return, no staged file). The
// edge-critic judges the produced artifact as a faithful DERIVATION of its upstream input
// and replies { pass, findings }: pass:true => findings empty; pass:false => findings is a
// non-empty list of self-contained strings, each naming a specific upstream requirement
// the artifact dropped/contradicted/distorted. Shape matches qrspi_critic_loop.py's
// canonical verdict ({pass, findings}); findings elements are pinned to strings here.
const CRITIC_VERDICT_SCHEMA = {
  type: 'object',
  required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
  },
}

// The qrspi-design-judge agent's comparative verdict (RUS-59 — the design-phase N-select
// stage). The judge scores N candidate designs on the four RUS-56 lenses (equal weight) and
// names, per non-winning candidate, the strong `graft_ideas` worth merging into the winner.
// Distinct from CRITIC_VERDICT_SCHEMA (binary {pass, findings}, no ranking, no graft dimension):
// this carries a per-candidate numeric ranking. The `winner` field is ADVISORY — the tested
// pure selector (scripts/qrspi_design_select.py) recomputes the authoritative winner from
// `scores` (highest score, lowest-index tie-break) and ignores this field.
const DESIGN_JUDGE_SCHEMA = {
  type: 'object',
  required: ['scores', 'winner'],
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        required: ['candidate', 'score', 'rationale', 'graft_ideas'],
        properties: {
          candidate: { type: 'string' },
          score: { type: 'number' },
          rationale: { type: 'string' },
          graft_ideas: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    winner: { type: 'string' },
  },
}

// The tested pure selector's output (scripts/qrspi_design_select.py, RUS-59 Slice 1). Reduces a
// DESIGN_JUDGE_SCHEMA judge verdict to the authoritative selection: `winner` is the highest-score
// candidate (lowest-index tie-break, recomputed deterministically — the judge's own winner field
// is ignored), `scores` is echoed through for logging, and `graftDirectives` is the first-seen-
// deduped union of all NON-winning candidates' graft_ideas (winner's own excluded; empty ⇒ the
// graft step is a no-op). The JS glue never re-derives this — the python module is the source of
// truth (it fails closed with a non-zero exit on empty/malformed input).
const DESIGN_SELECT_SCHEMA = {
  type: 'object',
  required: ['winner', 'scores', 'graftDirectives'],
  properties: {
    winner: { type: 'string' },
    scores: { type: 'array' },
    graftDirectives: { type: 'array', items: { type: 'string' } },
  },
}

// The decision returned by scripts/qrspi_critic_loop.py's CLI shim (next_action): the
// converge/revise/cap_reached action plus any residual findings to surface into the PR body
// on cap-reached. The JS glue (criticDecision) never re-derives this — it is the tested
// pure module's single source of truth.
const LOOP_DECISION_SCHEMA = {
  type: 'object',
  required: ['action', 'residual_findings'],
  properties: {
    action: { type: 'string', enum: ['converged', 'revise', 'cap_reached'] },
    residual_findings: { type: 'array', items: { type: 'string' } },
  },
}

// The decision returned by scripts/qrspi_slice_critic.py's `decide` CLI shim (RUS-75): whether
// to run the per-slice edge critic for one slice and, if so, the Graphite diff range that scopes
// it. The JS glue (sliceCriticDecide) never re-derives this — the tested pure module is the
// single source of truth. `run` is the only required field; the nullable string fields are
// `null` on a skip (alreadyCommitted / single-slice) and populated on a run.
const SLICE_DECIDE_SCHEMA = {
  type: 'object',
  required: ['run'],
  properties: {
    run: { type: 'boolean' },
    skipReason: { type: ['string', 'null'] },
    diffBase: { type: ['string', 'null'] },
    diffHead: { type: ['string', 'null'] },
  },
}

// The synthesized round verdict the qrspi_critic_synthesize.py worker emits (RUS-56): the M
// per-lens { pass, findings } replies reduced to one authoritative { pass, findings } for the
// round (pass only if every lens passed; findings is the exact-string-deduped union, each
// optionally lens-tagged as { text, lens }). findings items may therefore be a bare string OR
// a { text, lens } object — both are accepted. The JS glue never re-derives this reduction; it
// is the tested pure module (scripts/qrspi_critic_synthesize.py) single source of truth.
const SYNTHESIZED_VERDICT_SCHEMA = {
  type: 'object',
  required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean' },
    findings: {
      type: 'array',
      items: {
        oneOf: [
          { type: 'string' },
          {
            type: 'object',
            required: ['text'],
            properties: { text: { type: 'string' }, lens: { type: 'string' } },
          },
        ],
      },
    },
  },
}

// The design-critic lens set (RUS-56). Each id maps to the landed agentType
// `qrspi-design-critic-<id>` and its prompt file under .claude/agents/. Config-supplied lens
// validation now lives in scripts/qrspi_critics_config.py (the tested resolver); this constant
// is the JS-side fallback baked into DEFAULT_CRITIC_PHASES so a config-read failure still yields
// the full default panel.
const DEFAULT_DESIGN_LENSES = ['completeness', 'internal-consistency', 'edge-alignment', 'simplicity']

// The default design-phase N-select framing axes (RUS-59). When `critics.design.candidates`
// N > 1, runDesignSelectLoop fans out the first N of these framings as orthogonal produce runs
// (analogous to DEFAULT_DESIGN_LENSES for the critic panel). Each framing is passed to the
// SAME qrspi-design agentType as a per-framing instruction line (Decision 2 Option A: framings
// as data, no per-framing agent files). The list length (3) is the hard upper clamp on N.
const DEFAULT_DESIGN_FRAMINGS = ['mvp-first', 'risk-first', 'extensibility-first']

// The JS-side fallback mirror of scripts/qrspi_critics_config.py's all-defaults resolution —
// returned verbatim by parseCriticsEnvelope when the config read/parse fails, and shallow-merged
// under a partial envelope so every phase key is always present. Defaults encode the UNIFORM
// `enabled` vocabulary AND a uniform default: EVERY phase critic is OFF unless its config block
// sets `enabled: true` (critics are opt-in across the board). Keep this in lockstep with the
// Python resolver's defaults (verified there by qrspi_critics_config_test.py).
const DEFAULT_CRITIC_PHASES = {
  questions: { enabled: false, maxRounds: 2 },
  research: { enabled: false, maxRounds: 2 },
  design: { enabled: false, maxRounds: 2, lenses: DEFAULT_DESIGN_LENSES, candidates: 1 },
  structure: { enabled: false, maxRounds: 2 },
  plan: { enabled: false, maxRounds: 2 },
  implementation: { enabled: false, maxRounds: 2, coherence: { enabled: false, maxRounds: 2 } },
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

  python3 ${engineCmd('scripts/qrspi_persist.py')} --ticket ${id} --artifact ${name}

It moves the staged artifact into the ticket's worktree at the canonical path (which it
self-locates) and prints JSON { ok, dest, bytes, error? }. Parse that JSON and return it
verbatim. If it reports ok:false, return that as-is — HARD STOP, do NOT retry, do NOT
improvise alternative commands or paths.`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA }
  )
}

// Deterministic pre-critic node-check (RUS-57 Decision 2 Option A). Runs INSIDE the pre-persist
// staging window of runPhase — after the producer succeeds, before the edge-critic loop — on the
// still-staged artifact. The only node-check today is research's citation validator. The command
// is fully built at the call site (doDesign, where `wd`/`r` are in scope) and carried verbatim on
// `nodeCheck.cmd`, so this function needs no path context. It spawns a worker to run that one
// command and parse its single-line envelope. Returns { ok, unresolved } — ok:false (a broken
// citation, an I/O error, or a worker/parse failure) makes runPhase return false so nothing
// persists. A null worker result is treated as ok:false (fail-closed — the check could not run).
async function runNodeCheck(id, name, nodeCheck) {
  const env = await agent(
    `You are the NODE-CHECK worker for ${id} artifact "${name}". Your cwd is the main repo root.
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives:

  ${nodeCheck.cmd}

It prints ONE single-line JSON envelope { ok, unresolved, error? } and exits 0 (ok) or 1
(not ok). Parse that JSON and return it verbatim. If it reports ok:false or exits non-zero,
return that JSON as-is — HARD STOP, do NOT retry, do NOT improvise alternative commands.`,
    { label: `nodecheck:${id}:${name}`, phase: 'Critic', schema: NODECHECK_SCHEMA }
  )
  if (!env || typeof env.ok !== 'boolean') {
    return { ok: false, unresolved: [] }
  }
  return { ok: env.ok === true, unresolved: Array.isArray(env.unresolved) ? env.unresolved : [] }
}

// Edge-critic loop (RUS-55). Runs ENTIRELY inside the pre-persist staging window of
// runPhase: it critiques the just-produced artifact at stg(id, name) against its upstream
// input (the rubric anchor), and on a non-pass spawns a reviser that REWRITES stg(id, name)
// in place, then re-critiques — up to the cap. The converge / continue / cap decision is
// NOT re-derived here; it is delegated to the tested pure module scripts/qrspi_critic_loop.py
// (single-critic per round => the verdict is passed to next_action as a one-element list,
// OQ2). Returns { ok, residualFindings }: ok is true whenever the loop completed (converged
// OR cap_reached — a cap-reached artifact is still finalized, with its residual findings
// surfaced into the PR body, AC2); residualFindings is [] on converge and the last verdict's
// findings on cap_reached. A spawn failure (critic or reviser returns null) is ok:false
// (the loop could not run) — runPhase treats that like any other phase failure.
//
// criticConfig fields consumed here:
//   upstreamPath : absolute path to the upstream artifact (rubric anchor) — resolved at the
//                  call site where `wd` is in scope (doDesign/doPlan), so this function needs
//                  no `wd` (ref: structure §Unverified Assumptions, deferred-ctx note).
//   maxRounds    : cap, default 2 when omitted.
//   rubric       : optional extra rubric text spliced into the critic prompt; omitted when absent.
async function runCriticLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const upstreamPath = criticConfig.upstreamPath
  const artifactPath = stg(id, name)
  const rubricLine = criticConfig.rubric ? `RUBRIC = ${criticConfig.rubric}\n` : ''

  // AC-INSTR: accumulate the per-round verdict ({lens, pass, findings}) so every termination
  // (including aborts) can be reduced+appended to the per-ticket ledger as one CriticStepMetrics
  // record. The reduction (findingsCount) is done in PYTHON (recordCriticMetrics → reducer); JS
  // only collects the raw verdicts. The single critic has no panel lens, so lens is null.
  const metricRounds = []

  for (let round = 0; round < maxRounds; round++) {
    // One critic per round (single-critic, not parallel() — OQ2). The agent reads both
    // paths itself and returns the schema'd { pass, findings } verdict.
    const verdict = await agent(
      `You are the qrspi-critic for ${id} artifact "${name}", round ${round + 1}/${maxRounds}.
UPSTREAM_PATH = ${upstreamPath}
ARTIFACT_PATH = ${artifactPath}
${rubricLine}Read BOTH paths and judge ARTIFACT_PATH as a faithful derivation of UPSTREAM_PATH (review the EDGE, not the node). Return { pass, findings } per the schema.`,
      { label: `critic:${id}:${name}#${round + 1}`, phase: 'Critic', agentType: 'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA }
    )
    if (verdict === null) {
      log(`  ${id}: ${name} critic round ${round + 1} failed/skipped — stopping this ticket`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }
    const passed = verdict.pass === true
    const findings = Array.isArray(verdict.findings) ? verdict.findings : []
    // AC-INSTR: capture this round's verdict (single-critic ⇒ no lens) for the ledger record.
    metricRounds.push({ lens: null, pass: passed, findings })
    log(`  ${id}: ${name} critic round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)

    // Delegate the converge/revise/cap decision to the tested pure module. The verdict is
    // passed as a one-element list (single-critic). The script self-locates from __file__.
    const decision = await criticDecision([verdict], round, maxRounds)
    if (!decision) {
      log(`  ${id}: ${name} critic-loop decision failed to compute — stopping this ticket`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }
    if (decision.action === 'converged') {
      log(`  ${id}: ${name} critic CONVERGED at round ${round + 1}`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'converged')
      return { ok: true, residualFindings: [], metrics }
    }
    if (decision.action === 'cap_reached') {
      log(`  ${id}: ${name} critic CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to PR body`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'cap_reached')
      return { ok: true, residualFindings: decision.residual_findings, metrics }
    }
    // action === 'revise': spawn a reviser to rewrite stg(id, name) in place addressing the
    // findings, then re-critique on the next iteration. The reviser is the same typed phase
    // PRODUCER agent re-prompted with the findings (it already knows how to write this
    // artifact to the staging path; the findings are the only new input).
    log(`  ${id}: ${name} critic REVISE at round ${round + 1} — rewriting artifact to address findings`)
    const rev = await agent(
      `You are the REVISER for ${id} artifact "${name}". A critic reviewed it as a derivation of its upstream input and found it does NOT yet faithfully preserve every upstream requirement.
ARTIFACT_PATH = ${artifactPath}
UPSTREAM_PATH = ${upstreamPath}
FINDINGS (each names a specific upstream requirement the current artifact dropped/contradicted/distorted):
${findings.map((f, i) => `  ${i + 1}. ${f}`).join('\n')}

Read the current artifact at ARTIFACT_PATH and the upstream at UPSTREAM_PATH, then REWRITE the artifact IN PLACE at ARTIFACT_PATH so it resolves EVERY finding while keeping everything already correct. Write the full revised artifact to ARTIFACT_PATH (non-empty). Do not change any other file. Return a one-line summary.`,
      { label: `revise:${id}:${name}#${round + 1}`, phase: 'Critic' }
    )
    if (rev === null) {
      log(`  ${id}: ${name} reviser round ${round + 1} failed/skipped — stopping this ticket`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }
  }
  // Loop exhausted without an explicit decision return (defensive — next_action's cap branch
  // returns cap_reached at round == maxRounds-1, so we normally exit inside the loop). Treat
  // as cap-reached with no captured findings rather than silently passing.
  log(`  ${id}: ${name} critic loop exhausted ${maxRounds} round(s) without converging`)
  const metrics = await recordCriticMetrics(id, name, metricRounds, 'exhausted')
  return { ok: true, residualFindings: [], metrics }
}

// Multi-lens edge-critic PANEL loop (RUS-56) — the design-phase peer to the single-critic
// runCriticLoop. Same pre-persist staging window, same { ok, residualFindings } return shape,
// so runPhase's existing write-back (criticConfig.residualFindings) is unchanged. The ONLY
// difference is the round body: instead of one critic, it fans out criticConfig.lenses lens
// agents in PARALLEL, reduces their M { pass, findings } replies to one authoritative round
// verdict via the tested pure synthesize reducer (scripts/qrspi_critic_synthesize.py — the JS
// never re-derives the reduction), then delegates the converge/revise/cap decision to the SAME
// tested next_action (via criticDecision) the single critic uses. On `revise` it re-spawns the
// design producer with the synthesized findings, rewriting stg(id, name) IN PLACE (never
// emptying it). On `cap_reached` it returns the residual findings for the PR-body splice; on a
// round-0 all-lens pass it converges with zero revise spawns.
//
// Each lens id maps to agentType `qrspi-design-critic-<lens-id>` (the landed lens prompt
// files), and is spawned with CRITIC_VERDICT_SCHEMA — the same { pass, findings } contract the
// single critic returns. Every lens receives the identical input set: the staged design plus
// the persisted upstream ticket/research/questions paths (resolved at the call site, passed on
// criticConfig).
//
// criticConfig fields consumed here:
//   lenses        : non-empty list of lens ids (the panel switch — runPhase routes here only
//                   when lenses?.length). Each id => agentType qrspi-design-critic-<id>.
//   maxRounds     : cap, default 2 when omitted.
//   upstreamPath  : absolute path to research.md (the RESEARCH_PATH lens input).
//   ticketContentPath, questionsPath : absolute paths to the ticket content / questions.md
//                   lens inputs (resolved in doDesign where `wd`/`r` are in scope).
async function runCriticPanelLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const lenses = criticConfig.lenses
  const artifactPath = stg(id, name)
  const researchPath = criticConfig.upstreamPath
  const ticketContentPath = criticConfig.ticketContentPath
  const questionsPath = criticConfig.questionsPath
  const summaryRounds = []
  // AC-INSTR: accumulate EVERY lens verdict across rounds ({lens, pass, findings}) so the panel
  // step terminates into one CriticStepMetrics ledger record (findingsCount reduced in Python).
  const metricRounds = []

  for (let round = 0; round < maxRounds; round++) {
    // Fan out one agent PER LENS in parallel. Each returns the schema'd { pass, findings }
    // verdict; we tag each reply with its lens id so synthesize can audit-tag findings.
    const replies = await parallel(
      lenses.map(lens => async () => {
        const agentType = `qrspi-design-critic-${lens}`
        const verdict = await agent(
          `You are the ${lens} lens of the qrspi design-phase critic panel for ${id}, round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}
Read all four paths and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`,
          { label: `critic:${id}:${name}:${lens}#${round + 1}`, phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA }
        )
        return { lens, verdict }
      })
    )

    // A lens that failed to spawn (null verdict) cannot attest the design — stop this ticket
    // rather than silently treating a missing lens as a pass.
    const failedLens = replies.find(rp => !rp || rp.verdict === null)
    if (failedLens) {
      log(`  ${id}: ${name} panel round ${round + 1} — lens "${failedLens.lens}" failed/skipped, stopping this ticket`)
      // AC-INSTR: a lens failed to spawn — capture the lenses that DID reply this round so the
      // aborted record reflects partial progress, then emit the record (aborts count too).
      for (const rp of replies) {
        if (rp && rp.verdict !== null) {
          metricRounds.push({ lens: rp.lens, pass: rp.verdict.pass === true, findings: Array.isArray(rp.verdict.findings) ? rp.verdict.findings : [] })
        }
      }
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }

    // Build the per-lens verdict list (each tagged with its lens id) for the pure reducer.
    const lensVerdicts = replies.map(rp => ({
      pass: rp.verdict.pass === true,
      findings: Array.isArray(rp.verdict.findings) ? rp.verdict.findings : [],
      lens: rp.lens,
    }))
    // AC-INSTR: capture every lens verdict this round for the ledger record.
    for (const v of lensVerdicts) metricRounds.push({ lens: v.lens, pass: v.pass, findings: v.findings })

    // Reduce M lens verdicts to one authoritative round verdict via the tested pure module.
    const synth = await synthesizeVerdicts(lensVerdicts)
    if (!synth) {
      log(`  ${id}: ${name} panel round ${round + 1} — synthesize failed to compute, stopping this ticket`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }
    const passed = synth.pass === true
    const synthFindings = Array.isArray(synth.findings) ? synth.findings : []
    const passCount = lensVerdicts.filter(v => v.pass).length
    log(`  ${id}: ${name} panel round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${passCount}/${lenses.length} lenses passed, ${synthFindings.length} finding(s))`}`)
    summaryRounds.push(`r${round + 1}:${passed ? 'pass' : `${passCount}/${lenses.length}`}`)

    // Delegate the converge/revise/cap decision to the SAME tested next_action the single
    // critic uses, passing the synthesized verdict as the round's authoritative one-element
    // list (the panel reduces M lenses to ONE verdict per round before the decision).
    const decision = await criticDecision([{ pass: passed, findings: synthFindings }], round, maxRounds)
    if (!decision) {
      log(`  ${id}: ${name} panel critic-loop decision failed to compute — stopping this ticket`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }
    if (decision.action === 'converged') {
      log(`  ${id}: ${name} panel CONVERGED at round ${round + 1} [${summaryRounds.join(' ')}]`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'converged')
      return { ok: true, residualFindings: [], summary: `panel converged@r${round + 1} [${summaryRounds.join(' ')}]`, metrics }
    }
    if (decision.action === 'cap_reached') {
      log(`  ${id}: ${name} panel CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to PR body`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'cap_reached')
      return { ok: true, residualFindings: decision.residual_findings, summary: `panel cap-reached@r${round + 1} (${decision.residual_findings.length} residual) [${summaryRounds.join(' ')}]`, metrics }
    }
    // action === 'revise': re-spawn the design producer to rewrite stg(id, name) in place
    // addressing the synthesized findings, then re-run the panel next iteration. The findings
    // may be bare strings or { text, lens } objects — render either for the reviser prompt.
    log(`  ${id}: ${name} panel REVISE at round ${round + 1} — rewriting design to address ${synthFindings.length} finding(s)`)
    const rev = await agent(
      `You are the REVISER for ${id} artifact "${name}". A multi-lens critic panel reviewed it as a derivation of its upstream inputs and found it does NOT yet faithfully preserve every upstream requirement.
ARTIFACT_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}
FINDINGS (each names a specific upstream requirement the current design dropped/contradicted/distorted/over-reached, optionally tagged with the lens that raised it):
${synthFindings.map((f, i) => `  ${i + 1}. ${typeof f === 'object' && f ? `[${f.lens ?? 'panel'}] ${f.text ?? JSON.stringify(f)}` : f}`).join('\n')}

Read the current artifact at ARTIFACT_PATH and the upstream inputs, then REWRITE the artifact IN PLACE at ARTIFACT_PATH so it resolves EVERY finding while keeping everything already correct. Write the full revised artifact to ARTIFACT_PATH (non-empty). Do not change any other file. Return a one-line summary.`,
      { label: `revise:${id}:${name}#${round + 1}`, phase: 'Critic' }
    )
    if (rev === null) {
      log(`  ${id}: ${name} panel reviser round ${round + 1} failed/skipped — stopping this ticket`)
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
      return { ok: false, residualFindings: [], metrics }
    }
  }
  // Defensive: next_action returns cap_reached at round == maxRounds-1, so we normally exit
  // inside the loop. Treat exhaustion as cap-reached with no captured findings.
  log(`  ${id}: ${name} panel loop exhausted ${maxRounds} round(s) without converging`)
  const metrics = await recordCriticMetrics(id, name, metricRounds, 'exhausted')
  return { ok: true, residualFindings: [], summary: `panel exhausted ${maxRounds} round(s) [${summaryRounds.join(' ')}]`, metrics }
}

// Invoke the tested pure reducer qrspi_critic_synthesize.py via a worker (the JS sandbox cannot
// run python). Reduces M per-lens verdicts to one { pass, findings } round verdict. Returns the
// parsed verdict or null on failure. Mirrors criticDecision: the verdicts are passed to the
// script on stdin so the fragile finding text never round-trips through the worker's stdout echo.
async function synthesizeVerdicts(verdicts) {
  const out = await agent(
    `You are the CRITIC-SYNTHESIZE worker. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  printf '%s' ${JSON.stringify(JSON.stringify(verdicts))} | python3 ${engineCmd('scripts/qrspi_critic_synthesize.py')}

It prints JSON { pass, findings }. Parse and return it verbatim. If it errors, return that
as-is — HARD STOP, do NOT retry or improvise.`,
    { label: 'critic-synthesize', phase: 'Critic', schema: SYNTHESIZED_VERDICT_SCHEMA }
  )
  if (!out || typeof out.pass !== 'boolean') return null
  if (!Array.isArray(out.findings)) out.findings = []
  return out
}

// The CriticStepMetrics record the qrspi_critic_metrics.py reducer emits (RUS-77, AC-INSTR):
// one terminated critic step (one edge-critic loop OR one panel loop) reduced to { phase,
// rounds:[{lens, pass, findingsCount}], terminalAction }. tokensIn/tokensOut are OPTIONAL and
// ABSENT in the live path (OQ2 — no per-lens usage exposed). The JS glue never re-derives this
// reduction; the tested pure module (scripts/qrspi_critic_metrics.py) is the single source of
// truth (findingsCount is derived in Python, never in JS — ref: impl-log Slice 1 notes).
const CRITIC_METRICS_SCHEMA = {
  type: 'object',
  required: ['phase', 'rounds', 'terminalAction'],
  properties: {
    phase: { type: ['string', 'null'] },
    terminalAction: { type: 'string', enum: ['converged', 'cap_reached', 'exhausted', 'aborted'] },
    rounds: {
      type: 'array',
      items: {
        type: 'object',
        required: ['lens', 'pass', 'findingsCount'],
        properties: {
          lens: { type: ['string', 'null'] },
          pass: { type: 'boolean' },
          findingsCount: { type: 'integer' },
        },
      },
    },
    tokensIn: { type: 'integer' },
    tokensOut: { type: 'integer' },
  },
}

// Build one CriticStepMetrics record from a terminated critic step's accumulated per-round
// verdicts AND durably append it to the per-ticket ledger — via a worker, because the JS sandbox
// cannot run python (RUS-77, AC-INSTR). Mirrors synthesizeVerdicts/criticDecision: the fragile
// verdict text is piped on stdin so it never round-trips through the worker's stdout echo, and the
// python runs at the worker's main-repo-root cwd via engineCmd('scripts/…') — the SAME convention
// the sibling reducers (synthesize/decision) already prove, since r/repoRoot is NOT in scope in the
// loops (they take only name/id/criticConfig).
//
// The reduction (findingsCount per round) is derived in PYTHON by qrspi_critic_metrics.py — never
// in JS. Its bare-record stdout is captured and handed to qrspi_metrics_append.py, the single
// envelope authority (it injects ticketId + timestamp and appends one JSON line, failing CLOSED on
// a bad write). One chained command runs both: the reducer's record is the worker's return value
// (for the criticMetrics fold), and the appender is the side-effecting durability gate — a non-zero
// appender exit fails the chain so the worker surfaces no record (treated here as null ⇒ a
// step-instrumentation failure the caller logs, never a silent skip).
//
// `verdicts` is the accumulated rounds[] (each {lens, pass, findings}); `terminalAction` is the
// loop's matched termination (converged|cap_reached|exhausted|aborted — NEVER revise, which is a
// mid-loop continuation the reducer rejects). Returns the parsed CriticStepMetrics record, or null
// on any failure (worker / parse / append).
async function recordCriticMetrics(id, phase, verdicts, terminalAction) {
  const out = await agent(
    `You are the CRITIC-METRICS worker. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  printf '%s' ${JSON.stringify(JSON.stringify(verdicts))} | python3 ${engineCmd('scripts/qrspi_critic_metrics.py')} --terminal-action ${terminalAction} --phase ${phase} | tee /tmp/qrspi-metrics-${id}-${phase}.json && python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${id} --record "$(cat /tmp/qrspi-metrics-${id}-${phase}.json)" >/dev/null && cat /tmp/qrspi-metrics-${id}-${phase}.json

It builds the CriticStepMetrics record, appends it to the per-ticket ledger, then re-prints the
record as JSON { phase, rounds, terminalAction }. Parse and return that record verbatim. If any
step errors (non-zero exit), return that error as-is — HARD STOP, do NOT retry or improvise.`,
    { label: `critic-metrics:${id}:${phase}`, phase: 'Critic', schema: CRITIC_METRICS_SCHEMA }
  )
  if (!out || !Array.isArray(out.rounds) || typeof out.terminalAction !== 'string') return null
  return out
}

// Invoke the tested pure selector qrspi_design_select.py via a worker (the JS sandbox cannot run
// python). Reduces the judge verdict to { winner, scores, graftDirectives }. The judge output is
// passed on stdin (so the fragile rationale/graft text never round-trips through the worker's
// stdout echo), exactly as synthesizeVerdicts/criticDecision do. The script fails CLOSED with a
// non-zero exit + error envelope on empty/malformed input; a worker failure (null / no winner)
// surfaces as null here, which the caller treats as a fail-closed abort.
async function selectDesignWinner(judgeOutput) {
  const out = await agent(
    `You are the DESIGN-SELECT worker. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  printf '%s' ${JSON.stringify(JSON.stringify(judgeOutput))} | python3 ${engineCmd('scripts/qrspi_design_select.py')}

It prints JSON { winner, scores, graftDirectives } on success (exit 0) or { error } on a non-zero
exit (empty/malformed input — fail-closed). Parse and return whatever JSON it printed verbatim.
HARD STOP — do NOT retry or improvise.`,
    { label: 'design-select', phase: 'Design', schema: DESIGN_SELECT_SCHEMA }
  )
  if (!out || typeof out.winner !== 'string' || !out.winner) return null
  if (!Array.isArray(out.scores)) out.scores = []
  if (!Array.isArray(out.graftDirectives)) out.graftDirectives = []
  return out
}

// Copy the winning candidate's staged design over the canonical staged slot stg(id,'design')
// and re-check the result is non-empty, via a deterministic worker (the JS sandbox cannot touch
// the filesystem). Mirrors the persist worker's verbatim-one-command discipline. Returns true
// iff the copy landed a non-empty stg(id,'design'); false (caller aborts fail-closed) otherwise.
async function stageDesignWinner(id, winnerPath) {
  const dest = stg(id, 'design')
  const out = await agent(
    `You are the DESIGN-STAGE-WINNER worker for ${id}. Your cwd is the main repo root. Run EXACTLY
this one command verbatim — no path edits, no exploration, no alternatives:

  cp ${winnerPath} ${dest} && test -s ${dest} && printf '{"ok":true}\\n' || printf '{"ok":false}\\n'

It copies the winning candidate design over the canonical staged slot and verifies it is
non-empty. Return its JSON stdout verbatim ({ ok }). HARD STOP — do NOT retry or improvise.`,
    { label: `design-stage-winner:${id}`, phase: 'Design', schema: { type: 'object', required: ['ok'], properties: { ok: { type: 'boolean' } } } }
  )
  return !!(out && out.ok === true)
}

// Spawn the qrspi-design-graft agent to rewrite stg(id,'design') IN PLACE merging the named
// runner-up ideas, then re-check the file is still non-empty (graft-empties-file mitigation,
// Risk Register). Returns true iff the graft ran AND left a non-empty file. Only called when
// graftDirectives is non-empty (empty ⇒ the caller skips the graft as a no-op).
async function graftDesignWinner(id, graftDirectives) {
  const dest = stg(id, 'design')
  const rev = await agent(
    `You are the qrspi-design-graft agent for ${id}.
DESIGN_PATH = ${dest}
GRAFT_DIRECTIVES (runner-up ideas to merge into the winning design):
${graftDirectives.map((g, i) => `  ${i + 1}. ${g}`).join('\n')}

Read DESIGN_PATH, merge the directives into it preserving its structure, and write the full
revised design back to DESIGN_PATH (non-empty). Return a one-line summary.`,
    { label: `design-graft:${id}`, phase: 'Design', agentType: 'qrspi-design-graft' }
  )
  if (rev === null) {
    log(`  ${id}: design graft failed/skipped — stopping this ticket`)
    return false
  }
  // Re-verify the graft left a non-empty file (mirrors stageDesignWinner's non-empty gate).
  const out = await agent(
    `You are the DESIGN-GRAFT-VERIFY worker for ${id}. Your cwd is the main repo root. Run EXACTLY
this one command verbatim — no path edits, no exploration:

  test -s ${dest} && printf '{"ok":true}\\n' || printf '{"ok":false}\\n'

Return its JSON stdout verbatim ({ ok }). HARD STOP — do NOT retry or improvise.`,
    { label: `design-graft-verify:${id}`, phase: 'Design', schema: { type: 'object', required: ['ok'], properties: { ok: { type: 'boolean' } } } }
  )
  return !!(out && out.ok === true)
}

// Design-phase N-select stage (RUS-59). Runs ENTIRELY inside the pre-persist staging window of
// runPhase, AFTER the single produce agent and BEFORE the critic panel — but only when the
// resolved candidates count N > 1 (runPhase guards the call; N=1 never reaches here, leaving the
// single-produce path byte-for-byte unchanged). It:
//   1. Fans out the first N of DEFAULT_DESIGN_FRAMINGS as parallel candidate produce runs, each
//      the SAME qrspi-design agentType with a per-framing FRAMING line, written to a distinct
//      per-candidate slot stg(id,'design-cand-K'). Any null/empty candidate aborts fail-closed
//      (Decision 4 Option A) — no partial winner.
//   2. Judges the N candidates (qrspi-design-judge → DESIGN_JUDGE_SCHEMA).
//   3. Selects the winner deterministically via the tested pure selector (selectDesignWinner →
//      qrspi_design_select.py), obtaining { winner, scores, graftDirectives }.
//   4. Copies the winner over the canonical staged slot stg(id,'design') and re-checks non-empty.
//   5. When graftDirectives is non-empty, grafts the runner-up ideas in place (re-checking
//      non-empty); when empty, skips the graft (no-op).
// Lands the final synthesized design at exactly stg(id,'design') for the unchanged critic panel
// + persist to consume. Returns { ok, summary? }: ok:false on any candidate/judge/select/stage/
// graft failure (the caller aborts the ticket). summary folds the per-candidate judge scores for
// the doDesign result line (AC2 scores half).
//
// criticConfig fields consumed here (resolved in doDesign where wd/r are in scope):
//   candidates        : N (already clamped to [2, framings] by qrspi_critics_config.py).
//   ticketContentPath : the ticket content path (candidate + judge input).
//   questionsPath     : questions.md path (candidate + judge input).
//   upstreamPath      : research.md path (candidate + judge input — reused as RESEARCH_PATH).
//   templatePath      : the design template path (candidate produce input).
async function runDesignSelectLoop(name, id, config) {
  const n = config.candidates
  const framings = DEFAULT_DESIGN_FRAMINGS.slice(0, n)
  const ticketContentPath = config.ticketContentPath
  const researchPath = config.upstreamPath
  const questionsPath = config.questionsPath
  const templatePath = config.templatePath

  log(`  ${id}: design N-select — fanning out ${n} candidate(s) [${framings.join(', ')}]`)

  // 1. Fan out N framing candidate produce runs in parallel, each to a distinct staged slot.
  const candidates = await parallel(
    framings.map((framing, k) => async () => {
      const candId = `design-cand-${k}`
      const candPath = stg(id, candId)
      const res = await agent(
        `TICKET_ID = ${id}
TICKET_CONTENT_PATH = ${ticketContentPath}

QUESTIONS_PATH = ${questionsPath}
RESEARCH_PATH = ${researchPath}
OUTPUT_PATH = ${candPath}
TEMPLATE_PATH = ${templatePath}
FRAMING = ${framing}`,
        { label: `design-cand:${id}:${framing}`, phase: 'Design', agentType: 'qrspi-design' }
      )
      return { candId, candPath, framing, res }
    })
  )

  // Verify each candidate ran AND left a non-empty staged file. A null result is a spawn miss;
  // a present-but-empty file is caught by a single batched non-empty check below. Either aborts
  // the whole stage fail-closed (Decision 4 Option A) — no partial winner is ever selected.
  const failedSpawn = candidates.find(c => !c || c.res === null)
  if (failedSpawn) {
    log(`  ${id}: design candidate "${failedSpawn?.framing ?? '?'}" failed/skipped — aborting N-select (fail-closed)`)
    return { ok: false }
  }
  const nonEmpty = await candidatesNonEmpty(id, candidates.map(c => c.candPath))
  if (!nonEmpty) {
    log(`  ${id}: a design candidate staged empty/missing — aborting N-select (fail-closed)`)
    return { ok: false }
  }

  // 2. Judge the N candidates.
  const candidateLines = candidates
    .map(c => `${c.candId} (${c.framing}) = ${c.candPath}`)
    .join('\n')
  const judge = await agent(
    `You are the qrspi-design-judge for ${id}, comparing ${n} candidate designs.
CANDIDATE_PATHS:
${candidateLines}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}
Read all candidate paths and the upstream inputs, score each candidate on the four lenses
(equal weight), name per-non-winner graft_ideas, and return { scores, winner } per the schema.`,
    { label: `design-judge:${id}`, phase: 'Design', agentType: 'qrspi-design-judge', schema: DESIGN_JUDGE_SCHEMA }
  )
  if (judge === null) {
    log(`  ${id}: design judge failed/skipped — aborting N-select (fail-closed)`)
    return { ok: false }
  }

  // 3. Select the winner deterministically via the tested pure selector.
  const sel = await selectDesignWinner(judge)
  if (!sel) {
    log(`  ${id}: design selector failed/fail-closed — aborting N-select`)
    return { ok: false }
  }
  const winner = candidates.find(c => c.candId === sel.winner)
  if (!winner) {
    log(`  ${id}: design selector winner "${sel.winner}" not among candidates — aborting N-select (fail-closed)`)
    return { ok: false }
  }
  log(`  ${id}: design winner = ${sel.winner} (${winner.framing})`)

  // 4. Copy the winner over the canonical staged slot; re-check non-empty.
  if (!await stageDesignWinner(id, winner.candPath)) {
    log(`  ${id}: staging the design winner left an empty/missing file — aborting N-select (fail-closed)`)
    return { ok: false }
  }

  // 5. Conditionally graft runner-up ideas in place (skip as a no-op when none).
  let graftSummary = 'no graft'
  if (sel.graftDirectives.length) {
    log(`  ${id}: grafting ${sel.graftDirectives.length} runner-up idea(s) into the winner`)
    if (!await graftDesignWinner(id, sel.graftDirectives)) {
      log(`  ${id}: design graft did not complete / emptied the file — aborting N-select (fail-closed)`)
      return { ok: false }
    }
    graftSummary = `grafted ${sel.graftDirectives.length} idea(s)`
  } else {
    log(`  ${id}: no runner-up graft directives — skipping graft (no-op)`)
  }

  // Fold the per-candidate judge scores into the returned summary (AC2 scores half).
  const scoreParts = Array.isArray(sel.scores)
    ? sel.scores
        .filter(s => s && typeof s === 'object')
        .map(s => `${s.candidate}:${s.score}`)
    : []
  const summary = `N-select N=${n} winner=${sel.winner}(${winner.framing}) scores[${scoreParts.join(' ')}] ${graftSummary}`
  log(`  ${id}: design ${summary}`)
  return { ok: true, summary }
}

// Verify a list of staged candidate paths are ALL present and non-empty, via one deterministic
// worker command (the JS sandbox cannot touch the filesystem). Returns true iff every path is a
// non-empty file. Mirrors the persist worker's verbatim-one-command discipline.
async function candidatesNonEmpty(id, paths) {
  const test = paths.map(p => `test -s ${p}`).join(' && ')
  const out = await agent(
    `You are the DESIGN-CANDIDATES-CHECK worker for ${id}. Your cwd is the main repo root. Run
EXACTLY this one command verbatim — no path edits, no exploration:

  ${test} && printf '{"ok":true}\\n' || printf '{"ok":false}\\n'

Return its JSON stdout verbatim ({ ok }). HARD STOP — do NOT retry or improvise.`,
    { label: `design-candidates-check:${id}`, phase: 'Design', schema: { type: 'object', required: ['ok'], properties: { ok: { type: 'boolean' } } } }
  )
  return !!(out && out.ok === true)
}

// Read the OPTIONAL `critics` config block and resolve EVERY phase in ONE pass via the tested
// resolver scripts/qrspi_critics_config.py (the single read discipline — replaces the former
// readDesignCriticConfig + readImplementationCriticConfig, each of which spawned its own
// near-identical `--key critics` worker). The script reads .qrspi/config.json once and prints
// { ok, phases, warnings } with every phase resolved to { enabled, maxRounds, … }; parseCritics-
// Envelope turns that into the phases object (logging warnings), falling back to
// DEFAULT_CRITIC_PHASES on any failure. Each caller (doDesign / doPlan / doImplementation) calls
// this ONCE for its action and indexes the phase(s) it needs. `phaseLabel` only groups the worker
// in the progress display. Never throws / never gates the run. The reader command is self-locating
// (engineCmd → the main checkout, where .qrspi/config.json lives and is shared by all tickets).
async function readCriticsConfig(phaseLabel) {
  const cfgOut = await agent(
    `You are the CONFIG worker for the QRSPI phase critics. Your cwd is the main repo root.
Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives:

  python3 ${engineCmd('scripts/qrspi_critics_config.py')}

It reads the repo's .qrspi/config.json (self-locating) and prints a one-line JSON envelope
{ "ok": true, "phases": { … six phases … }, "warnings": [ … ] } to stdout. Output that JSON as
your FINAL message, exactly and verbatim — NO surrounding prose, NO code fences, NO edits. Do NOT
call any structured-output tool. If it printed ok:false, still output that JSON verbatim (do NOT
retry or improvise).`,
    { label: 'config:critics', phase: phaseLabel }
  )
  return parseCriticsEnvelope(cfgOut)
}

// Invoke the tested pure decision module qrspi_critic_loop.py via a worker (the JS sandbox
// cannot run python). Returns { action, residual_findings } or null on failure. The verdicts
// are serialized to a token-free staged JSON file the worker passes to the script on stdin,
// so the fragile verdict text never round-trips through the worker's stdout echo.
async function criticDecision(verdicts, round, maxRounds) {
  const out = await agent(
    `You are the CRITIC-DECISION worker. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  printf '%s' ${JSON.stringify(JSON.stringify(verdicts))} | python3 ${engineCmd('scripts/qrspi_critic_loop.py')} --round ${round} --max-rounds ${maxRounds}

It prints JSON { action, residual_findings }. Parse and return it verbatim. If it errors,
return that as-is — HARD STOP, do NOT retry or improvise.`,
    { label: `critic-decision#${round}`, phase: 'Critic', schema: LOOP_DECISION_SCHEMA }
  )
  if (!out || typeof out.action !== 'string') return null
  if (!Array.isArray(out.residual_findings)) out.residual_findings = []
  return out
}

// Invoke the tested pure decision module qrspi_slice_critic.py's `decide` shim via a worker (the
// JS sandbox cannot run python) to decide whether to run the per-slice edge critic for slice `n`
// and, if so, the Graphite diff range scoping it (RUS-75, AC1). Returns the parsed
// { run, skipReason, diffBase, diffHead } envelope or null on failure. The worker `setup` object
// lacks the ticket id, so it is injected here into the projected { id, slices } blob the script
// reads from stdin (the `decide` shim derives the branch names from it). Mirrors criticDecision:
// the blob is piped on stdin so the slice list never round-trips through the worker's stdout echo.
async function sliceCriticDecide(t, setup, n) {
  const blob = JSON.stringify({ id: t.id, slices: setup.slices })
  const out = await agent(
    `You are the SLICE-CRITIC-DECIDE worker. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  printf '%s' ${JSON.stringify(blob)} | python3 ${engineCmd('scripts/qrspi_slice_critic.py')} --slice-index ${n}

It prints JSON { run, skipReason, diffBase, diffHead }. Parse and return it verbatim. If it errors,
return that as-is — HARD STOP, do NOT retry or improvise.`,
    { label: `slice-decide:${t.id}#${n}`, phase: 'Critic', schema: SLICE_DECIDE_SCHEMA }
  )
  if (!out || typeof out.run !== 'boolean') return null
  return out
}

// Build the finalize-prompt FRAGMENT that splices the critic's residual findings (cap-reached
// only) into the phase commit message BEFORE `gt submit` — so Graphite seeds the PR body with
// them at creation (a body amended AFTER submit would not update the PR, since gt seeds the
// body from the commit message at creation only). No findings ⇒ '' (the finalize prompt is
// byte-for-byte unchanged). Mirrors qrspi_pr_body.py's seam: the findings are written to a
// token-free staged JSON file (the script owns the worktree path and reads the file) so the
// fragile finding text never round-trips through heredoc quoting. `phase` is 'design'|'plan'.
function criticBodyStep(id, phase, findings, wd) {
  if (!Array.isArray(findings) || findings.length === 0) return ''
  const stageFile = `/tmp/phase-stage/${id}/critic-findings-${phase}.json`
  return ` Then surface the edge-critic's residual findings into the PR body BEFORE submitting: (a) write this EXACT JSON verbatim (a JSON array of strings) to ${stageFile}: ${JSON.stringify(findings)} ; (b) run EXACTLY this one command verbatim from ${wd}: \`python3 ${engineCmd('scripts/qrspi_critic_body.py')} --ticket ${id} --phase ${phase} --findings-file ${stageFile}\` — it amends the ${id}/${phase} commit message to append the residual findings (self-locating); if it reports ok:false, return ok:false (do NOT submit).`
}

// Run one phase agent, then deterministically persist its staged artifact. Reuses an
// existing non-empty canonical artifact (resume). Returns true on success, false on
// failure/skip.
//
// criticConfig (RUS-55, OPTIONAL trailing arg): when present, the edge-critic loop runs in
// the pre-persist staging window — produce → critique → revise on stg(id, name) — before the
// persist gate. Absent (undefined) ⇒ the guard is false ⇒ the four original statements run
// VERBATIM (AC1, byte-for-byte unchanged no-critic behavior). On cap-reached the loop's
// residual findings are written back onto the passed criticConfig object as
// `criticConfig.residualFindings` so the caller (doDesign/doPlan) can splice them into the
// finalize commit body; this keeps runPhase's existing boolean return contract intact.
async function runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig) {
  if (existing && existing[name]) {
    log(`  ${id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
  // Design-phase N-select stage (RUS-59): runs BETWEEN the single produce-success and the critic
  // block, guarded by the resolved candidates count N > 1 (Decision 1 Option A). When N≤1 (the
  // default, OFF) this guard is false ⇒ ZERO extra spawns and the single-produce path is
  // byte-for-byte unchanged. When N>1 it fans out N framing candidates, judges + selects + grafts,
  // and lands the synthesized winner at stg(id, name) — exactly what the critic panel + persist
  // gate below already consume. A failed stage aborts the ticket (fail-closed). The N-select
  // summary is handed back on criticConfig.selectSummary for doDesign to fold into its result.
  if (criticConfig && criticConfig.candidates > 1) {
    const sel = await runDesignSelectLoop(name, id, criticConfig)
    if (!sel || !sel.ok) {
      log(`  ${id}: ${name} N-select stage did not complete — stopping this ticket`)
      return false
    }
    if (sel.summary) criticConfig.selectSummary = sel.summary
  }
  // Deterministic pre-critic node-check (RUS-57 Decision 2 Option A): when criticConfig carries
  // a nodeCheck (today only research's citation validator), run it on the still-staged artifact
  // AFTER the producer succeeds and BEFORE the edge-critic loop. A non-ok result (a provably
  // broken citation, an I/O error, or a worker/parse failure) returns false so NOTHING persists —
  // the check lives entirely inside the pre-persist staging window. No-nodeCheck phases skip this
  // block and behave byte-for-byte as before.
  if (criticConfig && criticConfig.nodeCheck) {
    const nc = await runNodeCheck(id, name, criticConfig.nodeCheck)
    if (!nc.ok) {
      log(`  ${id}: ${name} node-check FAILED${nc.unresolved.length ? ` — unresolved: [${nc.unresolved.join(', ')}]` : ''} — stopping this ticket (nothing persisted)`)
      return false
    }
    log(`  ${id}: ${name} node-check passed`)
  }
  // Edge-critic loop (RUS-55): runs BETWEEN produce-success and the persist gate, on the
  // still-staged artifact, so persist remains the single success gate. No-critic phases skip
  // this block entirely and behave byte-for-byte as before.
  if (criticConfig) {
    // Dispatch on lenses: a non-empty criticConfig.lenses selects the multi-lens PANEL
    // (design phase); its absence (the single-critic plan phase, or any other caller) keeps
    // the landed single-critic path byte-for-byte unchanged.
    const cr = criticConfig.lenses?.length
      ? await runCriticPanelLoop(name, id, criticConfig)
      : await runCriticLoop(name, id, criticConfig)
    if (!cr || !cr.ok) {
      log(`  ${id}: ${name} critic loop did not complete — stopping this ticket`)
      return false
    }
    // Hand the cap-reached residual findings back to the caller via the config object. The
    // panel also returns a one-line summary the caller can fold into its result summary.
    criticConfig.residualFindings = cr.residualFindings
    if (cr.summary) criticConfig.criticSummary = cr.summary
    // AC-INSTR: surface this step's CriticStepMetrics record to the caller the SAME way (on the
    // config object), so doDesign can fold it into the ticket result's criticMetrics array. The
    // loop already appended it to the ledger; this is the in-memory copy for the result object.
    // Null when the metrics shell-out itself failed (logged, never silently dropped).
    if (cr.metrics) criticConfig.criticMetrics = cr.metrics
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

  // ONE resolver read up front (the single read discipline): scripts/qrspi_critics_config.py
  // resolves EVERY phase's critic — the uniform `enabled` flag, maxRounds, and the design panel's
  // lenses/candidates — so questions/research/design here (and structure/plan in doPlan) index off
  // one shared resolution. A disabled phase ⇒ undefined criticConfig ⇒ runPhase skips its critic.
  const critics = await readCriticsConfig('Design')

  // Single edge-critic on questions (RUS-57), anchored on the TICKET (Q12 — questions are derived
  // from the ticket). No `lenses` ⇒ runPhase routes to the single-critic runCriticLoop. Gated on
  // critics.questions.enabled (uniform vocabulary; default ON).
  const questionsCritic = critics.questions.enabled ? {
    upstreamPath: r.ticketContentPath,
    maxRounds: critics.questions.maxRounds,
  } : undefined
  if (!critics.questions.enabled) log(`  ${t.id}: questions critic DISABLED by config`)
  if (!await runPhase('questions', 'qrspi-questions',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

OUTPUT_PATH = ${stg(t.id, 'questions')}
TEMPLATE_PATH = ${tpl(wd, 'questions.md')}`, r.existing, t.id, 'Design', questionsCritic)) return failTicket(t)

  // Single edge-critic on research (RUS-57). upstreamPath is questions.md and NEVER
  // r.ticketContentPath — the research phase is firewalled from the ticket (Risk Register
  // med/high; Q12). Research ALSO carries the citation node-check: runPhase runs the validator on
  // the STAGED research.md before the critic, failing the phase on a provably-broken citation
  // (out-of-bounds line/range) without persisting. The validator joins citations against `wd`
  // (the worktree root) explicitly — never resolve_repo_root() (RUS-57 Decision 3; impl-log
  // slice 1: pass --worktree-root wd). engineCmdFor(r,…) anchors the script on the host checkout
  // root (not the worktree HEAD, which a relocating ticket may have moved).
  // Gated on critics.research.enabled (default ON). Disabling the research critic also skips its
  // bundled citation node-check — they ride the same criticConfig, so `enabled:false` turns the
  // whole research-critic bundle off.
  const researchCritic = critics.research.enabled ? {
    upstreamPath: art(wd, t.id, 'questions.md'),
    maxRounds: critics.research.maxRounds,
    nodeCheck: {
      cmd: `python3 ${engineCmdFor(r, 'scripts/qrspi_verify_citations.py')} --artifact-path ${stg(t.id, 'research')} --worktree-root ${wd}`,
    },
  } : undefined
  if (!critics.research.enabled) log(`  ${t.id}: research critic DISABLED by config (citation node-check also skipped)`)
  if (!await runPhase('research', 'qrspi-research',
    `TICKET_ID = ${t.id}
QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
OUTPUT_PATH = ${stg(t.id, 'research')}
TEMPLATE_PATH = ${tpl(wd, 'research.md')}
REPO_ROOT = ${wd}

Project scope: explore ONLY files under ${wd}. The ticket is intentionally hidden from you — do not seek it out.`, r.existing, t.id, 'Design', researchCritic)) return failTicket(t)

  // Multi-lens edge-critic PANEL on the design artifact (RUS-56). The lens set + maxRounds were
  // resolved from the single config read above (critics.design > JS default four lenses / 2
  // rounds); `lenses` is the panel switch runPhase dispatches on. The lens inputs are resolved
  // HERE (where `wd`/`r` are in scope): research.md is upstreamPath (the rubric anchor, reused as
  // RESEARCH_PATH) plus the ticket content + questions.md. The panel populates residualFindings
  // exactly as the single critic does, so the criticBodyStep/PR-body flow below is unchanged.
  // Gated on critics.design.enabled (default ON). Disabled ⇒ undefined ⇒ runPhase skips BOTH the
  // panel and the N-select stage (which it guards on criticConfig.candidates).
  const designCritic = critics.design.enabled ? {
    upstreamPath: art(wd, t.id, 'research.md'),
    maxRounds: critics.design.maxRounds,
    lenses: critics.design.lenses,
    ticketContentPath: r.ticketContentPath,
    questionsPath: art(wd, t.id, 'questions.md'),
    // RUS-59 N-select: candidates (clamped [1,3]) gates the pre-critic N-select stage in
    // runPhase (N>1 only); templatePath is the candidate produce input it needs.
    candidates: critics.design.candidates,
    templatePath: tpl(wd, 'design.md'),
  } : undefined
  if (critics.design.enabled) {
    log(`  ${t.id}: design critic panel — ${critics.design.lenses.length} lens(es) [${critics.design.lenses.join(', ')}], maxRounds ${critics.design.maxRounds}`)
    if (critics.design.candidates > 1) log(`  ${t.id}: design N-select ENABLED — N=${critics.design.candidates} candidate framings`)
  } else {
    log(`  ${t.id}: design critic panel DISABLED by config`)
  }
  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design', designCritic)) return failTicket(t)

  phase('Finalize')
  // Residual critic findings (cap-reached only) to splice into the Design PR body. runPhase wrote
  // each phase's findings back onto its criticConfig object; absent ⇒ converged ⇒ nothing. All
  // three phases (questions/research/design) land on the SAME ${t.id}/design branch + PR, so their
  // residual findings are AGGREGATED into the one design-commit splice (RUS-57 T16). qrspi_critic_
  // body.py only knows the design/plan branch suffixes — there is no questions/research branch —
  // so questions/research findings ride the design phase, each tagged with its source phase.
  // cfg is undefined when that phase's critic was disabled by config — null-safe so a disabled
  // phase simply contributes no findings.
  const tagFindings = (phaseName, cfg) =>
    ((cfg?.residualFindings) ?? []).map(f => `[${phaseName}] ${f}`)
  const designFindings = [
    ...tagFindings('questions', questionsCritic),
    ...tagFindings('research', researchCritic),
    ...(designCritic?.residualFindings ?? []),
  ]
  const designBodyStep = criticBodyStep(t.id, 'design', designFindings, wd)
  const fin = await agent(
    `You are the DESIGN-PHASE finalize worker for ${t.id}, in ${wd}. Follow the "action: run_design" commit+submit steps of ${SKILL}.
1. Verify questions.md, research.md, design.md exist and are non-empty under ${wd}/.qrspi/${t.id}/. If any missing/empty, return ok:false (do NOT commit/transition).
2. Stage ONLY those three artifacts; add them as the single commit (subject "${t.id} [QR]: Design — ${t.title}") on the pre-created ${t.id}/design branch with \`gt modify -c\` (the branch already exists from worktree setup — do NOT use \`gt create\`).${designBodyStep} Then submit the Design PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`${reviewerFlags(r) ? ' (the reviewer flag is required — it is what surfaces the PR in the reviewer\'s Graphite queue; submit it EXACTLY as written, do not drop or alter the reviewer)' : ''} (handle a stale closed-PR association per the SKILL "Resubmitting" steps).
3. BEST-EFFORT project Linear → "Design Review" (a failed Linear write is a WARN, not a failure — still return ok:true with the PR created).
Return: ok, prUrl, newStatus, summary (1-2 sentences).`,
    { label: `finalize-design:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const out = finResult(t, fin, 'run_design')
  // AC-INSTR (RUS-77 Modified Types: TicketResult.criticMetrics): collect each phase's
  // CriticStepMetrics record (surfaced by runPhase onto its criticConfig when that phase's critic
  // ran) into one array and fold it into the result object. A phase whose critic was disabled by
  // config has an undefined criticConfig (so no `.criticMetrics`); records ride one design
  // branch/PR in phase order (questions → research → design). Per plan §12, when EVERY phase
  // critic is disabled (the critics-DISABLED path) NO record is surfaced and the `criticMetrics`
  // key is OMITTED entirely — the disabled path returns the byte-for-byte-unchanged result object
  // (no ledger write either: the loops were never dispatched).
  const criticMetrics = [
    questionsCritic?.criticMetrics,
    researchCritic?.criticMetrics,
    designCritic?.criticMetrics,
  ].filter(Boolean)
  if (criticMetrics.length) out.criticMetrics = criticMetrics
  if (out.action === 'run_design' && fin && fin.ok) {
    // Fold the N-select stage summary (per-candidate judge scores + winner + graft) and the
    // panel's per-round pass/fail summary (and any residual-finding count) into the result
    // summary so a batch run surfaces what the design phase did (AC2 scores half).
    if (designCritic?.selectSummary) out.summary = `${out.summary} [${designCritic.selectSummary}]`
    if (designCritic?.criticSummary) out.summary = `${out.summary} [${designCritic.criticSummary}]`
    if (designFindings.length) out.summary = `${out.summary} [critic: ${designFindings.length} residual finding(s) in PR body]`
  }
  return out
}

// ===========================================================================
// ACTION: advance → plan  (structure → plan → worktree, stacked on design)
// ===========================================================================
async function doPlan(t, r) {
  const wd = r.worktreeDir
  phase('Plan')

  // ONE resolver read for the plan action (the single read discipline). doPlan is a SEPARATE batch
  // action from doDesign, so reading here is the single read for this invocation — not a duplicate.
  const critics = await readCriticsConfig('Plan')

  // Single edge-critic on structure (RUS-57), anchored on its upstream design.md. No `lenses` ⇒
  // runPhase routes to the single-critic runCriticLoop. Gated on critics.structure.enabled (default ON).
  const structureCritic = critics.structure.enabled ? {
    upstreamPath: art(wd, t.id, 'design.md'),
    maxRounds: critics.structure.maxRounds,
  } : undefined
  if (!critics.structure.enabled) log(`  ${t.id}: structure critic DISABLED by config`)
  if (!await runPhase('structure', 'qrspi-structure',
    `TICKET_ID = ${t.id}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
OUTPUT_PATH = ${stg(t.id, 'structure')}
TEMPLATE_PATH = ${tpl(wd, 'structure.md')}`, r.existing, t.id, 'Plan', structureCritic)) return failTicket(t)

  // Edge-critic on the plan artifact, anchored on its upstream structure.md (OQ4). maxRounds is
  // config-overridable per-phase (RUS-57). Gated on critics.plan.enabled (default ON).
  const planCritic = critics.plan.enabled ? {
    upstreamPath: art(wd, t.id, 'structure.md'),
    maxRounds: critics.plan.maxRounds,
  } : undefined
  if (!critics.plan.enabled) log(`  ${t.id}: plan critic DISABLED by config`)
  if (!await runPhase('plan', 'qrspi-plan',
    `TICKET_ID = ${t.id}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
OUTPUT_PATH = ${stg(t.id, 'plan')}
TEMPLATE_PATH = ${tpl(wd, 'plan.md')}`, r.existing, t.id, 'Plan', planCritic)) return failTicket(t)

  if (!await runPhase('worktree', 'qrspi-worktree',
    `TICKET_ID = ${t.id}
PLAN_PATH = ${art(wd, t.id, 'plan.md')}
OUTPUT_PATH = ${stg(t.id, 'worktree')}
TEMPLATE_PATH = ${tpl(wd, 'worktree.md')}`, r.existing, t.id, 'Plan')) return failTicket(t)

  phase('Finalize')
  // structure + plan both land on the SAME ${t.id}/plan branch + PR (qrspi_critic_body.py only
  // knows the design/plan branch suffixes — there is no structure branch), so structure's residual
  // findings are AGGREGATED into the one plan-commit splice, tagged with their source phase (T16).
  const planFindings = [
    ...((structureCritic?.residualFindings ?? []).map(f => `[structure] ${f}`)),
    ...(planCritic?.residualFindings ?? []),
  ]
  const planBodyStep = criticBodyStep(t.id, 'plan', planFindings, wd)
  const fin = await agent(
    `You are the PLAN-PHASE finalize worker for ${t.id}, in ${wd}. Follow the "action: advance → nextPhase == plan" steps of ${SKILL}.
1. Verify structure.md, plan.md, worktree.md exist and are non-empty under ${wd}/.qrspi/${t.id}/. If any missing/empty, return ok:false.
2. gt checkout ${t.id}/design; stage ONLY those three artifacts; create the ${t.id}/plan branch STACKED on ${t.id}/design with \`gt create\` (single commit "${t.id} [SP]: Plan — ${t.title}").${planBodyStep} Then submit the Plan PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`${reviewerFlags(r) ? ' (submit the reviewer flag EXACTLY as written — it is what surfaces the PR in the reviewer\'s Graphite queue)' : ''}.
3. BEST-EFFORT project Linear → "Plan Review" (WARN on failure, still ok:true if the PR was created).
Return: ok, prUrl, newStatus, summary.`,
    { label: `finalize-plan:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const out = finResult(t, fin, 'advance:plan')
  if (out.action === 'advance:plan' && fin && fin.ok && planFindings.length) {
    out.summary = `${out.summary} [critic: ${planFindings.length} residual finding(s) in PR body]`
  }
  return out
}

// ---------------------------------------------------------------------------
// HELPER: runCoherenceCritic — the whole-stack coherence pass at the planning→
// implementation seam (RUS-58, AC2). Runs ONCE before the slice loop, judging the six
// frozen planning artifacts together for intent drift, and returns { ok, residualFindings }
// in the SAME shape runCriticLoop uses (so doImplementation carries findings the same way).
//   - There is NO reviser at the seam: per Decision 3 the disposition is surface-only — the
//     coherence pass never rewrites an upstream artifact (that high-blast-radius path is the
//     reviewer-initiated `reset`, not this critic). So the loop converges (pass) or carries
//     the findings; a `revise`/`cap_reached` next_action action both terminate by carrying
//     the current verdict's findings (there is nothing to rewrite to improve them).
//   - The convergence decision is the EXISTING tested next_action (via criticDecision),
//     NOT re-derived here (Decision 5 spirit).
//   - A critic SPAWN failure (verdict === null) or a failed decision returns ok:false, which
//     doImplementation maps to skip(...) (no silent ship; Risk Register row 2).
// `paths` is the resolved six-artifact path object; `maxRounds` is config.coherence.maxRounds.
async function runCoherenceCritic(id, paths, maxRounds) {
  const rounds = Number.isInteger(maxRounds) && maxRounds > 0 ? maxRounds : 2
  for (let round = 0; round < rounds; round++) {
    const verdict = await agent(
      `You are the qrspi-coherence-critic for ${id}, round ${round + 1}/${rounds}. Judge the WHOLE planning stack for intent drift — every ticket obligation must still be coherently carried from the ticket through questions, research, design, structure, and the plan.
TICKET_CONTENT_PATH = ${paths.ticket}
QUESTIONS_PATH = ${paths.questions}
RESEARCH_PATH = ${paths.research}
DESIGN_PATH = ${paths.design}
STRUCTURE_PATH = ${paths.structure}
PLAN_PATH = ${paths.plan}
Read all six paths and return { pass, findings } per the schema.`,
      { label: `coherence-critic:${id}#${round + 1}`, phase: 'Critic', agentType: 'qrspi-coherence-critic', schema: CRITIC_VERDICT_SCHEMA }
    )
    if (verdict === null) {
      log(`  ${id}: coherence critic round ${round + 1} failed/skipped — stopping this ticket`)
      return { ok: false, residualFindings: [] }
    }
    const passed = verdict.pass === true
    const findings = Array.isArray(verdict.findings) ? verdict.findings : []
    log(`  ${id}: coherence critic round ${round + 1}/${rounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)

    const decision = await criticDecision([verdict], round, rounds)
    if (!decision) {
      log(`  ${id}: coherence critic-loop decision failed to compute — stopping this ticket`)
      return { ok: false, residualFindings: [] }
    }
    if (decision.action === 'converged') {
      log(`  ${id}: coherence critic CONVERGED at round ${round + 1}`)
      return { ok: true, residualFindings: [] }
    }
    // revise OR cap_reached: there is no upstream reviser at the seam (surface-only, Decision 3),
    // so both terminate by carrying the current findings to the slice-1 PR body.
    log(`  ${id}: coherence critic ${decision.action} at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to slice-1 PR body (surface-only)`)
    return { ok: true, residualFindings: decision.residual_findings }
  }
  log(`  ${id}: coherence critic loop exhausted ${rounds} round(s) without converging`)
  return { ok: true, residualFindings: [] }
}

// ---------------------------------------------------------------------------
// HELPER: runSliceCritic — the per-slice edge critic inside doImplementation's slice loop
// (RUS-58, AC1/AC3). Judges ONE slice's diff (${diffBase}..${diffHead}) as a faithful
// implementation of that slice's plan/structure rubric, with the SINGLE-CRITIC path (NO panel
// — AC3: no `lenses`). Returns { ok, residualFindings } (same shape as runCriticLoop):
//   - Spawns the EXISTING qrspi-critic agent against the slice diff; the rubric is the slice's
//     planSlice + structureSlice (passed inline). The critic reads the diff via the worker's
//     git/gt access — it is given the Graphite diff range and the rubric text.
//   - On a non-pass verdict, routes to the EXISTING qrspi_revise_amend.py --branch ${id}/slice-N
//     (Decision 2 / Q7), then re-critiques on the next round.
//   - The converge/revise/cap decision is the EXISTING tested next_action via criticDecision
//     (Decision 5 — NOT re-implemented); cap_reached is ship-with-disclosure (carry findings).
//   - A critic or revise-amend SPAWN failure (null) ⇒ ok:false ⇒ doImplementation maps it to
//     skip(...) (no silent ship; Risk Register row 2).
async function runSliceCritic(t, r, wd, sliceN, dec, planSlice, structureSlice, maxRounds) {
  const rounds = Number.isInteger(maxRounds) && maxRounds > 0 ? maxRounds : 2
  const id = t.id
  const branch = `${id}/slice-${sliceN}`
  const diffRange = `${dec.diffBase}..${dec.diffHead}`
  const rubric = `PLAN_SLICE (the planned steps this slice must faithfully implement):\n${planSlice}\n\nSTRUCTURE_SLICE (the types/contracts/slice definition):\n${structureSlice}`

  for (let round = 0; round < rounds; round++) {
    const verdict = await agent(
      `You are the qrspi-critic for ${id} slice ${sliceN}, round ${round + 1}/${rounds}, judging an IMPLEMENTATION slice as a faithful derivation of its planned steps. Your cwd is ${wd}.
1. Read the slice's code diff with: \`gt checkout ${branch} --no-interactive\` then \`git diff ${diffRange}\` (the Graphite parent..this-slice range). This diff is the produced artifact you judge.
2. The rubric (the upstream you judge against) is the slice's plan + structure below:
${rubric}
Judge the EDGE: does the slice diff faithfully implement every planned step / contract for this slice — preserved, correctly built, or explicitly resolved? A planned step silently dropped, contradicted, or distorted is a finding. Do NOT judge prose; judge whether the code realizes the plan. Return { pass, findings } per the schema (each finding names the specific planned step/contract the diff drops/contradicts/distorts). Do NOT amend or commit anything — you only judge.`,
      { label: `slice-critic:${id}#${sliceN}r${round + 1}`, phase: 'Critic', agentType: 'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA }
    )
    if (verdict === null) {
      log(`  ${id}: slice ${sliceN} critic round ${round + 1} failed/skipped — stopping this ticket`)
      return { ok: false, residualFindings: [] }
    }
    const passed = verdict.pass === true
    const findings = Array.isArray(verdict.findings) ? verdict.findings : []
    log(`  ${id}: slice ${sliceN} critic round ${round + 1}/${rounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)

    const decision = await criticDecision([verdict], round, rounds)
    if (!decision) {
      log(`  ${id}: slice ${sliceN} critic-loop decision failed to compute — stopping this ticket`)
      return { ok: false, residualFindings: [] }
    }
    if (decision.action === 'converged') {
      log(`  ${id}: slice ${sliceN} critic CONVERGED at round ${round + 1}`)
      return { ok: true, residualFindings: [] }
    }
    if (decision.action === 'cap_reached') {
      log(`  ${id}: slice ${sliceN} critic CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to the slice PR body (ship-with-disclosure)`)
      return { ok: true, residualFindings: decision.residual_findings }
    }
    // action === 'revise': route to the existing qrspi_revise_amend.py to fix the slice IN PLACE,
    // then re-critique the amended branch on the next round.
    log(`  ${id}: slice ${sliceN} critic REVISE at round ${round + 1} — amending the slice to address findings`)
    const rev = await agent(
      `You are the SLICE REVISER for ${id} slice ${sliceN}, in ${wd}. The per-slice edge critic judged the slice diff (${diffRange}) and found it does NOT yet faithfully implement its planned steps.
FINDINGS (each names a specific planned step/contract the slice diff dropped/contradicted/distorted):
${findings.map((f, i) => `  ${i + 1}. ${f}`).join('\n')}
Do:
1. \`gt checkout ${branch} --no-interactive\`.
2. Edit the slice's code in ${wd} to resolve EVERY finding while keeping everything already correct (do NOT touch other slices' files or any phase artifact beyond what the findings require).
3. Stage your edits AND amend the slice commit IN PLACE by running EXACTLY this one self-locating command verbatim — no path edits, no alternatives:
     python3 ${engineCmdFor(r, 'scripts/qrspi_revise_amend.py')} --ticket ${id} --branch ${branch}
   It checks out the branch, stages every edit (excluding caches), amends with \`gt modify\` keeping the EXACT subject+trailers, and VERIFIES the amend captured your changes (it FAILS if nothing was staged or the tree is left dirty). It prints JSON { ok, branch, oldOid, newOid, dirty, error? }. If it prints ok:false, return ok:false — HARD STOP; do NOT hand-run gt modify/git add/git commit/git reset to work around it, and never run a bare \`gt modify --no-interactive\` (without staging it amends an empty index and silently drops your edits).
Return: ok, summary (one line naming what you changed), or ok:false with the verbatim reason.`,
      { label: `slice-revise:${id}#${sliceN}r${round + 1}`, phase: 'Critic', schema: WORKER_SCHEMA }
    )
    if (!rev || rev.ok !== true) {
      log(`  ${id}: slice ${sliceN} revise-amend round ${round + 1} failed — ${rev?.error ?? 'no result'} (stopping this ticket)`)
      return { ok: false, residualFindings: [] }
    }
  }
  log(`  ${id}: slice ${sliceN} critic loop exhausted ${rounds} round(s) without converging`)
  return { ok: true, residualFindings: [] }
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

  // --- RUS-58: whole-stack coherence pass at the planning→implementation seam (T12-T16).
  // The implementation critic is OPT-IN: readCriticsConfig resolves EVERY phase via
  // scripts/qrspi_critics_config.py; .implementation carries { enabled, maxRounds, coherence:
  // { enabled, maxRounds } } and defaults OFF when the block is absent, so this whole section is a
  // no-op (the byte-for-byte-unchanged path) unless the operator turns it on. `coherenceFindings`
  // is carried in memory through doImplementation and surfaced into the SLICE-1 PR body later
  // (AC2: no slice commit exists yet at the seam).
  const implCriticCfg = (await readCriticsConfig('Implementation')).implementation
  let coherenceFindings = []
  // RUS-75: cross-iteration accumulator of each slice's per-slice edge-critic residual findings,
  // keyed by 1-based slice number. Populated only on the enabled path (implCriticCfg.enabled);
  // surfaced into the matching slice-N PR body in the finalize worker. Stays {} when disabled.
  const perSliceFindings = {}
  if (implCriticCfg.coherence.enabled) {
    // T13: resolve the six coherence inputs inline — the five frozen planning artifacts via
    // art(wd,id,name) + the ticket content via r.ticketContentPath (mirrors the doDesign panel).
    const coherencePaths = {
      ticket: r.ticketContentPath,
      questions: art(wd, t.id, 'questions.md'),
      research: art(wd, t.id, 'research.md'),
      design: art(wd, t.id, 'design.md'),
      structure: art(wd, t.id, 'structure.md'),
      plan: art(wd, t.id, 'plan.md'),
    }
    // T14: fail-closed guard. The resolver's `existing` flags are the authoritative presence
    // check for the five planning artifacts (it emits them in the envelope); r.ticketContentPath
    // is resolved by construction before any advance. A missing/empty input ⇒ skip(...) (no
    // critic spawn against an incomplete stack; Risk Register row 3, Decision 6).
    const ex = r.existing || {}
    const missing = ['questions', 'research', 'design', 'structure', 'plan']
      .filter(k => !ex[k])
    if (!r.ticketContentPath) missing.push('ticket')
    if (missing.length) {
      log(`  ${t.id}: coherence pass enabled but inputs missing/empty [${missing.join(', ')}] — skipping ticket`)
      return skip(t, r.decision, `Coherence inputs missing/empty: ${missing.join(', ')}.`)
    }
    // T15: run the coherence critic ONCE at the seam (converges via next_action up to
    // coherence.maxRounds), carrying residual findings in memory for the slice-1 PR body.
    log(`  ${t.id}: implementation coherence pass ENABLED — maxRounds ${implCriticCfg.coherence.maxRounds}`)
    const coh = await runCoherenceCritic(t.id, coherencePaths, implCriticCfg.coherence.maxRounds)
    // T16: a coherence-critic SPAWN failure (ok:false) ⇒ skip(...), mirroring the implement/
    // commit failure paths (no silent ship; Risk Register row 2, Q8).
    if (!coh.ok) {
      return skip(t, r.decision, 'Coherence critic spawn failed; stopped without implementing.')
    }
    coherenceFindings = coh.residualFindings
  }

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

    // RUS-75 (AC1/AC2/AC3/AC6): per-slice edge critic, run IN-LOOP after this slice's commit.
    // Gated by implCriticCfg.enabled so the disabled path stays byte-for-byte unchanged (AC5).
    // alreadyCommitted slices `continue` above and never reach here; `decide` also returns
    // run:false for them as a second guard (single-slice tickets likewise skip via skipReason).
    if (implCriticCfg.enabled) {
      const dec = await sliceCriticDecide(t, setup, s.n)
      if (!dec) {
        log(`  ${t.id}: slice ${s.n} critic decide failed — stopping (prior slices preserved)`)
        return skip(t, r.decision, `Slice ${s.n} critic decide failed; stopped without shipping.`)
      }
      if (!dec.run) {
        // Critic-SKIP (NOT a ticket skip()): the slice still ships. Mirrors the coherence
        // "skipping" log lines, naming the reason the decide shim returned.
        log(`  ${t.id}: slice ${s.n} critic skipped (${dec.skipReason ?? 'no reason'}) — slice ships unjudged`)
      } else {
        const sc = await runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds)
        if (!sc.ok) {
          return skip(t, r.decision, `Slice ${s.n} critic spawn failed; stopped without shipping.`)
        }
        perSliceFindings[s.n] = sc.residualFindings
      }
    }
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

  // RUS-75 (AC4/AC4b): build the per-slice / coherence findings-splice steps for the finalize
  // worker, amended lowest-N-first, BEFORE the existing pr-summary splice + the single
  // `gt submit --stack`. Skip-on-empty is CALLER-SIDE and MANDATORY: a bucket whose findings are
  // empty (or whitespace-only) produces NO instruction, so qrspi_critic_body.py is never invoked
  // for it (its empty handling is message-level only; set_findings still runs gt checkout + gt
  // modify, which needlessly restacks — OQ3). The whole block is dormant when implCriticCfg is
  // off: coherenceFindings stays [] (gated by coherence.enabled) and perSliceFindings stays {}
  // (populated only on the enabled path), so the disabled transcript is byte-for-byte unchanged.
  const nonEmpty = (arr) => Array.isArray(arr) && arr.filter(f => String(f).trim() !== '').length > 0
  const spliceTargets = []
  // (a) coherence findings → slice-1 (no slice commit existed at the seam; AC2).
  if (nonEmpty(coherenceFindings)) {
    spliceTargets.push({ slice: 1, kind: 'coherence', findings: coherenceFindings })
  }
  // (b) per-slice residual findings, lowest-N-first.
  for (const n of Object.keys(perSliceFindings).map(Number).sort((a, b) => a - b)) {
    if (nonEmpty(perSliceFindings[n])) {
      spliceTargets.push({ slice: n, kind: 'per-slice', findings: perSliceFindings[n] })
    }
  }
  // Ordering for slice 1: coherence first, then slice-1 per-slice findings, then (below) pr-summary.
  const findingsSpliceStep = spliceTargets.length === 0 ? '' :
    `\n1b. Splice the edge-critic residual findings into the matching slice commit MESSAGES, in EXACTLY this order, EACH before the pr-summary splice in step 2 — for EACH item run EXACTLY the two commands verbatim (no path edits, no alternatives); if any prints ok:false, return ok:false — HARD STOP:\n` +
    spliceTargets.map((tg, i) => {
      const stageFile = `/tmp/phase-stage/${t.id}/critic-findings-slice-${tg.slice}-${tg.kind}.json`
      return `   (${i + 1}) [${tg.kind} findings → slice ${tg.slice}] write this EXACT JSON verbatim (a JSON array of strings) to ${stageFile}: ${JSON.stringify(tg.findings)} ; then run: python3 ${engineCmdFor(r, 'scripts/qrspi_critic_body.py')} --ticket ${t.id} --phase slice --slice ${tg.slice} --findings-file ${stageFile} (it appends the findings to the ${t.id}/slice-${tg.slice} commit message via gt modify, self-locating).`
    }).join('\n')

  phase('Finalize')
  const fin = await agent(
    `You are the implementation finalize worker for ${t.id}, in ${wd}. Follow the SKILL "advance → implementation" submit steps. PR bodies are seeded at Graphite CREATION from the commit message (\`gt submit\` has no body flag and seeds the body at creation only), so author the body via the commit message as below — this is the deterministic default. A post-hoc body correction, if ever needed, uses \`gh api repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@<file>\` (NOT \`gh pr edit\`, which can abort on the Projects-classic GraphQL bug). Do:
1. Amend pr-summary.md into the last slice commit as the durable artifact (git add .qrspi/${t.id}/pr-summary.md && gt modify --no-interactive).${findingsSpliceStep}
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
    `You are the submit worker for ${t.id} (active phase: ${r.decision.phase}), in ${r.worktreeDir}. Follow the "action: submit" steps of ${SKILL}: the phase branch exists but its PR was not opened. Verify the phase's artifacts are present+non-empty (if any are missing AND cannot be produced, return ok:false — never fabricate). This path CREATES the PR, and PR bodies are seeded at Graphite creation from the commit message (\`gt submit\` has no body flag and seeds the body at creation only) — the deterministic default; a post-hoc body correction, if needed, is \`gh api … pulls/<N> -X PATCH -F body=@<file>\`, not \`gh pr edit\`. If the active phase is IMPLEMENTATION, FIRST splice pr-summary.md into the slice-1 commit message by running EXACTLY, verbatim: \`python3 ${engineCmdFor(r, 'scripts/qrspi_pr_body.py')} --ticket ${t.id} --slice 1\` (if it prints ok:false, return ok:false — HARD STOP). Then submit the PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)} --no-edit --no-interactive\` (add --stack for implementation)${reviewerFlags(r) ? ' — submit the reviewer flag EXACTLY as written, it surfaces the PR in the reviewer\'s Graphite queue' : ''} and BEST-EFFORT project the matching Linear review status. (The body is seeded from the commit message at creation — no gh body edit is needed here.)
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
// ACTION: revise  (UNIFIED feedback handler — subsumes the former respond_comment)
// ===========================================================================
// AUTONOMOUS. The resolver emits `revise` when a frontier phase PR carries a formal
// CHANGES_REQUESTED AND/OR >=1 unaddressed reviewer comment. The decision carries:
//   - r.commentTargets    the unaddressed reviewer comments to evaluate per-intent
//   - r.decision.changeRequested  whether a formal change request is present
// The worker runs in two coherent steps within ONE pass (this is the unification — comment
// handling no longer slips to a separate later run):
//   1. PER-COMMENT INTENT ENGINE — for each commentTarget, an honest peer-reviewer worker
//      ANSWERs / APPLYs (edit + amend in place) / DECLINEs, and posts an in-thread reply.
//   2. FORMAL CHANGE REQUEST (only when changeRequested) — a worker addresses any remaining
//      change-request feedback (e.g. the review SUMMARY body, which is not a reply-able
//      thread comment), amends if there is anything left to change, then ALWAYS re-requests
//      review. Re-requesting flips reviewDecision back to REVIEW_REQUIRED — the loop-safe
//      termination signal that lets the next pass return `wait` instead of re-firing.
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

  if (!changeRequested && targets.length === 0) {
    // The resolver only emits revise with a change request and/or comment targets, so this
    // is a defensive guard, not an expected path.
    return skip(t, d, 'revise with neither a change request nor comment targets; nothing to do.')
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

  // --- Step 2a: comment-only path (no formal change request) — replies are the whole job.
  // Do NOT re-request review: the PR may be APPROVED, and we must not disturb it.
  if (!changeRequested) {
    const summary = `Responded to ${answered.length}/${targets.length} reviewer comment(s) on the ${d.phase} PR`
      + `${answered.some(a => a.applied) ? ` (${answered.filter(a => a.applied).length} applied as changes)` : ''}`
      + `${failures.length ? `; ${failures.length} failed` : ''}.`
    return { ticketId: t.id, action: 'revise', summary, prUrl: undefined }
  }

  // --- Step 2b: formal change request — address the review summary / remaining feedback,
  // amend only if there is something left to change, then ALWAYS re-request review.
  const fin = await agent(
    `You are the REVISE worker for ${t.id} (frontier phase: ${d.phase}), in ${r.worktreeDir}. A formal CHANGES_REQUESTED landed on the ${d.phase} PR. ${targets.length ? `The reviewer's INLINE/TOP-LEVEL comments have ALREADY been engaged and replied to in a prior step — do NOT re-reply to them; focus on the review SUMMARY body and any change-request feedback not tied to a specific comment.` : ''} Address it AUTONOMOUSLY, following the "action: revise" steps of ${SKILL}, with these REQUIRED adaptations:
- DO NOT attempt to RESOLVE review threads (only the reviewer can mark a thread resolved). Reading feedback via \`gh pr view\`/\`gh api graphql\` queries is fine. Thread resolution is the reviewer's job — leave threads as-is.
- Stay WITHIN the ${d.phase} phase only — never edit a downstream phase's artifacts (that is \`reset\`, not revise).
Steps:
1. Identify the branch(es) to fix. For design/plan: \`gt checkout ${t.id}/${d.phase} --no-interactive\`. For implementation: query the ticket's slice PRs (\`gh pr list --head ${t.id}/slice-... \` or graphql) and address EVERY slice whose PR is CHANGES_REQUESTED, lowest slice number first (changes restack upward).
2. Read the change request: the CHANGES_REQUESTED review SUMMARY body AND any unresolved thread comments not already addressed (READ-only queries per the SKILL).
3. If there is remaining feedback to act on, address it by editing the phase's artifacts/code in ${r.worktreeDir}. If the prior per-comment step already applied every needed change and NOTHING further remains, do NOT invent an edit — skip straight to step 5 (re-request review).
4. When you made edits, stage them AND amend the phase commit IN PLACE by running EXACTLY this one self-locating command verbatim (no path edits, no alternatives) — for design/plan run it once; for implementation run it once per CHANGES_REQUESTED slice branch, lowest slice number first:
   \`python3 ${engineCmdFor(r, 'scripts/qrspi_revise_amend.py')} --ticket ${t.id} --branch <BRANCH>\` where <BRANCH> = \`${t.id}/${d.phase}\` for design/plan, or \`${t.id}/slice-<N>\` for an implementation slice.
   The script checks out the branch, stages every edit you made (excluding caches), amends the commit with \`gt modify\` keeping its EXACT subject+trailers (it does NOT rename the subject), and VERIFIES the amend captured your changes — it FAILS if nothing was staged or the tree is left dirty. It prints JSON { ok, branch, oldOid, newOid, dirty, error? }. If ANY invocation prints ok:false, return ok:false — HARD STOP; do NOT hand-run \`gt modify\`/\`git add\`/\`git commit\`/\`git reset\` to work around it. Never run a bare \`gt modify --no-interactive\` here: without staging it amends an empty index and silently drops your edits. (If step 3 determined nothing further needs changing, SKIP this step entirely — do not run the amend script with no staged edits.)
5. Re-request review so the stale CHANGES_REQUESTED is cleared (ALWAYS do this, whether or not you amended in step 4): \`gt submit --publish --no-edit --rerequest-review${reviewerFlags(r)}${d.phase === 'implementation' ? ' --stack' : ''} --no-interactive\`. (Re-requesting review clears the change request; no gh body edit is involved here.)
6. BEST-EFFORT keep Linear in the current review status (a failed Linear write is a WARN, still return ok:true if review was re-requested).
Return: ok, prUrl, newStatus, summary (name what you changed — or state that the prior comment replies covered it and you only re-requested review — and confirm review was re-requested; if you could not address the feedback, return ok:false with the verbatim reason — never fabricate a fix).`,
    { label: `revise:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  const out = finResult(t, fin, `revise:${d.phase}`)
  if (out && commentSummary) {
    out.summary = `${out.summary || ''} Also ${commentSummary}.`.trim()
  }
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
      `You are the PEER-REVIEWER worker for ${t.id} (phase: ${d.phase}), in ${r.worktreeDir}. A reviewer left a comment on the ${d.phase} PR and the bot has NOT yet replied to it. Engage it as an honest peer reviewer — you may ANSWER it, APPLY a sound suggested change, or DECLINE it with a concrete rationale. You are HONESTY-BOUND: never fabricate a fact, a fix, or agreement; answer only from the actual artifacts/code/PR state.

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
    `You are the LAND worker for ${t.id}, in ${r.worktreeDir}. Every PR in the stack is approved+clean. Follow the "action: land" steps of ${SKILL}: ensure the stack is current (gt submit --publish --stack), merge bottom-up (gt merge --no-interactive — NOT --confirm, which forces a prompt --no-interactive cannot satisfy), then BEST-EFFORT project Linear → "Done". Do NOT remove the worktree, delete branches, or run \`gt sync --force\` — a separate deterministic cleanup step (qrspi_cleanup.py) handles all reaping AFTER the merge. Treat any infrastructure/merge error as a HARD STOP (return ok:false, and put the VERBATIM conflict/merge reason in the \`error\` field — NOT only in \`summary\`; the orchestrator surfaces \`error\` to the operator).
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
        log(`  ${t.id}: skipped (${a})`)
    }
    results.push(res)
    // RUS-68: a land whose cleanup left stranded origin refs (ok:true + non-empty
    // failedRemotes) requests a Reconcile RETRY rather than a halt — so we DON'T mark it
    // `processed`, which is the exact set runReconciliation excludes. Leaving it out lets
    // this run's Reconcile pass (when enabled) re-attempt the prune; otherwise the
    // (still-present) origin refs keep it in the backlog for a later run's pass.
    if (!res.reconcileRetry) processed.add(t.id)
    log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}${res.reconcileRetry ? ' (Reconcile retry scheduled — stranded remotes)' : ''}`)
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
