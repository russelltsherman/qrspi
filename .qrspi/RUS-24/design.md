# Design — Create a new agent skill called "using omlx cli"

**Ticket:** RUS-24
**Research basis:** research.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

The repo stores skills under `.claude/skills/<slug>/`, each with a `SKILL.md` at its root and optional `references/` subdirectory; no skill uses `scripts/` or `assets/` (ref: Q1). The only multi-file skill, `qrspi-work`, offloads one focused topic into `references/review-cascade.md` and pulls it in via an explicit in-body pointer rather than auto-loading (ref: Q2). Frontmatter convention is `name` (equal to the directory slug) plus a `description` that leads with a capability statement and includes a "Use when…" trigger clause; `command`/`argument-hint`/`allowed-tools` are optional Claude Code extensions (ref: Q3, ref: Q6). Naming follows a gerund "using-<tool>" slug, with directory name and `name` field always matching (ref: Q5). There is no repo-local SKILL.md size linter, no frontmatter validator, and no skill-authoring eval; the `evals/`+`scripts/` harness grades QRSPI phase outputs, not authored skills (ref: Q4, ref: Q7, ref: Q10, ref: Q11, ref: Q12). The `skill-creator`/"Anthropic skill builder" referenced by the ticket is a global, environment-provided skill and is NOT checked into this repo (ref: Q4). The qrspi phase skills are thin wrappers delegating to agents in `.claude/agents/`, an architecture that does NOT apply to a standalone tool-wrapper skill; the applicable model is the self-contained global `using-graphite-cli`/`writing-bash-scripts` style (ref: Discovered Patterns). Opinionated guidance in the repo is expressed via compact decision tables plus explicit forbidden/out-of-scope lists (ref: Q9). No in-repo skill gates on host platform/hardware, so the platform-precondition pattern is new for this skill (ref: Q8).

## Desired End State

