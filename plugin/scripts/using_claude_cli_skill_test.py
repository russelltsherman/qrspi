#!/usr/bin/env python3
"""Structure-validation test for the using-claude-cli skill.

Stdlib-only, assert-based (no pytest dependency) to match the repo's script
conventions (mirrors scripts/qrspi_*_test.py). Run with:
    python3 scripts/using_claude_cli_skill_test.py
Exits 0 if all checks pass, 1 on the first failure.

Slice 1 scope: assert the SKILL.md frontmatter parses as YAML with exactly the
five expected keys, the body is non-empty, and the body line count is <= 500.

Slice 2 scope (added): assert the four references/*.md depth docs exist and are
non-empty, and that every references/ link in the SKILL.md body resolves to a
file that actually exists (no dangling links).
"""

import os
import re
import sys

# Self-locate the repo root from this file's path so the test runs from any cwd.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
SKILL_DIR = os.path.join(REPO_ROOT, ".claude", "skills", "using-claude-cli")
SKILL_PATH = os.path.join(SKILL_DIR, "SKILL.md")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

EXPECTED_KEYS = {
    "name",
    "description",
    "command",
    "argument-hint",
    "allowed-tools",
}
MAX_BODY_LINES = 500

# The four advanced-topic depth docs the SKILL.md body links out to. Slice 2
# creates these; the contract is that the body's references/ links resolve to
# exactly this set (no missing, no dangling).
EXPECTED_REFERENCES = {
    "advanced-cli-flags.md",
    "hook-examples.md",
    "agent-team-orchestration.md",
    "permission-rule-patterns.md",
}

# Matches a Markdown link target pointing into the references/ directory, e.g.
# `[text](references/advanced-cli-flags.md)`. Captures the bare filename.
_REF_LINK_RE = re.compile(r"\]\(\s*references/([^)\s#]+)")


def split_frontmatter(text):
    """Return (frontmatter_str, body_str) for a `---`-delimited YAML header.

    Raises AssertionError if the file does not open with a `---` fence and have
    a matching closing `---`.
    """
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", (
        "SKILL.md must begin with a '---' frontmatter fence"
    )
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    assert end is not None, "SKILL.md frontmatter has no closing '---' fence"
    fm = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:])
    return fm, body


def parse_frontmatter_keys(fm):
    """Parse top-level `key: value` pairs from a simple YAML frontmatter block.

    The skill frontmatter is a flat scalar map (no nesting), so a stdlib
    line-based parse is sufficient and avoids a PyYAML dependency. Returns the
    set of top-level keys.
    """
    keys = set()
    for raw in fm.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        # Top-level keys are unindented "key: value" lines.
        assert not line.startswith((" ", "\t")), (
            "frontmatter must be a flat (non-nested) key map; "
            "found indented line: %r" % raw
        )
        assert ":" in line, "frontmatter line is not 'key: value': %r" % raw
        key = line.split(":", 1)[0].strip()
        assert key, "frontmatter line has an empty key: %r" % raw
        assert key not in keys, "duplicate frontmatter key: %r" % key
        keys.add(key)
    return keys


def _nonempty_file(path):
    """True if path is a file with non-whitespace content."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as fh:
        return bool(fh.read().strip())


def validate_references(body):
    """Assert the references/ depth docs exist and the body links resolve.

    Two halves of the same contract:
      1. Each expected references/*.md file exists and is non-empty.
      2. Every references/ link in the SKILL.md body points at a file that
         actually exists (no dangling links).

    Returns the sorted list of referenced filenames found in the body.
    """
    # 1. Each expected reference file exists and is non-empty.
    for name in sorted(EXPECTED_REFERENCES):
        path = os.path.join(REFERENCES_DIR, name)
        assert os.path.isfile(path), (
            "expected reference file missing: references/%s" % name
        )
        assert _nonempty_file(path), (
            "reference file is empty: references/%s" % name
        )

    # 2. Every references/ link in the body resolves to a real file.
    linked = sorted(set(_REF_LINK_RE.findall(body)))
    assert linked, (
        "SKILL.md body has no references/ links; expected links to %s"
        % sorted(EXPECTED_REFERENCES)
    )
    for name in linked:
        path = os.path.join(REFERENCES_DIR, name)
        assert os.path.isfile(path) and _nonempty_file(path), (
            "dangling references/ link in SKILL.md: references/%s "
            "does not resolve to a non-empty file" % name
        )

    return linked


def validate_skill_structure():
    assert os.path.isfile(SKILL_PATH), "SKILL.md not found at %s" % SKILL_PATH
    with open(SKILL_PATH, "r", encoding="utf-8") as fh:
        text = fh.read()

    fm, body = split_frontmatter(text)

    keys = parse_frontmatter_keys(fm)
    assert keys == EXPECTED_KEYS, (
        "frontmatter keys mismatch.\n  expected: %s\n  found:    %s"
        % (sorted(EXPECTED_KEYS), sorted(keys))
    )

    assert body.strip(), "SKILL.md body is empty"

    body_lines = len(body.splitlines())
    assert body_lines <= MAX_BODY_LINES, (
        "SKILL.md body is %d lines; must be <= %d"
        % (body_lines, MAX_BODY_LINES)
    )

    linked = validate_references(body)

    return body_lines, linked


def main():
    body_lines, linked = validate_skill_structure()
    print("OK: using-claude-cli SKILL.md")
    print("  frontmatter keys: exactly %d expected keys" % len(EXPECTED_KEYS))
    print("  body: non-empty, %d lines (<= %d)" % (body_lines, MAX_BODY_LINES))
    print(
        "  references: %d expected files present & non-empty; "
        "%d body link(s) resolve"
        % (len(EXPECTED_REFERENCES), len(linked))
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        sys.exit(1)
