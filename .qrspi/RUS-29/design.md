# Design — Create a new agent skill called writing-dockerfiles

**Ticket:** RUS-29
**Research basis:** research.md @ 2026-05-31T16:05:00Z
**Generated:** 2026-05-31T16:08:00Z
**Status:** draft

## Current State

Skills in this repo live under `.claude/skills/<skill-name>/SKILL.md` and are discovered purely by directory presence — there is no manifest, index, or settings.json registration to update (ref: Q1, ref: Q6). All ten existing skills are `qrspi-*` workflow skills; only `qrspi-work` has a subdirectory, `references/`, holding a single load-on-demand topic file, `review-cascade.md` (ref: Q1, ref: Q8). That reference is linked from the body as a bare relative path in prose — `Read references/review-cascade.md for cascade logic.` — not a markdown link (ref: Q2).

Frontmatter on command-style skills uses `name`, `description`, `command`, `argument-hint`, and `allowed-tools`; the `name` field is always kebab-case and always equals the directory name (ref: Q3, ref: Q4). The `description` field doubles as the trigger spec — every skill ends its description with "Use when…/Trigger on…" guidance (ref: Q3). A separate schema exists for internal agents under `.claude/agents/*.md` (`model` + `claude.tools`), which is not relevant to a content skill (ref: Q3).

There is no automated enforcement of skill body size, and no eval coverage for content skills: the harness in `evals/` + `scripts/` is purpose-built for QRSPI workflow phase prompts and asserts on produced artifacts like `questions.md`, not on a prose skill's structure or trigger accuracy (ref: Q7, ref: Q9, ref: Q12). Existing bodies range 25–730 lines; `qrspi-work` at 730 already exceeds the 500-line target, so the repo does not enforce it (ref: Q7). The repo contains no reusable Dockerfiles — `docs/container-sandbox/` is runtime-sandbox prose, and `.devcontainer/` is devcontainer config — so example Dockerfiles must be authored fresh (ref: Q11). The Anthropic skill-creator referenced by the ticket is a host-level capability, not present in `REPO_ROOT` (ref: Q5).

## Desired End State

A new skill at `.claude/skills/writing-dockerfiles/` that, when triggered, guides an agent to write and optimize production-grade, security-hardened Dockerfiles. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure + valid frontmatter** → `SKILL.md` with kebab-case `name: writing-dockerfiles` matching the dir, a trigger-bearing `description`, plus a `references/` directory (ref: Q1, Q3, Q4).
- **Built using the skill-creator** → the skill is produced/validated through the skill-creator skill-creation + eval loop (host-level); artifacts conform to the structure it expects (ref: Q5). Per global directive, skill creation goes through skill-creator, not ad-hoc.
- **Body under 500 lines / 5000 tokens** → the SKILL.md body carries only the concise opinionated checklist of conventions; depth is offloaded to references (ref: Q7, Q8).
- **Detailed reference material in `references/`** → language-specific patterns and worked examples live in `references/` files, loaded on demand, mirroring the `qrspi-work` relative-path linking style (ref: Q2, Q8).
- **Covers all major conventions** → base image selection, multi-stage builds, layer caching, `.dockerignore`, security, build args, healthchecks, signal handling each appear in the body, with detail in references.
- **≥1 complete example Dockerfile per language (Go, Node.js, Python, Java, Rust)** → in `references/`.
- **Security guidance: non-root, secrets management, image scanning** → a dedicated security section in the body and a security reference.
- **Signal handling warns against shell form, recommends exec form + init process** → explicit body section.

Scope exclusions hold: no Docker Compose, orchestration, CI/CD pipeline config, or runtime container config — build-time concerns only.

## Delta

New files (all under `.claude/skills/writing-dockerfiles/`):

- `SKILL.md` — frontmatter (`name`, `description`; optionally `command`/`argument-hint`/`allowed-tools` per the command-style convention, ref: Q3) + concise body covering the eight convention areas, each pointing to the relevant reference file by relative path (ref: Q2).
- `references/base-images.md` — minimal base selection, pinning to tags then digests, official/verified publishers.
- `references/multi-stage-and-caching.md` — multi-stage builds, named stages, layer ordering, `--mount=type=cache`, cache-bust ARG placement.
- `references/security.md` — non-root user, secrets at runtime and `--mount=type=secret`, cache/temp cleanup, scanning (Trivy/Grype/Snyk).
- `references/signals-and-healthchecks.md` — exec vs shell form, tini/dumb-init, STOPSIGNAL, HEALTHCHECK tuning, k8s-probe note.
- `references/dockerignore.md` — required entries, sensitive-file exclusions, sparing `!` exceptions.
- `references/languages.md` (or per-language files) — Go, Node.js, Python, Java, Rust patterns, each with one complete example Dockerfile.

