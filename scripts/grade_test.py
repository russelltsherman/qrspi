#!/usr/bin/env python3
"""Unit tests for the programmatic check registry in grade.py.

Stdlib-only ``unittest`` module (``_test.py`` suffix per repo convention),
imports ``grade`` by bare module name, runnable as
``python3 scripts/grade_test.py``.

Every new check has a compliant (expect ``True``) and a non-compliant (expect
``False``) case built from hand-made ``result`` dicts whose ``output`` mirrors
the corresponding ``.qrspi/templates/*`` markers. Cross-cutting tests assert
(a) all 36 suite-referenced names resolve in ``grade.CHECKS``, (b) below-floor
count checks yield ``passed: False`` through the dispatcher, and (c) every new
check returns a ``(False, msg)`` tuple — never a raised exception — on empty
output.
"""

import json
import os
import re
import unittest

import grade

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SUITE_PATH = os.path.join(REPO_ROOT, "evals", "suite.json")


def _result(output="", files=None):
    """Build a minimal run_eval result envelope entry."""
    return {"output": output, "files": files or []}


def _suite_names():
    """Return the set of programmatic check function names in evals/suite.json."""
    with open(SUITE_PATH) as f:
        suite = json.load(f)
    names = set()
    for case in suite["cases"]:
        for assertion in case.get("assertions", []):
            if assertion.get("type") != "programmatic":
                continue
            m = re.match(r"(\w+)\(", assertion["check"])
            if m:
                names.add(m.group(1))
    return names


# The 23 new check functions plus the 3 re-shaped count checks — every check
# this slice authors. Each maps to a "compliant output" / "non-compliant
# output" pair below, exercised generically for the empty-output safety test.
NEW_CHECK_NAMES = [
    "question_count", "slice_count", "total_steps",
    "section_count", "section_question_count", "all_questions_answered",
    "contains_not_found", "not_found_has_search_description",
    "all_answers_have_evidence",
    "code_snippets_under_limit", "risk_register_min_entries",
    "pattern_decisions_have_options", "contains_new_pattern_flag",
    "all_slices_have_context_cost", "no_slice_exceeds_file_limit",
    "all_files_marked_new_or_modify", "no_large_slices_without_justification",
    "all_modify_steps_have_current_after", "all_slices_have_verify_checkpoint",
    "all_steps_are_atomic",
    "has_critical_path", "all_tasks_have_required_fields",
    "session_boundaries_have_reasons", "sessions_have_load_manifests",
    "impl_log_has_required_fields", "impl_log_has_deviations",
]

# Full in-paren args (the trailing result is appended separately) for each new
# check, used by the empty-output safety test. Every check takes a leading
# filename; some take an additional heading/limit/section arg.
INPAREN_ARGS = {
    "question_count": ["questions.md"],
    "slice_count": ["structure.md"],
    "total_steps": ["plan.md"],
    "section_count": ["questions.md", "## "],
    "section_question_count": ["questions.md", "Edge Cases"],
    "all_questions_answered": ["research.md", "fixtures/q.md"],
    "contains_not_found": ["research.md"],
    "not_found_has_search_description": ["research.md"],
    "all_answers_have_evidence": ["research.md"],
    "code_snippets_under_limit": ["research.md", 20],
    "risk_register_min_entries": ["design.md", 2],
    "pattern_decisions_have_options": ["design.md", 2],
    "contains_new_pattern_flag": ["design.md"],
    "all_slices_have_context_cost": ["structure.md"],
    "no_slice_exceeds_file_limit": ["structure.md", 10],
    "all_files_marked_new_or_modify": ["structure.md"],
    "no_large_slices_without_justification": ["structure.md"],
    "all_modify_steps_have_current_after": ["plan.md"],
    "all_slices_have_verify_checkpoint": ["plan.md"],
    "all_steps_are_atomic": ["plan.md"],
    "has_critical_path": ["worktree.md"],
    "all_tasks_have_required_fields": ["worktree.md"],
    "session_boundaries_have_reasons": ["worktree.md"],
    "sessions_have_load_manifests": ["worktree.md"],
    "impl_log_has_required_fields": ["impl-log.md"],
    "impl_log_has_deviations": ["impl-log.md"],
}


