# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19
**Status:** draft

## Q1: How does `runPhase` currently sequence the producer agent spawn, the staged-artifact write, and the `qrspi_persist.py` move, and at what point in that sequence could a pre-persist gate intercept the staged artifact before it is moved to the canonical `.qrspi/<id>/` path?

**Answer:** `runPhase` (`.claude/workflows/qrspi-batch.js:512`) runs exactly three deterministic steps in order: (1) a resume short-circuit — `if (existing && existing[name]) return true` skips both the producer and persist for an already-persisted phase; (2) spawn the producer agent via `agent(prompt, {...agentType})`, treating a `null` return as phase failure (`return false`); (3) call `persistArtifact(id, name, phaseLabel)` (`:492`), which shells the worker to `python3 scripts/qrspi_persist.py --ticket <id> --artifact <name>`. The producer writes to the **token-free staging path** `stg(id, name)` = `/tmp/phase-stage/<id>/<name>.md` (`:464`), never the canonical path; `qrspi_persist.py` owns the canonical `.qrspi`-laden destination and `shutil.move`s the staged file there (`scripts/qrspi_persist.py:84-85`). A pre-persist gate has exactly one natural insertion point: **between step 2 (producer returns non-null) and step 3 (persistArtifact)** — the staged file exists at `stg(id, name)` and has NOT yet been moved. The gate would read the staged file (and the upstream inputs already on disk under `.worktrees/<id>/.qrspi/<id>/`), and on failure cause `runPhase` to return `false` (matching the existing failure contract) instead of calling `persistArtifact`.

**Evidence:**

```js
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
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
}
```

— `.claude/workflows/qrspi-batch.js:512-532`

```js
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:464`

**Dependencies:** `runPhase` is called by `doDesign` (`:683`) for `questions`/`research`/`design` and by `doPlan` (`:728`) for `structure`/`plan`/`worktree`. Downstream: `persistArtifact` → `agent()` → `scripts/qrspi_persist.py`. `existing` map originates from the resolver envelope (`detect_existing`, `scripts/qrspi_resolve.py:143`).
**Implicit contracts:** `runPhase` returns a boolean (`true` success, `false` failure/skip); its callers convert `false` to `failTicket(t)`. The producer must write its artifact to the staging path verbatim (agent rule "Write only to OUTPUT_PATH ... verbatim"). `persistArtifact` is the **real per-phase success gate** — an agent that wrote nothing or mangled its path leaves no staged file, so persist fails (`runPhase` comment, `:522-524`).

## Q2: What inputs (ticket text, answered questions, research artifact, REPO_ROOT) are spliced into the `qrspi-design` and `qrspi-plan` spawn prompts today, and how are those inputs passed (inline vs file path)?

**Answer:** **All inputs are passed as absolute file PATHS, never inline content.** The design spawn (`doDesign`, `.claude/workflows/qrspi-batch.js:704-711`) splices: `TICKET_ID`, `TICKET_CONTENT_PATH = r.ticketContentPath` (the resolver-staged ticket text file), `QUESTIONS_PATH = art(wd, id, 'questions.md')`, `RESEARCH_PATH = art(wd, id, 'research.md')`, `OUTPUT_PATH = stg(id, 'design')`, `TEMPLATE_PATH = tpl(wd, 'design.md')`. The plan spawn (`doPlan`, `:738-743`) splices: `TICKET_ID`, `STRUCTURE_PATH = art(wd, id, 'structure.md')`, `DESIGN_PATH = art(wd, id, 'design.md')`, `OUTPUT_PATH = stg(id, 'plan')`, `TEMPLATE_PATH = tpl(wd, 'plan.md')`. Note the **plan spawn does NOT receive the ticket or REPO_ROOT at all** — it only sees structure.md + design.md. The design spawn does NOT receive REPO_ROOT either (the design agent is forbidden codebase exploration). Only the `research` spawn (`:695-702`) passes `REPO_ROOT = wd`. `art`, `tpl`, `stg` are path helpers (`:458-464`); `wd = r.worktreeDir`. `r.ticketContentPath` is emitted by the resolver as a PATH (not the body) specifically to keep fragile Linear ticket text out of the worker stdout round-trip (`qrspi_resolve.py:25` comment).

**Evidence:**

```js
  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design')) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:704-711`

```js
  if (!await runPhase('plan', 'qrspi-plan',
    `TICKET_ID = ${t.id}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
OUTPUT_PATH = ${stg(t.id, 'plan')}
TEMPLATE_PATH = ${tpl(wd, 'plan.md')}`, r.existing, t.id, 'Plan')) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:738-743`

