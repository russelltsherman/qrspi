# Security Hardening Checklist

Hardening rules for GitHub Actions workflows. These map directly to
[zizmor](https://github.com/woodruffw/zizmor) static-analysis checks; a workflow
authored under these rules should pass `zizmor` clean. SHA-pinning is the
canonical hard rule — it is stated in `SKILL.md` and **restated** here so the
checklist is self-contained; both must agree.

## 1. Pin every action to a full commit SHA (hard rule)

Tags and branches are mutable: an attacker who compromises an action repo can
re-point `v4` at malicious code. A 40-hex commit SHA is immutable.

```yaml
# WRONG — mutable reference
- uses: actions/checkout@v4
# WRONG — branch is even worse
- uses: actions/checkout@main
# RIGHT — full SHA, version pinned in a trailing comment for humans + Dependabot
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

- Pin **third-party** actions without exception. Pin **first-party**
  (`actions/*`, `github/*`) actions too — defense in depth and consistency.
- Keep the `# vX.Y.Z` comment: Dependabot / Renovate use it to propose SHA bumps,
  so pinning does not freeze you on stale, vulnerable versions.
- zizmor check: `unpinned-uses`.

## 2. Least-privilege `permissions` (default-deny)

The `GITHUB_TOKEN` defaults to broad scopes. Set an explicit empty default at the
top of every workflow, then grant the minimum each job needs.

```yaml
permissions: {}          # default-deny for the whole workflow
jobs:
  build:
    permissions:
      contents: read     # only what this job needs
  release:
    permissions:
      contents: write
      id-token: write    # OIDC — see oidc-setup-patterns.md
```

- Never rely on the repository/organization default token scopes.
- Grant `write` scopes only on the specific job that performs the write.
- zizmor checks: `excessive-permissions`, `token-permissions`.

## 3. Avoid expression injection in `run:` blocks

Interpolating attacker-controllable `${{ ... }}` context (PR titles, branch
names, issue bodies, commit messages) directly into a shell `run:` is a code-
injection vector — the value is substituted *before* the shell parses the line.

```yaml
# WRONG — PR title is attacker-controlled, runs as shell
- run: echo "Title: ${{ github.event.pull_request.title }}"
# RIGHT — pass through an environment variable; shell quoting protects you
- env:
    TITLE: ${{ github.event.pull_request.title }}
  run: echo "Title: $TITLE"
```

- Treat all `github.event.*` free-text fields as untrusted.
- Prefer `env:` indirection; quote the variable in the script.
- zizmor check: `template-injection`.

## 4. `pull_request_target` rules

`pull_request_target` runs with **write** permissions and **secrets** in the
context of the base repo, but is triggered by forked PRs. Checking out and
executing PR-head code under this trigger hands secrets/token to attackers.

- Do **not** check out the PR head (`github.event.pull_request.head.sha` /
  `head.ref`) under `pull_request_target`.
- If you must process PR code (e.g. label, comment), check out the **base** ref
  only and never execute fork-supplied code/build scripts.
- Prefer `pull_request` (no secrets, read-only token) for anything that builds or
  runs untrusted PR code. Use `workflow_run` to gate privileged follow-up.
- zizmor check: `dangerous-triggers`, `artipacked` (for related checkout leaks).

## 5. CODEOWNERS for workflow files

- Add `.github/workflows/` (and this skill's reusable workflows) to `CODEOWNERS`
  so changes to CI require review from a trusted owner.
- Enable branch protection requiring CODEOWNERS review; workflow edits are a
  high-value supply-chain target.

## 6. Additional hardening

- Set `persist-credentials: false` on `actions/checkout` when the token is not
  needed for later steps (prevents credential leakage into the git config).
- Restrict `concurrency` and avoid `actions/github-script` with untrusted input.
- Pin runner images explicitly (`ubuntu-24.04`, not `ubuntu-latest`) for
  reproducibility where supply-chain stability matters.
- Scope secrets to GitHub **Environments** with required reviewers for deploys.

## zizmor check → rule map

| zizmor check          | Rule above |
|-----------------------|------------|
| `unpinned-uses`       | §1 SHA-pinning |
| `excessive-permissions` / `token-permissions` | §2 least-privilege |
| `template-injection`  | §3 expression injection |
| `dangerous-triggers`  | §4 `pull_request_target` |
| `artipacked`          | §4 / §6 credential persistence |

Run locally: `zizmor .github/workflows/`. Treat findings as blocking.
