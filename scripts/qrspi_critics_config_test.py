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
    DEFAULT_REVIEW_DESIGN_LENSES,
    DEFAULT_REVIEW_IMPL_LENSES,
    DEFAULT_REVIEW_PLAN_LENSES,
    KNOWN_IMPL_LENSES,
    KNOWN_PLAN_LENSES,
    default_phases,
    resolve_critics,
    resolve_design,
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
                # RUS-77 cost-lever gates default OFF/absent (gateBehindEdge retired in RUS-88).
                "digest": {"enabled": False},
            },
        )
        # lensModel key is OMITTED entirely (absent, not None) by default; the retired
        # gateBehindEdge key must NOT appear (RUS-88).
        self.assertNotIn("lensModel", out)
        self.assertNotIn("gateBehindEdge", out)
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

    def test_gate_behind_edge_key_never_emitted(self):
        # RUS-88: gateBehindEdge was retired — a config that still carries the key is
        # silently ignored and the resolved shape never includes it.
        self.assertNotIn("gateBehindEdge", self._resolve({})[0])
        self.assertNotIn("gateBehindEdge", self._resolve({"gateBehindEdge": {"enabled": True}})[0])

    def test_surviving_levers_on_parse_together(self):
        out, warnings = self._resolve({
            "digest": {"enabled": True},
            "lensModel": "claude-haiku",
        })
        self.assertEqual(out["digest"], {"enabled": True})
        self.assertEqual(out["lensModel"], "claude-haiku")
        self.assertNotIn("gateBehindEdge", out)
        self.assertEqual(warnings, [])


class DesignReviewWhitelistTests(unittest.TestCase):
    """RUS-82 whitelist/default decoupling: `design-review` is whitelist-acceptable
    (config-addable via critics.design.lenses) but default-OFF (absent from the default
    resolved set). resolve_design KEEPS it when listed, DROPS it when not, and the
    empty-after-filter fallback is unaffected."""

    def _resolve(self, cfg):
        warnings = []
        return resolve_design(cfg, warnings), warnings

    def test_default_resolve_is_still_the_four_design_review_absent(self):
        # T3: with no lenses config, the default resolved set is exactly the four — the
        # default-OFF invariant; design-review must NOT appear.
        out, warnings = self._resolve(None)
        self.assertEqual(out["lenses"], DEFAULT_DESIGN_LENSES)
        self.assertEqual(len(out["lenses"]), 4)
        self.assertNotIn("design-review", out["lenses"])
        self.assertEqual(warnings, [])

    def test_unlisted_design_review_dropped(self):
        # T4: design-review is NOT activated implicitly. A config that lists only other
        # (unknown) ids drops them and falls back to the four; design-review stays absent.
        out, warnings = self._resolve({"lenses": ["completeness", "internal-consistency"]})
        self.assertNotIn("design-review", out["lenses"])

    def test_listed_design_review_kept(self):
        # T5: opt-in activation survives the whitelist filter (KNOWN_DESIGN_LENSES now
        # admits design-review), with no warning since it is a known lens.
        out, warnings = self._resolve({"lenses": ["completeness", "design-review"]})
        self.assertIn("design-review", out["lenses"])
        self.assertEqual(out["lenses"], ["completeness", "design-review"])
        self.assertEqual(warnings, [])

    def test_design_review_alone_kept(self):
        # A config opting into ONLY design-review keeps just that lens (non-empty after
        # filter, so no fallback to the four).
        out, warnings = self._resolve({"lenses": ["design-review"]})
        self.assertEqual(out["lenses"], ["design-review"])
        self.assertEqual(warnings, [])

    def test_empty_after_filter_falls_back_to_the_four(self):
        # T6: an all-unknown lenses list resolves empty and falls back to the four
        # DEFAULT_DESIGN_LENSES — the whitelist change does not alter the fallback path,
        # and design-review is NOT injected by the fallback.
        out, warnings = self._resolve({"lenses": ["nope", "nada"]})
        self.assertEqual(out["lenses"], DEFAULT_DESIGN_LENSES)
        self.assertNotIn("design-review", out["lenses"])
        self.assertEqual(len(warnings), 1)


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