A new self-contained skill at `.claude/skills/using-omlx-cli/` that guides agents managing local LLM inference via the `omlx` CLI on Apple Silicon. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io structure + valid frontmatter** → directory `using-omlx-cli/` with `SKILL.md` (valid `name: using-omlx-cli` + trigger-style `description`) and a `references/` subdirectory (ref: Q1, Q3, Q5).
- **Built using the skill builder** → authored following the global skill-creator conventions (capability+trigger description, lean body, references offload); builder is external to repo (ref: Q4, Q6).
- **Body under 500 lines / 5000 tokens** → SKILL.md stays lean; long detail pushed to `references/` (ref: Q2, Q7).
- **Detailed reference material in references/** → memory tiers, KV-cache tuning, full flag reference, API examples, MCP/agent launch, and troubleshooting live in `references/` files (ref: Q2).
- **Full server lifecycle (install, serve, configure, monitor, stop)** → covered in the SKILL.md body as the primary workflow.
- **Memory-tier-aware model size recommendations** → a decision table (16/24/32/64 GB tiers) plus the ~0.5 GB/B + 5-6 GB overhead rule; opinionated guard against oversized models (ref: Q9).
- **Two-tier KV cache config/tuning** → documented (hot unified-memory tier + cold SSD tier, `--paged-ssd-cache-dir`).
- **OpenAI-compatible API usage** → endpoint table and client-config guidance.
- **MCP integration + agent launch patterns** → `--mcp-config` and `omlx launch <agent>` documented.
- **Failure modes + troubleshooting** → Metal OOM crash loop, silent memory pressure, mixed-workload instability, model-not-showing, with the repo's "stop-and-report, don't chase destructive workarounds" value mirrored (ref: Q8, Discovered Patterns).
- **Opinion on oMLX vs Ollama vs LM Studio** → decision table + explicit out-of-scope list (ref: Q9).

## Delta

New files (all under `.claude/skills/using-omlx-cli/`):

- `SKILL.md` — frontmatter (`name`, `description`) + lean body: preconditions, install/setup, server lifecycle (serve/configure/monitor/stop), memory-tier model-size decision table, two-tier KV cache summary, API endpoint table, MCP/agent-launch summary, the oMLX-vs-Ollama-vs-LM-Studio decision table, an in-scope/out-of-scope list, a troubleshooting quick table, and explicit pointers to each `references/` file.
- `references/configuration.md` — full `omlx serve` flag reference, settings.json/env-var precedence, ports.
- `references/performance-tuning.md` — two-tier KV cache deep dive, continuous batching, TurboQuant KV, memory-planning math, full per-tier recommendations.
- `references/api-and-mcp.md` — OpenAI/Anthropic-compatible endpoint details, client config (LangChain/LlamaIndex/OpenAI SDK), function calling, `--mcp-config`, `omlx launch` agent matrix.
- `references/troubleshooting.md` — detailed failure modes, monitoring commands (`powermetrics`), recovery steps, production-hardening checklist.

No modifications to existing files. No DB/middleware changes (none exist; this is a docs/skill deliverable).

## Pattern Decisions

### Decision 1: Skill architecture — self-contained vs thin-wrapper

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained skill (full guidance in SKILL.md + references/), like global `using-graphite-cli` | Matches tool-wrapper precedent; no agent dependency; portable | Body must be disciplined to stay under size budget |
| B | Thin wrapper delegating to a `.claude/agents/` agent, like qrspi phase skills | Consistent with in-repo qrspi skills | Wrong fit — qrspi wrappers exist to orchestrate Linear/git phases, not document a CLI; adds needless indirection |

**Recommendation:** Option A
**Rationale:** Research shows the thin-wrapper idiom is QRSPI-internal orchestration architecture, while a standalone tool-guidance skill maps to the global `using-graphite-cli`/`writing-bash-scripts` self-contained model (ref: Q1, Discovered Patterns).
**NEW PATTERN?** No — mirrors the established global "using-<tool>" self-contained skill model.

### Decision 2: Content split between SKILL.md body and references/

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Everything inline in SKILL.md | Single file | Blows the <500-line/5000-token budget; poor signal-to-noise |
| B | Lean body + 4 references files pulled in by explicit pointers | Keeps body under budget; matches `qrspi-work`→`references/` pattern | Slightly more files to maintain |

**Recommendation:** Option B
**Rationale:** `qrspi-work` already demonstrates offloading focused detail to `references/` with explicit in-body pointers (ref: Q2); keeps SKILL.md within the advisory size budget (ref: Q7).
**NEW PATTERN?** No.

### Decision 3: Frontmatter shape — minimal vs full Claude Code extensions

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `name` + `description` only | Matches agentskills.io minimum; no false slash-command/tool claims | Omits optional metadata |
| B | Add `command`/`argument-hint`/`allowed-tools` | Consistent with qrspi phase skills | Those skills are slash-command-invoked wrappers; a guidance skill has no slash command or tool lockdown to declare |

**Recommendation:** Option A
**Rationale:** The qrspi `allowed-tools`/`command` fields exist because those skills are invoked as slash commands and spawn agents (ref: Q3). A content/guidance skill is auto-invoked by description match and needs no tool lockdown; `name`+`description` is the agentskills.io minimum (ref: Q3, Q6).
**NEW PATTERN?** No — uses the documented frontmatter minimum.

### Decision 4: Opinionated guidance encoding

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Decision tables (memory tiers; oMLX vs Ollama vs LM Studio) + explicit out-of-scope list | Matches repo idiom (`qrspi-work` state table + forbidden list); scannable | None material |
| B | Prose recommendations | Flexible | Harder to scan; weaker as an enforceable guardrail |

**Recommendation:** Option A
**Rationale:** The repo expresses opinion via compact decision tables and explicit forbidden/out-of-scope lists (ref: Q9).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| omlx CLI facts (flags, URLs, behaviors) are unverifiable from this repo and may not match the real tool | med | med | Source all factual content from the ticket body verbatim; do not invent flags or behaviors beyond what the ticket specifies; note that commands are as documented by the tool |
| SKILL.md exceeds the advisory size budget | low | low | Push detail into 4 references files; keep body to lifecycle + decision tables + pointers (ref: Q2, Q7) |
| Skill description triggers too broadly/narrowly (no repo eval to tune it) | med | low | Write description with explicit Apple-Silicon/omlx trigger phrases and a "Use when" clause, mirroring `qrspi-work` (ref: Q6); rely on global skill-creator conventions |
| Agent on a non-Apple-Silicon host follows the skill and fails | med | med | Lead SKILL.md with hard preconditions (macOS 15+, Apple Silicon, Python 3.10+) and a stop-if-unmet instruction (ref: Q8) |
| Deliverable lands in `.worktrees/` (gitignored) and is lost | low | high | Author the skill inside the worktree at `.claude/skills/using-omlx-cli/` (tracked path), NOT under `.worktrees/`; verified by `git status` during implementation |

## Open Questions

- OQ1: Should the skill be authored as auto-invoked only (no slash command) per Decision 3, or does the team also want a `command:`/slash entry point for manual invocation? Design assumes auto-invoked only.
- OQ2: The ticket says "use the Anthropic skill builder skill," which is global and not in this repo. Is following its conventions (rather than literally invoking it inside this automated run) acceptable for the acceptance criterion? Design assumes yes.
- OQ3: Is four references files the right granularity, or should troubleshooting/perf be merged to reduce file count?
