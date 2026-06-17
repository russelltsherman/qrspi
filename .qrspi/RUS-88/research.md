# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## Q1: How does `runPhase` route between the panel loop and the edge-critic loop, and what is the exact conditional (`lenses?.length ? runCriticPanelLoop : runCriticLoop`) currently present in the source after RUS-84's restructuring of that line?

**Answer:** `runPhase` (`.claude/workflows/qrspi-batch.js:1427`) only enters critic logic when a truthy `criticConfig` is passed (`if (criticConfig)` at line 1469). Inside that block, after an optional `gateBehindEdge` short-circuit (lines 1478-1493, design-panel-only, default OFF), the routing is a ternary keyed on whether `criticConfig.lenses` is a non-empty array: a non-empty `lenses` selects the multi-lens `runCriticPanelLoop` (design phase); its absence selects the single-critic `runCriticLoop` (questions/research/structure/plan, or any other caller). The verbatim conditional is below.

**Evidence:**

```js
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
```

— `.claude/workflows/qrspi-batch.js:1494-1503`
**Dependencies:** `runPhase` is called by `doDesign`, `doPlan` (and produces). The ternary fans out to `runCriticLoop` (line 739) and `runCriticPanelLoop` (line 844). `criticConfig` is built per-phase in `doDesign`/`doPlan` from the resolved `readCriticsConfig` envelope.
**Implicit contracts:** Both loops MUST return `{ ok, residualFindings, metrics? }` (and panel additionally `summary`); `runPhase` consumes `cr.ok`, `cr.residualFindings`, `cr.summary`, `cr.metrics` uniformly (lines 1500-1512). The `lenses?.length` test is the SOLE discriminator — removing the single-critic branch must preserve this uniform return contract for the panel branch.

## Q2: What inputs does `runCriticLoop` receive (upstream artifact, produced artifact, phase identity) and what does it return to its caller, so the removal point and the caller's expected return contract are known?

**Answer:** Signature `async function runCriticLoop(name, id, criticConfig)` (`.claude/workflows/qrspi-batch.js:739`). It reads `criticConfig.maxRounds` (default 2), `criticConfig.upstreamPath` (rubric anchor, the upstream artifact), and `criticConfig.rubric` (optional). The produced artifact path is derived as `stg(id, name)` (the staging path). It spawns the `qrspi-critic` agent per round with `UPSTREAM_PATH`/`ARTIFACT_PATH`, delegates the converge/revise/cap decision to `criticDecision` (which shells to `scripts/qrspi_critic_loop.py`), and on `revise` re-spawns the producer agent to rewrite `stg(id, name)` in place. It returns `{ ok, residualFindings, metrics }`: `ok` true when the loop completed (converged OR cap_reached), `residualFindings` `[]` on converge else the last verdict's findings, `metrics` a `CriticStepMetrics` record (or null on metrics shell-out failure).

**Evidence:**

```js
async function runCriticLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const upstreamPath = criticConfig.upstreamPath
  const artifactPath = stg(id, name)
  const rubricLine = criticConfig.rubric ? `RUBRIC = ${criticConfig.rubric}\n` : ''
  ...
    if (decision.action === 'converged') {
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'converged')
      return { ok: true, residualFindings: [], metrics }
    }
    if (decision.action === 'cap_reached') {
      const metrics = await recordCriticMetrics(id, name, metricRounds, 'cap_reached')
      return { ok: true, residualFindings: decision.residual_findings, metrics }
    }
```

— `.claude/workflows/qrspi-batch.js:739-743, 780-789`
**Dependencies:** Upstream: `runPhase` (the only orchestration caller, line 1499). Downstream: `agent()` (spawns `qrspi-critic` agentType + the reviser producer), `criticDecision` → `scripts/qrspi_critic_loop.py`, `recordCriticMetrics` → `scripts/qrspi_critic_metrics.py`, `stg()`.
**Implicit contracts:** Caller `runPhase` only inspects `cr.ok`, `cr.residualFindings`, `cr.summary` (single-critic loop returns no `summary` — only the panel does), `cr.metrics`. A `null` from any spawned agent collapses to `{ ok: false }`, which `runPhase` maps to returning `false` (ticket stops). Note `runSliceCritic` (line ~1955) and `runCoherenceCritic` (line ~1900) are SEPARATE functions that ALSO spawn the `qrspi-critic` / `qrspi-coherence-critic` agents — they are NOT `runCriticLoop` and have their own return shapes.

## Q3: Where in `doImplementation` is the per-slice `qrspi-critic` invocation wired into the slice-diff flow, and what data (slice diff, upstream contract) is passed into it?

