# Design — Create a new agent skill for the kustomize CLI

**Ticket:** RUS-16
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Skills in this repo live under `.claude/skills/<skill-name>/`, each containing exactly one entry file `SKILL.md`; the skill→agent split (thin wrapper in `.claude/skills/`, heavy body in `.claude/agents/`) is the documented house convention (ref: Q1). Of the 10 in-repo skills, only `qrspi-work` carries a `references/` subdirectory (a single file, `review-cascade.md`); no skill anywhere uses a `scripts/` or `assets/` subdirectory (ref: Q1, ref: Q7). The progressive-disclosure mechanism is convention-only: a `SKILL.md` body names a sibling file by relative path in prose (e.g. "see `references/review-cascade.md`") and the agent opens it on demand — there is no in-repo loader or validator that parses or verifies those links (ref: Q3).

All 10 `SKILL.md` files share an identical five-field YAML frontmatter set delimited by `---` lines: `name`, `description`, `command`, `argument-hint`, `allowed-tools`; `name` equals the directory name and `command` is `/<name>` (ref: Q4). The `description` carries auto-invocation triggering text; the strongest in-repo example (`qrspi-work`) pairs a capability summary with an explicit "Use when…/Trigger on…" clause and literal example phrasings (ref: Q6). No in-repo mechanism enforces any `SKILL.md` size limit — the only `line_count` gate (`scripts/grade.py`) targets QRSPI artifacts like `design.md <= 300`, and `qrspi-work/SKILL.md` is already 565 lines with nothing flagging it (ref: Q5).

The Anthropic `skill-creator`/`skill-builder` skill is a **global plugin skill with no files under the repo root**, so its ingestion/emission behavior, frontmatter spec, size enforcement, and eval loop are outside project scope and unmappable from the codebase (ref: Q2, ref: Q4, ref: Q5, ref: Q12). There is **zero kustomize content anywhere in the repo** — patch-type, generator, transformer, component, CI, and build-failure questions all resolve to NOT FOUND / outside scope (ref: Q8, ref: Q9, ref: Q10, ref: Q11, ref: Q13, ref: Q14). The repo's eval harness (`evals/suite.json` + `scripts/run_eval.py` + `scripts/grade.py`) is a documented non-functional placeholder whose `execute_single()` is an explicit stub, and every eval case targets a QRSPI phase — there is no eval case or grading support for a generic new skill (ref: Q12). Two repo precedents the kustomize content will mirror: secret-bearing config is handled by gitignoring the real file and committing a `*.example` sibling (`.qrspi/config.json` ↔ `.qrspi/config.example.json`) (ref: Q9), and the repo-wide failure doctrine is "print the exact failing command + full stderr verbatim, then stop" (ref: Q14).

## Desired End State

A new skill `kustomize-cli` ships under `.claude/skills/kustomize-cli/` with a valid `SKILL.md` and a populated `references/` directory. Each acceptance criterion maps to concrete behavior:

- **agentskills.io directory structure + valid frontmatter** → `.claude/skills/kustomize-cli/SKILL.md` with the repo's five-field frontmatter (`name: kustomize-cli`, triggering `description`, `command: /kustomize-cli`, `argument-hint`, `allowed-tools`), plus a `references/` subdirectory (ref: Q1, ref: Q4).
- **Built using the Anthropic skill builder skill** → authored by invoking the global `skill-creator` skill (its eval loop is out of scope per research; see Open Questions) (ref: Q2, ref: Q12).
- **SKILL.md body under 500 lines / 5000 tokens** → body kept lean by pushing detail into `references/`; no automated gate exists, so this is enforced by author discipline and a manual `wc -l`/token check (ref: Q5).
- **Reference material in `references/`** → four files: patch-type selection guide, generator configuration patterns, transformer usage matrix, CI validation pipeline examples (ref: Q3).
- **Example directory tree (base/overlay/component)** → a canonical tree shown in `SKILL.md` (or a `references/` file), as inline prose-rendered text rather than a bundled `assets/` tree, since the repo has no `assets/` precedent (ref: Q7).
- **Covers all resource types (patches, generators, transformers, components, replacements)** → each gets a `SKILL.md` section linking to its reference file.
- **Strategic-merge vs JSON-patch decision framework** → the patch-type selection reference encodes the additive→strategic / remove-field-or-array-by-index→JSON-6902 rule (ref: Q11).
- **kubectl apply -k AND GitOps integration** → an integration section covering `kubectl apply -k`, `kustomize build | kubectl apply -f -`, and Argo CD / Flux pointing at the overlay directory (ref: Q13).
- **Deprecation awareness (vars→replacements, patchesStrategicMerge→patches)** → encoded as "prefer current field, recognize legacy" guidance in the patch and transformer references (ref: Q8).

