# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T20:05:00Z
**Status:** draft

## Q1: What does `qrspi_resolve.py` return in its envelope, and which fields identify the worktree path, the phase artifact path, and the phase PR for a given ticket id — i.e. what is already available to a `/review-<phase>` command without re-deriving it?

**Answer:** `qrspi_resolve.py` (the one-shot orchestrator) prints a single JSON envelope assembled by `build_envelope`. The relevant top-level fields are: `ok`, `repoRoot` (resolved HOST checkout root), `worktreeDir` (`<repoRoot>/.worktrees/<ticket>`), `existing` (a map of each artifact name → bool "exists+non-empty"), `decision` (the resolver decision dict, carries `action`/`phase`/`reason`), `commentTargets`, `ciFailing`/`ciFailingChecks`/`ciRedBranches`, `reviewers`/`teamReviewers` (comma-joined CSV for `gt submit`), `ticketContentPath` (token-free path to the staged ticket title+body), `tip` (stack tip branch from `pick_tip`), and `slices` (ascending list of slice branch names). There is **no explicit PR-number field** in the envelope — the PR is identified indirectly by the phase branch (`<ticket>/design`, `<ticket>/plan`, `<ticket>/slice-N`) which `qrspi_pr_state.build_state` resolves to per-PR review/CI state inside `state["phases"]` (folded into `decision`, not surfaced as a raw PR number at top level). Artifact ON-DISK location: `<worktreeDir>/.qrspi/<ticket>/<artifact>.md` (see `detect_existing`, joined as `os.path.join(worktree, ".qrspi", args.ticket)`).

**Evidence:**

```python
env = {
    "ok": ok,
    "repoRoot": REPO_ROOT if repo_root is None else repo_root,
    "worktreeDir": worktree_dir,
    "existing": existing,
    "decision": decision,
    "commentTargets": comment_targets_of(decision),
    "ciFailing": ci_failing_of(decision),
    "ciFailingChecks": ci_failing_checks_of(decision, phases),
    "ciRedBranches": red_branches_of(decision, phases, ticket or ""),
    "reviewers": reviewers,
    "teamReviewers": team_reviewers,
    "ticketContentPath": ticket_content_path,
    "tip": tip,
    "slices": slices if slices is not None else [],
}
```

— `scripts/qrspi_resolve.py:312-327`
— `detect_existing` builds the artifact-exists map: `scripts/qrspi_resolve.py:142-153`
— artifact dir is `os.path.join(worktree, ".qrspi", args.ticket)`: `scripts/qrspi_resolve.py:511`

**Dependencies:** Imports `qrspi_pr_state.build_state`/`branch_set`/`slice_numbers`, `qrspi_resolve_state.resolve`, `qrspi_paths`, `qrspi_config`. Calls `gh repo view` and `gh api user` (infra). Consumed by `.claude/workflows/qrspi-batch.js` (`resolveTicket`).
**Implicit contracts:** The envelope is the single deterministic contract between the resolver and the JS orchestrator — `decision`'s key set is FIXED, which is why CI/comment fields are RE-emitted at top level (a new field is additive and ignored by old consumers). The PR number is NOT in the envelope; a `/review-<phase>` command that needs a PR number must derive it itself (e.g. `gh pr list --head <ticket>/<phase>`) or read `state["phases"]` from the gather. The worker types only short tokens; every `qrspi`-laden path is computed in the script.

## Q2: How does the existing batch path locate and read each phase artifact (`design.md`, `plan.md`, slice diffs) for a ticket, and where do those artifacts live on disk relative to the resolved worktree?