**Answer:** In `doImplementation`'s slice loop, AFTER each slice's commit (line 2124), gated by `implCriticCfg.enabled` (line 2130). It first calls `sliceCriticDecide(t, setup, s.n)` (line 2131) — which shells to `scripts/qrspi_slice_critic.py` `decide` to decide run/skip and compute the diff range — then, when `dec.run`, calls `runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds)` (line 2141). `runSliceCritic` (defined at line ~1955) spawns the `qrspi-critic` agent (agentType `qrspi-critic`) whose produced artifact is the slice's code diff (`git diff ${dec.diffBase}..${dec.diffHead}`) and whose rubric (upstream) is the slice's `planSlice` + `structureSlice` passed inline. Residual findings are stored in `perSliceFindings[s.n]` for the slice PR-body splice.

**Evidence:**

```js
    if (implCriticCfg.enabled) {
      const dec = await sliceCriticDecide(t, setup, s.n)
      if (!dec) { ... return skip(...) }
      if (!dec.run) {
        log(`  ${t.id}: slice ${s.n} critic skipped (${dec.skipReason ?? 'no reason'}) — slice ships unjudged`)
      } else {
        const sc = await runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds)
        if (!sc.ok) { return skip(t, r.decision, `Slice ${s.n} critic spawn failed; stopped without shipping.`) }
        perSliceFindings[s.n] = sc.residualFindings
      }
    }
```

— `.claude/workflows/qrspi-batch.js:2130-2147`
**Dependencies:** `implCriticCfg` resolved at line 2044 (`(await readCriticsConfig('Implementation')).implementation`). `sliceCriticDecide` (line 1387) → `scripts/qrspi_slice_critic.py`. `runSliceCritic` (line 1955) → `agent` (spawns `qrspi-critic` and the slice reviser → `scripts/qrspi_revise_amend.py`), `criticDecision`. The diff range is `${dec.diffBase}..${dec.diffHead}` (line 1958).
**Implicit contracts:** `runSliceCritic` uses agentType `qrspi-critic` but is structurally INDEPENDENT of `runCriticLoop` — it has its own loop body, reviser (`qrspi_revise_amend.py` rather than a producer re-spawn), and does NOT emit `metrics`. The slice critic judges a code diff against `planSlice`+`structureSlice`, not an `UPSTREAM_PATH`/`ARTIFACT_PATH` file pair. Removing `runCriticLoop` does not by itself remove the per-slice path; the per-slice path reuses only the `qrspi-critic` AGENT and `criticDecision`, not the `runCriticLoop` function.

## Q4: What is the full set of call sites of `runCriticLoop` and the `qrspi-critic` agent/skill across the workflow and scripts, so every reference can be accounted for at removal?

**Answer:**
- `runCriticLoop` **definition**: `.claude/workflows/qrspi-batch.js:739`.
- `runCriticLoop` **call site** (the ONLY one): `.claude/workflows/qrspi-batch.js:1499` (the `lenses?.length` ternary false-branch in `runPhase`).
- `qrspi-critic` **agent** (`agentType: 'qrspi-critic'`) is spawned in THREE places: (1) `runCriticLoop` round body — line 759; (2) `runSliceCritic` round body — line 1968; (3) the `qrspi-critic` skill wrapper. The reviser spawns inside those loops do NOT set `agentType` (they default to the producer/generic agent).
- `qrspi-critic` **agent definition**: `.claude/agents/qrspi-critic.md`.
- `qrspi-critic` **skill**: `.claude/skills/qrspi-critic/SKILL.md` (a thin standalone `/qrspi-critic` wrapper; references `runCriticLoop in qrspi-batch.js` in its description).

**Evidence:**

```
.claude/workflows/qrspi-batch.js:739:async function runCriticLoop(name, id, criticConfig) {
.claude/workflows/qrspi-batch.js:1499:      : await runCriticLoop(name, id, criticConfig)
.claude/workflows/qrspi-batch.js:759:  ... agentType: 'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA }  (runCriticLoop)
.claude/workflows/qrspi-batch.js:1968: ... agentType: 'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA }  (runSliceCritic)
```

— grep over `.claude/workflows/qrspi-batch.js`, `.claude/agents/qrspi-critic.md`, `.claude/skills/qrspi-critic/SKILL.md`
**Dependencies:** The single-critic phases that route into `runCriticLoop` are built in `doDesign` (`questionsCritic` line 1688, `researchCritic` line 1711 — both have no `lenses`) and `doPlan` (`structureCritic` line 1830, `planCritic` line 1843). `designCritic` (line 1736) DOES carry `lenses`, so it routes to the panel, NOT `runCriticLoop`.
**Implicit contracts:** The `qrspi-critic` AGENT is shared by `runCriticLoop` AND `runSliceCritic` (per-slice). Removing the fidelity-only edge critic (`runCriticLoop`) while keeping the per-slice critic would leave the `qrspi-critic` agent+skill still in use by `runSliceCritic`. The agent description/skill description both name `runCriticLoop` and would be stale references if that function is deleted.

