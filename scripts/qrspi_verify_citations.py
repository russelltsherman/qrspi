#!/usr/bin/env python3
"""AC2 deterministic citation node-check for QRSPI research.md.

Why this exists
---------------
The research phase produces a research.md packed with codebase citations of the
form `file:line` / `file:start-end` / bare-file backtick spans. A citation that
points at a line number BEYOND the cited file's actual length is a provably broken
pointer -- it can never resolve no matter how the reader looks. This script is the
deterministic gate that catches exactly that case (AC2): the staged research.md is
parsed, every literal citation token is resolved against an EXPLICITLY-SUPPLIED
worktree root, and any token whose file exists but whose cited line/range is out of
bounds is reported verbatim. A non-`ok` result fails the research phase before the
artifact is ever persisted.

Two deliberate non-failures (design Decision 4 / OQ3 RESOLVED=tolerated):

- A citation to a file that does NOT exist under the worktree root is *tolerated*
  (a forward reference -- the file may be created by a later slice), NOT reported.
- Glob/placeholder tokens containing `*`, `<`, or `>` are excluded at parse time --
  they are illustrative, not concrete pointers.

Self-location boundary (Decision 3 Option A)
--------------------------------------------
`resolve_repo_root()` self-locates from `__file__` ONLY so this module can import its
siblings (`qrspi_paths`). It is NEVER used to resolve a citation -- citations resolve
against the `--worktree-root` the caller supplies. Conflating the two is the explicit
Risk-Register med/high item this design guards against, and the test sibling asserts
resolution happens against a tempdir root, never the repo root.

Output: a single-line JSON envelope on stdout:
    { "ok": bool, "unresolved": [<verbatim tokens>], "error"?: str }
ok is false when `unresolved` is non-empty or on any I/O error. Exit 0 on ok else 1.
"""

import argparse
import json
import os
import re
import sys

# ENGINE_ROOT: the dir holding this engine's scripts/ (from __file__) -- used ONLY for
# sibling imports, NEVER to resolve a citation. Citations resolve against the supplied
# --worktree-root (Decision 3 Option A; Risk Register med/high).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)


def resolve_repo_root():
    """Self-locate the engine root from __file__. Used ONLY for this module's own
    imports -- never to resolve a citation (Decision 3 Option A). Kept as a thin,
    explicit boundary so the test sibling can assert citation resolution never calls
    it."""
    return ENGINE_ROOT


# Tokens that are illustrative placeholders rather than concrete pointers
# (Decision 4 Option A). Any citation containing one of these is excluded at parse.
_PLACEHOLDER_CHARS = ("*", "<", ">")

# A backtick-delimited span. We only inspect the inside of `...` spans, since QRSPI
# citations are always written inside backticks.
_BACKTICK_SPAN = re.compile(r"`([^`]+)`")

# A concrete citation inside a backtick span: a path (no whitespace) optionally
# followed by `:line` or `:start-end`. The path segment forbids whitespace and
# backticks; the optional line spec is digits or digits-dash-digits.
_CITATION = re.compile(r"^(?P<file>[^\s`:]+):(?P<line>\d+(?:-\d+)?)$")

# A bare-file citation: a backtick span that is just a path with a slash or a dotted
# extension and no whitespace -- e.g. `scripts/qrspi_persist.py`. We require either a
# path separator or a dotted filename so prose words in backticks (`ok`, `runPhase`)
# are not mistaken for file citations.
_BARE_FILE = re.compile(r"^(?P<file>[^\s`:]+)$")


def _looks_like_path(text):
    """True when a bare backtick span looks like a file path (has a `/` or a dotted
    extension), not a prose code-word. Keeps `runPhase` / `ok` from being treated as
    file citations while admitting `scripts/x.py` and `config.json`."""
    if "/" in text:
        return True
    # dotted extension: something.ext where ext is 1+ word chars
    return bool(re.search(r"\.[A-Za-z0-9]+$", text))


