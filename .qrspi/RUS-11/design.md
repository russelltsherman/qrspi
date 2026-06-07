# Design — Create a new agent skill using the devcontainer CLI

**Ticket:** RUS-11
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

This repo has no devcontainer skill, no `skill-creator` skill, and no in-repo copy of the agentskills.io / Anthropic skill-builder standard — those are global/plugin skills living outside the repo (ref: Q4). The repo's only authority on the skill standard is the convention encoded in its own ten `.claude/skills/qrspi-*/SKILL.md` files (ref: Q1).

The observed on-disk layout is one directory per skill at `.claude/skills/<name>/` containing a mandatory `SKILL.md`, with an optional `references/` subdirectory; of the ten skills only `qrspi-work` uses a subdirectory (`references/review-cascade.md`), and none use `scripts/` or `assets/`, so `references/` is the only one of the four with in-repo precedent (ref: Q1). The observed frontmatter is a `---`-delimited YAML block with five keys present in all ten skills — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — with `name` always lowercase kebab-case and exactly equal to the directory name (ref: Q3).

Reference files are surfaced by progressive disclosure: there is no in-repo loader (it lives in the external harness), but the working convention is to cite each `references/<file>.md` by relative path from the SKILL body at the exact decision point where it is needed, so the body stays small and the reference is pulled on demand (ref: Q2). An orphaned reference file that the body never names would never be surfaced (ref: Q2). The single in-repo precedent for splitting content is `qrspi-work`: control flow and dispatch tables stay in the body, while a bounded, self-contained decision document moved to `references/` and is cited at the one branch that needs it (ref: Q7).

There is no SKILL.md size-check tooling and no body-budget enforcement anywhere in the repo; the budget is cultural, by author discipline (ref: Q6). Notably the repo's one large skill, `qrspi-work/SKILL.md`, is 565 lines — already over the 500-line guideline the ticket cites — and nothing flags it (ref: Q6, ref: Q7). Likewise there is no in-repo frontmatter parser or validator; malformed or oversized skills surface only at load time in the live external harness (ref: Q12).

The dominant pattern is the thin wrapper: 8 of 10 skills are ~25-35 line shims whose body spawns a sibling agent in `.claude/agents/<name>.md` via the `Agent` tool, with all prompt content in the agent file (ref: Q5). Two skills (`qrspi-ticket`, `qrspi-work`) break this — they hold full logic in SKILL.md with no sibling agent — so the wrapper convention is real but not universal (ref: Q5). The `description` field uses a two-part "what it does + Use when…/Trigger on…" trigger pattern; no in-repo description uses negative "when NOT to use" phrasing, so scoping is achieved by specificity of positive triggers, not exclusion clauses (ref: Q8). `allowed-tools` is the per-skill tool-lockdown mechanism, enforced in frontmatter rather than code (ref: Q3).

Verification in this repo is via stdlib-only `scripts/qrspi_*_test.py` unit tests plus manual end-to-end runs; the `evals/` + `run_eval.py` + `grade.py` harness is a non-functional placeholder (stubbed agent execution, `llm_judge` not integrated, and several suite checks unregistered or comparison-dropping), so there is no functional runtime skill eval in this repo (ref: Q10, ref: Q11). The repo's own `.devcontainer/devcontainer.json` exists (93 lines) and is build-based and heavily hardened: `build.dockerfile` not `image`, `remoteUser: vscode`, no `features` block, lifecycle work delegated to scripts (`initializeCommand`, `postCreateCommand`, `postStartCommand`), seccomp/capAdd hardening, and a `protected-paths` mechanism (ref: Q9).

## Desired End State

A new content-bearing skill `devcontainer-cli` ships under `.claude/skills/devcontainer-cli/` with a valid `SKILL.md` and a populated `references/` directory. Each acceptance criterion maps to a concrete behavior:

- **agentskills.io directory structure with valid frontmatter** → directory `devcontainer-cli/` with `SKILL.md` whose YAML frontmatter carries the five repo-observed keys (`name: devcontainer-cli` matching the directory, `description`, `command`, `argument-hint`, `allowed-tools`) (ref: Q1, ref: Q3).
- **Built using the Anthropic skill builder skill** → authored by invoking the global `skill-creator` skill, which is out-of-repo and cannot be evidenced here; this is recorded as an Open Question because this design phase cannot verify the builder ran (ref: Q4).
- **Body under 500 lines / 5000 tokens** → SKILL.md body holds only concise guidance and opinionated defaults; all detailed material lives in `references/`. No automated check exists, so this is met by discipline and a manual `wc -l` (ref: Q6).
- **`references/` covering CLI command reference, devcontainer.json schema cheatsheet, lifecycle decision tree, CI/CD workflow examples** → four reference files, each cited by relative path from the body at its decision point (ref: Q2, ref: Q7).
- **All six lifecycle hooks with when-to-use guidance** → the lifecycle decision-tree reference enumerates `initializeCommand`, `onCreateCommand`, `updateContentCommand`, `postCreateCommand`, `postStartCommand`, `postAttachCommand` with selection guidance and the skip-on-failure rule (new content; no in-repo precedent covers all six — ref: Q9 shows the repo uses only three hooks).
- **Opinionated defaults (non-root user, lockfile committed, named volumes for deps)** → stated as defaults in the body, framed as the skill's recommendation for *general* projects, with an explicit note acknowledging this repo's own hardened build-based devcontainer is a deliberate exception so the advice does not appear to contradict the working example (ref: Q9).
- **Docker Compose multi-container patterns** → covered in the body and/or schema cheatsheet (`dockerComposeFile`, `service`, `workspaceFolder`, `shutdownAction`).
- **CI/CD GitHub Actions integration** → covered in the CI/CD workflow-examples reference (`devcontainers/ci` action, pre-build/push, `--cache-from`).
- **Troubleshooting top issues** → a troubleshooting section in the body covering permissions, cache invalidation, volume ownership, lifecycle failures, and slow builds.

## Delta

**New files:**
- `.claude/skills/devcontainer-cli/SKILL.md` — concise body: frontmatter, install + primary workflow, opinionated defaults, lifecycle summary, Compose summary, troubleshooting, and relative-path pointers into the four reference files.
- `.claude/skills/devcontainer-cli/references/cli-commands.md` — full `devcontainer` CLI command reference (`up`, `exec`, `build`, `read-configuration`, `run-user-commands`, `--workspace-folder`, `--frozen-lockfile`, `--remove-existing-container`).
- `.claude/skills/devcontainer-cli/references/devcontainer-json-schema.md` — schema cheatsheet (`image` vs `build`, `remoteUser`, `forwardPorts`, `customizations`, `mounts`, `features`, Compose keys, `shutdownAction`).
- `.claude/skills/devcontainer-cli/references/lifecycle-decision-tree.md` — all six hooks, execution order, object/parallel syntax, skip-on-failure + idempotency rule.
- `.claude/skills/devcontainer-cli/references/cicd-workflows.md` — `devcontainers/ci` GitHub Action usage, pre-build-and-push, registry cache, CI image reuse as the local `image`.

**No modifications** to existing files. No agent file is created (this is a content skill, not a thin wrapper — see Decision 2). No `scripts/` or `assets/` directories (no in-repo precedent and no ticket requirement) (ref: Q1). No size-check tooling is added (out of scope; none exists — ref: Q6).

## Pattern Decisions

### Decision 1: Frontmatter shape for the new skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Match the five-key repo convention exactly (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Consistent with all ten existing skills; `name`==dir invariant honored | Repo convention may diverge from the formal agentskills.io schema, which is not in-repo |
| B | Use whatever the global skill-creator emits, even if keys differ | Aligns with the "built by skill builder" criterion and the true standard | Risks frontmatter inconsistent with the repo's ten skills; unverifiable here |

**Recommendation:** Option A, reconciled with B at authoring time.
**Rationale:** The only in-repo authority is the five-key pattern shared by all ten skills with `name`==directory==command basename (ref: Q3, ref: Discovered Patterns). The implementer should still run skill-creator (criterion) and, if it emits a different shape, prefer the repo convention for the keys the repo uses while keeping any extra standard keys the builder adds.
**NEW PATTERN?** No — directly follows the observed frontmatter convention (ref: Q3).

### Decision 2: Content skill vs thin wrapper + agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained content skill (logic in SKILL.md + references), no agent | Matches `qrspi-ticket`/`qrspi-work` precedent for non-orchestration skills; this skill gives guidance, it does not spawn a phase agent | Deviates from the dominant thin-wrapper rule |
| B | Thin wrapper SKILL.md + sibling `.claude/agents/devcontainer-cli.md` | Follows the documented "wrappers in skills, logic in agents" rule | Wrapper pattern exists to spawn a phase *agent* that produces an artifact; this skill has no artifact and no agent to delegate to — an empty shim |

