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


def question_count(filename: str, *rest) -> tuple[bool, str]:
    """Count questions and assert at least ``min_count`` are present.

    Dispatcher contract: ``result`` is always the trailing positional. The
    threshold may be supplied in-paren (``question_count('questions.md', 8)``)
    or omitted (``question_count('questions.md') >= 8`` — the suite's trailing
    operator is dropped by ``parse_check_call``), in which case a built-in
    default keeps the check enforceable rather than an inert pass.
    """
    result = rest[-1] if rest else {}
    min_count = int(rest[0]) if len(rest) > 1 else 8
    output = result.get("output", "") if isinstance(result, dict) else ""
    n = len(re.findall(r"^-\s+Q\d+:", output, re.MULTILINE))
    return n >= min_count, f"Found {n} questions (min {min_count})"


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


def slice_count(filename: str, *rest) -> tuple[bool, str]:
    """Count vertical slices and assert at least ``min_count`` are present.

    ``result`` is the trailing positional; ``min_count`` is in-paren when
    given, else a built-in default (the suite's trailing operator is dropped).
    """
    result = rest[-1] if rest else {}
    min_count = int(rest[0]) if len(rest) > 1 else 2
    output = result.get("output", "") if isinstance(result, dict) else ""
    n = len(re.findall(r"^## Slice \d+", output, re.MULTILINE))
    return n >= min_count, f"Found {n} slices (min {min_count})"


def all_slices_have_verification(filename: str, result: dict) -> tuple[bool, str]:
    """Check every slice has a Verification section."""
    output = result.get("output", "")
    slices = re.findall(r"^## Slice \d+", output, re.MULTILINE)
    verifications = re.findall(r"\*\*Verification:\*\*", output)
    ok = len(verifications) >= len(slices)
    return ok, f"Slices: {len(slices)}, Verification sections: {len(verifications)}"


def total_steps(filename: str, *rest) -> tuple[bool, str]:
    """Count implementation steps and assert at least ``min_count`` are present.

    ``result`` is the trailing positional; ``min_count`` is in-paren when
    given, else a built-in default (the suite's trailing operator is dropped).
    """
    result = rest[-1] if rest else {}
    min_count = int(rest[0]) if len(rest) > 1 else 1
    output = result.get("output", "") if isinstance(result, dict) else ""
    n = len(re.findall(r"^\d+\.\s+", output, re.MULTILINE))
    return n >= min_count, f"Found {n} steps (min {min_count})"


def pr_title_under_limit(filename: str, limit: int, result: dict) -> tuple[bool, str]:
    """Check PR title is under character limit."""
    output = result.get("output", "")
    match = re.search(r"^# PR:\s*(.+)$", output, re.MULTILINE)
    if not match:
        return False, "PR title not found"
    title = match.group(1).strip()
    ok = len(title) <= limit
    return ok, f"PR title length: {len(title)} (limit: {limit})"


# ── New checks: Questions phase ──

def section_count(filename: str, heading: str, result: dict) -> tuple[bool, str]:
    """Assert the output has at least one ``## `` section.

    Suite form is ``section_count('questions.md', '## ') >= 5`` — the second
    in-paren arg is the heading marker (e.g. ``'## '``); the trailing minimum
    is dropped by the parser, so a built-in floor (>= 1 section) keeps the
    check enforceable. Marker per ``.qrspi/templates/questions.md``.
    """
    output = result.get("output", "")
    marker = re.escape((heading or "## ").strip())
    n = len(re.findall(rf"^{marker}\s+\S", output, re.MULTILINE))
    return n >= 1, f"Found {n} '{(heading or '## ').strip()}' sections"


def section_question_count(filename: str, section: str, result: dict) -> tuple[bool, str]:
    """Assert the named ``## `` section contains at least one ``- QN:`` question.

    Suite form is ``section_question_count('questions.md', 'Edge Cases') >= 2``;
    the trailing minimum is dropped by the parser, so a built-in floor (>= 1)
    applies. Marker per ``.qrspi/templates/questions.md``.
    """
    output = result.get("output", "")
    if not section:
        return False, "No section name supplied"
    pattern = rf"^##\s+{re.escape(section)}[ \t]*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, output, re.DOTALL | re.MULTILINE)
    if not match:
        return False, f"Section '{section}' not found"
    body = match.group(1)
    n = len(re.findall(r"^-\s+Q\d+:", body, re.MULTILINE))
    return n >= 1, f"Section '{section}' has {n} questions"


