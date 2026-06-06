# Implementation Plan — Create a new agent skill using the omlx CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 22

> Note: this ticket ships a self-contained knowledge/reference *skill* authored via the external
> `skill-creator` skill — not application code. Steps create markdown artifacts; "tests" are
> structural/content checks (frontmatter order, three-way identity, body budget, dead-link scan),
> since the repo has no validator (structure.md C3, design.md §Current State). omlx CLI facts are
> sourced solely from the ticket — do not invent flags beyond it (structure.md Unverified
> Assumptions OQ2).

## Slice 1: Author the `using-omlx-cli` skill (SKILL.md + references)

### Setup

1. ✨ Invoke the external `skill-creator` skill to scaffold the new skill at
   `.claude/skills/using-omlx-cli/` (satisfies C7; OQ1 — invocation contract is out-of-repo, capture
   that skill-creator was the authoring path). All subsequent file steps are performed through /
   within that authoring flow.
2. ✨ Create directory `.claude/skills/using-omlx-cli/references/` — companion home for topic-split
   long-form content (SkillDir contract; design.md Decision 3).

### Core Logic — SKILL.md (thin entry point)

3. ✨ Create `.claude/skills/using-omlx-cli/SKILL.md` — write YAML frontmatter only, fields in the
   exact observed order `name → description → command → argument-hint → allowed-tools`
   (SkillFrontmatter type; C2). Set `name: using-omlx-cli`, `command: /using-omlx-cli`
   (three-way identity; C1).
4. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — set the `description` field to embed
   "Use when…" trigger phrases (Apple Silicon, local LLM inference, omlx).
   - **Current:** `description:` placeholder from scaffold
   - **After:** `description:` containing "Use when…" cues per design.md §Desired End State Q10
5. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — add lifecycle overview section
   (install / serve / configure / monitor / stop) with a relative pointer to
   `references/serve-flags.md` for flag detail (C4; design.md §Desired End State).
6. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — add memory-tier model-size summary
   (16/24/32/64 GB) with a relative pointer to `references/memory-tiers.md` (C4).
7. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — add two-tier (hot/cold) KV-cache summary
   referencing `--paged-ssd-cache-dir` / `--hot-cache-max-size`, pointing to
   `references/memory-tiers.md` for tuning tables (C4).
8. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — add OpenAI-compatible API + MCP + agent-launch
   summary (`/v1/chat/completions`, `/v1/embeddings`, `/v1/messages` @ `http://localhost:8000/v1`;
   `--mcp-config`; `omlx launch <agent>`), pointing to `references/serve-flags.md`.
9. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — add oMLX-vs-Ollama-vs-LM-Studio
   decision-guidance section encoding the ticket's "prefer when" rules.
10. ⚠️ Modify `.claude/skills/using-omlx-cli/SKILL.md` — add troubleshooting index pointing to
    `references/troubleshooting.md` (C4).

### Core Logic — references/

11. ✨ Create `.claude/skills/using-omlx-cli/references/serve-flags.md` (ReferenceFile) — full
    `omlx serve` flag reference, lifecycle detail, `--paged-ssd-cache-dir` / `--hot-cache-max-size`,
    API endpoints, `--mcp-config`, and `omlx launch <agent>` patterns.
12. ✨ Create `.claude/skills/using-omlx-cli/references/memory-tiers.md` (ReferenceFile) — per-tier
    (16/24/32/64 GB) model-size recommendation table and hot/cold KV-cache tuning tables.
13. ✨ Create `.claude/skills/using-omlx-cli/references/troubleshooting.md` (ReferenceFile) —
    Metal OOM crash loop, silent memory pressure, mixed-workload instability, model-not-showing.

### Tests / Structural checks

14. Run: `python3 -c "import sys,re,yaml" 2>/dev/null || true; sed -n '/^---$/,/^---$/p' .claude/skills/using-omlx-cli/SKILL.md`
    — confirm frontmatter parses and field order is `name → description → command → argument-hint → allowed-tools`.
    - **Expected:** five fields present, in that exact order (C2).
15. Run: `awk 'NR==FNR{next} END{print NR}' .claude/skills/using-omlx-cli/SKILL.md; wc -l .claude/skills/using-omlx-cli/SKILL.md`
    — confirm SKILL.md body < 500 lines (proxy for < 5000 tokens; C3).
    - **Expected:** line count < 500; bulk lives in `references/`.
16. Run: `grep -oE 'references/[A-Za-z0-9_-]+\.md' .claude/skills/using-omlx-cli/SKILL.md | sort -u`
    then verify each path exists — no dead links (C4).
    - **Expected:** every referenced companion exists; every companion is referenced.

### Verify Slice 1

17. **Checkpoint:** `ls .claude/skills/using-omlx-cli/SKILL.md .claude/skills/using-omlx-cli/references/serve-flags.md .claude/skills/using-omlx-cli/references/memory-tiers.md .claude/skills/using-omlx-cli/references/troubleshooting.md && test ! -e .claude/agents/using-omlx-cli.md && echo OK`
    - [ ] SKILL.md and all three `references/*.md` exist (C5).
    - [ ] frontmatter field order `name → description → command → argument-hint → allowed-tools` (C2).
    - [ ] folder == `name` == `/command` == `using-omlx-cli`; no collision in `.claude/skills/` (C1).
    - [ ] `description` contains "Use when…" trigger phrases (Apple Silicon, local LLM inference, omlx).
    - [ ] SKILL.md body < 500 lines / < 5000 tokens (C3).
    - [ ] every `references/` file linked by relative path; no dead links (C4).
    - [ ] no `.claude/agents/using-omlx-cli.md` created (C6).
    - [ ] all eight acceptance behaviors present across SKILL.md + references (design.md §Desired End State).
    - [ ] skill-creator was the authoring path and its eval/validation loop ran (C7).

---

## Slice 2: (Optional) Register skill in the human-facing catalog

> Gated on OQ3 — skip if the reviewer decides the unvalidated docs should not be touched.

### Core Logic

18. ⚠️ Modify `.claude/CLAUDE.md` — add `/using-omlx-cli` to the "Available skills" list with an
    accurate one-line description (documentation-only; not validated; design.md §Delta, OQ3).
    - **Current:** "Available skills" list ends at `/qrspi-pr <ticket-id> — Prepare pull request summary`
    - **After:** same list with an appended `/using-omlx-cli — <one-line description>` entry; existing entries untouched

### Tests

19. Run: `grep -n 'using-omlx-cli' .claude/CLAUDE.md`
    - **Expected:** exactly one new line in the skills/slash-command list referencing the skill.

### Verify Slice 2

20. **Checkpoint:** `grep -c 'using-omlx-cli' .claude/CLAUDE.md`
    - [ ] `using-omlx-cli` appears in the `.claude/CLAUDE.md` skills list with an accurate one-line description.
    - [ ] no behavior change — pure documentation edit; existing entries untouched.

---

## Rollback Notes

- Steps 1–13: Slice 1 creates only new files under `.claude/skills/using-omlx-cli/`. To reverse,
  delete the directory: `rm -rf .claude/skills/using-omlx-cli/`. No existing files are modified, so
  removal is non-destructive to the rest of the repo.
- Step 18: Slice 2 edits the documentation-only `.claude/CLAUDE.md`. To reverse, remove the single
  appended `/using-omlx-cli` line; existing entries are untouched, so a line-level revert is safe.
- No DB migrations, config changes, or destructive operations are involved.
