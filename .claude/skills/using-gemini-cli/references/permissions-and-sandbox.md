# Gemini CLI — Permissions & Sandbox (deep dive)

Verified against `geminicli.com/docs/cli/sandbox/`, the configuration reference, and
`google-gemini/gemini-cli` docs in **June 2026** (v0.38.x). Re-confirm with
`gemini --help` for your installed version. `⚠ UNVERIFIED` marks anything not
confirmed against the official docs.

## Table of contents

- [Approval model](#approval-model)
- [HARD STOP on error](#hard-stop-on-error)
- [Sandbox: why and when](#sandbox-why-and-when)
- [Sandbox backends](#sandbox-backends)
- [macOS Seatbelt profiles](#macos-seatbelt-profiles)
- [Mounts and extra flags](#mounts-and-extra-flags)

## Approval model

Gemini gates every tool call (file writes, shell execution, etc.) behind an
**approval mode**, selected with `--approval-mode <mode>`:

| Mode        | Behavior                                                                 |
|-------------|--------------------------------------------------------------------------|
| `default`   | Prompt the user for approval on each tool call. Safest; needs a human.    |
| `auto_edit` | Auto-approve edit tools (`replace`, `write_file`); prompt for everything else (e.g. shell). |
| `yolo`      | Auto-approve **all** tool calls. Same as the `--yolo` flag / Ctrl+Y toggle in the REPL. |

Key properties:

- `yolo` **cannot** be set as a default in `settings.json` — it must be passed on the
  command line every run. This is an intentional guardrail so a session never silently
  runs with full permissions.
- `⚠ UNVERIFIED`: a reported interaction (issue #13792) where disabling yolo also
  disabled `approval-mode=auto_edit`. Treat the two as potentially coupled and test
  your exact version rather than assuming independence.

### Choosing a mode

- **Interactive, human present:** `default`.
- **Semi-autonomous edits, human watching shell commands:** `auto_edit`.
- **Fully autonomous / subagent / CI:** `yolo` **paired with `--sandbox`** so the
  blast radius is contained. Never run `yolo` un-sandboxed against a real working tree
  you care about.

## HARD STOP on error

When a `gemini` invocation fails — non-zero exit, or an auth / permission / quota /
sandbox error in its output — **stop immediately**:

1. Surface the exact failing command and the exact error text verbatim.
2. Do **not** retry blindly.
3. Do **not** broaden the approval mode (e.g. jump to `yolo`) to "get past" an error.
   Picking a wider mode is a deliberate decision about acceptable autonomy, never an
   error-recovery tactic.

This matters most in automation: a silent retry-with-more-permission loop is exactly
how an autonomous agent does damage.

## Sandbox: why and when

The sandbox isolates tool execution (filesystem and network) from the host, so an
auto-approved or buggy tool call cannot wander outside the project. Enable per-run:

```bash
gemini --sandbox -p "…"     # or -s
export GEMINI_SANDBOX=true  # true | docker | podman | sandbox-exec
```

`--yolo` / `--approval-mode=yolo` turns the sandbox **on by default**. Recommend the
sandbox for any autonomous or subagent-driven run — it is what makes broad approval
modes safe to use.

## Sandbox backends

`GEMINI_SANDBOX` selects the backend:

- `sandbox-exec` — macOS Seatbelt (kernel-level, Apple-native; see profiles below).
- `docker` / `podman` — container isolation, cross-platform. Your current working
  directory is mounted **at the same absolute path** inside the container, so paths
  in prompts and output line up with the host.
- `true` — use the platform default.

## macOS Seatbelt profiles

On macOS, Seatbelt applies restrictions via `sandbox-exec`. Six built-in profiles,
selected with the `SEATBELT_PROFILE` env var:

| Profile               | Gist                                                       |
|-----------------------|------------------------------------------------------------|
| `permissive-open`     | **Default.** Blocks writes outside the project dir; allows reading system libs/binaries; unrestricted outbound network. |
| `permissive-proxied`  | Permissive file access; network forced through a proxy.    |
| `restrictive-open`    | Tighter file restrictions; open network.                   |
| `restrictive-proxied` | Tighter file restrictions; proxied network.                |
| `strict-open`         | Strictest file restrictions; open network.                 |
| `strict-proxied`      | Strictest file restrictions; proxied network.              |

The `-open` vs `-proxied` axis is network; the `permissive`/`restrictive`/`strict`
axis is filesystem. Start at the default and tighten only if a profile still lets a
run reach something it should not.

## Mounts and extra flags

- `SANDBOX_MOUNTS` — mount file system paths from **outside** the project workspace
  into the sandbox when a run legitimately needs them (e.g. a shared cache).
- `SANDBOX_FLAGS` — inject custom flags into the `docker`/`podman` command for
  advanced setups. Use sparingly: disabling container security features here can
  defeat the point of sandboxing.
