#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_critics_config.py — run with `python3`.

Covers the pure per-phase resolvers (enabled vocabulary, maxRounds, design lenses +
candidates, implementation coherence nesting) and the top-level resolve_critics
aggregation with in-memory dicts. Never touches the real repo config."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrspi_critics_config import (  # noqa: E402
    DEFAULT_DESIGN_LENSES,
    DEFAULT_DESIGN_FRAMINGS,
    DEFAULT_MAX_ROUNDS,
    default_phases,
    resolve_critics,
    resolve_design,
    resolve_edge_phase,
    resolve_enabled,
    resolve_implementation,
)


class ResolveEnabledTests(unittest.TestCase):
    """The uniform `enabled` vocabulary: explicit bool wins, else the phase default."""

    def test_explicit_true(self):
        self.assertTrue(resolve_enabled({"enabled": True}, False))

    def test_explicit_false(self):
        self.assertFalse(resolve_enabled({"enabled": False}, True))

    def test_absent_uses_default_true(self):
        self.assertTrue(resolve_enabled({}, True))

    def test_absent_uses_default_false(self):
        self.assertFalse(resolve_enabled({}, False))

    def test_non_bool_truthy_falls_back_to_default(self):
        # A truthy non-bool (e.g. 1, "yes") must NOT coerce to True — it falls to default.
        self.assertFalse(resolve_enabled({"enabled": 1}, False))
        self.assertTrue(resolve_enabled({"enabled": "yes"}, True))

    def test_non_bool_falsy_falls_back_to_default(self):
        # 0 / "" / null are not boolean False — they fall to the default, not off.
        self.assertTrue(resolve_enabled({"enabled": 0}, True))
        self.assertTrue(resolve_enabled({"enabled": None}, True))

    def test_non_dict_uses_default(self):
        self.assertTrue(resolve_enabled(None, True))
        self.assertFalse(resolve_enabled("nope", False))


class ResolveEdgePhaseTests(unittest.TestCase):
    """questions/research/structure/plan — default ON, bare {enabled, maxRounds}."""

    def test_defaults_when_absent(self):
        self.assertEqual(
            resolve_edge_phase(None),
            {"enabled": False, "maxRounds": DEFAULT_MAX_ROUNDS},
        )

    def test_enabled_true_honored(self):
        self.assertEqual(
            resolve_edge_phase({"enabled": True}),
            {"enabled": True, "maxRounds": DEFAULT_MAX_ROUNDS},
        )

    def test_enabled_false_honored(self):
        self.assertEqual(
            resolve_edge_phase({"enabled": False}),
            {"enabled": False, "maxRounds": DEFAULT_MAX_ROUNDS},
        )

    def test_max_rounds_positive_int_honored(self):
        self.assertEqual(resolve_edge_phase({"maxRounds": 5})["maxRounds"], 5)

    def test_max_rounds_zero_falls_back(self):
        self.assertEqual(resolve_edge_phase({"maxRounds": 0})["maxRounds"], DEFAULT_MAX_ROUNDS)

    def test_max_rounds_negative_falls_back(self):
        self.assertEqual(resolve_edge_phase({"maxRounds": -3})["maxRounds"], DEFAULT_MAX_ROUNDS)

    def test_max_rounds_bool_falls_back(self):
        # True is an int subclass but must not read as maxRounds 1.
        self.assertEqual(resolve_edge_phase({"maxRounds": True})["maxRounds"], DEFAULT_MAX_ROUNDS)

    def test_max_rounds_non_int_falls_back(self):
        self.assertEqual(resolve_edge_phase({"maxRounds": 2.5})["maxRounds"], DEFAULT_MAX_ROUNDS)
        self.assertEqual(resolve_edge_phase({"maxRounds": "3"})["maxRounds"], DEFAULT_MAX_ROUNDS)