**Dependencies:** Both consume the resolver envelope `r` (`r.worktreeDir`, `r.ticketContentPath`, `r.existing`). The design agent (`.claude/agents/qrspi-design.md:13-16`) accepts the ticket text "one of two ways" — inline `TICKET_CONTENT` OR `TICKET_CONTENT_PATH`; the batch always uses the path form.
**Implicit contracts:** Inputs are file paths the agent must `Read`; the agent must Write only to `OUTPUT_PATH` verbatim. The plan agent never sees ticket text or codebase — so AC-coverage for the plan phase can only be verified transitively through structure.md/design.md, not against the ticket directly.

## Q3: What is the exact invocation contract of `scripts/qrspi_persist.py` (arguments, exit codes, stdout/stderr shape) that the new pre-persist gate would need to run before, and how is its result consumed in `runPhase`?

**Answer:** CLI: `python3 scripts/qrspi_persist.py --ticket <id> --artifact <name>` with optional `--stage-root` (default `/tmp/phase-stage`) and `--repo-root` (default auto-detected via `qrspi_paths.resolve_repo_root`). `--artifact` is constrained to `choices=ARTIFACTS` = `["questions","research","design","structure","plan","worktree"]` (`:52,:101`). It prints **one JSON envelope on stdout** (`json.dump(env, sys.stdout, indent=2)` + `print()`), shape `{ ok, repoRoot, src, dest, bytes, error? }` (`:121-132`). **Exit code:** `0` on success, `1` on failure (`return 0 if error is None else 1`, `:133`). It is self-locating (repo root derived from `__file__` via `qrspi_paths`, never cwd/argument for the engine root). The pure `persist(src, dest)` helper (`:74-92`) is the unit-testable core: returns `(bytes, error)`; errors are "staged artifact not found or unreadable", "staged artifact is empty", "destination not written", "destination is empty after move". In `runPhase`, the result is consumed via `persistArtifact` which returns the parsed envelope; `runPhase` checks `if (!p || !p.ok)` and returns `false` on failure, otherwise logs `p.bytes` (`.claude/workflows/qrspi-batch.js:525-530`). A pre-persist gate would run BEFORE this call (when the staged file still exists at `src`).

**Evidence:**

```python
    env = {
        "ok": error is None,
        "repoRoot": repo_root,
        "src": src,
        "dest": dest,
        "bytes": bytes_written,
    }
    if error is not None:
        env["error"] = error
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:121-133`

**Dependencies:** imports `qrspi_paths` (sibling, `:48`); consumed by `persistArtifact` (`.claude/workflows/qrspi-batch.js:492-505`) parsed against `PERSIST_SCHEMA` (`:445`, requires `ok`).
**Implicit contracts:** Stdout is pure JSON (no prose) so the worker can parse it verbatim; failure reported ONCE as `ok:false` + verbatim `error`, **never retried** (`:24-25` docstring). The model types only short tokens (`--ticket`, `--artifact`); every qrspi-laden path is computed inside the script.

## Q4: What is the established CLI/envelope convention for the tested pure-Python helpers that a new verification-core helper should follow to match `qrspi_resolve.py` / `qrspi_persist.py`?

**Answer:** The convention is strict and consistent across `qrspi_persist.py`, `qrspi_resolve.py`, and `qrspi_ci_revise_bump.py`:
1. **Self-locating engine root:** `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` then `sys.path.insert(0, ENGINE_ROOT)` for sibling imports; host repo root resolved via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (`qrspi_persist.py:45-50`, `qrspi_ci_revise_bump.py:54-59`). Never trust cwd or a positional arg for the engine path.
2. **argparse** with long flags only (`--ticket`, `--artifact`, `--branch`, etc.); short token inputs, never long qrspi paths typed by the model.
3. **Pure functional core + thin `main()`:** filesystem/git-touching `main()` wraps unit-testable pure helpers (e.g. `persist(src, dest)`, `staging_path`, `dest_path` in persist; `detect_existing`, `build_envelope`, `pick_tip` in resolve). Pure helpers take values and return values (no I/O), so they unit-test against temp dirs.
4. **Single JSON envelope on stdout** via `json.dump(env, sys.stdout, indent=2)` followed by a bare `print()` (trailing newline). Envelope always carries `ok` (bool); `error` key present ONLY on failure.
5. **Exit code mirrors `ok`:** `return 0 if error is None else 1`.
6. **Stdlib-only**, no third-party deps (matches `run_tests.py` subprocess model).

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_persist.py:45-50`

```python
    json.dump(env, sys.stdout, indent=2)
    print()
