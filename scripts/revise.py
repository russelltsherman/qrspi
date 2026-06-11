#!/usr/bin/env python3
"""Generate targeted skill revisions based on failure diagnosis.

Produces minimal, surgical edits to agent prompts — not full rewrites.
Each edit is traceable to specific failure cases.
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Optional

import meta_agent


def load_diagnosis(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_skill(path: str) -> str:
    with open(path) as f:
        return f.read()


REVISION_SYSTEM_PROMPT = (
    "You are a skill-prompt revision agent. Given a skill prompt and a structured "
    "diagnosis of why eval cases failed, propose minimal, surgical edits to the "
    "skill prompt — never a full rewrite. Each edit MUST be anchored to text that "
    "appears VERBATIM and EXACTLY ONCE in the skill prompt.\n\n"
    "Respond with ONLY a JSON array of edit objects, each of the form "
    '{"old_text": "<exact substring to replace, copied verbatim from the skill>", '
    '"new_text": "<the replacement text>", "description": "<one sentence on what '
    'this edit fixes and which failure category it addresses>"}. '
    "To insert new guidance, set old_text to an existing unique anchor line and "
    "make new_text that line plus your addition. Return [] if no prompt edit can "
    "address the diagnosis. No prose, no code fences."
)


def _build_revision_user_prompt(skill_text: str, diagnosis: dict) -> str:
    """Assemble the user-prompt half for the revision meta-agent call. Pure."""
    return (
        "Skill prompt to revise:\n"
        "-----\n"
        "%s\n"
        "-----\n\n"
        "Failure diagnosis (JSON):\n"
        "%s\n\n"
        "Propose minimal anchored edits to fix the prompt-addressable failures."
        % (skill_text, json.dumps(diagnosis, indent=2))
    )


def _parse_revision_response(text: str) -> Optional[list]:
    """Parse the meta-agent text into a list of EditProposal dicts, or None.

    Defensive (plan §3.14, ref Q3, mirrors diagnose._parse_diagnosis_response):
    a NO_RESULT/empty/unparseable return, or a payload that is not a JSON array of
    well-formed edit objects, yields None so the caller falls back to "no edits"
    instead of crashing the `set -euo pipefail` loop. Each accepted edit must carry
    non-empty string `old_text` and `new_text`; `description` defaults to "".
    """
    if not text or not text.strip():
        return None
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, list):
        return None
    edits = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        old_text = item.get("old_text")
        new_text = item.get("new_text")
        if not isinstance(old_text, str) or not old_text:
            continue
        if not isinstance(new_text, str) or not new_text:
            continue
        description = item.get("description", "")
        edits.append({
            "old_text": old_text,
            "new_text": new_text,
            "description": description if isinstance(description, str) else "",
        })
    return edits


def propose_revisions(
    skill_text: str,
    diagnosis: dict,
) -> list:
    """Propose concrete, anchored edits to the skill text via the meta-agent.

    AC2 / Decision 2 (structure §Contracts, plan §3.14): invokes the shared
    `meta_agent.complete` seam with the skill text + diagnosis and parses concrete
    `{old_text, new_text, description}` EditProposals anchored in the actual skill
    content — replacing the old `pending_meta_agent` placeholder construction.

    Non-prompt-addressable categories (`MODEL_LIMITATION`, `EVAL_ISSUE`) are
    stripped from the diagnosis handed to the meta-agent so it only proposes
    prompt edits. Each parsed EditProposal is wrapped into the revision record
    shape `apply_revisions`/`revise_skill` consume (id, category, edit, etc.).

    Defensive (plan §3.14, ref Q3): a NO_RESULT/empty/unparseable meta-agent
    return is logged and degraded to an empty revision list rather than raising.
    """
    addressable = [
        rec for rec in diagnosis.get("recommendations", [])
        if rec.get("category") not in ("MODEL_LIMITATION", "EVAL_ISSUE")
    ]
    # Nothing prompt-addressable -> no model invocation, no edits.
    if not addressable:
        return []

    sub_diagnosis = dict(diagnosis)
    sub_diagnosis["recommendations"] = addressable

    text = meta_agent.complete(
        REVISION_SYSTEM_PROMPT,
        _build_revision_user_prompt(skill_text, sub_diagnosis),
    )
    proposals = _parse_revision_response(text)

    if not proposals:
        if proposals is None:
            print(
                "revise: no usable edits (empty/unparseable meta-agent result); "
                "falling back to no revisions",
                file=sys.stderr,
            )
        return []

    # Map each EditProposal back onto the addressable recommendations for
    # category/affected-case provenance (best-effort: index-aligned, falling back
    # to the first addressable recommendation when the model returns more or fewer
    # edits than recommendations).
    revisions = []
    for i, proposal in enumerate(proposals):
        rec = addressable[i] if i < len(addressable) else addressable[0]
        category = rec.get("category", "UNDER_SPECIFIED")
        affected = rec.get("affected_cases", [])
        revisions.append({
            "id": f"rev_{len(revisions) + 1}",
            "category": category,
            "affected_cases": affected,
            "action": rec.get("suggested_action", ""),
            "edit": {
                "type": "concrete",
                "description": proposal["description"],
                "old_text": proposal["old_text"],
                "new_text": proposal["new_text"],
            },
            "regression_risk": _assess_risk(category, len(affected), skill_text),
        })

    return revisions


def verify_anchor(skill_text: str, old_text: str) -> dict:
    """Confirm `old_text` is present and unique in `skill_text` before applying.

    Decision 3 (structure §Contracts, plan §3.15): returns an `AnchorCheck`
    `{ok, reason}` where `reason ∈ {"missing", "ambiguous", "ok"}`:

      - "missing"   if `old_text` does not occur in the skill (or is empty);
      - "ambiguous" if it occurs more than once (first-occurrence replace would be
        non-deterministic / could mis-write the skill);
      - "ok"        if it occurs exactly once.

    Lives in the revise layer so `apply_revisions`' contract stays unchanged; the
    caller skips + logs any non-`ok` edit so the skill is never mis-written.
    """
    if not old_text:
        return {"ok": False, "reason": "missing"}
    count = skill_text.count(old_text)
    if count == 0:
        return {"ok": False, "reason": "missing"}
    if count > 1:
        return {"ok": False, "reason": "ambiguous"}
    return {"ok": True, "reason": "ok"}


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

    # Pre-apply anchor verification (Decision 3, plan §3.16): skip + log any edit
    # whose anchor is missing or ambiguous so the skill is never mis-written; only
    # `ok` edits are handed to the (mechanically unchanged) apply_revisions pass.
    verified, anchor_log = _verify_anchors(skill_text, revisions)

    if dry_run:
        # Read-only under --dry-run (plan §3.19): emit the proposal + anchor checks
        # without applying, writing the skill, OR mutating revision-log.json.
        result = {
            "status": "dry_run",
            "revisions": revisions,
            "anchor_checks": anchor_log,
            "skill_path": skill_path,
        }
        return result

    modified_text, applied_log = apply_revisions(skill_text, verified)

    # Only write if something actually changed
    if modified_text != skill_text:
        with open(output_path, "w") as f:
            f.write(modified_text)
        print(f"Skill updated: {output_path}")
    else:
        print("No applicable edits — skill left unchanged.")

    result = {
        "status": "revised" if modified_text != skill_text else "no_changes",
        "revisions": revisions,
        "applied": applied_log,
        "anchor_checks": anchor_log,
        "output_path": output_path,
    }

    # Write revision log (only on a non-dry-run pass — see early return above).
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


def _verify_anchors(skill_text: str, revisions: list) -> tuple[list, list]:
    """Run verify_anchor per proposed edit (plan §3.16).

    Returns `(verified, anchor_log)` where `verified` is the subset of revisions
    whose anchor check is `ok` (the only edits passed to apply_revisions), and
    `anchor_log` records every revision's `{id, reason, ok}` so skipped
    missing/ambiguous edits are surfaced. A non-`ok` edit is logged to stderr and
    excluded so the skill is never mis-written.
    """
    verified = []
    anchor_log = []
    for rev in revisions:
        old_text = rev.get("edit", {}).get("old_text")
        check = verify_anchor(skill_text, old_text)
        anchor_log.append({"id": rev.get("id"), "ok": check["ok"], "reason": check["reason"]})
        if check["ok"]:
            verified.append(rev)
        else:
            print(
                "revise: skipping edit %s — anchor %s"
                % (rev.get("id"), check["reason"]),
                file=sys.stderr,
            )
    return verified, anchor_log


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
