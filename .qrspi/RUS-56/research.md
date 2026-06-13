# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

> **Top-level finding (load-bearing for every answer below):** The "foundation
> loop (1/5)" JS glue — `runCriticLoop` and the optional `criticConfig` parameter
> on `runPhase` — that this ticket's questions assume already exists is **NOT
> landed in this worktree**. RUS-55 (1/5) landed only Slices 1–2: the pure
> decision module `scripts/qrspi_critic_loop.py`, its test, the `qrspi-critic`
> agent, and the `qrspi-critic` skill. Slice 3 (wiring `runCriticLoop` into
> `runPhase` and passing `criticConfig` from `doDesign`/`doPlan`) was planned
> (`.qrspi/RUS-55/worktree.md:60-81`) but **the implementation is absent from
> `.claude/workflows/qrspi-batch.js`** — `grep` for `criticConfig`, `runCriticLoop`,
> `CRITIC_VERDICT_SCHEMA`, "lens", "panel", "synthesize", "maxRounds" all return
> ZERO hits in that file (verified below). Many questions ask about a multi-lens
> *panel* + *synthesize* stage; the codebase today has only a **single-critic**
> primitive and not even its orchestration wiring. Each answer states what exists
> vs. what is NOT FOUND.

---

## Q1: How does the design phase currently move from producing `design.md` to submitting the design PR, and at what point would a critic panel + synthesize + revise stage be inserted into that sequence?

**Answer:** The design phase is driven by `doDesign(t, r)` in the batch workflow. It calls `runPhase()` three times in sequence — `questions`, `research`, `design` — then runs a `Finalize` agent that commits the three artifacts onto the `<id>/design` branch and submits the PR. Each `runPhase` call (1) short-circuits if the artifact already exists, (2) spawns the phase agent which writes to a token-free staging path `stg(id,name)`, then (3) calls `persistArtifact` which moves the staged file to the canonical worktree path and is the real success gate. There is currently **no critic step between produce and persist** — `runPhase` has no `criticConfig` parameter, and `runCriticLoop` does not exist in the file.

Per the (unlanded) RUS-55 design, the panel/critique/revise stage is meant to sit **inside `runPhase`, between the produce `agent()` call and the `persistArtifact` gate**, because that is the only window where the just-produced artifact is still at `stg(id,name)` and not yet moved (`.qrspi/RUS-55/design.md:28-31,57-66`). For RUS-56 (Design edge critic), the critic would judge `design.md` against its upstream input.

**Evidence:**

```
async function doDesign(t, r) {
  const wd = r.worktreeDir
  phase('Design')
  if (!await runPhase('questions', 'qrspi-questions', ... )) return failTicket(t)
  if (!await runPhase('research', 'qrspi-research', ... )) return failTicket(t)
  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
...
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design')) return failTicket(t)
  phase('Finalize')
  const fin = await agent(`You are the DESIGN-PHASE finalize worker for ${t.id} ...`, ...)
  return finResult(t, fin, 'run_design')
}
```

— `.claude/workflows/qrspi-batch.js:594-633`

```
async function runPhase(name, agentType, prompt, existing, id, phaseLabel) {
  if (existing && existing[name]) { ...; return true }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { ...; return false }
  const p = await persistArtifact(id, name, phaseLabel)   // <-- insertion point is ABOVE this line
  if (!p || !p.ok) { ...; return false }
  ...
  return true
}
```

— `.claude/workflows/qrspi-batch.js:458-478`

**Dependencies:** `doDesign` → `runPhase` → `agent()` (runner primitive) + `persistArtifact` → `scripts/qrspi_persist.py`. Finalize → `gt modify -c` / `gt submit --publish` (Graphite). The non-batch entry path is `/qrspi-design` (`.claude/skills/qrspi-design/SKILL.md`) → the `qrspi-design` agent (`.claude/agents/qrspi-design.md`); that path does NOT go through `runPhase` and has no critic seam at all.
**Implicit contracts:** The produced artifact lives at `stg(id,name)` ONLY in the produce→persist window; after persist it is at `art(wd,id,name)`. A critic inserted here must rewrite `stg(id,name)` in place and never empty it, or the downstream non-empty persist check turns into `ok:false` and stops the ticket (`.qrspi/RUS-55/design.md:106`).

## Q2: How are the upstream artifacts (ticket, `research.md`, `questions.md`) and `design.md` located and read during the design phase, so each lens can be handed them as its rubric?

**Answer:** All artifact paths are computed by two pure JS path helpers in the batch workflow: `art(wd, id, name)` for the canonical persisted path and `stg(id, name)` for the token-free staging path. The design agent is handed `QUESTIONS_PATH` and `RESEARCH_PATH` as `art(wd, t.id, 'questions.md')` / `art(wd, t.id, 'research.md')` (already persisted by their own `runPhase` gate) and writes its output to `stg(t.id, 'design')`. The ticket text is NOT inlined into the prompt; it is staged to a token-free file by the resolve worker and passed as `r.ticketContentPath` (`TICKET_CONTENT_PATH`), which the design agent Reads. So for the (single) critic in RUS-56, the **upstream anchor** = `art(wd,id,'research.md')` (the canonical persisted path) and the **produced artifact** = `stg(id,'design')` (still in staging, pre-persist) — this matches the RUS-55 design's AC3 (`.qrspi/RUS-55/design.md:30`).

