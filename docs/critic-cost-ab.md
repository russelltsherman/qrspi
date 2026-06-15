# Runbook: Design-Critic Digest Cost A/B (manual, opt-in)

**Status:** Manual procedure — **NOT a deterministic test, NOT wired into `run_tests.py` / CI.**

This runbook documents the optional, manual, run-level token A/B that substantiates the
**literal** "measurably fewer tokens" cost claim for the design-critic **digest lever**
(shipped in RUS-77, commit `c6fa275`). Follow it once if a reviewer wants the externally
observed token figure (the dimension comparable to the ~749K-token observation that motivated
the lever); it is not part of the automated gate.

## What is already covered automatically (cited, not re-created)

The **structural** cost claim and the config resolution of the lever are already proven by
shipped RUS-77 unit tests — they run in `python3 scripts/run_tests.py` and in CI. This runbook
does **not** re-create them:

- **Digest is strictly shorter than the source research** —
  `scripts/qrspi_research_digest_test.py::test_digest_strictly_shorter`
  (plus `test_strips_all_fenced_evidence`, `test_deterministic_across_runs` for the trim shape
  and determinism).
- **The lever defaults OFF and the opt-in parses** —
  `scripts/qrspi_critics_config_test.py::test_digest_default_off` and
  `scripts/qrspi_critics_config_test.py::test_digest_enabled_true_parses`.

What those tests do **not** measure is the **literal external token count** of a real
design-panel run with the lever OFF vs ON. That is what this runbook adds — and only manually,
because it requires a real multi-agent panel invocation, which is non-deterministic and off CI.

## The lever

`critics.design.digest.enabled` in `.qrspi/config.json` (default **OFF**). When ON, the
research file is trimmed **once** of its verbose evidence code fences into a deterministic
digest (`scripts/qrspi_research_digest.py --research <research.md> --out <digest.md>`) that is
passed by path to every design-critic lens, instead of each lens re-reading the full
`research.md` (the measured cost driver). See `.qrspi/config.example.json` →
`critics.design.digest.$comment_optin` for how to opt in.

## Procedure

Run the **same** ticket through the design-critic panel twice — once with the lever OFF, once
ON — and compare externally observed input-token totals. Keep every other variable fixed (same
ticket, same `research.md`, same lenses, same `maxRounds`, same model).

1. **Pick a ticket** whose `research.md` is evidence-heavy (carries large fenced code/log
   blocks — the exact content the digest trims). A thin research file shows little delta; the
   lever's saving scales with trimmed fence volume.

2. **Sanity-check the structural trim** (optional, fast, local):

   ```sh
   python3 scripts/qrspi_research_digest.py \
     --research .worktrees/<ID>/.qrspi/<ID>/research.md \
     --out /tmp/<ID>-digest.md
   wc -c .worktrees/<ID>/.qrspi/<ID>/research.md /tmp/<ID>-digest.md
   ```

   The digest byte count must be smaller (the same property `test_digest_strictly_shorter`
   asserts). This is a proxy for the token saving, not the literal figure.

3. **Run A — lever OFF.** Ensure `.qrspi/config.json` has `critics.design.enabled: true`
   and `critics.design.digest.enabled: false` (or the `digest` block omitted). Run the design
   phase for the ticket. Record the externally observed **input-token** total for the run
   (e.g. from the provider/usage dashboard, or the harness's per-run token accounting if
   surfaced for that invocation).

4. **Run B — lever ON.** Set `critics.design.digest.enabled: true`, everything else identical.
   Re-run the design phase for the **same** ticket. Record the input-token total the same way.

5. **Compare.** Run B should show **measurably fewer** input tokens than Run A. The expected
   driver is each lens consuming the trimmed digest once instead of the full `research.md`
   per lens; the saving grows with the number of lenses and the volume of fenced evidence
   trimmed.

## Recording the result

Capture the two raw input-token totals, the delta (absolute + percent), the ticket id, the
lens set, and the model used. This is an externally observed, point-in-time measurement — it
is **not** committed as a test fixture or an assertion. If you want a durable note, add it to
the ticket's PR description or the relevant Linear issue, not to the CI suite.

## Why this stays off CI

A real design-critic panel run spawns multiple agents and calls a model — it is
non-deterministic, slow, and cost-incurring, so it cannot be a `scripts/*_test.py` picked up by
`python3 scripts/run_tests.py`. The deterministic guarantees (digest shorter, config resolves)
already live in the cited RUS-77 unit tests; this literal-token A/B is the manual complement,
run on demand only.
