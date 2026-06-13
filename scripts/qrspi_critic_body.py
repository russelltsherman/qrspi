#!/usr/bin/env python3
"""Splice a critic panel's cap-reached residual findings INTO a design finalize commit
message, so Graphite seeds the design PR body with the unresolved-findings block (RUS-56).

Why this exists
---------------
When the design critic panel hits its round cap without converging (`next_action` returns
`cap_reached`), the residual findings must surface into the design PR so a human reviewer
sees what the panel could not get the design agent to fix (ref: structure §Contracts
`qrspi_critic_body.py`, Decision 4, Q9 Path A, AC4).

Like the implementation PR body (`qrspi_pr_body.py`), the ONLY non-interactive lever for a
Graphite PR description is the branch commit message Graphite reads at creation — `gt
submit` has no body flag. So this CLI reads a staged residual-findings file plus the
finalize commit message, formats the findings as a "Residual critic findings" body block,
and splices it between the commit subject and its trailers via the LANDED, pure
`compose_message` (reused from qrspi_pr_body.py, never re-implemented).

This script does NOT touch git: it reads two inputs and emits the spliced message to
stdout. The caller (the design finalize step in qrspi-batch.js) feeds the result to its
commit-amend path. Keeping it git-free makes the splice fully unit-testable.

Empty-findings short-circuit: when the residual-findings file is empty / whitespace-only /
absent, the original commit message is emitted UNCHANGED (idempotent no-op) — the common
case where the panel converged and there are no residuals to surface (ref: Decision 4).

Inputs:
  --findings-file PATH   staged residual-findings file (one finding per line, or a JSON
                         findings list). Empty / missing ⇒ no-op.
  --message-file PATH    the finalize commit message. Omit to read the message from stdin.

Output: the (possibly unchanged) commit message on stdout.
"""

import argparse
import json
import os
import sys

# Sibling import of the landed pure splice helper. Self-locating sys.path insert so the
# import resolves regardless of caller cwd (matches qrspi_critic_synthesize.py).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from qrspi_pr_body import compose_message  # noqa: E402


# --- pure helpers (unit-tested) --------------------------------------------

def parse_findings(raw):
    """Parse a staged residual-findings file's contents into a list of finding strings.

    Accepts either:
      - a JSON array (e.g. `synthesize`'s `findings`, whose elements are bare strings or
        `{text, lens}` dicts) — each element is normalized to its display text; or
      - plain text, one finding per non-blank line.

    Returns a list of stripped, non-empty finding strings (empty list for empty/blank
    input). Pure; never raises.
    """
    if not isinstance(raw, str) or not raw.strip():
        return []

    stripped = raw.strip()
    # JSON array first (the natural serialization of synthesize's findings).
    if stripped.startswith("["):
        try:
            arr = json.loads(stripped)
        except (ValueError, TypeError):
            arr = None
        if isinstance(arr, list):
            out = []
            for item in arr:
                if isinstance(item, dict):
                    text = item.get("text")
                    lens = item.get("lens")
                    text = text if isinstance(text, str) else (
                        "" if text is None else str(text))
                    text = text.strip()
                    if not text:
                        continue
                    if isinstance(lens, str) and lens.strip():
                        out.append("%s (%s)" % (text, lens.strip()))
                    else:
                        out.append(text)
                elif isinstance(item, str):
                    if item.strip():
                        out.append(item.strip())
                elif item is not None:
                    out.append(str(item).strip())
            return out

    # Fall back to plain text, one finding per non-blank line.
    return [ln.strip() for ln in stripped.splitlines() if ln.strip()]


def format_body(findings):
    """Format a residual-findings list into the PR body block. Pure.

    Returns "" for an empty list (signals the no-op short-circuit upstream). Otherwise a
    titled, bulleted block ready to splice as the commit body.
    """
    if not findings:
        return ""
    lines = ["## Residual critic findings",
             "",
             "The design critic panel reached its round cap without converging. The "
             "following findings remain unresolved and should be reviewed:",
             ""]
    lines += ["- %s" % f for f in findings]
    return "\n".join(lines)


def splice(message, raw_findings):
    """Splice the residual-findings body into `message`, or return `message` unchanged
    when there are no findings. Pure — the unit-testable core.

    Idempotent re-splice safety is provided by `compose_message`, which re-authors the
    body between the subject and the trailer block (an already-spliced message yields the
    same output when re-spliced with the same findings).
    """
    findings = parse_findings(raw_findings)
    body = format_body(findings)
    if not body:
        # No residuals: preserve the original message byte-for-byte (no-op).
        return message
    return compose_message(message, body)


# --- IO wrapper (not unit-tested; manual) ----------------------------------

def _read_optional(path):
    """Read a file's contents, returning "" if the path is None or absent."""
    if not path or not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    parser = argparse.ArgumentParser(
        description="Splice critic residual findings into a design finalize commit message")
    parser.add_argument("--findings-file", default=None,
                        help="Staged residual-findings file (JSON array or one-per-line). "
                             "Empty/absent ⇒ message emitted unchanged.")
    parser.add_argument("--message-file", default=None,
                        help="Finalize commit message file. Omit to read from stdin.")
    args = parser.parse_args()

    if args.message_file:
        message = _read_optional(args.message_file)
    else:
        message = sys.stdin.read()

    raw_findings = _read_optional(args.findings_file)

    sys.stdout.write(splice(message, raw_findings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
