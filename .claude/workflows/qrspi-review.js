export const meta = {
  name: 'qrspi-review',
  description: 'Deterministic, propose-only on-demand review engine for the /review-* family: fan out the phase review panel ONCE (round 0, no revise loop) over a scratch copy of the phase artifact against the real codebase, then post one axis-enumerated advisory synopsis comment to the phase PR and append a ledger row — WITHOUT mutating the PR branch.',
  whenToUse: 'Invoked by the thin /review-design, /review-plan, /review-implementation SKILL wrappers (which pass {ticket, phase}). It replaces the per-command multi-round revise loop with a single deterministic round-0 panel pass. Advisory only — it never changes Linear status or advances the PR-gated lifecycle.',
  phases: [
    { title: 'Resolve', detail: 'worktree + phase PR number + head SHA + scratch-copy artifact + stage ticket text + resolve the *-review lens model override (worker agent)' },
    { title: 'Panel', detail: 'Fan out the phase DEFAULT_REVIEW_* lenses ONCE (round 0) over the scratch artifact + real codebase; the *-review (node-validity) lens carries the configured model override' },
    { title: 'Readiness', detail: 'design-phase ONLY: a single post-panel decision-readiness lens (terminal-advisory; feeds the synopsis, never a loop)' },
    { title: 'Synopsis', detail: 'synthesize ONCE → terminal action (converged on round-0 pass, else exhausted) → render synopsis → post advisory comment → append ledger row (agreement {}) → re-assert PR head SHA unchanged (worker agent)' },
  ],
}

// ---------------------------------------------------------------------------
// Why this exists (RUS-93 Slice 3)
// ---------------------------------------------------------------------------
// The /review-* family was three near-duplicate ~280-line SKILL.md procedures, each
// describing a multi-round critic REVISE loop (rounds 0..MAX_ROUNDS-1, a shared
// non-producer reviser rewriting a scratch copy, an agreement reducer, a design-only
// decision-readiness lens). RUS-93 collapses that to ONE deterministic engine:
//
//   * NO revise loop. The panel runs exactly ONCE (round 0). The terminal action is
//     `converged` when the round-0 reduced verdict passes, else `exhausted` (both are
//     in qrspi_critic_metrics.VALID_TERMINAL_ACTIONS; `revise` is non-terminal and is
//     rejected by build_record, which is exactly why it can never be emitted here).
//     The shared reviser (qrspi-critic-reviser) is therefore DORMANT for /review-* —
//     it is no longer spawned. Its qrspi_critic_loop MODULE is RETAINED (still imported
//     by qrspi_critic_synthesize for _coerce_verdict/parse_critic_verdict), only its
//     reviser-spawn call site is gone.
//
//   * Agreement is DROPPED (F2). qrspi_review_agreement.compute is NOT invoked; NO
//     "Agreement" line is rendered; the ReviewRecord's `agreement` is passed `{}` purely
//     to satisfy build_record's positional arg.
//
//   * The *-review (node-validity) lens model is now WIRED (Slice 2). The engine reads
//     resolve_review_lens_model(critics) ONCE and passes the resolved id as the `model`
//     key on the `*-review` lens agent(...) spawn ONLY — the other lenses inherit the
//     session model. The lens agent frontmatter stays model-less (the override is
//     supplied at spawn).
//
// PROPOSE-ONLY INVARIANT. This engine captures the phase PR head SHA before the panel
// and re-asserts it unchanged at the end. The ONLY GitHub writes it issues are (a) the
// single advisory comment via scripts/qrspi_comment_reply.py and (b) the ledger append
// via scripts/qrspi_metrics_append.py (a local file write). It issues NO branch-mutating
// command — no gt submit/modify/create/restack, no git push, no gh pr edit/merge/close/
// ready, no write-verb gh api on pulls/git refs. Read-only gh pr view/list and the
// gh pr comment write are the only gh surface it touches.
//
// ENGINE<->PYTHON SEAM (plan step 14 decision — recorded here, no fixtures added).
// Like qrspi-batch.js / qrspi-teeth-eval.js, the JS sandbox cannot run python or touch
// the filesystem, so EVERY python call is handed to a WORKER agent as a literal command
// STRING and the worker returns a STRUCTURED ENVELOPE validated by a JSON schema at the
// agent() boundary. This engine introduces NO new JS function that PARSES python stdout
// into a data structure (the existing scripts/fixtures/contract_seam/ family covers the
// batch's JS parse functions — parseResolveEnvelope, parseConfigEnvelope, etc. — which
// CONSUME python stdout; this engine has no such new parser). The deterministic python
// transforms it drives (qrspi_critic_synthesize.synthesize, qrspi_review_synopsis
// .render_synopsis / .partition_decision_readiness / .ledger_row_fields,
// qrspi_review_record.build_record) are ALREADY stdlib-unit-tested under
// scripts/run_tests.py. So there is no JS<->python parser seam to fixture here, and
// scripts/fixtures/contract_seam/review/ is intentionally NOT created (plan steps
// 23-24 are conditional on a seam existing; it does not).
// ---------------------------------------------------------------------------

