#!/usr/bin/env python3
"""Pure-stdlib helpers for the on-demand /review-* review family (RUS-91).

Why this exists
---------------
The `/review-*` skills used to hand-compose a prose synopsis keyed only on the
terminal action, and fed the ENTIRE per-lens verdict array to the reducer
(`qrspi_critic_synthesize.py`). RUS-91 widens both ends:

  - the synopsis must be HONEST and axis-enumerated — one row per lens with its
    pass + blocking finding count — plus a distinct advisory non-blocking-notes
    section and a decision-readiness "blocking-for-human" section;
  - the terminal-advisory `decision-readiness` lens output must be PARTITIONED
    out of the array fed to the reducer so it never drives a `revise` round;
  - the `critic-metrics.jsonl` row gains OPTIONAL additive fields (`axes`,
    `nonBlockingNotes`) derived from the same pre-reduction verdict array.

This module is the single tested source of truth for those three transforms.
All functions are pure (no I/O) and stdlib-only so they run under
`scripts/run_tests.py` in CI.

Data shapes (structure.md §New Types / §Contracts)
--------------------------------------------------
A `LensVerdict` element of the pre-reduction verdict array::

    {
      "lens": str,
      "pass": bool,
      "findings": [str],
      "nonBlockingNotes": [str],   # OPTIONAL advisory channel (Decision 4)
    }

The terminal-advisory `DecisionReadinessVerdict`::

    {
      "lens": "decision-readiness",
      "blockingDecisions": [{"question": str, "rationale": str}],
      "answerable": [{"question": str}],
    }
"""

DECISION_READINESS_LENS = "decision-readiness"


# --- pure core -------------------------------------------------------------

def _as_list(value):
    """Return value when it is a list, else an empty list (lenient read)."""
    return value if isinstance(value, list) else []


def _blocking_count(verdict):
    """Blocking finding count for one LensVerdict — len of its `findings` list.

    `findings` is the BLOCKING channel; `nonBlockingNotes` is advisory and is
    NOT counted here."""
    return len(_as_list(verdict.get("findings")))


def partition_decision_readiness(verdict_array):
    """Split the decision-readiness lens out of the pre-reduction verdict array.

    Returns ``(panel_array, decision_readiness_verdict)`` where ``panel_array``
    is every verdict EXCEPT the decision-readiness one (this is what is fed to
    ``qrspi_critic_synthesize.py`` so the terminal-advisory lens never drives a
    revise round — Decision 5), and ``decision_readiness_verdict`` is the single
    decision-readiness element, or ``None`` when the lens is absent.

    Pure; does not mutate the input. If more than one decision-readiness element
    is present (it should not be), the FIRST is returned and the rest are dropped
    from the panel array (they are advisory either way)."""
    verdict_array = _as_list(verdict_array)
    panel = []
    decision_readiness = None
    for verdict in verdict_array:
        if isinstance(verdict, dict) and verdict.get("lens") == DECISION_READINESS_LENS:
            if decision_readiness is None:
                decision_readiness = verdict
            continue
        panel.append(verdict)
    return panel, decision_readiness


def ledger_row_fields(verdict_array):
    """Derive the OPTIONAL additive ``critic-metrics.jsonl`` fields.

    Returns a dict with::

        {
          "axes": [{"lens": str, "pass": bool, "blockingCount": int}, ...],
          "nonBlockingNotes": [str, ...],   # union across all lenses
        }

    Built from the SAME pre-reduction verdict array the synopsis renders from
    (the reduced ``{pass, findings}`` alone is insufficient — the axes must
    enumerate every lens). Pure; the fields are additive so a reader that does
    not know them (`qrspi_critic_summary.summarize`, which reads via `.get()`)
    is unaffected."""
    verdict_array = _as_list(verdict_array)
    axes = []
    non_blocking = []
    for verdict in verdict_array:
        if not isinstance(verdict, dict):
            continue
        axes.append({
            "lens": verdict.get("lens"),
            "pass": bool(verdict.get("pass")),
            "blockingCount": _blocking_count(verdict),
        })
        non_blocking.extend(
            note for note in _as_list(verdict.get("nonBlockingNotes"))
        )
    return {"axes": axes, "nonBlockingNotes": non_blocking}


def render_synopsis(verdict_array, decision_readiness, terminal_action):
    """Render the honest, axis-enumerated synopsis as a Markdown string.

    Sections:
      1. **Axis enumeration** — one row per lens (PASS/FAIL + blocking count),
         from the PRE-reduction verdict array (the reduced view is insufficient).
      2. **Advisory non-blocking notes** — the union of every lens's
         ``nonBlockingNotes`` (Decision 4); rendered DISTINCT from blocking
         findings so an advisory note never reads as a blocker.
      3. **Decision readiness (blocking for human)** — the
         ``DecisionReadinessVerdict``'s ``blockingDecisions`` (Decision 5);
         these surface to the human but trigger NO revise round.
      4. **Terminal action** — the reducer's resolved terminal action.

    ``decision_readiness`` may be ``None`` (lens absent) — its section is then
    omitted. Pure; returns a string and performs no I/O."""
    verdict_array = _as_list(verdict_array)
    lines = []

    # 1. Axis enumeration -----------------------------------------------------
    lines.append("### Review axes")
    lines.append("")
    lines.append("| Lens | Verdict | Blocking findings |")
    lines.append("| --- | --- | --- |")
    for verdict in verdict_array:
        if not isinstance(verdict, dict):
            continue
        lens = verdict.get("lens")
        passed = bool(verdict.get("pass"))
        count = _blocking_count(verdict)
        verdict_label = "PASS" if passed else "FAIL"
        lines.append(f"| {lens} | {verdict_label} | {count} |")
    lines.append("")

    # 2. Advisory non-blocking notes -----------------------------------------
    non_blocking = []
    for verdict in verdict_array:
        if isinstance(verdict, dict):
            non_blocking.extend(_as_list(verdict.get("nonBlockingNotes")))
    if non_blocking:
        lines.append("### Advisory (non-blocking)")
        lines.append("")
        for note in non_blocking:
            lines.append(f"- {note}")
        lines.append("")

    # 3. Decision readiness (blocking for human) -----------------------------
    if isinstance(decision_readiness, dict):
        blocking = _as_list(decision_readiness.get("blockingDecisions"))
        if blocking:
            lines.append("### Decision readiness (blocking for human)")
            lines.append("")
            for item in blocking:
                if not isinstance(item, dict):
                    continue
                question = item.get("question", "")
                rationale = item.get("rationale", "")
                if rationale:
                    lines.append(f"- {question} — {rationale}")
                else:
                    lines.append(f"- {question}")
            lines.append("")

    # 4. Terminal action ------------------------------------------------------
    lines.append(f"**Terminal action:** {terminal_action}")

    return "\n".join(lines)
