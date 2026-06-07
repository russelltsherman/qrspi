# Structure Outline — Create a new agent skill using the Crossplane CLI

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This is a documentation/skill-authoring ticket, not a code change. There are
> no runtime types or function signatures. The "types" and "contracts" below are the
> structural conventions the artifacts must satisfy (frontmatter field set, link idiom,
> branching idiom) — these are the verifiable interfaces of a skill.

## New Types

- `SkillFrontmatter { name: kebab-case string, description: single-line string, command: "/" + name, argument-hint?: string, allowed-tools: string }`
  — YAML block delimited by `---` as the first content of `SKILL.md`; field set copied verbatim from an existing known-good skill (ref: design §Desired End State, Q3).
- `SkillDirectory { SKILL.md, references/cli-reference.md, references/composition-patterns.md, references/xrd-schemas.md, references/troubleshooting.md }`
  — the on-disk shape under `.claude/skills/<name>/` (ref: design §Delta).

## Modified Types

- None. The design's Delta states no existing skills, agents, scripts, templates, or config change (ref: design §Delta).

## Contracts

These are cross-file conventions every artifact in the slice must honor. They are
prose/structure conventions, not callable interfaces — no in-repo tooling validates them
(ref: design Risk Register), so each is a manual reviewer gate.

- **Frontmatter field set** — `SKILL.md` carries exactly `name`, `description`, `command`, `argument-hint` (OQ3 pending), `allowed-tools`; `name` == dirname == `command` minus leading `/` (ref: Q3, Q9).
- **Reference link idiom** — every `references/*.md` file is referenced from `SKILL.md` by a backticked relative-path prose pointer (e.g., "see `references/cli-reference.md`"); no include directive (ref: Q6).
- **Version-branching idiom** — v1/v2 guidance written as imperative `if v1 … otherwise v2 …` prose, defaulting to v2 unless installed version indicates v1 (ref: Q8, Decision 3).
- **Troubleshooting escalation order** — `trace → describe → events → logs` encoded as an ordered sequence in `SKILL.md`, detailed in `references/troubleshooting.md` (ref: design §Desired End State).
- **Canonical-source pointer** — CLI flags / API specs defer to official Crossplane docs rather than inlining volatile detail (ref: design §Desired End State).
- **Description trigger pattern** — `description` follows the "<what it does>. Use when/after <condition>." form within the 74–489 char observed range (ref: Q4).

## Slice 1: Author the `using-crossplane-cli` skill (SKILL.md + references/)

**Goal:** A complete, valid new skill directory exists end-to-end — frontmatter loads, the
body triggers and routes to four reference files, and the four reference files carry the
acceptance content. This is a single cohesive unit: the SKILL.md and the `references/`
files it directly links are a main file plus its support files (rule 8), authored in one
`skill-creator` session (5 new files, well under the 10-file limit).

**Files touched:**

- ✨ `.claude/skills/<name>/SKILL.md` — entry point: frontmatter (Frontmatter field-set contract) + lean body covering provider lifecycle, composition, XRD/claims, managed resources, packaging, troubleshooting escalation, kubectl/GitOps, env config; v1/v2 branching prose; each section pointing to a reference file (ref: design §Delta).
- ✨ `.claude/skills/<name>/references/cli-reference.md` — full `crossplane xpkg build/push/login/validate`, `render`, `trace` command/flag reference, deferring to official docs (ref: design §Delta).
- ✨ `.claude/skills/<name>/references/composition-patterns.md` — Pipeline-mode compositions, `function-patch-and-transform`, EnvironmentConfig, `crossplane render` validation (ref: design §Delta).
- ✨ `.claude/skills/<name>/references/xrd-schemas.md` — XRD schema templates, v1 cluster-scoped + Claims vs v2 `scope: Namespaced` XRs, connectionSecretKeys, versioning/conversion (ref: design §Delta).
- ✨ `.claude/skills/<name>/references/troubleshooting.md` — trace → describe → events → logs decision tree, condition checks (ReconcileError, Ready, Synced, Responsive), `xpkg validate` (ref: design §Delta).

**Verification:**

- [ ] `<name>` resolved (OQ1) as lowercase kebab-case, non-`qrspi-` prefixed; dirname == frontmatter `name` == `command` slug.
- [ ] Skill authored via the global `skill-creator` skill (per memory directive: never ship a SKILL.md ad-hoc); record the exact invocation used (resolves OQ2/OQ4).
- [ ] `SKILL.md` frontmatter is first-line `---` YAML and its field set diffs clean against a known-good existing skill (Frontmatter field-set contract).
- [ ] `argument-hint` inclusion decided (OQ3) and applied consistently.
- [ ] `SKILL.md` body is under 500 lines / 5000 tokens (manual count — no tooling enforces this; reviewer gate per Risk Register).
- [ ] All four `references/*.md` are linked from `SKILL.md` by backticked relative path (Reference link idiom); each linked file exists (no dangling pointer).
- [ ] v1/v2 guidance present as `if v1 … otherwise v2 …` prose defaulting to v2 (Version-branching idiom).
- [ ] Troubleshooting escalation appears as an ordered `trace → describe → events → logs` sequence in `SKILL.md` and is expanded in `references/troubleshooting.md`.
- [ ] `description` follows the "<what it does>. Use when…" pattern (Description trigger pattern).
- [ ] CLI flags / API specs in references point to official Crossplane docs as canonical (Canonical-source pointer).
- [ ] `skill-creator` eval loop (if available) run against the new skill; otherwise record that no in-repo trigger-accuracy harness exists (Risk Register) and rely on the reviewer checklist above.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

These are claims from design.md that cannot be mapped to a concrete in-repo type, file, or
interface and need human attention before planning.

- **`skill-creator` contract is a black box (OQ2, OQ4).** The exact invocation, inputs, output paths, and collision behavior of the global `skill-creator` skill are defined outside this repo (design Risk Register, Q2). The slice assumes "invoke skill-creator, then verify its output against the empirical conventions," but the actual interactive vs non-interactive entry point cannot be specified from the design alone.
- **Skill name `<name>` is undecided (OQ1).** The design suggests `using-crossplane-cli` but does not commit. Every file path in Slice 1 is templated on `<name>`; the name must be chosen before authoring so dirname == `name` == `command` slug stay consistent.
- **`argument-hint` inclusion is unresolved (OQ3).** 9/10 skills carry it; `qrspi-ticket` omits it. Whether this reference/guidance skill should include it is a judgment call left open by the design.
- **Body-size and trigger-accuracy are unverifiable by tooling (Risk Register, Q7, Q10–Q11).** The 500-line/5000-token limit and the description's trigger quality have no automated gate in-repo; both reduce to manual reviewer judgment, which the verification steps acknowledge but cannot mechanically confirm.
- **"Built using the Anthropic skill builder skill" acceptance has no in-repo validator (OQ4, Q5).** Whether invoking the global skill-creator is sufficient, or whether a recorded eval result is expected, cannot be resolved against repo artifacts.
