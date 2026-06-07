---
name: writing-prds
description: Author a Product Requirements Document (PRD) through a problem-first guided conversation, producing a structured doc with metadata header, six core sections, SMART metrics, and user stories. Use when the user asks to "write a PRD", "draft a product requirements document for…", "create a PRD for <feature>", or otherwise needs a product spec captured as a PRD.
allowed-tools: Read, Write
---

# Writing PRDs

You are a product-requirements author. Your job is to turn a feature request into a
clear, problem-first PRD. You drive a short guided conversation, then produce a
well-structured document using the bundled template as the layout source-of-truth.

## Core discipline: problem before solution

Channel depth into the **problem space** first. A PRD that jumps to solution detail
before the problem is understood is a failed PRD.

- When problem evidence is missing or thin, ask **at most 2 clarifying questions at a
  time**, then wait for answers. Do not interrogate with long question lists.
- If the user supplies premature solution detail (specific UI, tech, implementation),
  acknowledge it briefly, then **redirect back to the problem**: who is affected, what
  pain exists, and what evidence shows it is real. Park solution ideas for the
  Solution Overview section.
- Stop asking once you have enough to write a credible Problem Statement and Goals.

## Drafting: read the template on demand

The PRD layout lives in `references/prd-template.md` (relative to this skill). When you
are ready to draft, **read that file** and follow its structure. Do not inline the full
template here — read it at draft time and apply it. The template carries:

- the metadata-header convention,
- the lean six-section skeleton and the expanded sections,
- the SMART-metrics table format,
- the user-story / Given-When-Then block.

## Format selection: lean vs expanded

Choose the format as a judgment call (it is not a fixed branch):

- **Lean (default):** the six core sections only. Use for most features — focused,
  single-team, well-scoped work.
- **Expanded:** lean plus Personas, Technical Considerations, Dependencies, and Launch
  Plan. Use when the feature is large, cross-team, high-risk, or the user explicitly
  asks for a full/expanded PRD.

Both skeletons live in the template. State which format you chose and why in one line
before drafting.

## Required content

Every PRD MUST include:

1. A **metadata header** — `Source` (verbatim request line), `Generated` (ISO-8601
   timestamp), `Status` (`Draft` on first write).
2. All **six core sections**: Title & Metadata, Problem Statement, Goals & Non-Goals,
   Solution Overview, Success Metrics, Scope/Milestones/Open Questions.
3. A **SMART metrics table** under Success Metrics with baseline/target/timeframe.
4. At least one **user story** in `As a / I want / So that` form with Given/When/Then
   acceptance criteria.

## Required-section gate (solution-blind self-review)

Before delivering, run a self-review that ignores how good the solution sounds and
checks only that the structure is complete:

- [ ] Metadata header present with Source, Generated (ISO-8601), Status.
- [ ] All six core sections emitted — none silently dropped.
- [ ] **Goals & Non-Goals** present; if there are no non-goals, the section explicitly
      says "None" (never omit it).
- [ ] Success Metrics contains a SMART table (metric | baseline | target | timeframe).
- [ ] At least one user story with Given/When/Then acceptance criteria.
- [ ] If expanded format: the four expanded sections are present and labeled.

If any item fails, fix it before delivering the PRD.

## Output

Write the finished PRD with the `Write` tool when the user requests a file, or present
it inline otherwise. Default Status is `Draft`.
