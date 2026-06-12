#!/usr/bin/env python3
"""Single source of truth for engine-location vs host-checkout-root resolution.

Why this exists
---------------
Today every QRSPI script derives its repo root from its own ``__file__`` location
(``_SCRIPT_DIR`` → its parent). That conflates two distinct concepts that this module
splits apart so the engine can live anywhere (e.g. installed as a Claude Code plugin)
while operating on a *different* host checkout (ref: design.md Decision 2, Decision 3):

- the **engine root** — the directory holding the engine ``scripts/`` (where this very
  file lives). Stable regardless of host cwd or host root; the only thing siblings need
  for ``sys.path.insert(0, engine_root())`` so they can import each other.
- the **host checkout root** — the repository the engine is operating *on*. All host
  paths (the ``.worktrees/<id>`` dir, the ``.qrspi/config.json`` reviewer path, the
  envelope ``repoRoot``/``worktreeDir``, every gh/git/gt subprocess ``cwd``) key off it.

``resolve_repo_root`` is the one place that decides the host root, with precedence
``--repo-root`` (validated) → git-common-dir (validated) → ``__file__`` fallback
(ref: Decision 1, RQ4). It fails loud — raising :class:`HostRootError` — when a
supplied or auto-detected root does not pass the ``gh repo view`` validation gate, so a
stale ``--repo-root`` flag or a cwd that points at the wrong checkout is caught rather
than silently operating on the wrong repo (ref: RQ4, Risk Register rows 1/5).

The git-common-dir-first auto-detect mirrors what ``qrspi_pr_body.py`` /
``qrspi_comment_reply.py`` / ``qrspi_revise_amend.py`` already do to stay correct from a
linked worktree; this module is what Slices 2–3 collapse those private copies onto.

The pure precedence/validation logic is exercised by ``qrspi_paths_test.py`` with the
subprocess calls (git, gh) stubbed, including the divergence case (a synthetic engine
dir distinct from a synthetic checkout) that closes the Q11 testing gap.
"""

import os
import subprocess


class HostRootError(Exception):
    """Raised when a supplied or auto-detected host root fails the ``gh repo view``
    validation gate — i.e. it is not a real checkout with a resolvable GitHub remote.

    Fail-loud per RQ4/Decision 1: a stale ``--repo-root`` flag or a wrong cwd surfaces
    as this exception instead of silently operating on the wrong repository.
    """


def engine_root():
    """Directory holding the engine ``scripts/`` — the dir of this file.

    Stable regardless of host cwd or host root, because it is derived purely from
    ``__file__``. Consumed by callers' ``sys.path.insert(0, engine_root())`` so sibling
    modules import correctly even when the engine is not the cwd (ref: Decision 2).
    """
    return os.path.dirname(os.path.abspath(__file__))


def _git_common_dir(cwd=None):
    """Resolve the host checkout root from git's shared ``.git`` dir, or ``None``.

    ``git rev-parse --path-format=absolute --git-common-dir`` returns the *shared*
    ``.git`` directory — the MAIN repo's, even when ``cwd`` is a linked worktree — whose
    parent is the main checkout root. So this resolves ``<main>`` from anywhere inside
    the repo (including a worktree), never ``<worktree>``. Returns ``None`` when git
    cannot answer (cwd outside a repo, git missing), letting the caller fall back to the
    ``__file__`` root (ref: Decision 1 Option B; mirrors the private copies in
    qrspi_pr_body / qrspi_comment_reply / qrspi_revise_amend).
    """
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd, capture_output=True, text=True)
    except OSError:
        # git binary not found / not executable: no answer.
        return None
    common = (res.stdout or "").strip()
    if res.returncode == 0 and common:
        return os.path.dirname(common)
    return None


def _validate_root(candidate):
    """Assert ``candidate`` is a real checkout with a resolvable GitHub remote, else raise.

    Runs ``gh repo view`` with ``cwd=candidate`` and asserts it succeeds and returns a
    non-empty ``nameWithOwner`` — i.e. the candidate is a genuine GitHub checkout whose
    remote ``gh`` can resolve (the "expected GitHub remote" of RQ4: whatever the candidate's
    own remote resolves to, which is exactly the remote OWNER/REPO discovery already keys
    off). A non-checkout, a checkout with no GitHub remote, or a missing ``gh`` all make
    this fail, so a stale ``--repo-root`` or wrong cwd raises :class:`HostRootError`
    rather than returning silently (fail-loud, ref: RQ4/Risk Register row 1). Returns
    ``None`` on success.
    """
    try:
        res = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            cwd=candidate, capture_output=True, text=True)
    except OSError as exc:
        raise HostRootError(
            "could not validate host root %r: gh not runnable: %s" % (candidate, exc))
    if res.returncode != 0:
        msg = (res.stderr or "").strip() or (res.stdout or "").strip()
        raise HostRootError(
            "host root %r failed gh repo view validation: %s" % (candidate, msg))
    name = (res.stdout or "").strip()
    if not name:
        raise HostRootError(
            "host root %r resolved no GitHub remote (empty nameWithOwner)" % (candidate,))
    return None


def resolve_repo_root(repo_root=None, cwd=None, validate=True):
    """Resolve the host checkout root — the single source of truth for host paths.

    Precedence (ref: Decision 1, RQ4):
      1. an explicit ``repo_root`` (the ``--repo-root`` flag) — **wins when supplied**,
         but is validated, never trusted blindly;
      2. git-common-dir auto-detect from ``cwd`` — validated;
      3. the ``__file__`` fallback (``engine_root()``'s parent) — the unvalidated
         last resort, returned when git cannot answer (e.g. cwd outside a repo, in which
         case the caller invoked the engine by its absolute path and ``__file__`` is the
         best available answer).

    When ``validate`` is true the chosen root from source (1) or (2) is passed through
    :func:`_validate_root`, raising :class:`HostRootError` on mismatch so a stale flag or
    wrong cwd fails loud. The ``__file__`` fallback is the deliberate last resort and is
    NOT subjected to the gate — validating it would defeat its purpose (it is reached
    precisely when git/gh context is unavailable), and it only triggers when neither
    higher-precedence source produced a root.
    """
    if repo_root:
        root = os.path.abspath(repo_root)
        if validate:
            _validate_root(root)
        return root

    common = _git_common_dir(cwd=cwd)
    if common:
        if validate:
            _validate_root(common)
        return common

    # Last resort: the engine's own parent dir. Unvalidated by design.
    return os.path.dirname(engine_root())
