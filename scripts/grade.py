#!/usr/bin/env python3
"""Grade eval execution results using programmatic checks and LLM judges.

Runs programmatic assertions first (fast, deterministic), then LLM judge
assertions for subjective quality. Aggregates weighted scores per case
and across the suite.
"""

import argparse
import json
import os
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Programmatic Check Registry ──

def output_file_exists(filename: str, result: dict) -> tuple[bool, str]:
    """Check if a file was produced in the output."""
    exists = filename in result.get("files", [])
    return exists, f"File '{filename}' {'found' if exists else 'not found'} in outputs"


def has_section(filename: str, heading: str, result: dict) -> tuple[bool, str]:
    """Check if the output contains a markdown section with the given heading."""
    output = result.get("output", "")
    pattern = rf"^#+\s+.*{re.escape(heading)}"
    found = bool(re.search(pattern, output, re.MULTILINE | re.IGNORECASE))
    return found, f"Section '{heading}' {'found' if found else 'not found'}"


def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"


def question_count(filename: str, result: dict) -> int:
    """Count questions (lines starting with - Q or numbered Q patterns)."""
    output = result.get("output", "")
    questions = re.findall(r"^-\s+Q\d+:", output, re.MULTILINE)
    return len(questions)


def no_solution_language(filename: str, result: dict) -> tuple[bool, str]:
    """Check that output contains no solution-oriented language."""
    output = result.get("output", "")
    banned = [
        r"\bshould we\b", r"\bwe could\b", r"\bwe should\b",
        r"\bbest way to\b", r"\bI recommend\b", r"\bbetter approach\b",
        r"\bit would be better\b",
    ]
    violations = []
    for pattern in banned:
        matches = re.findall(pattern, output, re.IGNORECASE)
        violations.extend(matches)
    ok = len(violations) == 0
    return ok, f"Solution language: {violations if violations else 'none found'}"


def all_questions_have_target(filename: str, result: dict) -> tuple[bool, str]:
    """Check every question has a Target field."""
    output = result.get("output", "")
    questions = re.findall(r"^-\s+Q\d+:", output, re.MULTILINE)
    targets = re.findall(r"\*\*Target:\*\*", output)
    ok = len(targets) >= len(questions)
    return ok, f"Questions: {len(questions)}, Targets: {len(targets)}"


def current_state_has_citations(filename: str, result: dict) -> tuple[bool, str]:
    """Check that Current State section has (ref: QN) citations."""
    output = result.get("output", "")
    # Extract Current State section
    match = re.search(
        r"## Current State\s*\n(.*?)(?=\n## |\Z)",
        output, re.DOTALL
    )
    if not match:
        return False, "Current State section not found"
    section = match.group(1)
    citations = re.findall(r"\(ref:\s*Q\d+\)", section)
    # At least one citation per paragraph
    paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
    ok = len(citations) >= len(paragraphs) and len(citations) > 0
    return ok, f"Citations: {len(citations)}, Paragraphs: {len(paragraphs)}"


def no_code_blocks(filename: str, result: dict) -> tuple[bool, str]:
    """Check that output has no code blocks (for design docs)."""
    output = result.get("output", "")
    blocks = re.findall(r"```", output)
    ok = len(blocks) == 0
    return ok, f"Code blocks found: {len(blocks) // 2}"


def all_evidence_has_file_citations(filename: str, result: dict) -> tuple[bool, str]:
    """Check that Evidence blocks have file:line citations."""
    output = result.get("output", "")
    evidence_blocks = re.findall(r"\*\*Evidence:\*\*.*?(?=\*\*|\Z)", output, re.DOTALL)
    citations = re.findall(r"`[^`]+:\d+", output)
    ok = len(citations) >= len(evidence_blocks) and len(evidence_blocks) > 0
    return ok, f"Evidence blocks: {len(evidence_blocks)}, File citations: {len(citations)}"


def slice_count(filename: str, result: dict) -> int:
    """Count vertical slices in structure output."""
    output = result.get("output", "")
    slices = re.findall(r"^## Slice \d+", output, re.MULTILINE)
    return len(slices)