class GradeChecksTest(unittest.TestCase):

    # ── Questions / Research phase ──

    def test_question_count(self):
        compliant = "\n".join(f"- Q{i}: q?" for i in range(1, 10))
        self.assertTrue(grade.question_count("questions.md", _result(compliant))[0])
        self.assertFalse(grade.question_count("questions.md", _result("- Q1: q?"))[0])

    def test_section_count(self):
        out = "\n".join(f"## Sec{i}\n- Q{i}: q?" for i in range(1, 6))
        self.assertTrue(grade.section_count("questions.md", "## ", _result(out))[0])
        self.assertFalse(grade.section_count("questions.md", "## ", _result("no headings"))[0])

    def test_section_question_count(self):
        out = "## Edge Cases\n- Q4: q?\n- Q5: q?\n\n## Testing\n- Q6: q?"
        self.assertTrue(
            grade.section_question_count("questions.md", "Edge Cases", _result(out))[0]
        )
        bare = "## Edge Cases\n\n## Testing\n- Q6: q?"
        self.assertFalse(
            grade.section_question_count("questions.md", "Edge Cases", _result(bare))[0]
        )

    def test_all_questions_answered(self):
        ok = "## Q1: a?\n**Answer:** yes\n## Q2: b?\n**Answer:** no"
        self.assertTrue(grade.all_questions_answered("research.md", "f.md", _result(ok))[0])
        bad = "## Q1: a?\n**Answer:** yes\n## Q2: b?\n(no answer)"
        self.assertFalse(grade.all_questions_answered("research.md", "f.md", _result(bad))[0])

    def test_contains_not_found(self):
        self.assertTrue(grade.contains_not_found("research.md", _result("X: NOT FOUND — searched grep"))[0])
        self.assertFalse(grade.contains_not_found("research.md", _result("all found"))[0])

    def test_not_found_has_search_description(self):
        ok = "Endpoint: NOT FOUND — grepped routes/*.py, none match"
        self.assertTrue(grade.not_found_has_search_description("research.md", _result(ok))[0])
        bad = "Endpoint: NOT FOUND"
        self.assertFalse(grade.not_found_has_search_description("research.md", _result(bad))[0])

    def test_all_answers_have_evidence(self):
        ok = "**Answer:** a\n**Evidence:**\n```\nx\n```\n**Answer:** b\n**Evidence:**\n```\ny\n```"
        self.assertTrue(grade.all_answers_have_evidence("research.md", _result(ok))[0])
        bad = "**Answer:** a\n**Evidence:**\n```\nx\n```\n**Answer:** b\n(no evidence)"
        self.assertFalse(grade.all_answers_have_evidence("research.md", _result(bad))[0])

    # ── Design phase ──

    def test_code_snippets_under_limit(self):
        ok = "```\na\nb\n```"
        self.assertTrue(grade.code_snippets_under_limit("research.md", 20, _result(ok))[0])
        big = "```\n" + "\n".join(str(i) for i in range(25)) + "\n```"
        self.assertFalse(grade.code_snippets_under_limit("research.md", 20, _result(big))[0])

    def test_risk_register_min_entries(self):
        ok = ("## Risk Register\n"
              "| Risk | Likelihood | Impact | Mitigation |\n"
              "|------|-----------|--------|------------|\n"
              "| r1 | low | low | m1 |\n"
              "| r2 | med | high | m2 |\n")
        self.assertTrue(grade.risk_register_min_entries("design.md", 2, _result(ok))[0])
        thin = ("## Risk Register\n"
                "| Risk | Likelihood | Impact | Mitigation |\n"
                "|------|-----------|--------|------------|\n"
                "| r1 | low | low | m1 |\n")
        self.assertFalse(grade.risk_register_min_entries("design.md", 2, _result(thin))[0])

    def test_pattern_decisions_have_options(self):
        ok = ("### Decision 1: x\n| Option | Approach |\n|---|---|\n| A | ... |\n"
              "### Decision 2: y\n| Option | Approach |\n|---|---|\n| A | ... |\n")
        self.assertTrue(grade.pattern_decisions_have_options("design.md", 2, _result(ok))[0])
        bad = "### Decision 1: x\nno options table here\n"
        self.assertFalse(grade.pattern_decisions_have_options("design.md", 2, _result(bad))[0])

    def test_contains_new_pattern_flag(self):
        self.assertTrue(grade.contains_new_pattern_flag("design.md", _result("**NEW PATTERN?** No"))[0])
        self.assertFalse(grade.contains_new_pattern_flag("design.md", _result("no flag"))[0])

    # ── Structure phase ──

    def test_all_slices_have_context_cost(self):
        ok = ("## Slice 1: a\n**Context cost:** S\n\n"
              "## Slice 2: b\n**Context cost:** M\n")
        self.assertTrue(grade.all_slices_have_context_cost("structure.md", _result(ok))[0])
        bad = "## Slice 1: a\n**Context cost:** S\n\n## Slice 2: b\nno cost\n"
        self.assertFalse(grade.all_slices_have_context_cost("structure.md", _result(bad))[0])

    def test_no_slice_exceeds_file_limit(self):
        ok = "## Slice 1: a\n- ✨ `f1.py`\n- ⚠️ `f2.py`\n"
        self.assertTrue(grade.no_slice_exceeds_file_limit("structure.md", 10, _result(ok))[0])
        many = "## Slice 1: a\n" + "\n".join(f"- ✨ `f{i}.py`" for i in range(12))
        self.assertFalse(grade.no_slice_exceeds_file_limit("structure.md", 10, _result(many))[0])

    def test_all_files_marked_new_or_modify(self):
        ok = "**Files touched:**\n\n- ✨ `new.py` — x\n- ⚠️ `old.py` — y\n"
        self.assertTrue(grade.all_files_marked_new_or_modify("structure.md", _result(ok))[0])
        bad = "**Files touched:**\n\n- ✨ `new.py` — x\n- `old.py` — y\n"
        self.assertFalse(grade.all_files_marked_new_or_modify("structure.md", _result(bad))[0])

    def test_no_large_slices_without_justification(self):
        ok = "## Slice 1: a\n**Context cost:** L\nThis is large because justification: cohesion.\n"
        self.assertTrue(grade.no_large_slices_without_justification("structure.md", _result(ok))[0])
        bad = "## Slice 1: a\n**Context cost:** L\n**Depends on:** none\n"
        self.assertFalse(grade.no_large_slices_without_justification("structure.md", _result(bad))[0])

    # ── Plan phase ──

    def test_all_modify_steps_have_current_after(self):
        ok = "1. ⚠️ Modify `f.py`\n   - **Current:** x\n   - **After:** y\n"
        self.assertTrue(grade.all_modify_steps_have_current_after("plan.md", _result(ok))[0])
        bad = "1. ⚠️ Modify `f.py`\n   - **Current:** x\n"
        self.assertFalse(grade.all_modify_steps_have_current_after("plan.md", _result(bad))[0])

    def test_all_slices_have_verify_checkpoint(self):
        ok = ("## Slice 1: a\n**Checkpoint:** run tests\n\n"
              "## Slice 2: b\n**Checkpoint:** run more\n")
        self.assertTrue(grade.all_slices_have_verify_checkpoint("plan.md", _result(ok))[0])
        bad = "## Slice 1: a\n**Checkpoint:** run tests\n\n## Slice 2: b\nno checkpoint\n"
        self.assertFalse(grade.all_slices_have_verify_checkpoint("plan.md", _result(bad))[0])

    def test_all_steps_are_atomic(self):
        ok = "1. Modify `a.py`\n2. Modify `b.py`\n"
        self.assertTrue(grade.all_steps_are_atomic("plan.md", _result(ok))[0])
        bad = "1. Modify `a.py` and `b.py` together\n"
        self.assertFalse(grade.all_steps_are_atomic("plan.md", _result(bad))[0])

    # ── Worktree phase ──

    def test_has_critical_path(self):
        self.assertTrue(grade.has_critical_path("worktree.md", _result("**Critical path:** T1 → T2"))[0])
        self.assertFalse(grade.has_critical_path("worktree.md", _result("no path"))[0])

    def test_all_tasks_have_required_fields(self):
        ok = ("| Task ID | Description | Depends On | Plan Step | Cost | Status |\n"
              "|---|---|---|---|---|---|\n"
              "| T1 | do x | — | §1 | S | pending |\n")
        self.assertTrue(grade.all_tasks_have_required_fields("worktree.md", _result(ok))[0])
        bad = ("| Task ID | Description | Depends On | Plan Step | Cost | Status |\n"
               "|---|---|---|---|---|---|\n"
               "| T1 | do x |  | §1 | S | pending |\n")
        self.assertFalse(grade.all_tasks_have_required_fields("worktree.md", _result(bad))[0])

    def test_session_boundaries_have_reasons(self):
        ok = "## Session 1\n--- SESSION BOUNDARY ---\n**Reason:** fresh context\n## Session 2\n"
        self.assertTrue(grade.session_boundaries_have_reasons("worktree.md", _result(ok))[0])
        bad = "## Session 1\n--- SESSION BOUNDARY ---\n## Session 2\n"
        self.assertFalse(grade.session_boundaries_have_reasons("worktree.md", _result(bad))[0])

    def test_sessions_have_load_manifests(self):
        ok = "## Session 1\n**Load:** structure.md\n\n## Session 2\n**Load:** plan.md\n"
        self.assertTrue(grade.sessions_have_load_manifests("worktree.md", _result(ok))[0])
        bad = "## Session 1\n**Load:** structure.md\n\n## Session 2\nno load\n"
        self.assertFalse(grade.sessions_have_load_manifests("worktree.md", _result(bad))[0])

    # ── Implement phase ──

    def test_impl_log_has_required_fields(self):
        ok = "**Timestamp:** 2026\n**Tasks completed:** T1\n**Tests:**\n- cmd → ok\n"
        self.assertTrue(grade.impl_log_has_required_fields("impl-log.md", _result(ok))[0])
        bad = "**Timestamp:** 2026\n**Tests:**\n- cmd → ok\n"
        self.assertFalse(grade.impl_log_has_required_fields("impl-log.md", _result(bad))[0])

    def test_impl_log_has_deviations(self):
        self.assertTrue(grade.impl_log_has_deviations("impl-log.md", _result("**Deviations from plan.md:**\n- none"))[0])
        self.assertFalse(grade.impl_log_has_deviations("impl-log.md", _result("no deviations section"))[0])


