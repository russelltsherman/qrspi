#!/usr/bin/env python3
"""Deterministic persist of a staged QRSPI phase artifact into its worktree.

Why this exists
---------------
The phase agents (qrspi-questions / research / design / structure / plan /
worktree) run on a weak local worker model that reliably corrupts the literal
"qrspi" token whenever it must echo a long absolute artifact path back into a
Write call: `qrspi` -> `qrpii`, `.qrspi` -> `.qrpi`, etc. The artifact then lands
in a phantom directory (e.g. `/workspaces/qrpii/.worktrees/RUS-21/...`) and the
real worktree never receives it -- yet the agent still "reports completion". The
downstream finalize worker only discovers the missing artifact much later and
aborts the whole phase, so correctly-produced sibling artifacts are stranded as
uncommitted files and silently lost. This is the same path-mangling failure class
already neutralised for the RESOLVE worker by `qrspi_resolve.py`.

Fix A removes the qrspi path from the model entirely. The phase agent writes its
artifact to a SHORT, token-free staging path it cannot corrupt
(`/tmp/phase-stage/<ticket>/<artifact>.md`), and THIS script -- which self-locates
the repo root from its own `__file__` (never an argument, never cwd, the whole
point) -- owns the canonical destination, moves the file there, and verifies it is
non-empty. The caller types only short tokens (`--ticket`, `--artifact`); every
qrspi-laden path is computed here, deterministically. Any failure is reported ONCE
as `ok:false` with a verbatim message -- never retried -- so a weak model cannot
thrash on it.

Output: a single JSON envelope on stdout:
    { ok, repoRoot, src, dest, bytes, error? }
"""

import argparse
import json
import os
import shutil
import sys

# ENGINE_ROOT: the dir holding this engine's scripts/ (derived from __file__) — used
# ONLY for sibling imports, never a host path. REPO_ROOT: the HOST checkout root the
# artifact is persisted into, resolved through the shared qrspi_paths.resolve_repo_root()
# (git-common-dir first, so it is the MAIN checkout even when invoked from a worktree;
# __file__ parent as the last resort). validate=False keeps gh off the import path; the
# runtime override is validated in main(). Decoupling these two is the whole point of
# RUS-60: the engine can live anywhere while writing to a different host checkout
# (ref: design.md Decision 2; structure.md Modified Types).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]

# Token-free staging root the phase agents write to. Contains no "qrspi" token, so
# the worker model reproduces it intact. Kept in sync with the qrspi-batch workflow
# helper `stg(id, name) => /tmp/phase-stage/<id>/<name>.md`.
STAGE_ROOT = "/tmp/phase-stage"


# --- pure helpers (unit-tested) --------------------------------------------

def staging_path(stage_root, ticket, artifact):
    """Token-free path the phase agent wrote its artifact to. Pure."""
    return os.path.join(stage_root, ticket, "%s.md" % artifact)


def dest_path(repo_root, ticket, artifact):
    """Canonical worktree artifact path. Pure. The qrspi token lives ONLY here --
    computed by the script, never typed by the model."""
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)


def persist(src, dest):
    """Move a non-empty staged file `src` to `dest`, creating dest's parent dir.
    Returns (bytes_written, error) where error is None on success. Touches only the
    filesystem (no network/subprocess), so it is unit-testable against temp dirs."""
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    try:
        out = os.path.getsize(dest)
    except OSError:
        return 0, "destination not written: %s" % dest
    if out == 0:
        return 0, "destination is empty after move: %s" % dest
    return out, None


# --- entrypoint ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Persist a staged QRSPI artifact into its worktree (self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    parser.add_argument("--artifact", required=True, choices=ARTIFACTS,
                        help="Artifact name without extension (e.g. plan)")
    parser.add_argument("--stage-root", default=STAGE_ROOT,
                        help="Staging root (default: %s)" % STAGE_ROOT)
    parser.add_argument("--repo-root", default=None,
                        help="Explicit host checkout root override (validated against gh "
                             "repo view). When omitted, the host root is auto-detected from "
                             "cwd via git-common-dir (the MAIN checkout even from a worktree); "
                             "see qrspi_paths.resolve_repo_root.")
    args = parser.parse_args()

    # The HOST checkout root the artifact lands in: --repo-root wins (validated), else
    # git-common-dir from cwd. Decoupled from ENGINE_ROOT so the engine can write into a
    # different host checkout (ref: design.md Decision 2).
    repo_root = qrspi_paths.resolve_repo_root(args.repo_root, cwd=os.getcwd())

    src = staging_path(args.stage_root, args.ticket, args.artifact)
    dest = dest_path(repo_root, args.ticket, args.artifact)
    bytes_written, error = persist(src, dest)

    env = {
        "ok": error is None,
        "repoRoot": repo_root,
        "src": src,
        "dest": dest,
        "bytes": bytes_written,
    }
    if error is not None:
        env["error"] = error

    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
