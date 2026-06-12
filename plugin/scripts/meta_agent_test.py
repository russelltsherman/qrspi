#!/usr/bin/env python3
"""Unit tests for meta_agent.py — stdlib only, run with python3.

    python3 scripts/meta_agent_test.py

Slice 1 scope (plan §1.4, structure §Slice 1 Verification): the subprocess seam
(`_run_cli`) is mocked, and we assert (a) a normal call returns the model text and
(b) a subprocess/non-zero-exit failure returns the NO_RESULT sentinel without
raising out of `complete`. The pure helpers (`build_command`, `extract_text`) are
also covered directly so the contract is pinned independent of the subprocess.
"""

import unittest

import meta_agent as m


class BuildCommandTest(unittest.TestCase):
    def test_headless_print_mode(self):
        cmd = m.build_command("sys", "usr")
        # Must be a headless `claude -p` text invocation.
        self.assertEqual(cmd[0], "claude")
        self.assertIn("-p", cmd)
        self.assertIn("--output-format", cmd)
        self.assertEqual(cmd[cmd.index("--output-format") + 1], "text")

    def test_system_and_user_are_passed(self):
        cmd = m.build_command("the-system", "the-user")
        # System prompt goes behind --append-system-prompt; user is the positional.
        self.assertIn("--append-system-prompt", cmd)
        self.assertEqual(cmd[cmd.index("--append-system-prompt") + 1], "the-system")
        self.assertEqual(cmd[-1], "the-user")

    def test_model_omitted_by_default(self):
        self.assertNotIn("--model", m.build_command("s", "u"))

    def test_model_spliced_when_given(self):
        cmd = m.build_command("s", "u", model="some-model")
        self.assertIn("--model", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "some-model")

    def test_none_prompts_become_empty_strings(self):
        cmd = m.build_command(None, None)
        self.assertEqual(cmd[cmd.index("--append-system-prompt") + 1], "")
        self.assertEqual(cmd[-1], "")


class ExtractTextTest(unittest.TestCase):
    def test_success_returns_text(self):
        text, ok = m.extract_text(0, '{"category": "x"}\n', "")
        self.assertTrue(ok)
        self.assertEqual(text, '{"category": "x"}')

    def test_only_one_trailing_newline_stripped(self):
        text, ok = m.extract_text(0, "line1\nline2\n", "")
        self.assertTrue(ok)
        self.assertEqual(text, "line1\nline2")

    def test_nonzero_exit_is_sentinel(self):
        text, ok = m.extract_text(1, "ignored stdout", "boom")
        self.assertFalse(ok)
        self.assertEqual(text, m.NO_RESULT)

    def test_blank_stdout_is_sentinel(self):
        text, ok = m.extract_text(0, "   \n", "")
        self.assertFalse(ok)
        self.assertEqual(text, m.NO_RESULT)

    def test_none_stdout_is_sentinel(self):
        text, ok = m.extract_text(0, None, "")
        self.assertFalse(ok)
        self.assertEqual(text, m.NO_RESULT)


class CompleteTest(unittest.TestCase):
    """`complete` with the subprocess seam (`_run_cli`) mocked."""

    def setUp(self):
        self._orig = m._run_cli
        self.addCleanup(self._restore)

    def _restore(self):
        m._run_cli = self._orig

    def test_normal_call_returns_model_text(self):
        # (a) a normal call returns the raw model text.
        captured = {}

        def fake(cmd):
            captured["cmd"] = cmd
            return 0, '{"category": "ambiguous", "rationale": "quoted evidence"}\n', ""

        m._run_cli = fake
        out = m.complete("system prompt", "user prompt")
        self.assertEqual(out, '{"category": "ambiguous", "rationale": "quoted evidence"}')
        # The seam built a real claude headless command from the prompts.
        self.assertEqual(captured["cmd"][0], "claude")
        self.assertIn("-p", captured["cmd"])

    def test_subprocess_failure_returns_sentinel_no_raise(self):
        # (b) a subprocess/non-zero exit returns the sentinel and does NOT raise.
        m._run_cli = lambda cmd: (2, "", "model invocation failed")
        out = m.complete("s", "u")
        self.assertEqual(out, m.NO_RESULT)

    def test_missing_binary_returns_sentinel(self):
        # The real _run_cli maps FileNotFoundError -> rc 127; emulate that result
        # to prove complete() degrades rather than crashing the loop.
        m._run_cli = lambda cmd: (127, "", "claude CLI not found on PATH")
        self.assertEqual(m.complete("s", "u"), m.NO_RESULT)

    def test_blank_output_returns_sentinel(self):
        m._run_cli = lambda cmd: (0, "\n", "")
        self.assertEqual(m.complete("s", "u"), m.NO_RESULT)

    def test_run_cli_never_raises_on_missing_binary(self):
        # Exercise the REAL _run_cli against a guaranteed-missing binary to prove the
        # OS-error catch works end to end (no mock): it must return a non-zero rc,
        # not raise, so complete() can degrade to the sentinel.
        orig_bin = m._CLI_BIN
        m._CLI_BIN = "definitely-not-a-real-binary-xyzzy"
        try:
            rc, out, err = m._run_cli(m.build_command("s", "u"))
        finally:
            m._CLI_BIN = orig_bin
        self.assertNotEqual(rc, 0)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