class RegistryAndDispatcherTest(unittest.TestCase):

    def test_all_suite_names_registered(self):
        """AC1: every programmatic name in evals/suite.json resolves in CHECKS."""
        names = _suite_names()
        self.assertEqual(len(names), 36, f"expected 36 suite names, got {len(names)}")
        missing = sorted(n for n in names if n not in grade.CHECKS)
        self.assertEqual(missing, [], f"unregistered suite names: {missing}")

    def test_no_suite_assertion_falls_into_unknown_branch(self):
        """AC1: dispatching every suite assertion never yields passed: None."""
        with open(SUITE_PATH) as f:
            suite = json.load(f)
        dummy = _result("", [])
        unknown = []
        for case in suite["cases"]:
            for assertion in case.get("assertions", []):
                if assertion.get("type") != "programmatic":
                    continue
                ar = grade.run_programmatic_check(assertion, dummy)
                if ar["passed"] is None:
                    unknown.append((assertion["check"], ar["evidence"]))
        self.assertEqual(unknown, [], f"assertions resolving to None: {unknown}")

    def test_count_checks_below_threshold_fail(self):
        """AC3 / top risk: below-floor count checks yield passed: False via dispatcher."""
        cases = [
            ("question_count('questions.md')", _result("- Q1: only one")),
            ("slice_count('structure.md')", _result("## Slice 1: only one")),
            ("total_steps('plan.md')", _result("")),
        ]
        for check_str, res in cases:
            ar = grade.run_programmatic_check({"check": check_str}, res)
            self.assertIs(ar["passed"], False, f"{check_str} should fail below threshold; got {ar}")

    def test_count_checks_above_threshold_pass(self):
        """Count checks pass (passed is True, not inert) when the floor is met."""
        many_q = "\n".join(f"- Q{i}: q?" for i in range(1, 10))
        ar = grade.run_programmatic_check({"check": "question_count('questions.md')"}, _result(many_q))
        self.assertIs(ar["passed"], True, f"question_count should pass; got {ar}")

    def test_checks_dont_raise_on_empty_output(self):
        """Defensive-read risk: each new check returns (False, msg) on empty output."""
        empty = _result("", [])
        for name in NEW_CHECK_NAMES:
            func = grade.CHECKS[name]
            args = INPAREN_ARGS[name] + [empty]
            with self.subTest(check=name):
                outcome = func(*args)
                self.assertIsInstance(outcome, tuple, f"{name} did not return a tuple")
                passed, msg = outcome
                self.assertIs(passed, False, f"{name} should be False on empty output")
                self.assertIsInstance(msg, str)


