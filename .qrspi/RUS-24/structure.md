# Structure Outline — Create a new agent skill using the omlx CLI

**Design basis:** design.md @ 2026-06-04T13:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: this ticket ships a self-contained knowledge/reference *skill*, not application code.
> There are no runtime types or function signatures. The "types" and "contracts" below are the
> structural contracts the artifact must satisfy: the SKILL.md frontmatter schema, the three-way
> name identity, and the on-demand `references/` linking convention (all from design.md §Pattern
> Decisions and §Desired End State).

## New Types

- `SkillFrontmatter { name: kebab-string, description: string-with-"Use when…"-cues, command: "/"+name, argument-hint: string, allowed-tools: string[] }`
  — flat YAML block at top of SKILL.md, fields emitted in the repo's observed order
  `name → description → command → argument-hint → allowed-tools` (ref: design.md §Desired End State, Decision 1).
- `SkillDir { SKILL.md, references/ }` — directory at `.claude/skills/using-omlx-cli/`;
  `references/` holds topic-split companions linked from the body by relative path
  (ref: design.md Decision 3).
- `ReferenceFile { relative-path linked from SKILL.md body, long-form markdown }` — one per topic
  (serve-flags, memory-tiers, troubleshooting), read on demand (ref: design.md Decision 3 Option B).

## Modified Types

- None required. The skill catalog / slash-command list in `.claude/CLAUDE.md` is documentation-only
  and unvalidated; updating it is optional polish gated on OQ3 (ref: design.md §Delta, OQ3).

## Contracts

- **C1 — Three-way name identity:** folder name == frontmatter `name` == `/command` suffix,
  all equal to `using-omlx-cli`, kebab-case lowercase, unique within `.claude/skills/`
  (ref: design.md Decision 2; §Current State Q1/Q4).
- **C2 — Frontmatter field order:** `name → description → command → argument-hint → allowed-tools`,
  matching all ten existing skills (ref: design.md §Desired End State, Q2).
- **C3 — Body budget:** SKILL.md body < 500 lines / < 5000 tokens; overflow pushed to `references/`.
  Honored manually — no in-repo validator (ref: design.md §Desired End State, Q7).
- **C4 — Reference linking:** every `references/*.md` file is named in the SKILL.md body by its
  relative path; no manifest, read on demand (ref: design.md Decision 3).
- **C5 — Discovery location:** skill is discoverable only because it physically resides at
  `.claude/skills/using-omlx-cli/SKILL.md` (ref: design.md §Current State Q5).
- **C6 — Self-contained:** no `.claude/agents/using-omlx-cli.md` body is created; this skill is
  reference knowledge, not a phase orchestrator (ref: design.md Decision 1).
- **C7 — Authoring tool:** the skill is authored by invoking the external `skill-creator`
  ("Anthropic skill builder") skill; its invocation contract is out-of-repo (ref: design.md OQ1).

## Slice 1: Author the `using-omlx-cli` skill (SKILL.md + references)

**Goal:** A complete, discoverable, self-contained skill authored via `skill-creator` whose
SKILL.md covers the full omlx lifecycle and links topic-split reference companions — verifiable by
locating the skill, validating its frontmatter/identity/budget, and confirming each referenced
companion exists.
**Files touched:**

- ✨ `.claude/skills/using-omlx-cli/SKILL.md` — thin entry point: frontmatter (C1/C2) +
  lifecycle overview (install/serve/configure/monitor/stop), memory-tier model-size summary,
  two-tier KV-cache summary, OpenAI-compatible API + MCP + agent-launch summary,
  oMLX-vs-Ollama-vs-LM-Studio opinion, troubleshooting index, and relative pointers into `references/`.
- ✨ `.claude/skills/using-omlx-cli/references/serve-flags.md` — full `omlx serve` flag reference,
  lifecycle detail, `--paged-ssd-cache-dir` / `--hot-cache-max-size`, API endpoints
  (`/v1/chat/completions`, `/v1/embeddings`, `/v1/messages` @ `http://localhost:8000/v1`),
  `--mcp-config` and `omlx launch <agent>` patterns.
- ✨ `.claude/skills/using-omlx-cli/references/memory-tiers.md` — per-tier (16/24/32/64 GB) model-size
  recommendation table and two-tier (hot/cold) KV-cache tuning tables.
- ✨ `.claude/skills/using-omlx-cli/references/troubleshooting.md` — exhaustive failure modes:
  Metal OOM crash loop, silent memory pressure, mixed-workload instability, model-not-showing.

**Verification:**
- [ ] `ls .claude/skills/using-omlx-cli/SKILL.md` and each `references/*.md` exists (C5).
- [ ] SKILL.md frontmatter has fields in order `name → description → command → argument-hint → allowed-tools` (C2).
- [ ] folder == `name` == `/command` == `using-omlx-cli` (C1); no collision with existing `.claude/skills/` folders.
- [ ] `description` contains "Use when…" trigger phrases (Apple Silicon, local LLM inference, omlx) (ref: design.md §Desired End State, Q10).
- [ ] SKILL.md body < 500 lines / < 5000 tokens (C3); bulk lives in `references/`.
- [ ] every `references/` file is linked by relative path from the SKILL.md body (C4); no dead links.
- [ ] no `.claude/agents/using-omlx-cli.md` was created (C6).
- [ ] all eight acceptance behaviors in design.md §Desired End State are present across SKILL.md + references.
- [ ] skill-creator was the authoring path and its eval/validation loop was run (C7; see Unverified Assumptions).

**Context cost:** M
**Depends on:** none

## Slice 2: (Optional) Register skill in the human-facing catalog

**Goal:** The new skill appears in the documentation-only skill catalog and slash-command list so
humans can discover it — independently verifiable by grepping the catalog. Gated on OQ3; skip if the
reviewer decides the unvalidated docs should not be touched.
**Files touched:**

- ⚠️ `.claude/CLAUDE.md` — add `/using-omlx-cli` to the "Available skills" list and any skill catalog
  (documentation-only; not validated) (ref: design.md §Delta, OQ3).

**Verification:**
- [ ] `using-omlx-cli` appears in the `.claude/CLAUDE.md` skills/slash-command list with an accurate one-line description.
- [ ] no behavior change — pure documentation edit; existing entries untouched.

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- **skill-creator invocation contract (OQ1, C7):** the external `skill-creator` skill's exact inputs,
  outputs, file-output target, create-vs-edit semantics, and validation-reporting path are NOT in the
  repo (design.md §Current State Q3/Q5/Q7/Q9/Q11). The "built with the Anthropic skill builder"
  acceptance criterion therefore cannot be mechanically verified inside this project and depends on
  the global harness behaving as assumed.
- **omlx CLI facts (OQ2):** every omlx flag, port (`:8000`), endpoint, KV-cache option, MCP/agent
  pattern, and memory-tier figure originates solely from the ticket — omlx returns zero hits in the
  repo and in research. No upstream-docs source is confirmed to validate against; flags must not be
  invented beyond the ticket (design.md Risk Register, OQ2).
- **Skill name `using-omlx-cli` (OQ4):** breaks the repo's uniform `qrspi-*` namespace. Recommended
  by Decision 2 but unconfirmed by a human.
- **Body budget enforcement (C3):** the < 500-line / < 5000-token limit has no in-repo validator;
  compliance is honored manually and only externally checkable via skill-creator.
- **Triggering accuracy:** the eval/triggering harness is a non-functional placeholder (stub core,
  empty golden set), so "Use when…" trigger effectiveness can only be checked by manual judgment,
  not measured (design.md Risk Register, Q8/Q10).
