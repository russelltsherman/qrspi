# glab authentication

How `glab` decides *who* you are and *which* GitLab instance it talks to. Getting this
right is the difference between a script that runs unattended and one that hangs on a login
prompt or silently hits the wrong host.

## Two ways to authenticate

### 1. Token (use this for agents and CI)

`glab` reads a Personal Access Token (PAT) from the environment with no prompting. This is
the only auth method appropriate for an agent or a CI job, because it never blocks on input.

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
export GITLAB_HOST="gitlab.example.com"   # omit entirely for gitlab.com
glab auth status                          # always verify before doing real work
```

- The PAT needs the scopes your operations require — typically `api` (broad) or the
  narrower `read_api` + `write_repository` for read/push flows. A token missing a scope
  surfaces as a permissions/auth failure → that is a **HARD STOP**, not a recognized state.
- Inside GitLab CI, the job-scoped `CI_JOB_TOKEN` is limited; for cross-project or
  privileged actions provide an explicit PAT (often as a masked CI/CD variable named
  `GITLAB_TOKEN`).
- To log in non-interactively from a token without env vars, pipe it:
  `printf '%s' "$TOKEN" | glab auth login --hostname HOST --stdin`.

### 2. OAuth device flow (humans only)

`glab auth login` walks a person through an interactive OAuth/device-code flow. **Never use
the bare interactive form in a script** — it will block. It is documented here only so you
recognize it and avoid it in automation.

## Host selection — always explicit

There is no in-repo precedent for inferring the host from the git remote, so this skill
**does not guess**. Pick the host explicitly, in this precedence order:

1. `--hostname HOST` flag on the command (most explicit; wins).
2. `GITLAB_HOST` environment variable (good for a whole CI job).
3. Default: `gitlab.com`.

> Open question (design OQ4): whether to instead infer the host from the current repo's
> `origin` remote is an unresolved choice with no in-repo precedent. Until decided, prefer
> explicit `--hostname`/`GITLAB_HOST` and flag any ambiguity to a human rather than guessing.

```bash
glab auth status --hostname gitlab.example.com
glab mr list --hostname gitlab.example.com -R group/project -F json
```

## Multi-host configuration

`glab` stores per-host credentials in its config file (commonly
`~/.config/glab-cli/config.yml`; override the directory with `GLAB_CONFIG_DIR`). The file
holds a `hosts:` map so you can be logged into `gitlab.com` and one or more self-hosted
instances at once. Select among them per-command with `--hostname`/`GITLAB_HOST`.

```bash
glab auth status                 # lists every host you are logged into
GLAB_CONFIG_DIR=/tmp/glab glab auth status   # isolate config (useful in CI sandboxes)
```

## Credential conflicts as named states

When credentials are ambiguous or wrong, classify the situation rather than retrying blindly:

- **Multiple hosts configured, none specified** → recognized state: the command may default
  to `gitlab.com` and hit the wrong instance. Recovery: re-issue with explicit
  `--hostname`/`GITLAB_HOST`.
- **Token expired / revoked / wrong scope** → this is an authentication failure, NOT a
  recoverable state. Follow the **HARD STOP** rule in `SKILL.md`: print the exact failing
  command and error, stop, and report. Do not rotate tokens or edit config to "get past" it.
- **Logged into the wrong host for this repo** → recognized state. Recovery: specify the
  correct `--hostname`; do not assume.

The dividing line, restated: a conflict you can fix by being more *explicit* (which host) is
a recognized state; a credential that is *invalid* is an infrastructure failure and a HARD STOP.