**Evidence:**

```
const art = (wd, id, name) => `${wd}/.qrspi/${id}/${name}`
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:413,418`

```
  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design')) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:614-621`

**Dependencies:** `r.ticketContentPath` / `r.worktreeDir` come from `resolveTicket` → `scripts/qrspi_resolve.py` envelope. `art(...)` paths depend on `persistArtifact`/`scripts/qrspi_persist.py` having already run for each upstream artifact.
**Implicit contracts:** Ticket text never round-trips through worker stdout (HTML-escaping corrupts it, RUS-69) — it is always a file Read. A critic handed `stg(id,'design')` must read the *staged* copy, because the canonical `art(...)` design path does not exist yet at critic time (persist runs after).

## Q3: What interface does the "foundation loop (1/5)" expose for running M lenses in parallel, and what arguments does it accept (lens definitions, inputs, maxRounds)?

**Answer:** **NOT FOUND as a parallel/multi-lens interface — and the JS orchestration interface is not landed at all.** What exists from 1/5 is a **single-critic, single-verdict** pure decision core, `scripts/qrspi_critic_loop.py`, exposing two functions:
- `next_action(verdicts, round, max_rounds) -> {action, residual_findings}` where `action ∈ {"converged","revise","cap_reached"}`. It takes `verdicts` (a *list* of already-parsed `{pass, findings}` dicts; a single-critic edge yields a one-element list — the docstring explicitly notes OQ2), the current `round` index, and the per-phase cap `max_rounds`. The **last** verdict is authoritative.
- `parse_critic_verdict(text) -> {pass, findings}` — fail-closed parser.

The function takes the *already-parsed* verdict(s); it does NOT run lenses, spawn agents, or do parallelism. The intended JS glue `runCriticLoop(name, id, criticConfig, ...ctx) -> {ok, residualFindings}` (which would spawn the critic agent per round and delegate the decision to this module) is described in `.qrspi/RUS-55/design.md:48` and `.qrspi/RUS-55/worktree.md:72` but **does not exist in `.claude/workflows/qrspi-batch.js`** (verified: zero hits for `runCriticLoop`/`criticConfig`). RUS-55 OQ2 (`.qrspi/RUS-55/design.md:115`) explicitly pinned the primitive to a **single critic per round — not a `parallel()` fan-out** — deferring any multi-critic fan-out to the per-phase tickets (2/5–5/5). So a *parallel M-lens panel* is exactly the new capability RUS-56 would have to introduce; the foundation provides no such interface.

**Evidence:**

```
def next_action(verdicts, round, max_rounds):
    """...`verdicts` is the list of already-parsed `{pass, findings}` verdict dicts produced this
    round (a single-critic edge yields a one-element list — OQ2). The LATEST verdict (last
    element) is authoritative for this round. Returns:
        {"action": "converged"|"revise"|"cap_reached", "residual_findings": [...]}
    ...
    Signature: next_action(verdicts: list, round: int, max_rounds: int) -> dict"""
```

— `scripts/qrspi_critic_loop.py:80-101`

```
$ grep -n "runCriticLoop\|criticConfig\|maxRounds\|lens\|panel" .claude/workflows/qrspi-batch.js
(no output)
```

— verified at `.claude/workflows/qrspi-batch.js` (whole file)

**Dependencies:** `qrspi_critic_loop.py` is pure stdlib (json, re); no agent/IO coupling by design (`scripts/qrspi_critic_loop.py:25-27`). The JS consumer is missing.
**Implicit contracts:** `verdicts` is a *list*; callers pass one element for the single-critic case. `round`/`max_rounds` are `int()`-coerced (accept str). An empty list reads as NOT-passed (fail closed).

## Q4: What is the exact findings schema each lens must emit, and where is the schema validation performed for lens output?

**Answer:** The verdict schema is `{pass: bool, findings: list}`. Each `findings` entry is a self-contained string that **names the specific upstream requirement** affected and states how the produced artifact drops/contradicts/distorts it. The schema is defined narratively in the critic agent system prompt (`.claude/agents/qrspi-critic.md:36-42`) where it is named `CRITIC_VERDICT_SCHEMA` and described as "validated at the runner boundary." **Two validation layers are intended, but only one exists:**
- **Primary (NOT FOUND):** runner-level `StructuredOutput` validation against a JS constant `CRITIC_VERDICT_SCHEMA` in `qrspi-batch.js`. RUS-55 Decision 2 Option A chose this (`.qrspi/RUS-55/design.md:68-77`), but the constant is **not present** in `qrspi-batch.js` (zero hits), consistent with Slice 3 being unlanded.
- **Defensive backstop (EXISTS):** `parse_critic_verdict(text)` in `scripts/qrspi_critic_loop.py:49-77`, plus the shared coercer `_coerce_verdict(obj)` (`:34-46`). These coerce arbitrary parsed objects into the canonical shape, failing closed (`{pass: False, findings: []}`) on any malformed/empty/non-dict input, and never raise.