```

— `scripts/qrspi_ci_revise_bump.py:226-227` (same pattern as `qrspi_persist.py:131-132`)

**Dependencies:** All shell out through the batch `agent()` seam (a worker is told to run "EXACTLY this one command verbatim ... parse that JSON and return it"). The JS side validates the parsed envelope against a `*_SCHEMA` requiring `ok` (`PERSIST_SCHEMA`, `.claude/workflows/qrspi-batch.js:445`).
**Implicit contracts:** stdout is ONLY the JSON envelope (no diagnostic prose) — the worker returns it verbatim and the orchestrator parses it; success must NOT be inferred from exit code alone in some callers (`qrspi_ci_revise_bump` worker prompt, `:1196`: "Parse that JSON off its STDOUT (do NOT infer success from the exit code alone)").

## Q5: How do the `qrspi-design.md` and `qrspi-plan.md` agent definitions declare their `tools:` field today, and how is the read-only scoped-to-REPO_ROOT posture (RUS-82) expressed where it already exists in the repo?

**Answer:** Both producer agents declare a **minimal `Read, Write`** toolset in YAML frontmatter under a `claude:` key, and both EXPLICITLY forbid codebase exploration. `qrspi-design.md:4-6` → `claude:\n  tools: Read, Write`; hard constraint `:50`: "Your only reads are the input files ... no codebase exploration." `qrspi-plan.md:4-6` → identical `tools: Read, Write`; hard constraint `:38`: "Your only reads are the three input files. No codebase exploration." Neither grants Grep/Glob. The RUS-82 read-only-scoped posture already exists in the **critic review lenses**: `qrspi-design-critic-design-review.md:4-6` declares `claude:\n  tools: Read, Grep` and is the adversarial NODE-VALIDITY lens that takes a `CODEBASE_PATH` input and is instructed to "Read and Grep real source here to verify the artifact's claims against what the code actually does" (`:16`, `:25`). The plan/impl review lenses mirror this. The research agent itself (`qrspi-research.md`) is the other place a scoped-to-REPO_ROOT read posture exists (it explores the codebase but is firewalled to `REPO_ROOT`).

**Evidence:**

```yaml
---
name: qrspi-design
...
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-design.md:1-6`

```yaml
---
name: qrspi-design-critic-design-review
...
claude:
  tools: Read, Grep
---
```

— `.claude/agents/qrspi-design-critic-design-review.md:1-6`

```
- `CODEBASE_PATH` — absolute path to the repository root. Read and Grep real source here to verify the artifact's claims against what the code actually does.
```

— `.claude/agents/qrspi-design-critic-design-review.md:16`

**Dependencies:** The `*-review` lens is spawned by `.claude/workflows/qrspi-review.js` (on-demand `/review-*`), NOT by the autonomous batch (the batch "runs no phase critics or node-checks", `qrspi-batch.js:687,509-511`).
**Implicit contracts:** A verification-core that needs to confirm codebase claims would need `Read, Grep` (the RUS-82 pattern) scoped to a `CODEBASE_PATH`/`REPO_ROOT` input — the design/plan producers as written CANNOT verify codebase claims (Read/Write only, exploration forbidden). The lens also fails closed: "An unverified claim you cannot confirm is a finding" (`:65`).

## Q6: How does `runPhase` currently represent and propagate a phase failure into the existing revise pass, and what state/flag would a "verification failed → enter revise" outcome reuse versus add?

**Answer:** **There is NO connection today between a `runPhase` failure and the revise pass — they are entirely separate mechanisms.** A `runPhase` failure returns `false`, which the caller (`doDesign`/`doPlan`) converts to `failTicket(t)` → `{ ticketId, action: 'failed', summary: 'A phase agent failed; ticket left untouched (no fabrication).' }` (`.claude/workflows/qrspi-batch.js:1324-1326`). This is terminal-for-this-run: the ticket is left untouched, no PR exists yet, and on re-run `detect_existing` reports the unit as not-done so it recomputes. The **revise pass (`doRevise`, `:918`) is a different, PR-gated action** entirely: it is only reached for an EXISTING frontier PR carrying a formal `CHANGES_REQUESTED`, unaddressed reviewer comments, and/or red CI — driven by the resolver's `revise` decision (`qrspi_resolve_state.py:240-303`), dispatched at `:1653`. `doRevise` operates on a committed branch/PR via `gt`/`gh`, not on a staged pre-persist artifact. So a "verification failed during production → revise" outcome would be a **NEW** path: in-pipeline verification happens BEFORE any commit/PR exists, whereas `doRevise` presupposes a PR. The closest reusable element is the existing `runPhase`-returns-`false` → `failTicket` failure contract (recompute-on-rerun), NOT `doRevise`. A new in-loop "produce → verify → reproduce" gate would have to add its own bounded retry within `runPhase` (there is no existing producer-side retry counter — see Q10).

**Evidence:**

```js
function failTicket(t) {
  return { ticketId: t.id, action: 'failed', summary: 'A phase agent failed; ticket left untouched (no fabrication).' }
}
```

— `.claude/workflows/qrspi-batch.js:1324-1326`

```js
    case 'revise': res = await doRevise(t, r); break