**Answer:** Artifacts live at `<worktree>/.qrspi/<ticket>/<artifact>.md`. The batch path uses two helpers in `qrspi-batch.js`: `art(wd, id, name)` builds `${wd}/.qrspi/${id}/${name}` (the canonical READ path, passed to agents), and `stg(id, name)` builds `/tmp/phase-stage/${id}/${name}.md` (the token-free STAGING path agents WRITE to before persist). The artifacts are produced to the staging path, then `qrspi_persist.py` moves the staged file to the canonical worktree path. `qrspi_persist.dest_path` is the authoritative on-disk location computation. Slice "diffs" are not stored as artifacts — slices are git commits on `<ticket>/slice-N` branches; the code diff is the PR diff, not a file in `.qrspi/`.

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    """Canonical worktree artifact path. ... The qrspi token lives ONLY here --
    computed by the script, never typed by the model."""
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)
```

— `scripts/qrspi_persist.py:67-71`

```javascript
const art = (wd, id, name) => `${wd}/.qrspi/${id}/${name}`
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:628,633`
— `ARTIFACTS` list (`questions, research, design, structure, plan, worktree`): `scripts/qrspi_persist.py:52`

**Dependencies:** `qrspi_persist.py` ← `qrspi_paths.resolve_repo_root`. `art`/`stg` are used throughout `doDesign`/`doPlan` in `qrspi-batch.js`.
**Implicit contracts:** Repo root is resolved via git-common-dir FIRST (so it is the MAIN checkout even when invoked from a worktree) — a script self-locating from `__file__` inside a worktree would double-nest the path. Any `/review-*` command reading an artifact must compute `<worktree>/.qrspi/<ticket>/<artifact>.md` the same way; the `existing` map from `qrspi_resolve.py` already tells which artifacts are present+non-empty.

## Q3: How does the current `qrspi-design-critic-design-review` node-validity lens receive its inputs (artifact contents, codebase access, ticket/upstream context) and what format does it emit?

**Answer:** The lens is an agent (`.claude/agents/qrspi-design-critic-design-review.md`, tools `Read, Grep`) spawned with a prompt carrying named PATH inputs (not contents): `DESIGN_PATH` (the staged artifact under review), `RESEARCH_PATH` (upstream codebase facts), `CODEBASE_PATH` (repo root — it Reads/Greps real source here), and optional `TICKET_CONTENT_PATH`, `QUESTIONS_PATH`, `DIGEST_PATH`. It deliberately **opts OUT of the digest** (always reads full `RESEARCH_PATH`). It emits exactly a `{pass, findings}` verdict validated as `CRITIC_VERDICT_SCHEMA` at the runner boundary, with the strict invariant `pass:false ⟺ findings non-empty`. The lens is spawned by `runCriticPanelLoop` (opt-in, default-OFF; not in `DEFAULT_DESIGN_LENSES` but whitelist-acceptable). `CODEBASE_PATH` is threaded uniformly into every lens prompt from `criticConfig.codebasePath` (the worktree root `wd`).

**Evidence:**

```
- `DESIGN_PATH` — absolute path to the artifact under review (the staged artifact)...
- `RESEARCH_PATH` — absolute path to the upstream input the artifact was derived from...
- `CODEBASE_PATH` — absolute path to the repository root. Read and Grep real source here...
- `TICKET_CONTENT_PATH` — OPTIONAL...
- `QUESTIONS_PATH` — OPTIONAL...
- `DIGEST_PATH` — OPTIONAL. ... **You opt OUT of the digest:** ... Ignore `DIGEST_PATH`.
```

— `.claude/agents/qrspi-design-critic-design-review.md:14-19`
— verdict schema + invariant: `.claude/agents/qrspi-design-critic-design-review.md:52-59`
— spawned via `agentType = qrspi-design-critic-${lens}` with `CODEBASE_PATH` threaded: `.claude/workflows/qrspi-batch.js:769,777,786`

**Dependencies:** Spawned by `runCriticPanelLoop`; inputs resolved in `doDesign` (`designCritic.codebasePath = wd`, `ticketContentPath = r.ticketContentPath`, `questionsPath = art(wd,t.id,'questions.md')`, `upstreamPath = art(wd,t.id,'research.md')`) at `qrspi-batch.js:1562-1576`. Verdict reduced by `synthesize` (Q4).
**Implicit contracts:** The lens receives PATHS, never inlined content — it Reads them itself. The model-intent (Opus-tier) is a DOC NOTE only — there is NO `lensModel` frontmatter key on the agent; the lens inherits the panel's session model (`qrspi-design-critic-design-review.md:71-73`). Every finding must cite a real source location.

## Q4: What is the input/output contract of `qrspi_critic_synthesize.py` — what does it consume from the panel agents and what synthesized structure does it produce?

**Answer:** `synthesize(verdicts: list) -> dict`. Input: a JSON array of per-lens verdict entries for ONE round (each `{pass, findings}`, optionally tagged with a `lens` id). Each entry is coerced fail-closed via the LANDED `_coerce_verdict`/`parse_critic_verdict` from `qrspi_critic_loop.py`. Output: `{"pass": bool, "findings": list}` where `pass` is True ONLY if the list is non-empty AND every coerced lens passed (AND-semantics; any fail ⇒ round fails; empty list ⇒ fail-closed). `findings` is the exact-string-deduped UNION in first-seen order; bare-string findings from an identified lens are wrapped as `{"text": ..., "lens": ...}`. CLI: reads JSON array on stdin, prints `{pass, findings}` on stdout.

**Evidence:**

```python
def synthesize(verdicts):
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}
    all_passed = True
    ...
    for entry in verdicts:
        coerced = _coerce_lens(entry)
        if not coerced["pass"]:
            all_passed = False
        ...
    return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:76-118`
— CLI stdin→stdout shim: `scripts/qrspi_critic_synthesize.py:133-147`

**Dependencies:** Imports `_coerce_verdict`, `parse_critic_verdict` from `qrspi_critic_loop.py`. Invoked from JS via `synthesizeVerdicts` (worker pipes the array on stdin) at `qrspi-batch.js:884-898`, schema `SYNTHESIZED_VERDICT_SCHEMA`.
**Implicit contracts:** Pure, stdlib-only, never raises (fail-closed). It does NOT compare against a human verdict or produce an "agreement" — it only reduces M lenses to one round verdict. A `/review-*` command that wants a panel verdict reuses this reducer exactly; an "agreement" comparison would be NEW logic on top.

## Q5: How are panel lens agents currently spawned and orchestrated in the batch path (`runCriticPanelLoop` / `runCriticLoop`), and what is the existing interface for invoking a single lens against an artifact?

**Answer:** `runCriticPanelLoop(name, id, criticConfig)` is the ONLY surviving lenses-carrying loop (`runCriticLoop`, the single-edge critic, was retired in RUS-88). Per round it fans out one `agent()` PER LENS in `parallel(...)`, each with `agentType = qrspi-design-critic-<lens-id>`, schema `CRITIC_VERDICT_SCHEMA`, and a prompt carrying `DESIGN_PATH`, `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`, plus optional `DIGEST_PATH`/`CODEBASE_PATH` lines. It tags each reply with its lens id, reduces them via `synthesizeVerdicts` (Q4), then delegates converge/revise/cap to `criticDecision` (→ `qrspi_critic_loop.next_action`). On `revise` it re-spawns the design producer to rewrite the staged artifact in place; on `cap_reached` it returns `residualFindings`. It records a `CriticStepMetrics` ledger row via `recordCriticMetrics` on every termination.

**Evidence:**

```javascript
const replies = await parallel(
  lenses.map(lens => async () => {
    const agentType = `qrspi-design-critic-${lens}`
    ...
    const verdict = await agent(
      `You are the ${lens} lens of the qrspi design-phase critic panel for ${id}, round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}${digestLine}${codebaseLine}
Read every path provided above and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`,
      agentOpts)
    return { lens, verdict }
  })
)
```

— `.claude/workflows/qrspi-batch.js:767-792`
— loop body (synthesize → decision → revise/converge/cap): `qrspi-batch.js:819-872`
— `criticConfig` fields consumed (`lenses`, `maxRounds`, `upstreamPath`, `ticketContentPath`, `questionsPath`): `qrspi-batch.js:720-726,728-733`

**Dependencies:** `runCriticPanelLoop` ← `parallel`/`agent` (harness globals), `synthesizeVerdicts`, `criticDecision`, `recordCriticMetrics`, `buildResearchDigest`. The single-lens interface IS one `agent()` call with the four+optional PATH lines and `CRITIC_VERDICT_SCHEMA`.
**Implicit contracts:** The loop runs INSIDE `runPhase`'s pre-persist staging window (`qrspi-batch.js:1335-1350`), gated purely on `criticConfig?.lenses?.length`. It MUTATES the staged artifact in place across revise rounds — it is NOT read-only. A `/review-*` command wanting a non-mutating "scratch" review would need to copy the artifact OR skip the revise spawn. The whole `runCriticPanelLoop` is harness-coupled JS (uses injected `agent`/`parallel`/`log`/`runId`) — not unit-testable in isolation; only the pure reducers are tested.

## Q6: How are slash-command wrappers in `.claude/skills/` structured to accept a ticket id argument and invoke their underlying agent/workflow, so a new `/review-design <id>` family follows the same convention?

**Answer:** Each skill is a directory under `.claude/skills/<name>/` holding a `SKILL.md` with YAML frontmatter (`name`, `description`, `command: /<name>`, `argument-hint: <ticket-id>`, `allowed-tools:`) followed by markdown step instructions. The thin wrappers (e.g. `qrspi-research`) parse `$ARGUMENTS` for the ticket id, resolve `REPO_ROOT` from `pwd`, and spawn the corresponding agent via the `Agent` tool with `subagent_type: <agent>` and a prompt body of named PATH inputs. The richer `qrspi-work` skill is a state machine (no agent spawn; it embeds the orchestration logic itself) with broader `allowed-tools` including `Bash`, `Agent`, and `mcp__linear__*`. There is currently **NO `/review-*` skill family** — this would be net-new.

**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts...
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
...
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`...
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
   - Prompt body containing the five inputs: TICKET_ID, QUESTIONS_PATH, RESEARCH_PATH, TEMPLATE_PATH, REPO_ROOT
