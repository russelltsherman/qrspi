# Work Tree — Holistic design critic: adversarial node-validity lens with codebase access

**Plan basis:** plan.md @ 2026-06-16T00:00:00Z
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T18 → T19

## Session 1

**Load:** structure.md §Slice 1, plan.md §Slice 1, design.md Decision 2 / AC3 / AC8 (default-OFF invariant)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Decouple whitelist from default set in `qrspi_critics_config.py` (`KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) \| {"design-review"}`, default-OFF) | — | §1.1 | S | pending |
| T2 | Add decoupling comment above `KNOWN_DESIGN_LENSES` recording deliberate default-OFF intent | T1 | §1.2 | S | pending |
| T3 | Test: default resolve of `resolve_design` is still exactly the four lenses, `design-review` absent | T2 | §1.3 | S | pending |
| T4 | Test: `resolve_design` DROPS an unlisted `design-review` (with warning) | T3 | §1.4 | S | pending |
| T5 | Test: `resolve_design` KEEPS `design-review` when config lists it in `critics.design.lenses` | T3 | §1.5 | S | pending |
| T6 | Test: empty-after-filter resolve still falls back to the four `DEFAULT_DESIGN_LENSES` | T3 | §1.6 | S | pending |
| T7 | Run `python3 scripts/run_tests.py qrspi_critics_config` — all assertions green | T4, T5, T6 | §1.7 | S | pending |
| T8 | **Verify Slice 1** — full suite green; `DEFAULT_DESIGN_LENSES` still the four (default-OFF preserved) | T7 | §1.8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (config decoupling) complete and verified. Fresh context for Slice 2, which adds the agent + JS wiring + teeth fixture — a different file set and larger surface.

## Session 2

**Load:** structure.md §Slice 2, plan.md §Slice 2, design.md AC1/AC2/AC4/AC5/AC7 + Decision 1/3/5 + §Delta items 2–4, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9 | Create `.claude/agents/qrspi-design-critic-design-review.md` node-validity lens agent (`tools: Read, Grep`; phase-generic framing; consumes DESIGN_PATH/RESEARCH_PATH/CODEBASE_PATH; digest opt-out; blocking-only `{pass, findings}`) | T8 | §2.9 | L | pending |
| T10 | Add `codebasePath: wd` to the `designCritic` object in `doDesign` (`qrspi-batch.js`) | T9 | §2.10 | S | pending |
| T11 | Splice uniform `CODEBASE_PATH: <criticConfig.codebasePath>` line into every lens prompt in `runCriticPanelLoop` | T10 | §2.11 | M | pending |
| T12 | Replace hard-coded "Read all four paths" wording with path-agnostic wording in `runCriticPanelLoop` | T11 | §2.12 | S | pending |
| T13 | Add labelled `design-review` node-defect (false codebase claim, verified-absent symbol, unique marker) to `evals/teeth/design.md` | T12 | §2.13 | M | pending |
| T14 | Add `design-review: <marker>` to `LENS_MARKERS` in `qrspi-teeth-eval.js` | T13 | §2.14 | S | pending |
| T15 | Ensure eval critic config lists `design-review` in `critics.design.lenses` (teeth-run activation) | T14 | §2.15 | S | pending |
| T16 | Test: five-lens AND-reduction in `qrspi_critic_synthesize_test.py` (all-pass → pass; one-fail → fail) | T12 | §2.16 | S | pending |
| T17 | Test: add `design-review` marker to asserted marker/owning-lens map in `qrspi_teeth_assert_test.py` (if present) | T13 | §2.17 | S | pending |
| T18 | Run `python3 scripts/run_tests.py` — full suite green (five-lens synthesize + teeth-assert additions) | T16, T17 | §2.18 | S | pending |
| T19 | **Verify Slice 2** — full suite green; agent frontmatter `tools: Read, Grep` (no Bash/model key); teeth e2e: `design-review` fails on marker (AC5/AC2), passes clean design (AC6) | T15, T18 | §2.19 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. After Verify Slice 2 the feature is implementation-complete; no further session follows.
