# Dataview: DQL & Inline Fields

[Dataview](https://github.com/blacksmithgu/obsidian-dataview) turns a vault into a queryable
database. You do not need the plugin installed to produce Dataview-ready content — write the
**data** (frontmatter properties and inline fields) and the **queries** (DQL code blocks), and
the plugin renders them wherever it is enabled. This file covers both halves: the data sources
Dataview reads, and the query language it renders.

## Contents

- [Data sources](#data-sources) — frontmatter & inline fields
- [Inline-field syntax](#inline-field-syntax)
- [DQL query types](#dql-query-types)
- [Clauses](#clauses)
- [Implicit fields & functions](#implicit-fields--functions)
- [Inline DQL](#inline-dql)

## Data sources

Dataview reads two kinds of metadata from a note:

1. **Frontmatter properties** — the YAML block at the top (see `../SKILL.md` →
   *Frontmatter / properties*). A property `due: 2026-06-30` is queryable as the field `due`.
2. **Inline fields** — `Key:: value` written in the body, so metadata can live next to the
   prose it describes.

Both populate the same field namespace, so `WHERE due < date(today)` works whether `due` came
from frontmatter or an inline field.

## Inline-field syntax

```markdown
Status:: active
Priority:: 8
Deadline:: 2026-06-30
Owner:: [[Jane Doe]]
```

- `Key:: value` anywhere on a line creates a full-line field.
- **Bracketed** forms render the key inline with the text:
  - `[priority:: high]` — visible key+value in the sentence.
  - `(priority:: high)` — value visible, key hidden.
- Keys are normalized: `Due Date::` is queryable as `due-date` (lowercased, spaces → hyphens).
  Prefer simple lowercase keys to avoid surprises.
- Values are typed by shape, like frontmatter: bare numbers are numbers, `[[...]]` are links,
  ISO dates are dates.

## DQL query types

A query lives in a fenced ```dataview``` code block. The first word is the query type:

````markdown
```dataview
TABLE priority, due
FROM "Projects"
WHERE status = "active"
SORT due ASC
```
````

| Type | Output |
|------|--------|
| `LIST` | A bullet list of pages (optionally `LIST <expr>` for a custom label) |
| `TABLE` | A table; `TABLE col1, col2 AS "Header"` defines columns |
| `TASK` | The matching task checkboxes (`- [ ] …`), interactively checkable |
| `CALENDAR <dateField>` | A calendar heat-map keyed on a date field |

## Clauses

Compose a query from these clauses (in roughly this order):

| Clause | Purpose | Example |
|--------|---------|---------|
| `FROM` | Source: folder, tag, link, or combo | `FROM "Projects" AND #active` |
| `WHERE` | Filter rows by a boolean expression | `WHERE done = false AND due <= date(today) + dur(7 days)` |
| `SORT` | Order results | `SORT due ASC, priority DESC` |
| `GROUP BY` | Aggregate rows under a key | `GROUP BY status` |
| `FLATTEN` | Expand a list field into one row per item | `FLATTEN file.tasks AS task` |
| `LIMIT` | Cap the number of rows | `LIMIT 20` |

`FROM` sources:

- `"Folder"` — notes under a folder (quoted path).
- `#tag` — notes carrying a tag (`#project/active` matches the hierarchy).
- `[[Note]]` — notes that link to `Note`; `outgoing([[Note]])` for the reverse.
- Combine with `AND` / `OR` / `-` (exclude): `FROM #work AND -"Archive"`.

## Implicit fields & functions

Every page exposes a `file` object — useful even with no custom metadata:

| Field | Meaning |
|-------|---------|
| `file.name` | Basename | 
| `file.path` | Vault-relative path |
| `file.link` | A clickable link to the page |
| `file.tags` | All tags on the page |
| `file.ctime` / `file.mtime` | Created / modified timestamps |
| `file.tasks` | The task items in the page |

Common functions in `WHERE`/`TABLE` expressions:

- `date(today)`, `date(now)` — current date/time; `dur(7 days)` — a duration for date math.
- `contains(list, value)`, `length(list)` — list predicates.
- `choice(cond, a, b)` — inline conditional.
- `dateformat(date, "yyyy-MM-dd")` — format a date for display.

Example — projects due within a week, newest first:

````markdown
```dataview
TABLE due, priority, file.mtime AS "Updated"
FROM "Projects"
WHERE due AND due <= date(today) + dur(7 days) AND done = false
SORT due ASC
```
````

## Inline DQL

A single value can be embedded in prose with an inline query (note the `=`):

```markdown
This note was last edited `= this.file.mtime`.
Days until launch: `= (date(2026-09-01) - date(today)).days`
```

`this` refers to the current page, so `this.file.mtime` / `this.due` read the current note's
fields. Inline DQL renders one scalar value, not a table.
