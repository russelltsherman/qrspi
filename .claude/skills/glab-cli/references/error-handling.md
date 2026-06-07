# glab error handling — recognized states vs HARD STOP

Two failure categories, kept deliberately distinct. Mixing them is the central hazard: if you
treat an infrastructure failure as a "recoverable state" you paper over a broken environment;
if you treat a normal branch as a fatal error you halt work that should continue. Decide which
one you are in *before* acting.

## The decision procedure

On any non-zero exit:

1. Read the exact error text and the exit code.
2. Does it match a **recognized state** below (a known, expected branch with a scripted
   recovery)? → handle it in-band and continue.
3. Otherwise — anything about permissions, auth, config, missing tooling, or an unrecognized
   error → it is an **infrastructure failure**. Apply the HARD STOP rule. Do not guess.

## Exit codes

- `0` — success.
- non-zero — failure of some kind. The exit code alone does not tell you which category; the
  message does. Always capture stderr (`2>err.txt` or `2>&1`) so you can classify it.

`glab` does not guarantee a rich taxonomy of distinct exit codes across versions, so classify
on the **message**, not on a specific numeric code.

## Recognized states (handle in-band, do NOT HARD STOP)

These are expected outcomes with a deterministic recovery. They are *not* environment
failures — they happen on a perfectly healthy setup.

| State | How it shows up | Deterministic recovery |
|-------|-----------------|------------------------|
| MR already exists for branch | `glab mr create` reports an existing MR | Use `glab mr view` / `glab mr update` instead of creating |
| Release tag missing | `glab release create <tag>` cannot find the tag | Pass `--ref <branch-or-sha>` so glab creates the tag, or create the tag first |
| Pipeline not green at merge | `glab mr merge` refused; CI pending/failed | Wait (`glab ci status --wait`) or use `--when-pipeline-succeeds`; never force the merge |
| Empty result set | `glab ... -F json` returns `[]` | Treat with a `jq` fallback (`// empty`) and branch on the empty value |
| Wrong/ambiguous host | Command hit the wrong instance | Re-issue with explicit `--hostname`/`GITLAB_HOST` (see authentication.md) |

## Infrastructure failures (HARD STOP)

These mean the environment, not your command logic, is broken. Per `SKILL.md`, when one
occurs: **STOP IMMEDIATELY, print the exact failing command and exact error output, attempt
no workarounds, use no alternate tools, modify no configuration, and report.**

Triggers include:

- `command not found: glab` (or `jq`) — tooling missing.
- Authentication failures: expired/revoked/invalid token, `401`/`403`, insufficient scope.
- Config inaccessible or corrupt (`config.yml` unreadable, `GLAB_CONFIG_DIR` not writable).
- Permission denied (`EACCES`) on any file or socket.
- Any error you cannot map to a recognized state above.

The reason this is a hard stop rather than a retry: these failures are not fixed by trying
again or by "just one more thing," and a workaround (rotating a token, rewriting config,
switching tools) hides the real problem from the human who must fix it.

## Verbatim error propagation

When you stop or report, propagate the error **verbatim** — do not paraphrase, summarize, or
"clean up" `glab`'s output. The exact command and exact stderr are what let a human diagnose
the cause; a paraphrase loses the very details (host, scope, error code) that matter.

```bash
if ! out=$(glab mr merge "$MR" --yes 2>err.txt); then
  echo "COMMAND: glab mr merge $MR --yes"
  cat err.txt            # exact, unedited glab output
  # classify per the decision procedure above; if infrastructure → stop and report
fi
```
