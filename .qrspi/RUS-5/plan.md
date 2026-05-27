# Plan — writing-bash-scripts skill update

**Ticket:** RUS-5
**Generated:** 2026-05-27
**Parent:** structure.md

---

## Slice 1 — SKILL.md body additions, command prefix fix, eval cleanup

### Step 1.1: Delete eval workspace (if exists)

**File:** `/home/vscode/.claude/skills/writing-bash-scripts-workspace/`

**Action:** Delete the entire directory.

**Current:** Directory does not exist (confirmed). No action needed.

**After:** Directory absent.

**Rollback:** N/A — no existing state to restore.

---

### Step 1.2: Fix `command` frontmatter field

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md` (line 4)

**Current signature:**
```yaml
command: writing-bash-scripts
```

**After signature:**
```yaml
command: /writing-bash-scripts
```

**Purpose:** Add leading slash to match the convention used by all other global and project-local skills.

**Rollback:** Change line 4 back to `command: writing-bash-scripts`.

---

### Step 1.3: Expand Script Structure section to seven sections

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md` (lines 32-69)

**Action:** In the "Section order matters" subsection, change the ordered list from 6 items to 7 by adding a "Usage/Help" section between Helpers and Command functions.

**Current list (lines 61-66):**
```
1. Shebang and strict mode
2. Constants (readonly, uppercase)
3. Helpers (logging, cleanup, utility)
4. Command functions (one per subcommand)
5. Main (parse args, dispatch)
6. Entry point: `main "$@"` as the last line
```

**After list:**
```
1. Shebang and strict mode
2. Constants (readonly, uppercase)
3. Helpers (logging, cleanup, utility)
4. Usage/Help (usage function with heredoc)
5. Command functions (one per subcommand)
6. Main (parse args, dispatch)
7. Entry point: `main "$@"` as the last line
```

Also add a one-line description of the usage section in the block code example (line 44-47 area):
```
usage() { cat <<EOF
Usage: ${0##*/} ...
EOF
}
```

---

### Step 1.4: Add Usage/Help section

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`

**Action:** Insert a new section after "Strict Mode" (after line 116) or at a logical location in the body.

**Content to add:**

```markdown
## Usage / Help

Every script should provide a `usage()` function that prints usage information to
stderr. Use a heredoc for clean formatting:

```bash
usage() {
  cat <<EOF
Usage: ${0##*/} <command> [options]

Commands:
  start   Start the service
  stop    Stop the service
  help    Show this message

Options:
  -v, --verbose   Enable verbose output
  -h, --help      Show this message
EOF
}
```

Key conventions:
- Use `${0##*/}` to extract the script basename (no path)
- Align the `Commands:` and `Options:` columns with spaces
- List `help` as an explicit command that calls `usage` and exits 0
- Call `usage` and exit 2 when the user provides wrong arguments

