#!/usr/bin/env python3
"""Dev-install smoke check: prove the bundled QRSPI engine resolves under the plugin root.

Why this exists
---------------
RUS-62 relocates the whole QRSPI engine into a Claude Code plugin subtree (``plugin/``)
and rewrites every engine invocation from cwd-relative ``scripts/...`` to
``${CLAUDE_PLUGIN_ROOT}/scripts/...``. The in-scope Done-when gate (design OQ3,
"scripted now") is a smoke check that, after a dev install pointing ``--plugin-dir`` at
``plugin/``, a bundled ``qrspi_*.py`` actually resolves under ``${CLAUDE_PLUGIN_ROOT}``.

What it asserts
---------------
- The plugin root is resolved with precedence ``${CLAUDE_PLUGIN_ROOT}`` →
  :func:`qrspi_paths.engine_root`'s parent (the dev-install env var is the loader's
  signal; the ``engine_root()`` fallback covers an unset env var so the check still
  runs from a bare checkout — ref Q6).
- A bundled engine script resolves at ``<plugin_root>/scripts/<name>.py``. This is the
  literal ``${CLAUDE_PLUGIN_ROOT}/scripts/...`` invocation form the prose and JS emit.
- FAIL-LOUD (ref Q13): a referenced-but-absent bundled script raises
  :class:`MissingBundledScript` and the CLI exits non-zero, so a broken/partial install
  is caught rather than silently passing.

Exit codes: 0 when every required bundled script resolves; non-zero (fail-loud) when any
is missing or the plugin root cannot be determined.

Run (dev install): ``CLAUDE_PLUGIN_ROOT="$(pwd)/plugin" python3 plugin/scripts/qrspi_plugin_smoke.py``
"""

import os
import sys

# ENGINE_ROOT: this script's own dir (from __file__) — used ONLY for the sibling import
# of qrspi_paths, exactly like the rest of the harness.
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402


# A representative set of bundled engine scripts the plugin must ship. These are the
# load-bearing modules the orchestrator/prose invoke via ${CLAUDE_PLUGIN_ROOT}/scripts/...;
# if the relocation dropped any of them the install is broken. qrspi_paths.py is included
# because it is the sibling-import anchor every other script depends on.
REQUIRED_BUNDLED_SCRIPTS = (
    "qrspi_paths.py",
    "qrspi_resolve.py",
    "qrspi_resolve_state.py",
    "qrspi_pr_state.py",
    "qrspi_persist.py",
    "qrspi_pr_body.py",
)


class MissingBundledScript(Exception):
    """Raised when a referenced bundled script is absent under ``<plugin_root>/scripts/``.

    Fail-loud per Q13: a partial/broken plugin install surfaces as this exception (and a
    non-zero CLI exit) instead of silently passing.
    """


def plugin_root():
    """Resolve the plugin root with precedence ``${CLAUDE_PLUGIN_ROOT}`` → ``engine_root()`` parent.

    The Claude Code dev install (``--plugin-dir plugin/``) is expected to populate
    ``CLAUDE_PLUGIN_ROOT`` with the plugin subtree path; that is the smoke check's primary
    signal. When the env var is unset (a bare checkout, no loader), fall back to the parent
    of :func:`qrspi_paths.engine_root` — i.e. ``plugin/`` itself, since this file lives at
    ``plugin/scripts/`` (ref Q6). Returns an absolute path.
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return os.path.abspath(env)
    # Fallback: engine_root() is <plugin_root>/scripts; its parent is the plugin root.
    return os.path.dirname(qrspi_paths.engine_root())


def resolve_bundled_script(name, root=None):
    """Resolve ``<plugin_root>/scripts/<name>`` — the literal ``${CLAUDE_PLUGIN_ROOT}/scripts/<name>`` form.

    Raises :class:`MissingBundledScript` (fail-loud, Q13) when the file does not exist.
    Returns the absolute path on success.
    """
    base = root if root is not None else plugin_root()
    path = os.path.join(base, "scripts", name)
    if not os.path.isfile(path):
        raise MissingBundledScript(
            "bundled script %r does not resolve at %s "
            "(plugin root: %s)" % (name, path, base))
    return path


def run_smoke(required=REQUIRED_BUNDLED_SCRIPTS, root=None):
    """Resolve every required bundled script under the plugin root; return the resolved paths.

    Raises :class:`MissingBundledScript` on the first missing script (fail-loud). Pure
    enough to unit-test by passing an explicit ``root``.
    """
    base = root if root is not None else plugin_root()
    return [resolve_bundled_script(name, root=base) for name in required]


def main(argv=None):
    try:
        base = plugin_root()
        resolved = run_smoke(root=base)
    except MissingBundledScript as exc:
        print("qrspi plugin smoke check FAILED: %s" % exc, file=sys.stderr)
        return 1
    print("qrspi plugin smoke check OK: plugin root %s; %d bundled scripts resolve via "
          "${CLAUDE_PLUGIN_ROOT}/scripts/..." % (base, len(resolved)))
    for path in resolved:
        print("  - %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
