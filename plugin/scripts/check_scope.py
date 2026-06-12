#!/usr/bin/env python3
"""Check that implementation stayed within allowed scope.

Used as a script-type assertion in evals to verify the implement agent
only touched files listed in its session task list.
"""

import argparse
import json
import re
import sys


def load_allowed_files(worktree_session_path: str) -> set:
    """Extract allowed file paths from a worktree session manifest."""
    with open(worktree_session_path) as f:
        content = f.read()

    # Extract file paths from markdown (backtick-wrapped paths)
    files = set()
    for match in re.finditer(r"`([^`]+\.\w+)`", content):
        files.add(match.group(1))

    return files


def extract_touched_files(impl_log_path: str) -> set:
    """Extract files mentioned as modified in impl-log.md."""
    with open(impl_log_path) as f:
        content = f.read()

    files = set()
    for match in re.finditer(r"`([^`]+\.\w+)`", content):
        files.add(match.group(1))

    return files


def check_scope(impl_log_path: str, worktree_session_path: str) -> dict:
    """Check if implementation stayed within scope."""
    allowed = load_allowed_files(worktree_session_path)
    touched = extract_touched_files(impl_log_path)

    out_of_scope = touched - allowed
    result = {
        "passed": len(out_of_scope) == 0,
        "allowed_files": sorted(allowed),
        "touched_files": sorted(touched),
        "out_of_scope": sorted(out_of_scope),
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Check implementation scope")
    parser.add_argument("--log", required=True, help="Path to impl-log.md")
    parser.add_argument("--allowed", required=True, help="Path to worktree session file")
    args = parser.parse_args()

    result = check_scope(args.log, args.allowed)

    if result["passed"]:
        print("PASS: All files within scope")
    else:
        print(f"FAIL: Out-of-scope files: {result['out_of_scope']}")

    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