**Evidence:**

```
def _coerce_verdict(obj):
    if not isinstance(obj, dict):
        return {"pass": False, "findings": []}
    passed = bool(obj.get("pass", False))
    findings = obj.get("findings", [])
    if not isinstance(findings, list):
        findings = [findings] if findings else []
    return {"pass": passed, "findings": findings}
```

— `scripts/qrspi_critic_loop.py:34-46`

```
Emit exactly this shape (validated as `CRITIC_VERDICT_SCHEMA` at the runner boundary):
- `pass` (bool) — `true` only when the produced artifact is a faithful derivation ...
- `findings` (list) — one entry per problem ... names the specific upstream requirement ...
```

— `.claude/agents/qrspi-critic.md:37-42`

**Dependencies:** The intended `CRITIC_VERDICT_SCHEMA` would live alongside the other schemas (`WORKER_SCHEMA`, `PERSIST_SCHEMA`, etc. at `.claude/workflows/qrspi-batch.js:336-411`). The Python backstop has no external dependency.
**Implicit contracts:** `pass: true` SHOULD carry empty findings; `pass: false` MUST carry non-empty findings each naming the upstream item (`.claude/agents/qrspi-critic.md:42`). A truthy non-bool `pass` (e.g. `1`) is coerced to `bool`; a scalar `findings` string is wrapped into a one-element list (`scripts/qrspi_critic_loop.py:43-45`).

## Q5: How is `maxRounds` (default 2) configured and passed into a phase's critic loop, and is it overridable per-phase or per-run?

**Answer:** The design intent (RUS-55 OQ4, RESOLVED "per phase configurable") is that `maxRounds` is **per-phase configurable via `criticConfig`**, read as `criticConfig.maxRounds ?? 2` inside `runCriticLoop`, with the default `2` applied only when a `criticConfig` omits the field; there is to be **no module-level `maxRounds` constant** (`.qrspi/RUS-55/design.md:29,50,117`). Each `doDesign`/`doPlan` would pass its own `criticConfig {upstream:'...', maxRounds:N}`. The pure module already honors this: `next_action`'s `max_rounds` is a plain parameter (no default in the module). **However, none of this configuration surface exists yet:** there is no `criticConfig` in `qrspi-batch.js`, and `.qrspi/config.example.json` carries NO critic keys (only `reviewers`, `teamReviewers`, `linearTeam`, `linearProject`). So today `maxRounds` is **not** sourced from `.qrspi/config.json` — the design routes it through the JS `criticConfig` literal per phase, not the config file. Per-*run* overridability is NOT FOUND (no config or input plumbing for it).

**Evidence:**

```
{
  "reviewers": ["@me"],
  "teamReviewers": [],
  "linearTeam": "Your Linear Team",
  "linearProject": "QRSPI"
}
```

— `.qrspi/config.example.json` (no `maxRounds`/critic key)

```
`maxRounds` is **per-phase configurable via `criticConfig`**, not a fixed constant.
... `runCriticLoop` reads the cap from `criticConfig.maxRounds ?? 2`, and `runPhase`
forwards the whole `criticConfig` ... there is no module-level `maxRounds` constant.
```

— `.qrspi/RUS-55/design.md:117`

**Dependencies:** Config keys, if ever added, would be read via `scripts/qrspi_config.py` (`--key <name>`; `DEFAULTS = {"linearProject": "QRSPI"}`, unknown keys default to ""). That helper currently has no critic key.
**Implicit contracts:** `next_action(round, max_rounds)` int-coerces both args; cap is reached when `round + 1 >= max_rounds` (`scripts/qrspi_critic_loop.py:108`).

## Q6: How is the synthesized revise instruction passed back to the design agent for revision, and how is round count tracked across panel → synthesize → revise iterations?

**Answer:** **Round counting is fully specified; synthesis and the revise-handoff mechanism are NOT FOUND (unbuilt).** Round count is tracked by the pure module via the `round` argument: `next_action` returns `"revise"` while `round + 1 < max_rounds` and rounds remain, carrying `latest["findings"]` as `residual_findings` so the reviser has the critic's guidance; it returns `"cap_reached"` when `round + 1 >= max_rounds`. The *intended* JS counter is a `for (let round = 0; round < maxRounds; round++)` loop inside `runCriticLoop` that breaks on all-pass (RUS-55 Decision 3, `.qrspi/RUS-55/design.md:79-88`), but that loop **does not exist** in `qrspi-batch.js`. There is **no synthesis step at all** — the foundation is single-critic (one `{pass, findings}` per round, no cross-critic aggregation, OQ2). The mechanism for handing the revise instruction back to the design agent (e.g. re-spawning `qrspi-design` with findings in its prompt) is also unbuilt; the module only emits the `revise` *decision* + `residual_findings`, not a revise *prompt*.

