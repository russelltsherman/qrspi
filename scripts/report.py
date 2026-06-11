#!/usr/bin/env python3
"""Generate iteration reports from eval results.

Produces a summary report comparing versions, tracking score progression,
and flagging regressions.
"""

import argparse
import json
import os
from pathlib import Path


def load_version_results(results_dir: str) -> list:
    """Load all version results from the results directory."""
    versions = []
    results_path = Path(results_dir)

    for version_dir in sorted(results_path.iterdir()):
        if not version_dir.is_dir():
            continue
        grades_path = version_dir / "grades.json"
        if grades_path.exists():
            with open(grades_path) as f:
                grades = json.load(f)
            versions.append({
                "version": version_dir.name,
                "path": str(version_dir),
                "grades": grades,
            })

    return versions


def detect_regressions(current: dict, previous: dict) -> list:
    """Detect per-case regressions between versions."""
    regressions = []
    prev_cases = {c["case_id"]: c for c in previous.get("cases", [])}
    curr_cases = {c["case_id"]: c for c in current.get("cases", [])}

    for case_id, curr in curr_cases.items():
        prev = prev_cases.get(case_id)
        if prev is None:
            continue
        drop = prev["mean_score"] - curr["mean_score"]
        if drop > 0.2:  # More than 1 point on 5-point scale
            regressions.append({
                "case_id": case_id,
                "previous_score": prev["mean_score"],
                "current_score": curr["mean_score"],
                "drop": round(drop, 4),
            })

    return regressions


# Version-level test_score drop beyond this triggers a regression alert (AC4, ref Q15).
VERSION_SCORE_DROP_THRESHOLD = 0.05


def build_ledger_entry(
    version: dict, parent: str, regressions: list, previous_grades: dict = None
) -> dict:
    """Build a ledger entry for the version history.

    When ``previous_grades`` is supplied, computes the version-level ``test_score``
    delta from the prior version and flags a ``version_score_regression`` when the
    drop exceeds ``VERSION_SCORE_DROP_THRESHOLD`` (0.05). This complements the
    per-case 0.2 guard in ``detect_regressions`` (AC4, ref Q15).
    """
    grades = version["grades"]
    improvements = []
    if parent:
        # Identify cases that improved
        pass  # Would compare against parent

    test_score = grades.get("test_score", 0)
    version_score_drop = 0
    version_score_regression = False
    if previous_grades:
        version_score_drop = round(previous_grades.get("test_score", 0) - test_score, 4)
        version_score_regression = version_score_drop > VERSION_SCORE_DROP_THRESHOLD

    return {
        "version": version["version"],
        "timestamp": grades.get("timestamp", ""),
        "parent": parent,
        "train_score": grades.get("train_score", 0),
        "test_score": test_score,
        "train_test_gap": grades.get("train_test_gap", 0),
        "regressions": regressions,
        "regression_count": len(regressions),
        "version_score_drop": version_score_drop,
        "version_score_regression": version_score_regression,
    }


def check_promotion_criteria(entry: dict, previous_entry: dict) -> dict:
    """Check if a version meets promotion criteria."""
    criteria = {
        "test_score_no_regression": (
            entry["test_score"] >= previous_entry.get("test_score", 0)
        ),
        "no_large_case_drops": entry["regression_count"] == 0,
        "acceptable_gap": entry["train_test_gap"] <= 0.1,
    }
    promoted = all(criteria.values())
    return {
        "promoted": promoted,
        "criteria": criteria,
    }


def generate_report(results_dir: str, output_path: str) -> dict:
    """Generate a full iteration report."""
    versions = load_version_results(results_dir)

    if not versions:
        report = {"status": "NO_RESULTS", "message": "No version results found"}
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print("No results found.")
        return report

    # Build ledger
    ledger = []
    for i, version in enumerate(versions):
        parent = versions[i - 1]["version"] if i > 0 else None
        prev_grades = versions[i - 1]["grades"] if i > 0 else {}
        regressions = detect_regressions(version["grades"], prev_grades) if prev_grades else []
        entry = build_ledger_entry(version, parent, regressions, prev_grades)

        if i > 0:
            prev_entry = ledger[-1]
            entry["promotion"] = check_promotion_criteria(entry, prev_entry)
        else:
            entry["promotion"] = {"promoted": True, "criteria": {"baseline": True}}

        ledger.append(entry)

    # Summary
    latest = ledger[-1]
    best_test = max(e["test_score"] for e in ledger)
    score_trajectory = [e["test_score"] for e in ledger]

    # Detect plateau (last 3 versions within 0.01)
    plateau = False
    if len(score_trajectory) >= 3:
        recent = score_trajectory[-3:]
        plateau = (max(recent) - min(recent)) < 0.01

    # Detect overfitting (train-test gap growing)
    overfitting = False
    if len(ledger) >= 2:
        gaps = [e["train_test_gap"] for e in ledger]
        overfitting = len(gaps) >= 3 and gaps[-1] > gaps[-2] > gaps[-3]

    report = {
        "generated": versions[-1]["grades"].get("timestamp", ""),
        "total_versions": len(versions),
        "latest_version": latest["version"],
        "latest_train_score": latest["train_score"],
        "latest_test_score": latest["test_score"],
        "best_test_score": best_test,
        "score_trajectory": score_trajectory,
        "alerts": {
            "plateau": plateau,
            "overfitting": overfitting,
            "has_regressions": latest["regression_count"] > 0,
            "version_score_regression": latest.get("version_score_regression", False),
        },
        "ledger": ledger,
    }

    # Write report
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"=== Eval Report ({len(versions)} versions) ===")
    print(f"Latest: {latest['version']}")
    print(f"  Train: {latest['train_score']:.4f}")
    print(f"  Test:  {latest['test_score']:.4f}")
    print(f"  Gap:   {latest['train_test_gap']:.4f}")
    print(f"  Best test ever: {best_test:.4f}")
    if plateau:
        print("  ALERT: Score plateau detected — consider new eval cases or approach")
    if overfitting:
        print("  ALERT: Train-test gap increasing — possible overfitting")
    if latest.get("version_score_regression"):
        print(
            f"  ALERT: test_score dropped {latest['version_score_drop']:.4f} "
            f"from prior version (> {VERSION_SCORE_DROP_THRESHOLD})"
        )
    print(f"Report written to {output_path}")

    return report


# Also write the ledger.json for the regression guard
def update_ledger(results_dir: str):
    """Update the persistent ledger.json."""
    versions = load_version_results(results_dir)
    ledger_path = os.path.join(results_dir, "ledger.json")

    ledger = []
    for i, version in enumerate(versions):
        parent = versions[i - 1]["version"] if i > 0 else None
        prev_grades = versions[i - 1]["grades"] if i > 0 else {}
        regressions = detect_regressions(version["grades"], prev_grades) if prev_grades else []
        entry = build_ledger_entry(version, parent, regressions, prev_grades)
        ledger.append(entry)

    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    print(f"Ledger updated: {ledger_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate QRSPI eval report")
    parser.add_argument("--results-dir", required=True, help="Directory containing version results")
    parser.add_argument("--output", required=True, help="Output path for report")
    args = parser.parse_args()

    generate_report(args.results_dir, args.output)
    update_ledger(args.results_dir)


if __name__ == "__main__":
    main()
