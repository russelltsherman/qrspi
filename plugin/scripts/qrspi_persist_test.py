#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_persist.py. Run: python3 scripts/qrspi_persist_test.py"""

import os
import tempfile
import unittest

import qrspi_persist as qp


class StagingPathTest(unittest.TestCase):
    def test_token_free_construction(self):
        p = qp.staging_path("/tmp/phase-stage", "RUS-21", "plan")
        self.assertEqual(p, "/tmp/phase-stage/RUS-21/plan.md")
        # The staging path must NOT carry the qrspi token the model corrupts.
        self.assertNotIn("qrspi", p)

    def test_honours_custom_stage_root(self):
        p = qp.staging_path("/var/stg", "RUS-9", "structure")
        self.assertEqual(p, "/var/stg/RUS-9/structure.md")


class DestPathTest(unittest.TestCase):
    def test_canonical_worktree_layout(self):
        d = qp.dest_path("/repo", "RUS-21", "plan")
        self.assertEqual(d, "/repo/.worktrees/RUS-21/.qrspi/RUS-21/plan.md")

    def test_each_artifact_maps_to_its_own_file(self):
        for name in qp.ARTIFACTS:
            d = qp.dest_path("/repo", "RUS-7", name)
            self.assertTrue(d.endswith("/.qrspi/RUS-7/%s.md" % name))

    def test_dest_follows_host_checkout_not_engine_dir(self):
        # RUS-60 divergence: when the engine lives at a DIFFERENT path than the host
        # checkout, dest_path must follow the host checkout root the resolver returns
        # (passed in as `repo_root`), never the engine dir. Prove the two diverge by
        # passing a synthetic host root distinct from the engine's own dir.
        engine_dir = os.path.dirname(os.path.abspath(qp.__file__))
        host_root = "/synthetic/host-checkout"
        self.assertNotEqual(host_root, os.path.dirname(engine_dir))
        d = qp.dest_path(host_root, "RUS-60", "structure")
        self.assertEqual(d, "/synthetic/host-checkout/.worktrees/RUS-60/.qrspi/RUS-60/structure.md")
        # The dest must be rooted at the host checkout, NOT under the engine dir.
        self.assertTrue(d.startswith(host_root + os.sep))
        self.assertFalse(d.startswith(engine_dir + os.sep))


class PersistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _stage(self, ticket, artifact, content):
        src = qp.staging_path(os.path.join(self.root, "stage"), ticket, artifact)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as fh:
            fh.write(content)
        return src

    def test_moves_non_empty_file_and_reports_bytes(self):
        src = self._stage("RUS-21", "plan", "# Plan\n\n16 steps\n")
        dest = qp.dest_path(self.root, "RUS-21", "plan")
        n, err = qp.persist(src, dest)
        self.assertIsNone(err)
        self.assertGreater(n, 0)
        self.assertTrue(os.path.isfile(dest))
        with open(dest) as fh:
            self.assertEqual(fh.read(), "# Plan\n\n16 steps\n")
        # move() consumes the staging copy
        self.assertFalse(os.path.exists(src))

    def test_creates_missing_destination_dirs(self):
        src = self._stage("RUS-9", "structure", "x")
        dest = qp.dest_path(self.root, "RUS-9", "structure")
        self.assertFalse(os.path.isdir(os.path.dirname(dest)))
        _, err = qp.persist(src, dest)
        self.assertIsNone(err)
        self.assertTrue(os.path.isfile(dest))

    def test_missing_source_is_reported_not_raised(self):
        src = qp.staging_path(os.path.join(self.root, "stage"), "RUS-1", "plan")
        dest = qp.dest_path(self.root, "RUS-1", "plan")
        n, err = qp.persist(src, dest)
        self.assertEqual(n, 0)
        self.assertIsNotNone(err)
        self.assertIn("not found", err)
        self.assertFalse(os.path.exists(dest))

    def test_empty_source_is_rejected(self):
        src = self._stage("RUS-2", "design", "")
        dest = qp.dest_path(self.root, "RUS-2", "design")
        n, err = qp.persist(src, dest)
        self.assertEqual(n, 0)
        self.assertIsNotNone(err)
        self.assertIn("empty", err)
        # A rejected empty artifact must not create a bogus non-empty destination.
        self.assertFalse(os.path.isfile(dest))


if __name__ == "__main__":
    unittest.main()
