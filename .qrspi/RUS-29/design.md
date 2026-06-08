# Design — Create a new agent skill called writing dockerfiles

**Ticket:** RUS-29
**Research basis:** research.md @ 2026-06-04T11:53:10Z
**Generated:** 2026-06-04T12:10:00Z
**Status:** draft

## Current State

The repo holds exactly ten skills, all `qrspi-*`, under `.claude/skills/<slug>/SKILL.md`; there is no `writing-dockerfiles` skill and no `skill-creator` directory anywhere under REPO_ROOT — skill-creator exists only as an externally-provided, globally-available Claude Code skill (ref: scope note, Q1). The on-disk layout a skill follows in this repo is a per-skill directory named identically to its `name` field, containing a mandatory `SKILL.md` plus optional subdirectories created only when used; the sole attested subdirectory in the repo is `qrspi-work/references/` (ref: Q1, Q8). No skill ships a `scripts/` or `assets/` directory, so those conventions are unattested locally and should be omitted unless needed (ref: Q8).

Reference material is linked from a SKILL.md body by a bare relative path embedded in prose with a "see `references/...`" cue; there is no loader directive, no frontmatter manifest, and no auto-inclusion — the agent opens the file when the prose points there (ref: Q2). The de-facto frontmatter schema across all ten skills is uniform: `name`, `description`, `command`, `argument-hint`, `allowed-tools`; the universal agentskills minimum is `name` + `description`, both always present (ref: Q3). The directory name equals the `name` field verbatim as a lowercase-hyphenated slug, and `command` is `/<name>`; the human-readable phrase appears only in `description` (ref: Q5). Skill `description` is written capability-first followed by a "Use when..." trigger clause, optionally enumerating literal trigger phrases for sharper auto-invocation; YAML values are double-quoted only when they contain `:` or `"` (ref: Q4).

Skill discovery is purely by directory presence — there is no machine-read manifest, and no `settings.json`/`settings.local.json` exists in this worktree (ref: Q6). The `.claude/CLAUDE.md` "Available skills" list (lines 43-53) is human-facing documentation, not a registry the harness parses, and can drift out of sync (ref: Q6). There is no in-repo enforcement of any kind for skills: no frontmatter validator, no size/token gate, no reference-link checker, no skill-targeting tests (ref: Q3, Q7, Q10). The 500-line / 5000-token budget is advisory only — `qrspi-work/SKILL.md` is 565 lines with no tooling objecting (ref: Q7). Validation of a finished skill is manual human review, with `.claude/agents/qrspi-structure.md:40` codifying "invoking skill-creator" as the validation pass for skill-producing work (ref: Q10). The `evals/` + `scripts/run_eval.py` harness is a confirmed inert stub returning empty output, with no skill-authoring fixtures (ref: Q9). The repo's "tests required" convention binds to Python logic via `scripts/qrspi_*_test.py`; documentation-only artifacts carry no executable logic and none of the ten skills ships a sibling test, so a docs skill follows precedent by shipping none and relying on review (ref: Q11). Progress is surfaced via console stdout (status lines and JSON envelopes), not a written report artifact (ref: Q12).

Most QRSPI skills are thin slash-command wrappers that spawn a purpose-built agent from `.claude/agents/<name>.md`, which carries the real prompt (ref: Discovered Patterns). A docs-only capability skill does not fit that wrapper/agent split — it is self-contained prose plus `references/` (ref: Discovered Patterns).

## Desired End State

A new skill exists at `.claude/skills/writing-dockerfiles/SKILL.md` with a `references/` subdirectory, invokable by directory presence and discoverable for auto-invocation. Each acceptance criterion maps as follows:

- **Valid agentskills.io structure + frontmatter** → directory `writing-dockerfiles/` with `name: writing-dockerfiles`, a capability-first `description`, `command: /writing-dockerfiles`, `argument-hint`, and `allowed-tools`, matching the repo's de-facto schema (ref: Q3, Q5).
- **Built using the Anthropic skill builder skill** → authored via the externally-provided `skill-creator` skill; the repo cannot enforce or verify this internally, so it is a process step confirmed by the author (ref: Q1, Q10; see OQ1).
- **SKILL.md under 500 lines / 5000 tokens** → the body stays within budget; since enforcement is advisory only, this is a self-imposed authoring target verified by manual line/token count (ref: Q7).
- **Detailed reference material in `references/`** → language-specific patterns and full examples live in `references/*.md`, linked from the SKILL.md body by inline "see `references/...`" prose cues (ref: Q2).
- **Covers all major conventions** → base image selection, multi-stage builds, layer caching, .dockerignore, security, build args, healthchecks, and signal handling each have a body section, with depth pushed to references.
- **One complete example Dockerfile per language** → references include complete Go, Node.js, Python, Java, and Rust example Dockerfiles.
- **Security guidance: non-root, secrets, scanning** → a dedicated security section covers non-root user creation/`USER`, runtime/build-time secret injection (never `ARG`/`ENV`/`COPY`), and image scanning (Trivy/Grype/Snyk).
- **Signal handling warns against shell form** → an explicit section mandates exec-form `ENTRYPOINT`/`CMD`, warns against shell form swallowing signals, and recommends `tini`/`dumb-init`.

Out of scope per ticket: Docker Compose, orchestration, CI/CD pipeline config, and runtime container configuration.

## Delta

New files:
- `.claude/skills/writing-dockerfiles/SKILL.md` — the skill body: frontmatter + opinionated guidance sections for the eight convention areas + production-readiness, with inline cues into `references/`.
- `.claude/skills/writing-dockerfiles/references/base-images.md` — base image selection, pinning (tag vs digest), distroless/scratch/Alpine decision guidance.
- `.claude/skills/writing-dockerfiles/references/multistage-and-caching.md` — multi-stage build patterns, named stages, layer ordering, cache mounts, `.dockerignore` template.
- `.claude/skills/writing-dockerfiles/references/security.md` — non-root, secrets, package hygiene, scanning, build args.
- `.claude/skills/writing-dockerfiles/references/runtime.md` — healthchecks, signal handling, init processes, labels/EXPOSE/WORKDIR.
- `.claude/skills/writing-dockerfiles/references/languages/` — one file per language (`go.md`, `node.md`, `python.md`, `java.md`, `rust.md`), each with a complete example Dockerfile.

Modified files:
- `.claude/CLAUDE.md` "Available skills" list (lines 43-53) — add a `/writing-dockerfiles` entry for documentation hygiene (non-functional, but prevents drift) (ref: Q6).

No changes to: `scripts/`, `evals/`, any `settings.json` (none exists), or any agent definition — this skill is self-contained and ships no `scripts/` or `assets/` (ref: Q6, Q8). No new tests (docs-only artifact has no logic to bind to) (ref: Q11).

## Pattern Decisions

### Decision 1: Skill shape — self-contained capability vs wrapper/agent split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md with prose guidance + `references/` | Matches docs-skill need; reference material lives where the agent reads it; no orchestration coupling | Diverges from the dominant `qrspi-*` wrapper shape |
| B | Thin SKILL.md wrapper spawning a `.claude/agents/writing-dockerfiles.md` agent | Mirrors the strong repo wrapper/agent convention | The wrapper/agent split exists to dispatch workflow-phase agents, not to deliver static guidance; adds an empty layer with no dispatch to do |

**Recommendation:** Option A
**Rationale:** Research explicitly notes the wrapper/agent split is a workflow-phase convention and that a docs-only skill "would NOT follow this split — it would be self-contained SKILL.md with prose + `references/`" (ref: Discovered Patterns). Option A also matches the one attested `references/` consumer, `qrspi-work` (ref: Q1, Q2).
**NEW PATTERN?** No — it reuses the attested `SKILL.md` + `references/` layout; it simply does not adopt the (inapplicable) wrapper/agent split.

### Decision 2: Reference linking mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bare relative path with a prose "see `references/...`" cue | Exactly the one attested pattern (`qrspi-work`) | Relies on the agent following the cue manually (no auto-load) |
| B | A frontmatter manifest or explicit loader directive listing reference files | Could signal intent more strongly | Unattested in repo; no loader convention exists; risks non-functional cruft |

