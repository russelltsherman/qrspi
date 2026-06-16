export const meta = {
  name: 'qrspi-teeth-eval',
  description: 'Opt-in teeth eval: feed the REAL design-critic panel a single deliberately-flawed design fixture (three labelled defects) digest-ON over N trials, and assert each owning lens still catches its defect by a majority threshold — proving the cost-reduced panel keeps its teeth, non-vacuously',
  whenToUse: 'On demand, when you want to confirm the design-critic lenses still catch injected defects (especially after a cost-reduction change to the digest/panel). NOT wired into CI — runs only on explicit Workflow({name:"qrspi-teeth-eval"}) invocation. The deterministic majority/marker math is separately CI-tested via scripts/qrspi_teeth_assert_test.py.',
  phases: [
    { title: 'Digest', detail: 'Build the shared research digest (digest-ON) from the teeth research fixture via qrspi_research_digest.py' },
    { title: 'Panel', detail: 'Fan out the real qrspi-design-critic-<lens> agents over {completeness, internal-consistency, edge-alignment} × trials against the flawed design fixture' },
    { title: 'Assert', detail: 'Hand grouped per-lens verdicts + markers + threshold to qrspi_teeth_assert.py; return { digestOn, trials, perLens, overallPass }' },
  ],
}

// ---------------------------------------------------------------------------
// Why this exists (RUS-78, Slice 3 — AC-Teeth-eval)
// ---------------------------------------------------------------------------
// The teeth eval proves the design-critic panel still has TEETH after the RUS-77
// cost reduction (the shared research digest): a deliberately-flawed design fixture
// carrying three labelled defects is fed to the REAL lenses, DIGEST-ON, and each
// owning lens must return pass=false naming its defect by a majority threshold.
//
// MECHANISM (structure §Contracts "Teeth-eval spawning mechanism"): a lens is a
// registered agentType (qrspi-design-critic-<lens>) spawnable ONLY from a Workflow
// runner (this file), and it Reads its inputs as FILES. A plain python script cannot
// drive a lens, and run_eval.py's call_model is a tool-less single-turn API call that
// cannot let a lens Read fixtures — so the design's named scripts/qrspi_teeth_eval.py
// is infeasible. This workflow is the runner; the only DETERMINISTIC piece (the
// majority/marker decision) is extracted to the CI-tested pure core
// scripts/qrspi_teeth_assert.py, called here via a worker.
//
// OFF CI: a .claude/workflows/*.js file is outside run_tests.py's scripts/*_test.py
// glob, so this runner never joins the deterministic gate; it runs only on explicit
// Workflow(...) invocation (AC-Teeth-eval, Q11). The JS sandbox cannot run python or
// touch the filesystem, so the digest build and the assertion core both run through
// WORKER agents (the buildResearchDigest / synthesizeVerdicts patterns in
// qrspi-batch.js).
// ---------------------------------------------------------------------------

