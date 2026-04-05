#!/usr/bin/env python3
"""Diagnose eval failures and identify root causes.

Analyzes grading results, categorizes failures, and produces a
structured diagnosis for the revision agent.
"""

import argparse
import json
import os
from typing import Optional


# Failure categories
CATEGORIES = {
    "MISSING_INSTRUCTION": "Skill doesn't tell agent to do X",
    "CONFLICTING_INSTRUCTION": "Skill says A but case needs B",
    "OVER_CONSTRAINED": "Skill is too rigid for this edge case",
    "UNDER_SPECIFIED": "Skill is too vague, agent guesses wrong",
    "TOOL_MISUSE": "Agent uses wrong tool or wrong sequence",
    "CONTEXT_LOSS": "Agent loses track over long workflows",
    "MODEL_LIMITATION": "Not addressable via prompt changes",
    "EVAL_ISSUE": "The eval case or assertion is flawed",
}


def extract_failures(grades: dict) -> list:
    """Extract failed cases with their details."""
    failures = []
    for case in grades.get("cases", []):
        if case["mean_score"] >= 0.9:
            continue

        failed_assertions = []
        # Look at first trial for assertion details
        if case.get("trials"):
            for assertion in case["trials"][0].get("assertions", []):
                if assertion.get("passed") is False:
                    failed_assertions.append({
                        "check": assertion["check"],
                        "type": assertion["type"],
                        "evidence": assertion.get("evidence", ""),
                        "weight": assertion.get("weight", 1.0),
                    })

        failures.append({
            "case_id": case["case_id"],
            "score": case["mean_score"],
            "variance": case.get("stddev", 0),
            "tags": case.get("tags", []),
            "difficulty": case.get("difficulty", "unknown"),
            "failed_assertions": failed_assertions,
        })

    return sorted(failures, key=lambda f: f["score"])


def categorize_failure(failure: dict, skill_text: str) -> dict:
    """Categorize a failure based on assertion types and evidence.

    In a real implementation, this would use a meta-agent (LLM) to
    analyze the failure transcript against the skill text:

        response = meta_agent.complete(
            system=DIAGNOSIS_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Skill: {skill_text}\nFailure: {json.dumps(failure)}"
            }]
        )

    This stub uses heuristics for common patterns.
    """
    categories = []

    for fa in failure.get("failed_assertions", []):
        check = fa.get("check", "")
        evidence = fa.get("evidence", "")

        if "not found" in evidence.lower():
            categories.append("MISSING_INSTRUCTION")
        elif "solution language" in check.lower() or "no_solution" in check:
            categories.append("OVER_CONSTRAINED")
        elif fa["type"] == "llm_judge":
            categories.append("UNDER_SPECIFIED")
        else:
            categories.append("MISSING_INSTRUCTION")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in categories:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return {
        "case_id": failure["case_id"],
        "score": failure["score"],
        "categories": unique,
        "failed_assertions": failure["failed_assertions"],
        "regression_risk": "low" if failure["difficulty"] == "hard" else "medium",
    }


def produce_diagnosis(
    grades_path: str,
    skill_path: str,
    output_path: str,
) -> dict:
    """Produce a full diagnosis of eval failures."""
    with open(grades_path) as f:
        grades = json.load(f)
    with open(skill_path) as f:
        skill_text = f.read()

    failures = extract_failures(grades)
    if not failures:
        diagnosis = {
            "status": "ALL_PASSING",
            "message": "No failures detected — all cases above 0.9 threshold",
            "failures": [],
            "recommendations": [],
        }
    else:
        categorized = [categorize_failure(f, skill_text) for f in failures]

        # Group by category for recommendations
        by_category = {}
        for cf in categorized:
            for cat in cf["categories"]:
                by_category.setdefault(cat, []).append(cf["case_id"])

        recommendations = []
        for cat, case_ids in by_category.items():
            recommendations.append({
                "category": cat,
                "description": CATEGORIES.get(cat, "Unknown"),
                "affected_cases": case_ids,
                "suggested_action": _suggest_action(cat, len(case_ids)),
            })

        diagnosis = {
            "status": "FAILURES_DETECTED",
            "total_failures": len(failures),
            "worst_score": failures[0]["score"] if failures else None,
            "failures": categorized,
            "recommendations": recommendations,
            "non_prompt_issues": [
                cf for cf in categorized
                if "MODEL_LIMITATION" in cf["categories"]
                or "EVAL_ISSUE" in cf["categories"]
            ],
        }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(diagnosis, f, indent=2)

    print(f"Diagnosis: {diagnosis['status']}")
    if failures:
        print(f"  Failures: {len(failures)}")
        for r in diagnosis.get("recommendations", []):
            print(f"  [{r['category']}] {r['description']} — {len(r['affected_cases'])} cases")
    print(f"Written to {output_path}")

    return diagnosis


def _suggest_action(category: str, count: int) -> str:
    """Suggest a revision action based on failure category."""
    actions = {
        "MISSING_INSTRUCTION": "Add explicit instruction to skill prompt covering the missing behavior",
        "CONFLICTING_INSTRUCTION": "Resolve contradiction — remove or qualify the conflicting rule",
        "OVER_CONSTRAINED": "Relax the constraint or add an exception clause for this case type",
        "UNDER_SPECIFIED": "Add specificity — replace vague phrasing with concrete expected behavior",
        "TOOL_MISUSE": "Add tool selection guidance or worked examples to the skill prompt",
        "CONTEXT_LOSS": "Add checkpoint/summary instructions for long workflows",
        "MODEL_LIMITATION": "Not addressable via prompt — consider tool or architecture changes",
        "EVAL_ISSUE": "Review and fix the eval case — assertion may be flawed",
    }
    return actions.get(category, "Manual review required")


def main():
    parser = argparse.ArgumentParser(description="Diagnose QRSPI eval failures")
    parser.add_argument("--grades", required=True, help="Path to grades.json")
    parser.add_argument("--skill", required=True, help="Path to skill/agent prompt")
    parser.add_argument("--output", required=True, help="Output path for diagnosis.json")
    args = parser.parse_args()

    produce_diagnosis(args.grades, args.skill, args.output)


if __name__ == "__main__":
    main()