## Q5: How is `gateBehindEdge` defined, read, and consumed, and which functions or config keys reference it?

**Answer:** `gateBehindEdge` is a RUS-77 cost-lever, a nested `{enabled: bool}` block defaulting `{"enabled": False}`. **Defined/resolved** in `scripts/qrspi_critics_config.py:179-180` inside `resolve_design` (design phase only). **JS default mirror** at `.claude/workflows/qrspi-batch.js:638` (in `DEFAULT_CRITIC_PHASES.design`). **Consumed** in `runPhase` at `.claude/workflows/qrspi-batch.js:1478` — only when `criticConfig.lenses?.length` (i.e., the design panel) AND `gateBehindEdge.enabled`. Its honest behavior (per the inline comment, lines 1470-1492): the design phase routes to EITHER the panel OR an edge critic, never a sequence, so there is no in-scope upstream edge outcome to gate behind; when `gateBehindEdge.enabled` but no `criticConfig.edgePassed` is plumbed, it logs a no-op and runs the panel anyway. It is wired only into `doDesign`'s `designCritic` config (line 1741, `gateBehindEdge: critics.design.gateBehindEdge`).

**Evidence:**

```python
    # gateBehindEdge: nested {enabled} block, default {"enabled": False}.
    gate_cfg = cfg.get("gateBehindEdge") if isinstance(cfg.get("gateBehindEdge"), dict) else {}
    gate_behind_edge = {"enabled": resolve_enabled(gate_cfg, False)}
```

— `scripts/qrspi_critics_config.py:178-180`

```js
    if (criticConfig.lenses?.length && criticConfig.gateBehindEdge && criticConfig.gateBehindEdge.enabled) {
      if (criticConfig.edgePassed === true) { ... SKIP panel ... }
      log(`  ${id}: ${name} gateBehindEdge ON but no upstream edge outcome in scope ... (lever no-op; see plan §25)`)
    }
```

— `.claude/workflows/qrspi-batch.js:1478, 1492`
**Dependencies:** Resolver `scripts/qrspi_critics_config.py` (`resolve_design`) → JS `parseCriticsConfig` (line ~391) → `DEFAULT_CRITIC_PHASES` (line 638) → `doDesign` `designCritic` (line 1741) → consumed in `runPhase` (line 1478). Tested in `scripts/qrspi_critics_config_test.py` (`test_gate_behind_edge_default_off`, `test_gate_behind_edge_enabled_true_parses`, `test_gate_behind_edge_non_dict_falls_back_off`, `test_all_three_levers_on_parse_together`) and referenced in `scripts/qrspi_contract_fixtures_consumer_test.py:81`.
**Implicit contracts:** `gateBehindEdge` is a DESIGN-PANEL lever, NOT an edge-critic (`runCriticLoop`) lever — its `lenses?.length` guard means it never affects the single-critic path. It is, however, semantically about "gate the panel behind an EDGE critic pass," so removing the edge critic concept makes this lever's premise (an upstream edge outcome) permanently unreachable (already a documented no-op).

## Q6: What does `DEFAULT_CRITIC_PHASES` enumerate in `scripts/qrspi_critics_config.py`, and which entries correspond to the edge critic (questions/research/structure/plan) versus the design panel?

**Answer:** Note: `DEFAULT_CRITIC_PHASES` is a JS constant (`.claude/workflows/qrspi-batch.js:632`), NOT in `scripts/qrspi_critics_config.py`; the Python side's equivalent is `resolve_critics({})` / `default_phases()`. The Python resolver enumerates SIX phases in `resolve_critics` (line 227): `questions`, `research`, `structure`, `plan` (all via `resolve_edge_phase` — the single EDGE critic, shape `{enabled, maxRounds}`, listed in `EDGE_PHASES` at line 78); `design` (via `resolve_design` — the multi-lens PANEL, shape `{enabled, maxRounds, lenses, candidates, digest, gateBehindEdge, lensModel?}`); and `implementation` (via `resolve_implementation` — per-slice critic + nested `coherence`).

**Evidence:**

```python
# The four single-edge-critic planning phases (default ON, bare {enabled, maxRounds}).
EDGE_PHASES = ("questions", "research", "structure", "plan")
...
    phases = {
        "questions": resolve_edge_phase(c.get("questions")),
        "research": resolve_edge_phase(c.get("research")),
        "design": resolve_design(c.get("design"), warnings),
        "structure": resolve_edge_phase(c.get("structure")),
        "plan": resolve_edge_phase(c.get("plan")),
        "implementation": resolve_implementation(c.get("implementation")),
    }
```

