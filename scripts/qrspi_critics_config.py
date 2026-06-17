#!/usr/bin/env python3
"""Resolve the OPTIONAL `critics` block of .qrspi/config.json for ALL phases at once.

Why this exists
---------------
The qrspi-batch orchestrator (`.claude/workflows/qrspi-batch.js`) gates a critic on
two phases: a multi-lens PANEL on design, and an opt-in whole-stack coherence pass on
implementation. The fidelity-only edge critic on questions/research/structure/plan and
the per-slice edge critic were retired (RUS-88), so this resolver emits exactly those
two phases. Each needs config resolved with config-value > JS-default precedence:
whether the critic is `enabled`, its `maxRounds`, and (design-only) its
`lenses`/`candidates`, (implementation-only) its nested `coherence` block.

Historically this resolution lived as inline JS functions in qrspi-batch.js, split
across separate `--key critics` config reads. That JS is non-importable (it runs
orchestration at module load) so it could not be unit-tested, and the reads duplicated
the parse logic. This module is the single tested source of truth: it reads config ONCE
and emits a fully-resolved per-phase envelope, so the JS becomes thin glue with ONE read
feeding every phase (the "single read discipline").

Uniform `enabled` vocabulary
----------------------------
The design panel and the implementation coherence pass each honor an `enabled` flag with
the SAME default: OFF. Critics are uniformly opt-in — a phase runs its critic only when
its block sets `enabled: true`. Only an explicit boolean flips the flag; any non-boolean
`enabled` value falls back to the default (OFF).

Like qrspi_config.py / qrspi_resolve.py / qrspi_persist.py, it self-locates the repo
root from `__file__` (two levels up), so the JS caller types only the invocation.

Output: a single JSON envelope on stdout:
    { "ok": true,  "phases": {<design, implementation>}, "warnings": [<str>, ...] }   (exit 0)
    { "ok": false, "phases": {<all defaults>},        "warnings": [], "error": "<verbatim>" }  (exit !=0)

`phases` is ALWAYS present and complete (defaults on any failure) so the best-effort JS
consumer never has to special-case a missing phase.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

# Reuse the sibling's self-locating, best-effort reader (same scripts/ dir is on sys.path
# when run as `python3 scripts/qrspi_critics_config.py`). Avoids duplicating the
# read-config-or-empty idiom.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qrspi_config import read_config  # noqa: E402

# The script lives at <repo-root>/scripts/qrspi_critics_config.py, so the repo root is
# two levels up — derived from __file__, not cwd (mirrors qrspi_config.py).
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MAX_ROUNDS = 2

# The design-critic PANEL lens set (RUS-56) — mirrors DEFAULT_DESIGN_LENSES /
# KNOWN_DESIGN_LENSES in qrspi-batch.js. Config-supplied lenses are filtered to this
# allow-list; unknown names are dropped (with a warning) and an all-unknown set falls
# back to the full default four rather than silently disabling the panel.
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
# Whitelist/default DECOUPLING (RUS-82, design.md Decision 2 Option B): the adversarial
# node-validity lens `design-review` is whitelist-acceptable (a config may opt in to it via
# `critics.design.lenses`) but is DELIBERATELY NOT in DEFAULT_DESIGN_LENSES — it stays
# default-OFF so the default resolved panel is still the four edge-fidelity lenses. Do NOT
# re-couple KNOWN_DESIGN_LENSES back to set(DEFAULT_DESIGN_LENSES): that would either silently
# activate the heavier lens by default or, if added to the default set, defeat the opt-in.
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}

# The design-phase N-select framing axes (RUS-59) — mirrors DEFAULT_DESIGN_FRAMINGS in
# qrspi-batch.js. `candidates` (N) is clamped to [2, len(framings)] when > 1, else 1 (OFF).
DEFAULT_DESIGN_FRAMINGS = ["mvp-first", "risk-first", "extensibility-first"]

def _pos_int_or(value, default):
    """Return value when it is a positive int (NOT a bool), else default.

    Mirrors the JS `Number.isInteger(x) && x > 0 ? x : default` idiom. bool is an int
    subclass in Python, so it is excluded explicitly (True must not read as maxRounds 1)."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    return default


def resolve_enabled(cfg, default):
    """Resolve the uniform `enabled` flag: explicit bool wins, anything else ⇒ default.

    Every phase passes `default` False (critics are uniformly opt-in). A non-boolean
    `enabled` (absent, "", 1, null, junk) falls back to the default rather than coercing,
    so a malformed flag never silently flips a critic. `default` is kept a parameter (not
    hard-coded) so the per-phase resolvers read uniformly and a future per-phase default
    is a one-line change."""
    cfg = cfg if isinstance(cfg, dict) else {}
    value = cfg.get("enabled")
    if value is True:
        return True
    if value is False:
        return False
    return default