**Evidence:**

```
    if latest["pass"]:
        return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:105-111`

**Dependencies:** The reviser identity ("reviser writes a full artifact") is referenced in RUS-55's risk register (`.qrspi/RUS-55/design.md:106`) but the wiring is in the unlanded Slice 3. The design agent (`qrspi-design`) has tools `Read, Write` and writes only `OUTPUT_PATH`.
**Implicit contracts:** The reviser must rewrite `stg(id,'design')` in place (never empty it) so the persist gate still passes (Q1 contract).

## Q7: How is the revised `design.md` re-persisted between rounds, and does re-paneling re-read the staged artifact or an in-memory copy?

**Answer:** Per the RUS-55 design, the critic loop runs **entirely within the produce→persist window**, so `design.md` is **NOT persisted between rounds** — `persistArtifact`/`scripts/qrspi_persist.py` runs **once**, after the loop converges or caps, moving the final `stg(id,'design')` to `art(wd,id,'design.md')` (`.qrspi/RUS-55/design.md:10-12,28,65`). Each round's reviser rewrites the staged file at `stg(id,'design')` in place, and the next round's critic **re-reads that staged file from disk** (there is no in-memory artifact pass between phases — "No artifact is passed in memory between phases," `.qrspi/RUS-55/design.md:10`). `qrspi_persist.persist(src, dest)` (`scripts/qrspi_persist.py:74-92`) verifies `src` is non-empty, `os.makedirs` the dest dir, `shutil.move`s, then re-verifies the dest is non-empty. **This inter-round loop is unbuilt** (no `runCriticLoop`), but the persist helper itself is unchanged and is what would run once at the end.

**Evidence:**

```
def persist(src, dest):
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    ...
```

— `scripts/qrspi_persist.py:74-92`

```
The persist gate runs AFTER the produce `agent()` call and verifies the staged file
exists and is non-empty before `shutil.move` removes it from staging ... So between
produce and persist, the just-written artifact still lives at `stg(id,name)` and has
not yet been moved.
```

— `.qrspi/RUS-55/design.md:12`

**Dependencies:** `persistArtifact` (JS, `.claude/workflows/qrspi-batch.js:440-453`) spawns a worker that runs `scripts/qrspi_persist.py --ticket <id> --artifact design` verbatim and parses its `{ok,dest,bytes,error?}` envelope.
**Implicit contracts:** `shutil.move` is destructive — after persist, the staged copy is gone, so re-paneling must happen *before* the single persist. The reviser writing an empty staged file converts persist into `ok:false`.

## Q8: What happens when the panel passes on round 1 — what mechanism short-circuits the revise step so no revision occurs?

**Answer:** The pure module short-circuits: when the latest verdict's `pass` is truthy, `next_action` returns `{"action": "converged", "residual_findings": []}` immediately — discarding any findings on a passing verdict — so the (intended) JS loop breaks before any revise agent is spawned. RUS-55 AC4 states this as "all-pass on round 1 ⇒ single critic call, no revise" (`.qrspi/RUS-55/design.md:31`). The decision is exercised by two unit-test cases proving a passing verdict at round 0 converges with no residual findings even when the verdict carries a "nit." The JS-side `for`-loop `break`-on-converged that consumes this is unbuilt, but the decision logic is complete and tested.

**Evidence:**

```
check("passing verdict at round 0 ⇒ converged, no residual findings",
      next_action([{"pass": True, "findings": []}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})

check("passing verdict discards any findings on the verdict (converged carries none)",
      next_action([{"pass": True, "findings": ["a nit"]}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})
```

— `scripts/qrspi_critic_loop_test.py:40-46`

**Dependencies:** Consumed by the unbuilt `runCriticLoop` JS loop (would `break` on `action === 'converged'`).
**Implicit contracts:** A `converged` action ALWAYS carries empty `residual_findings`, so the finalize body never surfaces findings on a converged phase. `pass`-break means exactly one critic agent and zero revise agents run.

## Q9: After `maxRounds` is exhausted with unresolved findings, how are those findings surfaced into the design PR body, given that PR bodies are seeded only from the branch commit message at `gt submit` creation time?

**Answer:** Cap-reached returns `{"action": "cap_reached", "residual_findings": [<latest findings>]}`, and the loop still returns *success* so the phase proceeds to finalize (`.qrspi/RUS-55/design.md:29`). RUS-55 OQ3 (RESOLVED "pr body") routes residual findings **only into the design PR body, not Linear** (`.qrspi/RUS-55/design.md:116`). RUS-55 Decision 4 (`.qrspi/RUS-55/design.md:90-99`) chose Option A: write residual findings to a token-free staged file and **splice them into the finalize commit message** (mirroring `scripts/qrspi_pr_body.py`), because design/plan PR bodies are currently a bare commit *subject* with no multi-line body. **None of this is built yet:**
- The design finalize worker today builds a **subject-only** commit: `gt modify -c` with subject `"${t.id} [QR]: Design — ${t.title}"`, then `gt submit --publish` (`.claude/workflows/qrspi-batch.js:625-629`). There is no body splice for design.
- `scripts/qrspi_pr_body.py` exists but is **implementation-slice-only**: its `compose_message(existing_message, body_text)` splices a `pr-summary.md` body between subject and trailers for `<ticket>/slice-<N>` branches (`scripts/qrspi_pr_body.py:72-121,192-244`). There is no design/plan equivalent (`qrspi_critic_body.py` was the planned Path A helper in `.qrspi/RUS-55/worktree.md:78` — NOT FOUND in `scripts/`).