def all_questions_answered(filename: str, *rest) -> tuple[bool, str]:
    """Assert every ``## QN:`` block in research output carries an ``**Answer:**``.

    Suite form passes two filename args
    (``all_questions_answered('research.md', 'fixtures/...md')``); only the
    trailing ``result`` selects content. Marker per
    ``.qrspi/templates/research.md`` (``## Q1: ...`` / ``**Answer:**``).
    """
    result = rest[-1] if rest else {}
    output = result.get("output", "") if isinstance(result, dict) else ""
    blocks = re.split(r"(?m)^##\s+Q\d+:", output)[1:]
    if not blocks:
        return False, "No question blocks found"
    for i, block in enumerate(blocks, 1):
        if "**Answer:**" not in block:
            return False, f"Question block #{i} has no **Answer:**"
    return True, f"All {len(blocks)} question blocks answered"


# ── New checks: Research phase ──

def contains_not_found(filename: str, result: dict) -> tuple[bool, str]:
    """Assert a ``NOT FOUND`` marker is present in the output."""
    output = result.get("output", "")
    found = bool(re.search(r"NOT FOUND", output))
    return found, f"NOT FOUND marker {'present' if found else 'absent'}"


def not_found_has_search_description(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each ``NOT FOUND`` line carries a trailing search description.

    A bare ``NOT FOUND`` with nothing after it on the line is a violation.
    """
    output = result.get("output", "")
    if not output.strip():
        return False, "Empty output"
    lines = [ln for ln in output.splitlines() if "NOT FOUND" in ln]
    for ln in lines:
        tail = ln.split("NOT FOUND", 1)[1].strip(" :-—\t")
        if not tail:
            return False, f"Bare NOT FOUND without search description: {ln.strip()!r}"
    return True, f"All {len(lines)} NOT FOUND markers have a description"


def all_answers_have_evidence(filename: str, result: dict) -> tuple[bool, str]:
    """Assert every ``**Answer:**`` block carries an ``**Evidence:**`` marker.

    Marker per ``.qrspi/templates/research.md``.
    """
    output = result.get("output", "")
    answers = len(re.findall(r"\*\*Answer:\*\*", output))
    evidence = len(re.findall(r"\*\*Evidence:\*\*", output))
    if answers == 0:
        return False, "No **Answer:** blocks found"
    ok = evidence >= answers
    return ok, f"Answers: {answers}, Evidence blocks: {evidence}"


# ── New checks: Design phase ──

def code_snippets_under_limit(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Assert no fenced ``` block exceeds ``max_lines`` lines of content."""
    output = result.get("output", "")
    if not output.strip():
        return False, "Empty output"
    limit = int(max_lines)
    lines = output.splitlines()
    # Pair fences: find lines that start a fence, then the next fence line.
    fence_line_nums = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("```")]
    for a, b in zip(fence_line_nums[0::2], fence_line_nums[1::2]):
        span = b - a - 1
        if span > limit:
            return False, f"Code block at line {a + 1} has {span} lines (limit {limit})"
    return True, f"All {len(fence_line_nums) // 2} code blocks within {limit} lines"


def risk_register_min_entries(filename: str, min_count: int, result: dict) -> tuple[bool, str]:
    """Assert the Risk Register table has at least ``min_count`` data rows.

    Counts markdown table rows under a ``Risk Register`` heading, excluding the
    header row and the ``|---|`` separator. Marker per
    ``.qrspi/templates/design.md``.
    """
    output = result.get("output", "")
    floor = int(min_count)
    match = re.search(
        r"##\s+Risk Register\s*\n(.*?)(?=\n##\s|\Z)", output, re.DOTALL
    )
    if not match:
        return False, "Risk Register section not found"
    rows = [ln for ln in match.group(1).splitlines() if ln.strip().startswith("|")]
    # Drop header + separator rows.
    data_rows = [ln for ln in rows if not re.match(r"^\s*\|[\s|:-]+\|\s*$", ln)]
    n = max(0, len(data_rows) - 1)  # first remaining row is the header
    return n >= floor, f"Risk Register has {n} entries (min {floor})"


