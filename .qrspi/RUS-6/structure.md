# Structure Outline — Create a new agent skill called using-graphite-cli

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

No programmatic types. This skill is Markdown content. The "types" here are the
SKILL.md frontmatter schema and the references file set, expressed as document contracts below.

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — YAML block fenced by `---`, copied field-shape-verbatim from an existing SKILL.md (ref: design §Pattern Decisions / Risk Register, Q3).
- `ReferenceDoc { path: string, sections: string[] }` — on-demand `.md` under `references/`, linked by bare backtick relative path in SKILL.md prose (ref: design §Desired End State, Q6).

## Modified Types

None. The design specifies no modifications to existing files (ref: design §Delta).

## Contracts

These are document-level contracts (the cross-file interfaces an author must honor), not code signatures.

- `SKILL.md frontmatter` — exactly five fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) between `---` fences; `name` MUST equal the directory name `using-graphite-cli` (ref: design §Desired End State, Q1, Q3).
- `description field` — front-loaded concrete trigger phrases + "Use when…" phrasing; quote the value if it contains `:`/`'`/comma (ref: design §Risk Register, Q5).
- `allowed-tools value` — scoped `Bash(gt:*)` plus `Read`, per Decision 3 / OQ3 (ref: design §Pattern Decisions Decision 3). UNVERIFIED until OQ3 is resolved (see Unverified Assumptions).
- `SKILL.md → references link` — each reference file is pointed to by bare backtick-wrapped relative path in SKILL.md prose; content is NOT inlined (progressive disclosure, ref: Q6).
- `SKILL.md budget` — under 500 lines AND under ~5000 tokens (bytes/4 ≈ tokens); measured with `wc -l`/`wc -c` (ref: design §Risk Register, Q7).
- `Required inline content set` — SKILL.md body MUST contain: single-commit-per-branch hard rule; no-raw-git prohibition; Create→Submit→Modify→Sync loop; stack navigation + directionality (downstack=toward trunk, upstack=away); conflict resolution via `gt continue` (with explicit `git rebase --continue` prohibition); submit-flag defaults `--no-edit --publish`; pointers into references (ref: design §Desired End State acceptance criteria).
- `references/command-reference.md content set` — full `gt` catalog: init/config, create, submit + flags, modify, sync, navigation, downstack/upstack, restack, branch split, merge order (ref: design §Delta).
- `references/edge-cases.md content set` — conflict-resolution detail, metadata-drift recovery, trunk misdetection, deep-stack guidance, GitHub/CODEOWNERS integration (ref: design §Delta).

## Slice 1: Author the using-graphite-cli skill (SKILL.md + references)

**Goal:** A complete, valid, budget-compliant `using-graphite-cli` skill exists at `.claude/skills/using-graphite-cli/` — SKILL.md plus both reference files — satisfying every acceptance criterion in design §Desired End State. This is the end-to-end deliverable of the ticket and is verifiable on its own.

**Rationale for single slice:** The SKILL.md and its two reference files are mutually dependent — SKILL.md links into the references and the content split is editorial across all three. None can be meaningfully verified in isolation (a SKILL.md with dangling reference links, or orphan reference files, is incomplete). This is one unit of authoring work. Per Decision 1, there is no agent to spawn, so no separate agent-definition file. Validation (budget check, frontmatter check, dangling-link check, and the skill-creator/eval loop if applicable) is the final step of this slice, not a separate slice.

**Files touched:**

- ✨ `.claude/skills/using-graphite-cli/SKILL.md` — five-field frontmatter + always-needed inline content (hard rules, Create→Submit→Modify→Sync loop, navigation/directionality, conflict-resolution flow, submit-flag defaults, pointers into references) (ref: design §Delta).
- ✨ `.claude/skills/using-graphite-cli/references/command-reference.md` — full `gt` command catalog (ref: design §Delta).
- ✨ `.claude/skills/using-graphite-cli/references/edge-cases.md` — conflict detail, metadata-drift recovery, trunk misdetection, deep-stack, GitHub/CODEOWNERS (ref: design §Delta).