So the *mechanism* a design critic must reuse is the `compose_message` "splice body into the commit message Graphite reads at creation" pattern; the *design-phase application* of it does not exist.

**Evidence:**

```
2. Stage ONLY those three artifacts; add them as the single commit (subject
"${t.id} [QR]: Design — ${t.title}") on the pre-created ${t.id}/design branch with
`gt modify -c` (...); submit the Design PR PUBLISHED with `gt submit --publish${reviewerFlags(r)}`...
```

— `.claude/workflows/qrspi-batch.js:627`

```
def compose_message(existing_message, body_text):
    subject, trailers = split_subject_trailers(existing_message)
    parts = [subject, "", (body_text or "").strip()]
    if trailers:
        parts += ["", "\n".join(trailers)]
    return "\n".join(parts).rstrip() + "\n"
```

— `scripts/qrspi_pr_body.py:108-121`

**Dependencies:** `gt submit` has no `--body` flag (Graphite ≤1.8.x); the commit message is the only non-interactive lever (`scripts/qrspi_pr_body.py:8-29`). The implementation path calls `qrspi_pr_body.py` before `gt submit`; a design path would need a parallel helper or an in-prompt staged-body splice.
**Implicit contracts:** Multi-line findings must NOT be inlined into a heredoc commit *subject* (shell-quoting breakage) — Decision 4 rejected Option B for this reason (`.qrspi/RUS-55/design.md:95`). Use a file → splice, never a CLI-arg subject.

## Q10: How are conflicting or duplicate findings across lenses handled during synthesis (merge/dedupe), and what determines precedence when two lenses disagree?

**Answer:** **NOT FOUND — no synthesis/merge/dedupe module exists, and the foundation explicitly does not support multiple lenses.** RUS-55 OQ2 (RESOLVED "single") pinned the primitive to **a single critic agent per edge**, with "no cross-critic aggregation" (`.qrspi/RUS-55/design.md:115`). The pure module's `next_action` does take a `verdicts` *list* and treats the **last element as authoritative** ("latest verdict wins"), which is the only "precedence" rule present — but that is round-to-round latest-wins for a single critic, not cross-lens merge. Searches for `synthes*`, `merge.*find*`, `dedup*`, `precedence` across `scripts/` and `.claude/` returned no findings-synthesis code (only unrelated ticket-array dedupe in `qrspi_resolve.py`/`qrspi_order_tickets.py`). A multi-lens panel + synthesize stage with merge/dedupe/precedence is **entirely new work** this ticket would introduce; there is no existing pattern to extend.

**Evidence:**

```
# The LATEST (last) verdict is authoritative when more than one is supplied.
check("latest verdict is authoritative (last element wins)",
      next_action([{"pass": False, "findings": ["old"]},
                   {"pass": True, "findings": []}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})
```

— `scripts/qrspi_critic_loop_test.py:79-83`

```
~~OQ2~~ (RESOLVED — reviewer: "single"): This primitive ticket supports a single critic
agent per edge ... pins `runCriticLoop` to spawn exactly one critic agent per round (not a
`parallel()` fan-out), simplifying ... to one `{pass, findings}` reply per round with no
cross-critic aggregation.
```

— `.qrspi/RUS-55/design.md:115`

**Dependencies:** None exist. `parallel()` (a runner primitive for concurrent thunks) is available in the workflow vocabulary but is explicitly NOT used for critics in the foundation (`.qrspi/RUS-55/design.md:14,115`).
**Implicit contracts:** The existing `next_action` consumes ONE authoritative `{pass, findings}` per round. A multi-lens synthesis would have to reduce M lens verdicts to that single `{pass, findings}` *before* calling `next_action`, since the module's contract is one authoritative verdict per round.

## Q11: What is the failure behavior if a single lens errors or returns schema-invalid output mid-panel — does the panel abort, drop that lens, or block design submission?

