#!/usr/bin/env python3
"""Resolve a single .qrspi/config.json key (default-aware) and print a JSON envelope.

Why this exists
---------------
The qrspi-batch Query phase needs to scope its Linear `list_issues` sweep to the
repo's mapped project (`linearProject`, default "QRSPI") rather than sweeping every
project. Reading config.json from JS is awkward and path-sensitive; this self-locating,
stdlib-only helper does it deterministically — the JS side runs
`python3 scripts/qrspi_config.py --key linearProject` verbatim and parses the one line
of JSON it prints to stdout.

Like qrspi_resolve.py / qrspi_persist.py, it computes the repo root from its own
location (`__file__` two levels up), so the caller types only the invocation.

Output: a single JSON envelope on stdout:
    { "ok": true, "key": "<name>", "value": <str|null> }       (exit 0)
    { "ok": false, "key": "<name>", "value": null, "error": "<verbatim>" }  (exit !=0)
"""

import argparse
import json
import sys
from pathlib import Path

# The script lives at <repo-root>/scripts/qrspi_config.py, so the repo root is two
# levels up. Deriving it from __file__ (not cwd, not an argument) removes a
# path-sensitive caller step, mirroring qrspi_resolve.py / qrspi_persist.py.
REPO_ROOT = Path(__file__).resolve().parents[1]

# Per-key defaults. `linearProject` falls back to "QRSPI" (the repo's mapped project,
# ref: design §Delta, Q2/Q9). Unknown keys default to the empty string.
DEFAULTS = {"linearProject": "QRSPI"}


def select_value(config: dict, key: str, default: str) -> str:
    """Pure selector: return config[key] when present and truthy, else default.

    No I/O — argument-driven so the _test.py sibling can exercise it with in-memory
    dicts (ref: structure Contracts, Decision 3, Q12)."""
    value = config.get(key)
    return value if value else default


def read_config(repo_root: Path) -> dict:
    """Best-effort read of <repo_root>/.qrspi/config.json -> parsed dict.

    Returns {} on any OSError/ValueError; never raises. Modeled on
    qrspi_resolve.py._read_reviewer_config() (ref: design §Delta, Q3, Q9)."""
    path = Path(repo_root) / ".qrspi" / "config.json"
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Resolve a .qrspi/config.json key (default-aware) as JSON."
    )
    parser.add_argument("--key", required=True, help="config.json key to resolve")
    args = parser.parse_args()

    key = args.key
    default = DEFAULTS.get(key, "")
    try:
        config = read_config(REPO_ROOT)
        value = select_value(config, key, default)
        print(json.dumps({"ok": True, "key": key, "value": value}))
        return 0
    except Exception as exc:  # noqa: BLE001 — surface any unexpected error verbatim
        print(json.dumps({"ok": False, "key": key, "value": None, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