When implementing the dispatcher, route `help`, `-h`, and `--help` to `usage`.
See `references/patterns.md` for a full subcommand dispatcher example.
```

**Purpose:** Encode the ticket requirement for heredoc usage pattern with `${0##*/}` basename extraction and column alignment.

**Rollback:** Remove the inserted section.

---

### Step 1.5: Add Logging section

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`

**Action:** Insert a new section after "Usage/Help" (created in Step 1.4).

**Content to add:**

```markdown
## Logging

Send all log output to stderr (`>&2`). Reserve stdout for machine-parseable data.

Use three log levels at minimum:

```bash
log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
```

Add color when the output is a terminal:

```bash
log_info()  { printf '%b[INFO]  %s\n' "${COLOR_GREEN:-}" "$*" "${COLOR_RESET:-}" >&2; }
log_error() { printf '%b[ERROR] %s\n' "${COLOR_RED:-}" "$*" "${COLOR_RESET:-}" >&2; }

# Detect terminal and set colors
if [[ -t 2 ]]; then
  COLOR_RED=$'\033[1;31m'
  COLOR_GREEN=$'\033[1;32m'
  COLOR_RESET=$'\033[0m'
fi
```

Check `[[ -t 2 ]]` (is fd 2 a terminal?) before enabling colors. This prevents
ANSI escape codes from polluting piped output or log files.
```

**Purpose:** Move the logging pattern from `references/patterns.md` into the SKILL.md body so it is visible on first load.

**Rollback:** Remove the inserted section.

---

### Step 1.6: Add debugging trap pattern

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`

**Action:** Add a new subsection under "Error Handling" after the "Exit codes" section (around line 175).

**Content to add:**

```markdown
### Debugging trap

For quick debugging in development scripts, add a trap that reports the line number
on unexpected errors:

```bash
trap 'echo "Error on line $LINENO" >&2' ERR
```

This prints the failing line number to stderr when any command exits nonzero. Remove
or comment this out before production use. Do not confuse this with the production
`EXIT` trap used for cleanup.
```

**Purpose:** Encode the ticket convention for the debugging ERR trap pattern, which is not present in any existing file.

**Rollback:** Remove the inserted subsection.

---

### Step 1.7: Add ~200-line guidance

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`

**Action:** Insert a new top-level section after "ShellCheck" (after line 274, the last line of the current file).

**Content to add:**

```markdown
## Language Choice

Bash is the right tool for simple automation tasks — glue scripts, quick utilities,
and one-off operations. But bash scripts over 200 lines should be evaluated for
whether a different language is more appropriate.

Consider Python, Go, or another language when a script:
- Exceeds ~200 lines without strong justification
- Requires complex data structures, networking, or concurrency
- Needs robust error handling beyond trap and exit codes
- Will be maintained by multiple authors over time
- Is reused across many projects

The line-count threshold is a soft guideline, not a hard rule. Use judgment.
```

**Purpose:** Encode the ticket requirement for the 200-line threshold convention.

**Rollback:** Remove the inserted section.

---

### Step 1.8: Add Gotchas section

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`

**Action:** Insert a new top-level section after "Language Choice" (created in Step 1.7) or at the end.

**Content to add:**

```markdown
## Gotchas

Bash has subtle pitfalls even when you follow all conventions. When something behaves
unexpectedly, check these common issues first:

- **BSD vs GNU coreutils:** `grep`, `sed`, and `sort` differ between macOS and Linux.
  Use `g`-prefixed Homebrew versions on macOS, or write portable alternatives.
- **Bash 3.2 vs 4+:** macOS ships bash 3.2 (no associative arrays, no `${var//pat/rep}`).
  Always check the target bash version or use `#!/usr/bin/env bash` with a version gate.
- **Word splitting:** Unquoted `$(command)` or `$var` splits on whitespace.
  Always double-quote expansions.
- **Globbing hazards:** Unquoted `*` in expansions can match hidden files or cause
  "ambiguous redirect" errors.
- **Subshell variable scope:** Pipes create subshells. Variables set inside a pipeline
  do not persist after the pipeline exits. Use process substitution `<(...)` instead.

For a complete list, read `references/gotchas.md`.
```

**Purpose:** Provide progressive disclosure — key gotchas in SKILL.md body, full details in the reference file. Aligns with `qrspi-*` skill patterns.

**Rollback:** Remove the inserted section.

---

### Step 1.9: Add `declare -f` dynamic dispatch to Function Conventions

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md` (Function Conventions section, after line 230)

**Action:** Insert a new subsection under Function Conventions, after the "Separate declaration from assignment" section (after the closing code fence around line 229).

**Content to add:**

```markdown
### Dynamic subcommand dispatch

For scripts that load command modules dynamically, use `declare -f` to check if a
`cmd_<name>` function exists before calling it:

```bash
dispatch() {
  local cmd="${1:-help}"
  shift || true

  if declare -f "cmd_${cmd}" >/dev/null 2>&1; then
    "cmd_${cmd}" "$@"
  else
    log_error "Unknown command: ${cmd}"
    usage
    exit 1
  fi
}

# Register commands by defining cmd_* functions
cmd_start() { log_info "Starting..."; }
cmd_stop()  { log_info "Stopping..."; }

dispatch "$@"
```

This pattern eliminates the `case` statement for large command sets. Use `case`
dispatch for scripts with a small, fixed set of subcommands.
```

**Purpose:** Encode the ticket convention for `declare -f "cmd_${1}"` dynamic dispatch pattern alongside the existing `case` dispatch pattern.

**Rollback:** Remove the inserted subsection.

---

### Step 1.10: Verify SKILL.md

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`

**Verification commands:**
```bash
grep -n 'command: /writing-bash-scripts' /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
wc -l /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
grep -c '^## ' /home/vscode/.claude/skills/writing-bash-scripts/SKILL.md
```

**Expected results:**
- Line 4 contains `command: /writing-bash-scripts`
- Line count under 500 (currently 274 + ~100 additions = ~374)
- New sections present: Usage/Help, Logging, Gotchas, Language Choice, plus expanded Function Conventions

**Rollback:** Each step is independently reversible. Revert steps in reverse order if verification fails.

---

## Slice 2 — Template.sh minor additions

### Step 2.1: Add debugging trap to template.sh

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh`

**Current signature (lines 22-28):**
```bash
cleanup() {
  # Remove temp files, release locks, etc.
  if [[ -n "${TMPDIR_CUSTOM:-}" && -d "${TMPDIR_CUSTOM}" ]]; then
    rm -rf "${TMPDIR_CUSTOM}"
  fi
}
trap cleanup EXIT
```

**After signature:**
```bash
cleanup() {
  # Remove temp files, release locks, etc.
  if [[ -n "${TMPDIR_CUSTOM:-}" && -d "${TMPDIR_CUSTOM}" ]]; then
    rm -rf "${TMPDIR_CUSTOM}"
  fi
}
trap cleanup EXIT

# Debugging trap (remove before production)
# trap 'echo "Error on line $LINENO" >&2' ERR
```

**Purpose:** Add the debugging trap pattern so the template demonstrates all conventions. Commented out to avoid noise in normal use.

**Rollback:** Remove the added two lines.

---

### Step 2.2: Add comment on `${0##*/}` in constants section

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh` (line 9)

**Current:**
```bash
readonly SCRIPT_NAME="${0##*/}"
```

**After:**
```bash
readonly SCRIPT_NAME="${0##*/}"  # basename, no path
```

**Purpose:** Inline comment explaining the basename extraction pattern referenced in the new Usage/Help section.

**Rollback:** Remove the trailing comment.

---

### Step 2.3: Add color detection block to template.sh

**File:** `/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh`

**Action:** Insert after the constants section (after line 14) and before the helpers section.

**Content to add:**
```bash
# ─── Colors (terminal detection) ────────────────────────────────────

if [[ -t 2 ]]; then
  COLOR_RED=$'\033[1;31m'
  COLOR_GREEN=$'\033[1;32m'
  COLOR_RESET=$'\033[0m'
fi
```

**Purpose:** Demonstrate the `[[ -t 2 ]]` color detection pattern that was added to the SKILL.md Logging section.

**Rollback:** Remove the inserted block.

---

### Step 2.4: Verify template.sh

**Verification commands:**
```bash
bash -n /home/vscode/.claude/skills/writing-bash-scripts/references/template.sh
shellcheck -x /home/vscode/.claude/skills/writing-bash-scripts/references/template.sh
```

**Expected results:**
- `bash -n` exits 0 (no syntax errors)
- `shellcheck` exits 0 (zero warnings)

**Rollback:** Revert steps 2.1-2.3 in reverse order.

---

## Rollback Notes

All changes are to existing skill documentation files. Each step is independently reversible:

- **Step 1.2 (command prefix):** Single line change. Revert frontmatter.
- **Steps 1.3-1.9 (body additions):** Each inserts new text at a known location. Remove the inserted text to revert.
- **Steps 2.1-2.3 (template additions):** Each adds a small block. Remove the block to revert.

No database migrations, no config file changes, no destructive operations on shared state. The only "delete" is the eval workspace which does not exist.

If a step fails due to file permissions (EACCES), the skill directory is at `/home/vscode/.claude/skills/` which is the user's home directory and should be writable. If permissions are an issue, report the exact error and stop.
