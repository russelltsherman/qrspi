# Implementation Plan — Bring the /review-* on-demand review family up to manual-review depth

**Structure basis:** structure.md @ 2026-06-18T01:30:00Z
**Generated:** 2026-06-18T02:00:00Z
**Revised:** 2026-06-18 — plan-review corrections (code-verified): the `/review-design` panel is a NEW ordered `DEFAULT_REVIEW_DESIGN_LENSES` constant, NOT the batch `DEFAULT_DESIGN_LENSES` (which is four lenses and deliberately excludes node-validity `design-review` per RUS-82); plan/impl lens ids are phase-qualified (`plan-fidelity`/`impl-fidelity`/…) so they (a) compose to real agent names via `qrspi-<phase>-critic-<id>` and (b) do not collide in the bare-lens-keyed `critic-metrics.jsonl` summary; multi-lens `rounds[]` recording specified; the regression fixture REUSES the existing `evals/fixtures/design_dropped_criterion_broken.md` instead of authoring a duplicate.
**Status:** draft
**Total steps:** 58

## Slice 1: Per-phase lens config + synopsis/ledger helpers (the tested pure core)

### Setup

1. ⚠️ Modify `scripts/qrspi_critics_config.py` — add the ordered review-panel defaults the `/review-*` skills source, plus the per-phase allow-list sets (ref: structure.md Modified Types, Decision 2).
   - **Verified against code (resolves structure.md Unverified Assumption 5):** the module declares `DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]` (FOUR lenses) and `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}`. The node-validity `design-review` lens is DELIBERATELY excluded from `DEFAULT_DESIGN_LENSES` (RUS-82 decoupling; the file carries an explicit "Do NOT re-couple" comment). **The design's "match the batch `DEFAULT_DESIGN_LENSES`" framing is INCORRECT and is corrected here:** the batch default is four lenses and omits node-validity, but the on-demand review panel MUST include `design-review` (it is the *only* lens `/review-design` runs today). The review panel is therefore a NEW ordered constant — neither `DEFAULT_DESIGN_LENSES` (four, no node-validity) nor the unordered `KNOWN_DESIGN_LENSES` set.
   - **After:** module additionally declares the ordered review panels and the allow-list sets:
     - `DEFAULT_REVIEW_DESIGN_LENSES = ("completeness", "internal-consistency", "edge-alignment", "simplicity", "design-review")` — the four batch edge lenses PLUS the node-validity lens the batch leaves opt-in-OFF.
     - `DEFAULT_REVIEW_PLAN_LENSES = ("plan-review", "plan-fidelity", "plan-completeness")`.
     - `DEFAULT_REVIEW_IMPL_LENSES = ("impl-review", "impl-fidelity", "impl-completeness")`.
     - `KNOWN_PLAN_LENSES = set(DEFAULT_REVIEW_PLAN_LENSES)` and `KNOWN_IMPL_LENSES = set(DEFAULT_REVIEW_IMPL_LENSES)` — the per-phase allow-lists, mirroring the `KNOWN_DESIGN_LENSES` idiom.
   - **Lens-id ↔ agent mapping (load-bearing, verified):** the fan-out derives `subagent_type` as `qrspi-<phase>-critic-<lens-id>` (confirmed: lens `"design-review"` → `qrspi-design-critic-design-review`; lens `"plan-review"` → `qrspi-plan-critic-plan-review`). The new plan/impl lens ids are therefore PHASE-QUALIFIED to match BOTH the existing `plan-review`/`impl-review` convention AND the Slice 2 agent files: `plan-fidelity`/`plan-completeness` → `qrspi-plan-critic-plan-fidelity` / `qrspi-plan-critic-plan-completeness`; `impl-fidelity`/`impl-completeness` → `qrspi-impl-critic-impl-fidelity` / `qrspi-impl-critic-impl-completeness`. Do NOT use `plan-critic-fidelity`-style ids (they resolve to a nonexistent `qrspi-plan-critic-plan-critic-fidelity`); do NOT use bare `fidelity`/`completeness` either — `qrspi_critic_summary.summarize` keys its per-lens buckets on the bare lens id with NO phase qualifier (`key = lens`, verified), so a bare id would merge plan/impl/design dissent stats in the shared `critic-metrics.jsonl` summary. The design panel keeps its established bare edge-lens ids (`completeness`, `edge-alignment`, …) because only the design phase emits them.

