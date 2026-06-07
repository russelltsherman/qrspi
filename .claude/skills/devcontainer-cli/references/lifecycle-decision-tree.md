# devcontainer lifecycle hooks — decision tree

The Dev Container spec defines **six** lifecycle command hooks. They run at
distinct points in the create/start/attach sequence. Picking the right hook for
a task is the difference between a fast, cacheable build and a slow, fragile
one.

---

## Execution order

For a brand-new container:

```
initializeCommand        (on the HOST, before the container exists)
  └─ onCreateCommand          (in container, once, at creation)
       └─ updateContentCommand   (in container, at creation AND on content updates / prebuilds)
            └─ postCreateCommand      (in container, once, after the source is available)
                 └─ postStartCommand       (in container, every time the container starts)
                      └─ postAttachCommand      (in container, every time a tool attaches)
```

For an **existing** container that is merely (re)started, the create-time hooks
(`onCreateCommand`, `updateContentCommand`, `postCreateCommand`) are skipped;
only `postStartCommand` and `postAttachCommand` run again.

---

## When to use each hook

### `initializeCommand`

- **Runs:** on the **host**, before the container is created/started, every
  time.
- **Use for:** host-side preparation that must happen before build — e.g.
  generating a file the build needs, logging into a registry, `docker
  compose pull`. Keep it minimal; it blocks startup and runs outside the
  container.

### `onCreateCommand`

- **Runs:** inside the container, **once** when it is first created, as the
  earliest in-container step. Source code may not be fully available yet.
- **Use for:** baseline setup that belongs in the image-creation phase and is
  safe to bake into a prebuild — installing OS-level tools, seeding caches.

### `updateContentCommand`

- **Runs:** inside the container at creation **and** whenever content is
  updated, including during **prebuilds** (e.g. GitHub Codespaces prebuilds).
- **Use for:** work that depends on the repository content and should be part
  of a prebuild image — e.g. `npm ci`, restoring dependencies. Putting
  dependency installation here (rather than `postCreateCommand`) lets prebuilds
  cache it.

### `postCreateCommand`

- **Runs:** inside the container, **once** after creation, after the source
  tree is available.
- **Use for:** project bootstrap that needs the full checkout but does not
  belong in a prebuild — final `npm install`, DB migrations/seeding, generating
  local config.

### `postStartCommand`

- **Runs:** inside the container **every time it starts** (including restarts).
- **Use for:** starting background services or anything that must run on each
  boot — `service postgresql start`, re-establishing a tunnel. Must be safe to
  run repeatedly.

### `postAttachCommand`

- **Runs:** inside the container **every time a tool/editor attaches**.
- **Use for:** per-session, interactive niceties — printing a welcome/status
  message, `tail -f` a log. Avoid heavy work here; it runs on every attach.

---

## Object & parallel syntax

Each hook accepts three forms:

1. **String** — run via the shell:
   ```jsonc
   { "postCreateCommand": "npm install" }
   ```
2. **Array** — run directly (no shell; argv form, safer for args with spaces):
   ```jsonc
   { "postCreateCommand": ["npm", "install"] }
   ```
3. **Object** — named entries run **in parallel** with each other:
   ```jsonc
   {
     "postCreateCommand": {
       "deps": "npm install",
       "tools": ["bash", "-lc", "pip install -r requirements.txt"]
     }
   }
   ```
   Use the object form to overlap independent setup steps and shorten total
   create time.

---

## Skip-on-failure & idempotency rule

- **Skip-on-failure:** a **non-zero exit** from any lifecycle command fails that
  hook — the container creation/start is reported as failed and **subsequent
  hooks are skipped** rather than silently continuing. Do not swallow errors you
  care about; conversely, guard genuinely optional steps (e.g. append
  `|| true`) so a non-critical failure does not abort the whole sequence.
- **Idempotency:** hooks that re-run (`updateContentCommand`,
  `postStartCommand`, `postAttachCommand`) **must be idempotent** — safe to run
  many times. Guard service starts (`pgrep ... || start`), use `npm ci` over
  ad-hoc mutation, and avoid appending to files unconditionally.
