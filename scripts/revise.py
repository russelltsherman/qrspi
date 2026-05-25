#!/usr/bin/env python3
"""Generate targeted skill revisions based on failure diagnosis.

Produces minimal, surgical edits to agent prompts — not full rewrites.
Each edit is traceable to specific failure cases.
"""

import argparse
import json
import os
import re
import time
from typing import Optional


def load_diagnosis(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_skill(path: str) -> str:
    with open(path) as f:
        return f.read()


def propose_revisions(
    skill_text: str,
    diagnosis: dict,
) -> list:
    """Propose targeted edits to the skill text.

    In a real implementation, this calls a meta-agent:

        response = meta_agent.complete(
            system=REVISION_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Skill:\\n{skill_text}\\n\\nDiagnosis:\\n{json.dumps(diagnosis)}"
            }]
        )

    The meta-agent returns structured edits that are applied as diffs.
    This stub generates the revision request structure.
    """
    revisions = []

    for rec in diagnosis.get("recommendations", []):
        category = rec["category"]

        # Skip non-prompt-addressable issues
        if category in ("MODEL_LIMITATION", "EVAL_ISSUE"):
            continue

        revision = {
            "id": f"rev_{len(revisions) + 1}",
            "category": category,
            "affected_cases": rec["affected_cases"],
            "action": rec["suggested_action"],
            "edit": {
                "type": "pending_meta_agent",
                "description": (
                    f"Meta-agent should propose a specific edit to address "
                    f"{category} affecting cases: {', '.join(rec['affected_cases'])}"
                ),
                "old_text": None,
                "new_text": None,
            },
            "regression_risk": _assess_risk(category, len(rec["affected_cases"]), skill_text),
        }
        revisions.append(revision)

    return revisions


def apply_revisions(skill_text: str, revisions: list) -> tuple[str, list]:
    """Apply approved revisions to the skill text.

    Only applies revisions that have concrete old_text/new_text edits.
    Returns the modified text and a log of applied changes.
    """
    modified = skill_text
    applied = []

    for rev in revisions:
        edit = rev.get("edit", {})
        old_text = edit.get("old_text")
        new_text = edit.get("new_text")

        if old_text and new_text and old_text in modified:
            modified = modified.replace(old_text, new_text, 1)
            applied.append({
                "id": rev["id"],
                "status": "applied",
                "description": edit.get("description", ""),
            })
        elif old_text and old_text not in modified:
            applied.append({
                "id": rev["id"],
                "status": "skipped",
                "reason": "old_text not found in skill",
            })
        else:
            applied.append({
                "id": rev["id"],
                "status": "pending",
                "reason": "No concrete edit — requires meta-agent",
            })

    return modified, applied


def _assess_risk(category: str, affected_count: int, skill_text: str) -> str:
    """Assess regression risk of a proposed edit."""
    if category == "MISSING_INSTRUCTION":
        return "low"  # Adding new instruction rarely breaks existing behavior
    elif category == "CONFLICTING_INSTRUCTION":
        return "high"  # Changing existing rules can break passing cases
    elif category == "OVER_CONSTRAINED":
        return "medium"  # Relaxing constraints may cause new failures
    elif category == "UNDER_SPECIFIED":
        return "low"  # Adding specificity rarely hurts
    return "medium"


def revise_skill(
    skill_path: str,
    diagnosis_path: str,
    output_path: str,
    dry_run: bool = False,
) -> dict:
    """Main revision pipeline."""
    skill_text = load_skill(skill_path)
    diagnosis = load_diagnosis(diagnosis_path)

    if diagnosis.get("status") == "ALL_PASSING":
        print("No failures — no revisions needed.")
        return {"status": "no_changes", "revisions": []}

    revisions = propose_revisions(skill_text, diagnosis)

    if dry_run:
        result = {
            "status": "dry_run",
            "revisions": revisions,
            "skill_path": skill_path,
        }
    else:
        modified_text, applied_log = apply_revisions(skill_text, revisions)

        # Only write if something actually changed
        if modified_text != skill_text:
            with open(output_path, "w") as f:
                f.write(modified_text)
            print(f"Skill updated: {output_path}")
        else:
            print("No concrete edits to apply — revisions require meta-agent integration.")

        result = {
            "status": "revised" if modified_text != skill_text else "pending_meta_agent",
            "revisions": revisions,
            "applied": applied_log,
            "output_path": output_path,
        }

    # Write revision log
    log_path = os.path.join(os.path.dirname(output_path) or ".", "revision-log.json")
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "skill_path": skill_path,
        "diagnosis_path": diagnosis_path,
        **result,
    }

    # Append to log
    log = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            log = json.load(f)
    log.append(log_entry)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    print(f"Revision log: {log_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Revise QRSPI agent prompts")
    parser.add_argument("--skill", required=True, help="Path to skill/agent prompt")
    parser.add_argument("--diagnosis", required=True, help="Path to diagnosis.json")
    parser.add_argument("--output", required=True, help="Output path for revised skill")
    parser.add_argument("--dry-run", action="store_true", help="Show proposed changes without applying")
    args = parser.parse_args()

    revise_skill(args.skill, args.diagnosis, args.output, args.dry_run)


if __name__ == "__main__":
    main()
