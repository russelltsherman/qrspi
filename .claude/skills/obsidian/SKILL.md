---
name: obsidian
description: "Operate an Obsidian vault from an agent — create, read, edit, move, and search notes; manage YAML frontmatter properties, wikilinks, tags, and daily notes; and work with Dataview/Templater/Tasks plugin data formats. Use whenever the task involves an Obsidian vault, a `.md` note inside one, the `obsidian` CLI, an `obsidian://` URI, wikilinks (`[[...]]`), note frontmatter/properties, daily notes, or Dataview queries — even if the user only says 'add a note to my vault', 'update the frontmatter on my project note', or 'find all notes tagged #x'. Trigger on any Obsidian-vault read/write/search task, not only when the word 'obsidian' appears."
command: /obsidian
argument-hint: <what you want to do in the vault>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Obsidian Vault Operations

You operate an [Obsidian](https://obsidian.md) vault on behalf of the user. A vault is a
plain directory of UTF-8 Markdown files plus a hidden `.obsidian/` config folder — so most
work is ordinary file editing, but Obsidian layers conventions on top (YAML frontmatter
"properties", `[[wikilinks]]`, tags, daily notes) and ships an `obsidian` CLI (v1.12.4) and
an `obsidian://` URI scheme that drive the *running app* so it stays in sync with what you
change on disk.

The single most important judgement this skill encodes is **which mechanism to use** —
CLI, URI, or raw filesystem — because they have different consequences for whether the
running app notices your change and whether the operation is safe to repeat. Read the
`## CLI vs URI vs filesystem` decision table before any write.

This skill keeps detailed lookup material out of the body so it stays scannable:

- Full per-command CLI syntax, flags, and quoting/encoding rules → see references/cli-reference.md
- The complete `obsidian://` action catalogue and URI percent-encoding rules → see references/uri-protocol.md
- Dataview Query Language (DQL) and inline-field syntax → see references/dataview.md

> CLI command examples reflect Obsidian CLI **v1.12.4** conventions. The commands are
> documented from the published spec, not validated against a running binary in this
> environment — confirm the installed version with `obsidian --version` before relying on
> exact flag names (see references/cli-reference.md).

## Vault structure

A vault is just a folder. Treat its layout as user-owned convention, and discover it rather
than assume it:

- **`.obsidian/`** — app config (themes, hotkeys, enabled plugins, `app.json`,
  `daily-notes.json`, `templates.json`). Read it to learn the user's conventions (daily-note
  folder, date format, template folder); do **not** rewrite it casually — corrupting it
  breaks the app for the user.
- **Notes** — `.md` files, possibly nested in topic folders (`Projects/`, `Areas/`,
  `Daily/`, `Templates/`). A note's identity is its path + basename; the basename is what
  `[[wikilinks]]` resolve against.
- **Attachments** — images/PDFs, often under an `attachments/` or `_assets/` folder set by
  `app.json → attachmentFolderPath`.

Before writing, learn the layout: `obsidian files list` (or `find <vault> -name '*.md'`) to
enumerate notes, and read `.obsidian/daily-notes.json` / `app.json` for folder + date-format
conventions. Never hard-code "Daily/" or a date format you have not confirmed.

## Note CRUD

The lifecycle operations — **create, read, append, prepend, move, delete, search, daily** —
are exposed as `obsidian` CLI subcommands so the running app re-indexes the change. Use the
CLI for these rather than editing files blind, because a filesystem-only write leaves the
open app showing stale content until it rescans.

Quick mental model (full parameters, flags, and quoting rules in references/cli-reference.md):

| Intent | Command |
|--------|---------|
| New note | `obsidian create "<path>" --content "<text>"` |
| Read a note | `obsidian read "<path>"` |
| Add to end | `obsidian append "<path>" --content "<text>"` |
| Add to start | `obsidian prepend "<path>" --content "<text>"` |
| Rename/relocate (updates backlinks) | `obsidian move "<from>" "<to>"` |
| Remove | `obsidian delete "<path>"` |
| Full-text / property search | `obsidian search "<query>"` |
| Today's daily note | `obsidian daily` |

Always quote paths and content — note names routinely contain spaces. For the exact flag
set per command, and how to pass multi-line content safely, see references/cli-reference.md.

## Frontmatter / properties

Obsidian "properties" are a YAML frontmatter block fenced by `---` at the very top of a note
(it must be the first thing in the file, no blank line before it). Obsidian recognizes seven
property types; pick the type by the YAML shape — there is no separate type declaration, the
value's form *is* the type.

