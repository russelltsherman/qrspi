#!/usr/bin/env python3
"""Unit tests for revise.py — stdlib only, run with python3.

    python3 scripts/revise_test.py

Slice 3 scope (plan §3.20, structure §Slice 3 Verification): the shared LLM seam
`meta_agent.complete` is mocked, and we assert:
  (a) a concrete mocked edit applies and `revise_skill` returns `revised`;
  (b) a `missing` anchor is skipped + logged and the skill text is unchanged;
  (c) an `ambiguous` anchor is skipped + logged and the skill text is unchanged;
  (d) `--dry-run` leaves `revision-log.json` untouched.

The mock boundary is `meta_agent.complete` (per impl-log §Slice 1 notes — callers
may mock `complete` directly; reuses the diagnose_test.py `_MockSeam` pattern).
Defensive parsing is also covered: an empty/unparseable seam return degrades to
no revisions rather than raising.
"""

import json
import os
import tempfile
import unittest

import meta_agent
import revise


# --- fixtures --------------------------------------------------------------

SKILL_WITH_UNIQUE_ANCHOR = (
    "# Skill\n"
    "Always greet the user.\n"
    "Then answer the question.\n"
)

SKILL_WITH_DUP_ANCHOR = (
    "# Skill\n"
    "Be concise.\n"
    "Be concise.\n"
)


def _diagnosis(category="MISSING_INSTRUCTION", cases=None):
    """A FAILURES_DETECTED diagnosis with one prompt-addressable recommendation."""
    return {
        "status": "FAILURES_DETECTED",
        "total_failures": 1,
        "failures": [],
        "recommendations": [
            {
                "category": category,
                "description": "x",
                "affected_cases": cases or ["case-1"],
                "suggested_action": "add instruction",
            }
        ],
    }


class _MockSeam:
    """Context manager that replaces meta_agent.complete with a recording stub."""

    def __init__(self, return_value):
        self.return_value = return_value
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = meta_agent.complete

        def fake(system, user, model=None):
            self.calls.append((system, user, model))
            return self.return_value

        meta_agent.complete = fake
        return self

    def __exit__(self, *exc):
        meta_agent.complete = self._orig
        return False


def _edit_response(old_text, new_text, description="fix"):
    return json.dumps([{"old_text": old_text, "new_text": new_text, "description": description}])


def _run_revise(skill_text, seam_return, dry_run=False, diagnosis=None):
    """Write skill + diagnosis to a temp dir, run revise_skill under a mocked seam.

    Returns (result, dir, output_path, log_path, final_skill_text).
    """
    diagnosis = diagnosis if diagnosis is not None else _diagnosis()
    with tempfile.TemporaryDirectory() as d:
        skill_path = os.path.join(d, "skill.md")
        diag_path = os.path.join(d, "diagnosis.json")
        out_path = os.path.join(d, "skill.md")  # overwrite in place
        log_path = os.path.join(d, "revision-log.json")
        with open(skill_path, "w") as f:
            f.write(skill_text)
        with open(diag_path, "w") as f:
            json.dump(diagnosis, f)

        with _MockSeam(seam_return):
            result = revise.revise_skill(skill_path, diag_path, out_path, dry_run=dry_run)

        final_skill = None
        if os.path.exists(out_path):
            with open(out_path) as f:
                final_skill = f.read()
        log_exists = os.path.exists(log_path)
        log_contents = None
        if log_exists:
            with open(log_path) as f:
                log_contents = json.load(f)
        return result, log_exists, log_contents, final_skill


# --- pure verify_anchor ----------------------------------------------------

class VerifyAnchorTest(unittest.TestCase):
    def test_unique_anchor_ok(self):
        self.assertEqual(
            revise.verify_anchor(SKILL_WITH_UNIQUE_ANCHOR, "Always greet the user."),
            {"ok": True, "reason": "ok"},
        )

    def test_missing_anchor(self):
        self.assertEqual(
            revise.verify_anchor(SKILL_WITH_UNIQUE_ANCHOR, "not present"),
            {"ok": False, "reason": "missing"},
        )

    def test_empty_anchor_missing(self):
        self.assertEqual(
            revise.verify_anchor(SKILL_WITH_UNIQUE_ANCHOR, ""),
            {"ok": False, "reason": "missing"},
        )

    def test_ambiguous_anchor(self):
        self.assertEqual(
            revise.verify_anchor(SKILL_WITH_DUP_ANCHOR, "Be concise."),
            {"ok": False, "reason": "ambiguous"},
        )


# --- (a) concrete edit applies -> revised ----------------------------------

class ConcreteEditAppliesTest(unittest.TestCase):
    def test_concrete_edit_applies_and_status_revised(self):
        seam = _edit_response(
            "Always greet the user.",
            "Always greet the user warmly and by name.",
        )
        result, _log_exists, _log, final_skill = _run_revise(
            SKILL_WITH_UNIQUE_ANCHOR, seam
        )
        self.assertEqual(result["status"], "revised")
        self.assertIn("warmly and by name", final_skill)
        self.assertNotIn("Always greet the user.\n", final_skill)
        # The single applied edit is logged as applied.
        applied = [a for a in result["applied"] if a["status"] == "applied"]
        self.assertEqual(len(applied), 1)


# --- (b) missing anchor skipped, skill unchanged ---------------------------

