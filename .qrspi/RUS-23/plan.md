# Implementation Plan — Create a new agent skill using the Crossplane CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

> Note: This is a single-slice, documentation/skill-authoring ticket — no runtime
> code, no DB, no config changes (ref: structure §Modified Types "None"). "Tests"
> are reviewer-gate verifications, not executable unit tests, because no in-repo
> tooling validates skill frontmatter, body size, or trigger accuracy (ref: design
> Risk Register). Steps 1–3 resolve the three blocking Open Questions before any
> file is authored, since every file path is templated on the resolved `<name>`.

## Slice 1: Author the `using-crossplane-cli` skill (SKILL.md + references/)

### Setup

1. Resolve OQ1 — choose the skill `<name>`: lowercase kebab-case, non-`qrspi-`
   prefixed, where dirname == frontmatter `name` == `command` minus leading `/`
   (ref: structure Contracts "Frontmatter field set"; design OQ1). Default to the
   design's suggestion `using-crossplane-cli` unless the author overrides. This
   value is substituted for `<name>` in every path below.
2. Resolve OQ3 — decide whether `SKILL.md` carries `argument-hint`: this is a
   reference/guidance skill, not an argument-taking command, so follow the
   `qrspi-ticket` exception and OMIT `argument-hint` unless the author decides
   otherwise (ref: structure verification "argument-hint inclusion decided"; design OQ3).
   The decision must be applied consistently in step 5.
3. Resolve OQ2/OQ4 — confirm the `skill-creator` invocation path: per the memory
   directive, the skill MUST be authored via the global `skill-creator` skill
   (never an ad-hoc `SKILL.md`). Record the exact invocation used; treat
   `skill-creator` as a black box and verify only its output against the
   conventions below (ref: structure verification 2 & 10; design Risk Register, OQ2/OQ4).

### Core Logic

4. ✨ Invoke `skill-creator` to scaffold `.claude/skills/<name>/` — produces the
   directory plus an initial `SKILL.md`; this is the authoring entry point for all
   files in steps 5–9 (ref: structure Slice 1 "authored in one skill-creator session").
5. ✨ Create `.claude/skills/<name>/SKILL.md` — entry-point frontmatter +
   lean body. Frontmatter is first-line `---` YAML carrying exactly `name`,
   `description`, `command` (= `/<name>`), `allowed-tools`, and `argument-hint`
   per step 2's decision (Frontmatter field-set contract; `SkillFrontmatter` type,
   structure §New Types). `description` follows the "<what it does>. Use when…"
   form within 74–489 chars (Description trigger pattern). Body covers provider
   lifecycle, composition, XRD/claims, managed resources, packaging,
   troubleshooting escalation, kubectl/GitOps, env config — each section ending in
   a backticked relative-path pointer to its reference file (Reference link idiom).
6. ⚠️ Edit `.claude/skills/<name>/SKILL.md` — add v1/v2 version-branching prose.
   - **Current:** body sections present, no software-version guidance.
   - **After:** version guidance written as imperative `if v1 … otherwise v2 …`
     prose defaulting to v2 unless the installed version indicates v1
     (Version-branching idiom; design Decision 3).
7. ⚠️ Edit `.claude/skills/<name>/SKILL.md` — add the troubleshooting escalation
   sequence.
   - **Current:** troubleshooting section points to reference file only.
   - **After:** an ordered `trace → describe → events → logs` sequence appears
     inline in `SKILL.md` (Troubleshooting escalation order contract), expanded in
     step 12's reference file.
8. ✨ Create `.claude/skills/<name>/references/cli-reference.md` — full
   `crossplane xpkg build/push/login/validate`, `render`, and `trace` command/flag
   reference; defer CLI flags to official Crossplane docs as canonical
   (Canonical-source pointer; structure Slice 1, file 2).
9. ✨ Create `.claude/skills/<name>/references/composition-patterns.md` —
   Pipeline-mode compositions, `function-patch-and-transform`, EnvironmentConfig
   usage, `crossplane render` validation (structure Slice 1, file 3).
10. ✨ Create `.claude/skills/<name>/references/xrd-schemas.md` — XRD schema
    templates, v1 cluster-scoped + Claims vs v2 `scope: Namespaced` XRs,
    connectionSecretKeys, versioning/conversion (structure Slice 1, file 4).
11. ✨ Create `.claude/skills/<name>/references/troubleshooting.md` —
    trace → describe → events → logs decision tree, condition checks
    (ReconcileError, Ready, Synced, Responsive), `xpkg validate`
    (structure Slice 1, file 5).

### Tests (reviewer-gate verifications — no executable in-repo validator)

12. Run: `ls .claude/skills/<name>/SKILL.md .claude/skills/<name>/references/cli-reference.md .claude/skills/<name>/references/composition-patterns.md .claude/skills/<name>/references/xrd-schemas.md .claude/skills/<name>/references/troubleshooting.md`
    - **Expected:** all five files exist (`SkillDirectory` shape, structure §New Types); no dangling reference pointer.
13. Run: `head -n 1 .claude/skills/<name>/SKILL.md && grep -nE '^(name|description|command|allowed-tools|argument-hint):' .claude/skills/<name>/SKILL.md`
    - **Expected:** first line is `---`; the printed field set matches the step-2 decision and diffs clean against a known-good existing skill's frontmatter (Frontmatter field-set contract).

### Verify Slice 1

14. **Checkpoint:** `awk 'NR<=1 && $0!="---"{print "FAIL: frontmatter"; exit 1} END{print NR" lines"}' .claude/skills/<name>/SKILL.md && grep -c 'references/' .claude/skills/<name>/SKILL.md`
    - [ ] `<name>` resolved (OQ1): lowercase kebab-case, non-`qrspi-`; dirname == frontmatter `name` == `command` slug.
    - [ ] Skill authored via `skill-creator` (memory directive); exact invocation recorded (OQ2/OQ4).
    - [ ] `SKILL.md` frontmatter is first-line `---` YAML; field set diffs clean against a known-good skill.
    - [ ] `argument-hint` inclusion decided (OQ3) and applied consistently.
    - [ ] `SKILL.md` body under 500 lines / 5000 tokens (manual count — no tooling enforces this; reviewer gate).
    - [ ] All four `references/*.md` linked from `SKILL.md` by backticked relative path; each linked file exists (no dangling pointer).
    - [ ] v1/v2 guidance present as `if v1 … otherwise v2 …` prose defaulting to v2 (Version-branching idiom).
    - [ ] Troubleshooting escalation appears as an ordered `trace → describe → events → logs` sequence in `SKILL.md`, expanded in `references/troubleshooting.md`.
    - [ ] `description` follows the "<what it does>. Use when…" pattern (Description trigger pattern).
    - [ ] CLI flags / API specs in references point to official Crossplane docs as canonical (Canonical-source pointer).
    - [ ] `skill-creator` eval loop run if available; otherwise record that no in-repo trigger-accuracy harness exists (Risk Register) and rely on the reviewer checklist above.

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this slice.
- Steps 4–11 only create new files under a new directory `.claude/skills/<name>/`.
  Rollback = delete the directory: `rm -rf .claude/skills/<name>/`. No existing
  skills, agents, scripts, templates, or config are modified (ref: structure
  §Modified Types "None"), so removal is fully reversible with no side effects.
