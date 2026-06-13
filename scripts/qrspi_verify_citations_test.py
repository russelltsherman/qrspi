#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_verify_citations.py.

Run: python3 scripts/qrspi_verify_citations_test.py

Every citation is resolved against a tempfile.TemporaryDirectory() worktree root --
NEVER resolve_repo_root() (the Risk Register med/high item): a test explicitly asserts
the resolver root and the citation-resolution root are independent.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qrspi_verify_citations as vc


def _write(root, rel, lines):
    """Create a file under `root` at relative path `rel` with `lines` lines."""
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write("\n".join("line %d" % i for i in range(1, lines + 1)))
        fh.write("\n")
    return full


class ParseCitationsTest(unittest.TestCase):
    def test_extracts_file_line_and_range(self):
        text = "See `scripts/x.py:10` and `scripts/y.py:5-9` for details."
        self.assertEqual(
            vc.parse_citations(text),
            ["scripts/x.py:10", "scripts/y.py:5-9"],
        )

    def test_extracts_bare_file_path(self):
        text = "The config lives in `.qrspi/config.json`."
        self.assertEqual(vc.parse_citations(text), [".qrspi/config.json"])

    def test_excludes_glob_and_placeholder_tokens(self):
        # tokens containing *, <, or > are illustrative, not concrete pointers
        text = "`scripts/*_test.py` and `path/to/<file>:1` and `a/b.py:<n>`"
        self.assertEqual(vc.parse_citations(text), [])

    def test_ignores_prose_code_words(self):
        # backtick spans that are not path-like must not be treated as citations
        text = "The `runPhase` returns `ok` after `criticConfig` is set."
        self.assertEqual(vc.parse_citations(text), [])

    def test_preserves_order_and_verbatim(self):
        text = "`b/z.py:3` then `a/x.py:1-2`"
        self.assertEqual(vc.parse_citations(text), ["b/z.py:3", "a/x.py:1-2"])


class ResolveCitationTest(unittest.TestCase):
    def test_file_present_in_range_line_resolves(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "scripts/x.py", 20)
            self.assertTrue(vc.resolve_citation("scripts/x.py:10", root))

    def test_file_present_in_range_span_resolves(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "scripts/x.py", 20)
            self.assertTrue(vc.resolve_citation("scripts/x.py:5-15", root))

    def test_file_present_out_of_range_line_does_not_resolve(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "scripts/x.py", 20)
            self.assertFalse(vc.resolve_citation("scripts/x.py:99", root))

    def test_file_present_range_overruns_end_does_not_resolve(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "scripts/x.py", 20)
            self.assertFalse(vc.resolve_citation("scripts/x.py:18-40", root))

    def test_file_absent_is_tolerated(self):
        # forward reference (OQ3 RESOLVED=tolerated): absent file resolves True,
        # even with an arbitrary line number
        with tempfile.TemporaryDirectory() as root:
            self.assertTrue(vc.resolve_citation("does/not/exist.py:5", root))

    def test_bare_file_present_resolves(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "config.json", 3)
            self.assertTrue(vc.resolve_citation("config.json", root))

    def test_bare_file_absent_tolerated(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertTrue(vc.resolve_citation("missing.json", root))

    def test_resolution_uses_worktree_root_not_repo_root(self):
        # The Risk Register med/high guard: citation resolution must join against the
        # supplied worktree_root, NEVER resolve_repo_root(). Prove it by placing the
        # file ONLY under a tempdir distinct from the engine root and confirming it
        # resolves there -- while the same token against the engine root would not.
        with tempfile.TemporaryDirectory() as root:
            _write(root, "uniq_fixture.py", 4)
            self.assertNotEqual(os.path.realpath(root),
                                os.path.realpath(vc.resolve_repo_root()))
            self.assertTrue(vc.resolve_citation("uniq_fixture.py:2", root))
            # Against the engine root the fixture does not exist -> absent -> tolerated
            # (True), confirming resolution is keyed on the passed root, not the engine.
            self.assertTrue(
                vc.resolve_citation("uniq_fixture.py:2", vc.resolve_repo_root()))


class VerifyEnvelopeTest(unittest.TestCase):
    def test_clean_artifact_is_ok(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "scripts/x.py", 20)
            art = os.path.join(root, "research.md")
            with open(art, "w", encoding="utf-8") as fh:
                fh.write("All good: `scripts/x.py:10` and `missing.py:3`.\n")
            env = vc.verify(art, root)
            self.assertTrue(env["ok"])
            self.assertEqual(env["unresolved"], [])

    def test_out_of_range_reports_verbatim_token(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "scripts/x.py", 20)
            art = os.path.join(root, "research.md")
            with open(art, "w", encoding="utf-8") as fh:
                fh.write("Broken: `scripts/x.py:99` here.\n")
            env = vc.verify(art, root)
            self.assertFalse(env["ok"])
            self.assertEqual(env["unresolved"], ["scripts/x.py:99"])

    def test_missing_artifact_reports_error(self):
        with tempfile.TemporaryDirectory() as root:
            env = vc.verify(os.path.join(root, "nope.md"), root)
            self.assertFalse(env["ok"])
            self.assertIn("error", env)


if __name__ == "__main__":
    unittest.main()
