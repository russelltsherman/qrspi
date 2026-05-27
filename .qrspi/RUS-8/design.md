# Design — Create a new agent skill called using argocd cli

**Ticket:** RUS-8
**Research basis:** research.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## Current State

The codebase has no existing Argo CD skill. The only skills that reference Argo CD concepts indirectly are the QRSPI workflow skills (qrspi-work, qrspi-implement, etc.) which assume the existence of external skills for infrastructure operations (ref: Q13). The project uses the `.claude/skills/<name>/` directory pattern with a SKILL.md frontmatter section (name, description, command, argument-hint, allowed-tools) followed by the skill body. External skills like `using-graphite-cli` exist outside the repo.

The `argocd` CLI supports multiple output formats per subcommand (json, yaml, wide, tree), all rendered through a shared `PrintResource()` function in common.go (ref: Q1). Global options are injected via the `ARGOCD_OPTS` environment variable through a persistent flag inheritance chain on the root command (ref: Q2). All state (contexts, servers, tokens, certificates) is persisted in `~/.config/argocd/argocd.yaml` using a LocalConfig struct (ref: Q6).

Most `argocd` subcommands are fully flag-driven with no interactive prompts, making them suitable for agent automation. The exceptions are `login` and `account delete-token`, which require pre-supplied credentials or confirmation (ref: Q5). Tokens are opaque JWT strings generated server-side; project-scoped permissions are enforced server-side, not at the CLI level (ref: Q7). The CLI uses optimistic locking with 10 retry attempts for concurrent application modifications (ref: Q12).

## Desired End State

The `using-argocd-cli` skill will be created at `.claude/skills/using-argocd-cli/` following the agentskills.io pattern:

1. SKILL.md with valid frontmatter (name, description, command, argument-hint, allowed-tools) encoding the full Argo CD CLI operational guidance
2. A references/ directory containing detailed reference material organized by topic
3. The skill covers the full application lifecycle: create, sync, monitor, rollback, delete (ref: Q1-Q5)
4. Opinionated defaults encoded in the skill body: declarative manifests for production, manual sync, Git reverts over rollbacks, ApplicationSets at scale
5. Separate guidance sections for interactive developer use and CI/CD automation contexts (ref: Q2, Q5, Q7)
6. Clear escalation path: simple flags -> ARG ODC_OPTS -> context switching -> project configuration (ref: Q6, Q7, Q14)

Acceptance criteria mapping:
- Follows agentskills.io directory structure with valid SKILL.md frontmatter: directory at `.claude/skills/using-argocd-cli/` with SKILL.md frontmatter matching the pattern used by existing skills (qrspi-work, qrspi-implement)
- Built using the Anthropic skill builder skill: implementation proceeds through the skill-creator skill eval loop
- SKILL.md body under 500 lines / 5000 tokens: the frontmatter is 7 lines; the body covers activation, role, workflow, quick reference, operational sections, and safety
- Detailed reference material in references/ directory: separate files for CLI reference, sync model, auth/RBAC, troubleshooting
- Covers full application lifecycle (create, sync, monitor, rollback, delete): each lifecycle phase is a dedicated section with specific commands and flags
- Encodes opinionated defaults: declarative manifests, manual sync, git-revert-over-rollback, ApplicationSets-at-scale, deny-all-RBAC
- Includes guidance for both interactive and CI/CD contexts: separate subsections for each mode within operational sections
- Clear escalation path: progressive complexity from single-app commands to ApplicationSets to project-level configuration

## Delta

**New files:**
- `.claude/skills/using-argocd-cli/SKILL.md` — Main skill file (target ~200 lines, max 500)
- `.claude/skills/using-argocd-cli/references/cli-output.md` — Output format reference for all subcommands
- `.claude/skills/using-argocd-cli/references/sync-model.md` — Sync waves, resource hooks, phases
- `.claude/skills/using-argocd-cli/references/auth-rbac.md` — Authentication, tokens, RBAC, projects
- `.claude/skills/using-argocd-cli/references/troubleshooting.md` — Diagnostic commands and error patterns

**Modified files:**
- `.claude/CLAUDE.md` — Add `using-argocd-cli` to the available skills list

**No modified existing code:** This skill is a documentation-only prompt artifact. It does not modify any application code, configuration files, or build artifacts.

**No new DB queries or middleware:** Not applicable — this is a skill definition, not an application feature.

## Pattern Decisions

### Decision 1: Skill directory structure and reference organization

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Monolithic SKILL.md (~400 lines) with no references | Simple, single file, agent reads everything at activation | Exceeds recommended SKILL.md length; hard to maintain; slow context load |
| B | Compact SKILL.md (~150 lines) with references/ subdirectory | Matches existing pattern (qrspi-work/references/); SKILL.md stays under 500 lines; references are loaded on demand | Slightly more files to manage |

**Recommendation:** Option B
**Rationale:** The existing codebase pattern uses `references/` subdirectories (qrspi-work/references/review-cascade.md). The acceptance criteria explicitly require "detailed reference material in references/ directory." The agentskills.io standard favors compact SKILL.md bodies with reference material in subdirectories.
**NEW PATTERN?** No — follows the existing qrspi-work/references/ pattern.

