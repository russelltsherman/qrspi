#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_research_digest.py.
Run: python3 scripts/qrspi_research_digest_test.py"""

import os
import subprocess
import sys
import tempfile
import unittest

import qrspi_research_digest as d

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "qrspi_research_digest.py")

# A fixture shaped like the REAL research template: ## Q<n> sections with an
# **Answer:** prose line and a fenced ``` Evidence block, plus ## Discovered
# Patterns and ## Inconsistencies sections.
RESEARCH_FIXTURE = """# Research — Codebase Map

## Q1: How does the panel pass research today?

**Answer:** Each lens receives file PATHS, not content.

**Evidence:**

```js
const verdict = await agent(`RESEARCH_PATH = ${researchPath}`)
```

**Dependencies:** runCriticPanelLoop ← doDesign.

## Q2: Where is the model selected?

**Answer:** NOT FOUND in the orchestration layer.

**Evidence:**

```bash
$ grep -nc "model" qrspi-batch.js   # 4
```

**Implicit contracts:** agent options are {label, phase, agentType, schema}.

## Discovered Patterns

- Functional Core / Imperative Shell is load-bearing.

## Inconsistencies

- Eval harness is a documented placeholder.
"""


class StripFencesTest(unittest.TestCase):
    def test_drops_fence_contents_and_delimiters(self):
        text = "keep1\n```js\ndropped\n```\nkeep2"
        self.assertEqual(d.strip_fences(text), "keep1\nkeep2")

    def test_keeps_all_non_fence_lines(self):
        text = "## Q1\n**Answer:** x\n## Q2"
        self.assertEqual(d.strip_fences(text), "## Q1\n**Answer:** x\n## Q2")

    def test_indented_fence_delimiter_recognized(self):
        text = "keep\n   ```\n  dropped\n   ```\nkeep2"
        self.assertEqual(d.strip_fences(text), "keep\nkeep2")

    def test_unterminated_fence_drops_remainder(self):
        text = "keep\n```\ntail\nmore"
        self.assertEqual(d.strip_fences(text), "keep")


class BuildDigestTest(unittest.TestCase):
    def test_retains_headers_and_prose(self):
        digest, error = d.build_digest(RESEARCH_FIXTURE)
        self.assertIsNone(error)
        # Every real top-level section header is retained.
        self.assertIn("## Q1:", digest)
        self.assertIn("## Q2:", digest)
        self.assertIn("## Discovered Patterns", digest)
        self.assertIn("## Inconsistencies", digest)
        # Prose lines are retained.
        self.assertIn("**Answer:** Each lens receives file PATHS", digest)
        self.assertIn("**Dependencies:**", digest)
        self.assertIn("**Implicit contracts:**", digest)

    def test_strips_all_fenced_evidence(self):
        digest, error = d.build_digest(RESEARCH_FIXTURE)
        self.assertIsNone(error)
        # NONE of the fenced code-block contents survive.
        self.assertNotIn("const verdict = await agent", digest)
        self.assertNotIn('grep -nc "model"', digest)
        self.assertNotIn("```", digest)

    def test_digest_strictly_shorter(self):
        digest, error = d.build_digest(RESEARCH_FIXTURE)
        self.assertIsNone(error)
        self.assertLess(len(digest), len(RESEARCH_FIXTURE))

    def test_deterministic_across_runs(self):
        a, _ = d.build_digest(RESEARCH_FIXTURE)
        b, _ = d.build_digest(RESEARCH_FIXTURE)
        self.assertEqual(a, b)

    def test_empty_input_fail_closed(self):
        digest, error = d.build_digest("")
        self.assertIsNone(digest)
        self.assertIsNotNone(error)
        digest, error = d.build_digest("   \n  \n")
        self.assertIsNone(digest)
        self.assertIsNotNone(error)

    def test_all_fenced_input_fail_closed(self):
        # A research file that is ALL fenced code → empty after stripping → fail.
        text = "```\nonly code here\nmore code\n```\n"
        digest, error = d.build_digest(text)
        self.assertIsNone(digest)
        self.assertIsNotNone(error)


class CliTest(unittest.TestCase):
    def _run(self, research_text):
        """Run the CLI on research_text; return (returncode, digest_or_None)."""
        with tempfile.TemporaryDirectory() as tmp:
            research = os.path.join(tmp, "research.md")
            out = os.path.join(tmp, "digest.md")
            with open(research, "w") as fh:
                fh.write(research_text)
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--research", research, "--out", out],
                capture_output=True, text=True)
            digest = None
            if os.path.exists(out):
                with open(out) as fh:
                    digest = fh.read()
            return proc.returncode, digest

    def test_cli_writes_digest_exit_zero(self):
        rc, digest = self._run(RESEARCH_FIXTURE)
        self.assertEqual(rc, 0)
        self.assertIsNotNone(digest)
        self.assertIn("## Q1:", digest)
        self.assertNotIn("```", digest)

    def test_cli_empty_input_exit_nonzero_no_output(self):
        rc, digest = self._run("   \n")
        self.assertNotEqual(rc, 0)
        # No (or empty) output file was written.
        self.assertIn(digest, (None, ""))

    def test_cli_all_fenced_exit_nonzero(self):
        rc, digest = self._run("```\ncode\n```\n")
        self.assertNotEqual(rc, 0)
        self.assertIn(digest, (None, ""))

    def test_cli_missing_research_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "digest.md")
            proc = subprocess.run(
                [sys.executable, SCRIPT,
                 "--research", os.path.join(tmp, "nope.md"), "--out", out],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