— `scripts/qrspi_critics_config.py:77-78, 227-234`
**Dependencies:** `resolve_edge_phase` (line 110), `resolve_design` (line 121), `resolve_implementation` (line 201). JS mirror `DEFAULT_CRITIC_PHASES` at `.claude/workflows/qrspi-batch.js:632-642`. The two are kept in lockstep, asserted by `scripts/qrspi_critics_config_test.py` (`test_design_defaults_match_js_mirror` line 312, `test_all_phase_defaults_match_js_mirror` line 317).
**Implicit contracts:** The EDGE critic = the four `resolve_edge_phase` phases (questions/research/structure/plan); the design PANEL = `resolve_design`; implementation = per-slice critic + coherence. The `EDGE_PHASES` tuple comment still says "default ON" but the actual default is OFF (see Inconsistencies). Removing the edge critic touches `resolve_edge_phase` and the four phase entries; the design and implementation resolvers are independent.

## Q7: How does `scripts/qrspi_critics_config.py` resolve per-phase critic configuration (enabled flags, lenses, gateBehindEdge), and which keys in `.qrspi/config.json` / `.qrspi/config.example.json` feed it?

**Answer:** `main()` (line 244) calls `read_config(REPO_ROOT)` (the self-locating reader from `qrspi_config.py`), pulls the top-level `critics` key, and calls `resolve_critics(critics)` (line 219), which dispatches each of the six phase sub-keys to its resolver and returns `(phases, warnings)`. On any exception it emits a fail-safe envelope `{ ok: false, phases: default_phases(), ... }`. The uniform `enabled` flag is resolved by `resolve_enabled(cfg, default)` (line 93): only an explicit boolean flips it, any non-bool falls back to the default (always `False` — opt-in). `maxRounds` via `_pos_int_or` (line 81, default 2). `lenses` filtered against `KNOWN_DESIGN_LENSES` (line 71); `candidates` clamped to `[1, len(framings)]`; `gateBehindEdge`/`digest` nested `{enabled}` blocks. Config source: the top-level `critics` object in `.qrspi/config.json` (gitignored), documented in `.qrspi/config.example.json` (`critics` at line 6, with `design`, `implementation`, `questions`/`research`/`structure`/`plan` sub-blocks).

**Evidence:**

```python
def main():
    ...
        config = read_config(REPO_ROOT)
        critics = config.get("critics") if isinstance(config, dict) else None
        phases, warnings = resolve_critics(critics)
        print(json.dumps({"ok": True, "phases": phases, "warnings": warnings}))
```

— `scripts/qrspi_critics_config.py:244-252`
**Dependencies:** `qrspi_config.read_config` (imported line 52). The `.qrspi/config.example.json` `critics` block documents all knobs (lines 6-53). JS consumer `parseCriticsConfig` (line ~391) merges the emitted `phases` over `DEFAULT_CRITIC_PHASES`.
**Implicit contracts:** `phases` is ALWAYS present and complete (defaults on any failure) so the JS consumer never special-cases a missing phase. The four EDGE phases share the IDENTICAL `{enabled, maxRounds}` shape via `resolve_edge_phase`. The config-read is done ONCE per `doDesign`/`doPlan`/`doImplementation` (the "single read discipline").

## Q8: How is the design critic panel (and its four lenses including `edge-alignment`) configured and resolved separately from the edge critic, so the boundary that must stay byte-for-byte unaffected is identified?

**Answer:** The design panel is resolved by `resolve_design` (`scripts/qrspi_critics_config.py:121`), entirely separate from `resolve_edge_phase`. Its lens set defaults to `DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]` (line 64); config lenses are filtered against `KNOWN_DESIGN_LENSES` (= the four + `design-review`, line 71). Each lens id maps to agent `.claude/agents/qrspi-design-critic-<id>.md` (the five lens agents exist on disk: completeness, internal-consistency, edge-alignment, design-review, simplicity). At runtime the panel runs in `runCriticPanelLoop` (`.claude/workflows/qrspi-batch.js:844`), selected by `runPhase`'s `lenses?.length` ternary (line 1497). Note: `edge-alignment` is a design-PANEL LENS (a sub-judge inside the panel), NOT the standalone edge critic — they are namesakes but distinct mechanisms. The edge critic = `runCriticLoop` + `qrspi-critic` agent; the panel = `runCriticPanelLoop` + the five `qrspi-design-critic-*` lens agents.

**Evidence:**

```python
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
# ... design-review is whitelist-acceptable but DELIBERATELY NOT in DEFAULT_DESIGN_LENSES
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}
```

— `scripts/qrspi_critics_config.py:64-71`
**Dependencies:** `resolve_design` (independent of `resolve_edge_phase`). Runtime: `runCriticPanelLoop` (line 844) → fans out `qrspi-design-critic-<lens>` agents → reduces via `scripts/qrspi_critic_synthesize.py` → `criticDecision` → `scripts/qrspi_critic_loop.py`. Lens agents: `.claude/agents/qrspi-design-critic-{completeness,internal-consistency,edge-alignment,design-review,simplicity}.md`.
**Implicit contracts:** The boundary to keep byte-for-byte unaffected: `resolve_design`, `runCriticPanelLoop`, the five lens agents, `DEFAULT_DESIGN_LENSES`/`KNOWN_DESIGN_LENSES`, and `doDesign`'s `designCritic` build (line 1736). The panel shares `criticDecision` (`qrspi_critic_loop.py`) and `recordCriticMetrics` with the edge critic, so removing `runCriticLoop` must NOT delete those shared pure modules. The `edge-alignment` lens agent must NOT be confused with `qrspi-critic` — they are different files.