class ExtractJsonTest(unittest.TestCase):
    """Pure helper: locate + parse the first JSON object in mixed prose+JSON."""

    def test_valid_trailing_json_after_prose_prefix(self):
        out = 'Running scope check...\nDONE\n{"out_of_scope": ["foo.py"]}'
        self.assertEqual(grade._extract_json(out), {"out_of_scope": ["foo.py"]})

    def test_pure_json(self):
        self.assertEqual(grade._extract_json('{"ok": true}'), {"ok": True})

    def test_malformed_truncated_json_returns_none(self):
        self.assertIsNone(grade._extract_json('prefix {"out_of_scope": ['))

    def test_no_brace_returns_none(self):
        self.assertIsNone(grade._extract_json("no json here at all"))

    def test_empty_returns_none(self):
        self.assertIsNone(grade._extract_json(""))

    def test_non_object_json_returns_none(self):
        # A bare JSON array has no leading '{', so nothing is parsed.
        self.assertIsNone(grade._extract_json("[1, 2, 3]"))


class InterpretScriptResultTest(unittest.TestCase):
    """Pure half of the script-check runner — exit code + streams → result dict."""

    def _interpret(self, returncode, stdout="", stderr=""):
        return grade.interpret_script_result(
            "check_scope.py args", 2.0, returncode, stdout, stderr
        )

    def test_exit_zero_with_valid_json_passes(self):
        r = self._interpret(0, stdout='{"out_of_scope": []}')
        self.assertTrue(r["passed"])
        self.assertIs(type(r["passed"]), bool)
        self.assertIn("out_of_scope", r["evidence"])

    def test_canonical_five_key_shape(self):
        r = self._interpret(0, stdout='{"ok": true}')
        self.assertEqual(
            set(r.keys()), {"check", "type", "passed", "evidence", "weight"}
        )
        self.assertEqual(r["type"], "script")
        self.assertEqual(r["check"], "check_scope.py args")
        self.assertEqual(r["weight"], 2.0)

    def test_exit_one_with_json_out_of_scope_fails_and_surfaces_it(self):
        r = self._interpret(1, stdout='{"out_of_scope": ["secret.py"]}')
        self.assertFalse(r["passed"])
        self.assertIs(type(r["passed"]), bool)
        self.assertIn("out_of_scope", r["evidence"])
        self.assertIn("secret.py", r["evidence"])

    def test_nonzero_unparseable_stdout_fails_with_raw_stderr(self):
        r = self._interpret(1, stdout="Traceback nonsense", stderr="boom: bad arg")
        self.assertFalse(r["passed"])
        self.assertIs(type(r["passed"]), bool)
        self.assertIn("boom: bad arg", r["evidence"])
        self.assertIn("1", r["evidence"])  # exit code surfaced

    def test_empty_stdout_exit_zero(self):
        r = self._interpret(0, stdout="", stderr="")
        self.assertTrue(r["passed"])
        self.assertIs(type(r["passed"]), bool)

    def test_empty_stdout_nonzero_falls_back_to_placeholder(self):
        r = self._interpret(3, stdout="", stderr="")
        self.assertFalse(r["passed"])
        self.assertIn("3", r["evidence"])

    def test_malformed_json_nonzero_uses_stderr(self):
        r = self._interpret(1, stdout='partial {"a":', stderr="parse died")
        self.assertFalse(r["passed"])
        self.assertIn("parse died", r["evidence"])