def parse_citations(text):
    """Extract literal citation tokens from backtick-delimited spans in `text`.

    Recognizes `file:line`, `file:start-end`, and bare-file (`path/to/file`) forms.
    Excludes any token containing `*`, `<`, or `>` (glob/placeholder, Decision 4).
    Returns verbatim tokens (no normalization), in order of appearance. Pure."""
    tokens = []
    for span in _BACKTICK_SPAN.findall(text):
        inner = span.strip()
        if not inner:
            continue
        if any(c in inner for c in _PLACEHOLDER_CHARS):
            continue
        m = _CITATION.match(inner)
        if m:
            tokens.append(inner)
            continue
        b = _BARE_FILE.match(inner)
        if b and _looks_like_path(inner):
            tokens.append(inner)
    return tokens


def _split_token(token):
    """Split a citation token into (file, start, end). start/end are 1-based ints, or
    None for a bare-file token. A single `file:line` yields start==end. Pure."""
    m = _CITATION.match(token)
    if not m:
        return token, None, None
    line = m.group("line")
    if "-" in line:
        a, b = line.split("-", 1)
        return m.group("file"), int(a), int(b)
    n = int(line)
    return m.group("file"), n, n


def _count_lines(path):
    """Number of lines in the file at `path`. A file with no trailing newline still
    counts its last line; an empty file counts 0. Reads bytes to stay encoding-robust."""
    count = 0
    with open(path, "rb") as fh:
        last = b""
        for chunk in iter(lambda: fh.read(65536), b""):
            count += chunk.count(b"\n")
            last = chunk[-1:]
    # A non-empty file whose final byte is not a newline has one more (unterminated) line.
    if last not in (b"", b"\n"):
        count += 1
    return count


def resolve_citation(token, worktree_root):
    """Return True when `token` resolves, False ONLY when it provably does not.

    Resolves (True) when:
      - the cited file is ABSENT under worktree_root (tolerated forward reference, OQ3), OR
      - the file exists and the cited line/range is within the file's line count, OR
      - the token is a bare-file citation and the file exists.
    Does NOT resolve (False) only when the file exists AND the cited line/range is out
    of bounds (the AC2 hard-fail case).

    Paths are joined against `worktree_root` ONLY -- never resolve_repo_root()
    (Decision 3; Risk Register med/high). Pure w.r.t. its inputs (touches only the FS
    under worktree_root)."""
    file_part, start, end = _split_token(token)
    full = os.path.join(worktree_root, file_part)
    if not os.path.isfile(full):
        # Absent file => tolerated forward reference.
        return True
    if start is None:
        # Bare-file citation to an existing file => resolves.
        return True
    total = _count_lines(full)
    # The cited range is in bounds when its highest line is <= the file's line count and
    # its lowest line is >= 1.
    lo = min(start, end)
    hi = max(start, end)
    return lo >= 1 and hi <= total


def verify(artifact_path, worktree_root):
    """Parse `artifact_path`, resolve every citation against `worktree_root`, and return
    a CitationCheckEnvelope dict. On any I/O error, returns ok:false with a verbatim
    `error`. Pure w.r.t. the filesystem it reads."""
    try:
        with open(artifact_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return {"ok": False, "unresolved": [], "error": str(exc)}

    unresolved = [t for t in parse_citations(text)
                  if not resolve_citation(t, worktree_root)]
    return {"ok": len(unresolved) == 0, "unresolved": unresolved}


def main():
    parser = argparse.ArgumentParser(
        description="Verify research.md citations resolve against a worktree root "
                    "(AC2 deterministic node-check).")
    parser.add_argument("--artifact-path", required=True,
                        help="Path to the staged research.md to check.")
    parser.add_argument("--worktree-root", required=True,
                        help="Worktree root that citations are resolved against "
                             "(NEVER the engine/repo root).")
    args = parser.parse_args()

    env = verify(args.artifact_path, args.worktree_root)
    json.dump(env, sys.stdout)
    print()
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