## Delta

**New files (all under `.claude/skills/kustomize-cli/`):**

- `SKILL.md` — thin, lean body: scope guidance, base/overlay/components conventions, the example directory tree, one short section per resource type, the deprecation table, and "see `references/…`" pointers (relative-path progressive disclosure per the `qrspi-work` precedent, ref: Q3).
- `references/patch-selection.md` — strategic-merge vs JSON 6902 decision framework, including ambiguous cases (remove field, replace array item by index) and the `patchesStrategicMerge`/`patchesJson6902` → `patches:` deprecation (ref: Q8, ref: Q11).
- `references/generators.md` — `configMapGenerator`/`secretGenerator` patterns, `behavior:`/`generatorOptions`, and `.env`-via-`*.example` handling mirroring the repo's gitignore precedent (ref: Q9).
- `references/transformers.md` — labels/annotations/namespace/images/namePrefix/replacements usage matrix, the `commonLabels`-breaks-selectors caution, and the `vars` → `replacements` deprecation (ref: Q8, ref: Q10).
- `references/ci-validation.md` — `kustomize build` per overlay, `kubeconform`/`conftest`/OPA, and the verbatim-error-on-failure reporting norm (ref: Q13, ref: Q14).

**No modifications** to existing files: there is no agent body (kustomize-cli is a self-contained skill, not a QRSPI phase), no eval-suite entry (the harness is an inert placeholder with no generic-skill support, ref: Q12), and no `.claude/agents/` companion. **No new scripts, no `assets/` directory** (no in-repo precedent, ref: Q7).

## Pattern Decisions

### Decision 1: Self-contained skill vs thin-wrapper + agent body

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained: all content in `SKILL.md` + `references/`, no `.claude/agents/` body | Matches `qrspi-work` precedent for a non-phase skill; nothing to spawn; simpler | Diverges from the 9 thin-wrapper QRSPI skills |
| B | Thin wrapper that spawns a `kustomize-cli` agent body in `.claude/agents/` | Matches the dominant QRSPI house split | The split exists to spawn fresh-context phase subagents; kustomize-cli is reference guidance, not an orchestrated phase — an empty agent indirection adds no value |

**Recommendation:** Option A
**Rationale:** The thin-wrapper/agent split serves QRSPI's fresh-context phase spawning; `qrspi-work` already establishes the self-contained pattern for a skill that is not a spawned phase (ref: Q1, Discovered Patterns). A kustomize guidance skill is read-and-apply, not orchestrated, so Option A fits the existing exception rather than inventing indirection.
**NEW PATTERN?** No — follows the `qrspi-work` self-contained precedent.

### Decision 2: Where the canonical base/overlay/component example tree lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline prose-rendered tree in `SKILL.md` | Zero new structure; immediately visible; matches research finding that the repo has no `assets/` (ref: Q7) | Adds lines to the body that counts against the 500-line budget |
| B | Bundled real files under `assets/base/`, `assets/overlays/…` | Copy-pasteable real manifests | No in-repo `assets/` precedent exists; introduces an unmodeled subdirectory convention (ref: Q7) |

