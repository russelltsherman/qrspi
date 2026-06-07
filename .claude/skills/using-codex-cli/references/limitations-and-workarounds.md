# Limitations and workarounds

Codex is powerful but has sharp edges. Knowing them — and the workaround for each —
saves hours of confused debugging.

## Table of contents

- [Re-run non-determinism](#re-run-non-determinism)
- [macOS sandbox / network bugs](#macos-sandbox--network-bugs)
- [Long-chain limits](#long-chain-limits)
- [Context-window pressure and fresh sessions](#context-window-pressure-and-fresh-sessions)

## Re-run non-determinism

The same prompt can produce different edits across runs — that is expected behavior for
a sampling-based agent, not a bug. The failure mode is *hand-patching a bad run* instead
of letting the agent try again. Use this flow:

```
result looks wrong
   │
   ├─ 1. re-run the same prompt in a FRESH session
   │
   ├─ 2. diff the two attempts (git diff / compare branches)
   │        → which approach is actually correct / cleaner?
   │
   ├─ 3. run the test suite against each candidate
   │
   └─ 4. tests pass → accept that attempt
         tests fail → git restore / discard, then refine the PROMPT
                      (add the missing constraint) and re-run
```

**Worked example.** You ask Codex to "add input validation to the signup endpoint."
Run A rejects empty emails but not malformed ones; run B handles both but breaks an
existing test. Don't merge either blindly: diff them, run the tests (B fails one),
restore to clean, then re-prompt with "...and keep `test_signup_existing` green" — the
explicit constraint usually fixes it on the next run.

Because each run is cheap relative to your time, **re-run before you hand-edit.**

## macOS sandbox / network bugs

macOS uses Apple Seatbelt (`sandbox-exec`) for enforcement, and there are known rough
edges:

- **Network can behave inconsistently** when sandbox mode is set only via
  `config.toml`. The reliable workaround is to set the sandbox with the **`--sandbox`
  flag on the command line** for that run, which takes precedence and applies cleanly.
- `sandbox-exec` is deprecated by Apple (still functional), so warnings may appear;
  they are generally safe to ignore for now.
- When a sandboxed command unexpectedly fails with a permission or network error,
  first reproduce it with an explicit `--sandbox <mode>` flag before assuming the
  command itself is broken — the difference isolates a config-vs-flag problem.

On Linux, enforcement is via Landlock + seccomp (often through bubblewrap); the network
is likewise off by default outside `danger-full-access`.

## Long-chain limits

Very long agent chains (many sequential tool calls in one session) degrade: the agent
loses track of earlier decisions, repeats work, or contradicts prior steps. Mitigations:

- Break a big objective into a few discrete `codex exec` runs or fresh sessions rather
  than one marathon thread.
- Have the agent write intermediate state to a file (notes, a checklist) so a later run
  can pick it up without relying on in-context memory.
- For orchestration, prefer several focused subagent sessions over one ever-growing one
  (see `mcp-server-mode.md`).

## Context-window pressure and fresh sessions

Related to long chains: as a session fills its context window, the earliest content
(your original instructions, key constraints) gets crowded out and quality drifts.

Signs you're hitting it: the agent re-asks things it already knew, ignores a constraint
it followed earlier, or its edits get sloppier deep into a session.

Workaround: **start a fresh session** for the next discrete task, carrying forward only a
short, deliberate summary of the state that matters. Don't rely on `codex resume` to
rescue a session that has already drifted — resume keeps the bloated context. A clean
session with a tight summary almost always outperforms a long, saturated one.
