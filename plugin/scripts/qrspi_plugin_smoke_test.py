#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_plugin_smoke.py.

Asserts the two contractual cases (ref: structure New Types — ${CLAUDE_PLUGIN_ROOT} /
engine_root() fallback, fail-loud on missing bundled script; plan Slice 4 step 20):
  - success: with the bundled layout intact under a synthetic plugin root, the smoke
    check resolves every required script and main() exits 0.
  - fail-loud: a referenced bundled script absent → MissingBundledScript and main()
    exits non-zero.
  - plugin_root() precedence: ${CLAUDE_PLUGIN_ROOT} wins; engine_root()-parent fallback
    when the env var is unset.

Run: python3 scripts/qrspi_plugin_smoke_test.py
"""

import os
import tempfile
import unittest

import qrspi_plugin_smoke as smoke
from qrspi_plugin_smoke import MissingBundledScript


def _make_plugin_tree(scripts):
    """Create a temp dir shaped like a plugin root holding ``scripts/<name>`` for each name.

    Returns the temp dir path (caller cleans up via the TemporaryDirectory context).
    """
    root = tempfile.mkdtemp()
    scripts_dir = os.path.join(root, "scripts")
    os.makedirs(scripts_dir)
    for name in scripts:
        with open(os.path.join(scripts_dir, name), "w") as fh:
            fh.write("# stub bundled script\n")
    return root


class ResolveBundledScriptTest(unittest.TestCase):
    def test_resolves_existing_script(self):
        root = _make_plugin_tree(["qrspi_paths.py"])
        try:
            got = smoke.resolve_bundled_script("qrspi_paths.py", root=root)
            self.assertEqual(got, os.path.join(root, "scripts", "qrspi_paths.py"))
        finally:
            _rmtree(root)

    def test_missing_script_fails_loud(self):
        root = _make_plugin_tree([])  # empty scripts/ dir
        try:
            with self.assertRaises(MissingBundledScript):
                smoke.resolve_bundled_script("qrspi_paths.py", root=root)
        finally:
            _rmtree(root)


class RunSmokeTest(unittest.TestCase):
    def test_intact_layout_resolves_all(self):
        root = _make_plugin_tree(smoke.REQUIRED_BUNDLED_SCRIPTS)
        try:
            resolved = smoke.run_smoke(root=root)
            self.assertEqual(len(resolved), len(smoke.REQUIRED_BUNDLED_SCRIPTS))
            for path in resolved:
                self.assertTrue(os.path.isfile(path))
        finally:
            _rmtree(root)

    def test_partial_layout_fails_loud(self):
        # All but one required script present → must fail loud on the missing one.
        present = list(smoke.REQUIRED_BUNDLED_SCRIPTS)[:-1]
        root = _make_plugin_tree(present)
        try:
            with self.assertRaises(MissingBundledScript):
                smoke.run_smoke(root=root)
        finally:
            _rmtree(root)


class MainExitCodeTest(unittest.TestCase):
    def test_success_exits_zero(self):
        root = _make_plugin_tree(smoke.REQUIRED_BUNDLED_SCRIPTS)
        try:
            os.environ["CLAUDE_PLUGIN_ROOT"] = root
            self.assertEqual(smoke.main([]), 0)
        finally:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
            _rmtree(root)

    def test_missing_exits_nonzero(self):
        root = _make_plugin_tree([])  # nothing bundled
        try:
            os.environ["CLAUDE_PLUGIN_ROOT"] = root
            self.assertNotEqual(smoke.main([]), 0)
        finally:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
            _rmtree(root)


class PluginRootPrecedenceTest(unittest.TestCase):
    def test_env_var_wins(self):
        try:
            os.environ["CLAUDE_PLUGIN_ROOT"] = "/synthetic/plugin-root"
            self.assertEqual(smoke.plugin_root(), os.path.abspath("/synthetic/plugin-root"))
        finally:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)

    def test_fallback_is_engine_root_parent(self):
        # Unset env var → fall back to the parent of engine_root() (i.e. plugin/).
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        import qrspi_paths
        self.assertEqual(smoke.plugin_root(), os.path.dirname(qrspi_paths.engine_root()))


def _rmtree(path):
    # Minimal recursive cleanup (stdlib shutil avoided to keep parity, but it's stdlib too).
    import shutil
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
