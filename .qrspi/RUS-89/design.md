# Design — Phase review-panel commands (/review-*): on-demand node-validity review panels

**Ticket:** RUS-89
**Research basis:** research.md @ 2026-06-17T20:05:00Z
**Generated:** 2026-06-17T20:40:00Z
**Revised:** 2026-06-17 (review pass — named the scratch-revise actor, wired the loop to the tested `next_action`, gave open-question answers a real output path, and resolved the agreement-pending reconciliation)
**Status:** draft

## Current State

The only surviving critic loop is the batch-path `runCriticPanelLoop(name, id, criticConfig)`, which fans out one `agent()` per lens in `parallel(...)`, reduces verdicts, and converges/revises/caps via the pure `next_action` (ref: Q5, Q8). It runs inside `runPhase`'s pre-persist staging window and **mutates the staged artifact in place** across revise rounds — it is not read-only (ref: Q5). The single-edge `runCriticLoop` was retired in RUS-88 (ref: Q5).

The node-validity lens (`.claude/agents/qrspi-design-critic-design-review.md`, tools Read/Grep) receives named PATH inputs — `DESIGN_PATH`, `RESEARCH_PATH`, `CODEBASE_PATH` (it Reads/Greps real source here), and optional `TICKET_CONTENT_PATH`/`QUESTIONS_PATH`/`DIGEST_PATH` — and emits exactly `{pass, findings}` validated as `CRITIC_VERDICT_SCHEMA`, with the invariant `pass:false ⟺ findings non-empty`. It opts OUT of the digest, always reading full research (ref: Q3). It is opt-in and default-OFF (not in `DEFAULT_DESIGN_LENSES`) (ref: Q3).

`qrspi_resolve.py` prints one JSON envelope with `repoRoot`, `worktreeDir`, `existing` (artifact-name → exists+non-empty), `decision`, `reviewers`/`teamReviewers`, `ticketContentPath`, `tip`, and `slices`. There is **no PR-number field**; the PR is identified indirectly by the phase branch (`<id>/design`, `<id>/plan`, `<id>/slice-N`) (ref: Q1). Artifacts live on disk at `<worktreeDir>/.qrspi/<ticket>/<artifact>.md`, built by `art(wd,id,name)` for reads and `stg(id,name)` (`/tmp/phase-stage/<id>/<name>.md`) for token-free staging (ref: Q2). A missing artifact is `existing[name]=False`; an absent phase PR is reflected in `decision`, not an error or sentinel — the resolver returns the full actual state (ref: Q10).

`qrspi_critic_synthesize.synthesize(verdicts) -> {pass, findings}` reduces M per-lens verdicts for ONE round with AND-semantics (pass only if non-empty and every lens passed; empty ⇒ fail-closed), deduping findings in first-seen order; it is pure, stdlib-only, never raises, and does NOT compare against a human verdict (ref: Q4). The loop tracks `for round in 0..maxRounds` (default 2), carries the staged artifact, `summaryRounds[]`, `metricRounds[]`, and the once-computed `digestPath`/`lensModel`; the cap is `maxRounds`, configurable, not a hard-coded 3 (ref: Q8).

The RUS-78 ledger is the per-ticket critic-metrics JSONL at `<root>/.worktrees/<ticket>/.qrspi/<ticket>/critic-metrics.jsonl`, written by `qrspi_metrics_append.py` (the single envelope authority injecting `ticketId`/`timestamp`/`runId`) from a `CriticStepMetrics` record `{phase, rounds:[{lens,pass,findingsCount}], terminalAction}` (ref: Q7, Q15). There is **NO panel-vs-human agreement field or keying** anywhere — the ledger records only the panel's own verdicts; agreement is net-new (ref: Q7, Q15, Inconsistencies). Cost levers `digest` (`{enabled}`, default OFF) and optional `lensModel` are resolved by `qrspi_critics_config.resolve_design`; `digest` builds one shared `research-digest.md`, `lensModel` is speculative/possibly inert (ref: Q9).