// ENGINE_ROOT / engineCmd — the directory the QRSPI engine (this workflow + its scripts/
// + agents/) lives in, mirroring qrspi-batch.js / qrspi-teeth-eval.js. Env override first
// (future plugin install), else the runner's cwd, else '.'.
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) ||
  '.'
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`

// engineCmdFor(r, rel) — engine path for a worker running in a WORKER cwd (a worktree),
// where engineCmd's `.` fallback re-resolves against the worker's cwd, not the runner's.
// Derive the host checkout root deterministically from the resolve envelope's
// worktreeDir (`<root>/.worktrees/<id>`) — the engine scripts live at <root>/scripts/ on
// trunk regardless of what a worktree HEAD relocated. Precedence mirrors qrspi-batch.js:
// CLAUDE_PLUGIN_ROOT -> host root from worktreeDir -> ENGINE_ROOT.
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

// ---------------------------------------------------------------------------
// Per-phase configuration (sourced from DEFAULT_REVIEW_*_LENSES in
// scripts/qrspi_critics_config.py — kept in sync with that single source of truth).
// ---------------------------------------------------------------------------
//  - key            : the input.phase discriminator the SKILL wrappers pass.
//  - recordPhase    : the `phase` label embedded in the ReviewRecord / ledger row.
//  - agentPrefix    : lens id -> agentType is `${agentPrefix}-${lensId}`.
//  - branchSuffix   : the phase branch suffix; the PR is derived from this head.
//  - artifact       : the tracked artifact file scratch-copied under review.
//  - reviewLens     : the node-validity lens id that (a) carries the model override and
//                     (b) NEVER receives TICKET_CONTENT_PATH (research+code-only).
//  - ticketLenses   : the lens ids that DO receive TICKET_CONTENT_PATH.
//  - lenses         : the full ordered panel (matches DEFAULT_REVIEW_*_LENSES).
//  - decisionReadiness : true ONLY for design — the terminal-advisory post-panel lens.
//  - stateAllPr     : true for impl — derive the top-slice PR with `gh pr list --state all`
//                     so a partially-landed stack still resolves the frontier PR.
const PHASES = {
  design: {
    recordPhase: 'design',
    agentPrefix: 'qrspi-design-critic',
    branchSuffix: 'design',
    artifact: 'design.md',
    // The phase-specific subject var every lens reads as "the artifact under review"
    // (the lens defs say DESIGN_PATH/PLAN_PATH/IMPL_PATH, never the generic ARTIFACT_PATH).
    // The engine emits `${subjectVar} = ${scratch}` so the panel reads the scratch copy.
    subjectVar: 'DESIGN_PATH',
    reviewLens: 'design-review',
    ticketLenses: ['completeness', 'edge-alignment'],
    lenses: ['completeness', 'internal-consistency', 'edge-alignment', 'simplicity', 'design-review'],
    decisionReadiness: true,
    stateAllPr: false,
  },
  plan: {
    recordPhase: 'plan',
    agentPrefix: 'qrspi-plan-critic',
    branchSuffix: 'plan',
    artifact: 'plan.md',
    subjectVar: 'PLAN_PATH',
    reviewLens: 'plan-review',
    ticketLenses: ['plan-fidelity', 'plan-completeness'],
    lenses: ['plan-review', 'plan-fidelity', 'plan-completeness'],
    decisionReadiness: false,
    stateAllPr: false,
  },
  impl: {
    recordPhase: 'implementation',
    agentPrefix: 'qrspi-impl-critic',
    branchSuffix: null, // impl reviews the slice stack; the PR is the TOP slice (resolved by the worker)
    artifact: 'impl-log.md',
    subjectVar: 'IMPL_PATH',
    reviewLens: 'impl-review',
    ticketLenses: ['impl-fidelity', 'impl-completeness'],
    lenses: ['impl-review', 'impl-fidelity', 'impl-completeness'],
    decisionReadiness: false,
    stateAllPr: true,
  },
}

// --- schemas ---------------------------------------------------------------

// One lens verdict — identical to runCriticPanelLoop's / the teeth eval's lens contract.
// `nonBlockingNotes` is the OPTIONAL advisory channel threaded through to the synopsis.
const CRITIC_VERDICT_SCHEMA = {
  type: 'object',
  required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
    nonBlockingNotes: { type: 'array', items: { type: 'string' } },
  },
}

// The decision-readiness lens verdict (design phase only) — NOT the {pass, findings}
// shape. It is terminal-advisory: it feeds the synopsis, never the loop.
const DECISION_READINESS_SCHEMA = {
  type: 'object',
  required: ['lens', 'blockingDecisions', 'answerable'],
  properties: {
    lens: { type: 'string' },
    blockingDecisions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['question'],
        properties: { question: { type: 'string' }, rationale: { type: 'string' } },
      },
    },
    answerable: {
      type: 'array',
      items: { type: 'object', required: ['question'], properties: { question: { type: 'string' } } },
    },
  },
}

// The Resolve worker's envelope: all read-only setup folded into one deterministic
// worker so the engine types one invocation. `ok:false` is a hard stop.
const RESOLVE_SCHEMA = {
  type: 'object',
  required: ['ok'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    worktreeDir: { type: 'string' },
    pr: { type: 'number' },
    headSha: { type: 'string' },
    scratch: { type: 'string' }, // the scratch copy path the lenses read
    // reviewDecision was removed: it had no consumer after F2 dropped agreement.
    research: { type: 'string' },
    questions: { type: 'string' }, // "" when absent
    structure: { type: 'string' }, // "" when absent
    designPath: { type: 'string' }, // "" when absent (the design.md upstream, for plan/impl)
    planPath: { type: 'string' }, // "" when absent
    ticketContent: { type: 'string' }, // the staged ticket text path
    lensModel: { type: 'string' }, // the *-review model override, or "" when unset
  },
}

// The Synopsis/finalize worker's envelope.
const SYNOPSIS_SCHEMA = {
  type: 'object',
  required: ['ok', 'summary'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    terminalAction: { type: 'string' }, // converged | exhausted
    posted: { type: 'boolean' },
    shaUnchanged: { type: 'boolean' }, // the worker's self-report (advisory only)
    headShaAfter: { type: 'string' }, // the re-read head SHA; the ENGINE compares it === resolved.headSha
    summary: { type: 'string' },
  },
}

// --- args ------------------------------------------------------------------
// { ticket: string, phase: 'design'|'plan'|'impl' }. The thin SKILL wrappers pass both.
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args

const TICKET = (typeof input?.ticket === 'string' && input.ticket.trim() !== '')
  ? input.ticket.trim()
  : undefined
const PHASE_KEY = (typeof input?.phase === 'string') ? input.phase.trim() : undefined

if (!TICKET) {
  return { ok: false, error: 'qrspi-review: missing required input.ticket (Linear id, e.g. RUS-89)' }
}
const cfg = PHASE_KEY && PHASES[PHASE_KEY]
if (!cfg) {
  return { ok: false, error: `qrspi-review: input.phase must be one of design|plan|impl (got ${PHASE_KEY ?? 'undefined'})` }
}

// ===========================================================================
// RESOLVE — fold all read-only setup into one worker (the propose-only invariant's
// "before" snapshot): worktree + phase PR number + head SHA + scratch copy + staged
// ticket text + the *-review lens model override. Every python/gh op is handed to the
// worker as a literal command string; it returns the validated envelope above. ok:false
// (phase/PR missing, resolve error) is a HARD STOP — the engine does NOT fabricate a PR.
// ===========================================================================
phase('Resolve')

// Derive the phase PR head. impl reviews the slice STACK, so its PR is the TOP slice
// (the worker reads `tip`/`slices` from the resolve envelope and uses --state all so a
// partially-landed stack still resolves the frontier). design/plan derive from the
// fixed branch suffix.
const branchHeadInstr = cfg.stateAllPr
  ? `the TOP slice branch (the resolve envelope's \`tip\`, equivalently the last element of \`slices\`); derive its PR with \`gh pr list --head <tip> --state all --json number,state --jq '.[0]'\` (use --state all so a partially-landed stack still resolves the frontier PR). If \`slices\` is empty or no PR is found, return ok:false (there is no implementation to review).`
  : `the \`${TICKET}/${cfg.branchSuffix}\` branch; derive its PR with \`gh pr list --head ${TICKET}/${cfg.branchSuffix} --json number --jq '.[0]'\`. If no PR is found, return ok:false (the ${cfg.branchSuffix} phase PR does not exist).`

const resolved = await agent(
  `You are the RESOLVE worker for the /review-${PHASE_KEY} engine, ticket ${TICKET}. Your cwd is the MAIN repo root. Do EXACTLY these steps — no exploration, no path guessing, no extra commentary. Issue NO branch-mutating command (no gt/git push/gh pr edit/merge/close/ready) — this is a read-only setup pass.

1. Run the one-shot resolver and read its JSON envelope:
     python3 ${engineCmd('scripts/qrspi_resolve.py')} --ticket ${TICKET}
   Capture \`worktreeDir\` (= <repoRoot>/.worktrees/${TICKET}). The ${cfg.recordPhase} artifacts live under <worktreeDir>/.qrspi/${TICKET}/. ${cfg.stateAllPr ? 'Also capture `slices` (the ascending slice-branch list) and `tip` (the stack tip).' : 'Also capture `existing` — if the ' + cfg.branchSuffix + ' phase does not exist, return ok:false.'}

2. Derive the phase PR number from ${branchHeadInstr}
   Capture PR = .number.

3. Record the PR head SHA NOW (the propose-only "before" snapshot):
     gh pr view <PR> --json headRefOid --jq '.headRefOid'

4. Scratch-copy the artifact under review to a short token-free path (the panel reads the COPY, never the tracked file):
     mkdir -p /tmp/phase-stage/${TICKET}/review
     cp "<worktreeDir>/.qrspi/${TICKET}/${cfg.artifact}" /tmp/phase-stage/${TICKET}/review/${cfg.artifact}
   scratch = /tmp/phase-stage/${TICKET}/review/${cfg.artifact}

5. Stage the ticket text for the fidelity/coverage lenses: call mcp__linear__get_issue (id ${TICKET}); use the Write tool to write the issue title + a blank line + its full description VERBATIM to /tmp/phase-stage/${TICKET}/review/ticket.md. If the fetch fails or the description is empty, Write a short note there that the ticket text was unavailable and proceed (the lenses treat a missing ticket as "no stated AC to check against").

6. Resolve the *-review lens model override (Slice 2 reader) — run EXACTLY:
     python3 -c "import sys; sys.path.insert(0,'${engineCmd('scripts')}'); import qrspi_critics_config as c; cfg=c.read_config(c.REPO_ROOT); crit=cfg.get('critics') if isinstance(cfg,dict) else None; m=c.resolve_review_lens_model(crit); print(m if m else '')"
   Capture its stdout (stripped) as lensModel — the empty string when unset.

7. Record which optional upstream files EXIST under <worktreeDir>/.qrspi/${TICKET}/ (use \`test -f\` or \`ls\`): research.md (research), questions.md (questions), structure.md (structure), design.md (designPath), plan.md (planPath). For each, return its ABSOLUTE path if it exists, else "".

Return JSON: { ok:true, worktreeDir, pr:<number>, headSha:"<sha>", scratch:"<scratch path>", research:"<...or empty>", questions:"<...or empty>", structure:"<...or empty>", designPath:"<...or empty>", planPath:"<...or empty>", ticketContent:"/tmp/phase-stage/${TICKET}/review/ticket.md", lensModel:"<...or empty>" }. On any missing prerequisite (phase/PR absent, resolve error), return { ok:false, error:"<reason>" } — HARD STOP, do NOT fabricate a PR or path.`,
  { label: `review-resolve:${TICKET}`, phase: 'Resolve', schema: RESOLVE_SCHEMA }
)

if (!resolved || !resolved.ok) {
  const reason = resolved?.error ?? 'no result'
  log(`review-${PHASE_KEY} ${TICKET}: resolve failed — ${reason}`)
  return { ok: false, ticket: TICKET, phase: PHASE_KEY, error: `resolve failed: ${reason}` }
}

const wd = resolved.worktreeDir
log(`review-${PHASE_KEY} ${TICKET}: PR #${resolved.pr}, head ${String(resolved.headSha).slice(0, 12)}, lensModel=${resolved.lensModel || '(session default)'}`)

// The named PATH inputs every lens shares (only non-empty optional paths are threaded).
// The SUBJECT under review is bound to the phase-specific var the lens defs require
// (DESIGN_PATH/PLAN_PATH/IMPL_PATH — "This is your subject. Read it in full."), pointing
// at the scratch COPY (resolved.scratch). The generic ARTIFACT_PATH the lenses never read
// was a port regression; it is dropped. An upstream design/plan path is threaded ONLY when
// its var name differs from the subject var — so the design phase does not re-emit
// DESIGN_PATH at the tracked file (the design IS the subject), nor plan re-emit PLAN_PATH.
const sharedPaths = []
sharedPaths.push(`${cfg.subjectVar} = ${resolved.scratch}`)
sharedPaths.push(`CODEBASE_PATH = ${wd}`)
if (resolved.research) sharedPaths.push(`RESEARCH_PATH = ${resolved.research}`)
if (resolved.structure) sharedPaths.push(`STRUCTURE_PATH = ${resolved.structure}`)
if (resolved.designPath && cfg.subjectVar !== 'DESIGN_PATH') sharedPaths.push(`DESIGN_PATH = ${resolved.designPath}`)
if (resolved.planPath && cfg.subjectVar !== 'PLAN_PATH') sharedPaths.push(`PLAN_PATH = ${resolved.planPath}`)
if (resolved.questions) sharedPaths.push(`QUESTIONS_PATH = ${resolved.questions}`)
const sharedPathsBlock = sharedPaths.join('\n')

// ===========================================================================
// PANEL — fan out the phase panel ONCE (round 0, NO revise loop). The *-review
// node-validity lens carries the resolved model override (and NEVER the ticket text);
// the ticket lenses receive TICKET_CONTENT_PATH. A lens that fails to spawn (null
// verdict) cannot attest — fail CLOSED rather than treat a missing reply as a pass.
// ===========================================================================
phase('Panel')

const jobs = cfg.lenses.map((lensId) => async () => {
  const agentType = `${cfg.agentPrefix}-${lensId}`
  const getsTicket = cfg.ticketLenses.includes(lensId)
  const promptLines = [
    `You are the ${lensId} lens of the QRSPI ${cfg.recordPhase}-phase review panel (on-demand /review-${PHASE_KEY}, round 0).`,
    sharedPathsBlock,
  ]
  // TICKET_CONTENT_PATH is scoped — fidelity/coverage lenses ONLY, never the
  // node-validity *-review lens (it stays research+code-only).
  if (getsTicket && resolved.ticketContent) promptLines.push(`TICKET_CONTENT_PATH = ${resolved.ticketContent}`)
  promptLines.push(`Read every path provided above and judge the artifact under review (${cfg.subjectVar}) through your lens against the real source under CODEBASE_PATH. Return exactly one { pass, findings } verdict (you MAY also emit nonBlockingNotes). Do not write any files.`)
  // Wire the model override on the *-review (node-validity) lens ONLY (Slice 2). The
  // other lenses inherit the session model. When lensModel is "", omit `model` entirely.
  const opts = { label: `review:${PHASE_KEY}:${lensId}:${TICKET}`, phase: 'Panel', agentType, schema: CRITIC_VERDICT_SCHEMA }
  if (lensId === cfg.reviewLens && resolved.lensModel) opts.model = resolved.lensModel
  const verdict = await agent(promptLines.join('\n'), opts)
  return { lens: lensId, verdict }
})

const replies = await parallel(jobs)

const failed = replies.find(rp => !rp || rp.verdict === null)
if (failed) {
  log(`review-${PHASE_KEY} ${TICKET}: lens "${failed.lens}" failed to spawn — aborting (fail-closed)`)
  return { ok: false, ticket: TICKET, phase: PHASE_KEY, error: `lens "${failed.lens}" failed to spawn` }
}

// The round-0 pre-reduction per-lens verdict array — tagged with lens id, the source
// for BOTH the synthesize input and the axis-enumerated synopsis. Coerce defensively
// (the schema already validated shape; this normalizes optional fields).
const verdictArray = replies.map(rp => {
  const v = rp.verdict
  const entry = {
    lens: rp.lens,
    pass: v.pass === true,
    findings: Array.isArray(v.findings) ? v.findings : [],
  }
  if (Array.isArray(v.nonBlockingNotes)) entry.nonBlockingNotes = v.nonBlockingNotes
  return entry
})

// ===========================================================================
// READINESS — design phase ONLY: a single post-panel decision-readiness lens. It is
// terminal-advisory — its verdict feeds the synopsis and NEVER drives a loop (there is
// no loop). plan/impl skip it; render_synopsis receives null for decision-readiness.
// ===========================================================================
let decisionReadiness = null
if (cfg.decisionReadiness) {
  phase('Readiness')
  const drLines = [
    `You are the decision-readiness lens of the QRSPI design review (terminal-advisory — your verdict feeds the synopsis only, it drives no revise round).`,
    `DESIGN_PATH = ${resolved.scratch}`,
    `CODEBASE_PATH = ${wd}`,
  ]
  if (resolved.research) drLines.push(`RESEARCH_PATH = ${resolved.research}`)
  if (resolved.questions) drLines.push(`QUESTIONS_PATH = ${resolved.questions}`)
  if (resolved.ticketContent) drLines.push(`TICKET_CONTENT_PATH = ${resolved.ticketContent}`)
  drLines.push(`Partition the design's open questions into genuine human DECISIONS (blockingDecisions, each {question, rationale}) vs. answerable ones (answerable, each {question}). Return the DecisionReadinessVerdict { lens:"decision-readiness", blockingDecisions:[...], answerable:[...] }. Do not write any files.`)
  const dr = await agent(drLines.join('\n'),
    { label: `review:design:decision-readiness:${TICKET}`, phase: 'Readiness', agentType: 'qrspi-design-critic-decision-readiness', schema: DECISION_READINESS_SCHEMA })
  if (dr && dr.lens === 'decision-readiness') {
    decisionReadiness = {
      lens: 'decision-readiness',
      blockingDecisions: Array.isArray(dr.blockingDecisions) ? dr.blockingDecisions : [],
      answerable: Array.isArray(dr.answerable) ? dr.answerable : [],
    }
  } else {
    log(`review-design ${TICKET}: decision-readiness lens returned no verdict — synopsis omits its section`)
  }
}

// ===========================================================================
// SYNOPSIS — the deterministic Python pipeline + the comment write + the ledger append
// + the propose-only "after" SHA re-assert, all handed to ONE worker as literal command
// strings. NO revise loop: synthesize runs ONCE over the round-0 panel; the terminal
// action is `converged` when the reduced verdict passes, else `exhausted`. Agreement is
// DROPPED (F2): build_record gets agreement={} ONLY (qrspi_review_agreement.compute is
// NOT invoked), and NO Agreement line is rendered.
// ===========================================================================
phase('Synopsis')

// The fragile verdict JSON is written to a FILE by the worker (never the worker's stdout
// echo, which would HTML-escape `>` etc.), and the python steps READ that file via a
// sys.argv path. This deliberately AVOIDS `printf ... | python3 - <<PY` — a pipe AND a
// heredoc both redirect stdin, the heredoc wins the fd, so `json.load(sys.stdin)` would
// read the SCRIPT, not the piped JSON (verified broken). File-arg reads are unambiguous.
const verdictJson = JSON.stringify(verdictArray)
const decisionReadinessJson = JSON.stringify(decisionReadiness) // "null" when absent
const reviewDir = `/tmp/phase-stage/${TICKET}/review`
const verdictFile = `${reviewDir}/verdicts-${cfg.recordPhase}.json`
const drFile = `${reviewDir}/decision-readiness-${cfg.recordPhase}.json`
const synopsisFile = `${reviewDir}/synopsis-${cfg.recordPhase}.md`
const recordFile = `${reviewDir}/record-${cfg.recordPhase}.json`
const actionFile = `${reviewDir}/terminal-action-${cfg.recordPhase}.txt`
const advisoryHeader = `## Advisory ${cfg.recordPhase} review (propose-only — no branch changes)`

const fin = await agent(
  `You are the SYNOPSIS/finalize worker for the /review-${PHASE_KEY} engine, ticket ${TICKET}, PR #${resolved.pr}. Your cwd is the MAIN repo root. Run the steps below EXACTLY (no path edits, no exploration, no extra commands). This is PROPOSE-ONLY: issue NO branch-mutating command — no gt submit/modify/create/restack, no git push, no gh pr edit/merge/close/ready, no write-verb gh api on pulls or git refs. The ONLY GitHub write is the ONE \`gh pr comment\` in step 5 (issued via the helper script).

0. Write the two input JSON files VERBATIM with the Write tool (do NOT hand-type the JSON in a shell heredoc — store it byte-for-byte):
   - Write to ${verdictFile} this exact content (the round-0 pre-reduction per-lens verdict array):
${verdictJson}
   - Write to ${drFile} this exact content (the decision-readiness verdict, or the literal null when this phase has none):
${decisionReadinessJson}

1. Synthesize the round-0 verdict ONCE and decide the terminal action (NO revise loop). Run EXACTLY, capturing stdout to ${actionFile}:

     python3 - ${verdictFile} > ${actionFile} <<'PY'
import json, sys
sys.path.insert(0, "${engineCmd('scripts')}")
import qrspi_review_synopsis, qrspi_critic_synthesize
verdicts = json.load(open(sys.argv[1]))
panel, _dr = qrspi_review_synopsis.partition_decision_readiness(verdicts)
reduced = qrspi_critic_synthesize.synthesize(panel)
print("converged" if reduced.get("pass") else "exhausted")
PY

   ${actionFile} now holds exactly one line: "converged" or "exhausted". The python steps below read it via \`$(cat ${actionFile})\` — do not type the action by hand.

2. Build the ReviewRecord and write it to ${recordFile}. terminal_action is read from ${actionFile}; agreement is the EMPTY object {} (F2 — qrspi_review_agreement.compute is NOT called and there is NO Agreement line). Run EXACTLY:

     python3 - ${verdictFile} "$(cat ${actionFile})" > ${recordFile} <<'PY'
import json, sys
sys.path.insert(0, "${engineCmd('scripts')}")
import qrspi_review_record, qrspi_review_synopsis
verdicts = json.load(open(sys.argv[1]))
terminal_action = sys.argv[2]
record = qrspi_review_record.build_record(
    phase="${cfg.recordPhase}", rounds=verdicts,
    terminal_action=terminal_action, agreement={})
record.update(qrspi_review_synopsis.ledger_row_fields(verdicts))
print(json.dumps(record))
PY

   (build_record rejects a non-terminal action; "converged"/"exhausted" are both valid, so this only succeeds because there is no revise.)

3. Render the axis-enumerated synopsis to ${synopsisFile} (the verdict array and the decision-readiness verdict are read from their files; a file holding the literal null renders no decision-readiness section). Run EXACTLY:

     python3 - ${verdictFile} ${drFile} "$(cat ${actionFile})" > ${synopsisFile} <<'PY'
import json, sys
sys.path.insert(0, "${engineCmd('scripts')}")
import qrspi_review_synopsis
verdicts = json.load(open(sys.argv[1]))
decision_readiness = json.load(open(sys.argv[2]))
terminal_action = sys.argv[3]
print(${JSON.stringify(advisoryHeader)} + "\\n")
print(qrspi_review_synopsis.render_synopsis(verdicts, decision_readiness, terminal_action))
PY

   Do NOT append any Agreement line — F2 removed it.

4. Post the synopsis as ONE top-level advisory comment to PR #${resolved.pr} (a comment write, NOT a branch write). Run EXACTLY:

     python3 ${engineCmd('scripts/qrspi_comment_reply.py')} --ticket ${TICKET} --pr ${resolved.pr} --reply-mode toplevel --body-file ${synopsisFile}

   Confirm the returned envelope has "ok": true. If it is ok:false, return ok:false with that error (HARD STOP).

5. Append the ReviewRecord to the ledger. Run EXACTLY:

     python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${TICKET} --run-id "review-${cfg.recordPhase}-${TICKET}-$(date -u +%Y%m%dT%H%M%SZ)" --record "$(cat ${recordFile})"

   Confirm it returns ok:true. If ok:false, return ok:false with that error (HARD STOP).

6. Re-read the PR head SHA (the propose-only "after" snapshot). Run EXACTLY and capture its stdout VERBATIM:

     gh pr view ${resolved.pr} --json headRefOid --jq '.headRefOid'

   Return that exact SHA string as headShaAfter (do NOT alter it). The ENGINE — not you — compares it against the resolve snapshot ${resolved.headSha} and fails the run if they differ; report shaUnchanged as your own best-effort check (it equals ${resolved.headSha}) but the engine's headShaAfter comparison is authoritative.

Return JSON: { ok:true, terminalAction:"<the action from ${actionFile}>", posted:true, shaUnchanged:<bool>, headShaAfter:"<the exact SHA from step 6>", summary:"<1-2 sentence summary: which PR got the synopsis, the terminal action, and that the branch is untouched>" }. On any failure return { ok:false, error:"<reason>", summary:"<reason>" }.`,
  { label: `review-synopsis:${TICKET}`, phase: 'Synopsis', schema: SYNOPSIS_SCHEMA }
)

if (!fin || !fin.ok) {
  const reason = fin?.error ?? fin?.summary ?? 'no result'
  log(`review-${PHASE_KEY} ${TICKET}: synopsis/finalize failed — ${reason}`)
  return { ok: false, ticket: TICKET, phase: PHASE_KEY, pr: resolved.pr, error: `synopsis failed: ${reason}` }
}

// Authoritative propose-only assert: the ENGINE compares the re-read head SHA against the
// resolve snapshot rather than trusting the worker's shaUnchanged self-report. A blank
// headShaAfter (worker failed to read it) is also a violation — we cannot prove the branch
// is untouched, so fail closed.
const headShaAfter = typeof fin.headShaAfter === 'string' ? fin.headShaAfter.trim() : ''
const shaMatches = headShaAfter !== '' && headShaAfter === String(resolved.headSha).trim()
if (!shaMatches) {
  log(`review-${PHASE_KEY} ${TICKET}: PR head SHA changed or unverifiable (before=${String(resolved.headSha).slice(0, 12)}, after=${headShaAfter ? headShaAfter.slice(0, 12) : '(missing)'}) — propose-only invariant violated`)
  return { ok: false, ticket: TICKET, phase: PHASE_KEY, pr: resolved.pr, error: `propose-only invariant violated: PR head SHA ${headShaAfter ? 'changed' : 'unverifiable'} during the run (before ${resolved.headSha}, after ${headShaAfter || 'unknown'})` }
}

log(`review-${PHASE_KEY} ${TICKET}: synopsis posted to PR #${resolved.pr} (terminal action ${fin.terminalAction}); branch untouched`)
return {
  ok: true,
  ticket: TICKET,
  phase: PHASE_KEY,
  pr: resolved.pr,
  terminalAction: fin.terminalAction,
  shaUnchanged: true,
  summary: fin.summary,
}
