#!/usr/bin/env python3
"""Teeth eval for the design completeness-lens contract (RUS-77 / AC-TEETH).

Contract-style ``unittest`` (Decision 4 Option B): load the deliberately-flawed
design fixture ``evals/fixtures/design_dropped_criterion_broken.md`` and its
golden ``evals/golden/design_dropped_criterion_broken.json`` and DETERMINISTICALLY
assert that the dropped acceptance criterion is surfaced by the SAME
stated-minus-covered coverage check the completeness-lens contract is asked to
perform.

This is a STRUCTURAL check over the *fixture*, not a live LLM call: it verifies
the fixture is well-formed (it really carries a detectable dropped-criterion
flaw) and — via the "teeth-of-the-teeth" repair case — that the detection is
load-bearing (repairing the fixture makes the flaw vanish, so the test would
FAIL if the injected flaw were removed). True behavioral teeth on the live LLM
critic (Decision 4 Option A) require reviving ``evals/run_eval.py`` (a
non-functional placeholder) and are deferred; the fixture + golden created here
are the durable substrate a revived runner would consume.

Run: python3 scripts/qrspi_teeth_test.py
"""

import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURE = os.path.join(
    REPO_ROOT, "evals", "fixtures", "design_dropped_criterion_broken.md")
GOLDEN = os.path.join(
    REPO_ROOT, "evals", "golden", "design_dropped_criterion_broken.json")


# ---------------------------------------------------------------------------
# Pure helpers (importable so the repair "teeth-of-the-teeth" case can re-run
# detection on an in-memory repaired copy of the design).
# ---------------------------------------------------------------------------

