# devcontainer CLI — command & flag reference

The `@devcontainers/cli` is the open-source reference implementation of the Dev
Container spec. Install it globally with npm, then drive containers from a
`.devcontainer/devcontainer.json` in your project.

```bash
npm install -g @devcontainers/cli
devcontainer --version
```

All commands accept `--workspace-folder <path>`, which points at the project
root that contains `.devcontainer/` (or a top-level `devcontainer.json`). When
omitted, most commands default to the current directory.

---

## `devcontainer up`

Creates (or reuses) and starts the dev container described by the
configuration, running the create/start lifecycle hooks. This is the primary
"bring the environment online" command.

```bash
devcontainer up --workspace-folder .
```

Useful flags:

- `--workspace-folder <path>` — project root holding `.devcontainer/`.
- `--remove-existing-container` — tear down any container previously created
  for this workspace before creating a fresh one. Use this when the image or
  configuration changed and you want a clean rebuild rather than reusing the
  stale container.
- `--id-label <name=value>` — extra labels used to identify the container
  (lets you run more than one container per workspace).
- `--mount` — add an extra bind/volume mount for this run.

Output includes a JSON result line with `outcome`, `containerId`, and
`remoteUser`, which CI and scripts can parse.

## `devcontainer exec`

Runs a command **inside** the already-running dev container, as the configured
`remoteUser`, with the container's environment and working directory.

```bash
devcontainer exec --workspace-folder . bash -lc "npm test"
devcontainer exec --workspace-folder . node --version
```

Everything after the flags is the command (and its arguments) to execute. This
is how CI runs builds/tests against the same environment developers use.

## `devcontainer build`

Builds the dev container **image** without creating or starting a container.
Useful for pre-building and pushing an image to a registry so later `up` runs
(local or in CI) are fast.

```bash
devcontainer build --workspace-folder . --image-name ghcr.io/org/repo-dev:latest
devcontainer build --workspace-folder . --push true \
  --image-name ghcr.io/org/repo-dev:latest
```

Useful flags:

- `--image-name <name>` — tag for the built image (repeatable).
- `--push true` — push the built image to its registry.
- `--no-cache` — build without the layer cache.
- `--cache-from <ref>` — seed the build cache from a registry image (see
  `cicd-workflows.md`).
- `--platform <os/arch>` — target platform(s) for the build.

## `devcontainer read-configuration`

Resolves and prints the **effective** merged configuration (base
`devcontainer.json` plus any applied features and defaults) as JSON. Use it to
debug what the CLI actually sees — which `remoteUser`, ports, mounts, and
lifecycle commands are in effect after feature merging.

```bash
devcontainer read-configuration --workspace-folder . | jq .
devcontainer read-configuration --workspace-folder . --include-features-configuration
```

## `devcontainer run-user-commands`

Runs the **lifecycle hook commands** (`onCreateCommand`,
`updateContentCommand`, `postCreateCommand`, `postStartCommand`,
`postAttachCommand`) against a running container, without recreating it. Handy
to re-trigger setup steps after editing the config, or to run only the
post-create steps in a pipeline.

```bash
devcontainer run-user-commands --workspace-folder .
```

See `lifecycle-decision-tree.md` for which hooks fire and in what order.

---

## Named flags quick reference

| Flag | Commands | Purpose |
|------|----------|---------|
| `--workspace-folder <path>` | all | Project root containing `.devcontainer/`. |
| `--remove-existing-container` | `up` | Discard the existing container and create a clean one (force-rebuild path). |
| `--frozen-lockfile` | `up` | Fail rather than mutate the cached feature/config lockfile (`.devcontainer-lock.json`); enforces reproducible, lockfile-pinned feature versions — use in CI so a drifting feature version is an error, not a silent upgrade. |

Other commonly used flags: `--image-name`, `--push`, `--no-cache`,
`--cache-from`, `--platform`, `--id-label`, `--mount`, `--config <path>`.
