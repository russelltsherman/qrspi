# Gemini CLI — Multi-Agent Orchestration (deep dive)

How to call the Gemini CLI as a sub-process from another agent or script. Verified
against the official docs in **June 2026** (v0.38.x); re-confirm flags with
`gemini --help`. `⚠ UNVERIFIED` marks anything not confirmed against official docs.

## Table of contents

- [Mental model: stateless calls](#mental-model-stateless-calls)
- [Passing context in](#passing-context-in)
- [Capturing results out](#capturing-results-out)
- [Filesystem as the handoff channel](#filesystem-as-the-handoff-channel)
- [Sandbox and approval for autonomous runs](#sandbox-and-approval-for-autonomous-runs)
- [HARD STOP on error](#hard-stop-on-error)
- [Deprecation impact](#deprecation-impact)

## Mental model: stateless calls

A non-interactive `gemini -p` call is a **pure function of its inputs**. It does
**not** persist a session — call N+1 remembers nothing from call N. There is no
conversation id to thread through. Every piece of state the next call needs must be
re-supplied explicitly. Design orchestration around this: each invocation is a fresh,
self-contained unit of work.

(The interactive REPL keeps a session, but it blocks on human input and is unsuitable
for orchestration — use `-p` only.)

## Passing context in

Two channels, combinable:

```bash
# Instruction via -p, bulk context via stdin (appended to the prompt).
cat build.log | gemini -p "Identify the root cause of this build failure."

# Compose multiple sources on stdin.
{ git diff; echo '---'; cat NOTES.md; } | gemini -p "Update NOTES.md for this diff."
```

Standing project conventions can also live in `GEMINI.md` (auto-prepended), but for
orchestration prefer explicit prompt/stdin so a call is reproducible from its
arguments alone.

## Capturing results out

The model's answer goes to **stdout**; capture it like any command:

```bash
result="$(printf '%s' "$context" | gemini -p "$instruction")"

# Machine-parseable output:
gemini --output-format json -p "$instruction" > result.json
```

Keep stdout clean for the payload. `⚠ UNVERIFIED`: the exact JSON schema of
`--output-format json` — inspect a sample for your version before parsing fields.

## Filesystem as the handoff channel

Because calls are stateless, **on-disk artifacts are the durable handoff channel**
between steps and between agents. A robust pattern:

1. Orchestrator writes inputs to a known path (e.g. `/tmp/run/input.md`).
2. `gemini -p "Read /tmp/run/input.md and write your answer to /tmp/run/output.md"`
   (with an approval/sandbox mode that permits the write).
3. Orchestrator reads `/tmp/run/output.md` and verifies it is non-empty before
   proceeding.

This mirrors how stateless workers coordinate generally: short, explicit paths;
verify the artifact exists and is non-empty as the success gate; never assume an
in-memory result survived across a process boundary.

## Sandbox and approval for autonomous runs

For unattended runs:

- Authenticate with an **API key in the environment** (`GEMINI_API_KEY`), not OAuth —
  no interactive browser step.
- Run **sandboxed** (`--sandbox`) so auto-approved tool calls cannot escape the
  project.
- Choose the approval mode deliberately: `auto_edit` when only edits should be
  automatic, `yolo` only when paired with the sandbox. See
  `permissions-and-sandbox.md`.

## HARD STOP on error

A blocked or failed invocation must surface the **exact** error verbatim and stop —
no silent retry, no permission escalation to push through. In an orchestration loop
this is critical: an automatic "try again with `--yolo`" is how an agent causes
damage. Bubble the failure up to the orchestrator (or human) with the failing command
and its output intact.

## Deprecation impact

Per the June 18, 2026 deprecation, free-tier and Google AI Pro/Ultra access to this
CLI stops; paid Gemini API keys and Gemini Code Assist Standard/Enterprise/Cloud
licenses are documented as continuing. For automation this means: pin to a paid API
key path for anything that must outlive the cutover, and track **Antigravity CLI** as
the successor (it is stated to support subagents, hooks, extensions, and agent skills,
but not 1:1 feature parity, and is not open source as of this writing). Re-verify the
current state before standing up new long-lived pipelines.