**Recommendation:** Option A
**Rationale:** Q2 establishes the bare-relative-path-plus-prose-cue as the only attested convention; there is no loader directive or manifest in the repo (ref: Q2).
**NEW PATTERN?** No — directly mirrors `qrspi-work/SKILL.md:282-283`.

### Decision 3: References directory granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Topic-split refs (base-images, caching, security, runtime) + a `languages/` subfolder with one file per language | Keeps SKILL.md body small; each topic loads independently; language examples isolated | More files to maintain; nested subfolder is one level deeper than the attested flat `references/` |
| B | A single large `references/dockerfiles.md` containing everything | Fewest files; flat, exactly matching attested depth | Forces the agent to load all material at once; harder to cite a specific topic; works against the body size budget |

**Recommendation:** Option A
**Rationale:** The acceptance criteria demand both broad convention coverage and per-language examples; topic-split files keep the SKILL.md body under the advisory 500-line budget (ref: Q7) and let the prose cue the agent to exactly the relevant reference. The `languages/` nesting is one level deeper than the only attested example but the harness discovers references by prose path, not by enforced depth (ref: Q2), so it carries no functional risk.
**NEW PATTERN?** Partial — a nested `references/languages/` subfolder is deeper than the single attested flat `references/`. Flagged: justified by the five-language requirement; functionally equivalent since reference resolution is by prose-cited relative path, not a depth-constrained loader (ref: Q2).

### Decision 4: Description / auto-invocation phrasing

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Capability-first + "Use when..." + enumerated trigger phrases (Dockerfile authoring/optimizing/hardening), quoted if it contains `:` | Sharpens auto-invocation; matches the trigger-dense form used by `qrspi-work`/`qrspi-questions` | Slightly longer description |
| B | Short single-sentence capability + "Use when..." only | Matches the 8-of-10 short-form skills; minimal | Weaker auto-invocation matching for varied phrasings |

**Recommendation:** Option A
**Rationale:** Q4 shows both forms coexist with no enforced length cap; the trigger-dense form improves matching for a capability invoked by diverse phrasings ("write a Dockerfile", "optimize this image", "harden my container build"). Quote the YAML value if it contains a colon (ref: Q4).
**NEW PATTERN?** No — reuses the attested long, trigger-dense description form.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| "Built using skill-creator" acceptance criterion is unverifiable in-repo (skill-creator is external, no validator exists) | high | low | Treat as a process step the author attests to; rely on manual review of structural correctness (ref: Q1, Q10); see OQ1 |
| SKILL.md body exceeds the advisory 500-line / 5000-token budget with no tooling to catch it (qrspi-work already does at 565) | med | low | Push depth into `references/`; keep body to the eight section summaries + cues; manually count lines/tokens before completion (ref: Q7) |
| `.claude/CLAUDE.md` skills list drifts (skill invokable without it; easy to forget the doc update) | med | low | Include the CLAUDE.md edit in the Delta as a required hygiene step, not optional (ref: Q6) |
| Nested `references/languages/` depth diverges from the single attested flat `references/`, risking a reviewer flag | low | low | Documented as a flagged partial-new-pattern (Decision 3); resolution is by prose-cited relative path so depth is functionally irrelevant (ref: Q2) |
| Reference prose cues not followed because there is no auto-load mechanism, leaving language examples unread | med | med | Use explicit, imperative "read `references/<topic>.md` before writing X" cues rather than passive parentheticals; mirror the attested cue style (ref: Q2) |

## Open Questions

- OQ1: The "Built using the Anthropic skill builder skill" criterion cannot be verified from inside the repo (skill-creator is external, no in-repo validator) — is author attestation + manual structural review sufficient evidence, or does the reviewer require a skill-creator eval/score artifact (which the repo's own eval harness cannot produce, per Q9)?
- OQ2: Should the `.claude/CLAUDE.md` "Available skills" list update be part of this ticket's deliverable, or is keeping that human-facing list `qrspi-*`-only (treating writing-dockerfiles as a separate, non-workflow capability) the intended boundary?
- OQ3: Is the nested `references/languages/` subfolder acceptable, or should language examples be flattened into `references/lang-<name>.md` to stay exactly at the single attested directory depth?