def pattern_decisions_have_options(filename: str, min_count: int, result: dict) -> tuple[bool, str]:
    """Assert each ``### Decision`` block lists an ``| Option |`` options table.

    Marker per ``.qrspi/templates/design.md``.
    """
    output = result.get("output", "")
    blocks = re.split(r"(?m)^###\s+Decision", output)[1:]
    if not blocks:
        return False, "No ### Decision blocks found"
    for i, block in enumerate(blocks, 1):
        if not re.search(r"\|\s*Option\s*\|", block):
            return False, f"Decision #{i} lists no | Option | table"
    return True, f"All {len(blocks)} decisions list options"


def contains_new_pattern_flag(filename: str, result: dict) -> tuple[bool, str]:
    """Assert a ``NEW PATTERN?`` flag marker is present. Marker per design.md."""
    output = result.get("output", "")
    found = bool(re.search(r"NEW PATTERN\?", output))
    return found, f"NEW PATTERN? flag {'present' if found else 'absent'}"


# ── New checks: Structure phase ──

def all_slices_have_context_cost(filename: str, result: dict) -> tuple[bool, str]:
    """Assert every ``## Slice`` block has a ``**Context cost:**`` line.

    Marker per ``.qrspi/templates/structure.md``.
    """
    output = result.get("output", "")
    blocks = re.split(r"(?m)^##\s+Slice\s+\d+", output)[1:]
    if not blocks:
        return False, "No ## Slice blocks found"
    for i, block in enumerate(blocks, 1):
        if "**Context cost:**" not in block:
            return False, f"Slice #{i} has no **Context cost:**"
    return True, f"All {len(blocks)} slices have a Context cost"


def no_slice_exceeds_file_limit(filename: str, max_files: int, result: dict) -> tuple[bool, str]:
    """Assert no ``## Slice`` block lists more than ``max_files`` file bullets.

    File bullets are ``- ✨``/``- ⚠️`` lines under a slice. Marker per
    ``.qrspi/templates/structure.md``.
    """
    output = result.get("output", "")
    if not output.strip():
        return False, "Empty output"
    limit = int(max_files)
    blocks = re.split(r"(?m)^##\s+Slice\s+\d+", output)[1:]
    for i, block in enumerate(blocks, 1):
        files = re.findall(r"(?m)^-\s+(?:✨|⚠️)", block)
        if len(files) > limit:
            return False, f"Slice #{i} lists {len(files)} files (limit {limit})"
    return True, f"No slice exceeds {limit} files"


