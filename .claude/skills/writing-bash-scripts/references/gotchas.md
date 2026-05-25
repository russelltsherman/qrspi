# Bash Gotchas and Portability Reference

## BSD vs GNU coreutils

macOS ships BSD coreutils; Linux ships GNU. Key differences:

| Command | GNU (Linux) | BSD (macOS) | Portable alternative |
|---------|-------------|-------------|---------------------|
| `sed -i` | `sed -i 's/a/b/' file` | `sed -i '' 's/a/b/' file` | Use `sed -i.bak` then `rm file.bak`, or use `perl -pi -e` |
| `date` | `date -d '2 days ago'` | `date -v-2d` | Use `date -u` for UTC; avoid relative date math in bash |
| `readlink -f` | Works | Does not exist | Use `cd "$(dirname "$0")" && pwd` pattern instead |
| `find -regex` | Uses `emacs` regex by default | Uses `basic` regex | Always specify `-regextype posix-extended` on GNU, or avoid `-regex` |
| `grep -P` | Perl regex support | Not available | Use `grep -E` (extended regex) for portability |
| `mktemp` | `mktemp` (no template required) | `mktemp -t prefix` | `mktemp /tmp/prefix.XXXXXX` works on both |
| `stat` | `stat -c '%s' file` | `stat -f '%z' file` | Use `wc -c < file` for file size |

### Strategy

- Do not assume GNU extensions are available.
- Test on both platforms if portability matters.
- When in doubt, use POSIX-compliant alternatives.

## Bash 3.2 vs 4+

macOS ships bash 3.2 (2007). Newer features require bash 4+:

| Feature | Available since | Workaround for bash 3.2 |
|---------|----------------|------------------------|
| Associative arrays (`declare -A`) | bash 4.0 | Use separate indexed arrays or external tools |
| `mapfile` / `readarray` | bash 4.0 | Use `while IFS= read -r line` loop |
| `&>>` redirect (append stdout+stderr) | bash 4.0 | Use `>> file 2>&1` |
| `${var,,}` lowercase | bash 4.0 | Use `tr '[:upper:]' '[:lower:]'` |
| `${var^^}` uppercase | bash 4.0 | Use `tr '[:lower:]' '[:upper:]'` |
| `coproc` | bash 4.0 | Use named pipes or temp files |
| `|&` (pipe stderr) | bash 4.0 | Use `2>&1 |` |
| Negative array indices | bash 4.3 | Use `${arr[${#arr[@]}-1]}` for last element |
| Nameref (`declare -n`) | bash 4.3 | Pass variable name and use `eval` carefully |

### Strategy

- If targeting macOS without Homebrew bash: stick to bash 3.2 features.
- Add a version check at script top if you need bash 4+:

```bash
if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
  echo "Error: bash 4+ required (found ${BASH_VERSION})" >&2
  exit 1
fi
```

## Common ShellCheck warnings

| Code | Problem | Fix |
|------|---------|-----|
| SC2086 | Unquoted variable: `echo $var` | Quote it: `echo "${var}"` |
| SC2046 | Unquoted command substitution: `echo $(cmd)` | Quote it: `echo "$(cmd)"` |
| SC2155 | Declare and assign on one line: `local x=$(cmd)` | Split: `local x; x=$(cmd)` |
| SC2164 | `cd` without error check: `cd dir` | Use `cd dir || exit 1` or `cd dir || return 1` |
| SC2034 | Variable appears unused | Remove it, export it, or add `# shellcheck disable=SC2034` |
| SC2013 | Using `cat` in `for` loop: `for x in $(cat file)` | Use `while IFS= read -r x` instead |
| SC2001 | Using `sed` where bash expansion works: `echo "$x" \| sed 's/a/b/'` | Use `"${x//a/b}"` |
| SC2129 | Multiple redirects to same file | Group with `{ cmd1; cmd2; } > file` |
| SC2162 | `read` without `-r` | Always use `read -r` to prevent backslash interpretation |
| SC2115 | Risky `rm -rf "$dir/"` if var is empty | Guard: `rm -rf "${dir:?}/"` |

### Suppressing warnings

Use inline directives only when the warning is a false positive:

```bash
# shellcheck disable=SC2034
readonly CONFIG_VERSION="1.0"  # Used by sourced scripts
```

- Place the directive on the line immediately before the flagged line.
- Always include a comment explaining why the suppression is justified.
- Never blanket-suppress at the file level unless every instance is intentional.

## Word splitting pitfalls

Word splitting occurs on unquoted expansions. The shell splits on characters in `IFS` (default: space, tab, newline):

```bash
# Dangerous — word splits, then globs
files=$(ls)
for f in $files; do  # Breaks on filenames with spaces

# Safe — use arrays or globs
for f in *; do
  [[ -f "${f}" ]] || continue
```

- **Always quote** variable expansions and command substitutions.
- Unquoted `$@` and `${array[@]}` split each element further — always quote them.
- When you intentionally want splitting (rare), set `IFS` explicitly and document it:

```bash
IFS=',' read -r -a items <<< "${csv_line}"
```

## Globbing hazards

Unquoted variables undergo glob expansion after word splitting:

```bash
var="*.txt"
echo $var     # Expands to matching filenames!
echo "$var"   # Prints literal "*.txt"
```

- When iterating over globs, handle the case where nothing matches:

```bash
shopt -s nullglob  # Empty expansion when no match (bash-specific)
for f in "${dir}"/*.log; do
  process "${f}"
done
shopt -u nullglob  # Restore default
```

- Without `nullglob`, a non-matching glob expands to the literal pattern string.
- Use `shopt -s failglob` if you want an error on non-matching globs.

## Subshell variable scope

Variables set inside a subshell are not visible to the parent:

```bash
# BROKEN — pipe creates a subshell
count=0
echo "a b c" | while read -r word; do
  ((count++))
done
echo "${count}"  # Still 0!

# FIXED — use process substitution (bash 3.2+)
count=0
while read -r word; do
  ((count++))
done < <(echo "a b c")
echo "${count}"  # 3

# FIXED (alternative) — use a heredoc or herestring
count=0
while read -r word; do
  ((count++))
done <<< "a b c"
echo "${count}"  # 1 (single line)
```

Other subshell traps:
- `$(command)` runs in a subshell — variable changes inside are lost.
- `(commands)` explicit subshell — same issue.
- `var=$(cmd)` captures output but not side effects on variables.
- Parenthesized groups `(cmd1; cmd2)` are subshells; brace groups `{ cmd1; cmd2; }` are not.