class ScriptModuleConstantsTest(unittest.TestCase):
    def test_script_timeout_is_120(self):
        self.assertEqual(grade.SCRIPT_TIMEOUT_SEC, 120)


class StubJudge:
    """Deterministic judge_client stub: records calls, returns canned responses.

    ``responses`` is a list of dicts (the judge_client return contract) and/or
    Exception instances. Each call pops the next; an Exception is raised to
    simulate a transient call failure (exercising call_with_retry).
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, prompt):
        self.calls += 1
        item = self._responses.pop(0) if self._responses else self._responses_default()
        if isinstance(item, Exception):
            raise item
        return item

    @staticmethod
    def _responses_default():
        raise AssertionError("StubJudge called more times than configured")


def _judge_response(text, input_tokens=10, output_tokens=5):
    return {"text": text, "input_tokens": input_tokens, "output_tokens": output_tokens}


class LlmJudgeTest(unittest.TestCase):
    """Covers the injectable-judge contract: build/parse helpers, retry, and
    the run_llm_judge error mapping. All stubbed — no network, no anthropic."""

    def test_build_prompt_includes_criteria_and_output(self):
        prompt = grade.build_judge_prompt("must cite sources", "the agent output")
        self.assertIn("must cite sources", prompt)
        self.assertIn("the agent output", prompt)
        self.assertIn("SCORE:", prompt)

    def test_parse_extracts_score_and_rationale(self):
        score, rationale = grade.parse_judge_response("SCORE: 4\nRATIONALE: good enough")
        self.assertEqual(score, 4)
        self.assertEqual(rationale, "good enough")

    def test_parse_raises_when_no_score(self):
        with self.assertRaises(ValueError):
            grade.parse_judge_response("I think this is pretty good, no marker here")

    def test_happy_path_score_5_passes(self):
        stub = StubJudge([_judge_response("SCORE: 5\nRATIONALE: excellent")])
        ar = grade.run_llm_judge(
            {"criteria": "is good", "weight": 2.0},
            _result("some output"),
            {},
            judge_client=stub,
        )
        self.assertEqual(stub.calls, 1)
        self.assertIs(ar["passed"], True)
        self.assertEqual(ar["score"], 5)
        self.assertEqual(ar["evidence"], "excellent")
        self.assertEqual(ar["weight"], 2.0)
        self.assertEqual(ar["type"], "llm_judge")

    def test_score_below_threshold_fails_but_scored(self):
        stub = StubJudge([_judge_response("SCORE: 2\nRATIONALE: weak")])
        ar = grade.run_llm_judge(
            {"criteria": "is good"}, _result("x"), {}, judge_client=stub
        )
        self.assertIs(ar["passed"], False)
        self.assertEqual(ar["score"], 2)

    def test_out_of_range_maps_to_failure(self):
        stub = StubJudge([_judge_response("SCORE: 9\nRATIONALE: nonsense")])
        ar = grade.run_llm_judge(
            {"criteria": "is good"}, _result("x"), {}, judge_client=stub
        )
        self.assertEqual(stub.calls, 1, "out-of-range must not retry")
        self.assertIs(ar["passed"], False)
        self.assertIsNone(ar["score"])
        self.assertIn("out of range", ar["evidence"])

    def test_unparseable_maps_to_failure_no_retry(self):
        stub = StubJudge([_judge_response("no score marker at all")])
        ar = grade.run_llm_judge(
            {"criteria": "is good"}, _result("x"), {}, judge_client=stub
        )
        self.assertEqual(stub.calls, 1, "parse failure must not retry")
        self.assertIs(ar["passed"], False)
        self.assertIsNone(ar["score"])
        self.assertIn("Unparseable", ar["evidence"])

    def test_retry_exhaustion_calls_three_times(self):
        stub = StubJudge(
            [RuntimeError("boom"), RuntimeError("boom"), RuntimeError("boom")]
        )
        slept = []
        orig_sleep = grade.time.sleep
        grade.time.sleep = slept.append  # don't actually sleep
        try:
            ar = grade.run_llm_judge(
                {"criteria": "is good"}, _result("x"), {}, judge_client=stub
            )
        finally:
            grade.time.sleep = orig_sleep
        self.assertEqual(stub.calls, 3, "must retry up to 3 attempts then give up")
        self.assertEqual(slept, [1.0, 2.0], "exponential backoff between the 3 attempts")
        self.assertIs(ar["passed"], False)
        self.assertIsNone(ar["score"])
        self.assertIn("failed after", ar["evidence"])

    def test_retry_recovers_before_exhaustion(self):
        stub = StubJudge(
            [RuntimeError("transient"), _judge_response("SCORE: 4\nRATIONALE: ok")]
        )
        orig_sleep = grade.time.sleep
        grade.time.sleep = lambda _s: None  # don't actually sleep
        try:
            ar = grade.run_llm_judge(
                {"criteria": "is good"}, _result("x"), {}, judge_client=stub
            )
        finally:
            grade.time.sleep = orig_sleep
        self.assertEqual(stub.calls, 2)
        self.assertIs(ar["passed"], True)
        self.assertEqual(ar["score"], 4)

    def test_empty_output_is_graded_not_short_circuited(self):
        stub = StubJudge([_judge_response("SCORE: 1\nRATIONALE: nothing here")])
        ar = grade.run_llm_judge(
            {"criteria": "is good"}, _result(""), {}, judge_client=stub
        )
        self.assertEqual(stub.calls, 1, "empty output must still reach the judge")
        self.assertIs(ar["passed"], False)
        self.assertEqual(ar["score"], 1)

    def test_call_with_retry_no_sleep_on_success(self):
        stub = StubJudge([_judge_response("SCORE: 3\nRATIONALE: meh")])
        out = grade.call_with_retry(stub, "prompt")
        self.assertEqual(stub.calls, 1)
        self.assertEqual(out["text"], "SCORE: 3\nRATIONALE: meh")

    def test_no_anthropic_import_at_module_load(self):
        """Importing grade must not require anthropic (lazy import contract)."""
        import sys

        self.assertNotIn("anthropic", sys.modules, "grade must not import anthropic eagerly")


if __name__ == "__main__":
    unittest.main()
