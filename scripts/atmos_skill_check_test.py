#!/usr/bin/env python3
"""Stdlib-only unit tests for atmos_skill_check.

Exercises parse_frontmatter and every check_skill branch (pass case plus each
failure mode) using tempfile fixtures. Run with: python3 scripts/atmos_skill_check_test.py
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import atmos_skill_check as checker

SCRIPT = Path(__file__).resolve().parent / "atmos_skill_check.py"


def _frontmatter(name: str = "atmos") -> str:
    return (
        "---\n"
        f"name: {name}\n"
        "description: Work with atmos stacks.\n"
        "command: /atmos\n"
        "argument-hint: <stack>\n"
        "allowed-tools: Bash, Read\n"
        "---\n"
    )


def _write_well_formed(skill_dir: Path, *, name: str = "atmos", body: str = "# Atmos\n\nDocs.\n") -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_frontmatter(name) + body, encoding="utf-8")
    refs = skill_dir / "references"
    refs.mkdir(exist_ok=True)
    for ref in checker.REQUIRED_REFERENCES:
        (refs / ref).write_text("content\n", encoding="utf-8")


class ParseFrontmatterTest(unittest.TestCase):
    def test_parses_leading_block(self) -> None:
        fm = checker.parse_frontmatter(_frontmatter() + "# Body\n")
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "atmos")
        self.assertEqual(fm["description"], "Work with atmos stacks.")
        self.assertEqual(fm["allowed-tools"], "Bash, Read")

    def test_none_when_no_leading_fence(self) -> None:
        self.assertIsNone(checker.parse_frontmatter("# Just a heading\n\ntext\n"))

    def test_none_when_fence_not_at_start(self) -> None:
        self.assertIsNone(checker.parse_frontmatter("preamble\n---\nname: x\n---\n"))


class CheckSkillTest(unittest.TestCase):
    def _tmp(self) -> Path:
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        return Path(self._td.name)

    def test_well_formed_passes(self) -> None:
        skill = self._tmp() / "atmos"
        _write_well_formed(skill)
        self.assertEqual(checker.check_skill(skill), [])

    def test_missing_skill_md(self) -> None:
        skill = self._tmp() / "atmos"
        skill.mkdir()
        violations = checker.check_skill(skill)
        self.assertTrue(any("missing 'SKILL.md'" in v for v in violations))

    def test_missing_frontmatter_field(self) -> None:
        skill = self._tmp() / "atmos"
        skill.mkdir(parents=True)
        fm = (
            "---\n"
            "name: atmos\n"
            "description: d\n"
            "command: /atmos\n"
            "argument-hint: <stack>\n"
            "---\n"  # allowed-tools omitted
        )
        (skill / "SKILL.md").write_text(fm + "# Body\n", encoding="utf-8")
        refs = skill / "references"
        refs.mkdir()
        for ref in checker.REQUIRED_REFERENCES:
            (refs / ref).write_text("x\n", encoding="utf-8")
        violations = checker.check_skill(skill)
        self.assertTrue(any("missing field 'allowed-tools'" in v for v in violations))

    def test_empty_core_field(self) -> None:
        skill = self._tmp() / "atmos"
        skill.mkdir(parents=True)
        fm = (
            "---\n"
            "name: atmos\n"
            "description:\n"
            "command: /atmos\n"
            "argument-hint: <stack>\n"
            "allowed-tools: Bash\n"
            "---\n"
        )
        (skill / "SKILL.md").write_text(fm + "# Body\n", encoding="utf-8")
        refs = skill / "references"
        refs.mkdir()
        for ref in checker.REQUIRED_REFERENCES:
            (refs / ref).write_text("x\n", encoding="utf-8")
        violations = checker.check_skill(skill)
        self.assertTrue(any("'description' is empty" in v for v in violations))

    def test_name_mismatch(self) -> None:
        skill = self._tmp() / "atmos"
        _write_well_formed(skill, name="wrong-name")
        violations = checker.check_skill(skill)
        self.assertTrue(any("!= skill dir 'atmos'" in v for v in violations))

    def test_no_frontmatter_block(self) -> None:
        skill = self._tmp() / "atmos"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# No frontmatter\n", encoding="utf-8")
        refs = skill / "references"
        refs.mkdir()
        for ref in checker.REQUIRED_REFERENCES:
            (refs / ref).write_text("x\n", encoding="utf-8")
        violations = checker.check_skill(skill)
        self.assertTrue(any("malformed '---'-fenced block" in v for v in violations))

    def test_over_budget_body_lines(self) -> None:
        skill = self._tmp() / "atmos"
        big_body = "\n".join(f"line {i}" for i in range(checker.MAX_BODY_LINES + 10)) + "\n"
        _write_well_formed(skill, body=big_body)
        violations = checker.check_skill(skill)
        self.assertTrue(any("exceeds limit of 500" in v for v in violations))

    def test_over_budget_body_tokens(self) -> None:
        skill = self._tmp() / "atmos"
        # Few lines but large char count to trip the token guard, not the line cap.
        huge_line = "x" * (checker.MAX_BODY_TOKENS * checker.CHARS_PER_TOKEN + 100)
        _write_well_formed(skill, body=huge_line + "\n")
        violations = checker.check_skill(skill)
        self.assertTrue(any("tokens exceeds budget" in v for v in violations))
        self.assertFalse(any("exceeds limit of 500" in v for v in violations))

    def test_missing_reference(self) -> None:
        skill = self._tmp() / "atmos"
        _write_well_formed(skill)
        (skill / "references" / "vendoring.md").unlink()
        violations = checker.check_skill(skill)
        self.assertTrue(any("missing 'vendoring.md'" in v for v in violations))

    def test_empty_reference(self) -> None:
        skill = self._tmp() / "atmos"
        _write_well_formed(skill)
        (skill / "references" / "workflows.md").write_text("", encoding="utf-8")
        violations = checker.check_skill(skill)
        self.assertTrue(any("'workflows.md' is empty" in v for v in violations))


class CliTest(unittest.TestCase):
    def _run(self, skill_dir: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(skill_dir)],
            capture_output=True, text=True,
        )

    def test_cli_exit_zero_on_well_formed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            skill = Path(td) / "atmos"
            _write_well_formed(skill)
            result = self._run(skill)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "")

    def test_cli_exit_one_on_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            skill = Path(td) / "atmos"
            _write_well_formed(skill, name="wrong")
            result = self._run(skill)
            self.assertEqual(result.returncode, 1)
            self.assertIn("!= skill dir", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