**Answer:** For the **single-critic** primitive that exists, the failure behavior is **fail-closed, never abort, never block**: an unreadable/empty/non-JSON/malformed verdict is coerced to `{pass: False, findings: []}` by `parse_critic_verdict`/`_coerce_verdict`, which **never raise**. A failed verdict reads as NOT-passed, so the loop would `revise` (rounds remain) or `cap_reached` (at cap) — it never silently reports "converged" on a garbled reply (`scripts/qrspi_critic_loop.py:60-77,96-103`). Critically, **cap-reached still returns success**, so a non-converging/erroring critic **does not block design submission** — the phase proceeds to finalize with residual findings surfaced (Q9). RUS-55 design states the rationale: the critic is pinned to a frontier model so the StructuredOutput stall is "out-of-contract," and `parse_critic_verdict` is a defensive backstop for the residual weak-model-stall risk (`.qrspi/RUS-55/design.md:105,114`). **Panel/multi-lens drop-vs-abort behavior is NOT FOUND** (no panel exists); only the single-critic fail-closed path is implemented. A test battery asserts a range of garbage inputs never raise.

**Evidence:**

```
for bad in ["", "   ", "}{", "not json", "{pass:true}", "[1,2,3]", "42", "true",
            None, 12345, '{"findings": "x"}']:
    ...
    try:
        out = parse_critic_verdict(bad)
        if isinstance(out, dict) and out.get("pass") is False: ... ok ...
    except Exception as exc:   # the whole point is it must never raise
        failures += 1; print("FAIL: ... RAISED %r" % (bad, exc))
```

— `scripts/qrspi_critic_loop_test.py:141-153`

```
Fails closed: an empty/garbled verdict list, or a non-dict latest verdict, reads as
NOT-passed (via _coerce_verdict), so a missing verdict can never report "converged"
```

— `scripts/qrspi_critic_loop.py:96-98`

**Dependencies:** The fail-closed pattern mirrors `parseLandVerdict → incomplete` and the resolve/land-verify plain-text parsers (`.qrspi/RUS-55/design.md:20,108`).
**Implicit contracts:** A missing verdict NEVER converges (fail toward another round / cap, not toward pass). Cap-reached is success, not failure — the persist/finalize gate, not the critic, is what blocks a ticket.

## Q12: How do existing `scripts/qrspi_*_test.py` unit tests stub critic lenses, and what pattern would the synthesis merge/dedupe and panel-wiring tests follow?

**Answer:** The established pattern is **pure-logic-in-Python + stdlib-only assert-based `_test.py` sibling fed hand-built fixture dicts — no `agent()` stubbing, no subprocess mocking of the impure boundary**. There is **no precedent for stubbing `agent()` or critic *lenses*** because the JS orchestration (`qrspi-batch.js`) is not unit-tested at all (`.qrspi/RUS-55/design.md:21,109`). `scripts/qrspi_critic_loop_test.py` is the template: it imports `next_action`/`parse_critic_verdict`, calls them with literal `{pass, findings}` dicts (the "stub" for a critic verdict is just a dict literal), and asserts the returned decision via a `check(label, got, want)` helper that increments `failures`/`total` and `sys.exit(1 if failures else 0)`. A synthesis merge/dedupe test would follow exactly this: a new pure function (e.g. `synthesize(verdicts) -> {pass, findings}`) in a `scripts/qrspi_*.py` module, exercised by a `_test.py` sibling with literal lists of `{pass, findings}` dicts as input fixtures and expected merged output. Panel-*wiring* (the JS `runCriticLoop`) would remain **untested JS, verified by manual e2e** — the design firewall is "push the testable decision into Python, keep only agent-spawn glue in untested JS" (`.qrspi/RUS-55/design.md:109`).

**Evidence:**

```
def check(label, got, want):
    global failures, total
    total += 1
    if got == want: print("ok: %s" % label)
    else: failures += 1; print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))
...
check("non-passing verdict at round 0 with rounds remaining ⇒ revise",
      next_action([{"pass": False, "findings": ["dropped req X"]}], round=0, max_rounds=2),
      {"action": "revise", "residual_findings": ["dropped req X"]})
...
print("\n%d/%d checks passed" % (total - failures, total)); sys.exit(1 if failures else 0)
```

— `scripts/qrspi_critic_loop_test.py:29-36,50-52,156-157`

**Dependencies:** Tests `sys.path.insert(0, _HERE)` then import the sibling module (`scripts/qrspi_critic_loop_test.py:14-23`). Run with bare `python3 scripts/<name>_test.py`, exit 0/1. No third-party deps, no test runner. (Note: some other tests use stdlib `unittest`, e.g. `grade_test.py`; both styles coexist.)
**Implicit contracts:** Fixtures are plain dicts/lists; the impure boundary (agent spawn, gt/git subprocess) is deliberately EXCLUDED from tests (see `qrspi_restack_test.py` docstring per `.qrspi/RUS-67/research.md:274`). A critic-synthesis test must keep its function pure (no IO) to fit.

## Q13: How does the eval suite run against the design phase to produce the before/after design-phase score (post-RUS-37 checks) required by the acceptance criteria?