def all_slices_have_verification(filename: str, result: dict) -> tuple[bool, str]:
    """Check every slice has a Verification section."""
    output = result.get("output", "")
    slices = re.findall(r"^## Slice \d+", output, re.MULTILINE)
    verifications = re.findall(r"\*\*Verification:\*\*", output)
    ok = len(verifications) >= len(slices)
    return ok, f"Slices: {len(slices)}, Verification sections: {len(verifications)}"


def total_steps(filename: str, result: dict) -> int:
    """Count implementation steps in plan output."""
    output = result.get("output", "")
    steps = re.findall(r"^\d+\.\s+", output, re.MULTILINE)
    return len(steps)


def pr_title_under_limit(filename: str, limit: int, result: dict) -> tuple[bool, str]:
    """Check PR title is under character limit."""
    output = result.get("output", "")
    match = re.search(r"^# PR:\s*(.+)$", output, re.MULTILINE)
    if not match:
        return False, "PR title not found"
    title = match.group(1).strip()
    ok = len(title) <= limit
    return ok, f"PR title length: {len(title)} (limit: {limit})"


# ── Check Dispatcher ──

CHECKS = {
    "output_file_exists": output_file_exists,
    "has_section": has_section,
    "line_count": line_count,
    "no_solution_language": no_solution_language,
    "all_questions_have_target": all_questions_have_target,
    "current_state_has_citations": current_state_has_citations,
    "no_code_blocks": no_code_blocks,
    "all_evidence_has_file_citations": all_evidence_has_file_citations,
    "all_slices_have_verification": all_slices_have_verification,
    "pr_title_under_limit": pr_title_under_limit,
}


def parse_check_call(check_str: str) -> tuple[str, list]:
    """Parse a check string like "has_section('design.md', 'Risk Register')"."""
    match = re.match(r"(\w+)\((.+)\)", check_str)
    if not match:
        return check_str, []
    func_name = match.group(1)
    args_str = match.group(2)
    # Simple argument parser for string and number literals
    args = []
    for arg in re.findall(r"'([^']*)'|(\d+)", args_str):
        if arg[0]:
            args.append(arg[0])
        elif arg[1]:
            args.append(int(arg[1]))
    return func_name, args


def run_programmatic_check(assertion: dict, result: dict) -> dict:
    """Run a single programmatic assertion against an execution result."""
    check_str = assertion["check"]
    func_name, args = parse_check_call(check_str)

    if func_name in CHECKS:
        try:
            outcome = CHECKS[func_name](*args, result)
            if isinstance(outcome, tuple):
                passed, evidence = outcome
            else:
                # Numeric return — used for count checks
                passed = True
                evidence = f"Value: {outcome}"
        except Exception as e:
            passed = False
            evidence = f"Check error: {e}"
    else:
        # Unknown check — skip with warning
        passed = None
        evidence = f"Unknown check function: {func_name}"

    return {
        "check": check_str,
        "type": "programmatic",
        "passed": passed,
        "evidence": evidence,
        "weight": assertion.get("weight", 1.0),
    }


def run_llm_judge(assertion: dict, result: dict, case: dict) -> dict:
    """Run an LLM judge assertion.

    In a real implementation, this calls a grading model:

        response = judge_model.complete(
            system="You are grading an AI agent's output...",
            messages=[{"role": "user", "content": grading_prompt}],
        )

    This stub returns a placeholder for integration.
    """
    return {
        "check": assertion["criteria"],
        "type": "llm_judge",
        "passed": None,  # null until real judge is integrated
        "score": None,    # 1-5 scale from judge
        "evidence": "LLM judge not yet integrated — requires model API",
        "weight": assertion.get("weight", 1.0),
    }


def run_script_check(assertion: dict, result: dict) -> dict:
    """Run a script-based assertion.

    Executes the script and interprets its exit code and stdout.
    """
    return {
        "check": assertion["check"],
        "type": "script",
        "passed": None,
        "evidence": "Script checks not yet integrated",
        "weight": assertion.get("weight", 1.0),
    }


# ── Scoring ──

def score_case(assertion_results: list) -> dict:
    """Compute weighted score for a single case."""
    max_score = 0.0
    actual_score = 0.0
    for ar in assertion_results:
        weight = ar.get("weight", 1.0)
        max_score += weight
        if ar.get("passed") is True:
            actual_score += weight
        elif ar.get("score") is not None:
            # LLM judge: normalize 1-5 to 0-1
            actual_score += weight * (ar["score"] - 1) / 4

    normalized = actual_score / max_score if max_score > 0 else 0.0
    return {
        "score": round(normalized, 4),
        "actual": round(actual_score, 2),
        "max": round(max_score, 2),
        "assertion_count": len(assertion_results),
    }