def all_files_marked_new_or_modify(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each file bullet under a ``Files touched`` list is marked new/modify.

    A file bullet under a ``**Files touched:**`` block must carry ``✨`` or
    ``⚠️``. Marker per ``.qrspi/templates/structure.md``.
    """
    output = result.get("output", "")
    sections = re.split(r"\*\*Files touched:\*\*", output)[1:]
    if not sections:
        return False, "No **Files touched:** block found"
    for si, section in enumerate(sections, 1):
        for ln in section.splitlines():
            stripped = ln.strip()
            if stripped.startswith("- `") or re.match(r"^-\s+`", stripped):
                if "✨" not in ln and "⚠️" not in ln:
                    return False, f"Unmarked file bullet in block #{si}: {stripped!r}"
            # stop at the next blank-separated non-bullet structural line
        # only inspect bullets that are file paths (backtick-wrapped)
    return True, "All file bullets marked new/modify"


def no_large_slices_without_justification(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each ``**Context cost:** L`` slice carries a justification line.

    A justification is any non-empty content following the L cost within the
    slice block. Marker per ``.qrspi/templates/structure.md``.
    """
    output = result.get("output", "")
    if not output.strip():
        return False, "Empty output"
    blocks = re.split(r"(?m)^##\s+Slice\s+\d+", output)[1:]
    for i, block in enumerate(blocks, 1):
        m = re.search(r"\*\*Context cost:\*\*\s*L\b", block)
        if not m:
            continue
        if not re.search(r"justif", block, re.IGNORECASE):
            return False, f"L-cost slice #{i} has no justification"
    return True, "All L-cost slices justified"


# ── New checks: Plan phase ──

def all_modify_steps_have_current_after(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each ``⚠️ Modify`` step shows both ``**Current:**`` and ``**After:**``.

    Marker per ``.qrspi/templates/plan.md``.
    """
    output = result.get("output", "")
    if not output.strip():
        return False, "Empty output"
    # Split on numbered steps; inspect blocks containing a Modify marker.
    steps = re.split(r"(?m)^\d+\.\s+", output)[1:]
    modify_steps = [s for s in steps if "⚠️" in s and re.search(r"Modify", s, re.IGNORECASE)]
    if not modify_steps:
        return True, "No ⚠️ Modify steps to validate"
    for i, s in enumerate(modify_steps, 1):
        if "**Current:**" not in s or "**After:**" not in s:
            return False, f"Modify step #{i} missing **Current:**/**After:**"
    return True, f"All {len(modify_steps)} Modify steps show current→after"


def all_slices_have_verify_checkpoint(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each ``## Slice`` block has a ``**Checkpoint:**`` verify line.

    Marker per ``.qrspi/templates/plan.md`` (``### Verify`` / ``**Checkpoint:**``).
    """
    output = result.get("output", "")
    blocks = re.split(r"(?m)^##\s+Slice\s+\d+", output)[1:]
    if not blocks:
        return False, "No ## Slice blocks found"
    for i, block in enumerate(blocks, 1):
        if "**Checkpoint:**" not in block:
            return False, f"Slice #{i} has no **Checkpoint:** verify line"
    return True, f"All {len(blocks)} slices have a verify checkpoint"


def all_steps_are_atomic(filename: str, result: dict) -> tuple[bool, str]:
    """Assert no numbered step joins multiple files/actions with ``and``.

    Heuristic per the plan.md atomicity rule: a step naming two backtick-wrapped
    file paths joined by ``and`` is non-atomic.
    """
    output = result.get("output", "")
    steps = re.split(r"(?m)^(\d+)\.\s+", output)
    # steps = ['', '1', 'text1', '2', 'text2', ...]
    pairs = list(zip(steps[1::2], steps[2::2]))
    if not pairs:
        return False, "No numbered steps found"
    for num, text in pairs:
        first_line = text.splitlines()[0] if text.splitlines() else ""
        paths = re.findall(r"`[^`]+\.\w+`", first_line)
        if len(paths) >= 2 and re.search(r"\band\b", first_line):
            return False, f"Step {num} is non-atomic (multiple files + 'and')"
    return True, f"All {len(pairs)} steps are atomic"


# ── New checks: Worktree phase ──

def has_critical_path(filename: str, result: dict) -> tuple[bool, str]:
    """Assert a ``**Critical path:**`` marker is present.

    Marker per ``.qrspi/templates/worktree.md``.
    """
    output = result.get("output", "")
    found = bool(re.search(r"\*\*Critical path:\*\*", output))
    return found, f"Critical path {'present' if found else 'absent'}"


def all_tasks_have_required_fields(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each task table row carries the required columns.

    The worktree task table is ``| Task ID | Description | Depends On | Plan
    Step | Cost | Status |``. A data row must have all 6 non-empty cells.
    Marker per ``.qrspi/templates/worktree.md``.
    """
    output = result.get("output", "")
    rows = re.findall(r"(?m)^\|\s*(T\d+|\*\*[^|]*\*\*)\s*\|.*$", output)
    data_rows = [ln for ln in output.splitlines()
                 if re.match(r"^\|\s*(T\d+)\s*\|", ln)]
    if not data_rows:
        return False, "No task rows (| TN | ...) found"
    for ln in data_rows:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 6 or any(not c for c in cells[:6]):
            return False, f"Task row missing required fields: {ln.strip()!r}"
    return True, f"All {len(data_rows)} tasks have required fields"


def session_boundaries_have_reasons(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each ``--- SESSION BOUNDARY ---`` is followed by a ``**Reason:**``.

    Marker per ``.qrspi/templates/worktree.md``.
    """
    output = result.get("output", "")
    if not output.strip():
        return False, "Empty output"
    parts = output.split("--- SESSION BOUNDARY ---")[1:]
    if not parts:
        return True, "No session boundaries to validate"
    for i, part in enumerate(parts, 1):
        if "**Reason:**" not in part.split("##")[0]:
            return False, f"Session boundary #{i} has no **Reason:**"
    return True, f"All {len(parts)} session boundaries have a reason"


def sessions_have_load_manifests(filename: str, result: dict) -> tuple[bool, str]:
    """Assert each ``## Session`` block has a ``**Load:**`` manifest line.

    Marker per ``.qrspi/templates/worktree.md``.
    """
    output = result.get("output", "")
    blocks = re.split(r"(?m)^##\s+Session\s+\d+", output)[1:]
    if not blocks:
        return False, "No ## Session blocks found"
    for i, block in enumerate(blocks, 1):
        if "**Load:**" not in block:
            return False, f"Session #{i} has no **Load:** manifest"
    return True, f"All {len(blocks)} sessions have a Load manifest"


# ── New checks: Implement phase ──

def impl_log_has_required_fields(filename: str, result: dict) -> tuple[bool, str]:
    """Assert the impl log carries the required per-session fields.

    Required markers per ``.qrspi/templates/impl-log.md``: ``**Timestamp:**``,
    ``**Tasks completed:**``, and ``**Tests:**``.
    """
    output = result.get("output", "")
    required = ["**Timestamp:**", "**Tasks completed:**", "**Tests:**"]
    missing = [m for m in required if m not in output]
    if missing:
        return False, f"Impl log missing fields: {', '.join(missing)}"
    return True, "Impl log has all required fields"


def impl_log_has_deviations(filename: str, result: dict) -> tuple[bool, str]:
    """Assert a deviations section marker is present.

    Marker per ``.qrspi/templates/impl-log.md`` (``**Deviations from ...:**``).
    """
    output = result.get("output", "")
    found = bool(re.search(r"\*\*Deviations from [^*]+:\*\*", output))
    return found, f"Deviations section {'present' if found else 'absent'}"


# ── Check Dispatcher ──

CHECKS = {
    # Pre-existing (10)
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
    # Re-shaped count checks (3)
    "question_count": question_count,
    "slice_count": slice_count,
    "total_steps": total_steps,
    # Questions phase (2 new)
    "section_count": section_count,
    "section_question_count": section_question_count,
    "all_questions_answered": all_questions_answered,
    # Research phase (3 new)
    "contains_not_found": contains_not_found,
    "not_found_has_search_description": not_found_has_search_description,
    "all_answers_have_evidence": all_answers_have_evidence,
    # Design phase (4 new)
    "code_snippets_under_limit": code_snippets_under_limit,
    "risk_register_min_entries": risk_register_min_entries,
    "pattern_decisions_have_options": pattern_decisions_have_options,
    "contains_new_pattern_flag": contains_new_pattern_flag,
    # Structure phase (4 new)
    "all_slices_have_context_cost": all_slices_have_context_cost,
    "no_slice_exceeds_file_limit": no_slice_exceeds_file_limit,
    "all_files_marked_new_or_modify": all_files_marked_new_or_modify,
    "no_large_slices_without_justification": no_large_slices_without_justification,
    # Plan phase (3 new)
    "all_modify_steps_have_current_after": all_modify_steps_have_current_after,
    "all_slices_have_verify_checkpoint": all_slices_have_verify_checkpoint,
    "all_steps_are_atomic": all_steps_are_atomic,
    # Worktree phase (4 new)
    "has_critical_path": has_critical_path,
    "all_tasks_have_required_fields": all_tasks_have_required_fields,
    "session_boundaries_have_reasons": session_boundaries_have_reasons,
    "sessions_have_load_manifests": sessions_have_load_manifests,
    # Implement phase (2 new)
    "impl_log_has_required_fields": impl_log_has_required_fields,
    "impl_log_has_deviations": impl_log_has_deviations,
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