// ENGINE_ROOT — the dir holding this engine's scripts/ + evals/, mirroring
// qrspi-batch.js. The teeth eval runs against the engine's OWN fixtures (no per-ticket
// worktree), so the engine root IS the operating root here: env override first (future
// plugin install), else the runner's cwd, else '.'.
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) ||
  '.'
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`

// Fixture paths (absolute, off ENGINE_ROOT) — the four inputs the design panel Reads,
// exactly the shape runCriticPanelLoop threads (DESIGN/TICKET/RESEARCH/QUESTIONS), plus
// the digest output path the digest-ON run threads as DIGEST_PATH.
const DESIGN_PATH = engineCmd('evals/teeth/design.md')
const TICKET_CONTENT_PATH = engineCmd('evals/teeth/ticket.md')
const RESEARCH_PATH = engineCmd('evals/teeth/research.md')
const QUESTIONS_PATH = engineCmd('evals/teeth/questions.md')
const DIGEST_PATH = '/tmp/teeth/research-digest.md'
// RUS-82: the repo root the node-validity `design-review` lens Reads/Greps to verify the
// fixture's codebase claims. The teeth eval runs against the engine's OWN checkout, so the
// engine root IS the codebase root — it holds the real scripts/ (incl.
// qrspi_critic_synthesize.py) the design.md defect falsely claims a symbol from. The eval is
// standalone (no runCriticPanelLoop), so it threads its OWN CODEBASE_PATH into the inline
// prompt below; the loop-side splice in qrspi-batch.js never reaches this runner.
const CODEBASE_PATH = ENGINE_ROOT

// The lens -> defect-marker ownership map (structure §Contracts). Each owning lens must
// cite its unique marker when it catches its defect; the marker turns "names its defect"
// into a deterministic substring test in qrspi_teeth_assert.py. The edge-alignment marker
// frobnicate_widget() is a research.md fact a CORRECT digest retains (it lives in prose,
// not a fenced block) — so a digest that trimmed it would make edge-alignment pass and
// overallPass go false (the non-vacuity / digest-risk-gating check, review finding #1).
// RUS-82: `design-review` (node-validity) is activated for the teeth run SOLELY by being a
// key here (LENSES = Object.keys(LENS_MARKERS)). The eval is a standalone fan-out with NO
// critics.design.lenses config and does NOT call resolve_design, so the production default-OFF
// whitelist is irrelevant — this map is the only activation lever. Its marker is cited when the
// lens catches the false-codebase-claim defect in evals/teeth/design.md (verified against real
// source via the CODEBASE_PATH threaded into the eval's inline prompt below).
const LENS_MARKERS = {
  'completeness': 'AC-TEETH-COMPLETENESS',
  'internal-consistency': 'TEETH-INCONSISTENCY',
  'edge-alignment': 'frobnicate_widget()',
  'design-review': 'TEETH-NODE-VALIDITY',
}
const LENSES = Object.keys(LENS_MARKERS)

// The { pass, findings } verdict schema, identical to runCriticPanelLoop's lens contract.
const CRITIC_VERDICT_SCHEMA = {
  type: 'object',
  required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
  },
}

// The teeth-eval report the assertion core returns.
const TEETH_REPORT_SCHEMA = {
  type: 'object',
  required: ['perLens', 'overallPass'],
  properties: {
    overallPass: { type: 'boolean' },
    perLens: { type: 'object' },
  },
}

// --- args ------------------------------------------------------------------
// { trials?: number } — number of trials per lens (default 3). The majority threshold
// is the integer majority of trials (>= ceil((trials+1)/2)); for the default 3 this is
// 2, i.e. the structure's ">=2-of-3".
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const TRIALS = (Number.isInteger(input?.trials) && input.trials > 0) ? input.trials : 3
const THRESHOLD = Math.floor(TRIALS / 2) + 1

// --- Digest phase ----------------------------------------------------------
// Build the shared research digest ONCE (digest-ON) via a worker running the real
// deterministic qrspi_research_digest.py, GUARDED with `test -s` so an empty/missing
// digest fails CLOSED (verbatim buildResearchDigest pattern, qrspi-batch.js:999-1004).
// The JS sandbox cannot run python; the worker runs it at the engine root cwd.
log(`teeth-eval: building shared research digest (digest-ON) from ${RESEARCH_PATH}`)
const digestBuilt = await agent(
  `You are the RESEARCH-DIGEST worker for the teeth eval. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  mkdir -p /tmp/teeth && python3 ${engineCmd('scripts/qrspi_research_digest.py')} --research ${RESEARCH_PATH} --out ${DIGEST_PATH} && test -s ${DIGEST_PATH} && printf '{"ok":true}\\n' || printf '{"ok":false}\\n'