def score_suite(case_scores: list) -> dict:
    """Compute aggregate suite scores with variance."""
    scores = [cs["score"] for cs in case_scores]
    return {
        "mean": round(statistics.mean(scores), 4) if scores else 0.0,
        "stddev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
        "min": round(min(scores), 4) if scores else 0.0,
        "max": round(max(scores), 4) if scores else 0.0,
        "case_count": len(scores),
    }


# ── Main Grading Pipeline ──

def grade_results(results_path: str, suite_path: str, output_dir: Optional[str] = None) -> dict:
    """Grade execution results against the eval suite."""
    with open(results_path) as f:
        results_data = json.load(f)
    with open(suite_path) as f:
        suite = json.load(f)

    # Index cases by ID
    cases_by_id = {c["id"]: c for c in suite["cases"]}

    # Group results by case_id
    results_by_case = {}
    for r in results_data.get("results", []):
        cid = r["case_id"]
        results_by_case.setdefault(cid, []).append(r)

    case_grades = []
    for case_id, trials in results_by_case.items():
        case = cases_by_id.get(case_id, {})
        assertions = case.get("assertions", [])
        split = case.get("split", "train")

        trial_scores = []
        for trial_result in trials:
            assertion_results = []

            for assertion in assertions:
                atype = assertion.get("type", "")
                if atype == "programmatic":
                    ar = run_programmatic_check(assertion, trial_result)
                elif atype == "llm_judge":
                    ar = run_llm_judge(assertion, trial_result, case)
                elif atype == "script":
                    ar = run_script_check(assertion, trial_result)
                else:
                    ar = {"check": "unknown", "type": atype, "passed": None,
                          "evidence": f"Unknown assertion type: {atype}", "weight": 0}
                assertion_results.append(ar)

            trial_score = score_case(assertion_results)
            trial_score["trial_id"] = trial_result.get("trial_id", 0)
            trial_score["assertions"] = assertion_results
            trial_scores.append(trial_score)

        # Aggregate across trials
        scores = [ts["score"] for ts in trial_scores]
        case_grade = {
            "case_id": case_id,
            "split": split,
            "tags": case.get("tags", []),
            "difficulty": case.get("difficulty", "unknown"),
            "mean_score": round(statistics.mean(scores), 4) if scores else 0.0,
            "stddev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
            "trials": trial_scores,
        }
        case_grades.append(case_grade)

    # Split into train/test
    train_grades = [cg for cg in case_grades if cg["split"] == "train"]
    test_grades = [cg for cg in case_grades if cg["split"] == "test"]

    train_scores = score_suite(
        [{"score": cg["mean_score"]} for cg in train_grades]
    )
    test_scores = score_suite(
        [{"score": cg["mean_score"]} for cg in test_grades]
    )

    output = {
        "timestamp": results_data.get("timestamp", ""),
        "skill_hash": results_data.get("skill_hash", ""),
        "train_score": train_scores["mean"],
        "test_score": test_scores["mean"],
        "train_test_gap": round(abs(train_scores["mean"] - test_scores["mean"]), 4),
        "train_details": train_scores,
        "test_details": test_scores,
        "cases": case_grades,
    }

    # Write grades
    out_dir = output_dir or os.path.dirname(results_path)
    grades_path = os.path.join(out_dir, "grades.json")
    with open(grades_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Train score: {train_scores['mean']:.4f} (+/- {train_scores['stddev']:.4f})")
    print(f"Test score:  {test_scores['mean']:.4f} (+/- {test_scores['stddev']:.4f})")
    print(f"Train-test gap: {output['train_test_gap']:.4f}")
    print(f"Grades written to {grades_path}")

    return output


def main():
    parser = argparse.ArgumentParser(description="Grade QRSPI eval results")
    parser.add_argument("--results", required=True, help="Path to results.json")
    parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
    parser.add_argument("--output", help="Output directory (default: same as results)")
    args = parser.parse_args()

    grade_results(args.results, args.suite, args.output)


if __name__ == "__main__":
    main()