### Core Logic

2. ✨ Create `scripts/qrspi_review_synopsis.py` — new pure-stdlib helper module exposing `render_synopsis()`, `partition_decision_readiness()`, and `ledger_row_fields()` (ref: structure.md Slice 1 Files touched, Contracts).
3. ✨ In `scripts/qrspi_review_synopsis.py`, implement `partition_decision_readiness(verdictArray) -> (panelArray, decisionReadinessVerdict)` — splits the `decision-readiness` lens element out of the pre-reduction verdict array so it never reaches synthesize (ref: structure.md Contracts; Decision 5). Returns the remaining panel array plus the single `DecisionReadinessVerdict` (or an empty/None decision-readiness sentinel when the lens is absent).
4. ✨ In `scripts/qrspi_review_synopsis.py`, implement `render_synopsis(verdictArray, decisionReadiness, terminalAction) -> str` — renders, from the PRE-reduction per-lens verdict array, an axis enumeration (one row per lens with its `pass` + blocking finding count), a distinct advisory non-blocking-notes section (union of each lens's `nonBlockingNotes`), a decision-readiness "blocking-for-human" section, and the terminal action (ref: structure.md Contracts, SynopsisModel; design Decision 4/5).
5. ✨ In `scripts/qrspi_review_synopsis.py`, implement `ledger_row_fields(verdictArray) -> dict` — derives the OPTIONAL additive `critic-metrics.jsonl` fields (`nonBlockingNotes: [str]`, `axes: [{lens, pass, blockingCount}]`) from the same verdict array (ref: structure.md Contracts, Modified Types).

### Tests

6. ✨ Create `scripts/qrspi_review_synopsis_test.py` — stdlib `unittest` covering `render_synopsis()` axis enumeration (all lenses listed with per-lens pass), non-blocking passthrough (notes rendered in the advisory section), `partition_decision_readiness()` (decision-readiness element removed from panel array and returned separately; absent-lens case), and `ledger_row_fields()` (axes + nonBlockingNotes shape) (ref: structure.md Slice 1 Files touched).
7. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — assert the new constants exist with the expected ordered contents and that the batch-vs-review decoupling holds.
   - **Current:** covers `KNOWN_DESIGN_LENSES` / design defaults only.
   - **After:** asserts `DEFAULT_REVIEW_DESIGN_LENSES == ("completeness","internal-consistency","edge-alignment","simplicity","design-review")`, `DEFAULT_REVIEW_PLAN_LENSES == ("plan-review","plan-fidelity","plan-completeness")`, `DEFAULT_REVIEW_IMPL_LENSES == ("impl-review","impl-fidelity","impl-completeness")`, and the `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES` allow-list sets; asserts `"design-review" in DEFAULT_REVIEW_DESIGN_LENSES` AND `"design-review" not in DEFAULT_DESIGN_LENSES` (locks the review-panel-vs-batch-default distinction so a future edit cannot silently collapse them); asserts every plan/impl review-panel lens id is phase-qualified (no bare id shared across phases) so `qrspi-<phase>-critic-<id>` resolves to a distinct agent.
8. ⚠️ Modify `scripts/qrspi_critic_summary.py` — ONLY IF a gap exists: confirm `summarize` reads the new optional row fields (`nonBlockingNotes`, `axes`) via `.get()` with defaults; if it already does, make NO change and record the no-op in the commit message (ref: structure.md Slice 1 Files touched; Unverified Assumption 1).
   - **Current:** `qrspi_critic_summary.summarize(...)` reads row fields via `.get()` with defaults (per design §Delta / OQ4) — to be confirmed by reading the file.
   - **After:** unchanged if already lenient; otherwise minimal `.get()`-default read added for the two new keys.
9. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add a fixture old-style metrics row (no `nonBlockingNotes`/`axes`) asserting it still parses (backward-compat), plus a new-style row asserting the new fields surface.
   - **Current:** parses rows carrying the existing `rounds[]` shape.
   - **After:** additionally asserts old rows without the new keys still parse AND new fields are surfaced when present.

### Verify Slice 1

10. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] Full suite green (new + existing tests).
    - [ ] `python3 scripts/run_tests.py critic` and `python3 scripts/run_tests.py synopsis` pass in isolation.
    - [ ] The old-style metrics-row fixture (no `nonBlockingNotes`/`axes`) parses (backward-compat assertion holds).

