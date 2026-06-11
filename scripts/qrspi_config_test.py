#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_config.py — run with `python3`.

Covers the pure selector (select_value) with in-memory dicts and the best-effort
reader (read_config) against a tempfile dir. Never touches the real repo config
(ref: structure §Slice 1 AC5, Q12)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrspi_config import read_config, select_value  # noqa: E402


class SelectValueTests(unittest.TestCase):
    def test_key_present_and_truthy_returns_value(self):
        self.assertEqual(
            select_value({"linearProject": "Acme"}, "linearProject", "QRSPI"),
            "Acme",
        )

    def test_key_absent_returns_default(self):
        self.assertEqual(
            select_value({}, "linearProject", "QRSPI"),
            "QRSPI",
        )

    def test_key_present_but_empty_returns_default(self):
        self.assertEqual(
            select_value({"linearProject": ""}, "linearProject", "QRSPI"),
            "QRSPI",
        )

    def test_key_present_but_none_returns_default(self):
        self.assertEqual(
            select_value({"linearProject": None}, "linearProject", "QRSPI"),
            "QRSPI",
        )


class ReadConfigTests(unittest.TestCase):
    def _write_config(self, root: Path, payload):
        qrspi_dir = root / ".qrspi"
        qrspi_dir.mkdir(parents=True, exist_ok=True)
        (qrspi_dir / "config.json").write_text(payload)

    def test_present_file_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, json.dumps({"linearProject": "Acme"}))
            self.assertEqual(read_config(root), {"linearProject": "Acme"})

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_config(Path(tmp)), {})

    def test_malformed_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, "{ this is not valid json ")
            self.assertEqual(read_config(root), {})

    def test_non_dict_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, json.dumps(["not", "a", "dict"]))
            self.assertEqual(read_config(root), {})

    def test_default_applied_when_key_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, json.dumps({"linearTeam": "T"}))
            self.assertEqual(
                select_value(read_config(root), "linearProject", "QRSPI"),
                "QRSPI",
            )

    def test_value_echoed_when_key_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, json.dumps({"linearProject": "Acme"}))
            self.assertEqual(
                select_value(read_config(root), "linearProject", "QRSPI"),
                "Acme",
            )


if __name__ == "__main__":
    unittest.main()