**Answer:** The eval harness is a **documented non-functional placeholder** — it cannot produce a real before/after design-phase score. `scripts/eval_all.py` is the multi-agent driver: it discovers phase agents under `.claude/agents/` (`qrspi-<phase>.md`), runs each against its phase-filtered slice of `evals/suite.json` into `results/all/<phase>/`, and aggregates a `summary.json` with `train_score`/`test_score` and `phase_regressions`. **But its own docstring states the underlying `run_eval.py` + `grade.py` path is a placeholder whose `execute_single` returns empty output, so "real scores against the stubbed harness are uniformly ~0"** (`scripts/eval_all.py:11-18`). `run_eval.py`'s `call_model` is the single mockable Anthropic-API seam (locally-imported `anthropic`), and the suite (`evals/suite.json`, name `qrspi-agent-evals`, defaults `trials_per_case:3, max_tokens:128000`, NO `model` key) has design cases `case_005`, `case_006`, `case_014` ("Produce a design document for this feature."). The **RUS-37 design-phase checks** are the programmatic graders in `scripts/grade.py` — e.g. `no_code_blocks` (`:111-116`), `has_section('design.md', ...)`, the `NEW PATTERN?` marker check (`:322`), and per-template markers (`:290,309`). RUS-37 committed these as a stdlib `unittest` harness in `scripts/grade_test.py` (28 checks, per `.qrspi/RUS-38/impl-log.md:10`, `.qrspi/RUS-39/impl-log.md:20`). So the "before/after design-phase score (post-RUS-37 checks)" the ticket's acceptance criteria reference is computed by running `eval_all.py`/`run_eval.py` + `grade.py` over the design cases — but **only `--model` against a real Anthropic key produces non-zero numbers; the committed harness scores ~0** (CLAUDE.md confirms: "evals/ + scripts/run_eval.py is a non-functional placeholder"). Verifying RUS-56 with a real before/after delta therefore requires supplying a live model in the suite `defaults` (`run_eval.py:210-222` hard-errors if `defaults.model` is absent).

**Evidence:**

```
This is a *plumbing* driver, not a scorer: the underlying single-agent path
(``run_eval.py`` + ``grade.py``) is a non-functional placeholder whose
``execute_single`` returns empty output (see CLAUDE.md / RUS-41 OQ4), so real
scores against the stubbed harness are uniformly ~0.
```

— `scripts/eval_all.py:11-15`

```
def no_code_blocks(filename: str, result: dict) -> tuple[bool, str]:
    """Check that output has no code blocks (for design docs)."""
    output = result.get("output", "")
    blocks = re.findall(r"```", output)
    ok = len(blocks) == 0
    return ok, f"Code blocks found: {len(blocks) // 2}"
```

— `scripts/grade.py:111-116`

**Dependencies:** `eval_all.py` → `run_eval.py` (`call_model` → `anthropic` SDK, key from `ANTHROPIC_API_KEY`) → `grade.py` checks → suite `evals/suite.json`. Design cases: `case_005/006/014`. `run_eval.py:211-220` requires `defaults.model` + `defaults.max_tokens` (hard error otherwise).
**Implicit contracts:** The placeholder harness yields ~0 uniformly; a real score requires a live model id in suite `defaults` and an API key. The grade-check DSL parses strings like `has_section('design.md', 'Risk Register')` (`scripts/grade.py:601`).

## Q14: How are panel findings, synthesis output, and per-round revise decisions logged or reported so a human can audit why a design was (or was not) revised before review?

**Answer:** The intended observability surface is `log(...)` lines plus a fold into `res.summary` — RUS-55 plans to "surface critic rounds / per-round pass-fail / cap-reached via `log(...)` and fold a summary into `res.summary`" (`.qrspi/RUS-55/design.md:51`, Q14; worktree task T20c at `.qrspi/RUS-55/worktree.md:77`). **This is unbuilt** (no `runCriticLoop`, no critic `log` lines in `qrspi-batch.js`). The existing precedent it would follow: `runPhase` already emits `log(...)` lines like `${id}: ${name} → saved ${p.bytes}B (${summary})` (`.claude/workflows/qrspi-batch.js:476`), and ticket-level results carry a `summary` field consumed by `finResult`/`skip` (`.claude/workflows/qrspi-batch.js:420-422`). The **authoritative audit surface for "why a design was/wasn't revised" is the PR body**, not Linear (Q9/OQ3): cap-reached residual findings are spliced into the design finalize commit (→ PR description) — that is the human-reviewable artifact. So per-round decisions would be ephemeral run logs (`log`), while the *persisted* audit trail of unresolved findings is the PR body.

**Evidence:**

```
log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:476`

```
- Surface critic rounds / per-round pass-fail / cap-reached via `log(...)` and fold a
  summary into `res.summary` (ref: Q14).
