# Scripting glab in CI and agents

This is the mechanics layer: how to turn `glab` invocations into deterministic, parseable
steps that an agent or CI job can branch on without a human in the loop. The guiding idea is
that the *caller* should make decisions on structured data, and a multi-step flow should
expose a **single result** rather than forcing the caller to re-parse intermediate output.

## Merge-after-green

The rule: an MR is merged only after its pipeline is green. Two non-interactive shapes:

```bash
# A) Server-side auto-merge: GitLab waits for the pipeline, then merges. No blocking.
glab mr merge "$MR" --when-pipeline-succeeds --squash --remove-source-branch --yes

# B) Client-side wait: block here, inspect the result, then merge yourself.
glab ci status --wait                       # returns when the pipeline reaches a terminal state
status=$(glab ci list -F json | jq -r '.[0].status')
[ "$status" = "success" ] && glab mr merge "$MR" --squash --remove-source-branch --yes
```

Use (A) for fire-and-forget automation; use (B) when later steps depend on the merge having
actually happened in this run. (Confirm `--when-pipeline-succeeds` vs `--auto-merge` and the
`glab ci status` wait flag against your installed version — see `commands.md`.)

## Parse JSON, never scrape tables

Human-formatted tables are not a stable contract; column widths and wording change. Use
`-F json` where available, or `glab api` (always JSON), and extract with `jq`.

```bash
# Get the iid of the open MR for the current branch
branch=$(git rev-parse --abbrev-ref HEAD)
mr_iid=$(glab mr list --source-branch "$branch" --state opened -F json | jq -r '.[0].iid // empty')
```

Always provide a `jq` fallback (`// empty`, `// "unknown"`) so an empty result is a value you
can test, not a crash.

## Exit codes

`glab` returns `0` on success and non-zero on failure. Check it explicitly; do not infer
success from the presence of stdout.

```bash
if ! out=$(glab mr view "$MR" -F json 2>err.txt); then
  # non-zero exit: decide recognized-state vs HARD STOP from the message (see error-handling.md)
  cat err.txt
fi
```

A non-zero exit that corresponds to a **recognized state** (e.g. "MR already exists") is
handled in-band. A non-zero exit from auth/config/tooling is a **HARD STOP** — print the
exact command and output and stop. See `error-handling.md` for the decision procedure.

## The single-`{"ok": ...}` envelope pattern

Fold a multi-step flow into one JSON object so the caller branches on a single value instead
of re-deriving state from scattered output. Emit `ok: false` plus context on any failure.

```bash
set -euo pipefail
emit() { printf '%s\n' "$1"; exit "${2:-0}"; }

branch=$(git rev-parse --abbrev-ref HEAD)
mr_iid=$(glab mr list --source-branch "$branch" --state opened -F json | jq -r '.[0].iid // empty')

if [ -z "$mr_iid" ]; then
  # recognized state: no MR yet → create one, then re-read
  mr_iid=$(glab mr create --fill --yes >/dev/null && \
           glab mr list --source-branch "$branch" --state opened -F json | jq -r '.[0].iid')
fi

if glab mr merge "$mr_iid" --when-pipeline-succeeds --squash --remove-source-branch --yes; then
  emit "$(jq -nc --arg iid "$mr_iid" '{ok:true, mr:($iid|tonumber), action:"auto-merge-armed"}')"
else
  emit "$(jq -nc --arg iid "$mr_iid" '{ok:false, mr:($iid|tonumber), error:"merge request refused"}')" 1
fi
```

The caller then needs only: `result=$(./flow.sh); [ "$(jq -r .ok <<<"$result")" = true ]`.

## CI environment notes

- Set `GITLAB_TOKEN` (and `GITLAB_HOST` for self-hosted) as masked CI/CD variables; verify
  with `glab auth status` as the first real step.
- Isolate config in ephemeral runners with `GLAB_CONFIG_DIR=$(mktemp -d)` so concurrent jobs
  do not share state.
- Keep `set -euo pipefail` on so an unexpected non-zero exit surfaces immediately rather than
  letting a later step act on stale data.