---

## Slice 2: The shared non-producer reviser + the five new lens agents

### Setup

11. Invoke the `skill-creator` skill before authoring any agent in this slice (per MEMORY directive: never ship a SKILL/agent ad-hoc). Use its authoring + eval loop for each `.md` agent below.

### Core Logic

12. ✨ Create `.claude/agents/qrspi-critic-reviser.md` — the ONE shared non-producer adversarial reviser, phase-parameterized via a `PHASE` input (`design|plan|impl`) (ref: structure.md Slice 2; Contracts `qrspi-critic-reviser`; design Decision 3).
13. ⚠️ In `.claude/agents/qrspi-critic-reviser.md`, specify the agent contract: accepts `PHASE` input; writes ONLY to `OUTPUT_PATH` (scratch-verbatim, copied without alteration); propose-only (no tracked path / no branch write); receives `RESIDUAL_FINDINGS` containing node-validity/fidelity findings ONLY (decision-readiness excluded) (ref: structure.md Contracts; design Decision 5).
14. ✨ Create `.claude/agents/qrspi-plan-critic-plan-fidelity.md` — adversarial, ticket-grounded plan fidelity lens that emits a `LensVerdict` (ref: structure.md Slice 2; Contracts "Each new lens agent").
15. ⚠️ In `.claude/agents/qrspi-plan-critic-plan-fidelity.md`, encode the adversarial contract: declare `TICKET_CONTENT_PATH` as a consumed input; require a SPECIFIC named descoping/deviation counter-example (plan element vs. the ticket AC it narrows) OR an affirmative "no AC narrowed, checked each: <list>"; default `pass:false` under uncertainty (fail-closed) (ref: structure.md Contracts; design Risk Register row 1).
16. ✨ Create `.claude/agents/qrspi-plan-critic-plan-completeness.md` — plan completeness lens asserting every AC + every answered question is covered by the plan; emits a `LensVerdict` (ref: structure.md Slice 2).
17. ⚠️ In `.claude/agents/qrspi-plan-critic-plan-completeness.md`, encode the same adversarial contract (named counter-example OR affirmative per-AC checklist; fail-closed default; declares `TICKET_CONTENT_PATH`) (ref: structure.md Contracts; design Risk Register row 1).
18. ✨ Create `.claude/agents/qrspi-impl-critic-impl-fidelity.md` — adversarial, ticket-grounded impl fidelity lens emitting a `LensVerdict`; declares `TICKET_CONTENT_PATH` (ref: structure.md Slice 2).
19. ⚠️ In `.claude/agents/qrspi-impl-critic-impl-fidelity.md`, encode the adversarial contract (named counter-example OR affirmative per-AC checklist; fail-closed default) (ref: structure.md Contracts; design Risk Register row 1).
20. ✨ Create `.claude/agents/qrspi-impl-critic-impl-completeness.md` — impl completeness lens asserting every AC + answered question is covered by the implementation; emits a `LensVerdict`; declares `TICKET_CONTENT_PATH` (ref: structure.md Slice 2).
21. ⚠️ In `.claude/agents/qrspi-impl-critic-impl-completeness.md`, encode the adversarial contract (named counter-example OR affirmative per-AC checklist; fail-closed default) (ref: structure.md Contracts; design Risk Register row 1).
22. ✨ Create `.claude/agents/qrspi-design-critic-decision-readiness.md` — non-producer decision-readiness lens replacing the self-grading open-question pass; declares `TICKET_CONTENT_PATH`; emits a `DecisionReadinessVerdict` partitioning open questions into `blockingDecisions` (genuinely human-to-decide, with rationale) vs `answerable` (ref: structure.md New Types `DecisionReadinessVerdict`; design Decision 5).