```

— `.claude/skills/qrspi-research/SKILL.md:1-24`
— `qrspi-work` frontmatter (state-machine style, wider tools): `.claude/skills/qrspi-work/SKILL.md:1-9`

**Dependencies:** Skills reference agent definitions in `.claude/agents/`. `qrspi-work` references `references/*.md` and `docs/qrspi-pr-gated-lifecycle-design.md`.
**Implicit contracts:** Convention: SKILL.md frontmatter + numbered steps; agent prompts pass PATHS not content; ticket id from `$ARGUMENTS`; `REPO_ROOT` from `pwd`. A new `/review-design <id>` family should mirror `qrspi-research` (thin wrapper → agent) or `qrspi-work` (richer, runs `qrspi_resolve.py` and posts comments). NOTE: skills/agents are NOT auto-registered for the batch workflow — `runCriticPanelLoop` invokes agents by `agentType` string directly, independent of any SKILL.md.

## Q7: What is the schema and write mechanism of the RUS-78 agreement ledger that AC2 requires reuse of — where is it stored, what records a "structured verdict", and how is panel-vs-human agreement keyed?

**Answer:** The RUS-78 ledger is the per-ticket **critic-metrics ledger** at `<root>/.worktrees/<ticket>/.qrspi/<ticket>/critic-metrics.jsonl` (JSONL, one record per line). It is written by `qrspi_metrics_append.py`, which is the SINGLE envelope authority: it wraps a bare `CriticStepMetrics` record (built by `qrspi_critic_metrics.build_record`) into a `CriticMetricsLedgerLine` by injecting `ticketId`, `timestamp` (UTC ISO-8601), and `runId`. The "structured verdict" recorded per critic step is `{phase, rounds:[{lens, pass, findingsCount}], terminalAction}`. **There is NO existing "panel-vs-human agreement" field or keying** — the ledger records ONLY the panel's own verdicts/findings per round + terminal action + `runId`/`timestamp`/`ticketId`. Panel-vs-human agreement would be NEW: the closest existing key is `runId` (per-invocation) + `ticketId` + `phase`. (See Inconsistencies — the questions assume an "agreement ledger" that does not exist as such.)

**Evidence:**

```python
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record)
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
    return line
```

— `scripts/qrspi_metrics_append.py:67-79`
— ledger path `.../.qrspi/<ticket>/critic-metrics.jsonl`: `scripts/qrspi_metrics_append.py:60-64`
— append + non-empty verify (fail-closed): `scripts/qrspi_metrics_append.py:82-99`
— `CriticStepMetrics` shape `{phase, rounds:[{lens,pass,findingsCount}], terminalAction}`: `scripts/qrspi_critic_metrics.py:54-105`

**Dependencies:** `qrspi_metrics_append.py` ← `qrspi_paths`. Fed by `qrspi_critic_metrics.py` (pure reducer). Invoked from JS via `recordCriticMetrics` (chained worker command piping the record into the appender) at `qrspi-batch.js:975-989`.
**Implicit contracts:** The appender is the single envelope authority — its `ticketId`/`timestamp`/`runId` WIN over any pre-existing values in the record. Repo root via git-common-dir so the ledger lands in the MAIN checkout's worktree (not a double-nested phantom). `runId` is required and always a string. To record panel-vs-human agreement, a new record field (e.g. `humanVerdict`/`agreement`) would be ADDED to the record shape and the appender's wrap — the storage mechanism (JSONL append, keyed by ticket/run/phase) is reusable as-is.

## Q8: How does the loop-until-stable mechanism in the batch critic path track round count and detect "stable", and what state does it carry between rounds that a `≤3 round` scratch-copy loop would need to replicate?

**Answer:** The loop is `for (let round = 0; round < maxRounds; round++)` in `runCriticPanelLoop` (`maxRounds` default 2, from `criticConfig.maxRounds`). "Stable"/converged is decided by `criticDecision` → the pure `next_action(verdicts, round, max_rounds)`: `converged` when the latest synthesized verdict `pass` is truthy; `cap_reached` when not-passed AND `round+1 >= max_rounds`; `revise` otherwise. State carried between rounds: the staged artifact (rewritten in place on revise), `summaryRounds[]` (per-round pass/fail tags), `metricRounds[]` (every lens verdict for the ledger), and the `digestPath`/`lensModel` computed once before the loop. A `≤3 round` scratch loop would replicate: the round counter, the per-round synthesized verdict, the artifact being revised, and the accumulated per-round records — but would need a SCRATCH copy of the artifact rather than the live staged file (Q12).

**Evidence:**

```python
def next_action(verdicts, round, max_rounds):
    latest = _coerce_verdict(verdicts[-1]) if isinstance(verdicts, list) and verdicts else {"pass": False, "findings": []}
    if latest["pass"]:
        return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:84-115`
— loop header + `maxRounds` default: `.claude/workflows/qrspi-batch.js:728,764`
— between-round state (`summaryRounds`, `metricRounds`, `digestPath`, `lensModel`): `qrspi-batch.js:734-762`

**Dependencies:** `next_action` ← `_coerce_verdict`. Invoked via `criticDecision` worker (stdin pipe) in JS. `maxRounds` resolved by `qrspi_critics_config.resolve_design` (`DEFAULT_MAX_ROUNDS = 2`, `_pos_int_or`).
**Implicit contracts:** `next_action` is pure and fails closed (empty/garbled verdict ⇒ NOT-passed ⇒ never reports converged). The cap is `maxRounds`, NOT a hard-coded 3 — to make a `≤3 round` loop, `maxRounds` is the configurable lever (config `critics.design.maxRounds`, or pass 3 directly). The loop mutates the artifact in place — replicating it for a scratch review means cloning the artifact first.

## Q9: What are the RUS-78 cost levers (`digest` / `lensModel`) referenced in the constraints — where are they configured and how does a panel run consume them?

**Answer:** Both are resolved by `qrspi_critics_config.resolve_design` from `.qrspi/config.json` → `critics.design`. `digest` is a nested `{enabled: bool}` block (default `{"enabled": False}`); `lensModel` is an OPTIONAL string key, OMITTED entirely from the resolved result unless config supplies a non-empty string. Consumption in `runCriticPanelLoop`: when `criticConfig.digest.enabled`, it builds ONE shared research digest (`buildResearchDigest` → `qrspi_research_digest.py`, guarded `test -s` fail-closed) at `/tmp/phase-stage/<id>/research-digest.md` and threads `DIGEST_PATH` into each lens prompt (lenses then read the smaller digest instead of full `RESEARCH_PATH`); when `lensModel` is a non-empty string it is ridden as the `agent()` `model` option per lens (a SPECULATIVE seam — there is no evidence the harness honors `agent().model`, default-OFF). The `design-review` node-validity lens opts OUT of the digest (always reads full research).

**Evidence:**

```python
digest_cfg = cfg.get("digest") if isinstance(cfg.get("digest"), dict) else {}
digest = {"enabled": resolve_enabled(digest_cfg, False)}
...
lens_model = cfg.get("lensModel")
if isinstance(lens_model, str) and lens_model.strip():
    result["lensModel"] = lens_model
```

— `scripts/qrspi_critics_config.py:152-171`
— JS consumption (digest build + `DIGEST_PATH`/`lensModel` threading): `.claude/workflows/qrspi-batch.js:739-762,770-780`

**Dependencies:** `resolve_design` ← `qrspi_config.read_config`. `buildResearchDigest` ← `qrspi_research_digest.py`. Config read once via `criticsForPhase`/`parseCriticsEnvelope` (`qrspi-batch.js:1240`).
**Implicit contracts:** `digest` is the PRIMARY cost lever; `lensModel` is speculative/possibly inert. Both default OFF so the default panel run is byte-for-byte the pre-RUS-77 behavior. An empty/missing digest fails the phase CLOSED (no lens ever reads an empty digest). `lensModel` is config-only, applied uniformly to all lenses (not per-lens-specific).

## Q10: How does `qrspi_resolve.py` behave when the requested phase artifact does not yet exist or the phase PR is absent (e.g. `/review-plan` invoked before the plan PR exists)?

**Answer:** `qrspi_resolve.py` does not take a "requested phase" argument — it resolves the whole ticket state. A missing artifact is reported as `existing[<name>] = False` (via `detect_existing`, which returns False on any `OSError`/missing/empty file; a missing directory yields all-False). A phase PR being absent is reflected in the resolver `decision`: `qrspi_resolve_state.resolve` computes `existing` phases from real (trunk-ahead) branches; a phase with no branch/PR is simply not in `existing`, and the decision routes accordingly (e.g. `run_design`, `advance`, `submit`, or `entry_blocked`). It does NOT error or return a sentinel for "phase X not yet present" — it returns a full envelope describing the actual state. An INFRA failure (gh/git error) returns ONE `ok:false` envelope with the verbatim error and all-False `existing` (never retried).

**Evidence:**

```python
def detect_existing(qrspi_dir):
    out = {}
    for name in ARTIFACTS:
        path = os.path.join(qrspi_dir, "%s.md" % name)
        try:
            out[name] = os.path.getsize(path) > 0
        except OSError:
            out[name] = False
    return out
```

— `scripts/qrspi_resolve.py:142-153`
— infra-error → single `ok:false` envelope (all-False existing): `scripts/qrspi_resolve.py:522-531`

**Dependencies:** `detect_existing` (pure), `qrspi_resolve_state.resolve`, `qrspi_pr_state.build_state` (which returns absent-PR shapes with `reviewDecision: None`, `unresolvedThreads: 0` — `qrspi_pr_state.py:293`).
**Implicit contracts:** A `/review-<phase>` command must itself check `existing[<phase>]` (and/or the decision phase) to decide whether the artifact/PR exists — `qrspi_resolve.py` will not error for a not-yet-reached phase. The PR number is not in the envelope (Q1), so absence-of-PR is inferred from the branch set / decision, not a null PR field.

## Q11: How is the "frontier" phase determined for `/review` (comprehensive) and `/review-implementation`, and what happens when the stack is partially built or partially landed?

**Answer:** In `qrspi_resolve_state.resolve`, the frontier is the HIGHEST existing phase: `frontier = max(existing, key=_order)`, where `existing = [p for p in PHASES if phase_exists(phases, p)]` and `phase_exists` requires REAL work (≥1 commit ahead of trunk — `qrspi_pr_state.real_branches`). Phase order is design < plan < implementation. CI is evaluated on the frontier (`ci_state(phases, frontier)`); for implementation the per-slice CI is aggregated (any slice red → red, else any pending → pending, else green/none). Partially-built: a phase whose branch carries no commit ahead of trunk is NOT "real" and not in `existing`. Partially-landed: a MERGED-and-pruned design branch is detected via `design_already_landed` (the `phases.design.merged` flag) so the entry gate does NOT mistake a merged design for an un-started ticket; the resolver falls through to `land`/active-phase logic while an open slice keeps `implementation` in `existing`.

**Evidence:**

```python
frontier = max(existing, key=_order)
fci = ci_state(phases, frontier)
```

— `scripts/qrspi_resolve_state.py:288-289`

```python
def ci_state(phases, name):
    if name == "implementation":
        states = [s.get("ciState", "none") for s in _impl_slices(phases)]
        if any(s == "red" for s in states): return "red"
        if any(s == "pending" for s in states): return "pending"
        if any(s == "green" for s in states): return "green"
        return "none"
    return phases.get(name, {}).get("ciState", "none")
```

— `scripts/qrspi_resolve_state.py:110-126`
— partially-landed (`design_already_landed`): `qrspi_resolve_state.py:141-158,210`
— real-work gate (`real_branches`, trunk-ahead): `scripts/qrspi_pr_state.py:452-482`

**Dependencies:** `resolve` ← `phase_exists`, `ci_state`, `phase_changes_requested`, `phase_comment_targets`, `ci_revise_attempt_of`. `build_state` ← `real_branches`, `slice_numbers`, `branch_set`, gh GraphQL (`statusCheckRollup`).
**Implicit contracts:** "Frontier" = highest REAL (trunk-ahead) phase, not merely highest branch. Implementation is reviewed as a WHOLE stack (CI/comments/change-requests aggregated across all slice PRs). A partially-landed stack is handled by the merge signal so the gather does not misread a pruned design as un-started — the known resolver bug (project memory `resolver-partially-landed-stack`) is when lower PRs merged + top slice open makes the resolver wrongly say `entry_blocked`; a `/review` command should check `gh pr list --state all` before trusting branch-derived state.

## Q12: For AC1's "scratch copy" requirement, how does the existing harness create an isolated working copy of an artifact/worktree without mutating or pushing the open PR branch, and what mechanism guarantees no push occurs?

**Answer:** **NOT FOUND** as an existing mechanism. There is no "scratch copy" helper in the codebase. The closest existing patterns: (1) the critic loop writes/revises the artifact at the STAGING path `/tmp/phase-stage/<id>/<name>.md` (`stg`) which is OUTSIDE the worktree and never committed/pushed by the critic itself — persist (`qrspi_persist.py`) later moves it into the worktree, and only the FINALIZE worker commits via `gt modify`/`gt submit`. (2) The digest is built to `/tmp/phase-stage/<id>/research-digest.md` (a `/tmp` scratch file). No git-level "no push" guarantee mechanism exists — the guarantee in the panel path is structural: `runCriticPanelLoop` only ever `agent()`-spawns lens/reviser agents and writes to `/tmp` staging; the only push is `gt submit` in the separate finalize worker. A `/review-*` command achieving "scratch copy, no push" would build NEW isolation (e.g. copy the artifact to `/tmp`, run the panel against the copy, and simply never invoke any `gt submit`/`gt modify`).

Searched: `grep -rn "scratch copy|scratch-copy|/review-" .claude/ scripts/ docs/` → no hits for scratch-copy; only `stg`/`/tmp/phase-stage` staging pattern found.

**Evidence:**

```javascript
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:633` (the `/tmp` staging convention)
— digest scratch file in `/tmp`: `.claude/workflows/qrspi-batch.js:748`
— pushes happen ONLY in finalize via `gt submit` (separate from the critic loop): `qrspi-batch.js:1603` (design finalize), `:1874,:1894` (impl/submit)

**Dependencies:** Staging pattern shared by `qrspi_persist.py` (`STAGE_ROOT = "/tmp/phase-stage"`, `scripts/qrspi_persist.py:57`).
**Implicit contracts:** "No push" is achieved by SEPARATION OF CONCERNS — the critic/review loop touches only `/tmp` staging and `agent()` spawns; commit/push (`gt submit`/`gt modify`) lives exclusively in finalize/revise workers. There is no enforcement primitive; a `/review-*` command guarantees no-push by simply never calling `gt submit`/`gt modify`/`gh`-write. Reusing `/tmp/phase-stage/<id>/` as the scratch root matches the existing convention.

## Q13: What deterministic seams in the existing critic/synthesis path already have stdlib `scripts/*_test.py` coverage, and how do those tests stub the agent invocations so a new verdict/agreement reducer test follows the same pattern?

**Answer:** The tested pure seams are: `qrspi_critic_synthesize.py` (`qrspi_critic_synthesize_test.py`), `qrspi_critic_loop.py` (`qrspi_critic_loop_test.py`), `qrspi_critic_metrics.py` (`qrspi_critic_metrics_test.py`), `qrspi_metrics_append.py` (`qrspi_metrics_append_test.py`), `qrspi_critics_config.py` (`qrspi_critics_config_test.py`), `qrspi_critic_body.py`, `qrspi_critic_summary.py`, `qrspi_resolve_state.py`, `qrspi_pr_state.py`, etc. The tests do NOT stub agent invocations — the design deliberately SEPARATES the pure reducer (no agent/IO/git coupling) from the harness-coupled JS glue. Tests call the pure function with in-memory dicts/lists and assert the output via a simple `check(label, got, want)` helper (no test-runner framework, assert-based). `run_tests.py` discovers every `scripts/*_test.py` and runs each as its own subprocess, failing non-zero if any fails.

**Evidence:**

```python
def check(label, got, want):
    global failures, total
    total += 1
    if got == want: print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))
```

— `scripts/qrspi_critic_synthesize_test.py:29-36`
— tests call `synthesize([...])` with in-memory verdict lists: `qrspi_critic_synthesize_test.py:40-60`
— `run_tests.py` discovers `*_test.py` and runs each as a subprocess: `scripts/run_tests.py:4-6,36-44`

**Dependencies:** Tests `sys.path.insert(0, _HERE)` then import the sibling pure module. `run_tests.py` is the aggregating runner (also the CI gate `.github/workflows/tests.yml`).
**Implicit contracts:** The unit-test pattern = a pure stdlib function with NO agent/git/IO, tested with literal in-memory inputs via `check(...)`. A new verdict/agreement reducer should be written as a PURE function in `scripts/qrspi_*.py` with a `_test.py` sibling using the same `check` idiom — the agent fan-out stays in the (untested) JS glue. There is NO mocking of `agent()`; you simply don't test the JS.

## Q14: How does the batch path currently post a synopsis/comment to a phase PR (which script/command and which PR), so the advisory synopsis comment for AC1/AC3/AC4/AC5 reuses the same posting mechanism?

**Answer:** Two distinct mechanisms exist. (1) For reviewer-comment replies during `revise`: `scripts/qrspi_comment_reply.py` posts an INLINE threaded reply (`gh api POST /repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies`) or a TOP-LEVEL fresh PR comment (`gh pr comment <pr> --body-file -`); it is self-locating (resolves owner/repo via `gh repo view`), takes `--ticket/--pr/--comment-id/--reply-mode/--body-file`, and prints a `ReplyEnvelope`. Invoked from JS at `qrspi-batch.js:2137`. (2) For critic RESIDUAL FINDINGS surfaced into a PR body (not a comment): `scripts/qrspi_critic_body.py` amends the phase commit message (`gt modify -m`) so Graphite seeds the PR description at creation — invoked via `criticBodyStep` (`qrspi-batch.js:1274`). A fresh advisory SYNOPSIS comment would reuse `qrspi_comment_reply.py` in TOPLEVEL mode (`--reply-mode toplevel`, `gh pr comment`).

**Evidence:**

```python
if reply_mode == REPLY_MODE_TOPLEVEL:
    return {
        "kind": "gh",
        "cmd": ["pr", "comment", str(pr), "--repo", "%s/%s" % (owner, repo),
                "--body-file", "-"],
        "stdin": body,
    }
```

— `scripts/qrspi_comment_reply.py:84-91`
— self-locating owner/repo via `gh repo view`: `qrspi_comment_reply.py:166-180`
— JS invocation in the comment-reply step: `.claude/workflows/qrspi-batch.js:2137`
— residual-findings → PR BODY (commit amend, not a comment): `scripts/qrspi_critic_body.py:198-214`; `qrspi-batch.js:1274`

**Dependencies:** `qrspi_comment_reply.py` ← `qrspi_paths`, `gh` (REST + `gh pr comment`). Requires the PR NUMBER (not in the resolve envelope — must be derived, e.g. `gh pr list --head <branch>`).
**Implicit contracts:** Top-level comment posting = `gh pr comment <pr> --body-file <file>` (body read from a file to avoid shell-quoting). `gh` PR comment writes SUCCEED with the bot's classic PAT (the old cross-account block is gone — project memory). The body file is the token-free input convention. For an advisory synopsis, `--reply-mode toplevel` with `--comment-id` set to any addressed comment (it is unused for toplevel except as `inReplyToId` echo). NOTE: `qrspi_comment_reply.py`'s `--comment-id` is REQUIRED even for toplevel — a synopsis-only post may need a minor relaxation or a dummy id.

## Q15: What does the RUS-78 ledger record per run that enables a future data-gated decision, and where can a human inspect those logged records?

**Answer:** Each ledger line (`CriticMetricsLedgerLine`) records, per terminated critic step: `phase` (e.g. `design`), `rounds` (array of `{lens, pass, findingsCount}` — both the per-lens pass/fail AND the finding count per round, never collapsed to a rate), `terminalAction` (one of `converged|cap_reached|exhausted|aborted`), plus the appender-injected `ticketId`, `timestamp` (UTC ISO-8601), and `runId` (per-invocation id). Optional `tokensIn`/`tokensOut` exist in the schema but are NEVER populated in the live path (the harness exposes no per-subagent token usage — the "at what token cost" dimension is currently UNMET). A human inspects them at `<repo>/.worktrees/<ticket>/.qrspi/<ticket>/critic-metrics.jsonl` (one JSON object per line). This enables a future data-gated decision keyed on `runId`/`ticketId`/`phase` + the per-lens pass/findingsCount trail — but there is NO human-verdict / agreement field recorded yet.

**Evidence:**

```python
record = {
    "phase": phase,
    "rounds": rounds,            # [{lens, pass, findingsCount}, ...]
    "terminalAction": terminalAction,
}
if usage:                        # absent in the live path (OQ2)
    if usage.get("tokensIn") is not None: record["tokensIn"] = usage["tokensIn"]
    if usage.get("tokensOut") is not None: record["tokensOut"] = usage["tokensOut"]
```

— `scripts/qrspi_critic_metrics.py:91-103`
— per-round `{lens, pass, findingsCount}` (pass AND count preserved): `qrspi_critic_metrics.py:82-89`
— `runId` always stamped: `scripts/qrspi_metrics_append.py:67-79`; `runId` source in JS: `.claude/workflows/qrspi-batch.js:118-120`
— inspection path `.../critic-metrics.jsonl`: `scripts/qrspi_metrics_append.py:60-64`

**Dependencies:** `qrspi_critic_metrics.build_record` (pure) → `qrspi_metrics_append.py` (durable append) → JSONL file. Chained in JS `recordCriticMetrics` (`qrspi-batch.js:975-989`).
**Implicit contracts:** `terminalAction` enum is exactly the four loop terminations (`revise` is REJECTED — it is non-terminal). `findingsCount` is derived in PYTHON, never JS. The record is the panel's SELF-report only — adding panel-vs-human agreement requires a new field. The JSONL is append-only, fail-closed on a bad write, and lives in the ticket worktree (not committed unless the finalize worker stages `.qrspi/`).

---

## Discovered Patterns

- **Self-locating deterministic scripts.** Every write/state script (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_comment_reply.py`, `qrspi_critic_body.py`, `qrspi_pr_body.py`) resolves the HOST repo root via `qrspi_paths.resolve_repo_root` (git-common-dir first) so the `qrspi`-laden path is NEVER typed by the weak worker model. New review-command scripts should follow this exact pattern.
- **Pure-core / harness-shell split.** Decision logic lives in pure stdlib Python (`next_action`, `synthesize`, `build_record`, `resolve`) with `_test.py` siblings; the agent fan-out / git mutation lives in non-importable JS glue (`qrspi-batch.js`) and is NOT unit-tested. A new reducer belongs in Python; new orchestration belongs in JS (or a new skill state-machine).
- **PATH-passing, never content.** Agents (including critic lenses) receive named PATH inputs (`DESIGN_PATH = ...`) and Read them themselves; fragile text is never inlined into prompts or echoed through worker stdout (it is piped on stdin or read from `--body-file`/`--findings-file`).
- **`/tmp/phase-stage/<id>/` staging convention** (`stg` / `STAGE_ROOT`) is the token-free scratch root used by both artifact staging and the digest — the natural place for an AC1 "scratch copy".
- **Fail-closed everywhere.** Empty/garbled verdicts, missing digests, bad writes all resolve to NOT-passed / `ok:false` and stop the ticket rather than silently passing.
- **Uniform opt-in critic config.** All critics default OFF; `qrspi_critics_config.resolve_design` is the single resolved source for `enabled`/`maxRounds`/`lenses`/`candidates`/`digest`/`lensModel`.

## Inconsistencies

- **The questions assume an "agreement ledger" (Q7/AC2) and "structured verdict" panel-vs-human agreement keying that DO NOT EXIST.** The RUS-78 ledger (`critic-metrics.jsonl`) records only the PANEL's own per-round verdicts + terminal action + `runId`/`ticketId`/`timestamp`. There is no human-verdict field and no agreement comparison anywhere in the codebase. AC2's "reuse the RUS-78 agreement ledger" must mean "reuse the critic-metrics ledger mechanism and ADD an agreement field" — the agreement concept is net-new.
- **No `/review-*` command family exists** (Q6). The whole `/review-design`, `/review-plan`, `/review`, `/review-implementation` surface is net-new; only the production-phase skills (`qrspi-questions`...`qrspi-pr`) and `qrspi-work` exist.
- **No "scratch copy" mechanism exists** (Q12). "No push" is currently a structural property (critic loop only touches `/tmp` + `agent()`; only finalize pushes), not an enforced primitive.
- **The PR number is absent from the `qrspi_resolve.py` envelope** (Q1/Q14) yet `qrspi_comment_reply.py` requires `--pr`. A `/review-*` command posting a synopsis comment must derive the PR number itself (e.g. `gh pr list --head <ticket>/<phase> --json number`).
- **`qrspi_comment_reply.py --comment-id` is REQUIRED even in `toplevel` mode** (`scripts/qrspi_comment_reply.py:204-206`), though for a fresh synopsis comment there is no comment being replied to — a minor mismatch a synopsis-posting path must work around (pass a placeholder) or relax.
- **Stale doc note:** `qrspi_critic_metrics.py:36-38` flags that `design.md:76` lists only `converged/cap_reached` for `terminalAction`, while the faithful enum is the four-value set (`converged|cap_reached|exhausted|aborted`).
- **`render_findings_section` text says "edge-critic"** (`scripts/qrspi_critic_body.py:134`) even though the only surviving critic is the design PANEL (the edge critic was retired in RUS-88) — a stale label in user-visible PR-body output.
- **`lensModel` may be inert** (Q9): the code comment (`qrspi-batch.js:759-761`) admits there is no evidence the harness honors an `agent()` `model` option, so the speculative cost lever may have no effect.
