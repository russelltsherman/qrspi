# Permission rule patterns

> **Provenance.** Everything here is **[CLI-spec]** — synthesized from the Claude Code
> CLI/settings permission specification and **not** verified against this repository. The
> one **[in-project]** fact is `--dangerously-skip-permissions`, used in
> `.devcontainer/post-create.sh`. Rule grammar, mode names, and evaluation order are
> externally-derived; confirm them against your installed version before relying on them.

The SKILL.md body summarizes the permission flags. This file is the rule-syntax reference:
the `Tool` vs `Tool(specifier)` grammar, how deny/ask/allow are evaluated, read-only
command lists, and CI/CD safety.

## Rule syntax [CLI-spec]

A permission rule names a tool, optionally narrowed by a specifier:

- **`Tool`** — matches every use of that tool. Examples: `Read`, `Edit`, `Write`,
  `Bash`, `WebFetch`.
- **`Tool(specifier)`** — matches only uses whose argument matches the specifier. The
  specifier is a glob-like pattern over the tool's primary argument.

Examples of `Tool(specifier)`:

```
Bash(git status)            # exactly `git status`
Bash(git diff:*)            # any `git diff ...` invocation
Bash(npm run test:*)        # any `npm run test ...`
Read(./src/**)              # reads under ./src
Edit(./src/**)              # edits under ./src
WebFetch(domain:example.com) # fetches scoped to a domain
```

Globs: `*` matches within a path/argument segment and `**` matches across segments, so
`Read(./src/**)` covers nested files. Match the specifier grammar your installed version
documents — these forms are **[CLI-spec]**.

## Three rule lists and how they are evaluated [CLI-spec]

Permissions are expressed as three lists in `settings.json` — `deny`, `ask`, and `allow`
— evaluated in a fixed precedence:

```
deny  →  ask  →  allow
```

1. **deny** is checked first and is absolute. If a call matches a deny rule it is blocked,
   regardless of any allow rule. Deny always wins.
2. **ask** is checked next. A match prompts the user to approve this specific call.
3. **allow** is checked last. A match runs without a prompt.
4. **No match** falls back to the session's default behavior (governed by
   `--permission-mode`).

The ordering means: put the dangerous things in `deny` (they can never be overridden), the
sensitive-but-sometimes-fine things in `ask`, and the safe routine things in `allow`.

```json
{
  "permissions": {
    "deny":  ["Bash(rm -rf:*)", "Bash(git push:*)", "Read(./.env)"],
    "ask":   ["Bash(git commit:*)", "Write(./src/**)"],
    "allow": ["Read(./**)", "Bash(git status)", "Bash(git diff:*)"]
  }
}
```

## Permission modes [CLI-spec]

`--permission-mode <mode>` sets the default posture for calls that hit no explicit rule:

- A **plan / read-only** posture — the agent can read and reason but edits/commands prompt
  or are withheld. Best for review, audit, and exploration runs.
- An **accept-edits** posture — file edits proceed without prompting (commands may still
  gate), for trusted implementation runs.
- The default interactive posture — prompt on sensitive actions.

Pick the narrowest mode that lets the task finish; widen with explicit `allow` rules
rather than loosening the whole mode.

## Read-only command allow-lists [CLI-spec]

For an inspection/review run, allow a curated set of non-mutating commands and deny the
rest. This lets a script run unattended without a blanket bypass:

```json
{
  "permissions": {
    "allow": [
      "Read(./**)",
      "Bash(git status)", "Bash(git diff:*)", "Bash(git log:*)",
      "Bash(ls:*)", "Bash(cat:*)", "Bash(rg:*)"
    ],
    "deny": [
      "Bash(git push:*)", "Bash(git commit:*)",
      "Bash(rm:*)", "Write(./**)", "Edit(./**)"
    ]
  }
}
```

The allow-list is the safe surface; the deny-list is the backstop that no default-mode
fallback can override.

## CI/CD safety [CLI-spec] / [in-project]

In automation there is no human to answer an `ask` prompt, so a run must be **fully
pre-authorized or it stalls**:

- **Prefer an explicit allow-list** matched to exactly what the job does; everything else
  stays denied. This is the safe default for CI.
- **`--dangerously-skip-permissions` bypasses the entire system** — every prompt, every
  rule. **[in-project]:** this repo uses it in `.devcontainer/post-create.sh`, which is
  safe only because the dev container is a disposable, isolated sandbox with no real
  credentials.
- **Never** use `--dangerously-skip-permissions` on a host with real secrets, production
  access, or a non-throwaway checkout. In those environments, scope with allow/deny rules
  (and hooks) instead.
- **Combine with hooks** for logic a static rule can't express (e.g. "block writes outside
  `$PWD`"); see [hook-examples.md](hook-examples.md).

## Quick reference [CLI-spec]

| Want | Use |
|------|-----|
| Block something unconditionally | `deny` rule (wins over everything) |
| Prompt before a sensitive call | `ask` rule |
| Run a known-safe call silently | `allow` rule |
| Set the no-match default posture | `--permission-mode` |
| Unattended run, real credentials | curated `allow` + `deny`, never `--dangerously-skip-permissions` |
| Unattended run, disposable sandbox | `--dangerously-skip-permissions` acceptable |

See also: [advanced-cli-flags.md](advanced-cli-flags.md) for `--allowedTools` /
`--disallowedTools` per-run scoping, and [hook-examples.md](hook-examples.md) for
enforcement beyond static rules.