class ReviewPanelConstantsTests(unittest.TestCase):
    """RUS-91: the on-demand /review-* panels are NEW ordered constants, DISTINCT
    from the batch DEFAULT_DESIGN_LENSES. Plan/impl lens ids are phase-qualified so
    `qrspi-<phase>-critic-<id>` resolves to a distinct agent and the ids do not
    collide in the bare-lens-keyed critic-metrics summary."""

    def test_review_design_panel_exact_ordered_contents(self):
        self.assertEqual(
            DEFAULT_REVIEW_DESIGN_LENSES,
            ("completeness", "internal-consistency", "edge-alignment",
             "simplicity", "design-review"),
        )

    def test_review_plan_panel_exact_ordered_contents(self):
        self.assertEqual(
            DEFAULT_REVIEW_PLAN_LENSES,
            ("plan-review", "plan-fidelity", "plan-completeness"),
        )

    def test_review_impl_panel_exact_ordered_contents(self):
        self.assertEqual(
            DEFAULT_REVIEW_IMPL_LENSES,
            ("impl-review", "impl-fidelity", "impl-completeness"),
        )

    def test_review_panel_is_distinct_from_batch_default(self):
        # Locks the review-panel-vs-batch-default distinction: design-review is in
        # the review panel but NOT in the batch default. A future edit cannot
        # silently collapse them.
        self.assertIn("design-review", DEFAULT_REVIEW_DESIGN_LENSES)
        self.assertNotIn("design-review", DEFAULT_DESIGN_LENSES)

    def test_known_plan_impl_allow_lists_mirror_their_panels(self):
        self.assertEqual(KNOWN_PLAN_LENSES, set(DEFAULT_REVIEW_PLAN_LENSES))
        self.assertEqual(KNOWN_IMPL_LENSES, set(DEFAULT_REVIEW_IMPL_LENSES))

    def test_plan_impl_lens_ids_are_phase_qualified(self):
        # Every plan/impl review-panel lens id is phase-prefixed (no bare id shared
        # across phases) so qrspi-<phase>-critic-<id> resolves to a distinct agent
        # and the ids do not merge in the bare-lens-keyed metrics summary.
        for lens in DEFAULT_REVIEW_PLAN_LENSES:
            self.assertTrue(lens.startswith("plan-"),
                            f"plan lens id {lens!r} is not phase-qualified")
        for lens in DEFAULT_REVIEW_IMPL_LENSES:
            self.assertTrue(lens.startswith("impl-"),
                            f"impl lens id {lens!r} is not phase-qualified")
        # No id collides across the two phase panels.
        self.assertEqual(KNOWN_PLAN_LENSES & KNOWN_IMPL_LENSES, set())


class ResolveImplementationTests(unittest.TestCase):
    def test_defaults_all_off(self):
        # RUS-88: the per-slice edge critic was retired, so the top-level enabled/maxRounds
        # (which gated ONLY that loop) are gone — only the coherence sub-block survives.
        self.assertEqual(
            resolve_implementation(None),
            {"coherence": {"enabled": False, "maxRounds": DEFAULT_MAX_ROUNDS}},
        )

    def test_only_coherence_key_present(self):
        # The retired top-level enabled/maxRounds keys must NOT reappear.
        out = resolve_implementation({"enabled": True, "maxRounds": 7})
        self.assertEqual(set(out), {"coherence"})
        self.assertNotIn("enabled", out)
        self.assertNotIn("maxRounds", out)

    def test_coherence_enabled_true_honored(self):
        out = resolve_implementation({"coherence": {"enabled": True, "maxRounds": 4}})
        self.assertTrue(out["coherence"]["enabled"])
        self.assertEqual(out["coherence"]["maxRounds"], 4)

    def test_non_dict_coherence_falls_back(self):
        out = resolve_implementation({"coherence": "yes"})
        self.assertEqual(out["coherence"], {"enabled": False, "maxRounds": DEFAULT_MAX_ROUNDS})


class ResolveCriticsTests(unittest.TestCase):
    """Top-level aggregation: only the two surviving phases present (RUS-88 retired the
    fidelity-only edge critic on questions/research/structure/plan), defaults all OFF."""

    def test_absent_block_two_phases_only(self):
        # RUS-88: resolve_critics emits EXACTLY {design, implementation} — no edge phase.
        for critics in (None, "", {}, [], 42):
            phases, warnings = resolve_critics(critics)
            self.assertEqual(set(phases), {"design", "implementation"})
            self.assertEqual(warnings, [])
            # The design panel defaults OFF (opt-in); the coherence pass defaults OFF.
            self.assertFalse(phases["design"]["enabled"], f"design should default disabled with critics={critics!r}")
            self.assertFalse(phases["implementation"]["coherence"]["enabled"])
            # No retired edge phase leaks back in.
            for gone in ("questions", "research", "structure", "plan"):
                self.assertNotIn(gone, phases)

    def test_no_lenses_config_still_emits_no_edge_phase(self):
        # A config with no lenses (or no design block) still resolves the panel + coherence,
        # and emits no edge phase — the 2-key shape is invariant of the lens set.
        phases, _ = resolve_critics({})
        self.assertEqual(set(phases), {"design", "implementation"})
        self.assertEqual(phases["design"]["lenses"], DEFAULT_DESIGN_LENSES)
        self.assertIn("coherence", phases["implementation"])

    def test_panel_and_coherence_still_resolve_when_enabled(self):
        # Lenses present ⇒ the panel resolves with that lens set; coherence sub-shape retained.
        phases, _ = resolve_critics({
            "design": {"enabled": True, "lenses": ["completeness"]},
            "implementation": {"coherence": {"enabled": True, "maxRounds": 3}},
        })
        self.assertTrue(phases["design"]["enabled"])
        self.assertEqual(phases["design"]["lenses"], ["completeness"])
        self.assertTrue(phases["implementation"]["coherence"]["enabled"])
        self.assertEqual(phases["implementation"]["coherence"]["maxRounds"], 3)

    def test_default_phases_matches_empty_resolution(self):
        # Structurally the two are equal; the expectation now reflects exactly 2 keys.
        self.assertEqual(default_phases(), resolve_critics({})[0])
        self.assertEqual(set(default_phases()), {"design", "implementation"})

    def test_warnings_aggregated_from_design(self):
        _, warnings = resolve_critics({"design": {"lenses": ["x"], "candidates": 50}})
        self.assertEqual(len(warnings), 2)


if __name__ == "__main__":
    unittest.main()