```

— `.qrspi/RUS-55/design.md:51`

**Dependencies:** `log(...)` and `phase(...)` are runner-injected; `res.summary` flows into the per-ticket result object returned by `doDesign` → `finResult`. The PR-body audit trail depends on the unbuilt design-body splice (Q9).
**Implicit contracts:** Run-time `log` lines are ephemeral (not persisted); the durable, reviewer-facing record of residual findings is the PR body (the authoritative advancement surface per the PR-gated lifecycle, `.claude/CLAUDE.md`).

---

## Discovered Patterns

- **Self-locating, stdlib-only Python helper + JSON envelope.** Every `scripts/qrspi_*.py` (`qrspi_persist`, `qrspi_pr_body`, `qrspi_config`, `qrspi_resolve`, `qrspi_critic_loop`) derives its repo root from `__file__` (never cwd/args), takes short token-free CLI flags, and emits ONE JSON envelope on stdout with an `ok` boolean + verbatim `error`, exit 0/non-zero, reported once and never retried. The "qrspi"-laden path is computed in Python, never typed by the weak worker model (`scripts/qrspi_persist.py:8-29`).
- **Pure-decision-in-Python, agent-glue-in-untested-JS.** The testable converge/revise/cap decision lives in `qrspi_critic_loop.py` with a `_test.py` sibling; the untestable agent-spawn glue stays in `qrspi-batch.js`, verified only by manual e2e. This is the same firewall used across the suite (22+ `_test.py` siblings).
- **Token-free staging + deterministic move (Fix A).** Phase agents write to `/tmp/phase-stage/<id>/<name>.md` (`stg()`); `qrspi_persist.py` moves to canonical. Persist's non-empty check IS the phase success gate. A critic must rewrite the staged file in place within the produce→persist window.
- **Fail-closed verdict/envelope parsing.** Every parser (`parse_critic_verdict`, `parseLandVerdict`, the resolve/restack envelope parsers) coerces malformed/empty input to a safe NOT-passed/`incomplete`/`wait`/`ok:false` value and NEVER raises — a garbled reply can never mark work done.
- **PR body authored at `gt submit` creation via the commit message.** `gt submit` has no body flag; the only non-interactive body lever is the branch commit message Graphite seeds at creation. `qrspi_pr_body.compose_message` splices a body between subject and trailers for implementation slices; design/plan currently have subject-only bodies.
- **Optional-trailing-arg + `if (x)` guard for opt-in behavior.** RUS-55 specifies extending `runPhase` with an optional trailing `criticConfig` guarded by `if (criticConfig)`, so absent ⇒ byte-for-byte unchanged. This idiom is the intended (unbuilt) integration seam.

## Inconsistencies

- **Foundation 1/5 is partially landed: agent + skill + pure module exist, but the JS glue (`runCriticLoop`, `criticConfig`, `CRITIC_VERDICT_SCHEMA`) is NOT in `qrspi-batch.js`.** The `qrspi-critic` agent (`.claude/agents/qrspi-critic.md:3`) and skill (`.claude/skills/qrspi-critic/SKILL.md:3`) both say they are "Spawned by runCriticLoop in qrspi-batch.js" / "Normally spawned by runCriticLoop", but no such function exists in the workflow (zero grep hits). RUS-55's worktree.md Slice 3 (`runCriticLoop` wiring, T15–T22) was planned but its implementation is absent from this worktree. Any 2/5 design must account for the foundation orchestration being unbuilt.
- **Ticket-questions assume a multi-lens *panel* + *synthesize* stage; the foundation is explicitly single-critic.** RUS-55 OQ2 (`.qrspi/RUS-55/design.md:115`) pinned the primitive to "a single critic agent per edge ... no cross-critic aggregation," deferring multi-critic fan-out to per-phase tickets. So the panel/synthesis/merge-dedupe capability the questions reference does not exist anywhere yet (Q3, Q10).
- **`CRITIC_VERDICT_SCHEMA` is named as runner-validated but is not defined.** `.claude/agents/qrspi-critic.md:37` says the verdict is "validated as `CRITIC_VERDICT_SCHEMA` at the runner boundary," yet the JS constant is absent from `qrspi-batch.js` (the other schemas — `WORKER_SCHEMA`, `PERSIST_SCHEMA`, etc. — are present at `:336-411`). Validation today rests solely on the Python `parse_critic_verdict` backstop.
- **Design Decision 2 (schema'd return) vs. the realized backstop.** RUS-55 Decision 2 recommended Option A (`agent({schema: CRITIC_VERDICT_SCHEMA})`, frontier model) over the plain-text path, treating `parse_critic_verdict` as "only a defensive backstop." Because the schema path is unbuilt, the ONLY validation that exists is the supposedly-secondary backstop.
- **Eval harness cannot produce the before/after score the acceptance criteria imply.** `scripts/eval_all.py:11-15` and CLAUDE.md both label `run_eval.py` + `grade.py` a non-functional placeholder returning ~0 uniformly, yet the ticket's acceptance criteria (per Q13) call for a before/after design-phase score. A real delta requires injecting a live model into `evals/suite.json` `defaults` (which currently omits `model`, so `run_eval.py:211-216` hard-errors).
- **Two test idioms coexist.** Most `qrspi_*_test.py` use a bare assert + `check()` + `sys.exit(1 if failures)` style (e.g. `qrspi_critic_loop_test.py`); a few (e.g. `grade_test.py`) use stdlib `unittest`. A new critic-synthesis test could follow either, but the dominant/foundation-adjacent style is the bare-assert `check()` pattern.
