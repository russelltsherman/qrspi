# Structure Outline — Create a new agent skill using argo workflows cli

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This is a Markdown documentation/skill artifact, not a code change — there are no programmatic types. The structural "types" are file artifacts with required shapes:

- `SKILL.md frontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }` — repo-standard 5-field shape (ref: design Decision 3, Q3). Invariant: directory name == `name` == `command` minus leading slash (ref: Q9).
- `reference file` — a plain Markdown file under `references/` loaded on demand by relative path via the `Read` tool; natural-language progressive disclosure, no templating (ref: Q6).

## Modified Types

- None. No code types are added or changed (ref: design §Delta — "No new DB queries, middleware, or eval cases").

## Contracts

These are the cross-file interface invariants the skill must honor — the "contract" between the SKILL.md body and its reference files, and between the skill and the harness.

- `SKILL.md body → references/*.md` — the body MUST name each reference file and state when to open it (decision-first overview + pointers). The agent discovers references only through these pointers; an unreferenced file is dead (ref: Q6, Q8, design §Delta).
- `directory name == frontmatter.name == frontmatter.command (sans leading "/")` — naming invariant; must hold for `using-argo-workflows-cli` (ref: Q9, Decision 2).
- `SKILL.md body ≤ 500 lines / 5000 tokens` — budget contract; no automated enforcement exists, so it must be checked manually (ref: Q7, Risk Register).
- `frontmatter has exactly the 5 repo-standard fields` — name, description, command, argument-hint, allowed-tools; no `version`, no extras (ref: Q3, Decision 3).
- `all CLI examples use non-interactive, scriptable flags` — explicit `--namespace`, lint/dry-run before submit (ref: Q4, design §Desired End State).

## Slice 1: Author the `using-argo-workflows-cli` skill (body + references)

**Goal:** A complete, agentskills.io-conformant skill exists at `.claude/skills/using-argo-workflows-cli/` with a lean SKILL.md body and all reference files, built via the global `skill-creator` skill and reconciled to repo conventions. End-to-end testable: the skill is auto-discoverable, frontmatter is valid, the body is under budget, and every reference file is reachable from a body pointer and covers its assigned acceptance criteria.

