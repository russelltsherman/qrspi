# Structure Outline — Create a new agent skill using Codex CLI

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This is a documentation-authoring task; it produces Markdown artifacts, not code.
There are no programmatic types. The closest structural analogue is the `SKILL.md`
frontmatter contract, captured here as the schema every artifact must satisfy.

- `SkillFrontmatter { name: slug, description: string|quoted-string, command: slug, argument-hint: string, allowed-tools: comma-separated-list }`
  — the verified in-repo 5-field shape (ref: design §Decision 2, Q3). `name` MUST equal the
  containing directory name and the `command` slug (three-way identity, ref: Q4).

## Modified Types

None. No existing file's schema or interface changes (ref: design §Delta — "Not in scope").

## Contracts

The cross-slice interface is the set of filenames and on-demand load pointers that bind
`SKILL.md` to its `references/`. These names are the contract the body slice consumes and
the reference slice must produce verbatim.

- `SKILL_DIR := .claude/skills/<name>/` — final `<name>` from OQ1; candidate `codex-cli`.
  Decided value is a precondition (see Unverified Assumptions) and must be identical across
  directory name, frontmatter `name`, and `command`.
- `references/sandbox-and-platform.md` — sandbox modes (read-only / workspace-write /
  danger-full-access) + macOS Seatbelt and Linux Bubblewrap+Landlock enforcement (ref: Q9, Decision 3).
- `references/config-toml.md` — `~/.codex/config.toml` vs `.codex/config.toml`, key sections,
  `[profiles.<name>]`, `model_instructions_file`, project-root detection.
- `references/multi-agent.md` — MCP server mode, Agents SDK pipelines, subagents, worktree parallelism.
- On-demand load pointer convention: body references each file via an explicit
  `Read references/<file>.md` instruction tied to a narrow execution path (ref: Q7,
  `qrspi-work` precedent). The exact relative paths above are the binding the body must emit.

## Slice 1: Reference material (`references/`)

**Goal:** Produce the three long-form reference files as standalone, content-complete
Markdown documents. Each is independently verifiable for topic coverage before the body
wires them in. This slice delivers the offloaded knowledge the `SKILL.md` body will point to.
**Files touched:**

- ✨ `.claude/skills/<name>/references/sandbox-and-platform.md` — sandbox modes
  (read-only / workspace-write / danger-full-access) + OS-conditional enforcement: macOS
  Seatbelt, Linux Bubblewrap+Landlock; structured as rule-lists + fenced blocks + hazard
  callouts (ref: Q8 structuring precedent, Q9 NEW PATTERN, Decision 3).
- ✨ `.claude/skills/<name>/references/config-toml.md` — `~/.codex/config.toml` vs
  `.codex/config.toml`, key sections, `[profiles.<name>]`, `model_instructions_file`,
  project-root detection.
- ✨ `.claude/skills/<name>/references/multi-agent.md` — MCP server mode, Agents SDK
  pipelines, subagents, worktree parallelism.

**Verification:**

- [ ] All three files exist under `.claude/skills/<name>/references/` with the exact
      filenames listed in Contracts.
- [ ] `sandbox-and-platform.md` covers all three sandbox modes AND both OS branches
      (macOS Seatbelt, Linux Bubblewrap+Landlock), including the macOS `network_access`
      Seatbelt bug (ref: design §Desired End State, Risk Register).
- [ ] `config-toml.md` documents both config locations, `[profiles.<name>]`, and
      `model_instructions_file`.
- [ ] `multi-agent.md` covers MCP server mode, Agents SDK, subagents, and worktree parallelism.
- [ ] Markdown lints clean (consistent with repo `SKILL.md` style — fenced `bash` blocks, headings).

**Context cost:** M
**Depends on:** none (but requires the `<name>` decision from Unverified Assumptions to fix the directory path).

## Slice 2: `SKILL.md` body + integration + validation

**Goal:** Author the always-loaded `SKILL.md` (frontmatter + body) that consults and points
to the Slice 1 references, then validate the complete skill end-to-end against acceptance
criteria. This is the slice a developer completes in one sitting: the body has no value
without the references it links, and its validation exercises the whole skill.
**Files touched:**

