#!/usr/bin/env python3
"""Deterministic shared-digest generator for research.md (RUS-77, AC-COST).

Why this exists
---------------
Today the design-critic panel passes the FULL research.md by path to every lens,
and each lens Reads it itself (Q1). With the default four-lens panel run over
maxRounds rounds, the same ~36KB research.md is re-read 4× per round — the measured
cost driver this ticket's primary cost lever targets (design.md Decision 3, primary
lever). This CLI builds ONE deterministic trimmed digest of research.md before the
fan-out; the JS wiring passes its path to all lenses (DIGEST_PATH) so each reads the
smaller digest instead of the full research.

Extraction policy (deterministic, no LLM)
----------------------------------------
This policy is **content-reducing, not section-dropping**, and is re-derived from
research.md's ACTUAL structure (see .qrspi/templates/research.md and any real
research.md): its top-level sections are `## Q1`…`## Q<n>` plus `## Discovered
Patterns` and `## Inconsistencies`. The earlier whitelist idea (`## Current State` /
`## Desired End State` / `## Delta`) named DESIGN/STRUCTURE template headers that
never appear in research.md, so it would have matched nothing.

So the policy KEEPS every real top-level section header and every prose line (the
`**Answer:**`, `**Dependencies:**`, `**Implicit contracts:**` lines, the
Discovered-Patterns / Inconsistencies prose) and STRIPS only the fenced ``` code
blocks — the verbose **Evidence** code fences (up to a 20-line fence per Q per the
template) that account for the bulk of the bytes. The reduction is a simple line
scan: drop every line from a fence-opening ``` to its matching closing ``` (the
delimiters and their contents); keep all other lines verbatim, in document order.
Deterministic ⇒ byte-identical across runs on the same input.

Fail-closed
-----------
If the input research file is empty/whitespace-only, OR the digest after stripping
is empty/whitespace-only (e.g. a research file that is ALL fenced code), write
nothing and exit non-zero. The JS call site also guards with `test -s <out>`
before fan-out, so an empty digest never reaches a lens.

Usage:
    python3 scripts/qrspi_research_digest.py --research <path> --out <path>
"""

import argparse
import sys


# --- pure helpers (unit-tested) --------------------------------------------

def strip_fences(text):
    """Return ``text`` with all fenced code blocks removed.

    A fence is delimited by a line whose stripped content starts with ``` (three
    backticks). The opening fence line, every line inside the fence, and the
    closing fence line are all dropped; all other lines are kept verbatim and in
    document order. An unterminated fence (opened but never closed) drops the rest
    of the document — fail toward less content, never echoing raw evidence. Pure:
    a deterministic string→string transform with no I/O. Returns the joined
    surviving lines (no trailing newline is added)."""
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            # Toggle: a fence delimiter line is itself dropped on both open & close.
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append(line)
    return "\n".join(out)


def build_digest(research_text):
    """Build the digest string from raw research.md ``research_text``.

    Returns ``(digest, error)`` where ``error`` is None on success. Fail-closed:
    an empty/whitespace-only input OR an empty/whitespace-only result after
    fence-stripping returns ``(None, <message>)`` so the caller writes nothing and
    exits non-zero. Pure (no I/O)."""
    if not research_text or not research_text.strip():
        return None, "research input is empty or whitespace-only"
    digest = strip_fences(research_text)
    if not digest.strip():
        return None, "digest is empty after stripping fenced code blocks"
    # Preserve a single trailing newline so the digest is a well-formed text file.
    return digest + "\n", None


# --- entrypoint ------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a deterministic trimmed digest of research.md "
                    "(strips fenced code blocks, keeps headers + prose)")
    parser.add_argument("--research", required=True,
                        help="Absolute path to research.md (input)")
    parser.add_argument("--out", required=True,
                        help="Absolute path to write the digest to (output)")
    args = parser.parse_args(argv)

    try:
        with open(args.research) as fh:
            research_text = fh.read()
    except OSError as exc:
        sys.stderr.write("research input not found or unreadable: %s\n" % exc)
        return 1

    digest, error = build_digest(research_text)
    if error is not None:
        sys.stderr.write("%s\n" % error)
        return 1

    try:
        with open(args.out, "w") as fh:
            fh.write(digest)
    except OSError as exc:
        sys.stderr.write("digest output not writable: %s\n" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