**Recommendation:** Option A
**Rationale:** No skill in the repo uses `assets/`; the template-reading precedent treats scaffolding as "reference only — not written locally" (ref: Q7). An inline tree keeps the skill within established structure and the body lean if the tree is moved to a `references/` file when budget is tight.
**NEW PATTERN?** No (Option A). Option B would be a NEW PATTERN — flagged and not recommended.

### Decision 3: SKILL.md size control with no enforcing gate

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lean body + four `references/` files; manual `wc -l`/token check at author time | Honors the <500-line criterion; matches progressive-disclosure precedent (ref: Q3) | Relies on author discipline; no CI catches regressions |
| B | Put everything in `SKILL.md`, no `references/` | Single file | Violates the acceptance criterion requiring `references/`; risks the `qrspi-work` 565-line overrun (ref: Q5) |

**Recommendation:** Option A
**Rationale:** The acceptance criteria explicitly require a `references/` directory and a sub-500-line body; the repo has no size validator, so the only lever is structural offloading into references, exactly the progressive-disclosure convention the repo demonstrates once (ref: Q3, ref: Q5).
**NEW PATTERN?** No — extends the single existing `references/` example to a fuller four-file set.

### Decision 4: Representing secret-bearing `.env` in `secretGenerator` examples

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Reference an uncommitted `.env` + commit a `.env.example` sibling, mirroring `.qrspi/config.json` ↔ `.qrspi/config.example.json` | Reuses the established repo precedent (ref: Q9); no secret material | Examples are illustrative only, not runnable as-is |
| B | Inline literal secret values in the example | Self-contained example | Models a leak anti-pattern; contradicts the repo's gitignore-the-secret convention (ref: Q9) |

**Recommendation:** Option A
**Rationale:** The repo already codifies "gitignore the real secret-bearing file, commit a `*.example`" (ref: Q9); the generator reference should teach the same `.env` + `.env.example` shape, keeping the skill's guidance consistent with the host repo's own secret handling.
**NEW PATTERN?** No — directly mirrors the `config.example.json` precedent.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| kustomize reference content is entirely net-new (zero in-repo source, ref: Q13) — factual errors on deprecated fields / patch semantics could ship | med | high | Source field/version facts during authoring (Open Questions OQ1); keep deprecation guidance as "prefer X, recognize legacy Y" so legacy repos are not broken (ref: Q8) |
| SKILL.md silently exceeds 500 lines — no validator exists and `qrspi-work` already overran to 565 (ref: Q5) | med | med | Manual `wc -l` + token check before submit; offload aggressively into the four `references/` files (Decision 3) |
| "Built using the skill builder" acceptance criterion is unverifiable in-repo — skill-creator is out of scope and its eval loop does not apply here (ref: Q2, ref: Q12) | high | low | Invoke `skill-creator` during authoring and note it in the PR; do not attempt to add an eval-suite case (no generic-skill grading support exists, ref: Q12) |
| `references/` progressive disclosure is convention-only with no link validator (ref: Q3) — a mistyped relative path silently fails | low | med | Use exact `references/<file>.md` relative paths; manually confirm each linked file exists before submit |

## Open Questions

- OQ1: Which kustomize version/API levels should the skill target for its deprecation guidance (e.g. the exact release where `vars` and `patchesStrategicMerge` were deprecated)? Research confirms no in-repo source for this — a human must set the version baseline (ref: Q8, ref: Q13).
- OQ2: Should "Built using the Anthropic skill builder skill" be satisfied by invoking the global `skill-creator` during authoring only, or does the team expect a recorded eval artifact? The repo's eval harness is an inert placeholder with no generic-skill case, so there is no in-repo path to produce one (ref: Q12).
- OQ3: Is the canonical example tree acceptable as inline `SKILL.md` prose, or does the team want runnable `assets/` manifests despite there being no in-repo `assets/` precedent (ref: Q7)?