No registry/manifest edit is required (ref: Q6). No existing skill or eval file is modified. Optionally, a small structural validation (frontmatter parses; body within budget; every referenced file exists; example Dockerfiles structurally valid) satisfies the project TDD directive, since the existing harness does not cover this skill type (ref: Q9, Q10).

## Pattern Decisions

### Decision 1: References layout — single file vs. one file per topic

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One `references/languages.md` + a few topic files | Fewer files; matches `qrspi-work`'s single-reference precedent | A combined languages file grows large; less granular load-on-demand |
| B | One reference file per convention area + per language | Granular load-on-demand; each file a single coherent topic (matches the discovered pattern) | More files to keep linked; slightly more linking boilerplate |

**Recommendation:** Option B
**Rationale:** Research found the established pattern is "each reference file is a single coherent topic; the body tells the agent precisely when to open it" (ref: Q8). Per-topic files keep the body lean and let the agent pull only the relevant language, directly serving the <500-line body target (ref: Q7).
**NEW PATTERN?** No — extends the existing `qrspi-work/references/` load-on-demand pattern (ref: Q1, Q8). It is, however, the first *multi-file* references directory in the repo.

### Decision 2: Frontmatter shape — command-style vs. minimal content-skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Minimal: `name` + `description` only | Smallest valid skill; matches agentskills.io's load-bearing fields (ref: Q3) | Diverges from the repo's command-style skills that all carry `command`/`argument-hint`/`allowed-tools` |
| B | Command-style: add `command`, `argument-hint`, `allowed-tools` | Consistent with the 10 existing skills' frontmatter | `command`/`argument-hint` imply a slash-invoked workflow; this skill is auto-triggered by description, so they may be noise |

**Recommendation:** Option A, with `allowed-tools` optional
**Rationale:** This is an auto-triggered advisory content skill, not a slash-command workflow phase. The load-bearing fields are `name` (kebab, == dir) and a trigger-rich `description` (ref: Q3, Q4). Adding `command`/`argument-hint` would imply an invocation contract the skill does not have. This is a deliberate, justified divergence from the qrspi command-style convention; flag it for human review in OQ2.
**NEW PATTERN?** Partial — first content (non-command) skill in this repo; still conforms to the skill frontmatter schema (ref: Q3).

### Decision 3: How "tested" is satisfied for a prose skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Manual structural checklist only | Zero new code; fast | Not repeatable; weak against the TDD directive |
| B | Small static validator (frontmatter parses, body ≤ budget, no dangling reference links, example Dockerfiles structurally valid via hadolint/docker if available) | Repeatable, mechanical, honors TDD; catches dangling links and oversize body | New script to maintain; depends on optional linters being present |

**Recommendation:** Option B (degrade gracefully if hadolint/docker absent)
**Rationale:** The existing harness gives no path for content skills (ref: Q9, Q10), and the project TDD directive requires verification. Static checks are the meaningful definition of "tested" for prose (ref: Q10). Where hadolint/docker is unavailable, fall back to structural parse of example blocks.
**NEW PATTERN?** Yes — no skill-validation tooling exists today (ref: Q7, Q9). Justified because no existing mechanism covers content skills.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Body exceeds 500-line/5000-token budget as conventions are added | med | med | Enforce the offload-to-references rule from the start; measure with `wc -l` / token estimate before commit; trim body to checklist + pointers |
| Example Dockerfiles contain subtle errors (won't build / insecure) presented as best practice | med | high | Validate each example with hadolint/`docker build --check` where available; keep examples minimal and structurally reviewed; cite the convention each line serves |
| Skill description triggers poorly (over- or under-fires) | med | med | Write a precise "Use when… / Do NOT use for…" description per the repo convention (ref: Q3); run the skill-creator trigger/variance eval loop (host-level) before finalizing (ref: Q5, Q12) |
| Divergence from command-style frontmatter confuses future maintainers | low | low | Document the rationale in design/structure; surface in OQ2 for human sign-off |
| Dangling reference links (body points to a file that doesn't exist or vice-versa) | med | med | Static validator checks bidirectional reference integrity (Decision 3, Option B) |

## Open Questions

- OQ1: Should the skill be built strictly via the host-level skill-creator skill (per ticket process step 1 and the global directive), with this QRSPI planning serving as the design input — or is a hand-authored skill acceptable if it passes the same structural/eval checks? The skill-creator is not in-repo (ref: Q5), so the planner cannot run it; confirm the intended build path.
- OQ2: Confirm the frontmatter shape (Decision 2): minimal `name` + `description` content-skill, or match the repo's command-style frontmatter for consistency?
- OQ3: Are hadolint and/or a Docker daemon available in the target environment for example validation, or should validation be purely structural/static (Decision 3)?
- OQ4: Should language references be one combined file or one file per language (Decision 1 settled on per-topic; confirm this matches reviewer preference given it introduces the first multi-file references dir)?