## Q9: When a planning phase has no `lenses` configured, what is the current fallback behavior, and what code path executes if neither a panel nor `runCriticLoop` runs (the "ungated" path)?

**Answer:** Two distinct cases. (a) When a phase's critic is enabled but has no `lenses` (questions/research/structure/plan — they never carry `lenses`), `runPhase`'s ternary (line 1497) takes the false branch → `runCriticLoop` (the single edge critic). (b) When a phase's critic is DISABLED by config, `doDesign`/`doPlan` pass `criticConfig = undefined` (e.g., `const questionsCritic = critics.questions.enabled ? {...} : undefined`, line 1688), so `runPhase`'s `if (criticConfig)` guard (line 1469) is false and the ENTIRE critic block is skipped — the artifact is produced and persisted with NO critic gate (the "ungated"/byte-for-byte-unchanged no-critic path). In the ungated path the only success gate is `persistArtifact` (line 1484/1518). There is no separate fallback — absence of `criticConfig` means no critic runs at all.

**Evidence:**

```js
  if (existing && existing[name]) { ... return true }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { ... return false }
  ...
  if (criticConfig) {     // <-- absent criticConfig => entire critic block skipped (ungated)
    ...
    const cr = criticConfig.lenses?.length
      ? await runCriticPanelLoop(name, id, criticConfig)
      : await runCriticLoop(name, id, criticConfig)
```

— `.claude/workflows/qrspi-batch.js:1428-1499`
**Dependencies:** `doDesign` builds `questionsCritic`/`researchCritic`/`designCritic` conditionally on `.enabled` (lines 1688-1755); `doPlan` builds `structureCritic`/`planCritic` (lines 1830-1847). Disabled ⇒ `undefined` ⇒ ungated. `persistArtifact` is the residual success gate.
**Implicit contracts:** With critics default OFF (all phases `enabled: false`), the SHIPPED default is already the ungated path for every planning phase. Removing `runCriticLoop` would make the single-critic branch dead even when a config opts in (`enabled: true`). The phase would then need to route to the ungated path or error — currently the ternary's false branch is the ONLY consumer of `runCriticLoop`.

## Q10: Does any caller of `runCriticLoop` depend on a pass/fail verdict to gate advancement, retry, or block persistence — i.e., does removal leave any phase that previously could fail now always proceeding?

**Answer:** Yes — `runPhase` blocks persistence on the loop's `ok`, not on `pass`. The verdict's pass/fail does NOT gate advancement directly: the loop internally converges or reaches cap, and a cap-reached artifact is STILL persisted (residual findings only surfaced into the PR body). The single way `runCriticLoop` can stop a phase is returning `ok: false` (a critic or reviser SPAWN failure, or a failed `criticDecision`); `runPhase` then returns `false` and the ticket stops BEFORE persist (line 1500-1503). So removal effects: (1) a phase that today could halt on a critic/reviser spawn failure would no longer halt for that reason; (2) the produce→critique→revise rewrite (which can MUTATE the staged artifact before persist) disappears, so the artifact persists exactly as the producer wrote it; (3) residual-finding PR-body splices for the planning phases disappear. There is no separate retry/Linear-status gate tied to the verdict — advancement is PR-review-gated downstream, independent of the critic verdict.

**Evidence:**

```js
    const cr = criticConfig.lenses?.length
      ? await runCriticPanelLoop(name, id, criticConfig)
      : await runCriticLoop(name, id, criticConfig)
    if (!cr || !cr.ok) {
      log(`  ${id}: ${name} critic loop did not complete — stopping this ticket`)
      return false        // <-- only ok:false (spawn failure) stops the phase; pass/fail does not
    }
    criticConfig.residualFindings = cr.residualFindings
```