class MissingAnchorSkippedTest(unittest.TestCase):
    def test_missing_anchor_skipped_and_skill_unchanged(self):
        seam = _edit_response("THIS TEXT IS NOT IN THE SKILL", "whatever")
        result, _log_exists, _log, final_skill = _run_revise(
            SKILL_WITH_UNIQUE_ANCHOR, seam
        )
        # No edit landed -> not "revised", skill text byte-for-byte unchanged.
        self.assertEqual(result["status"], "no_changes")
        self.assertEqual(final_skill, SKILL_WITH_UNIQUE_ANCHOR)
        # The skip is recorded in the anchor log with reason "missing".
        reasons = {c["reason"] for c in result["anchor_checks"]}
        self.assertIn("missing", reasons)
        # apply_revisions was never handed the unsafe edit.
        applied = [a for a in result["applied"] if a["status"] == "applied"]
        self.assertEqual(applied, [])


# --- (c) ambiguous anchor skipped, skill unchanged -------------------------

class AmbiguousAnchorSkippedTest(unittest.TestCase):
    def test_ambiguous_anchor_skipped_and_skill_unchanged(self):
        seam = _edit_response("Be concise.", "Be concise and direct.")
        result, _log_exists, _log, final_skill = _run_revise(
            SKILL_WITH_DUP_ANCHOR, seam
        )
        self.assertEqual(result["status"], "no_changes")
        self.assertEqual(final_skill, SKILL_WITH_DUP_ANCHOR)
        reasons = {c["reason"] for c in result["anchor_checks"]}
        self.assertIn("ambiguous", reasons)
        applied = [a for a in result["applied"] if a["status"] == "applied"]
        self.assertEqual(applied, [])


# --- (d) --dry-run does not mutate revision-log.json -----------------------

class DryRunNoLogMutationTest(unittest.TestCase):
    def test_dry_run_does_not_write_revision_log(self):
        seam = _edit_response(
            "Always greet the user.",
            "Always greet the user warmly.",
        )
        result, log_exists, _log, final_skill = _run_revise(
            SKILL_WITH_UNIQUE_ANCHOR, seam, dry_run=True
        )
        self.assertEqual(result["status"], "dry_run")
        # revision-log.json must NOT have been created/mutated.
        self.assertFalse(log_exists)
        # The skill itself is also left untouched under dry-run.
        self.assertEqual(final_skill, SKILL_WITH_UNIQUE_ANCHOR)
        # The proposal + anchor checks are still surfaced for inspection.
        self.assertIn("revisions", result)
        self.assertIn("anchor_checks", result)

    def test_dry_run_does_not_append_to_existing_log(self):
        seam = _edit_response(
            "Always greet the user.",
            "Always greet the user warmly.",
        )
        with tempfile.TemporaryDirectory() as d:
            skill_path = os.path.join(d, "skill.md")
            diag_path = os.path.join(d, "diagnosis.json")
            out_path = os.path.join(d, "skill.md")
            log_path = os.path.join(d, "revision-log.json")
            with open(skill_path, "w") as f:
                f.write(SKILL_WITH_UNIQUE_ANCHOR)
            with open(diag_path, "w") as f:
                json.dump(_diagnosis(), f)
            # Seed an existing log.
            existing = [{"timestamp": "prior", "status": "revised"}]
            with open(log_path, "w") as f:
                json.dump(existing, f)

            with _MockSeam(seam):
                revise.revise_skill(skill_path, diag_path, out_path, dry_run=True)

            with open(log_path) as f:
                after = json.load(f)
            self.assertEqual(after, existing)  # untouched


# --- defensive: no-result / unparseable seam -> no revisions ---------------

class DefensiveSeamTest(unittest.TestCase):
    def test_no_result_seam_yields_no_revisions(self):
        result, _log_exists, _log, final_skill = _run_revise(
            SKILL_WITH_UNIQUE_ANCHOR, meta_agent.NO_RESULT
        )
        self.assertEqual(result["status"], "no_changes")
        self.assertEqual(result["revisions"], [])
        self.assertEqual(final_skill, SKILL_WITH_UNIQUE_ANCHOR)

    def test_unparseable_seam_yields_no_revisions(self):
        result, _log_exists, _log, final_skill = _run_revise(
            SKILL_WITH_UNIQUE_ANCHOR, "not json {{{"
        )
        self.assertEqual(result["status"], "no_changes")
        self.assertEqual(result["revisions"], [])
        self.assertEqual(final_skill, SKILL_WITH_UNIQUE_ANCHOR)

    def test_non_prompt_addressable_diagnosis_makes_no_seam_call(self):
        diag = _diagnosis(category="MODEL_LIMITATION")
        with tempfile.TemporaryDirectory() as d:
            skill_path = os.path.join(d, "skill.md")
            diag_path = os.path.join(d, "diagnosis.json")
            out_path = os.path.join(d, "skill.md")
            with open(skill_path, "w") as f:
                f.write(SKILL_WITH_UNIQUE_ANCHOR)
            with open(diag_path, "w") as f:
                json.dump(diag, f)
            with _MockSeam("should not be called") as seam:
                result = revise.revise_skill(skill_path, diag_path, out_path)
            self.assertEqual(seam.calls, [])
        self.assertEqual(result["revisions"], [])


# --- ALL_PASSING short-circuit (pre-existing behavior preserved) -----------

class AllPassingTest(unittest.TestCase):
    def test_all_passing_returns_no_changes_without_seam_call(self):
        with tempfile.TemporaryDirectory() as d:
            skill_path = os.path.join(d, "skill.md")
            diag_path = os.path.join(d, "diagnosis.json")
            out_path = os.path.join(d, "skill.md")
            with open(skill_path, "w") as f:
                f.write(SKILL_WITH_UNIQUE_ANCHOR)
            with open(diag_path, "w") as f:
                json.dump({"status": "ALL_PASSING", "recommendations": []}, f)
            with _MockSeam("should not be called") as seam:
                result = revise.revise_skill(skill_path, diag_path, out_path)
            self.assertEqual(seam.calls, [])
        self.assertEqual(result["status"], "no_changes")


if __name__ == "__main__":
    unittest.main()