It generates the digest then verifies it is non-empty, printing { "ok": true } on success or
{ "ok": false } on any failure. Parse and return that JSON verbatim. HARD STOP, do NOT retry or improvise.`,
  { label: 'teeth:digest', phase: 'Digest', schema: { type: 'object', required: ['ok'], properties: { ok: { type: 'boolean' } } } }
)
if (!digestBuilt || digestBuilt.ok !== true) {
  log('teeth-eval: digest build failed/empty — aborting (fail-closed)')
  return { ok: false, error: 'research digest build failed or empty', digestOn: true, trials: TRIALS }
}
log(`teeth-eval: digest built → ${DIGEST_PATH} (lenses read the digest, digest-ON)`)

// --- Panel phase -----------------------------------------------------------
// Fan out the REAL qrspi-design-critic-<lens> agents over LENSES × TRIALS in parallel,
// each with the SAME prompt shape runCriticPanelLoop uses (the four input paths + the
// threaded DIGEST_PATH line, digest-ON), and group the verdicts by lens.
const jobs = []
for (const lens of LENSES) {
  for (let trial = 0; trial < TRIALS; trial++) {
    jobs.push(async () => {
      const verdict = await agent(
        `You are the ${lens} lens of the qrspi design-phase critic panel (teeth eval), trial ${trial + 1}/${TRIALS}.
DESIGN_PATH = ${DESIGN_PATH}
TICKET_CONTENT_PATH = ${TICKET_CONTENT_PATH}
RESEARCH_PATH = ${RESEARCH_PATH}
QUESTIONS_PATH = ${QUESTIONS_PATH}
DIGEST_PATH = ${DIGEST_PATH}
CODEBASE_PATH = ${CODEBASE_PATH}
Read every path provided above and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`,
        { label: `teeth:critic:${lens}#${trial + 1}`, phase: 'Panel', agentType: `qrspi-design-critic-${lens}`, schema: CRITIC_VERDICT_SCHEMA }
      )
      return { lens, verdict }
    })
  }
}
const replies = await parallel(jobs)

// A lens that failed to spawn (null verdict) cannot attest — abort rather than silently
// treating a missing reply as a pass (mirrors runCriticPanelLoop's failed-lens guard).
const failed = replies.find(rp => !rp || rp.verdict === null)
if (failed) {
  log(`teeth-eval: lens "${failed.lens}" failed/skipped a trial — aborting`)
  return { ok: false, error: `lens "${failed.lens}" failed to spawn`, digestOn: true, trials: TRIALS }
}

// Group verdicts by lens into { lens: [ {pass, findings}, ... ] } for the assertion core.
const trialsByLens = {}
for (const lens of LENSES) trialsByLens[lens] = []
for (const rp of replies) {
  trialsByLens[rp.lens].push({
    pass: rp.verdict.pass === true,
    findings: Array.isArray(rp.verdict.findings) ? rp.verdict.findings : [],
  })
}

// --- Assert phase ----------------------------------------------------------
// Hand the grouped verdicts (stdin) + the per-lens markers + threshold to the pure
// CI-tested qrspi_teeth_assert.py via a worker (the synthesizeVerdicts stdin pattern,
// qrspi-batch.js:980-997). The fragile verdict text rides stdin, never the worker's
// stdout echo. The script prints { perLens, overallPass }.
log(`teeth-eval: asserting per-lens majority catch (threshold ${THRESHOLD}-of-${TRIALS}) via qrspi_teeth_assert.py`)
const report = await agent(
  `You are the TEETH-ASSERT worker. Your cwd is the main repo root. Run EXACTLY this one
command verbatim (no path edits, no exploration) and return its JSON stdout verbatim:

  printf '%s' ${JSON.stringify(JSON.stringify(trialsByLens))} | python3 ${engineCmd('scripts/qrspi_teeth_assert.py')} --markers ${JSON.stringify(JSON.stringify(LENS_MARKERS))} --threshold ${THRESHOLD}

It prints JSON { perLens, overallPass }. Parse and return it verbatim. If it errors, return that
as-is — HARD STOP, do NOT retry or improvise.`,
  { label: 'teeth:assert', phase: 'Assert', schema: TEETH_REPORT_SCHEMA }
)
if (!report || typeof report.overallPass !== 'boolean') {
  log('teeth-eval: assertion core failed to compute — aborting')
  return { ok: false, error: 'teeth assertion core failed', digestOn: true, trials: TRIALS }
}

log(`teeth-eval: overallPass=${report.overallPass} (digest-ON, ${TRIALS} trials, threshold ${THRESHOLD})`)
return { digestOn: true, trials: TRIALS, threshold: THRESHOLD, perLens: report.perLens, overallPass: report.overallPass }