PR comments are posted via `qrspi_comment_reply.py`, which supports a TOPLEVEL fresh-comment mode (`gh pr comment <pr> --body-file -`), is self-locating, and requires `--pr` and `--comment-id` (the latter required even for toplevel) (ref: Q14, Inconsistencies). Skills are `.claude/skills/<name>/SKILL.md` (frontmatter + numbered steps) that parse `$ARGUMENTS` for the ticket id and spawn an agent by `subagent_type`; there is **no `/review-*` family today** — it is net-new (ref: Q6). No "scratch copy" mechanism exists; "no push" is a structural property (the critic loop touches only `/tmp` + `agent()`; only finalize calls `gt submit`) (ref: Q12). Frontier = highest REAL (≥1 commit ahead of trunk) phase via `max(existing, key=_order)`; partially-landed stacks can misfire to `entry_blocked` (known bug) so a `/review` should check `gh pr list --state all` (ref: Q11). Tested seams are pure stdlib functions with `_test.py` siblings using a `check(label, got, want)` idiom; agent fan-out is never stubbed — the JS glue is not tested (ref: Q13).

## Desired End State

A net-new, human-invoked `/review-*` skill family, advisory + propose-only, that never mutates or pushes the open PR branch. Mapping each acceptance criterion to behavior:

- **AC1 — `/review-design` end-to-end.** `/review-design <id>` runs `qrspi_resolve.py`, reads `worktreeDir`/`existing`, derives the design PR number via `gh pr list --head <id>/design --json number`, copies `design.md` to a scratch path under `/tmp/phase-stage/<id>/review/`, then runs the **scratch loop**: each round spawns the `qrspi-design-critic-design-review` lens against the scratch copy + real codebase, reduces the per-round verdict(s) with `qrspi_critic_synthesize.py`, and feeds that reduced verdict into the tested pure **`next_action(verdicts, round, max_rounds)`** (`scripts/qrspi_critic_loop.py`) for the converge/revise/cap decision (≤3 rounds). On a `revise` action the **phase producer agent `qrspi-design` is re-spawned to rewrite the *scratch copy* in place** — the lens itself only emits `{pass, findings}` and is barred from writing files, so the reviser is the producer, exactly the `runCriticPanelLoop` producer-as-reviser pattern (`qrspi-batch.js:851-865`) but pointed at `/tmp` instead of the staged artifact. After the loop terminates, a **separate open-question-resolution pass** — the phase producer `qrspi-design` (full upstream context + codebase access), NOT the strict-schema lens — answers the design's Open Questions section in free text. The command posts an advisory synopsis (verdict + findings + resolved open-question answers) as a toplevel comment on the design PR. No `gt submit`/`gt modify`/branch write occurs.
- **AC2 — agreement instrumentation.** Each run builds a `CriticStepMetrics`-shaped record (via `qrspi_critic_metrics.build_record`) extended with an `agreement` block (panel verdict vs. the PR's human `reviewDecision`) and a `mode: "on-demand-review"` discriminator, appended to the RUS-78 critic-metrics JSONL via the existing `qrspi_metrics_append.py` mechanism (which keys every line by `ticketId`/`timestamp`/`runId`). When the human has not yet reviewed (`reviewDecision` is `None` — the common case for an advisory run before the reviewer acts), the row logs `agreement: "pending"` rather than a false disagreement; **reconciliation is by re-invocation** — re-running `/review-design` after the human decides emits a fresh row whose `agreement` now resolves against the present decision, and offline analysis joins the latest pre-decision (`pending`) row to the later decided row by `ticketId`+`phase`. **Token-cost dimension deferred:** the harness exposes no per-subagent token usage (ref: Q15), so `tokensIn`/`tokensOut` are omitted in v1 — agreement is logged without cost (OQ4).
- **AC3 — `/review-plan`.** A new plan node-validity lens agent (steps technically sound vs. real code) + `/review-plan <id>` command, posting a synopsis to the plan PR.
- **AC4 — `/review-implementation`.** A new impl lens agent (correctness/security/efficiency/performance vs. real code + tests) + `/review-implementation <id>` command; one rolled-up synopsis comment on the top slice PR.
- **AC5 — `/review` comprehensive.** A whole-stack coherence pass `/review <id>` posting a synopsis to the frontier PR (checking `gh pr list --state all` to avoid the partially-landed misfire, ref: Q11).
- **AC6 — separate path, no batch regression.** The on-demand engine reuses the lens *agents* and the `synthesize` *script* only; it does NOT touch `runCriticPanelLoop` or any batch gating code. Default critic config stays OFF (ref: Q9), so batch behavior is byte-for-byte unchanged.
- **AC7 — tests + docs.** New pure reducers (agreement, scratch-loop verdict aggregation, resolve-field extraction) get `scripts/*_test.py` siblings green under `python3 scripts/run_tests.py`; commands verified by manual e2e; CLAUDE.md documents the family.

## Delta

New skill directories (each a thin wrapper mirroring `qrspi-research`, ref: Q6): `.claude/skills/review-design/SKILL.md`, `.claude/skills/review-plan/SKILL.md`, `.claude/skills/review-implementation/SKILL.md`, `.claude/skills/review/SKILL.md`. Each parses `$ARGUMENTS`, runs `qrspi_resolve.py`, derives the phase PR number, drives the scratch loop, and posts the synopsis. Authored via `skill-creator` (constraint).

New agent definitions (mirroring the design-review lens, ref: Q3): `.claude/agents/qrspi-plan-critic-plan-review.md` (AC3) and `.claude/agents/qrspi-impl-critic-impl-review.md` (AC4). The existing `qrspi-design-critic-design-review.md` is reused as-is (read-only `{pass, findings}` lens) for AC1/AC5. **The scratch-revise actor is the existing phase producer agent** — `qrspi-design` for `/review-design`, `qrspi-plan` for `/review-plan`, `qrspi-implement` for `/review-implementation` — re-spawned to rewrite the *scratch copy* in place (the same producer-as-reviser pattern `runCriticPanelLoop` uses at the staged artifact, `qrspi-batch.js:851-865`; the lens never writes). **Open-question resolution** (AC1) is a separate post-loop codebase-access pass reusing the phase producer `qrspi-design`, kept out of the strict `{pass, findings}` lens whose validated schema (`CRITIC_VERDICT_SCHEMA`) has no field for answers. No NEW reviser/resolver agent is introduced — both roles reuse the existing producers.

New pure Python seams with `_test.py` siblings (ref: Q13): `scripts/qrspi_review_agreement.py` (compute `{panelVerdict, humanVerdict, agreement}` from a panel `{pass}` and a human review decision string, with the `None`→`"pending"` category); `scripts/qrspi_review_record.py` (build the agreement-extended ledger record, reusing `qrspi_critic_metrics.build_record` shape + the new agreement block + `mode` discriminator). Reused unchanged: `qrspi_critic_synthesize.py` (per-round multi-lens reduce), **`scripts/qrspi_critic_loop.py`'s `next_action` (the converge/revise/cap decision — the same tested loop seam the batch path uses, invoked via its CLI shim)**, `qrspi_metrics_append.py`, `qrspi_resolve.py`, `qrspi_comment_reply.py`.

Modified: `scripts/qrspi_comment_reply.py` — relax `--comment-id` to optional in toplevel mode (a synopsis has no comment to reply to) (ref: Q14, Inconsistencies). `CLAUDE.md` (and worktree copy) — document the `/review-*` family.

Open question (deferred per Out of Scope): whether `/review-plan` and `/review-implementation` also resolve their phases' open questions — design panel definitely does.

## Pattern Decisions

### Decision 1: Where the loop/orchestration lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Skill SKILL.md drives the scratch loop directly (Bash + Agent), like `qrspi-work`'s state machine | No new JS workflow; reuses skill convention (ref: Q6); fully separate from batch (AC6) | Loop logic in markdown prose; harder to keep deterministic |
| B | New `.claude/workflows/review.js` workflow invoked by the skills | Deterministic JS control flow via `workflow-creator` | New harness-coupled, untestable JS (ref: Q5); heavier; risks drifting toward batch coupling |

**Recommendation:** Option A
**Rationale:** The reusable determinism — per-round reduce via `synthesize`, the converge/revise/cap decision via the tested pure **`next_action`** (`scripts/qrspi_critic_loop.py`), and the agreement reducer — all lives in tested pure Python (ref: Q13, Discovered Patterns "pure-core/harness-shell split"), so the SKILL.md prose only *sequences* spawn-lens → `synthesize` → `next_action` → (re-spawn producer-reviser | stop); it never re-implements stable-detection or round-counting itself. That thin spawn+post sequence is what `qrspi-work` already demonstrates running in-skill (ref: Q6). This keeps the on-demand path maximally separate from `runCriticPanelLoop` (AC6) and avoids a second harness-coupled JS file. The constraint permits a Workflow only "any Workflow via workflow-creator" — it does not require one.
**NEW PATTERN?** No — mirrors the `qrspi-work` in-skill orchestration pattern (ref: Q6) and reuses the batch path's `next_action` loop seam unchanged.

### Decision 2: Scratch-copy isolation (no-push guarantee)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Copy artifact to `/tmp/phase-stage/<id>/review/<artifact>.md`; lens reads the copy; on `revise` the re-spawned phase producer rewrites the copy; never call `gt`/`gh`-write to the branch | Reuses the `/tmp/phase-stage` staging convention (ref: Q12, Discovered Patterns); no-push by separation of concerns | Relies on discipline (no enforcement primitive exists, ref: Q12) |
| B | Spin up a second git worktree of the PR branch for the scratch revise | True git isolation | Heavy; no existing helper (ref: Q12); risks accidental push; over-engineered for an advisory read |

**Recommendation:** Option A
**Rationale:** Research found no scratch-copy or no-push primitive; the existing structural guarantee is "the critic loop only touches `/tmp` + `agent()`; only finalize pushes" (ref: Q12). Reusing `/tmp/phase-stage/<id>/` matches the established convention and trivially satisfies "does NOT push" by never invoking `gt submit`/`gt modify`/`gh`-write on the branch (AC1, constraint).
**NEW PATTERN?** Yes (a per-review scratch subdirectory) — justified because no scratch-copy mechanism exists (ref: Q12); it is a minimal extension of the existing `/tmp/phase-stage` staging root, not a new concept.

### Decision 3: Recording panel-vs-human agreement

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend the `CriticStepMetrics` record with an `agreement` block and append via `qrspi_metrics_append.py` to the same `critic-metrics.jsonl` | Reuses the single envelope authority + JSONL append exactly (ref: Q7); additive field, old consumers ignore it | The ledger now mixes batch-gate rows and on-demand-review rows (disambiguate via a `source`/`mode` tag) |
| B | New separate `review-agreement.jsonl` ledger | Clean separation of concerns | Duplicates the append/envelope mechanism; AC2 says "reusing the RUS-78 ledger" |

**Recommendation:** Option A
**Rationale:** AC2 explicitly says reuse the RUS-78 ledger; research confirms the agreement concept is net-new and the storage mechanism (JSONL append keyed by `ticketId`/`runId`/`phase`) is reusable as-is by ADDING a field (ref: Q7, Inconsistencies). Add a `mode: "on-demand-review"` discriminator so batch-gate and review rows are separable for the future data-gated analysis (ref: Q15).
**NEW PATTERN?** No — extends the existing record/appender; the `agreement` field is new data, not a new mechanism (ref: Q7).

### Decision 4: How the panel learns the human verdict for agreement

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Read the PR's `reviewDecision` from the gather (`qrspi_pr_state.build_state` → `state["phases"]`) at review time | Reuses existing gather; one source of truth (ref: Q1, Q11) | If the human hasn't reviewed yet, `reviewDecision` is None → agreement = "no-human-verdict-yet" |
| B | Re-query the PR via fresh `gh pr view --json reviewDecision` in the skill | Decoupled from the resolve envelope | Duplicate gh call; second source of PR state |

**Recommendation:** Option A
**Rationale:** The resolver already gathers per-phase review state including absent-PR shapes (`reviewDecision: None`) (ref: Q10, Q11); the agreement reducer treats None as a distinct "pending" agreement category rather than a disagreement, fail-soft. This avoids a second PR-state source.
**NEW PATTERN?** No — consumes existing gather output (ref: Q1, Q11).

### Decision 5: Where resolved open-question answers go (the lens schema can't hold them)

AC1 requires the design panel to **resolve the design's open questions**, but the reused `qrspi-design-critic-design-review` lens emits exactly `{pass, findings}` (`CRITIC_VERDICT_SCHEMA`) and is told "Do not write any files" (ref: Q3) — its validated output has no field for free-text answers.

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Resolve open questions in a **separate post-loop pass** by the phase producer `qrspi-design` (codebase access + full upstream context); capture its free-text answers and splice them into the synopsis comment | Keeps the lens contract intact; reuses an existing producer (no new agent); answers are real prose, not schema-abused | One extra agent spawn per review |
| B | Overload the lens `findings` to also carry open-question answers | No extra spawn | Corrupts the `pass:false ⟺ findings non-empty` invariant; mixes "blocking defect" and "answered question"; breaks `synthesize`/`next_action` semantics |

**Recommendation:** Option A
**Rationale:** The lens's strict binary verdict is load-bearing for `synthesize`/`next_action` (a finding means "revise"); answers are not defects and must not feed the revise loop. A distinct producer pass with codebase access produces answers in the form the synopsis needs, at the cost of one spawn (acceptable for a human-invoked, advisory command).
**NEW PATTERN?** No — a producer pass over the same artifact + codebase, output captured as text for the comment (the synopsis already aggregates free text).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Accidental branch mutation/push during scratch revise (violates v1 advisory posture) | low | high | Scratch copy in `/tmp` only; skill steps never call `gt submit`/`gt modify`/`gh`-write to the branch; e2e check that PR head SHA is unchanged after a review (ref: Q12) |
| Coupling the on-demand path back into `runCriticPanelLoop`, regressing the batch gate (AC6) | med | high | Reuse only the lens *agents* + `synthesize` script; touch no batch JS; keep all critic config OFF by default (ref: Q5, Q9); no shared mutable state |
| `qrspi_comment_reply.py --comment-id` required even for toplevel blocks a synopsis post | high | med | Relax `--comment-id` to optional in toplevel mode (small, tested change) (ref: Q14, Inconsistencies) |
| PR number absent from resolve envelope → synopsis posts to wrong/no PR | med | med | Derive PR number per phase via `gh pr list --head <id>/<phase> --json number`; for `/review` use `--state all` to dodge the partially-landed misfire (ref: Q1, Q11, Q14) |
| Codebase-access panels token-heavy across ≤3 rounds × multiple lenses | med | med | Keep default rounds modest (constraint); reuse `digest` cost lever where the lens permits (design lens opts out, ref: Q3, Q9); document expected cost |
| Agreement ledger conflated with batch-gate rows, polluting future analysis | low | med | Tag review rows with `mode: "on-demand-review"`; pure reducer + `_test.py` (ref: Q7, Q15) |
| `qrspi-design-critic-design-review` files also edited by RUS-88/RUS-77 family (shared critic files) | med | med | Reuse the design lens read-only; new lenses are net-new files; rebase whoever lands second (ticket Relationships) |

## Open Questions

- OQ1: Should `/review-plan` and `/review-implementation` also resolve their phases' open questions, or is open-question resolution design-phase-only in v1? (Ticket marks this an explicit design-phase decision; Out of Scope leaves it open. Design-phase resolution is settled — Decision 5; the plan/impl extension stays open.)
- ~~OQ2~~ **RESOLVED (Decision 4 + AC2):** when `reviewDecision` is `None` the reducer emits a distinct `agreement: "pending"` bucket (never a false disagreement), and reconciliation is by re-invocation — a later run after the human decides emits a decided row joined to the pending row by `ticketId`+`phase`.
- OQ3: For `/review` comprehensive, should the synopsis aggregate per-phase lens verdicts into one whole-stack verdict, or post per-phase sub-synopses under one comment? (AC5 says "one synopsis to the frontier PR" but the aggregation shape is unspecified.)
- ~~OQ4~~ **RESOLVED (AC2):** deferred for v1 — the harness exposes no per-subagent token usage (ref: Q15), so agreement is logged without `tokensIn`/`tokensOut`; the cost dimension of RUS-78 is explicitly out of scope here.
- OQ5: `lensModel` may be inert (no evidence the harness honors `agent().model`) (ref: Q9). Should v1 wire it speculatively or omit it until verified? (Leaning omit-until-verified.)