```yaml
---
title: Quarterly Plan          # Text   — a plain string
priority: 3                     # Number — bare numeric, no quotes
done: false                     # Checkbox — YAML boolean true/false
due: 2026-06-30                 # Date — ISO YYYY-MM-DD, unquoted
reviewed: 2026-06-30T14:00:00   # Date & Time — ISO 8601 with a T separator
tags:                           # List — a YAML sequence (one item per dash)
  - planning
  - q3
related:                        # Links — wikilinks as quoted strings in a list
  - "[[Project Atlas]]"
  - "[[Roadmap 2026]]"
---
```

Type-by-type, one example each:

- **Text** — `status: in progress` (any string; quote it if it contains a leading `[`, `:`, or `#`).
- **Number** — `effort: 8` (no quotes; quoting makes it Text).
- **Checkbox** — `archived: true` (YAML `true`/`false` only; `"true"` becomes Text).
- **Date** — `start: 2026-01-15` (bare ISO date).
- **Date & Time** — `created: 2026-01-15T09:30:00` (ISO with `T`; an offset like `+00:00` is allowed).
- **List** — `aliases:` followed by `- item` lines (a YAML sequence).
- **Links** — a List whose items are quoted wikilinks: `- "[[Note Name]]"`. The quotes
  matter — an unquoted `[[...]]` is not valid YAML and will silently break the whole block.

When editing frontmatter, modify the YAML in place and keep keys you don't understand —
plugins and the user store data here. A malformed block makes Obsidian show *no* properties,
so validate after editing (see `## Error handling`).

## Linking

Links are how a vault becomes a graph. Prefer Obsidian wikilinks over standard Markdown links
for vault-internal references, because wikilinks survive note renames (Obsidian rewrites them)
and feed the graph/backlink views; standard `[text](path.md)` links do not.

| Form | Meaning |
|------|---------|
| `[[Note Name]]` | Link to a note by basename |
| `[[Note Name#Heading]]` | Link to a specific heading within a note |
| `[[Note Name#^block-id]]` | Link to a specific block (a `^block-id` anchored paragraph) |
| `[[Note Name\|Display text]]` | Pipe-display: link target stays, shown text is custom |
| `[[Note Name#Heading\|Display]]` | Heading link with custom display text |
| `![[Note Name]]` / `![[image.png]]` | Embed (transclude) a note or attachment |

Use a standard Markdown link `[label](https://…)` only for **external URLs** and for files you
deliberately do *not* want in the graph. Block ids are created by appending ` ^my-id` to the end
of a paragraph, then referenced with `#^my-id`. When you rename a note via `obsidian move`, the
CLI updates inbound `[[wikilinks]]`; a manual filesystem rename does **not** — that is a primary
reason to move via the CLI (see `## CLI vs URI vs filesystem`).

## Tags

Tags are lightweight cross-cutting labels, complementary to folders and links.

- **Inline tags** live in note body text as `#tag`, e.g. `#project/active` (nesting with `/`
  creates a hierarchy: `#project` and `#project/active` both match `#project`).
- **Frontmatter tags** live under the `tags:` property as a List (see above). Prefer the
  frontmatter form for structured/queryable metadata; use inline `#tags` for in-context
  annotation.
- Tags are case-sensitive, may contain letters/digits/`_`/`-`/`/`, must **not** be purely
  numeric (`#2026` is not a tag — write `#y2026`), and take no spaces.
- Do not duplicate a tag in both inline and frontmatter form on the same note unless the user
  asks — it double-counts in tag panes and Dataview.

## CLI vs URI vs filesystem

Three mechanisms can change a vault. They are **not** interchangeable — choose by what the
running app needs to know and whether the action must be safely repeatable.

| Mechanism | Use it for | Why / consequence |
|-----------|-----------|-------------------|
| **`obsidian` CLI** | All note CRUD, search, daily notes, link-preserving moves | The app re-indexes the change, so links/backlinks/graph stay correct. **Default choice.** |
| **`obsidian://` URI** | Driving the *running app's* UI — opening a note, jumping to a heading, triggering a command/Templater, capture-style appends | Requires the app to be running and focuses a window; it is a UI action, not a reliable batch primitive (see references/uri-protocol.md). |
| **Raw filesystem** (Read/Write/Edit/Glob/Grep) | Bulk read-only inspection, grepping content, and edits only when the CLI cannot express them | Fast and scriptable, but the running app will show **stale** content until it rescans, and renames here **break `[[wikilinks]]`**. |

Imperative guidance:

- **Prefer the CLI for every write** that has a subcommand (create/append/prepend/move/delete),
  because it keeps the running app's index consistent — a filesystem write does not.
- **Do NOT rename or move a note with `mv` or filesystem Edit** — it orphans every inbound
  `[[wikilink]]`. Use `obsidian move`, because it rewrites the backlinks for you.
- **Prefer Grep/Glob for read-only search across many files** when you need raw matches the
  CLI's `search` does not expose (e.g. regex over body text); the consequence is only that you
  read possibly-stale-in-app content, which is harmless for reads.
- **Do NOT use an `obsidian://` URI as a scripting primitive** for bulk edits — it depends on
  a running, focused app and returns no machine-readable result, so failures are silent. Reserve
  it for single interactive "open/show this" actions (see references/uri-protocol.md).

## Idempotency

Agent actions get retried, so make writes safe to repeat:

- **create** is not inherently idempotent — re-running can either error on an existing path or
  clobber it depending on flags. Before creating, check existence (`obsidian read`/`test -f`);
  if it exists, switch to `append`/`prepend` or an explicit overwrite the user approved.
- **append/prepend** are *additive*, not idempotent — running twice inserts the text twice.
  When a section must exist exactly once, read first and only write if the marker is absent
  (e.g. grep for a unique heading or a `^block-id` before appending it).
- **move/delete** are naturally idempotent-ish: a second `move` fails because the source is
  gone, and a second `delete` is a no-op or a not-found — treat "already in the target state"
  as success, not failure.
- For frontmatter edits, set the key to the desired value (overwrite) rather than appending —
  setting `status: done` twice is idempotent; appending a second `status:` key corrupts the YAML.

## Plugin conventions

Community plugins store their data **inside the notes** as frontmatter and inline syntax, so
you can produce plugin-ready content without installing or running the plugin. Write the data
formats; the plugin renders them when present.

- **Dataview** — reads frontmatter properties and *inline fields* (`Key:: value` written in
  the body) and renders ```dataview``` DQL code blocks. To make a note queryable, just write
  well-formed properties/inline fields; to build a query view, emit a DQL block. Full DQL and
  inline-field syntax → see references/dataview.md.
- **Templater** — templates live in the configured template folder (read
  `.obsidian/templates.json` or the Templater config) and use `<% … %>` tags (e.g.
  `<% tp.date.now("YYYY-MM-DD") %>`). When authoring a template file, leave the `<% %>` tags
  literal — they are expanded by the app at insertion time, not by you. Triggering insertion is
  a *running-app* action (URI/command), not a filesystem write.
- **Tasks** — tasks are Markdown checkboxes with inline emoji/dataview-style metadata, e.g.
  `- [ ] Ship draft 📅 2026-06-30 ⏫ #work` (due date `📅`, priority `⏫`/`🔼`/`🔽`,
  recurrence `🔁`). A completed task is `- [x] … ✅ 2026-06-12`. Write these literally in the
  body; the plugin queries them via its own code blocks.

Do not assume a plugin is installed — only write its data format. If a behavior *requires* the
plugin to execute (Templater expansion, a Dataview re-render), that needs the running app, so
fall back to the URI/command path and tell the user.

## Error handling

Handle these conditions in the QRSPI `condition → action` style. Infrastructure/auth failures
are a HARD STOP, not a puzzle to solve.

- **Obsidian app not running** (a CLI command or `obsidian://` URI times out / reports no
  running instance) → report it and STOP for URI actions (they *require* the app). For CLI
  writes, if the command supports a no-app/headless mode use it; otherwise tell the user to
  open the vault. Do **not** silently fall back to a raw filesystem write that the app won't
  index — that desyncs the vault.
- **Malformed YAML frontmatter** (edit leaves a note showing no properties, or a parser errors)
  → STOP and surface the exact note + the offending lines. The usual causes are an unquoted
  `[[wikilink]]` in a Links property, a tab character, or a missing closing `---`. Re-read the
  block, fix the specific YAML, and re-validate; never blanket-rewrite the user's other keys.
- **Link collision** (a `create`/`move` target basename already exists, so a `[[wikilink]]`
  would become ambiguous) → STOP before clobbering. Disambiguate by folder path or an explicit
  user-approved rename; do not overwrite an existing note to resolve the collision.
- **Vault path not found / config unreadable** (`.obsidian/` missing, `EACCES`, permission
  denied) → this is an infrastructure/auth error. **HARD STOP:** print the exact failing
  command and its verbatim output, and exit. Do not `chmod`, do not guess another path, do not
  retry in a loop. The thought "let me just try one more thing" is the failure mode to avoid.
