#!/usr/bin/env python3
"""Pure multi-lens verdict synthesis for the QRSPI design critic panel (RUS-56).

Why this exists
---------------
The design critic panel (`runCriticPanelLoop` JS glue in
`.claude/workflows/qrspi-batch.js`) fans out M lens agents per round — completeness,
internal-consistency, edge-alignment, simplicity — each returning its own
`{pass, findings}` `LensVerdict`. Before the loop's `next_action` decision can run, those
M per-lens verdicts must be reduced to ONE authoritative `SynthesizedVerdict` for the
round (ref: structure §New Types `SynthesizedVerdict`, §Contracts `synthesize`, OQ2).

That reduction is the one piece of the panel worth unit-testing, so it lives here as a
pure stdlib-only module with no agent / IO / git coupling. The JS glue keeps only the
untestable agent-spawn mechanics and delegates the reduction to `synthesize` below, which
the panel appends to its per-round verdict list before calling the landed
`next_action(verdicts, round, max_rounds)`.

Reduction rules (OQ2 — no lens privileged):
  - `pass` is True ONLY if EVERY lens passed (all-pass AND). Any single failing lens — or
    any malformed lens reply, which fails closed to NOT-passed — makes the round not pass.
  - `findings` is the exact-string-deduped UNION of every lens's findings, preserving
    first-seen order across lenses. When a lens entry carries a lens identifier, each of
    its findings may be lens-tagged as `{text, lens}` for audit; bare-string findings stay
    bare (ref: §New Types `LensVerdict` findings `list[str | {text, lens}]`).

Each lens entry is coerced through the LANDED, fail-closed `parse_critic_verdict`
(reused, never re-implemented) before reduction, so a garbled lens reply can never
silently mark the round converged.
"""

import json
import os
import sys

# Sibling import of the landed fail-closed coercion. Self-locating sys.path insert so the
# module imports the same way regardless of the caller's cwd (matches the established
# pattern in qrspi_critic_loop_test.py / qrspi_pr_body.py).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from qrspi_critic_loop import next_action, parse_critic_verdict  # noqa: E402


def _lens_label(entry):
    """Best-effort lens identifier for an entry, for optional finding tagging.

    A lens identifier may ride alongside the verdict as a `lens` (or `name`) key on the
    raw entry dict. Returns the string label or None. Pure; never raises."""
    if isinstance(entry, dict):
        for key in ("lens", "name"):
            val = entry.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def _finding_text(finding):
    """Normalize a single finding to its plain text for dedup keying.

    A finding is either a bare string or an already-tagged `{text, lens}` dict; in the
    latter case the `text` field is the dedup key. Pure; never raises."""
    if isinstance(finding, dict):
        text = finding.get("text")
        if isinstance(text, str):
            return text
        return str(text) if text is not None else ""
    return finding if isinstance(finding, str) else str(finding)


def synthesize(verdicts):
    """Reduce M per-lens `LensVerdict`s to one authoritative `SynthesizedVerdict`.

    Args:
        verdicts: list of lens entries. Each entry is whatever a lens agent returned —
            a `{pass, findings}` dict (optionally carrying a `lens`/`name` identifier),
            or any malformed value. Every entry is coerced through the landed,
            fail-closed `parse_critic_verdict`-style `_coerce`... — actually via
            `parse_critic_verdict` when the entry is a string, and the canonical coercion
            when it is already a dict — before reduction.

    Returns:
        {"pass": bool, "findings": list} where:
          - `pass` is True ONLY if every coerced lens passed (all-pass AND); an empty
            list of lenses yields `pass: False` (fail closed — no lens vouched for it).
          - `findings` is the exact-string-deduped union of all lens findings, in
            first-seen order. A finding is lens-tagged as `{text, lens}` when its lens
            entry carried a lens identifier; otherwise it stays a bare string. Dedup keys
            on the plain finding text, so the same text from two lenses appears once
            (first occurrence — and its tag — wins).

    Pure; touches no filesystem / agent / git. Never raises.

    Signature: synthesize(verdicts: list) -> dict
    """
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}

    all_passed = True
    findings = []
    seen = set()

    for entry in verdicts:
        label = _lens_label(entry)
        # Coerce fail-closed: strings go through the prose-tolerant parser; everything
        # else (dicts, garbage) is normalized to the canonical {pass, findings} shape by
        # round-tripping through parse_critic_verdict's dict path. We reuse the landed
        # parser rather than re-implementing coercion (ref: §Contracts).
        if isinstance(entry, str):
            coerced = parse_critic_verdict(entry)
        elif isinstance(entry, dict):
            coerced = _coerce_dict(entry)
        else:
            coerced = {"pass": False, "findings": []}

        if not coerced["pass"]:
            all_passed = False

        for finding in coerced["findings"]:
            text = _finding_text(finding)
            if text in seen:
                continue
            seen.add(text)
            if isinstance(finding, dict):
                # Already-tagged finding: keep its existing tag verbatim.
                findings.append(finding)
            elif label is not None:
                findings.append({"text": text, "lens": label})
            else:
                findings.append(text)

    return {"pass": all_passed, "findings": findings}


