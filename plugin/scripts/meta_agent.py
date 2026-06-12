#!/usr/bin/env python3
"""Single shared LLM-invocation seam for the eval self-improvement loop.

Decision 1, Option A (design.md / structure.md §Contracts): `complete(system, user)`
is a thin wrapper over the `using-claude-cli` subprocess path — `claude -p` headless
print mode — returning the raw model text as a string. Both downstream consumers
(`diagnose.py`'s `categorize_failure` and `revise.py`'s `propose_revisions`, Slices 2
and 3) call THIS function rather than each re-deriving how to shell out to the model,
and parse the returned text as JSON themselves (Decision 2, Option A — `MetaResponse`
is just `str`).

Defensive failure handling (Decision 1, ref Q3, Q6): the loop runs under
`set -euo pipefail`, so a model invocation that errors must NOT crash the loop. Any
subprocess failure — non-zero exit, missing `claude` binary, timeout, or unexpected
OS error — is logged to stderr and yields the `NO_RESULT` sentinel (an empty string)
that callers treat as "no result" (no category, no edits) instead of raising.

The boundary that the unit tests (`scripts/meta_agent_test.py`) mock is `_run_cli`,
the lone subprocess call. Everything else here is pure and directly testable:

- `build_command(system, user, model=None)` — the `claude -p ...` argv.
- `extract_text(returncode, stdout, stderr)` — map a CLI result to text-or-sentinel.

Run the tests with:
    python3 scripts/meta_agent_test.py
"""

import subprocess
import sys

# The "no result" sentinel. An empty string is the natural no-result value for a
# text-returning seam: callers JSON-parse the return, and an empty/blank string
# parses to "nothing to do" (no category, no edits) without a special-case type.
NO_RESULT = ""

# Default headless invocation of the `using-claude-cli` path. `-p/--print` runs
# non-interactively, emits the final result to stdout, and exits; `--output-format
# text` is the human/plain text result the callers parse as JSON. `--system-prompt`
# carries the role/instruction half so the positional `user` argument stays the
# concrete task evidence.
_CLI_BIN = "claude"

# Subprocess wall-clock guard so a hung model call cannot wedge the loop forever;
# a timeout is caught and degraded to the NO_RESULT sentinel like any other failure.
_TIMEOUT_SECONDS = 600


def _log(message):
    """Emit a diagnostic to stderr (stdout is the model-text channel)."""
    print("meta_agent: %s" % message, file=sys.stderr)


# --- pure helpers (unit-tested) --------------------------------------------

def build_command(system, user, model=None):
    """Build the `claude -p` argv for a (system, user) prompt pair. Pure.

    Headless print mode with plain-text output; the system prompt is appended to
    the CLI's own system prompt via `--append-system-prompt`, and the user prompt
    is the positional starting prompt. `model` is spliced in only when provided so
    the default model selection is left to the CLI/environment (OQ1: concrete model
    id is unresolved — callers/env may pin it, this seam does not hard-code one).
    """
    cmd = [_CLI_BIN, "-p", "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    cmd += ["--append-system-prompt", system or "", user or ""]
    return cmd


def extract_text(returncode, stdout, stderr):
    """Map a CLI (returncode, stdout, stderr) result to model text or the sentinel.

    Pure, so the success/failure decision is unit-testable without running the CLI:

      - returncode == 0 with non-blank stdout -> the raw model text (stripped of a
        single trailing newline the CLI appends, otherwise verbatim).
      - returncode == 0 but blank stdout      -> NO_RESULT (the model produced
        nothing usable; callers treat as no result, logged by the caller path).
      - returncode != 0                        -> NO_RESULT (the invocation failed).

    Returns (text, ok) where `ok` is whether a usable result was produced, so the
    caller can decide whether to log a failure.
    """
    if returncode != 0:
        return NO_RESULT, False
    text = stdout if stdout is not None else ""
    # `claude -p` text output ends with a trailing newline; drop exactly one so a
    # JSON-only response round-trips, but preserve internal formatting.
    if text.endswith("\n"):
        text = text[:-1]
    if not text.strip():
        return NO_RESULT, False
    return text, True


# --- subprocess boundary (mocked in tests) ---------------------------------

def _run_cli(cmd):
    """Run the `claude` CLI argv, returning (returncode, stdout, stderr).

    This is the single mockable seam. It NEVER raises: any OS-level failure
    (missing binary, timeout, etc.) is caught and reported as a non-zero result so
    `complete` degrades to the sentinel rather than propagating an exception into
    the `set -euo pipefail` loop.
    """
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS
        )
        return res.returncode, res.stdout, res.stderr
    except FileNotFoundError:
        return 127, "", "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "", "claude CLI timed out after %ds" % _TIMEOUT_SECONDS
    except OSError as exc:  # pragma: no cover - defensive catch-all
        return 1, "", "claude CLI invocation failed: %s" % exc


# --- public contract -------------------------------------------------------

def complete(system, user, model=None):
    """Invoke the shared LLM seam and return the raw model text (`MetaResponse = str`).

    Contract (structure.md §Contracts): single shared LLM-invocation seam over the
    `using-claude-cli` path; on any subprocess/invocation failure returns the
    NO_RESULT sentinel (logged) that callers treat as "no result" rather than
    crashing the loop. Never raises.
    """
    cmd = build_command(system, user, model=model)
    returncode, stdout, stderr = _run_cli(cmd)
    text, ok = extract_text(returncode, stdout, stderr)
    if not ok:
        detail = (stderr or "").strip() or (stdout or "").strip() or "no output"
        _log("no result (rc=%s): %s" % (returncode, detail))
        return NO_RESULT
    return text


if __name__ == "__main__":  # pragma: no cover - manual smoke entry point
    # Minimal manual smoke: `python3 scripts/meta_agent.py "<system>" "<user>"`.
    _system = sys.argv[1] if len(sys.argv) > 1 else "You are a helpful assistant."
    _user = sys.argv[2] if len(sys.argv) > 2 else "Reply with the single word OK."
    sys.stdout.write(complete(_system, _user))
    sys.stdout.write("\n")
