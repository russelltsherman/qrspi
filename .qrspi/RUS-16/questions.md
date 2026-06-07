# Questions — Create a new agent skill using the kustomize CLI

**Ticket:** RUS-16
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the canonical on-disk directory structure for an agentskills.io-standard skill (the `SKILL.md` plus `references/`, `scripts/`, `assets/` layout), and where in this repo are skills expected to live?
  **Target:** the module/directory responsible for skill definitions (`.claude/skills/` and `.claude/agents/`)
- Q2: How does the Anthropic skill-builder skill ingest a specification and emit the generated skill files — what inputs does it read and what files does it produce on disk?
  **Target:** the skill-creator skill (`.claude/skills/skill-creator/` or its referenced builder)
- Q3: How are `references/` files referenced from a `SKILL.md` body so an agent loads them on demand rather than inline (the progressive-disclosure mechanism)?
  **Target:** the module responsible for skill reference loading / skill-creator documentation

## API Surface

- Q4: What frontmatter fields does a valid `SKILL.md` require (name, description, and any others), and what are the format constraints on each?
  **Target:** the skill-creator skill's SKILL.md authoring/validation rules
- Q5: What is the enforced size limit for a `SKILL.md` body, and how is the "under 500 lines / 5000 tokens" acceptance criterion measured or validated in this repo?
  **Target:** the skill-creator skill or any skill-size validation script

## State Management

- Q6: How is the `description` field used to trigger auto-invocation of a skill, and what wording patterns make a skill reliably trigger versus not (relevant to a kustomize-CLI skill being picked up)?
  **Target:** the skill-creator skill's description-optimization / triggering guidance
- Q7: Are example asset files (e.g., a sample `base/overlays/components` directory tree) stored under `assets/` and copied verbatim, or rendered/templated at skill-build time?
  **Target:** the module responsible for skill `assets/` handling

## Edge Cases

- Q8: How should the skill encode deprecation awareness (`vars` → `replacements`, `patchesStrategicMerge`/`patchesJson6902` → `patches:`) so an agent prefers the current field without breaking on repos still using the legacy fields?
  **Target:** the references content covering patch/transformer field selection
- Q9: How is a `secretGenerator` referencing uncommitted `.env` files represented in skill examples without leaking secrets or committing the `.env` files themselves into the repo?
  **Target:** the references content covering generator configuration patterns
- Q10: What does the skill prescribe when `commonLabels` would inject into a Deployment selector and break a rolling update — how is the transformer-vs-commonLabels decision boundary expressed?
  **Target:** the references content covering the transformer usage matrix
- Q11: How should the decision framework distinguish strategic merge patch from JSON 6902 patch for the ambiguous cases (removing a field, replacing an array item by index)?
  **Target:** the references content covering patch-type selection

## Testing

- Q12: How are skills validated or evaluated in this repo (does the skill-creator eval loop apply), and what constitutes a passing check for a newly authored skill?
  **Target:** the skill-creator eval harness / `evals/` + `scripts/run_eval.py`
- Q13: What CI validation patterns for kustomize output (`kustomize build` per overlay, `kubeconform`, `conftest`/OPA) should the references document, and is there an existing example pipeline format to mirror?
  **Target:** the references content covering CI validation pipeline examples

## Observability

- Q14: What signals should the skill instruct an agent to surface when `kustomize build` fails on an overlay (which directory, which resource, the build stderr) so failures are diagnosable in CI logs?
  **Target:** the references content covering CI validation / build-failure reporting