def _coerce_dict(obj):
    """Canonical fail-closed coercion of an already-parsed dict lens entry to
    `{pass: bool, findings: list}`. Mirrors the landed parser's dict path so synthesize
    handles in-memory dicts (the JS glue ingests via parse_critic_verdict and hands us
    dicts) without re-stringifying. Pure; never raises."""
    passed = bool(obj.get("pass", False))
    found = obj.get("findings", [])
    if not isinstance(found, list):
        found = [found] if found else []
    return {"pass": passed, "findings": found}


# --- round driver (CLI, not unit-tested at module scope) -------------------

def decide_round(verdicts, round, max_rounds):
    """Reduce one round's M lens verdicts AND decide the loop's next move.

    The JS panel loop (`runCriticPanelLoop` in qrspi-batch.js) cannot run python in its
    sandbox, so it delegates the per-round reduction+decision to this one entry point: it
    hands over the M raw lens replies plus the round index and per-phase cap, and gets back
    the single authoritative verdict for the round AND the converge/revise/cap_reached
    action — both computed by reusing the LANDED pure functions (`synthesize` here,
    `next_action` from qrspi_critic_loop), never re-implemented in JS.

    Args:
        verdicts: list of raw per-lens entries (each a {pass, findings} dict, optionally
            carrying a lens/name identifier, or any malformed value — coerced fail-closed).
        round: zero-based index of the current round.
        max_rounds: the per-phase round cap.

    Returns:
        {"action": "converged"|"revise"|"cap_reached",
         "pass": bool,
         "synthesized_findings": list,
         "residual_findings": list}
      where `pass`/`synthesized_findings` are this round's authoritative SynthesizedVerdict
      and `residual_findings` is next_action's carry (the synthesized findings on
      revise/cap_reached, empty on converged). Pure; never raises.
    """
    synthesized = synthesize(verdicts)
    decision = next_action([synthesized], round, max_rounds)
    return {
        "action": decision["action"],
        "pass": synthesized["pass"],
        "synthesized_findings": list(synthesized["findings"]),
        "residual_findings": list(decision["residual_findings"]),
    }


def _main():
    """CLI: read a `{verdicts, round, max_rounds}` JSON envelope from stdin, emit the
    `decide_round` result as JSON on stdout. The single deterministic command the panel
    worker runs per round. A garbled/empty envelope fails closed (no lenses ⇒ not-passed),
    so the loop never reports converged on bad input."""
    raw = sys.stdin.read()
    try:
        env = json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        env = {}
    if not isinstance(env, dict):
        env = {}
    verdicts = env.get("verdicts")
    if not isinstance(verdicts, list):
        verdicts = []
    try:
        round_idx = int(env.get("round", 0))
    except (ValueError, TypeError):
        round_idx = 0
    try:
        max_rounds = int(env.get("max_rounds", 1))
    except (ValueError, TypeError):
        max_rounds = 1
    sys.stdout.write(json.dumps(decide_round(verdicts, round_idx, max_rounds)))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