```

— `.claude/workflows/qrspi-batch.js:1653` (revise is dispatched from the resolver decision, not from a producer failure)

**Dependencies:** `failTicket` ← `runPhase` returning false ← producer `null` or persist failure. `doRevise` ← resolver `revise` decision ← `qrspi_pr_state.py` gather of an existing PR.
**Implicit contracts:** The producer pipeline is **pre-commit** (staged artifacts, no PR); `doRevise` is **post-commit** (existing PR, `gt`/`gh` mutations). They share no state/flag today. The honesty posture is uniform: never fabricate; `failTicket`'s summary explicitly says "no fabrication".

## Q7: What is the canonical structure of the design artifact's `## Open Questions` section, and where is that section defined in the design template?

**Answer:** `## Open Questions` is defined in `.qrspi/templates/design.md:43-45` as the sixth and final required section. Its canonical structure is a bulleted list of items prefixed `OQN:` (`- OQ1: <question that needs human input>`), described as "things only a human can answer." The design agent reinforces this: required section 6 is "**Open Questions** — things only a human can answer" (`.claude/agents/qrspi-design.md:38`), and the agent's example summary mentions "2 open questions" (`:29`). There is no machine-enforced schema for OQ items beyond the `OQN:` prose convention; the template uses a single example bullet `OQ1`. This is the natural sink where AC2/AC5-style "unverifiable claim" or "contradicted premise" conversions would be appended — the only section explicitly designated for human-resolvable unknowns.

**Evidence:**

```markdown
## Open Questions

- OQ1: <question that needs human input>
```

— `.qrspi/templates/design.md:43-45`

```
6. **Open Questions** — things only a human can answer.
```

— `.claude/agents/qrspi-design.md:38`

**Dependencies:** The template is read by the design agent at spawn (`TEMPLATE_PATH = tpl(wd, 'design.md')`, `qrspi-batch.js:711`). The on-demand `/review-design` engine "answers the design's open questions" (per `.claude/CLAUDE.md` review-design description), so OQ items are an established downstream consumer.
**Implicit contracts:** OQ items are prose bullets, `OQN:` numbered; "no code blocks, prose and tables only" (`qrspi-design.md:42`). The Current State section is the other claim-bearing section — every sentence there MUST carry `(ref: QN)` back to research.md (`qrspi-design.md:33,43`; template `:11`), which is the existing convention for grounding design claims in upstream evidence.

## Q8: How is a ticket's set of acceptance criteria currently surfaced to the design/plan producers (AC3 completeness mapping), and what happens to the AC-coverage check when the ticket has zero or malformed acceptance criteria?

**Answer:** **ACs are surfaced ONLY as raw ticket markdown text to the DESIGN producer, and NOT AT ALL to the PLAN producer; there is no machine-readable AC extraction or coverage check anywhere in the codebase.** ACs live in the ticket as a free-form checklist: `.qrspi/templates/ticket.md:21-24` defines `## Acceptance Criteria` with `- [ ] AC1: ...` / `- [ ] AC2: ...` items. The full ticket text (title + description, including that section verbatim) is staged by the resolver to a token-free file and surfaced to the design agent via `TICKET_CONTENT_PATH = r.ticketContentPath` (`qrspi-batch.js:706`; `qrspi_resolve.py:25` comment). The design agent is told (instruction-only, not enforced) to map "every acceptance criterion from the ticket" into Desired End State (`qrspi-design.md:34` section requirement; `:44` rule 3). The **plan agent receives only structure.md + design.md, never the ticket** (`qrspi-batch.js:738-743`), so it cannot check AC coverage against the ticket — it inherits whatever ACs the design carried forward. **Zero/malformed AC handling:** there is no code path that parses, counts, or validates ACs, so an empty or malformed `## Acceptance Criteria` section degrades silently — the design agent simply has nothing to map, and no error/finding is raised. A verification-core implementing AC3 completeness would be the FIRST mechanism to extract ACs from ticket text and would have to define the zero/malformed behavior itself.

**Evidence:**

```markdown
## Acceptance Criteria

- [ ] AC1: <outcome observable by a user or stakeholder>
- [ ] AC2: <outcome observable by a user or stakeholder>
```

— `.qrspi/templates/ticket.md:21-24`

```
3. Every acceptance criterion from the ticket appears in Desired End State.
```

— `.claude/agents/qrspi-design.md:44` (an instruction to the LLM, not a machine check)

**Dependencies:** Ticket text flows resolver (`ticketContentPath`) → design agent only. The plan agent's only ticket-derived inputs are transitive (structure.md ← design.md ← ticket).
**Implicit contracts:** AC coverage is currently an LLM-honored prose instruction, never verified. The design agent CANNOT explore the codebase to verify an AC is achievable (Read/Write only, Q5). The plan agent has no ticket access at all — an AC3 plan-phase check would need the ticket text plumbed into the plan spawn (a new input that does not exist today).

