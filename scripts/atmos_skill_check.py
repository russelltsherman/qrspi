#!/usr/bin/env python3
"""Mechanical acceptance checker for the atmos skill directory.

Verifies the three checkable acceptance criteria for a skill directory before
(and after) any human-authored content exists:

1. Frontmatter shape -- the leading ``---``-fenced block of ``SKILL.md`` carries
   the in-repo five-field schema (``name, description, command, argument-hint,
   allowed-tools``); the agentskills.io core fields ``name`` and ``description``
   are non-empty; and frontmatter ``name`` equals the skill directory name.
2. Body budget -- the body (everything after the frontmatter) is under 500 lines
   (exact) and within an approximate ~5000-token guard.
3. Reference presence -- all five ``references/*.md`` files exist and are
   non-empty: ``stack-yaml-schema.md, vendoring.md, workflows.md,
   cli-reference.md, troubleshooting.md``.

Stdlib-only. CLI: ``python3 scripts/atmos_skill_check.py <skill_dir>`` exits 0
when there are no violations, 1 otherwise (printing each violation).
"""

import re
import sys
from pathlib import Path

# Type aliases (see structure.md Contracts).
Violation = str
Frontmatter = dict  # dict[str, str]

# The in-repo five-field frontmatter schema.
REQUIRED_FIELDS = ("name", "description", "command", "argument-hint", "allowed-tools")
# agentskills.io core fields that must additionally be non-empty.
CORE_NONEMPTY_FIELDS = ("name", "description")

# The five required reference docs.
REQUIRED_REFERENCES = (
    "stack-yaml-schema.md",
    "vendoring.md",
    "workflows.md",
    "cli-reference.md",
    "troubleshooting.md",
)

# Body budget guards.
MAX_BODY_LINES = 500  # exact line-count cap
MAX_BODY_TOKENS = 5000  # approximate token guard
# Rough token estimate: ~4 characters per token (stdlib-only approximation).
CHARS_PER_TOKEN = 4

_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*\r?\n?",
    re.DOTALL,
)


def parse_frontmatter(text: str) -> Frontmatter | None:
    """Extract the leading ``---``-fenced YAML-ish key/value block.

    Returns a ``dict[str, str]`` of the ``key: value`` lines inside the block,
    or ``None`` if ``text`` has no valid leading fenced block.
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None
    block = match.group("body")
    result: Frontmatter = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def _body_after_frontmatter(text: str) -> str:
    """Return the content after the leading frontmatter block (or all of it)."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return text
    return text[match.end():]


def check_skill(skill_dir: Path) -> list[Violation]:
    """Run all acceptance checks against a skill directory.

    Returns a list of human-readable violation messages; an empty list means the
    skill passes.
    """
    violations: list[Violation] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        violations.append("skill: missing 'SKILL.md'")
        # Without SKILL.md we cannot run frontmatter/body checks; still check refs.
        violations.extend(_check_references(skill_dir))
        return violations

    text = skill_md.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)

    if frontmatter is None:
        violations.append("frontmatter: missing or malformed '---'-fenced block")
    else:
        # (a) five-field schema present.
        for field in REQUIRED_FIELDS:
            if field not in frontmatter:
                violations.append(f"frontmatter: missing field '{field}'")
        # core fields non-empty.
        for field in CORE_NONEMPTY_FIELDS:
            if field in frontmatter and not frontmatter[field]:
                violations.append(f"frontmatter: field '{field}' is empty")
        # (b) name == directory name.
        name = frontmatter.get("name")
        if name is not None and name != skill_dir.name:
            violations.append(
                f"frontmatter: name '{name}' != skill dir '{skill_dir.name}'"
            )

    # (c) body line/token budget.
    body = _body_after_frontmatter(text)
    line_count = len(body.splitlines())
    if line_count >= MAX_BODY_LINES:
        violations.append(
            f"body: {line_count} lines exceeds limit of {MAX_BODY_LINES}"
        )
    approx_tokens = len(body) // CHARS_PER_TOKEN
    if approx_tokens > MAX_BODY_TOKENS:
        violations.append(
            f"body: ~{approx_tokens} tokens exceeds budget of ~{MAX_BODY_TOKENS}"
        )

    # (d) reference presence.
    violations.extend(_check_references(skill_dir))

    return violations


def _check_references(skill_dir: Path) -> list[Violation]:
    """Check that all five references/*.md files exist and are non-empty."""
    violations: list[Violation] = []
    refs_dir = skill_dir / "references"
    for ref in REQUIRED_REFERENCES:
        path = refs_dir / ref
        if not path.is_file():
            violations.append(f"references: missing '{ref}'")
        elif path.stat().st_size == 0:
            violations.append(f"references: '{ref}' is empty")
    return violations


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: atmos_skill_check.py <skill_dir>", file=sys.stderr)
        return 1
    skill_dir = Path(argv[1])
    violations = check_skill(skill_dir)
    for violation in violations:
        print(violation)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
