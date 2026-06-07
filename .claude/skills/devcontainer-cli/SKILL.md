---
name: devcontainer-cli
description: Author, run, and debug Dev Containers with the @devcontainers/cli and devcontainer.json — the open-source Dev Container spec, not editor-managed containers. Use when working with .devcontainer/ files, the `devcontainer` CLI (up/exec/build/read-configuration/run-user-commands), lifecycle hooks (postCreateCommand and friends), devcontainer features/lockfiles, or running the same dev container in CI via devcontainers/ci. Do NOT use for general Docker/Kubernetes/Codespaces work that does not involve the Dev Container spec.
command: /devcontainer-cli
argument-hint: "(no arguments — guidance skill)"
allowed-tools: Read, Bash, Edit, Write, Grep, Glob
---

# devcontainer-cli

Guidance for building and operating **Dev Containers** with the open-source
`@devcontainers/cli` and a `.devcontainer/devcontainer.json`. A Dev Container is
a reproducible, fully-configured development environment described as code, so
every developer — and CI — works in the identical environment.

This skill is the **entry point**. It carries the workflow and opinionated
defaults; the detailed command, schema, lifecycle, and CI references live
alongside it under `references/` and are cited at each decision point below.
Read the relevant reference when you need the full detail rather than
inlining it here.

## Install & primary workflow

Install the CLI once, then drive containers from your project root:

```bash
npm install -g @devcontainers/cli
devcontainer up --workspace-folder .                       # create/start the env
devcontainer exec --workspace-folder . bash -lc "npm test" # run inside it
```

The everyday loop is: **edit `devcontainer.json` → `up` → `exec`**. When the
image or config changed and you want a clean rebuild rather than reusing a stale
container, add `--remove-existing-container`. For the full command set
(`up`, `exec`, `build`, `read-configuration`, `run-user-commands`) and every
flag, see [`references/cli-commands.md`](references/cli-commands.md). When the
environment misbehaves, `devcontainer read-configuration --workspace-folder .`
prints the *effective* merged config (base + features + defaults) so you can see
exactly what the CLI resolved — start debugging there.

## Configuring devcontainer.json

A devcontainer derives its container in exactly one of three mutually exclusive
ways — `image` (prebuilt, fastest), `build` (from a Dockerfile, for
project-specific layers), or Docker Compose (multi-service). Choose one. For the
key-by-key cheatsheet (`image`/`build`, `remoteUser`, `forwardPorts`,
`customizations`, `mounts`, `features`), see
[`references/devcontainer-json-schema.md`](references/devcontainer-json-schema.md).

### Opinionated defaults (general-project advice)

For a typical project, prefer these — they avoid the most common
Dev Container failure modes:

- **Run as a non-root user.** Set `remoteUser` to a non-root user (e.g. `node`,
  `vscode`). Running as root is the usual cause of root-owned files on the host
  and permission errors later. Match `remoteUser` to the UID that owns mounted
  files.
- **Commit the lockfile.** Pin feature versions and commit
  `.devcontainer-lock.json`, then enforce it in CI with
  `devcontainer up --frozen-lockfile` so a drifting feature version is a hard
  error, not a silent upgrade.
- **Use named volumes for dependency directories.** Mount `node_modules`,
  package caches, etc. as Docker-managed **named volumes** rather than
  bind-mounting from the host — you get container-native ownership and far
  better I/O performance.

> **Caveat — this repo is a deliberate exception.** These defaults target
> general projects optimizing for speed and convenience. *This* repository
> intentionally ships a hardened, **build-based** devcontainer (a Dockerfile
> build rather than a prebuilt `image`) as a deliberate security/reproducibility
> choice. Do not "simplify" it to a plain `image` to match the advice above —
> the build-based setup here is intentional. Apply the general defaults to other
> projects, not to this repo's hardened container.

## Lifecycle hooks

