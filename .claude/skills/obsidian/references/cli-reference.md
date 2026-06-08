# Obsidian CLI Reference (v1.12.4)

The `obsidian` CLI drives a vault while keeping the running app's index consistent. Examples
below reflect **CLI v1.12.4** conventions and are documented from the published command spec;
confirm the installed version with `obsidian --version` and check `obsidian <command> --help`
before relying on an exact flag name, since flags can shift between releases.

## Contents

- [Global conventions](#global-conventions)
- [Quoting & encoding](#quoting--encoding)
- [Commands](#commands)
  - [create](#create) · [read](#read) · [append](#append) · [prepend](#prepend)
  - [move](#move) · [delete](#delete) · [search](#search) · [daily](#daily)
  - [properties](#properties) · [tags](#tags) · [links](#links) · [files](#files) · [templates](#templates)

## Global conventions

- **Vault selection.** Commands operate on the current/default vault. Target a specific vault
  with `--vault "<vault-name-or-path>"` (or set it once in the CLI config). When in doubt, pass
  `--vault` explicitly so a write never lands in the wrong vault.
- **Note paths** are vault-relative and include the `.md` extension only where noted; most
  commands accept either the basename (`"Project Atlas"`) or a folder-qualified path
  (`"Projects/Project Atlas"`). Folder-qualify whenever a basename is ambiguous.
- **Exit codes.** `0` = success; non-zero = failure (not-found, collision, app-not-running).
  Always check the exit code — a non-zero on a write means the change did **not** happen.
- **Help.** `obsidian --help` lists commands; `obsidian <command> --help` lists that command's
  flags for the installed version.

## Quoting & encoding

- **Always quote** path and content arguments. Note names routinely contain spaces, `&`, `#`,
  and parentheses, all of which the shell would otherwise split or interpret.
- **Multi-line content.** Prefer a heredoc or `--content-file` over embedding `\n` in a shell
  string, so newlines and YAML indentation survive intact:

  ```bash
  obsidian create "Projects/Spec.md" --content "$(cat <<'EOF'
  ---
  title: Spec
  tags:
    - draft
  ---
  # Spec
  EOF
  )"
  ```

  The single-quoted `'EOF'` prevents the shell from expanding `$`, backticks, and `[[...]]`
  inside the body.
- **Special characters in content.** A literal `#`, `*`, or `[[` is fine *inside* a quoted
  string; the danger is only at the shell layer. Use single quotes when the content contains
  `$` or backticks you do not want expanded.
- **Frontmatter is whitespace-sensitive.** Use spaces, never tabs, for YAML indentation — a
  tab silently invalidates the whole properties block.

## Commands

### create

Create a new note. Not idempotent — re-running may error on or overwrite an existing path.

```bash
obsidian create "<path>" --content "<text>"
obsidian create "Projects/Atlas.md" --content "# Atlas\n\nKickoff notes." [--overwrite]
```

| Flag | Purpose |
|------|---------|
| `--content "<text>"` | Initial body (and frontmatter) of the note |
| `--content-file <file>` | Read body from a file instead of the CLI arg |
| `--overwrite` | Replace if the path already exists (otherwise create fails on collision) |

Check existence first (`obsidian read` / `test -f`) unless an overwrite is explicitly intended.

### read

Print a note's full content to stdout (read-only; safe to repeat).

```bash
obsidian read "<path>"
obsidian read "Daily/2026-06-08.md"
```

### append

Add text to the **end** of an existing note. Additive, not idempotent — twice inserts twice.

```bash
obsidian append "<path>" --content "<text>"
obsidian append "Daily/2026-06-08.md" --content "- [ ] Follow up with ops"
```

`--content-file <file>` is also accepted. To keep a section unique, grep for a marker first
and only append if absent.

### prepend

Add text to the **start** of a note's body. Same additive semantics as `append`.

```bash
obsidian prepend "<path>" --content "> [!note] Reviewed 2026-06-08"
```

Note: `prepend` inserts after the frontmatter block, not before it — it will not push text
above the `---` properties fence.

### move

Rename or relocate a note **and rewrite inbound `[[wikilinks]]`** so backlinks stay valid.
This is why moves must go through the CLI, never `mv`.

```bash
obsidian move "<from>" "<to>"
obsidian move "Inbox/Quick.md" "Projects/Atlas/Quick.md"
```

A second move of the same source fails (source gone) — treat "already at target" as success.
If the target basename already exists, this is a **link collision**: STOP and disambiguate.

### delete

Remove a note. Effectively idempotent — a second delete is a no-op / not-found.

```bash
obsidian delete "<path>"
obsidian delete "Inbox/Quick.md" [--trash]
```

| Flag | Purpose |
|------|---------|
| `--trash` | Move to the system trash instead of permanent deletion (prefer this — recoverable) |

### search

Full-text and property search across the vault (read-only).

```bash
obsidian search "<query>"
obsidian search "tag:#project/active"
obsidian search "path:Projects/ deadline"
```

Supports Obsidian search operators (`tag:`, `path:`, `file:`, `line:`, quoted phrases). For
raw regex over body text that the operators can't express, fall back to `Grep`/`rg`.

### daily

Open or create today's daily note, honoring the vault's daily-note config
(`.obsidian/daily-notes.json` — folder, date format, template).

```bash
obsidian daily
obsidian daily --date 2026-06-30        # a specific day
obsidian daily --append "- Standup notes"
```

Use this instead of hand-constructing the daily-note path — the folder and date format are
user config you should not assume.

### properties

Read or modify a note's YAML frontmatter properties without hand-editing the YAML block.

```bash
obsidian properties get "<path>" [<key>]
obsidian properties set "<path>" <key> <value>
obsidian properties remove "<path>" <key>
obsidian properties set "Projects/Atlas.md" status done
obsidian properties set "Projects/Atlas.md" tags "[planning, q3]"   # List value
```

Setting a key is idempotent (overwrite). Prefer this over filesystem YAML edits when available —
the CLI keeps the block well-formed (correct quoting for Links, list shape for List). Confirm
the seven property types and their YAML shapes in `../SKILL.md` → *Frontmatter / properties*.

### tags

List tags in the vault or on a note, and add/remove note tags.

```bash
obsidian tags list                       # all tags + counts
obsidian tags get "<path>"               # tags on one note
obsidian tags add "<path>" <tag>
obsidian tags remove "<path>" <tag>
obsidian tags add "Projects/Atlas.md" project/active
```

Pass tags **without** the leading `#`. Adding an existing tag is idempotent.

### links

Inspect a note's outgoing links and its backlinks (read-only; useful before a move/delete).

```bash
obsidian links get "<path>"              # outgoing [[wikilinks]] from the note
obsidian links backlinks "<path>"        # notes that link TO this one
obsidian links broken                    # vault-wide unresolved links
```

Run `links backlinks` before deleting a note so you know what you are about to orphan.

### files

Enumerate and inspect files in the vault.

```bash
obsidian files list [--folder "<path>"] [--ext md]
obsidian files info "<path>"             # size, created/modified, link counts
```

Use `files list` to discover the vault layout before writing (folders, naming conventions)
rather than assuming a structure.

### templates

List configured templates and insert one into a note (templates folder comes from
`.obsidian/templates.json` or the Templater config).

```bash
obsidian templates list
obsidian templates apply "<template>" --to "<path>"
obsidian templates apply "Meeting" --to "Daily/2026-06-08.md"
```

Core-template insertion fills date/title tokens. **Templater** `<% … %>` expansion requires
the running app (it is a UI/command action) — see ./uri-protocol.md for triggering it, and
`../SKILL.md` → *Plugin conventions* for authoring template files.
