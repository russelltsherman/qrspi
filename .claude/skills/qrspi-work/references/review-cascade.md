# Review Cascade Logic

When planning review feedback requires changes to an artifact, downstream artifacts
may be invalidated. The planning artifacts form a dependency chain:

```
Questions → Research → Design → Structure → Plan → Work Tree
└────────── design half ──────┘└──────── plan half ────────┘
```

## Two gates, two cascade scopes

Planning has two human review gates. Which artifacts exist — and therefore how far a
cascade can reach — depends on which gate the feedback came from:

- **Design Review** (after the design half): only Questions, Research, and Design exist.
  Cascade is bounded to those three. There is no Structure/Plan/Work Tree to re-run yet,
  so a design-decision change here simply lands in `design.md` and is carried into the
  plan half when the ticket reaches `Design Approved`.
- **Plan Review** (after the plan half): all six artifacts exist. The full cascade below
  applies.

## Cascade Rules

### Identify the earliest affected artifact

Map each review comment to the artifact it targets. If a comment affects multiple
artifacts, use the earliest one in the chain.

### Determine cascade depth

Not every change cascades. Use judgment:

| Change type | Cascade? |
|---|---|
| Typo, wording fix, clarification | No cascade — fix only the targeted artifact |
| New question added to questions.md | Re-run Research (it needs to answer the new question), then re-evaluate Design through Work Tree |
| Research finding corrected or added | Re-evaluate Design (its citations may change), then downstream if Design changes |
| Design decision changed | Re-run Structure (slice boundaries may shift), Plan, Work Tree |
| Design risk added but decision unchanged | No cascade — add to risk register only |
| Structure slice split or merged | Re-run Plan (step counts change), Work Tree (sessions change) |
| Structure contract changed | Re-run Plan (step details change), Work Tree |
| Plan step modified | Re-evaluate Work Tree (session boundaries may shift) |
| Work Tree session boundary moved | No cascade — it's the last artifact |

### Re-running a downstream phase

When re-running a downstream phase, spawn a sub-agent with the same instructions
as the original phase, but provide the UPDATED upstream artifacts. The sub-agent
produces a fresh version of the artifact.

Do not try to patch a downstream artifact manually. Regenerating it ensures
consistency with the updated upstream.

### Commit strategy

After addressing all feedback and cascading:
1. All updated artifacts are on disk.
2. Make a single commit with all changes:
   ```
   <ticket-id>: Address planning review feedback
   ```
3. Push and update the PR.

### Example

Reviewer says: "The design should use event sourcing instead of CRUD for the audit log."

1. Affected artifact: `design.md` (Pattern Decisions section)
2. Update `design.md` — change the pattern decision
3. Cascade: Design decision changed → re-run Structure
4. Spawn sub-agent to regenerate `structure.md` from updated `design.md`
5. If slice boundaries changed → re-run Plan
6. Spawn sub-agent to regenerate `plan.md` from updated `structure.md`
7. Re-run Work Tree from updated `plan.md`
8. Commit all four updated files