The spec defines **six** lifecycle hooks that run at distinct points
(`initializeCommand` on the host; then `onCreateCommand`,
`updateContentCommand`, `postCreateCommand`, `postStartCommand`,
`postAttachCommand` in the container). Choosing the right hook is the difference
between a fast, cacheable build and a slow, fragile one — for example, put
dependency restoration in `updateContentCommand` so prebuilds cache it, and keep
`postAttachCommand` light because it runs on every attach. A **non-zero exit
fails the hook and skips the rest**, and any re-running hook must be idempotent.
For the full decision tree, execution order, the three command forms
(string/array/object-parallel), and the skip-on-failure rule, see
[`references/lifecycle-decision-tree.md`](references/lifecycle-decision-tree.md).
You can re-run just the hooks against a live container with
`devcontainer run-user-commands` (see `references/cli-commands.md`).

## Docker Compose (multi-service)

When the dev environment is more than one container (app + db + cache), use
Docker Compose. The Compose keys **replace** `image`/`build`:
`dockerComposeFile` (the Compose file(s)), `service` (which service the editor
attaches to), `workspaceFolder` (path inside the container), and
`shutdownAction` (`stopCompose` / `stopContainer` / `none` on disconnect).
The remaining devcontainer keys (lifecycle hooks, `forwardPorts`,
`customizations`) still apply to the chosen service. See the Compose section of
[`references/devcontainer-json-schema.md`](references/devcontainer-json-schema.md)
for the full key table and an example.

## Running the same container in CI

Run the **identical** dev container in CI that developers use locally to
eliminate "works on my machine" drift. The `devcontainers/ci` GitHub Action
wraps the CLI: `runCmd` is equivalent to `up` then `exec`. The high-value
pattern is **pre-build and push**: build the image once on the default branch,
push it to a registry (e.g. GHCR), seed later builds with `cacheFrom`
(the registry cache, mapping to the CLI's `--cache-from`), then point local
`devcontainer.json` at that published `image` so everyone pulls the same
artifact CI validated. For the workflow YAML, caching, and the
build-then-reuse-as-`image` pattern, see
[`references/cicd-workflows.md`](references/cicd-workflows.md).

## Troubleshooting

- **Permission / ownership errors** (`EACCES`, root-owned files). Almost always
  a `remoteUser` mismatch — the process user's UID does not own the mounted
  files. Set `remoteUser` to a non-root user that matches the file owner, and
  run `devcontainer read-configuration` to confirm which user is actually in
  effect. (schema: `references/devcontainer-json-schema.md`.)
- **Volume ownership** for dependency dirs. If `node_modules`/caches are
  host-owned or slow, move them to a **named volume** (`mounts`) so Docker owns
  them with container-native UID and performance instead of bind-mounting from
  the host. (schema: `references/devcontainer-json-schema.md`.)
- **Stale build / cache invalidation.** Old layers or config not taking effect:
  rebuild clean with `devcontainer up --remove-existing-container`, or
  `devcontainer build --no-cache`. In CI, seed fresh layers with `--cache-from`
  / `cacheFrom`. (commands: `references/cli-commands.md`; CI:
  `references/cicd-workflows.md`.)
- **Lifecycle hook failures.** A hook exited non-zero, so creation/start is
  reported failed and later hooks were skipped. Re-run just the hooks with
  `devcontainer run-user-commands` to iterate, guard genuinely optional steps
  with `|| true`, and make re-running hooks idempotent. (decision tree:
  `references/lifecycle-decision-tree.md`.)
- **Slow builds.** Cold-cache Dockerfile builds are slow. Pre-build and push the
  image in CI, reuse it locally via an `image:` reference, and seed the cache
  with `--cache-from` / `cacheFrom`; move cacheable dependency work into
  `updateContentCommand` so prebuilds capture it. (CI:
  `references/cicd-workflows.md`; hooks:
  `references/lifecycle-decision-tree.md`.)
