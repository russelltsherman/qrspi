#!/usr/bin/env python3
"""Unit tests for qrspi_ci_revise_bump.py pure helpers — stdlib only, run with python3.

The pure core `bump_ci_revise_trailer` is the SOLE deterministic authority for advancing the
`CI-Revise-Attempt: N` head-commit trailer (RUS-83 / Option A'). These tests pin the AC5
guarantee: absent ⇒ 1, N ⇒ N+1, EXACTLY one trailer (no duplicate appended), and the subject
plus every other trailer preserved byte-for-byte — with the same last-occurrence-wins parse as
the gather (the trailer is the shared serialization contract between writer and reader).
"""

import unittest

import qrspi_ci_revise_bump as m


def trailer_count(message):
    return len(m._CI_REVISE_ATTEMPT_RE.findall(message))


class ParseTest(unittest.TestCase):
    def test_absent_is_zero(self):
        self.assertEqual(m.parse_ci_revise_attempt("subject\n\nbody"), 0)

    def test_none_is_zero(self):
        self.assertEqual(m.parse_ci_revise_attempt(None), 0)

    def test_empty_is_zero(self):
        self.assertEqual(m.parse_ci_revise_attempt(""), 0)

    def test_single_value(self):
        self.assertEqual(m.parse_ci_revise_attempt("subj\n\nCI-Revise-Attempt: 2"), 2)

    def test_last_occurrence_wins(self):
        msg = "subj\n\nCI-Revise-Attempt: 1\nCI-Revise-Attempt: 4"
        self.assertEqual(m.parse_ci_revise_attempt(msg), 4)


class BumpAbsentTest(unittest.TestCase):
    def test_absent_trailer_becomes_one(self):
        new_msg, prior, new_value = m.bump_ci_revise_trailer("Fix the build\n\nsome body")
        self.assertEqual(prior, 0)
        self.assertEqual(new_value, 1)
        self.assertEqual(trailer_count(new_msg), 1)
        self.assertIn("CI-Revise-Attempt: 1", new_msg)

    def test_subject_preserved_when_absent(self):
        new_msg, _, _ = m.bump_ci_revise_trailer("RUS-83 [I] 1/3: do a thing\n\nbody line")
        self.assertTrue(new_msg.startswith("RUS-83 [I] 1/3: do a thing\n"))
        self.assertIn("body line", new_msg)


class BumpExistingTest(unittest.TestCase):
    def test_two_becomes_three(self):
        msg = "subj\n\nbody\n\nCI-Revise-Attempt: 2"
        new_msg, prior, new_value = m.bump_ci_revise_trailer(msg)
        self.assertEqual(prior, 2)
        self.assertEqual(new_value, 3)
        self.assertIn("CI-Revise-Attempt: 3", new_msg)

    def test_exactly_one_trailer_no_duplicate(self):
        # An existing trailer must be REPLACED, not duplicated.
        msg = "subj\n\nCI-Revise-Attempt: 5"
        new_msg, _, _ = m.bump_ci_revise_trailer(msg)
        self.assertEqual(trailer_count(new_msg), 1)
        self.assertIn("CI-Revise-Attempt: 6", new_msg)
        self.assertNotIn("CI-Revise-Attempt: 5", new_msg)

    def test_last_occurrence_wins_then_single(self):
        # Two trailers present: prior is the LAST (4), and the result collapses to one.
        msg = "subj\n\nCI-Revise-Attempt: 1\nCI-Revise-Attempt: 4"
        new_msg, prior, new_value = m.bump_ci_revise_trailer(msg)
        self.assertEqual(prior, 4)
        self.assertEqual(new_value, 5)
        self.assertEqual(trailer_count(new_msg), 1)
        self.assertIn("CI-Revise-Attempt: 5", new_msg)
        self.assertNotIn("CI-Revise-Attempt: 1", new_msg)


class PreservationTest(unittest.TestCase):
    def test_subject_preserved_byte_for_byte(self):
        subject = "RUS-83 [I] 2/3: wire doRevise to the helper"
        msg = subject + "\n\nbody paragraph\n\nCI-Revise-Attempt: 1"
        new_msg, _, _ = m.bump_ci_revise_trailer(msg)
        self.assertTrue(new_msg.startswith(subject + "\n"))

    def test_other_trailers_preserved(self):
        msg = (
            "Fix build\n\n"
            "Explanatory body.\n\n"
            "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>\n"
            "CI-Revise-Attempt: 2"
        )
        new_msg, _, new_value = m.bump_ci_revise_trailer(msg)
        self.assertEqual(new_value, 3)
        self.assertIn(
            "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>",
            new_msg,
        )
        self.assertEqual(trailer_count(new_msg), 1)
        self.assertIn("CI-Revise-Attempt: 3", new_msg)

    def test_other_trailer_order_kept_before_counter(self):
        # The Co-Authored-By trailer stays in place; the counter is the LAST line.
        msg = (
            "Fix build\n\n"
            "Co-Authored-By: Someone <s@example.com>\n"
            "CI-Revise-Attempt: 0"
        )
        new_msg, _, _ = m.bump_ci_revise_trailer(msg)
        lines = new_msg.rstrip("\n").split("\n")
        self.assertEqual(lines[-1], "CI-Revise-Attempt: 1")
        self.assertIn("Co-Authored-By: Someone <s@example.com>", lines)

    def test_result_ends_with_single_newline(self):
        new_msg, _, _ = m.bump_ci_revise_trailer("subj")
        self.assertTrue(new_msg.endswith("CI-Revise-Attempt: 1\n"))
        self.assertFalse(new_msg.endswith("\n\n"))


class EnvelopeTest(unittest.TestCase):
    def test_ok_envelope_has_no_error_key(self):
        env = m.build_envelope("RUS-83/slice-1", ok=True, prior=0, new=1)
        self.assertEqual(env["ok"], True)
        self.assertEqual(env["branch"], "RUS-83/slice-1")
        self.assertEqual(env["prior"], 0)
        self.assertEqual(env["new"], 1)
        self.assertNotIn("error", env)

    def test_failure_envelope_carries_error(self):
        env = m.build_envelope("RUS-83/design", ok=False, error="boom")
        self.assertEqual(env["ok"], False)
        self.assertEqual(env["error"], "boom")


if __name__ == "__main__":
    unittest.main()