**Recommendation:** Option A.
**Rationale:** The thin-wrapper convention exists for phase agents that parse `$ARGUMENTS`, spawn a subagent, and verify an output artifact (ref: Q5). A guidance skill produces no artifact and has nothing to delegate, so it fits the `qrspi-ticket`/`qrspi-work` self-contained precedent (ref: Q5).
**NEW PATTERN?** No — `qrspi-ticket` and `qrspi-work` are existing self-contained skills (ref: Q5).

### Decision 3: Body/reference split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Concise body (defaults, workflow, troubleshooting) + four `references/*.md` cited by relative path at each decision point | Matches the `qrspi-work` progressive-disclosure precedent; satisfies the references criterion; keeps the body under budget | Requires discipline to keep each reference cited (orphans are dead) |
| B | Single large SKILL.md holding all CLI/schema/lifecycle/CI detail | Simpler authoring | Violates the `references/` criterion and risks exceeding the 500-line budget, as `qrspi-work` itself does at 565 lines |

**Recommendation:** Option A.
**Rationale:** The repo's one split precedent keeps control flow in the body and moves bounded lookup material to `references/`, cited by relative path where needed (ref: Q2, ref: Q7). The ticket explicitly mandates four reference files, so the split is required, not optional.
**NEW PATTERN?** No — follows the `qrspi-work` reference-splitting precedent (ref: Q7).

### Decision 4: Trigger scoping in the description

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Two-part description with specific positive "Use when…/Trigger on…" devcontainer phrases | Matches the repo's only scoping mechanism (positive specificity) | Cannot use a negative clause to fence off general Docker work — no in-repo precedent |
| B | Add an explicit "do NOT use for general Docker / Kubernetes / Codespaces" clause | Directly encodes the ticket's out-of-scope boundary | No in-repo description uses negative phrasing; behavior is unverifiable here |

**Recommendation:** Option A, with a short negative clause borrowed from the ticket's out-of-scope list as a low-risk addition.
**Rationale:** The established mechanism is specificity of positive triggers; there is no in-repo anti-trigger precedent (ref: Q8). Adding a brief negative clause is harmless and serves the ticket's scope guidance, but the primary scoping should be concrete devcontainer trigger phrases.
**NEW PATTERN?** Partial — the negative-clause portion is a new pattern; justified because the ticket explicitly requires fencing out general Docker work and no positive-only phrasing fully captures an exclusion (ref: Q8).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Opinionated defaults (prefer `image`, use `features`) contradict the repo's own build-based, hardened devcontainer, confusing readers | med | med | Frame defaults as general-project recommendations and add an explicit note that this repo's build-based hardened setup is a deliberate exception (ref: Q9) |
| SKILL.md body exceeds the 500-line / 5000-token budget with nothing in-repo to catch it | med | med | Push all detail into the four references; keep the body to workflow + defaults + troubleshooting + pointers; manual `wc -l` and token estimate before finishing (ref: Q6, ref: Q7) |
| A reference file is created but never cited from the body, so the harness never surfaces it (dead reference) | med | low | Cite every `references/<file>.md` by relative path at its decision point, as `qrspi-work` does (ref: Q2) |
| "Built using the skill builder" criterion is unverifiable in this repo (skill-creator is out of scope) | high | low | Implementer invokes the global `skill-creator` skill at authoring time; this design records it as an Open Question rather than asserting compliance (ref: Q4) |
| Frontmatter shape assumed from repo convention diverges from the true agentskills.io schema | low | med | Reconcile repo five-key convention with whatever skill-creator emits; keep `name`==directory invariant (ref: Q3) |

## Open Questions

- OQ1: The "Built using the Anthropic skill builder skill" criterion requires the global `skill-creator` skill, which is outside this repo and not evidenced here (ref: Q4). Should the implementer run skill-creator and, if its output frontmatter differs from the repo's five-key convention, which one wins?
- OQ2: Should the skill's opinionated defaults reflect the general agentskills.io guidance (prefer `image`, use `features`, named volumes) even though this repo's own devcontainer deliberately does the opposite (build-based, no features, hardened)? How prominent should the "this repo is an exception" caveat be (ref: Q9)?
- OQ3: Is `argument-hint` meaningful for a guidance skill that takes no positional ticket argument, and if not, what placeholder value should it carry to satisfy the five-key convention (ref: Q3)?
- OQ4: Is verifying acceptance criteria via manual review (sections present, six hooks covered, `wc -l`) acceptable, given the eval harness is a non-functional placeholder and there is no SKILL.md validator (ref: Q6, ref: Q10, ref: Q12)?