def split_sections(design_text):
    """Return {section_title: section_body} for every ``## `` heading.

    The body is every line after the heading up to the next ``## `` heading
    (deeper ``### `` subheadings stay inside their parent ``## `` section).
    """
    sections = {}
    current = None
    buf = []
    for line in design_text.splitlines():
        m = re.match(r"^##\s+(.*\S)\s*$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf)
            current = m.group(1).strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def stated_criteria(design_text):
    """Extract the quoted acceptance-criterion labels from Desired End State.

    Each criterion is a bullet of the shape ``- "<label>" -> <behavior>``.
    Returns the ordered list of ``<label>`` strings.
    """
    sections = split_sections(design_text)
    body = sections.get("Desired End State", "")
    labels = []
    for line in body.splitlines():
        m = re.match(r'^\s*-\s+"([^"]+)"', line)
        if m:
            labels.append(m.group(1))
    return labels


def _coverage_signatures(label):
    """Distinctive tokens that prove a criterion is implemented in the Delta.

    Deterministic, fixture-shape-specific: a criterion is "covered" iff at
    least one of its signature tokens appears in the implementation sections
    (Delta + Pattern Decisions). For the dropped "403 unless admin" criterion
    the signatures (``403``, ``canAccess``) appear NOWHERE in the broken
    fixture's Delta/Decisions, so it reads as uncovered.
    """
    tokens = set()
    # The bare label text is itself a signature.
    tokens.add(label.lower())
    # Any standalone HTTP status code in the label (e.g. 401, 403).
    for code in re.findall(r"\b(\d{3})\b", label):
        tokens.add(code)
    # A few semantic tokens for the criteria in this fixture family.
    low = label.lower()
    if "admin" in low or "403" in low:
        tokens.update({"canaccess", "403", "admin"})
    if "401" in low or "unauthorized" in low:
        tokens.update({"requireauth", "401"})
    if "p95" in low or "200ms" in low or "latency" in low:
        tokens.update({"p95", "perf/", "load-test"})
    if "prefs" in low or "preference" in low or "display" in low:
        tokens.update({"getpreferences", "foruser", "default_preferences"})
    return tokens


def covered_criteria(design_text, criteria):
    """Return the subset of *criteria* whose signatures appear in the impl text.

    Implementation text = the Delta section plus all Pattern Decisions.
    """
    sections = split_sections(design_text)
    impl_text = "\n".join([
        sections.get("Delta", ""),
        sections.get("Pattern Decisions", ""),
    ]).lower()
    covered = []
    for label in criteria:
        sigs = _coverage_signatures(label)
        if any(sig in impl_text for sig in sigs):
            covered.append(label)
    return covered


def dropped_criteria(design_text):
    """Return stated criteria that are NOT covered by the implementation.

    This is the exact ``stated - covered`` gap the completeness-lens contract
    is asked to surface.
    """
    stated = stated_criteria(design_text)
    covered = set(covered_criteria(design_text, stated))
    return [c for c in stated if c not in covered]


def repair_fixture(design_text, dropped_label):
    """Return a copy of *design_text* with *dropped_label* re-added to the Delta.

    Used by the teeth-of-the-teeth case: re-adding the dropped criterion's
    implementation must make the detection find NO dropped criterion, proving
    the assertion would FAIL if the injected flaw were absent.
    """
    # Inject a Delta bullet carrying the dropped criterion's coverage signature.
    repair_bullet = (
        "- Modified file `src/controllers/preferences.js` — the handler calls "
        "`canAccess(req.auth, :id)` so non-self, non-admin subjects get 403 "
        f'(implements "{dropped_label}").'
    )
    lines = design_text.splitlines()
    out = []
    inserted = False
    in_delta = False
    for line in lines:
        m = re.match(r"^##\s+(.*\S)\s*$", line)
        if m:
            # Leaving the Delta section: insert the repair before the next ##.
            if in_delta and not inserted:
                out.append(repair_bullet)
                inserted = True
            in_delta = (m.group(1).strip() == "Delta")
        out.append(line)
    if in_delta and not inserted:
        out.append(repair_bullet)
        inserted = True
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class FixtureWellFormedTest(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE) as fh:
            self.design = fh.read()
        with open(GOLDEN) as fh:
            self.golden = json.load(fh)

    def test_golden_states_all_criteria_present_in_fixture(self):
        stated = stated_criteria(self.design)
        # The fixture really states every criterion the golden enumerates.
        self.assertEqual(stated, self.golden["statedCriteria"])

    def test_dropped_criterion_is_detected(self):
        # The injected flaw is detectable by the stated-minus-covered check.
        dropped = dropped_criteria(self.design)
        self.assertEqual(dropped, [self.golden["droppedCriterion"]])
        self.assertTrue(self.golden["mustSurface"])

    def test_dropped_is_subset_of_stated_minus_covered(self):
        stated = set(stated_criteria(self.design))
        covered = set(covered_criteria(self.design, stated))
        gap = stated - covered
        self.assertIn(self.golden["droppedCriterion"], gap)


class TeethOfTheTeethTest(unittest.TestCase):
    """If the injected flaw is removed, the detection must find nothing.

    This is what gives the eval teeth: a fixture that no longer drops the
    criterion yields an empty dropped set, so a passing-but-empty detection
    here proves the assertion above is load-bearing (it would fail if the
    flaw were silently repaired).
    """

    def setUp(self):
        with open(FIXTURE) as fh:
            self.design = fh.read()
        with open(GOLDEN) as fh:
            self.golden = json.load(fh)

    def test_repaired_fixture_has_no_dropped_criterion(self):
        repaired = repair_fixture(self.design, self.golden["droppedCriterion"])
        self.assertEqual(dropped_criteria(repaired), [])

    def test_repair_only_changes_the_dropped_criterion(self):
        # Sanity: repairing must not change which criteria are stated.
        repaired = repair_fixture(self.design, self.golden["droppedCriterion"])
        self.assertEqual(
            stated_criteria(repaired), stated_criteria(self.design))
        # And the broken fixture still detects the flaw (no mutation leak).
        self.assertEqual(
            dropped_criteria(self.design), [self.golden["droppedCriterion"]])


if __name__ == "__main__":
    unittest.main()