- ✨ `.claude/skills/<name>/SKILL.md` — frontmatter (5-field shape, `name` == directory ==
  `command`) + body sections: overview; approval-mode selection table (suggest / auto-edit /
  full-auto with context→mode decision table, ref: Q8); `codex exec` non-interactive/CI
  patterns (positional, stdin `-`, prompt-plus-stdin; `--json`/`--quiet`; hermetic flags);
  AGENTS.md hierarchy + authoring (`AGENTS.override.md`/`AGENTS.md` discovery, concatenation
  precedence, size cap, nested-dir rules); known limitations + workarounds (re-run
  nondeterminism, macOS `network_access` Seatbelt bug, context-window pressure,
  `--sandbox` override verification); Unix pipe composition examples. Includes explicit
  `Read references/<file>.md` on-demand pointers to all three Slice 1 files (ref: Q7).
  Target body under 500 lines / 5000 tokens (ref: Q6).

**Verification:**

- [ ] Frontmatter has exactly the 5 fields (`name`, `description`, `command`,
      `argument-hint`, `allowed-tools`) and `name` equals the directory name and `command` (ref: Q4).
- [ ] Body contains all required sections: approval-mode table, `codex exec` patterns,
      AGENTS.md authoring, limitations/workarounds, pipe examples.
- [ ] Body emits an explicit `Read references/<file>.md` pointer for each of the three
      reference files, and each pointed-to file exists (cross-slice contract honored).
- [ ] `wc -l SKILL.md` body under 500 lines AND token estimate under 5000 (hand-checked,
      ref: Q6 — unenforced ceiling).
- [ ] skill-creator skill invoked during authoring; invocation recorded as process
      attestation (ref: Risk Register, OQ2 — cannot be verified in-repo).
- [ ] Skill loads / lists without frontmatter-loader error (manual check).

**Context cost:** M
**Depends on:** Slice 1 (body's `Read references/<file>.md` pointers must target files that exist).

---

## Unverified Assumptions

These are claims from design.md that could not be mapped to a concrete, settled value and
need human attention before planning proceeds. The first two are blocking — the directory
path and frontmatter shape are baked into every file in both slices.

- **Final skill `<name>` (OQ1, BLOCKING).** Design defers the name to an Open Question;
  candidate is `codex-cli`, and there is no convention to derive whether it should carry the
  `qrspi-` prefix (all 10 existing skills are `qrspi-`-prefixed domain markers, but this skill
  is not a QRSPI phase). Every file path and the frontmatter `name`/`command` depend on this.
  Must be decided before Slice 1 starts.

- **"Built using the Anthropic skill builder / skill-creator skill" (OQ2).** The skill-creator
  is a global Claude Code skill living outside REPO_ROOT and unreadable under the research
  firewall (ref: Q2, Q5). Whether merely invoking it during implementation satisfies the
  acceptance criterion — and what attestation the reviewer expects — is unverified. Cannot be
  proven in-repo; mapped to a process attestation in Slice 2 verification.

- **agentskills.io frontmatter standard (OQ4).** The ticket cites the agentskills.io
  frontmatter standard, but no such schema exists in-repo (`grep "agentskills"` → 0 hits,
  ref: Q3). The structure conforms to the observed in-repo 5-field shape (Decision 2). Whether
  that satisfies the acceptance criterion, or whether the exact agentskills.io field list must
  be used instead, is unconfirmed. If the answer is "use agentskills.io fields verbatim,"
  the `SkillFrontmatter` contract above changes.

- **agentskills.io `scripts/` and `assets/` directories.** The ticket references agentskills.io
  directory conventions, but `scripts/` and `assets/` are not present in any in-repo skill
  (ref: Q1) and the design includes no such files. Assumed out of scope; confirm none are required.

- **Codex CLI factual content (re-run nondeterminism, macOS `network_access` Seatbelt bug,
  Bubblewrap+Landlock, config.toml schema, MCP/Agents-SDK behavior).** The design asserts
  these as the reference/body subject matter, but none could be verified against in-repo
  sources — Codex CLI is external and the firewall forbade reading external docs. The
  implementer must source accurate, current Codex CLI facts at authoring time; the structure
  cannot validate their correctness.

- **Codex-specific eval suite (OQ3).** Design defers whether to build a third eval suite. This
  structure treats it as deferred / out of scope (no eval files in either slice, ref: §Delta).
  Confirm deferral is acceptable.