## Q9: What does the existing persist/revise path do when the staged artifact is missing or empty, and how would a verification gate distinguish "no verification signal present" from "verification ran and failed"?

**Answer:** `qrspi_persist.py`'s pure `persist(src, dest)` (`:74-92`) handles missing/empty deterministically and fail-loud: a missing/unreadable `src` → `(0, "staged artifact not found or unreadable: <src>")`; a zero-byte `src` → `(0, "staged artifact is empty: <src>")`; both yield envelope `ok:false` + that verbatim error and exit 1. `runPhase` consumes this via `persistArtifact` and treats `!p.ok` as phase failure → `false` → `failTicket` (`qrspi-batch.js:525-528`). This is the existing **"no artifact" gate**. For a NEW pre-persist verification gate, the "no verification signal present → behave exactly as today" vs "verification ran and failed" distinction has a clean basis in the existing fail-closed conventions: the verification-core should emit a tri-state in its JSON envelope (the existing pattern is a single `ok` bool plus optional `error`; a verification-core would extend to e.g. `{ ok, verified: true|false, findings: [...] }` or a `signal: "none"|"pass"|"fail"` field). The CLAUDE.md/docstring convention is **fail toward the safe direction** — resolver "fail toward blocking" (`qrspi_resolve.py` blocker classification, RD3) and the review lens "An unverified claim you cannot confirm is a finding (fail closed)" (`qrspi-design-critic-design-review.md:65`). "No signal present" = the gate found nothing to verify (e.g. no codebase claims, no ACs) and must pass through unchanged (the AC: "behave exactly as today"); "ran and failed" = the gate verified a specific claim/AC and it was false/uncovered, producing findings that route to revise/Open-Questions. These are distinguished by **whether findings is empty AND whether any verifiable signal existed**, exactly mirroring the lens invariant `pass:false ⟺ findings non-empty` (`qrspi-design-critic-design-review.md:46-48`).

**Evidence:**

```python
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
```

— `scripts/qrspi_persist.py:78-83`

```
> `pass:false ⟺ findings non-empty`. Pass with findings is forbidden; fail with no findings is forbidden.
```

— `.claude/agents/qrspi-design-critic-design-review.md:48`

**Dependencies:** `persist` ← `main()` ← worker ← `runPhase`. The fail-closed posture is shared by `qrspi_resolve_state.py` (blocker classification) and the review lenses.
**Implicit contracts:** Persist already refuses zero-byte files at BOTH ends (src empty AND dest empty after move, `:82,:90`). A verification gate distinguishing "no signal" from "failed" should encode it as an explicit envelope field, not overload `ok` (which today means only "the move succeeded"). The "behave exactly as today" AC maps to: gate emits no findings → `runPhase` proceeds to persist unchanged.

## Q10: How is the revise loop bounded today, so a verification gate that repeatedly fails does not loop indefinitely?

**Answer:** The ONLY bounded revise loop today is the **CI-revise cap** (RUS-81/RUS-83), and it bounds the PR-gated CI-failure revise — NOT producer-side verification. The mechanism: a `CI-Revise-Attempt: N` head-commit trailer counts consecutive red revises. The resolver `resolve(state, ci_revise_cap=3)` reads the effective count via `ci_revise_attempt_of(phases, name)` (`qrspi_resolve_state.py:129-134`, which `max(...)`-aggregates per-slice counts for implementation) and, in the CI-gated slot (`:289-303`): if `attempt < ci_revise_cap` → `revise` (ciFailing=True); else → `wait` with `ciGaveUp=True` (parked for manual diagnosis). The cap is configurable via the flat `ciReviseCap` key in `.qrspi/config.json` (default 3; non-positive/non-integer → 3). The counter has **two resets**: a read-side reset in the gather (`ciReviseAttempt` forced to 0 whenever rollup ≠ red) and a writer-side reset in `doRevise` (`resetCiReviseTrailer`, `:1032-1037`, every non-CI amend overwrites to 0); the bump is orchestrator-owned via `bumpCiReviseTrailers` → `qrspi_ci_revise_bump.py` (`:1026,:1192-1205`). **There is NO equivalent bound on a producer-side verification loop** — `runPhase` runs the producer exactly ONCE and either succeeds (persist) or fails (`failTicket`, terminal-for-run). So an in-loop "produce → verify → reproduce-if-failed" gate would need a NEW, distinct attempt counter; the `CI-Revise-Attempt` trailer is unusable here because it lives on a committed PR head, and verification happens pre-commit. The natural model is a small in-`runPhase` retry bound (e.g. produce up to N times, then `failTicket`), mirroring the cap-then-give-up shape (`ciGaveUp`).