def resolve_design(cfg, warnings):
    """Resolve the design-critic PANEL phase. Default OFF (opt-in).

    Returns {enabled, maxRounds, lenses, candidates, digest, lensModel?}.
    Unknown lenses are dropped (warned); an all-unknown/empty set falls back to the default
    four. `candidates` (N-select) is 1 (OFF) unless a finite number > 1, then clamped to
    [2, len(framings)] (clamp-down warned).

    The RUS-77 AC-COST cost-lever gates default OFF / absent so the default resolution
    preserves current behavior (ref: design.md §Delta Decision 3):
      - `digest: {enabled: bool}`     — shared research digest (default {"enabled": False})
      - `lensModel: str`              — per-lens model override (default ABSENT — the key is
                                        omitted entirely, not None, when not configured)

    `warnings` is appended to in place so the CLI can surface what JS used to `log()`."""
    cfg = cfg if isinstance(cfg, dict) else {}
    enabled = resolve_enabled(cfg, False)
    max_rounds = _pos_int_or(cfg.get("maxRounds"), DEFAULT_MAX_ROUNDS)

    lenses = list(DEFAULT_DESIGN_LENSES)
    raw_lenses = cfg.get("lenses")
    if isinstance(raw_lenses, list):
        known = [l for l in raw_lenses if isinstance(l, str) and l in KNOWN_DESIGN_LENSES]
        unknown = [l for l in raw_lenses if not (isinstance(l, str) and l in KNOWN_DESIGN_LENSES)]
        if unknown:
            warnings.append(
                "dropping unknown design-critic lens(es) ["
                + ", ".join(str(u) for u in unknown)
                + "] — known: ["
                + ", ".join(DEFAULT_DESIGN_LENSES)
                + "]"
            )
        # An empty resolved set (lenses present but all unknown) falls back to the
        # default four rather than disabling the panel silently (RUS-56 OQ3).
        lenses = known if known else list(DEFAULT_DESIGN_LENSES)

    framing_cap = len(DEFAULT_DESIGN_FRAMINGS)
    candidates = 1
    c = cfg.get("candidates")
    if isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) and c > 1:
        requested = int(math.floor(c))
        candidates = min(requested, framing_cap)
        if requested > framing_cap:
            warnings.append(
                f"clamping design-critic candidates {requested} -> {framing_cap} "
                f"(max framings: [{', '.join(DEFAULT_DESIGN_FRAMINGS)}])"
            )

    # --- RUS-77 cost-lever gates (all default OFF / absent) -----------------
    # digest: nested {enabled} block, default {"enabled": False}. Only an explicit
    # boolean flips it (same uniform vocabulary as every other enabled flag).
    digest_cfg = cfg.get("digest") if isinstance(cfg.get("digest"), dict) else {}
    digest = {"enabled": resolve_enabled(digest_cfg, False)}

    result = {
        "enabled": enabled,
        "maxRounds": max_rounds,
        "lenses": lenses,
        "candidates": candidates,
        "digest": digest,
    }

    # lensModel: optional model-name override. The key is OMITTED entirely (not None)
    # unless config supplies a non-empty string, so the default resolution is
    # byte-identical to the pre-RUS-77 shape plus the two nested gate blocks.
    lens_model = cfg.get("lensModel")
    if isinstance(lens_model, str) and lens_model.strip():
        result["lensModel"] = lens_model

    return result


def resolve_implementation(cfg):
    """Resolve the implementation-critic phase. Default OFF (the opt-in seam, RUS-58).

    Returns {coherence: {enabled, maxRounds}}. The per-slice edge critic was retired
    (RUS-88), so the top-level `enabled`/`maxRounds` (which gated ONLY that per-slice
    loop) are gone; only the nested coherence block (the whole-stack pass, default OFF)
    survives."""
    cfg = cfg if isinstance(cfg, dict) else {}
    coh = cfg.get("coherence") if isinstance(cfg.get("coherence"), dict) else {}
    return {
        "coherence": {
            "enabled": resolve_enabled(coh, False),
            "maxRounds": _pos_int_or(coh.get("maxRounds"), DEFAULT_MAX_ROUNDS),
        },
    }


def resolve_critics(critics):
    """Pure resolver: a parsed `critics` object (or anything) -> (phases, warnings).

    `critics` that is not a dict (absent block, "", null, junk) resolves every phase to
    its defaults. No I/O — argument-driven so the _test.py sibling exercises it with
    in-memory dicts."""
    warnings = []
    c = critics if isinstance(critics, dict) else {}
    phases = {
        "design": resolve_design(c.get("design"), warnings),
        "implementation": resolve_implementation(c.get("implementation")),
    }
    return phases, warnings


def default_phases():
    """The all-defaults resolution (no critics block) — used for the fail-safe envelope."""
    phases, _ = resolve_critics({})
    return phases


def main():
    argparse.ArgumentParser(
        description="Resolve the .qrspi/config.json `critics` block for all phases as JSON."
    ).parse_args()
    try:
        config = read_config(REPO_ROOT)
        critics = config.get("critics") if isinstance(config, dict) else None
        phases, warnings = resolve_critics(critics)
        print(json.dumps({"ok": True, "phases": phases, "warnings": warnings}))
        return 0
    except Exception as exc:  # noqa: BLE001 — surface any unexpected error verbatim
        print(json.dumps({"ok": False, "phases": default_phases(), "warnings": [], "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