### Decision 2: allowed-tools configuration

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | No allowed-tools (open access to all tools) | Flexible, agent can use any tool needed for CLI automation | Less restrictive; violates principle of least privilege |
| B | Restrictive allowed-tools: Read, Write, Edit, Bash, Glob, Grep | Follows the principle that skills should declare their tool needs; matches existing skill patterns (qrspi-work declares 6 tools) | Requires careful review of which tools the skill actually needs |
| C | Add mcp tools for Argo CD server API | Could enable server-side operations beyond CLI | Out of scope — ticket explicitly excludes K8s resource authoring and server installation |

**Recommendation:** Option B
**Rationale:** All existing skills in the repo declare their allowed-tools explicitly (qrspi-work uses 6 tools, qrspi-implement uses 4). The skill performs CLI operations via Bash and reads/writes documentation files. The accepted tools are Read, Write, Edit, Bash, Glob, Grep. MCP tools are unnecessary since the skill operates through the `argocd` CLI, not a custom MCP server.
**NEW PATTERN?** No — follows the allowed-tools pattern from all existing skills.

### Decision 3: Authentication guidance encoding

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Token-based via ARGOCD_AUTH_TOKEN only | Simple, single canonical path, stateless, no local file I/O | Misses interactive developer use case where `argocd login` is preferred |
| B | Two-mode guidance: tokenless (CI/CD) and token-based (interactive) | Covers both contexts required by acceptance criteria; reflects the research findings about ARGOCD_OPTS and context management | More complex skill; requires clear mode separation to avoid confusion |
| C | Default to interactive login, document token as advanced | Matches typical developer workflow; tokens treated as special case | CI/CD mode is the harder use case and should be the default for agent skills |

**Recommendation:** Option B
**Rationale:** The research shows that CI/CD pipelines should use project-scoped role tokens (ref: Q7) while interactive use supports `argocd login` + context switching (ref: Q5, Q6). The ticket explicitly requires guidance for both interactive developer use and CI/CD automation contexts. Tokenless mode uses `ARGOCD_AUTH_TOKEN` env var (no file I/O, no local config). Interactive mode uses `argocd login` and `argocd context`.
**NEW PATTERN?** No — multi-mode guidance pattern exists in the QRSPI workflow skills (e.g., qrspi-work handles both new tickets and resumed tickets).

### Decision 4: Sync strategy default encoding

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Manual sync is default, automated sync documented as opt-in | Safe default for production; aligns with ticket opinionated defaults | Must ensure automated sync section is prominent for teams that want it |
| B | Automated sync with self-heal is default | Modern GitOps recommendation; reduces manual intervention | Riskier default; could cause unexpected resource pruning in production |
| C | Environment-dependent default (dev=auto, prod=manual) | Most nuanced; best fit for each context | Adds conditional logic that makes the skill harder to follow |

**Recommendation:** Option A
**Rationale:** The ticket specifies "Default to manual sync for production; automated sync only for non-critical." Manual sync is the safer default. The sync model research shows phase-waves ordering and resource hooks as ordering mechanisms (ref: Q4), which are independent of sync strategy choice and should be documented regardless.
**NEW PATTERN?** No — opinionated defaults are a standard pattern (see qrspi-work's worktree path convention).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds 500 lines during implementation | medium | high — fails acceptance criteria | Enforce line count gate during review. References directory absorbs detailed material. Use the skill-creator eval loop to measure tokens/lines. |
| Agent applies `--force` flag inappropriately | medium | high — can overwrite live cluster state, conflict with self-heal | Explicit safety section with RED WARNING markers. Document `--force` only as last resort. Require dry-run (`--dry-run`) before force operations. |
| Token leakage in logs or environment | low | high — JWT tokens grant full or project-scoped access | Document `ARGOCD_AUTH_TOKEN` masking in CI. Recommend project-scoped tokens (ref: Q7). Warn against plaintext config file storage. |
| Skill drift as Argo CD CLI evolves | low | medium — commands or flags may change between versions | Reference specific Argo CD version in skill metadata. Document that `--help` output should be validated before use. Add version caveat to SKILL.md. |
| ApplicationSets complexity overwhelms junior agents | medium | low — creates incorrect multi-cluster deployments | Gate ApplicationSets behind explicit mention. Put ApplicationSets in references, not in main workflow. Provide simple app-of-apps as fallback. |
| Context switching confusion when managing multiple clusters | low | medium — agent targets wrong cluster for operations | Make context management section early in skill. Show `argocd context` list before any cluster-specific operation. |

## Open Questions

- OQ1: What is the minimum Argo CD server version this skill should support? The CLI version and server version have specific compatibility matrices. Should the skill include a `argocd version` check as a first-step diagnostic?
- OQ2: Should the skill include SSO login guidance? The research shows `argocd login` has no `--yes` flag to bypass TLS prompts (ref: Q5), but SSO mode may avoid interactive prompts entirely. The decision affects CI/CD automation paths.
- OQ3: What is the expected skill activation pattern? Should it activate on any mention of "Argo CD", "argocd", "sync", or "deploy", or should it use a more specific trigger like `/argocd`? The command field in the frontmatter is currently empty.
- OQ4: Should the skill support Argo CD Rollouts (progressive delivery) commands (`argocd rollouts ...`), or is that explicitly out of scope? The ticket says out of scope is "CI pipeline config" but doesn't mention Rollouts.
- OQ5: What is the target audience density — how many agents will use this skill concurrently? The research shows optimistic locking with 10 retries for conflicts (ref: Q12), but the skill should communicate expected retry behavior to agents.
