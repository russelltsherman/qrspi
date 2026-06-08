#!/usr/bin/env python3
"""Unit tests for qrspi_revise_amend.py pure helpers — stdlib only, run with python3.

The verification gate (`verify_amend`) is the regression guard for the RUS-53 bug: a
revise worker edited design.md, amended with an empty index, pushed an unchanged commit,
and reported success. These tests pin the predicate that now turns that silent no-op into
a hard failure.
"""

import unittest

import qrspi_revise_amend as m


class WorktreePathTest(unittest.TestCase):
    def test_canonical_layout(self):
        self.assertEqual(
            m.worktree_path("/repo", "RUS-53"),
            "/repo/.worktrees/RUS-53",
        )


class IsCachePathTest(unittest.TestCase):
    def test_pyc_is_cache(self):
        self.assertTrue(m.is_cache_path("scripts/foo.pyc"))

    def test_pycache_dir_is_cache(self):
        self.assertTrue(m.is_cache_path("scripts/__pycache__/foo.cpython-311.pyc"))
        self.assertTrue(m.is_cache_path("__pycache__/bar.pyc"))

    def test_source_is_not_cache(self):
        self.assertFalse(m.is_cache_path(".qrspi/RUS-53/design.md"))
        self.assertFalse(m.is_cache_path("scripts/qrspi_pr_state.py"))

    def test_empty_is_not_cache(self):
        self.assertFalse(m.is_cache_path(""))
        self.assertFalse(m.is_cache_path(None))


class DirtyPathsTest(unittest.TestCase):
    def test_empty_clean(self):
        self.assertEqual(m.dirty_paths(""), [])
        self.assertEqual(m.dirty_paths(None), [])

    def test_modified_artifact_is_dirty(self):
        # This is the RUS-53 shape: design.md left modified after a no-op amend.
        out = " M .qrspi/RUS-53/design.md\n"
        self.assertEqual(m.dirty_paths(out), [".qrspi/RUS-53/design.md"])

    def test_untracked_code_is_dirty(self):
        out = "?? scripts/new_module.py\n"
        self.assertEqual(m.dirty_paths(out), ["scripts/new_module.py"])

    def test_caches_are_filtered_out(self):
        out = (
            " M .qrspi/RUS-53/design.md\n"
            "?? scripts/__pycache__/x.cpython-311.pyc\n"
            " M scripts/foo.pyc\n"
        )
        # Only the real edit remains; caches never count as dirty.
        self.assertEqual(m.dirty_paths(out), [".qrspi/RUS-53/design.md"])

    def test_only_caches_reads_clean(self):
        out = "?? scripts/__pycache__/x.pyc\n"
        self.assertEqual(m.dirty_paths(out), [])

    def test_rename_keeps_destination_path(self):
        out = "R  old/name.py -> new/name.py\n"
        self.assertEqual(m.dirty_paths(out), ["new/name.py"])

    def test_quoted_path_is_unquoted(self):
        out = ' M "path with space.md"\n'
        self.assertEqual(m.dirty_paths(out), ["path with space.md"])


class ClassifyModifyTest(unittest.TestCase):
    def test_success(self):
        self.assertEqual(m.classify_modify(0, "ok", ""), (True, None))

    def test_failure_prefers_stderr(self):
        ok, err = m.classify_modify(1, "stdout noise", "boom")
        self.assertFalse(ok)
        self.assertEqual(err, "boom")

    def test_failure_falls_back_to_stdout(self):
        ok, err = m.classify_modify(1, "stdout detail", "")
        self.assertFalse(ok)
        self.assertEqual(err, "stdout detail")

    def test_failure_generic_when_silent(self):
        ok, err = m.classify_modify(2, "", "")
        self.assertFalse(ok)
        self.assertIn("rc=2", err)


class VerifyAmendTest(unittest.TestCase):
    """The regression guard for the RUS-53 silent-no-op bug. Gated on (staged, dirty) —
    NOT on commit-OID equality, because `git commit --amend` bumps the committer timestamp
    and changes the OID on every amend even when the tree is byte-identical."""

    def test_staged_and_clean_succeeds(self):
        ok, err = m.verify_amend(True, [])
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_nothing_staged_fails(self):
        # The exact RUS-53 failure: the edited file was left unstaged, so the index was
        # empty at amend time and the commit captured nothing.
        ok, err = m.verify_amend(False, [])
        self.assertFalse(ok)
        self.assertIn("no staged changes", err)

    def test_dirty_after_amend_fails(self):
        # Staging missed a file that is still in the working tree post-amend.
        ok, err = m.verify_amend(True, [".qrspi/RUS-53/design.md"])
        self.assertFalse(ok)
        self.assertIn("still dirty", err)
        self.assertIn("design.md", err)

    def test_nothing_staged_takes_precedence(self):
        ok, err = m.verify_amend(False, ["x.py"])
        self.assertFalse(ok)
        self.assertIn("no staged changes", err)


class BuildEnvelopeTest(unittest.TestCase):
    def test_success_envelope_shape(self):
        env = m.build_envelope("RUS-53", "RUS-53/design", "/repo/.worktrees/RUS-53",
                               ok=True, old_oid="a", new_oid="b", dirty=[],
                               repo_root="/repo")
        self.assertEqual(env, {
            "ok": True,
            "repoRoot": "/repo",
            "ticket": "RUS-53",
            "branch": "RUS-53/design",
            "worktreeDir": "/repo/.worktrees/RUS-53",
            "oldOid": "a",
            "newOid": "b",
            "dirty": [],
        })

    def test_error_envelope_includes_error(self):
        env = m.build_envelope("RUS-53", "RUS-53/design", "/wt", ok=False,
                               dirty=["design.md"], error="boom", repo_root="/repo")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"], "boom")
        self.assertEqual(env["dirty"], ["design.md"])


if __name__ == "__main__":
    unittest.main()
