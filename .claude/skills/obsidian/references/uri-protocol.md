# Obsidian URI Protocol (`obsidian://`)

The `obsidian://` URI scheme drives the **running** Obsidian app's UI. It is for single,
interactive "open / show / trigger this" actions — not a batch-scripting primitive: it
requires a running, focused app and returns no machine-readable result, so failures are
silent. For reliable, repeatable writes use the CLI (see ./cli-reference.md).

## Invoking a URI

A URI is opened by the OS handler, not executed in-process:

```bash
# macOS
open "obsidian://open?vault=MyVault&file=Projects%2FAtlas"
# Linux
xdg-open "obsidian://open?vault=MyVault&file=Projects%2FAtlas"
```

Always quote the whole URI in the shell — it contains `&`, `?`, and `%` that the shell would
otherwise split.

## URI structure

```
obsidian://<action>?<key>=<value>&<key>=<value>
```

- `<action>` selects what to do (`open`, `new`, `search`, …).
- Each parameter **value** must be percent-encoded (see below).
- `vault` is almost always required to disambiguate which vault to target.

## Action catalogue

| Action | Purpose | Key parameters |
|--------|---------|----------------|
| `open` | Open/focus a note or vault | `vault`, `file` (path or basename) **or** `path` (absolute) |
| `new` | Create a note (optionally with content) | `vault`, `name` or `file`, `content`, `append`, `prepend`, `overwrite`, `silent` |
| `search` | Open search with a query | `vault`, `query` |
| `hook-get-address` | Return a link to the current note (Obsidian URI plugins) | `vault`, `file` |
| `advanced-uri` | Rich actions via the *Advanced URI* community plugin | `vault`, `filepath`, `heading`, `block`, `commandid`, `mode`, `data`, `eval` |

Notes on the most useful ones:

- **`open`** — jump to a heading or block with the file value, e.g.
  `file=Atlas%23Overview` (`#` → `%23`) for a heading, or `file=Atlas%23%5Eabc123` for a
  `^abc123` block id (`^` → `%5E`).
- **`new`** — `content=` seeds the body; combine with `append=true` or `prepend=true` to add to
  an existing note, and `silent=true` to avoid stealing focus. `overwrite=true` replaces. This
  overlaps the CLI's `create`/`append`; prefer the CLI for scripts and reserve `new` for
  capture-style flows from other apps.
- **`advanced-uri`** (community plugin, not built in) — the only URI path that can reliably
  target a heading/block for *writing*, run a command by `commandid`, or trigger Templater. It
  requires the plugin to be installed; check before relying on it.

## Percent-encoding rules

Every parameter value is percent-encoded (RFC 3986). The characters that bite most often in
vault paths and queries:

| Character | Encoding | Where it appears |
|-----------|----------|------------------|
| space | `%20` | note names |
| `/` | `%2F` | folder separators in `file=` |
| `#` | `%23` | heading refs (`Note#Heading`) |
| `^` | `%5E` | block refs (`Note#^id`) |
| `&` | `%26` | within content/queries (would otherwise end the value) |
| `?` | `%3F` | within content/queries |
| `%` | `%25` | a literal percent in content |
| `[` / `]` | `%5B` / `%5D` | wikilinks inside `content=` |
| `|` | `%7C` | pipe-display links inside `content=` |

Encode the **value only**, not the `key=` or the `&` separators between parameters. Example:
to open `Projects/Atlas` at heading `Q3 Plan`:

```
obsidian://open?vault=MyVault&file=Projects%2FAtlas%23Q3%20Plan
```

If a URI does nothing, the usual causes are: the app is not running, the `vault` name is
wrong, or a value was left un-encoded (a raw `&` or `#` truncated it). Because the scheme
returns no error, verify the *effect* (re-read the note) rather than assuming success — and
for anything that must be reliable, use the CLI instead.
