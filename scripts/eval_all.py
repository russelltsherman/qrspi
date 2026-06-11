#!/usr/bin/env python3
"""Multi-agent eval driver for the QRSPI phase agents.

Discovers the phase agents under ``.claude/agents/`` (``qrspi-<phase>.md``),
runs each one against its phase-filtered slice of the shared eval suite into
``results/all/<phase>/``, and writes a consolidated ``results/all/summary.json``
that distinguishes phase-level from suite-level regressions and ``errored``
phases from genuine ``low_score`` phases.

This is a *plumbing* driver, not a scorer: the underlying single-agent path
(``run_eval.py`` + ``grade.py``) is a non-functional placeholder whose
``execute_single`` returns empty output (see CLAUDE.md / RUS-41 OQ4), so real
scores against the stubbed harness are uniformly ~0. The unit tests exercise
discovery, filtering, aggregation, the error-vs-low-score distinction, and the
``--regression-only`` exit code — NOT real-score correctness.

JSON record shapes (contracts, not classes):

  PhaseResult {
    phase: str,
    status: "ok" | "errored" | "low_score",
    train_score: float,
    test_score: float,
    error: str | None,
    results_dir: str,
    baseline_score: float | None,   # prior test_score for drop-vs-previous
  }

  Summary {
    phases: { <phase>: PhaseResult },
    suite_aggregate: { train_score: float, test_score: float },
    phase_regressions: [str],
    suite_regression: bool,
    errored_phases: [str],
  }
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

# The single documented CI regression threshold: a suite-level (and per-phase)
# drop of more than this many points versus the previous run trips a regression.
# This adopts run_loop.sh's 0.05 drop-vs-previous semantics (design.md Q7 / OQ1
# resolved to *drop*). report.py's 0.2 per-CASE threshold is intentionally NOT
# reused here — that one guards individual case regressions inside the iteration
# ledger; this one guards the aggregate phase/suite score for the CI exit gate.
REGRESSION_THRESHOLD: float = 0.05

# Score below which a (non-errored) phase is flagged as a genuine low_score,
# distinct from an errored phase. A phase only earns "ok" when it neither
# errored nor scored below this floor.
LOW_SCORE_FLOOR: float = 0.5

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent


def discover_agents(agents_dir: str = ".claude/agents") -> list:
    """Return the phase names of all ``qrspi-*.md`` agents under ``agents_dir``.

    Globs ``qrspi-*.md`` and strips the ``qrspi-`` prefix from each stem so
    ``.claude/agents/qrspi-design.md`` yields ``"design"`` (ref Q5).
    """
    phases = []
    for path in sorted(glob.glob(os.path.join(agents_dir, "qrspi-*.md"))):
        stem = Path(path).stem  # e.g. "qrspi-design"
        phases.append(stem.removeprefix("qrspi-"))
    return phases


def phase_to_agent_path(phase: str, agents_dir: str = ".claude/agents") -> str:
    """Map a phase name to its agent prompt path (ref Q4).

    ``"design"`` -> ``<agents_dir>/qrspi-design.md``.
    """
    return os.path.join(agents_dir, f"qrspi-{phase}.md")


def filter_suite(suite: dict, phase: str) -> dict:
    """Return a sub-suite for ``phase``, preserving the suite's identity (ref Q10).

    Keeps every top-level field (notably ``name``) and replaces ``cases`` with
    only those whose ``case["phase"] == phase``. The ``name`` and ``cases`` keys
    are always retained so the result still satisfies ``run_eval.load_suite``'s
    required-field check (it raises ``ValueError`` if either is missing).
    """
    filtered = dict(suite)
    filtered["cases"] = [c for c in suite.get("cases", []) if c.get("phase") == phase]
    # Defensive: guarantee the required keys survive even on a malformed suite.
    filtered.setdefault("name", suite.get("name", phase))
    return filtered


def _load_json(path: str):
    with open(path) as f:
        return json.load(f)


def read_phase_result(phase: str, results_dir: str) -> dict:
    """Read a phase's ``grades.json`` + ``results.json`` into a PhaseResult.

    Scores come from ``<results_dir>/grades.json`` (``train_score`` /
    ``test_score``). Errors come from ``<results_dir>/results.json``: if ANY
    execution record carries a non-null ``error``, the phase status is
    ``"errored"`` — this is kept distinct from a genuine ``"low_score"`` so a
    crashed phase is never silently read as merely under-performing (ref Q9,
    Decision 4). An optional ``<results_dir>/baseline.json`` supplies the prior
    ``test_score`` for the drop-vs-previous regression check.
    """
    grades_path = os.path.join(results_dir, "grades.json")
    results_path = os.path.join(results_dir, "results.json")
    baseline_path = os.path.join(results_dir, "baseline.json")

    train_score = 0.0
    test_score = 0.0
    if os.path.exists(grades_path):
        grades = _load_json(grades_path)
        train_score = float(grades.get("train_score", 0.0) or 0.0)
        test_score = float(grades.get("test_score", 0.0) or 0.0)

    error = None
    if os.path.exists(results_path):
        results = _load_json(results_path)
        for rec in results.get("results", []):
            if rec.get("error"):
                error = str(rec["error"])
                break

    baseline_score = None
    if os.path.exists(baseline_path):
        baseline = _load_json(baseline_path)
        bs = baseline.get("test_score")
        baseline_score = None if bs is None else float(bs)

    if error is not None:
        status = "errored"
    elif test_score < LOW_SCORE_FLOOR:
        status = "low_score"
    else:
        status = "ok"

    return {
        "phase": phase,
        "status": status,
        "train_score": train_score,
        "test_score": test_score,
        "error": error,
        "results_dir": results_dir,
        "baseline_score": baseline_score,
    }


def aggregate(phase_results: list, regression_threshold: float = REGRESSION_THRESHOLD) -> dict:
    """Consolidate per-phase results into a Summary (ref AC3).

    Phase-level and suite-level signals are kept as DISTINCT fields:

      * ``phase_regressions`` — phases whose ``test_score`` dropped more than
        ``regression_threshold`` below their own ``baseline_score``.
      * ``suite_regression`` — True when the suite-mean ``test_score`` dropped
        more than ``regression_threshold`` below the suite-mean baseline.
      * ``errored_phases`` — phases whose status is ``"errored"`` (kept separate
        from low_score / regression).

    Errored phases are excluded from the regression comparison so a crash is not
    double-counted as a score drop.
    """
    phases = {pr["phase"]: pr for pr in phase_results}

    scored = [pr for pr in phase_results if pr["status"] != "errored"]
    train_scores = [pr["train_score"] for pr in scored]
    test_scores = [pr["test_score"] for pr in scored]
    suite_train = sum(train_scores) / len(train_scores) if train_scores else 0.0
    suite_test = sum(test_scores) / len(test_scores) if test_scores else 0.0

    phase_regressions = []
    for pr in scored:
        baseline = pr.get("baseline_score")
        if baseline is not None and (baseline - pr["test_score"]) > regression_threshold:
            phase_regressions.append(pr["phase"])

    baselines = [
        pr["baseline_score"] for pr in scored if pr.get("baseline_score") is not None
    ]
    suite_regression = False
    if baselines:
        suite_baseline = sum(baselines) / len(baselines)
        suite_regression = (suite_baseline - suite_test) > regression_threshold

    errored_phases = [pr["phase"] for pr in phase_results if pr["status"] == "errored"]

    return {
        "phases": phases,
        "suite_aggregate": {
            "train_score": round(suite_train, 4),
            "test_score": round(suite_test, 4),
        },
        "phase_regressions": phase_regressions,
        "suite_regression": suite_regression,
        "errored_phases": errored_phases,
    }


def _warn_empty_fixtures(suite: dict) -> None:
    """Warn (do NOT fix) when a case references a missing/empty fixture (ref Q2, OQ2).

    The latent empty-fixture condition is surfaced for visibility only; fixture
    resolution itself is deliberately left unchanged (the design defers the fix).
    Fixture paths are resolved relative to the repo root, mirroring run_eval's
    ``os.path.exists`` check executed with CWD at the repo root.
    """
    for case in suite.get("cases", []):
        for fixture in case.get("context", {}).get("files", []):
            abs_path = fixture if os.path.isabs(fixture) else os.path.join(_REPO_ROOT, fixture)
            if not os.path.exists(abs_path):
                print(
                    f"WARNING: case {case.get('id', '?')} references missing fixture "
                    f"'{fixture}' (left unresolved — see RUS-41 OQ2)",
                    file=sys.stderr,
                )
            elif os.path.isfile(abs_path) and os.path.getsize(abs_path) == 0:
                print(
                    f"WARNING: case {case.get('id', '?')} references empty fixture "
                    f"'{fixture}' (left unresolved — see RUS-41 OQ2)",
                    file=sys.stderr,
                )


def run_phase(phase: str, suite: dict, suite_path: str, agents_dir: str,
              results_root: str, trials: int = 3) -> dict:
    """Run the single-agent path for one phase into ``results_root/<phase>/``.

    Builds the phase-filtered sub-suite, writes it to a temp file inside the
    phase's results dir, then invokes the existing single-agent path as a
    subprocess (``run_eval.py`` then ``grade.py``) exactly as run_loop.sh does
    — confirmed in-file as the integration seam (run_eval writes ``results.json``;
    grade writes ``grades.json``). Returns the PhaseResult. Raising is the
    caller's concern; this isolates nothing itself.
    """
    phase_dir = os.path.join(results_root, phase)
    os.makedirs(phase_dir, exist_ok=True)

    sub_suite = filter_suite(suite, phase)
    sub_suite_path = os.path.join(phase_dir, "suite.json")
    with open(sub_suite_path, "w") as f:
        json.dump(sub_suite, f, indent=2)

    agent_path = phase_to_agent_path(phase, agents_dir)

    subprocess.run(
        [sys.executable, str(_THIS_DIR / "run_eval.py"),
         "--skill", agent_path,
         "--suite", sub_suite_path,
         "--output", phase_dir,
         "--trials", str(trials)],
        cwd=str(_REPO_ROOT), check=True,
    )
    subprocess.run(
        [sys.executable, str(_THIS_DIR / "grade.py"),
         "--results", os.path.join(phase_dir, "results.json"),
         "--suite", sub_suite_path,
         "--output", phase_dir],
        cwd=str(_REPO_ROOT), check=True,
    )

    return read_phase_result(phase, phase_dir)


def drive(phases: list, suite_path: str, agents_dir: str, results_root: str,
          trials: int = 3) -> dict:
    """Run every requested phase (isolating per-phase failures) and aggregate.

    Each phase is wrapped in try/except so one failed or errored phase does NOT
    abort the whole ``--all`` run (ref Q10, Risk Register): a crashed phase is
    recorded as an ``errored`` PhaseResult and the driver moves on. Writes
    ``results_root/summary.json`` (a top-level file under ``all/``, NEVER a phase
    ``grades.json``, so report.py's ``all/`` guard keeps it out of the version
    ledger — ref Q8, Decision 3).
    """
    suite = _load_json(suite_path)
    _warn_empty_fixtures(suite)

    os.makedirs(results_root, exist_ok=True)

    phase_results = []
    for phase in phases:
        try:
            phase_results.append(
                run_phase(phase, suite, suite_path, agents_dir, results_root, trials)
            )
        except Exception as e:  # isolate: one bad phase must not abort the run
            print(f"WARNING: phase '{phase}' failed to run: {e}", file=sys.stderr)
            phase_results.append({
                "phase": phase,
                "status": "errored",
                "train_score": 0.0,
                "test_score": 0.0,
                "error": str(e),
                "results_dir": os.path.join(results_root, phase),
                "baseline_score": None,
            })

    summary = aggregate(phase_results, REGRESSION_THRESHOLD)

    summary_path = os.path.join(results_root, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written to {summary_path}")

    return summary


def _has_regression(summary: dict) -> bool:
    return bool(summary["phase_regressions"]) or bool(summary["suite_regression"])


def main(argv: list) -> int:
    """CLI entrypoint (ref Q6, AC1, AC2).

    ``--all`` runs every discovered phase agent; ``--phase <name>`` runs a single
    mapped agent. ``--regression-only`` performs one pass (no revision step) and
    returns a non-zero exit code when any phase or the suite regressed past
    ``REGRESSION_THRESHOLD`` — the CI gate. Returns 0 otherwise.
    """
    parser = argparse.ArgumentParser(
        description="Run all QRSPI phase agents against their phase-filtered eval slices."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true",
                       help="Run every discovered qrspi-* phase agent.")
    group.add_argument("--phase", help="Run a single named phase agent.")
    parser.add_argument("--regression-only", action="store_true",
                        help="One pass, no revision; non-zero exit on regression.")
    parser.add_argument("--agents-dir", default=str(_REPO_ROOT / ".claude" / "agents"),
                        help="Directory of qrspi-*.md agents.")
    parser.add_argument("--suite", default=str(_REPO_ROOT / "evals" / "suite.json"),
                        help="Path to the shared eval suite JSON.")
    parser.add_argument("--results-dir", default=str(_REPO_ROOT / "results" / "all"),
                        help="Root for the consolidated results/all/ tree.")
    parser.add_argument("--trials", type=int, default=3, help="Trials per case.")
    args = parser.parse_args(argv)

    if args.all:
        phases = discover_agents(args.agents_dir)
    else:
        phases = [args.phase]

    summary = drive(phases, args.suite, args.agents_dir, args.results_dir, args.trials)

    if args.regression_only and _has_regression(summary):
        print("REGRESSION: phase_regressions="
              f"{summary['phase_regressions']} suite_regression={summary['suite_regression']}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