— `.claude/workflows/qrspi-batch.js:1497-1506`
**Dependencies:** `runPhase` callers `doDesign`/`doPlan`. Residual findings flow to `criticBodyStep` (line 1410) → `scripts/qrspi_critic_body.py` (PR-body splice). Convergence math lives in `scripts/qrspi_critic_loop.py` (`next_action`).
**Implicit contracts:** A cap-reached artifact is "ship-with-disclosure" — pass=false never blocks persist, only surfaces findings. Thus removing the edge critic does NOT remove a hard advancement gate (there isn't one on the verdict); it removes the in-place revision pass and the spawn-failure halt. The design panel (`runCriticPanelLoop`) retains the identical `ok`-based semantics and is unaffected.

## Q11: How is the `qrspi-coherence-critic` whole-stack pass invoked at the planning→implementation seam, and is it independent of `runCriticLoop` such that removing the edge critic leaves it intact?

**Answer:** It is invoked by `runCoherenceCritic` (defined `.claude/workflows/qrspi-batch.js:~1900`), called ONCE in `doImplementation` (line 2076) at the planning→implementation seam, gated by `implCriticCfg.coherence.enabled` (line 2050). It spawns agentType `qrspi-coherence-critic` (line 1912) with the six artifact paths, loops up to `coherence.maxRounds` using `criticDecision` for convergence, and carries residual findings to the slice-1 PR body (it NEVER rewrites an upstream artifact). It is structurally INDEPENDENT of `runCriticLoop`: separate function, separate agent (`qrspi-coherence-critic`, defined `.claude/agents/qrspi-coherence-critic.md`), separate config resolver (`resolve_implementation.coherence`). It shares only the `criticDecision` pure module (`qrspi_critic_loop.py`) and `CRITIC_VERDICT_SCHEMA`. Removing `runCriticLoop` leaves the coherence pass intact provided the shared `criticDecision`/`qrspi_critic_loop.py`/`CRITIC_VERDICT_SCHEMA` are preserved.

**Evidence:**

```js
  if (implCriticCfg.coherence.enabled) {
    ...
    const coh = await runCoherenceCritic(t.id, coherencePaths, implCriticCfg.coherence.maxRounds)
    if (!coh.ok) { return skip(t, r.decision, 'Coherence critic spawn failed; stopped without implementing.') }
    coherenceFindings = coh.residualFindings
```

— `.claude/workflows/qrspi-batch.js:2050, 2076-2082`
**Dependencies:** `runCoherenceCritic` (line 1900) → `agent` (agentType `qrspi-coherence-critic`) → `criticDecision` → `scripts/qrspi_critic_loop.py`. Config via `resolve_implementation` (`scripts/qrspi_critics_config.py:201`). Agent `.claude/agents/qrspi-coherence-critic.md`.
**Implicit contracts:** Coherence returns `{ ok, residualFindings }` (same shape as `runCriticLoop` but no `metrics`). It depends on the shared pure-module decision core and the verdict schema, NOT on `runCriticLoop` itself. Any edge-critic removal must NOT delete `qrspi_critic_loop.py`, `criticDecision`, or `CRITIC_VERDICT_SCHEMA`, or it breaks both the coherence pass AND the per-slice critic AND the design panel.

## Q12: Which `scripts/*_test.py` files assert edge-critic / `gateBehindEdge` behavior, and which assert design-panel and coherence config resolution, so the right tests are removed and the right ones are preserved?

**Answer:**
- **Edge-critic decision core** (shared by edge, slice, coherence, panel): `scripts/qrspi_critic_loop_test.py` — tests `next_action` converge/revise/cap + `parse_critic_verdict`. PRESERVE (shared core).
- **Edge-phase config resolution**: `scripts/qrspi_critics_config_test.py` contains `TestResolveEdgePhase` cases (`test_defaults_when_absent`, `test_enabled_true_honored`, `test_max_rounds_*` lines 61-92) AND the `EDGE_PHASES` per-phase toggle test (`test_per_phase_enabled_independently_toggled` line 370). These assert the FOUR edge phases.
- **`gateBehindEdge`**: in `scripts/qrspi_critics_config_test.py` (`test_gate_behind_edge_default_off` line 208, `_enabled_true_parses` 212, `_non_dict_falls_back_off` 216, `test_all_three_levers_on_parse_together` 222) and a fixture assertion in `scripts/qrspi_contract_fixtures_consumer_test.py:81`. These are DESIGN-phase (`resolve_design`) tests.
- **Design panel**: `scripts/qrspi_critics_config_test.py` `TestResolveDesign` (lenses/candidates/digest/lensModel/gateBehindEdge, lines 102-274), `scripts/qrspi_critic_synthesize_test.py` (panel reduction), `scripts/qrspi_research_digest_test.py` (digest lever). PRESERVE.
- **Per-slice critic**: `scripts/qrspi_slice_critic_test.py` (decide run/skip + diff range). PRESERVE if per-slice critic stays.
- **Coherence**: `scripts/qrspi_critics_config_test.py` `TestResolveImplementation` (`test_coherence_enabled_true_honored` line 339, etc., lines 326-348). PRESERVE.
- **Metrics/body/summary**: `qrspi_critic_metrics_test.py`, `qrspi_critic_body_test.py`, `qrspi_critic_summary_test.py` — shared across all critic kinds. PRESERVE.

**Evidence:**

```
scripts/qrspi_critics_config_test.py:208:    def test_gate_behind_edge_default_off(self):
scripts/qrspi_critics_config_test.py:212:    def test_gate_behind_edge_enabled_true_parses(self):
scripts/qrspi_critics_config_test.py:216:    def test_gate_behind_edge_non_dict_falls_back_off(self):
scripts/qrspi_critics_config_test.py:222:    def test_all_three_levers_on_parse_together(self):
```

— grep `scripts/qrspi_critics_config_test.py`
**Dependencies:** No `_test.py` is dedicated SOLELY to the edge critic — the edge-critic logic is exercised through `qrspi_critic_loop_test.py` (shared core) and the `resolve_edge_phase` cases inside `qrspi_critics_config_test.py`. There is no `runCriticLoop`-specific Python test (the JS function is harness-coupled and unit-test-deferred per CLAUDE.md). The `EDGE_PHASES` constant and `resolve_edge_phase` would need their tests adjusted if those phases stop routing to an edge critic.
**Implicit contracts:** `qrspi_critic_loop.py` and its test are SHARED by all four critic kinds (edge, slice, coherence, panel) — removing edge must NOT remove them. The `gateBehindEdge` tests live in the DESIGN resolver test class, not an edge-phase class.

## Q13: How does `scripts/run_tests.py` discover and aggregate the `_test.py` suite, so removed test files and new ungated-routing assertions register correctly in the regression gate?

**Answer:** `discover_tests` (line 36) globs every `*_test.py` in the script's own directory (`SCRIPT_DIR`, self-located from `__file__`), sorted, optionally substring-filtered. `run_suite` (line 78) runs each as its own subprocess (`run_one`, line 51) with a 180s per-file timeout, collects PASS/FAIL, and `main` (line 107) exits non-zero if any file fails. Discovery is purely filename-pattern-based: a DELETED `*_test.py` simply drops from the set; a NEW `*_test.py` is auto-discovered with zero registration. There is no manifest/import list to update.

**Evidence:**

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48`
**Dependencies:** Invoked in CI by `.github/workflows/tests.yml` (the regression gate, per CLAUDE.md). `run_tests_test.py` is itself a discovered member (it imports this module's functions under `__main__` guard).
**Implicit contracts:** Filename `*_test.py` is the SOLE registration mechanism — a new ungated-routing assertion file just needs the `_test.py` suffix and to live in `scripts/`. Note: JS (`qrspi-batch.js`) is explicitly OUT of scope here (docstring lines 18-19), so any new ungated-routing logic in the JS `runPhase` ternary cannot be covered by this Python runner — it must be verified via a Python contract fixture or manual e2e (per the CLAUDE.md testing-dynamic-workflows convention).

## Q14: What logging, recorded results, or run-summary output does `runCriticLoop` (and the per-slice critic) currently emit, and what result entries would disappear from a batch run once the edge critic is removed?

**Answer:** `runCriticLoop` emits per-round `log()` lines: round PASS/FAIL with finding count (line 770), CONVERGED (781), CAP-REACHED with residual count (786), REVISE (794), plus failure/exhaustion lines (762, 776, 806, 814). It returns `metrics` (a `CriticStepMetrics` record built by `recordCriticMetrics` → `scripts/qrspi_critic_metrics.py`, appended to the per-ticket ledger by `scripts/qrspi_metrics_append.py`) which `runPhase` surfaces onto `criticConfig.criticMetrics` (line 1512); `doDesign` folds these into the ticket result's `criticMetrics` array (lines 1800-1805, `out.criticMetrics`). Residual findings flow into the PR-body summary (`out.summary` lines 1811-1812). The per-slice critic (`runSliceCritic`) emits analogous round logs (lines 1976, 1984, 1988, 1993) but NO `metrics` and stores findings in `perSliceFindings`. Removing the edge critic would drop: questions/research/structure/plan critic ledger records (`CriticStepMetrics` for those phases), their `[critic: N residual finding(s) in PR body]` summary fragments, and their per-round log lines — the design panel, per-slice, and coherence records/logs remain.

**Evidence:**

```js
    log(`  ${id}: ${name} critic round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)
    ...
    if (cr.metrics) criticConfig.criticMetrics = cr.metrics
```

— `.claude/workflows/qrspi-batch.js:770, 1512`

```js
  const criticMetrics = [
    questionsCritic?.criticMetrics,
    researchCritic?.criticMetrics,
    designCritic?.criticMetrics,
  ].filter(Boolean)
  if (criticMetrics.length) out.criticMetrics = criticMetrics
```

— `.claude/workflows/qrspi-batch.js:1800-1805`
**Dependencies:** `recordCriticMetrics` (line ~1080) → `scripts/qrspi_critic_metrics.py` + `scripts/qrspi_metrics_append.py`. Summarizer `scripts/qrspi_critic_summary.py` (referenced at line 110) scopes/reads the ledger. `criticBodyStep` → `scripts/qrspi_critic_body.py` for PR-body splice.
**Implicit contracts:** `out.criticMetrics` aggregates `questionsCritic`/`researchCritic`/`designCritic` records (line 1800-1804); removing the edge critic would drop the `questionsCritic`/`researchCritic` entries (and structure/plan in `doPlan`), leaving only `designCritic`. A phase with a DISABLED critic already surfaces no record (the array filters out `undefined`), so removal is consistent with the existing disabled-phase behavior. The metrics ledger/summary/body modules are SHARED — they must survive removal to keep the panel/slice/coherence records intact.

---

## Discovered Patterns

- **Four critic mechanisms share one decision core.** The single EDGE critic (`runCriticLoop`), the design PANEL (`runCriticPanelLoop`), the per-SLICE critic (`runSliceCritic`), and the COHERENCE critic (`runCoherenceCritic`) are four distinct JS functions that all delegate the converge/revise/cap decision to ONE tested pure module, `scripts/qrspi_critic_loop.py` (via the `criticDecision` shim), and all use `CRITIC_VERDICT_SCHEMA`. Three of them (edge, slice, coherence) reuse the SAME `qrspi-critic` or `qrspi-coherence-critic` agent; the panel uses five dedicated `qrspi-design-critic-*` lens agents.
- **Uniform return contract `{ ok, residualFindings, metrics? }`.** Every critic loop returns this shape; `ok:false` = spawn/decision failure (halts the ticket), `ok:true` with non-empty `residualFindings` = cap-reached ship-with-disclosure. Pass/fail of the verdict NEVER hard-gates advancement; it only triggers in-loop revision or PR-body disclosure.
- **Critics are uniformly opt-in, default OFF.** `resolve_enabled(cfg, False)` for every phase; disabled ⇒ `criticConfig === undefined` ⇒ `runPhase` skips the whole critic block (the "ungated" byte-for-byte-unchanged path). The shipped default config already runs every planning phase ungated.
- **Single-read discipline + JS/Python mirror lockstep.** `scripts/qrspi_critics_config.py` is read ONCE per `do*` phase; `DEFAULT_CRITIC_PHASES` (JS, line 632) mirrors `resolve_critics({})` (Python), with lockstep asserted by `qrspi_critics_config_test.py:312,317`.
- **Self-locating Python scripts.** `qrspi_critics_config.py`, `run_tests.py`, and siblings derive paths from `__file__` (not cwd), so callers type only the invocation.
- **Test registration is filename-pattern-only.** `run_tests.py` auto-discovers any `scripts/*_test.py`; no manifest. JS is explicitly out of scope for the Python gate.

## Inconsistencies

- **Stale "default ON" comments vs. actual default OFF.** `scripts/qrspi_critics_config.py:77` labels `EDGE_PHASES` as "(default ON, ...)", and `.claude/workflows/qrspi-batch.js` comments at lines 1688, 1711, 1830, 1843 say "default ON" for questions/research/structure/plan critics. The CODE defaults every phase OFF (`resolve_enabled(cfg, False)`, lines 110-118; module docstring lines 21-28 explicitly state the opt-in/OFF default). The comments predate the uniform-opt-in change and are now wrong.
- **`gateBehindEdge` is a documented no-op for its stated purpose.** The lever's name and config comment (`.qrspi/config.example.json:10`) describe "skip the design panel if an upstream edge-critic outcome passed," but the runtime comment (`.claude/workflows/qrspi-batch.js:1470-1492`) admits the design phase routes to panel OR edge (never a sequence), so no in-scope edge outcome exists and the lever logs a no-op and runs the panel anyway. Removing the edge critic makes this premise permanently unreachable.
- **`edge-alignment` (panel lens) vs. the edge critic (`qrspi-critic`).** Namesake confusion risk: `edge-alignment` is one of the four design-PANEL lenses (`.claude/agents/qrspi-design-critic-edge-alignment.md`), wholly separate from the standalone fidelity edge critic (`runCriticLoop` + `.claude/agents/qrspi-critic.md`). The panel lens must NOT be removed when the edge critic is.
- **`qrspi-critic` agent/skill descriptions name `runCriticLoop`.** `.claude/agents/qrspi-critic.md:3` and `.claude/skills/qrspi-critic/SKILL.md:3` both say "Spawned by runCriticLoop in qrspi-batch.js," but the SAME agent is also spawned by `runSliceCritic` (per-slice, line 1968) — the descriptions already undercount its callers, and would become stale references if `runCriticLoop` is deleted while the per-slice critic keeps the agent alive.
- **`DEFAULT_CRITIC_PHASES` location.** Q6/Q12 reference it as in `scripts/qrspi_critics_config.py`, but the constant by that name lives in `.claude/workflows/qrspi-batch.js:632`; the Python equivalent is `default_phases()`/`resolve_critics({})`. Flagged so the removal does not search the wrong file.
