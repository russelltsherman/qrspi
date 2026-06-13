#!/usr/bin/env python3
"""Pure synthesis reducer for the QRSPI multi-lens design critic panel (RUS-56).

Why this exists
---------------
The Stage-1 (design) critic is a *panel*: M independent lens agents (completeness,
internal-consistency, edge-alignment, simplicity) each critique the produced design
against its upstream inputs and emit a `{pass, findings}` verdict. Before the loop
decision (`next_action` in qrspi_critic_loop.py) can act, those M per-lens verdicts must
be reduced to ONE authoritative verdict for the round. That reduction is the only piece of
the panel worth unit-testing, so it lives here as a pure, stdlib-only function with no
agent / IO / git coupling (mirroring qrspi_critic_loop.py — ref: structure §Contracts,
Decision 1). The JS glue (`runCriticPanelLoop`) keeps only the untestable lens fan-out and
delegates this reduction to `synthesize` below.

Reduction rule (ref: OQ2, structure §New Types `SynthesizedVerdict`):
  - `pass` is True only if EVERY coerced lens passed (any single fail ⇒ the round fails).
  - `findings` is the exact-string-deduped UNION of all lens findings, preserving
    first-seen order. No lens is privileged.
  - Optional lens-tagging: when a lens entry carries a lens identifier, each emitted
    finding may be wrapped as `{"text": ..., "lens": ...}` for audit. Bare-string findings
    on an unidentified lens stay bare.

Fail-closed: every entry is coerced through the LANDED `parse_critic_verdict` /
`_coerce_verdict` from qrspi_critic_loop.py first — a malformed / empty / non-dict entry
reads as NOT-passed and contributes no findings, so a garbled lens reply can never silently
pass the round (ref: Q11, structure Slice 1).
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from qrspi_critic_loop import (  # noqa: E402
    _coerce_verdict,
    parse_critic_verdict,
)


def _coerce_lens(entry):
    """Coerce one lens entry to the canonical `{pass: bool, findings: list}` shape using the
    LANDED coercion (no re-implemented logic): a dict goes through `_coerce_verdict`, a string
    through `parse_critic_verdict`, anything else fails closed to NOT-passed. Pure helper."""
    if isinstance(entry, dict):
        return _coerce_verdict(entry)
    if isinstance(entry, str):
        return parse_critic_verdict(entry)
    return {"pass": False, "findings": []}


def _lens_id(entry):
    """Extract an optional lens identifier from a raw lens entry (the dict's `lens` key), or
    None. Used only for optional finding-tagging; absence leaves findings bare."""
    if isinstance(entry, dict):
        lens = entry.get("lens")
        if isinstance(lens, str) and lens:
            return lens
    return None


def _finding_key(finding):
    """The exact-string dedupe key for a finding. A bare string keys on itself; a
    `{text, lens}`-style dict keys on its `text` so the same finding text from two lenses
    dedupes to one (ref: OQ2 'exact-string-deduped union')."""
    if isinstance(finding, dict):
        text = finding.get("text")
        return text if isinstance(text, str) else repr(finding)
    return finding


def synthesize(verdicts):
    """Reduce M lens verdicts to one authoritative `SynthesizedVerdict`.

    `verdicts` is the list of raw per-lens replies for one round. Each entry is coerced
    fail-closed via the landed `parse_critic_verdict` / `_coerce_verdict` before reduction.

    Returns `{"pass": bool, "findings": list}`:
      - `pass` is True ONLY if the verdict list is non-empty AND every coerced lens passed.
        An empty list reads as NOT-passed (no lens attested the design — fail closed).
      - `findings` is the exact-string-deduped union of every lens's findings, in first-seen
        order. When a lens carries a `lens` identifier, its bare-string findings are wrapped
        as `{"text": <finding>, "lens": <lens>}`; findings from an unidentified lens, and
        findings that are already `{text, lens}` dicts, are emitted unchanged.

    Pure: no IO, never raises (every entry is coerced fail-closed).

    Signature: synthesize(verdicts: list) -> dict
    """
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}

    all_passed = True
    findings = []
    seen = set()

    for entry in verdicts:
        coerced = _coerce_lens(entry)
        if not coerced["pass"]:
            all_passed = False
        lens = _lens_id(entry)
        for finding in coerced["findings"]:
            key = _finding_key(finding)
            if key in seen:
                continue
            seen.add(key)
            # Tag bare-string findings with their lens when one is known; leave
            # already-structured ({text, lens}) findings and unidentified-lens findings as-is.
            if lens is not None and isinstance(finding, str):
                findings.append({"text": finding, "lens": lens})
            else:
                findings.append(finding)

    return {"pass": all_passed, "findings": findings}


# --- thin CLI (RUS-56 Slice 3) ---------------------------------------------
# A deterministic stdin->stdout shim so the JS orchestrator (which cannot run python in its
# sandbox) can invoke the pure `synthesize` reducer via a worker, exactly like
# qrspi_critic_loop.py exposes `next_action`. The pure function above is unchanged; this only
# exposes it.
#
#   printf '%s' '<json verdicts array>' | python3 qrspi_critic_synthesize.py
#
# Reads a JSON ARRAY of per-lens verdict entries from stdin (each entry is coerced fail-closed
# inside `synthesize`, never raising), then prints the synthesized round verdict as JSON:
# { pass, findings }. A non-array / unparseable stdin reduces to the empty list ⇒ fail-closed
# { "pass": false, "findings": [] } (no lens attested the design).
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reduce M per-lens verdicts (stdin JSON array) to one round verdict (self-contained CLI)")
    parser.parse_args(argv)

    raw = sys.stdin.read()
    try:
        verdicts = json.loads(raw) if raw.strip() else []
    except (ValueError, TypeError):
        verdicts = []

    result = synthesize(verdicts)
    json.dump(result, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