**Evidence:**

```python
        attempt = ci_revise_attempt_of(phases, frontier)
        if attempt < ci_revise_cap:
            return decision("revise", phase=frontier, ciFailing=True,
                            ...
        return decision("wait", phase=frontier, ciFailing=True, ciGaveUp=True,
                        ...
```

— `scripts/qrspi_resolve_state.py:291-303`

```python
def ci_revise_attempt_of(phases, name):
    """The effective consecutive-red CI-revise attempt count for phase `name` ...
    Missing/absent -> 0."""
```

— `scripts/qrspi_resolve_state.py:129-134`

**Dependencies:** Cap read by `resolve()`; trailer written by `qrspi_ci_revise_bump.py` (bump) and the revise worker reset path; surfaced as `ciGaveUp` onto skip/result records (`qrspi-batch.js:472,1661,1670`).
**Implicit contracts:** A bounded loop must (1) count consecutive failures durably, (2) cap-then-park with a visible give-up signal (`ciGaveUp` is the precedent), (3) reset on success. The producer pipeline has none of this — it is single-shot — so a verification gate must supply its own bound. Pre-commit verification cannot reuse the commit-trailer counter.

## Q11: What is the structure and convention of the existing stdlib-only `_test.py` siblings and the aggregating runner that a new `scripts/<verification-core>_test.py` must conform to?

**Answer:** Convention (enforced by `scripts/run_tests.py`): (1) Each test is `scripts/<name>_test.py`, a **standalone, stdlib-only, assert-based** script (no pytest) that exits 0 on success / non-zero on first failure (`qrspi_resolve_state_test.py:1-7` docstring). (2) It imports the module under test directly by name (`from qrspi_resolve_state import resolve`, `:11`) — works because tests live beside the modules in `scripts/`. (3) Tests build small fixture dicts via local helpers (e.g. `_phase`, `_slice`, `state`, a `CASES = []` table, `qrspi_resolve_state_test.py:14-59`) and assert pure-function behavior; I/O-touching helpers are tested against temp dirs. (4) `run_tests.py` auto-discovers every `scripts/*_test.py` (`discover_tests`, `:36-48`), runs each as its **own subprocess** with `sys.executable` and a 180s timeout (`run_one`, `:51-75`), prints per-file PASS/FAIL + aggregate, and exits non-zero if any fail (`main`, `:107-138`). No registration is needed — dropping a `*_test.py` into `scripts/` is sufficient; the CI gate (`.github/workflows/tests.yml`) runs the same runner. The runner itself (`run_tests.py`) and `run_tests_test.py` are handled specially (`:30-33`). A new `scripts/<verification-core>_test.py` must: be self-contained, import the new core by name, use assert-based CASES, exit non-zero on failure, and require no dependency beyond stdlib.

**Evidence:**

```python
from qrspi_resolve_state import resolve
...
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0, comments=None,
           merged=False, ci_state="none", ci_attempt=0):
    return {"branchExists": branch, ...}
...
CASES = []
```

— `scripts/qrspi_resolve_state_test.py:11-59`

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    ...
def run_one(path, python=None, timeout=DEFAULT_TIMEOUT):
    proc = subprocess.run([python, path], capture_output=True, text=True, timeout=timeout)
    ok = proc.returncode == 0
