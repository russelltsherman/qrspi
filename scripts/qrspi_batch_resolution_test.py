#!/usr/bin/env python3
"""Resolution guard for the qrspi-batch workflow's ENGINE_ROOT precedence.

Stdlib-only, assert-based (same convention as qrspi_paths_test.py et al.). This is the only
automated signal that the *synced* batch workflow finds the QRSPI engine: it exercises the REAL
``ENGINE_ROOT``/``engineCmd`` precedence defined in ``.claude/workflows/qrspi-batch.js`` rather
than re-implementing it, by extracting those source lines and running them under ``node -e``.

Why node (not a python re-implementation): the precedence lives in JS
(``process.env.CLAUDE_PLUGIN_ROOT`` -> ``process.cwd()`` -> ``'.'``). Copying that logic into the
test would let the test pass while the shipped workflow drifted. Shelling out to the actual
constant keeps the guard honest (ref: structure.md Slice 2, Q12, design Delta).

Cases:
  (a) CLAUDE_PLUGIN_ROOT set    -> ENGINE_ROOT resolves to that dir; engineCmd('scripts/x.py')
                                   resolves UNDER it (not cwd).
  (b) CLAUDE_PLUGIN_ROOT unset  -> ENGINE_ROOT falls back to process.cwd(); engineCmd resolves
                                   under cwd.

Run: python3 scripts/qrspi_batch_resolution_test.py
"""

import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WORKFLOW = os.path.normpath(
    os.path.join(_HERE, "..", ".claude", "workflows", "qrspi-batch.js")
)

failures = 0
total = 0


def check(label, got, want):
    global failures, total
    total += 1
    if got == want:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))


def _extract_engine_root_source():
    """Pull the `const ENGINE_ROOT = ...` block and the `engineCmd` arrow from the real workflow.

    Returns JS source (string) defining ENGINE_ROOT and engineCmd, so the test runs the SHIPPED
    precedence, not a copy. Fails loudly if the source shape changed (the regex no longer matches),
    which is itself a useful signal that the contract under test moved.
    """
    with open(_WORKFLOW, "r", encoding="utf-8") as fh:
        src = fh.read()

    er = re.search(r"const ENGINE_ROOT =\n(?:.*\n)*?  '\.'\n", src)
    if er is None:
        raise AssertionError(
            "could not locate the `const ENGINE_ROOT = ...` block in %s — did its shape change?"
            % _WORKFLOW
        )

    ec = re.search(r"const engineCmd = \(rel\) => .*\n", src)
    if ec is None:
        raise AssertionError(
            "could not locate the `const engineCmd = ...` arrow in %s — did its shape change?"
            % _WORKFLOW
        )

    return er.group(0) + ec.group(0)


def main():
    engine_src = _extract_engine_root_source()

    # node runs with cwd = a known dir so the cwd-fallback case is deterministic.
    run_cwd = _HERE
    base_env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}

    # Case (a): CLAUDE_PLUGIN_ROOT set -> ENGINE_ROOT is that dir; engineCmd resolves under it.
    plugin_root = "/opt/plugins/qrspi"
    env_set = dict(base_env, CLAUDE_PLUGIN_ROOT=plugin_root)
    # run node from run_cwd to prove the env var wins over cwd
    proc_set = subprocess.run(
        [
            "node",
            "-e",
            engine_src
            + "process.stdout.write(ENGINE_ROOT + '\\n');\n"
            + "process.stdout.write(engineCmd('scripts/qrspi_persist.py') + '\\n');\n",
        ],
        env=env_set,
        cwd=run_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc_set.returncode == 0, proc_set.stderr
    set_root, set_cmd = proc_set.stdout.strip().split("\n")
    check("(a) CLAUDE_PLUGIN_ROOT set -> ENGINE_ROOT is plugin root", set_root, plugin_root)
    check(
        "(a) engineCmd resolves under CLAUDE_PLUGIN_ROOT (not cwd)",
        set_cmd,
        plugin_root + "/scripts/qrspi_persist.py",
    )
    check(
        "(a) engineCmd is NOT under cwd when plugin root is set",
        set_cmd.startswith(run_cwd + "/"),
        False,
    )

    # Case (b): CLAUDE_PLUGIN_ROOT unset -> ENGINE_ROOT falls back to process.cwd().
    proc_unset = subprocess.run(
        [
            "node",
            "-e",
            engine_src
            + "process.stdout.write(ENGINE_ROOT + '\\n');\n"
            + "process.stdout.write(engineCmd('scripts/qrspi_persist.py') + '\\n');\n",
        ],
        env=base_env,
        cwd=run_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc_unset.returncode == 0, proc_unset.stderr
    unset_root, unset_cmd = proc_unset.stdout.strip().split("\n")
    check("(b) CLAUDE_PLUGIN_ROOT unset -> ENGINE_ROOT falls back to cwd", unset_root, run_cwd)
    check(
        "(b) engineCmd resolves under cwd when plugin root unset",
        unset_cmd,
        run_cwd + "/scripts/qrspi_persist.py",
    )

    print("\n%d/%d checks passed" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