**Rationale for single slice:** The SKILL.md body and the four reference files are mutually dependent — the body's only function is to summarize and point into the references, and the references are dead content without the body's pointers. Neither half verifies meaningfully alone (a body with no references fails the coverage criteria; references with no body fail discoverability). This is one cohesive unit a developer builds in one sitting using `skill-creator`, per design Decision 1 (Option B). Splitting body from references would manufacture a false testability boundary. 5 files, under the 10-file limit.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/SKILL.md` — lean body: 5-field frontmatter, when-to-use, decision-first overview, pointers to each reference file (ref: design §Delta).
- ✨ `.claude/skills/using-argo-workflows-cli/references/cli-commands.md` — full command-group catalog: submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, template — with flags and non-interactive submission conventions (ref: design §Desired End State, Q4).
- ✨ `.claude/skills/using-argo-workflows-cli/references/templates.md` — DAG vs Steps decision criteria, template authoring, parameters/variables, WorkflowTemplate vs ClusterWorkflowTemplate scope.
- ✨ `.claude/skills/using-argo-workflows-cli/references/reliability.md` — retry strategy / exponential backoff, error handling, timeouts, resource management (limits, nodeSelector, parallelism, synchronization), artifact best practices (keys, parameterization, GC).
- ✨ `.claude/skills/using-argo-workflows-cli/references/cron-and-debugging.md` — CronWorkflow lifecycle (create/list/suspend/resume/delete/lint/get) and the debugging escalation path (`argo get` → `argo logs` → `kubectl describe`).

**Verification:**

- [ ] Directory layout matches agentskills.io: `using-argo-workflows-cli/SKILL.md` + `references/` (ref: Q1).
- [ ] Frontmatter has exactly the 5 repo-standard fields and the directory == `name` == `command` (sans `/`) invariant holds (ref: Q3, Q9).
- [ ] SKILL.md body is ≤ 500 lines and ≤ 5000 tokens (manually counted, e.g. `wc -l`; no automated check exists — ref: Q7).
- [ ] Every reference file is named in the body with explicit when-to-open guidance; no orphan reference files (Contracts).
- [ ] All 15 command groups from the acceptance criteria appear in `cli-commands.md`.
- [ ] Each named convention (DAG/Steps decision, retry/backoff, debugging escalation, CronWorkflow lifecycle, resource conventions, artifact best practices) is present in its assigned reference file and summarized in the body.
- [ ] All CLI invocations use non-interactive/scriptable flags (explicit `--namespace`, lint/dry-run before submit) — ref: Q4.
- [ ] `skill-creator` was used to scaffold/refine, and its output was reconciled to the repo's 5-field frontmatter and directory layout (ref: Q2, Risk Register).

**Context cost:** L
**Depends on:** none

## Slice 2 (conditional): Register skill in project `.claude/CLAUDE.md`

**Goal:** If OQ3 is answered "yes," `using-argo-workflows-cli` is listed in the project `.claude/CLAUDE.md` "Available skills" section so it is documented alongside the workflow skills. Independently verifiable: the file lists the new skill.

**Conditional:** Skip entirely unless OQ3 is resolved to require registration. This is a genuine, separable boundary from Slice 1 (the skill functions without it — skills are auto-discovered, ref: Q1, Q9), so it is its own slice rather than folded into Slice 1. Note that `.claude/CLAUDE.md` currently lists only `qrspi-*` workflow skills, so adding a non-`qrspi-` capability skill here is a documentation-convention decision pending OQ1/OQ3.

**Files touched:**

- ⚠️ `.claude/CLAUDE.md` — add `using-argo-workflows-cli` to the "Available skills" list with a one-line description.

**Verification:**

- [ ] OQ3 has been resolved "yes" before doing this slice.
- [ ] `.claude/CLAUDE.md` lists `using-argo-workflows-cli` with a description consistent with the other entries.

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

These are claims from design.md that could not be mapped to a concrete file/interface and need human attention before planning:

- **OQ1 — skill name (`using-argo-workflows-cli` vs a `qrspi-` prefix).** Slice 1's directory name, frontmatter `name`, and `command` all depend on this. The structure assumes the recommended `using-argo-workflows-cli` (design Decision 2, Option A). If reversed, every file path in Slice 1 changes. **Blocks Slice 1.**
- **OQ2 — `allowed-tools` scope.** Design Decision 3 leaves open whether the skill is read-only guidance (`Read` + scoped read `Bash`) or may execute `argo`/`kubectl`. This determines the frontmatter `allowed-tools` value and whether CLI examples are advisory or executable. **Affects Slice 1 frontmatter.**
- **OQ3 — register in `.claude/CLAUDE.md`?** Gates whether Slice 2 runs at all (design §Delta calls this optional and an Open Question).
- **OQ4 — SKILL.md conformance eval case in scope?** Design marks this out of scope (ref: Q11). No slice creates an eval case. If brought in scope, a new slice touching `evals/`/`scripts/` would be required — flagging so planning can confirm exclusion.
- **OQ5 — target argo CLI / Argo Workflows version.** The reference files' flag and feature accuracy depend on this. The design's mitigation is to keep guidance principle-based and note the targeted version; the specific version string is unresolved. **Affects content of all reference files in Slice 1.**
- **"Built using the Anthropic skill builder skill" acceptance criterion.** This maps to a build-time action (invoke the global `skill-creator`), not a committed file (ref: Q2). It is verifiable only as a process step, not an artifact — captured as a Slice 1 verification checkbox, but there is no in-repo evidence it occurred, so reviewers must trust the build log.