class ResolveDesignTests(unittest.TestCase):
    def _resolve(self, cfg):
        warnings = []
        return resolve_design(cfg, warnings), warnings

    def test_defaults(self):
        out, warnings = self._resolve(None)
        self.assertEqual(
            out,
            {
                "enabled": False,
                "maxRounds": DEFAULT_MAX_ROUNDS,
                "lenses": DEFAULT_DESIGN_LENSES,
                "candidates": 1,
                # RUS-77 cost-lever gates all default OFF/absent.
                "digest": {"enabled": False},
                "gateBehindEdge": {"enabled": False},
            },
        )
        # lensModel key is OMITTED entirely (absent, not None) by default.
        self.assertNotIn("lensModel", out)
        self.assertEqual(warnings, [])

    def test_enabled_true_honored(self):
        out, _ = self._resolve({"enabled": True})
        self.assertTrue(out["enabled"])

    def test_enabled_false_honored(self):
        out, _ = self._resolve({"enabled": False})
        self.assertFalse(out["enabled"])

    def test_known_lenses_subset_kept_in_order(self):
        out, warnings = self._resolve({"lenses": ["simplicity", "completeness"]})
        self.assertEqual(out["lenses"], ["simplicity", "completeness"])
        self.assertEqual(warnings, [])

    def test_unknown_lenses_dropped_with_warning(self):
        out, warnings = self._resolve({"lenses": ["completeness", "bogus"]})
        self.assertEqual(out["lenses"], ["completeness"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("bogus", warnings[0])

    def test_all_unknown_lenses_fall_back_to_default(self):
        out, warnings = self._resolve({"lenses": ["nope", "nada"]})
        self.assertEqual(out["lenses"], DEFAULT_DESIGN_LENSES)
        self.assertEqual(len(warnings), 1)

    def test_non_list_lenses_ignored(self):
        out, warnings = self._resolve({"lenses": "completeness"})
        self.assertEqual(out["lenses"], DEFAULT_DESIGN_LENSES)
        self.assertEqual(warnings, [])

    def test_candidates_le_one_is_off(self):
        self.assertEqual(self._resolve({"candidates": 1})[0]["candidates"], 1)
        self.assertEqual(self._resolve({"candidates": 0})[0]["candidates"], 1)

    def test_candidates_two_kept(self):
        self.assertEqual(self._resolve({"candidates": 2})[0]["candidates"], 2)

    def test_candidates_clamped_down_with_warning(self):
        cap = len(DEFAULT_DESIGN_FRAMINGS)
        out, warnings = self._resolve({"candidates": 99})
        self.assertEqual(out["candidates"], cap)
        self.assertEqual(len(warnings), 1)
        self.assertIn("clamping", warnings[0])

    def test_candidates_float_floored(self):
        self.assertEqual(self._resolve({"candidates": 2.9})[0]["candidates"], 2)

    def test_candidates_bool_ignored(self):
        self.assertEqual(self._resolve({"candidates": True})[0]["candidates"], 1)

    def test_candidates_non_finite_ignored(self):
        self.assertEqual(self._resolve({"candidates": math.inf})[0]["candidates"], 1)

    # --- RUS-77 cost-lever gates ------------------------------------------

    def test_digest_default_off(self):
        out, _ = self._resolve({})
        self.assertEqual(out["digest"], {"enabled": False})

    def test_digest_enabled_true_parses(self):
        out, _ = self._resolve({"digest": {"enabled": True}})
        self.assertEqual(out["digest"], {"enabled": True})

    def test_digest_non_dict_falls_back_off(self):
        # A non-dict digest value (junk/string/null) resolves to the default-OFF block.
        self.assertEqual(self._resolve({"digest": "yes"})[0]["digest"], {"enabled": False})
        self.assertEqual(self._resolve({"digest": True})[0]["digest"], {"enabled": False})

    def test_digest_non_bool_enabled_falls_back_off(self):
        # Uniform enabled vocabulary — a non-bool inner enabled falls to default OFF.
        self.assertEqual(self._resolve({"digest": {"enabled": 1}})[0]["digest"], {"enabled": False})

    def test_lens_model_absent_by_default(self):
        self.assertNotIn("lensModel", self._resolve({})[0])

    def test_lens_model_string_parses(self):
        out, _ = self._resolve({"lensModel": "claude-haiku"})
        self.assertEqual(out["lensModel"], "claude-haiku")

    def test_lens_model_empty_or_blank_omitted(self):
        # Empty/whitespace-only model strings leave the key absent (treated as unset).
        self.assertNotIn("lensModel", self._resolve({"lensModel": ""})[0])
        self.assertNotIn("lensModel", self._resolve({"lensModel": "   "})[0])

    def test_lens_model_non_string_omitted(self):
        self.assertNotIn("lensModel", self._resolve({"lensModel": 7})[0])
        self.assertNotIn("lensModel", self._resolve({"lensModel": True})[0])
        self.assertNotIn("lensModel", self._resolve({"lensModel": None})[0])

    def test_gate_behind_edge_default_off(self):
        out, _ = self._resolve({})
        self.assertEqual(out["gateBehindEdge"], {"enabled": False})

    def test_gate_behind_edge_enabled_true_parses(self):
        out, _ = self._resolve({"gateBehindEdge": {"enabled": True}})
        self.assertEqual(out["gateBehindEdge"], {"enabled": True})

    def test_gate_behind_edge_non_dict_falls_back_off(self):
        self.assertEqual(
            self._resolve({"gateBehindEdge": "yes"})[0]["gateBehindEdge"],
            {"enabled": False},
        )

    def test_all_three_levers_on_parse_together(self):
        out, warnings = self._resolve({
            "digest": {"enabled": True},
            "lensModel": "claude-haiku",
            "gateBehindEdge": {"enabled": True},
        })
        self.assertEqual(out["digest"], {"enabled": True})
        self.assertEqual(out["lensModel"], "claude-haiku")
        self.assertEqual(out["gateBehindEdge"], {"enabled": True})
        self.assertEqual(warnings, [])


class JsMirrorParityTests(unittest.TestCase):
    """Lockstep: the Python default resolution must equal the JS DEFAULT_CRITIC_PHASES
    mirror in .claude/workflows/qrspi-batch.js (structure.md Modified Types). The JS
    object is parsed out of the source file by regex (the file is harness-coupled and
    not importable), then compared field-for-field against default_phases()."""

    def _js_default_critic_phases(self):
        import json as _json
        import re

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        js_path = os.path.join(repo_root, ".claude", "workflows", "qrspi-batch.js")
        with open(js_path, "r", encoding="utf-8") as fh:
            src = fh.read()
        # Grab the object literal assigned to DEFAULT_CRITIC_PHASES.
        m = re.search(r"const DEFAULT_CRITIC_PHASES = (\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(m, "could not locate DEFAULT_CRITIC_PHASES in qrspi-batch.js")
        body = m.group(1)
        # Resolve the `lenses: DEFAULT_DESIGN_LENSES` reference to the literal array,
        # then strip JS-only constructs (the `// ...` comment lines) before JSON-parsing.
        body = body.replace("DEFAULT_DESIGN_LENSES", _json.dumps(DEFAULT_DESIGN_LENSES))
        body = re.sub(r"^\s*//.*$", "", body, flags=re.MULTILINE)
        # Quote bare object keys (identifier: -> "identifier":) and drop trailing commas.
        body = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', body)
        body = re.sub(r",(\s*[}\]])", r"\1", body)
        body = body.replace("false", "false").replace("true", "true")
        return _json.loads(body)

    def test_design_defaults_match_js_mirror(self):
        py = default_phases()["design"]
        js = self._js_default_critic_phases()["design"]
        self.assertEqual(py, js, "Python resolve_design defaults and JS DEFAULT_CRITIC_PHASES.design diverged")

    def test_all_phase_defaults_match_js_mirror(self):
        py = default_phases()
        js = self._js_default_critic_phases()
        self.assertEqual(set(py), set(js))
        for phase in py:
            self.assertEqual(py[phase], js[phase], f"phase {phase!r} default diverged between Python and JS mirror")


class ResolveImplementationTests(unittest.TestCase):
    def test_defaults_all_off(self):
        self.assertEqual(
            resolve_implementation(None),
            {
                "enabled": False,
                "maxRounds": DEFAULT_MAX_ROUNDS,
                "coherence": {"enabled": False, "maxRounds": DEFAULT_MAX_ROUNDS},
            },
        )

    def test_enabled_true_honored(self):
        self.assertTrue(resolve_implementation({"enabled": True})["enabled"])

    def test_coherence_enabled_true_honored(self):
        out = resolve_implementation({"coherence": {"enabled": True, "maxRounds": 4}})
        self.assertTrue(out["coherence"]["enabled"])
        self.assertEqual(out["coherence"]["maxRounds"], 4)

    def test_non_dict_coherence_falls_back(self):
        out = resolve_implementation({"coherence": "yes"})
        self.assertEqual(out["coherence"], {"enabled": False, "maxRounds": DEFAULT_MAX_ROUNDS})

    def test_top_level_max_rounds_honored(self):
        self.assertEqual(resolve_implementation({"maxRounds": 7})["maxRounds"], 7)


class ResolveCriticsTests(unittest.TestCase):
    """Top-level aggregation: every phase present, defaults preserve historical behavior."""

    def test_absent_block_all_defaults(self):
        for critics in (None, "", {}, [], 42):
            phases, warnings = resolve_critics(critics)
            self.assertEqual(set(phases), {
                "questions", "research", "design", "structure", "plan", "implementation",
            })
            self.assertEqual(warnings, [])
            # EVERY phase defaults OFF — critics are uniformly opt-in.
            for p in ("questions", "research", "design", "structure", "plan", "implementation"):
                self.assertFalse(phases[p]["enabled"], f"{p} should default disabled with critics={critics!r}")
            self.assertFalse(phases["implementation"]["coherence"]["enabled"])

    def test_default_phases_matches_empty_resolution(self):
        self.assertEqual(default_phases(), resolve_critics({})[0])

    def test_per_phase_enabled_independently_toggled(self):
        phases, _ = resolve_critics({
            "design": {"enabled": True},
            "plan": {"enabled": True, "maxRounds": 3},
            "implementation": {"enabled": True, "coherence": {"enabled": True}},
        })
        self.assertTrue(phases["design"]["enabled"])
        self.assertFalse(phases["questions"]["enabled"])  # untouched ⇒ default OFF
        self.assertTrue(phases["plan"]["enabled"])
        self.assertEqual(phases["plan"]["maxRounds"], 3)
        self.assertTrue(phases["implementation"]["enabled"])
        self.assertTrue(phases["implementation"]["coherence"]["enabled"])

    def test_warnings_aggregated_from_design(self):
        _, warnings = resolve_critics({"design": {"lenses": ["x"], "candidates": 50}})
        self.assertEqual(len(warnings), 2)


if __name__ == "__main__":
    unittest.main()
