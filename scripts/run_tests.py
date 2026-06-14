#!/usr/bin/env python3
"""Aggregating test runner for the qrspi Python script suite.

Discovers every ``scripts/*_test.py`` sibling and runs each as its own
subprocess (matching the repo convention: each test is a standalone
``python3 scripts/<name>_test.py`` that exits 0 on success, non-zero on
failure). Reports a per-file PASS/FAIL line plus an aggregate summary, and
exits non-zero if any test file fails so CI can gate on it.

Stdlib-only (no pytest), self-locating from this file's path so it runs from
any cwd. Mirrors the conventions of the other ``scripts/qrspi_*`` tools.

Usage:
    python3 scripts/run_tests.py            # run every *_test.py
    python3 scripts/run_tests.py resolve    # run only files matching "resolve"
    python3 scripts/run_tests.py --list     # list discovered test files, run none

JavaScript test coverage (the qrspi-batch.js workflow orchestrator) is
deliberately out of scope here and deferred to future development.
"""

import argparse
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# This runner and its own test must never be executed as suite members:
# run_tests.py is not a *_test.py file, and run_tests_test.py is included as a
# normal member (it only imports this module's functions, guarded by __main__).
DEFAULT_TIMEOUT = 180  # seconds per test file; a hung test fails rather than wedging CI


def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    """Return the sorted absolute paths of every ``*_test.py`` in *scripts_dir*.

    If *pattern* is given, keep only files whose basename contains it
    (case-sensitive substring match).
    """
    names = sorted(
        n for n in os.listdir(scripts_dir)
        if n.endswith("_test.py")
    )
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]


def run_one(path, python=None, timeout=DEFAULT_TIMEOUT):
    """Run a single test file as a subprocess.

    Returns ``(ok, duration_seconds, output)`` where *ok* is True iff the
    process exited 0. A timeout counts as a failure (ok=False). *output* is the
    combined stdout+stderr, captured for printing only on failure.
    """
    python = python or sys.executable
    start = time.time()
    try:
        proc = subprocess.run(
            [python, path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        ok = proc.returncode == 0
        output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        ok = False
        captured = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", "replace")
        output = captured + f"\n[TIMEOUT after {timeout}s]"
    return ok, time.time() - start, output


def run_suite(paths, python=None, timeout=DEFAULT_TIMEOUT, out=sys.stdout):
    """Run every path in *paths*, printing progress. Return (passed, failures).

    *failures* is a list of ``(path, output)`` for every file that did not exit 0.
    """
    failures = []
    passed = 0
    suite_start = time.time()
    print(f"Running {len(paths)} Python test file(s)...\n", file=out)
    for path in paths:
        name = os.path.basename(path)
        ok, duration, output = run_one(path, python=python, timeout=timeout)
        if ok:
            passed += 1
            print(f"  PASS {name} ({duration:.2f}s)", file=out)
        else:
            failures.append((path, output))
            print(f"  FAIL {name} ({duration:.2f}s)", file=out)
    elapsed = time.time() - suite_start
    print("\n" + "=" * 56, file=out)
    print(f"{passed} passed, {len(failures)} failed in {elapsed:.2f}s", file=out)
    if failures:
        print("\nFailing test output:", file=out)
        for path, output in failures:
            print(f"\n----- {os.path.basename(path)} -----", file=out)
            print(output.rstrip() or "(no output)", file=out)
    return passed, failures


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the qrspi Python test suite (every scripts/*_test.py)."
    )
    parser.add_argument(
        "pattern", nargs="?", default=None,
        help="optional substring; only run test files whose name contains it",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="list the discovered test files and exit without running them",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"per-file timeout in seconds (default {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args(argv)

    paths = discover_tests(pattern=args.pattern)

    if args.list:
        for path in paths:
            print(os.path.basename(path))
        return 0

    if not paths:
        where = f" matching {args.pattern!r}" if args.pattern else ""
        print(f"No test files found{where}.", file=sys.stderr)
        return 1

    _passed, failures = run_suite(paths, timeout=args.timeout)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