**Verification:**

- [ ] `wc -l .claude/skills/using-graphite-cli/SKILL.md` < 500 and `wc -c` / 4 < 5000 (ref: Q7).
- [ ] Frontmatter has exactly the five fields between `---` fences; `name` == `using-graphite-cli` == directory name (ref: Q1, Q3).
- [ ] Every backtick-relative-path reference in SKILL.md resolves to an existing file under `references/`; no reference content is inlined.
- [ ] SKILL.md body contains each required inline element: single-commit-per-branch rule, no-raw-git prohibition, full Create→Submit→Modify→Sync loop, navigation + directionality definitions, `gt continue` conflict flow with explicit `git rebase --continue` prohibition, `--no-edit --publish` submit defaults, and warning against mixing raw git branch/rebase with tracked branches.
- [ ] `command-reference.md` and `edge-cases.md` each cover their full content set (see Contracts).
- [ ] If skill-creator is available in the build environment (OQ1), the skill was authored/validated through it and its eval loop; otherwise the deferral is documented in the PR.

**Context cost:** M
**Depends on:** none

## Slice 2 (CONDITIONAL): Reconcile evals/graphite-evals.json with run_eval.py

**Goal:** `evals/graphite-evals.json` runs cleanly through `scripts/run_eval.py` — i.e., it uses the `name`/`cases` schema with the assertion shape `run_eval.py` requires, instead of the current `skill_name`/`evals` + `{text, type}` shape that raises `ValueError` (ref: Q9, Q10). This is independently runnable and verifiable (execute the harness, observe no `ValueError`), giving it a genuine testability boundary distinct from Slice 1.

**INCLUDE THIS SLICE ONLY IF** OQ2 resolves to "Definition of Done includes running the eval suite." If the ticket scope is "build the skill" and excludes running evals, OMIT this slice and document the deferral in the PR (ref: design §Risk Register row 1, OQ2).

**Files touched:**

- ⚠️ `evals/graphite-evals.json` — convert top-level `skill_name`→`name`, `evals`→`cases`, and `{text, type}` assertion objects to the format used by `evals/suite.json` / required by `scripts/run_eval.py` (ref: Q9, Q10).

**Verification:**

- [ ] `python scripts/run_eval.py` (or the documented invocation) runs `graphite-evals.json` without raising `ValueError`.
- [ ] All 5 converted cases parse and execute; results recorded.

**Context cost:** S
**Depends on:** Slice 1 (the eval suite exercises the skill authored in Slice 1)

---

## Unverified Assumptions

- **OQ1 / "Anthropic skill builder skill" as hard requirement:** The design cannot confirm whether building via skill-creator is a hard process gate, because skill-creator is not in-repo (ref: Q2, design OQ1). If mandatory, the human must confirm skill-creator is available in the build environment before Slice 1 starts. Affects *how* Slice 1 is executed, not *what* it produces.
- **OQ2 / eval-suite scope:** Whether the Definition of Done includes running `evals/graphite-evals.json` is undecided (design OQ2). This gates whether Slice 2 is in or out of scope. Cannot be mapped to concrete work until resolved.
- **OQ3 / execute-vs-advise → `allowed-tools` value:** Whether the skill should execute `gt` (needs `Bash(gt:*)`) or only advise the orchestrating agent is unresolved (design OQ3, Decision 3). The `allowed-tools` contract value above (`Bash(gt:*)` + `Read`) is the design's pending recommendation, not a confirmed value.
- **OQ4 / references file count:** The design proposes splitting references into `command-reference.md` + `edge-cases.md`, but the only in-repo precedent (`qrspi-work`) uses a single reference file (design OQ4, Q6). Slice 1 assumes the two-file split; if OQ4 resolves to "one combined file," merge the two reference content sets into a single `references/*.md` (does not change the slice boundary).
- **Trigger/auto-invocation firing is unverifiable in-repo:** No in-repo trigger-accuracy tooling exists (ref: Q10, Q11). The `description` field is hand-crafted per the front-loaded-trigger pattern, but whether it actually fires cannot be checked from repo files.
