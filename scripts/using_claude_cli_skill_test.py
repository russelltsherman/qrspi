#!/usr/bin/env python3
"""Structure-validation test for the using-claude-cli skill.

Stdlib-only, assert-based (no pytest dependency) to match the repo's script
conventions (mirrors scripts/qrspi_*_test.py). Run with:
    python3 scripts/using_claude_cli_skill_test.py
Exits 0 if all checks pass, 1 on the first failure.

Slice 1 scope: assert the SKILL.md frontmatter parses as YAML with exactly the
five expected keys, the body is non-empty, and the body line count is <= 500.
Reference-existence assertions (references/*.md) are added in Slice 2.
"""

import os
import sys

# Self-locate the repo root from this file's path so the test runs from any cwd.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
SKILL_PATH = os.path.join(
    REPO_ROOT, ".claude", "skills", "using-claude-cli", "SKILL.md"
)

EXPECTED_KEYS = {
    "name",
    "description",
    "command",
    "argument-hint",
    "allowed-tools",
}
MAX_BODY_LINES = 500


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

    return body_lines


def main():
    body_lines = validate_skill_structure()
    print("OK: using-claude-cli SKILL.md")
    print("  frontmatter keys: exactly %d expected keys" % len(EXPECTED_KEYS))
    print("  body: non-empty, %d lines (<= %d)" % (body_lines, MAX_BODY_LINES))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        sys.exit(1)