### Tests

23. Run the skill-creator eval/authoring loop for each of the six agents above (`qrspi-critic-reviser`, the four fidelity/completeness lenses, and `qrspi-design-critic-decision-readiness`) — do not accept an agent until its loop converges (ref: structure.md Slice 2 Verification; MEMORY skill-creator directive).
24. Validate triggering for each new agent with direct `claude -p` routing probes in the real repo (sandbox `run_eval` is invalid here — ref: structure.md Verification; design Risk Register; MEMORY).
    - **Expected:** each agent is selected by `subagent_type` and returns its declared shape.
25. Manual probe (deliberately-descoped sample): confirm each fidelity/completeness lens emits a `LensVerdict` producing a named counter-example OR an affirmative per-AC checklist, and defaults `pass:false` under uncertainty.
26. Manual probe: confirm `qrspi-critic-reviser` writes ONLY to `OUTPUT_PATH` and leaves no tracked-path/branch mutation.

### Verify Slice 2

27. **Checkpoint:** `claude -p` routing probe per agent (six agents) + manual descoped-sample probe
    - [ ] skill-creator eval/authoring loop run + converged per agent.
    - [ ] Each new agent triggers by `subagent_type`.
    - [ ] Each lens emits a `LensVerdict` (decision-readiness emits `DecisionReadinessVerdict`); fidelity/completeness lenses produce a named counter-example OR affirmative per-AC checklist over a descoped sample.
    - [ ] Reviser writes ONLY to OUTPUT_PATH; no tracked-path/branch mutation.

---

## Slice 3: Upgrade /review-design end-to-end (the reference wiring)

### Setup

28. Read `.claude/skills/review-design/SKILL.md` in full BEFORE editing to map the current single-lens fan-out (Step 4a), the verdict-array assembly piped to `qrspi_critic_synthesize.py`, the Step 5 open-question pass, and the reviser `subagent_type` invocation (resolves structure.md Unverified Assumption 2: exact SKILL.md step structure).

### Core Logic

29. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — fan-out step: replace the single `design-review` lens spawn with the FULL design panel sourced from `DEFAULT_REVIEW_DESIGN_LENSES` (Slice 1 step 1) = `completeness` + `internal-consistency` + `edge-alignment` + `simplicity` + `design-review`. For each lens id, spawn `subagent_type: qrspi-design-critic-<lens-id>` and tag its verdict-array element `{"lens":"<lens-id>", ...}` (ref: structure.md Slice 3; design §Delta, OQ1 — the design's "matches `DEFAULT_DESIGN_LENSES`" framing is corrected per Slice 1 step 1: the review panel is the distinct `DEFAULT_REVIEW_DESIGN_LENSES`, which additionally includes node-validity `design-review`).
   - **Current:** Step 4a spawns exactly ONE node-validity lens (`qrspi-design-critic-design-review`) via the Agent tool.
   - **After:** Step 4a fans out the five-lens panel (sourced from `DEFAULT_REVIEW_DESIGN_LENSES`) into the pre-reduction verdict array.
30. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — ticket plumbing: add a step that fetches the ticket via `mcp__linear__get_issue` and stages its text to `TICKET_CONTENT_PATH` under `/tmp/phase-stage/<id>/review/ticket.md`, then passes that path to the `edge-alignment`, `completeness`, and `decision-readiness` lenses ONLY (node-validity lens unchanged) (resolves structure.md Unverified Assumption 3: ticket fetch/stage mechanism + path; design Decision 6).
31. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — partition step: before piping to `qrspi_critic_synthesize.py`, call `partition_decision_readiness()` (from `scripts/qrspi_review_synopsis.py`) so the decision-readiness verdict is removed from the synthesize array and held aside as terminal-advisory (ref: structure.md Contracts; design Decision 5).
   - **Current:** the entire verdict array is fed to `qrspi_critic_synthesize.py`.
   - **After:** only the node-validity/fidelity panel array is fed to synthesize; decision-readiness is partitioned out.
32. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — replace Step 5 (self-grading open-question pass spawning the producer) with a spawn of the `qrspi-design-critic-decision-readiness` lens; its `DecisionReadinessVerdict` feeds the synopsis only, never the revise loop (ref: structure.md Slice 3; design Decision 5).
   - **Current:** Step 5 spawns the producer (`qrspi-design`) in advisory mode to free-text "answer" open questions.
   - **After:** Step 5 spawns the non-producer decision-readiness lens; blocking decisions surface in the synopsis.
33. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — reviser swap: change the `revise`-loop reviser `subagent_type` from the producer (`qrspi-design`) to the shared `qrspi-critic-reviser`, passing `PHASE=design` and `RESIDUAL_FINDINGS` = node-validity/fidelity findings only (ref: structure.md Slice 3; design Decision 3).
   - **Current:** `revise` re-spawns `qrspi-design` (the producer) to rewrite the scratch copy.
   - **After:** `revise` spawns `qrspi-critic-reviser` with `PHASE=design`.
34. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — synopsis widening + multi-lens ledger recording: replace the hand-composed prose synopsis with a `render_synopsis()` call (PRE-reduction verdict array + decision-readiness verdict + terminal action), and MERGE the additive fields from `ledger_row_fields()` onto the dict returned by `qrspi_review_record.build_record` before appending the `critic-metrics.jsonl` row (`build_record` constructs the row from `rounds`; the new fields are merged onto its result, not passed as a parameter) (ref: structure.md Contracts; design §Delta axis-enumeration source).
   - **Multi-lens `rounds[]` shape (was single-lens — verified):** today each round records ONE synthesized entry tagged `{"lens":"design-review", ...}`. Under the panel, feed `build_record(rounds=...)` the FULL per-lens verdict list across every round (N lenses × R rounds, each `{lens, pass, findings}`) — NOT one synthesized entry per round — so `qrspi_critic_summary.summarize` keeps bucketing per-lens dissent by `rnd["lens"]` (the phase-qualified ids from Slice 1 keep those buckets phase-distinct). The synthesized `{pass, findings}` is still computed per round for `next_action`/the revise decision; it is simply not what gets recorded as the round entries.
   - **Current:** synopsis is hand-composed prose keyed only on terminal action; one synthesized round entry per round; ledger collapses findings to a count.
   - **After:** synopsis is axis-enumerated with a non-blocking section + decision-readiness section; `rounds[]` carries per-lens entries; row carries merged `axes` + `nonBlockingNotes`.

### Tests

35. End-to-end run `/review-design <existing-ticket-id>` over a ticket with an existing design PR (ref: structure.md Slice 3 Verification).
    - **Expected:** synopsis comment posted listing all five lenses + per-lens pass + a non-blocking section; PR head SHA identical before/after; decision-readiness blocking items appear but trigger NO reviser round; `TICKET_CONTENT_PATH` passed to fidelity/completeness/decision-readiness lenses only.
36. **Checkpoint guard:** capture PR head SHA before and after the run and assert equality (propose-only invariant — ref: design Q6/Q15).

### Verify Slice 3

37. **Checkpoint:** `/review-design <id>` end-to-end + `gh pr view <design-pr> --json headRefOid` before/after
    - [ ] Axis-enumerated synopsis lists all five lenses + per-lens pass + non-blocking section.
    - [ ] PR head SHA identical before/after (propose-only).
    - [ ] Decision-readiness blocking items appear in the synopsis but trigger NO reviser round.
    - [ ] `TICKET_CONTENT_PATH` passed to fidelity/completeness/decision-readiness lenses ONLY (node-validity lens unchanged).

---

## Slice 4: Upgrade /review-plan and /review-implementation

### Setup

38. Read `.claude/skills/review-plan/SKILL.md` and `.claude/skills/review-implementation/SKILL.md` in full BEFORE editing, mirroring the Slice 3 step map (single-lens fan-out, synthesize pipe, Step 5/reviser swap points, and — for impl — the frontier-resolution step) (ref: structure.md Unverified Assumption 2/4).

### Core Logic — review-plan

39. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — fan-out: replace the single `plan-review` lens spawn with the plan panel sourced from `DEFAULT_REVIEW_PLAN_LENSES` (`plan-review` + `plan-fidelity` + `plan-completeness`); for each lens id spawn `subagent_type: qrspi-plan-critic-<lens-id>` and tag `{"lens":"<lens-id>", ...}` into the pre-reduction verdict array (ref: structure.md Slice 4; design §Delta).
   - **Current:** spawns exactly ONE node-validity lens (`qrspi-plan-critic-plan-review`).
   - **After:** fans out the `DEFAULT_REVIEW_PLAN_LENSES` panel.
40. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — ticket plumbing: fetch via `mcp__linear__get_issue`, stage to `TICKET_CONTENT_PATH` (`/tmp/phase-stage/<id>/review/ticket.md`), and pass to the fidelity/completeness lenses ONLY (ref: structure.md Slice 4; design Decision 6).
41. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — reviser swap: change the `revise`-loop reviser `subagent_type` to `qrspi-critic-reviser` with `PHASE=plan` (ref: structure.md Slice 4).
   - **Current:** `revise` re-spawns `qrspi-plan` (the producer).
   - **After:** `revise` spawns `qrspi-critic-reviser` with `PHASE=plan`.
42. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — synopsis widening: swap the hand-composed synopsis for `render_synopsis()` + append `ledger_row_fields()` to the ledger row (ref: structure.md Contracts).
   - **Current:** hand-composed prose synopsis + count-only ledger.
   - **After:** axis-enumerated synopsis + `axes`/`nonBlockingNotes` ledger fields.

### Core Logic — review-implementation

43. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — fan-out: replace the single `impl-review` lens spawn with the impl panel sourced from `DEFAULT_REVIEW_IMPL_LENSES` (`impl-review` + `impl-fidelity` + `impl-completeness`); for each lens id spawn `subagent_type: qrspi-impl-critic-<lens-id>` and tag `{"lens":"<lens-id>", ...}` into the pre-reduction verdict array (ref: structure.md Slice 4).
   - **Current:** spawns exactly ONE node-validity lens (`qrspi-impl-critic-impl-review`).
   - **After:** fans out the `DEFAULT_REVIEW_IMPL_LENSES` panel.
44. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — define the impl lens input granularity: the fidelity/completeness lenses run over the AGGREGATED slice stack (one panel pass over the whole implementation), not per-slice, consistent with the existing single rolled-up synopsis to the top slice PR (resolves structure.md Unverified Assumption 4).
45. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — ticket plumbing: fetch via `mcp__linear__get_issue`, stage to `TICKET_CONTENT_PATH`, pass to fidelity/completeness lenses ONLY (ref: structure.md Slice 4; design Decision 6).
46. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — reviser swap: change the `revise`-loop reviser `subagent_type` to `qrspi-critic-reviser` with `PHASE=impl` (ref: structure.md Slice 4).
   - **Current:** `revise` re-spawns `qrspi-implement` (the producer).
   - **After:** `revise` spawns `qrspi-critic-reviser` with `PHASE=impl`.
47. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — synopsis widening: swap to `render_synopsis()` + append `ledger_row_fields()` to the ledger row (ref: structure.md Contracts).
   - **Current:** hand-composed rolled-up synopsis + count-only ledger.
   - **After:** axis-enumerated rolled-up synopsis + `axes`/`nonBlockingNotes` ledger fields.
48. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — frontier guard: align frontier resolution with `/review`'s `gh pr list --state all` guard to dodge the partially-landed-stack misfire (ref: structure.md Slice 4; design Risk Register row 4).
   - **Current:** frontier resolution does NOT use `--state all`.
   - **After:** frontier resolved via `gh pr list --state all`.

### Tests

49. End-to-end run `/review-plan <id>` over a ticket with a plan PR; capture PR head SHA before/after.
    - **Expected:** axis-enumerated synopsis with plan-panel lenses + per-lens pass; head SHA unchanged; ticket passed to fidelity/completeness lenses only.
50. End-to-end run `/review-implementation <id>` over a ticket with a slice stack; capture top-slice PR head SHA before/after.
    - **Expected:** rolled-up synopsis posted to the top slice PR; frontier resolved via `--state all` (no partially-landed misfire); head SHA unchanged; ticket passed to fidelity/completeness lenses only.

### Verify Slice 4

51. **Checkpoint:** `/review-plan <id>` and `/review-implementation <id>` end-to-end + head-SHA before/after on each
    - [ ] `/review-plan` posts an axis-enumerated synopsis with the plan panel lenses + per-lens pass.
    - [ ] `/review-implementation` posts the rolled-up synopsis to the top slice PR; frontier resolved via `--state all`.
    - [ ] Both: PR head SHA unchanged before/after (propose-only).
    - [ ] Both: ticket passed to fidelity/completeness lenses only.

---

## Slice 5: Upgrade whole-stack /review + author the regression fixture

### Setup

52. Read `.claude/skills/review/SKILL.md` in full BEFORE editing to map its binding table (per-phase panel composition) and Step 3b per-phase fan-out / per-phase synopsis sub-section assembly (ref: structure.md Unverified Assumption 2).

### Core Logic

53. ⚠️ Modify `.claude/skills/review/SKILL.md` — bind the upgraded per-phase panels (`DEFAULT_REVIEW_DESIGN_LENSES`, `DEFAULT_REVIEW_PLAN_LENSES`, `DEFAULT_REVIEW_IMPL_LENSES`) in the binding table; render the honest per-phase synopsis sub-sections via `render_synopsis()`; emit ONE ledger row per reviewed phase via `ledger_row_fields()` merged onto each phase's `build_record` dict (ref: structure.md Slice 5; design §Delta).
   - **Current:** binding table composes the three SINGLE node-validity lenses; per-phase sub-sections are hand-composed prose; one ledger row per phase from count-only data.
   - **After:** binding table composes the upgraded multi-lens panels; sub-sections are axis-enumerated; ledger rows carry the additive fields.
54. ✨ REUSE the existing `evals/fixtures/design_dropped_criterion_broken.md` (DASH-417) as the descoping regression anchor INSTEAD of authoring a new fixture — verified present: it is an independently-authored design (RUS-77 / AC-TEETH era, a DIFFERENT purpose, so non-circular per design OQ5) that states four ACs in its Desired End State and SILENTLY DROPS one ("403 unless admin") from its Delta/Pattern Decisions, carrying a "Do NOT fix this fixture" guard. Confirm a ticket fixture supplying those four ACs exists for `TICKET_CONTENT_PATH`; if none states all four ACs verbatim, add a minimal `evals/fixtures/ticket_dropped_criterion.md` listing them (ref: structure.md Slice 5; design OQ5). Authoring a brand-new `descoping-design.md` is DROPPED as needless duplication (ticket constraint: "reuse existing machinery").
55. ⚠️ Modify `evals/fixtures/README.md` — ensure the provenance table documents `design_dropped_criterion_broken.md` as the RUS-91 design-panel regression anchor (which AC it drops: "403 unless admin"; purpose), adding the row if absent, plus a row for any `ticket_dropped_criterion.md` added in step 54 (ref: structure.md Slice 5).
   - **Current:** provenance table may not flag `design_dropped_criterion_broken.md` under RUS-91's regression use.
   - **After:** provenance table documents the reused design fixture (and any added ticket fixture) as the descoping regression anchor.

### Tests

56. Regression probe: run the upgraded design panel lenses (at minimum `completeness` + `edge-alignment`) DIRECTLY over `evals/fixtures/design_dropped_criterion_broken.md` with its ticket fixture as `TICKET_CONTENT_PATH` — a LENS-LEVEL probe, since a static fixture is not a live PR the full `/review-design` skill can resolve. Assert a NON-clean result: the dropped "403 unless admin" AC surfaces as a blocking completeness/fidelity finding (mirrors the stated-minus-covered coverage check already asserted by `scripts/qrspi_teeth_test.py`). This closes design OQ5's regression AC at the lens level; full-skill end-to-end over a live ticket is covered by step 35 (ref: structure.md Slice 5 Verification; design OQ5).
57. End-to-end run `/review <id>` over a ticket with a frontier PR; capture frontier-PR head SHA before/after.
    - **Expected:** ONE rolled-up synopsis with per-phase sub-sections, each axis-enumerated; one ledger row per phase; head SHA unchanged.

### Verify Slice 5

58. **Checkpoint:** `/review <id>` end-to-end + `/review-design` over the fixture + `python3 scripts/run_tests.py`
    - [ ] `/review <id>` posts ONE rolled-up synopsis with per-phase sub-sections, each axis-enumerated; one ledger row per phase.
    - [ ] PR head SHA unchanged (propose-only across the whole stack).
    - [ ] Design panel lenses over `evals/fixtures/design_dropped_criterion_broken.md` (+ ticket fixture) surface the dropped "403 unless admin" AC as a blocking finding (lens-level regression probe).
    - [ ] `python3 scripts/run_tests.py` still green.

---

## Rollback Notes

- Step 1 (`qrspi_critics_config.py`): additive constants only — revert by deleting `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES` and their defaults; no migration, no downstream data.
- Steps 2–5 (`qrspi_review_synopsis.py`): new file — revert by deleting it (and its `_test.py`); no other module imports it until Slice 3.
- Step 8 (`qrspi_critic_summary.py`): if a change was made, it is a `.get()`-default read; the `critic-metrics.jsonl` new fields are OPTIONAL and additive, so rolling back the reader leaves old AND new rows parseable (backward-compat is symmetric). No metrics-file migration is performed or required.
- Steps 12–22 (new agents): new files — revert by deleting them; until Slices 3–5 swap the `subagent_type`, no skill references them, so deletion is safe.
- Steps 29–34, 39–48, 53 (SKILL.md edits): config/prose changes with no persisted state — revert via Graphite by restoring the prior commit; the propose-only invariant means no PR branch was ever mutated, so there is nothing to unwind on any reviewed ticket.
- Step 54 (REUSE of `evals/fixtures/design_dropped_criterion_broken.md`; possible new `ticket_dropped_criterion.md`) + Step 55 (README row): test fixtures only, not wired into any runtime path (the eval harness is a non-functional placeholder) — revert by removing any ADDED ticket fixture and the README row(s); the reused design fixture pre-exists and is left untouched.
- No DB migrations, no destructive ops, no config-key removals in this plan.