```

— `scripts/run_tests.py:36-67`

**Dependencies:** Discovery is filename-suffix-based (`*_test.py`); subprocess isolation means a test must be runnable as `python3 scripts/<name>_test.py` from any cwd. CI: `.github/workflows/tests.yml` (per CLAUDE.md).
**Implicit contracts:** Zero-registration discovery; subprocess isolation (a hung/segfaulting test fails its own subprocess, not the suite); stdlib-only (no `requirements.txt` install needed for the suite). Test the **pure core**, not the I/O `main()` (the resolve/restack/cleanup `main()` serializers are explicitly NOT pinned, per `docs/testing-dynamic-workflows.md:163-182`).

## Q12: How is the JS↔Python contract between `qrspi-batch.js` and the pure-Python helpers currently exercised, so the new gate's JS-to-core seam is covered?

**Answer:** Via **committed contract/golden fixtures** asserted from BOTH sides (RUS-76), documented in `docs/testing-dynamic-workflows.md:124-182`. The contract lives at `scripts/fixtures/contract_seam/<seam>/<variant>.json` (existing seams confirmed on disk: `cleanup, config, critics, land, ordered-tickets, resolve, restack, sync-trunk`). Two test files assert against the same goldens: (a) **producer side** — `scripts/qrspi_contract_fixtures_producer_test.py` asserts each Python producer's actual output conforms (shape + byte-for-byte serialization) to that seam's `wellformed.json`; (b) **consumer side** — `scripts/qrspi_contract_fixtures_consumer_test.py` drives `scripts/contract_seam_runner.js`, a `node:vm` harness that loads `qrspi-batch.js` via the strip-`export` + async-wrap + injected-globals recipe and exposes the JS `parse*` functions through an appended shim, asserting each parser accepts the well-formed fixture and fail-closes (exact sentinel shape) on malformed/edge variants. It skips cleanly when `node` is absent (`shutil.which("node")`). Both are `scripts/*_test.py` auto-discovered by `run_tests.py`. Coverage is "all eight `parse*` seams." **Two documented limitations:** (a) silent-seam debuggability gap for `parseOrderedTickets`/`parseCriticsEnvelope` (guarded by value-difference, not sentinel); (b) the resolve/restack/cleanup `main()` serializers are NOT pinned (the producer test re-serializes via hardcoded `json.dumps` kwargs rather than exercising `main()`'s own `json.dump`/`print`). For a new gate: add a `contract_seam/<verification-core>/` fixture set and assert the producer (Python) + the consumer (a new JS `parseVerification*` parser, if the batch needs one) against it.

**Evidence:**

```
   - **Producer side:** `scripts/qrspi_contract_fixtures_producer_test.py`
     asserts each Python producer's actual output conforms ... to that seam's `wellformed.json`.
   - **Consumer side:** `scripts/qrspi_contract_fixtures_consumer_test.py`
     drives `scripts/contract_seam_runner.js` (a `node:vm` harness that loads
     `qrspi-batch.js` ... and exposes the parsers through an appended shim) ...
```

— `docs/testing-dynamic-workflows.md:135-145`

**Dependencies:** `qrspi_contract_fixtures_{producer,consumer}_test.py` ↔ `scripts/contract_seam_runner.js` ↔ `qrspi-batch.js` ↔ `scripts/fixtures/contract_seam/<seam>/*.json`. `qrspi-batch.js` is otherwise NOT unit-testable (top-level `return`, injected globals, no `import`/`require` — `docs/testing-dynamic-workflows.md:30-44,204-228`).
**Implicit contracts:** The contract is "as strong as the fixtures are complete" — each JS parser validates only the fields it dereferences; other envelope fields are guarded only by the producer-side byte match (`docs/testing-dynamic-workflows.md:153-161`). If the new verification core's envelope is consumed by `qrspi-batch.js` via a new parser, that parser belongs in the consumer-test seam set; if the batch returns it verbatim (like the persist envelope, validated by `PERSIST_SCHEMA` not a `parse*` fn), the producer-side fixture + the JS `*_SCHEMA` suffice.

## Q13: How does `runPhase` currently surface a phase outcome (logs, recorded result codes, the batch run summary) so that a verification-gate failure and the resulting revise pass are visible in the run output?

**Answer:** Outcomes surface at three layers. (1) **`log()` lines** (an injected harness global, not defined in-file): `runPhase` logs reuse (`reusing existing ${name}.md`, `:514`), persist success (`${name} → saved ${p.bytes}B`, `:530`), and two failure forms — producer null (`${name} phase failed or was skipped`, `:519`) and persist failure (`${name} reported done but no artifact was staged/persisted — ${p?.error}`, `:527`). (2) **Recorded result objects** pushed to the `results` array (`qrspi-batch.js:1607,1663`): each action handler returns `{ ticketId, action, summary, newStatus?, prUrl? }`; a producer/persist failure becomes `failTicket` → `action: 'failed'` (`:1324`); finalize failures become `finResult` → `action` + a `... finalize failed: <error>` summary (`:1327-1332`). Special flags ride the record: `ciGaveUp`, `ciReviseBumpFailed`, `reconcileRetry` (`:472,1029,1319`). (3) **Per-ticket dispatch log + run summary**: the main loop logs `[i/N] <id> → <action> (newStatus) (flags...)` (`:1670`) and the workflow returns `{ ticketsProcessed: results.length, results, reconciliation }` as the final envelope (`:1682`). A verification-gate failure inside `runPhase` would naturally surface as: a `log()` line at the gate, `runPhase` returning `false`, and the ticket recorded as `action: 'failed'` (or a new dedicated action/summary). To make the verification specifically visible (vs a generic "agent failed"), the gate should emit a distinct log line and a distinguishing summary/flag on the result record — mirroring how `ciGaveUp` is carried onto skip/result records and re-printed in the dispatch log (`:1661,1670`).

**Evidence:**

```js
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:525-530`

```js
    results.push(res)
    ...
    log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}${res.ciGaveUp ? ' (CI-revise cap reached ...)' : ''}...`)
```

— `.claude/workflows/qrspi-batch.js:1663-1670`

**Dependencies:** `log`/`phase` are injected harness globals (`docs/testing-dynamic-workflows.md:36-37`). `results` is returned as the run envelope (`:1682`). `finResult`/`failTicket`/`skip` shape the records (`:1324-1333,466-474`).
**Implicit contracts:** Every result object carries `ticketId`, `action`, `summary`; optional `newStatus`/`prUrl`/flags. The final return `{ ticketsProcessed, results, reconciliation }` is the machine-readable run summary. A failed phase NEVER advances the ticket (records `failed`, leaves PR/Linear untouched) — the honesty/no-fabrication posture; a new gate failure must follow the same "record + don't advance" contract.

---

## Discovered Patterns

- **Staging + deterministic move (Fix A)** is the spine of every producer phase: the weak worker writes to a token-free `/tmp/phase-stage/<id>/<name>.md` path it cannot corrupt, and a self-locating Python script owns the qrspi-laden canonical path and verifies non-emptiness. Persist is "the real per-phase success gate" (`qrspi-batch.js:522-524`). A new pre-persist verification gate slots into exactly this seam.
- **Functional Core / Imperative Shell** is the documented, enforced architecture: all deterministic logic lives in unit-tested `scripts/*.py`; `qrspi-batch.js` is a logic-starved shell that only shells out and parses JSON. New deterministic logic MUST be a Python helper with a `_test.py` sibling, never inline JS (`docs/testing-dynamic-workflows.md:107-114`).
- **Single JSON envelope on stdout** (`{ ok, ..., error? }`, `indent=2` + trailing `print()`, exit code mirrors `ok`) is the universal helper-to-worker contract, validated JS-side against a `*_SCHEMA` requiring `ok`.
- **Fail-closed / fail-toward-blocking** posture pervades: resolver blocker classification (RD3), the review lens "unverified claim → finding" (`qrspi-design-critic-design-review.md:65`), persist refusing empty files. A verification gate should adopt the same direction.
- **`pass:false ⟺ findings non-empty`** is the canonical verdict invariant in the RUS-82 review lenses — a ready-made shape for a verification verdict, with an OPTIONAL `nonBlockingNotes` advisory channel that surfaces real-but-non-material observations without gating.
- **Cap-then-park-with-visible-give-up** (`CI-Revise-Attempt` trailer + `ciGaveUp`) is the only bounded-retry precedent; it lives on committed PR heads and is unusable pre-commit, so a producer-side gate needs its own bound.
- **The autonomous batch runs NO in-pipeline critics/node-checks** — they were all removed; the on-demand `/review-*` family (`qrspi-review.js`, RUS-93) is the surviving review path, and it is propose-only/advisory (never mutates the branch or advances the lifecycle). A new in-pipeline verification gate would be a deliberate re-introduction of an in-loop check, distinct from the advisory `/review-*` engine.

## Inconsistencies

- **Plan agent's input asymmetry vs AC-coverage intent.** The design agent is told to map "every acceptance criterion from the ticket" (`qrspi-design.md:44`) and receives the ticket text; the plan agent (`qrspi-plan.md`) receives ONLY structure.md + design.md and never sees the ticket — yet the plan phase is where atomic steps that must satisfy ACs are written. A plan-phase AC3 completeness check cannot work against the ticket today because the ticket is not plumbed into the plan spawn (`qrspi-batch.js:738-743`).
- **AC "mapping" is instruction-only, never verified.** `qrspi-design.md:44` rule 3 ("Every acceptance criterion from the ticket appears in Desired End State") reads as a guarantee, but nothing extracts, counts, or checks ACs — it is an LLM-honored prose instruction. A ticket with zero/malformed ACs degrades silently with no error.
- **Design agent cannot verify the codebase claims it is required to make.** The design template/agent require every Current State sentence to carry `(ref: QN)` and Pattern Decisions to "reference existing codebase patterns" (`qrspi-design.md:33,45`; template `:11`), yet the agent is Read/Write-only with codebase exploration explicitly forbidden (`:50`). Verification of those claims against real source exists ONLY in the separate RUS-82 `*-review` lens (Read/Grep + CODEBASE_PATH), which the autonomous batch does NOT run.
- **`ok` is overloaded for the persist envelope.** `qrspi_persist.py`'s `ok` means only "the move succeeded" — it is not a content-validity signal. A verification gate reusing/extending this envelope must add an explicit field (not overload `ok`) to distinguish "no verification signal present" from "verification ran and failed" (Q9).
- **Docstring drift in `qrspi-design.md`.** Line 20 documents a `FRAMING` input and an "N-select stage" ("the N-select stage wants this candidate biased toward"), but per CLAUDE.md/`testing-dynamic-workflows.md:201` the N-select stage and the in-pipeline design panel "were all removed" from the autonomous batch — the FRAMING/N-select prose is stale relative to the current single-produce batch path (`qrspi-batch.js:704` passes no FRAMING).
