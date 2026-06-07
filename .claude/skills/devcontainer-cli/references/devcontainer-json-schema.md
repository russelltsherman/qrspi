# devcontainer.json — schema cheatsheet

`.devcontainer/devcontainer.json` (or `.devcontainer.json` at the repo root)
describes the development container. It is JSON-with-comments (JSONC). The keys
below are the ones you reach for most; the full spec lives at
<https://containers.dev/implementors/json_reference/>.

---

## Choosing the base: `image` vs `build` vs Compose

A devcontainer derives its container in exactly one of three mutually exclusive
ways. Pick one.

### `image` — use a prebuilt image

Fastest path. Point at a published image (Docker Hub, GHCR, etc.). No local
Dockerfile build. Ideal when a CI pipeline has already built and pushed the
image (see `cicd-workflows.md`).

```jsonc
{
  "image": "mcr.microsoft.com/devcontainers/typescript-node:20"
}
```

### `build` — build from a Dockerfile

Use when you need project-specific layers (system packages, compiled tools, a
hardened non-root setup). Slower on a cold cache but reproducible.

```jsonc
{
  "build": {
    "dockerfile": "Dockerfile",
    "context": "..",
    "args": { "VARIANT": "20" },
    "cacheFrom": "ghcr.io/org/repo-dev:latest"
  }
}
```

`image` and `build` are mutually exclusive — set one, not both.

### Docker Compose — multi-service environments

Use when the dev environment is more than one container (app + db + cache).
Compose keys replace `image`/`build`:

| Key | Meaning |
|-----|---------|
| `dockerComposeFile` | Path (or array of paths) to the Compose file(s); later files override earlier ones. |
| `service` | Name of the service in the Compose file that the editor attaches to (the "dev" container). |
| `workspaceFolder` | Path **inside** the container where the project is mounted / where the editor opens. |
| `shutdownAction` | What to do when the editor disconnects: `stopCompose` (stop all services), `stopContainer`, or `none`. |

```jsonc
{
  "dockerComposeFile": ["../docker-compose.yml", "docker-compose.dev.yml"],
  "service": "app",
  "workspaceFolder": "/workspaces/repo",
  "shutdownAction": "stopCompose"
}
```

---

## Common configuration keys

### `remoteUser`

The user the editor/process runs as inside the container (e.g. `node`,
`vscode`). Set this to a **non-root** user for safer, correctly-owned files.
Distinct from `containerUser` (the user the container *starts* as). A mismatch
between `remoteUser` and the UID that owns mounted files is the usual cause of
permission errors.

```jsonc
{ "remoteUser": "node" }
```

### `forwardPorts`

Ports inside the container to make reachable from the host. Pair with
`portsAttributes` to label them or set `onAutoForward` behavior.

```jsonc
{
  "forwardPorts": [3000, 5432],
  "portsAttributes": { "3000": { "label": "web", "onAutoForward": "openBrowser" } }
}
```

### `customizations`

Tool-specific settings namespaced by tool. The `vscode` namespace carries
`settings` and `extensions`; other tools (e.g. `codespaces`) have their own.

```jsonc
{
  "customizations": {
    "vscode": {
      "extensions": ["dbaeumer.vscode-eslint"],
      "settings": { "editor.formatOnSave": true }
    }
  }
}
```

### `mounts`

Extra bind or volume mounts beyond the default workspace mount. Use a **named
volume** for dependency directories (e.g. `node_modules`, package caches) so
they live in Docker-managed storage with container-native ownership and
performance, instead of being bind-mounted from the host.

```jsonc
{
  "mounts": [
    "source=repo-node-modules,target=/workspaces/repo/node_modules,type=volume"
  ]
}
```

### `features`

Composable, versioned add-ons (language runtimes, CLIs, tools) layered onto the
base image without editing a Dockerfile. Keyed by feature OCI reference with an
options object.

```jsonc
{
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/github-cli:1": { "version": "latest" }
  }
}
```

Feature versions resolve into `.devcontainer-lock.json`; pin them and commit the
lockfile for reproducibility (`devcontainer up --frozen-lockfile` enforces it in
CI — see `cli-commands.md`).

---

## Lifecycle commands

`devcontainer.json` also carries the six lifecycle hooks (`initializeCommand`,
`onCreateCommand`, `updateContentCommand`, `postCreateCommand`,
`postStartCommand`, `postAttachCommand`). Their selection, order, and syntax are
documented separately in `lifecycle-decision-tree.md`.
