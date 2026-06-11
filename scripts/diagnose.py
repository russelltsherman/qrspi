#!/usr/bin/env python3
"""Diagnose eval failures and identify root causes.

Analyzes grading results, categorizes failures, and produces a
structured diagnosis for the revision agent.
"""

import argparse
import json
import os
import sys
from typing import Optional

import meta_agent


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


DIAGNOSIS_SYSTEM_PROMPT = (
    "You are a skill-evaluation diagnostician. Given a skill prompt and the "
    "evidence from a single failing eval case, classify the ROOT CAUSE of the "
    "failure into exactly one category and justify it with quoted evidence.\n\n"
    "The category MUST be one of:\n"
    + "\n".join("  - %s: %s" % (k, v) for k, v in CATEGORIES.items())
    + "\n\nRespond with ONLY a JSON object of the form "
    '{"category": "<ONE_CATEGORY>", "rationale": "<one or two sentences that '
    'quote the failure evidence>"}. No prose, no code fences."'
)


def _build_diagnosis_user_prompt(failure: dict, skill_text: str) -> str:
    """Assemble the user-prompt half for the diagnosis meta-agent call. Pure."""
    return (
        "Skill prompt under evaluation:\n"
        "-----\n"
        "%s\n"
        "-----\n\n"
        "Failing eval case evidence (JSON):\n"
        "%s\n\n"
        "Classify the root cause and quote the evidence."
        % (skill_text, json.dumps(failure, indent=2))
    )


def _parse_diagnosis_response(text: str) -> Optional[dict]:
    """Parse the meta-agent text into {category, rationale}, or None on failure.

    Defensive (plan §2.9, ref Q3): a NO_RESULT/empty/unparseable return, or a
    category outside CATEGORIES, yields None so the caller falls back to a
    no-category diagnosis instead of crashing the loop.
    """
    if not text or not text.strip():
        return None
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    category = parsed.get("category")
    if category not in CATEGORIES:
        return None
    rationale = parsed.get("rationale", "")
    return {"category": category, "rationale": rationale if isinstance(rationale, str) else ""}


def categorize_failure(failure: dict, skill_text: str) -> dict:
    """Categorize a failure via the meta-agent, grounded in failure evidence.

    Decision 1 / AC1 (structure §Contracts, plan §2.7): invokes the shared
    `meta_agent.complete` seam with the full skill text plus the failing-case
    evidence and parses a grounded `{category, rationale}` where
    `category ∈ CATEGORIES` and `rationale` quotes the failure evidence.

    The return preserves the keys `produce_diagnosis` consumes — `case_id`,
    `score`, `categories` (a single-element list holding the grounded category so
    the downstream group-by-category recommendation assembly is unchanged),
    `failed_assertions`, `regression_risk` — and adds the grounded `category` /
    `rationale` fields.

    Defensive (plan §2.9, ref Q3): a NO_RESULT/empty/unparseable meta-agent
    return is logged and degraded to a no-category result (`category=None`,
    empty `categories`) rather than raising into the `set -euo pipefail` loop.
    """
    text = meta_agent.complete(
        DIAGNOSIS_SYSTEM_PROMPT,
        _build_diagnosis_user_prompt(failure, skill_text),
    )
    parsed = _parse_diagnosis_response(text)

    if parsed is None:
        print(
            "diagnose: no usable categorization for case %s "
            "(empty/unparseable meta-agent result); falling back to no-category"
            % failure.get("case_id"),
            file=sys.stderr,
        )
        category = None
        rationale = ""
        categories = []
    else:
        category = parsed["category"]
        rationale = parsed["rationale"]
        categories = [category]

    return {
        "case_id": failure["case_id"],
        "score": failure["score"],
        "category": category,
        "rationale": rationale,
        "categories": categories,
        "failed_assertions": failure["failed_assertions"],
        "regression_risk": "low" if failure["difficulty"] == "hard" else "medium",
    }


def produce_diagnosis(
    grades_path: str,
    skill_path: str,
    output_path: str,
    dry_run: bool = False,
) -> dict:
    """Produce a full diagnosis of eval failures.

    `dry_run` (plan §2.10, ref Q9): the diagnosis file is the single permitted
    side effect of this stage, so a dry run still writes `output_path` (the
    diagnosis itself) but performs no other side effects. The flag is threaded so
    any future side effect added here is suppressed under `--dry-run`.
    """
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

    print(f"Diagnosis: {diagnosis['status']}{' (dry-run)' if dry_run else ''}")
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit the diagnosis with no side effects beyond the diagnosis file",
    )
    args = parser.parse_args()

    produce_diagnosis(args.grades, args.skill, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
