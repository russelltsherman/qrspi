# Design — Create a new agent skill using the omlx CLI

**Ticket:** RUS-24
**Research basis:** research.md @ 2026-06-04T12:31:04Z
**Generated:** 2026-06-04T13:00:00Z
**Status:** draft

## Current State

Skills in this repo live one directory per skill at `.claude/skills/<skill-name>/`, each with a `SKILL.md` entry point; ten skills exist today, all namespaced `qrspi-*` (ref: Q1). The layout is convention-only — there is no validator, manifest, or schema file in the repo enforcing an "agentskills.io-standard" structure (ref: Q1). Only one skill uses a companion subdirectory: `qrspi-work/references/review-cascade.md`; no skill has a `scripts/` or `assets/` subdir, so `references/` is the only in-repo precedent for offloading material (ref: Q1, ref: Q6).

A second, distinct structure exists: `.claude/agents/<name>.md` holds heavier agent prompt bodies as flat `.md` files, while `.claude/skills/<name>/SKILL.md` holds the thin slash-command wrapper that delegates to it (ref: Q1). The two use different frontmatter shapes — skills use a flat `allowed-tools:` list; agents use a nested `claude: → tools:` block (ref: Q2). Every in-repo SKILL.md opens with YAML frontmatter in a consistent field order: `name → description → command → argument-hint → allowed-tools` (ref: Q2). A hard three-way identity holds across all ten skills: folder name == frontmatter `name` == `/command` suffix (ref: Q1, ref: Q4). Names are kebab-case lowercase; uniqueness of the folder within `.claude/skills/` is the only in-scope guard against collision (ref: Q4).

Descriptions encode activation cues ("Use when…") as the de-facto triggering mechanism; there is no programmatic triggering check in the repo (ref: Q10). The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder whose agent-execution core is a stub producing zeros, with `evals/golden/` empty and 17/21 fixtures missing (ref: Q8, ref: Q10). The in-repo failure-surfacing idiom is "verify post-condition, report error, stop" — fail-loud (ref: Q11).

Critically, the `skill-creator` ("Anthropic skill builder") skill, its invocation contract, its file-output target, its create-vs-edit semantics, its token/line budget enforcement, and its validation-reporting path are all NOT in the repo — they are external/global and out of project scope (ref: Q3, ref: Q5, ref: Q7, ref: Q9, ref: Q11). For a skill to be discovered it must physically reside at `.claude/skills/<name>/SKILL.md` regardless of how it is authored (ref: Q5).

## Desired End State

A new skill, proposed name `using-omlx-cli` (see Decision 2), lives at `.claude/skills/using-omlx-cli/SKILL.md` with optional `references/` companions, authored via the external `skill-creator` skill. Each acceptance criterion maps to concrete behavior:

- **agentskills.io directory structure with valid SKILL.md frontmatter** → `.claude/skills/using-omlx-cli/SKILL.md` with frontmatter in the repo's observed field order `name → description → command → argument-hint → allowed-tools`, matching all ten existing skills (ref: Q1, ref: Q2).
- **Built using the Anthropic skill builder skill** → authored by invoking the external `skill-creator` skill; note this is out-of-repo tooling with no in-repo invocation contract (ref: Q3) — see OQ1.
- **SKILL.md body under 500 lines / 5000 tokens** → kept thin by offloading bulk to `references/` per the repo's wrapper-vs-body overflow idiom; no in-repo limit enforces this, so it is honored manually (ref: Q7).
- **Detailed reference material in references/ if needed** → companion files under `.claude/skills/using-omlx-cli/references/`, referenced by relative path in the SKILL.md body, read on demand (ref: Q6).
- **Covers full server lifecycle (install, serve, configure, monitor, stop)** → SKILL.md sections + a `references/` file for the long-form flag/lifecycle detail.
- **Memory-tier-aware model size recommendations** → an opinionated table (16/24/32/64 GB tiers) per ticket; guards against loading a 70B model on 16 GB.
- **Two-tier KV cache configuration and tuning** → documented hot/cold tier behavior and `--paged-ssd-cache-dir` / `--hot-cache-max-size` guidance.
- **OpenAI-compatible API endpoint usage** → `/v1/chat/completions`, `/v1/embeddings`, `/v1/messages` at `http://localhost:8000/v1`.
- **MCP integration and agent launch patterns** → `--mcp-config` and `omlx launch <agent>` coverage.
- **Common failure modes and troubleshooting** → Metal OOM crash loop, silent memory pressure, mixed-workload instability, model-not-showing.
- **Opinion on oMLX vs Ollama vs LM Studio** → a decision-guidance section encoding the ticket's "prefer when" rules.

The skill description embeds "Use when…" trigger phrases (Apple Silicon, local LLM inference, omlx) to match the repo's triggering convention (ref: Q10).

## Delta

New files:
- `.claude/skills/using-omlx-cli/SKILL.md` — thin entry point: frontmatter + lifecycle overview, memory-tier table, KV-cache summary, API/MCP/agent-launch summary, oMLX-vs-alternatives opinion, troubleshooting index, and relative pointers into `references/`.
- `.claude/skills/using-omlx-cli/references/` — one or more companion files holding the long-form detail that would push SKILL.md over budget (full `omlx serve` flag reference, exhaustive troubleshooting, per-tier tuning tables).

No modified files are strictly required. The existing slash-command list in `.claude/CLAUDE.md` and the project skill catalog are documentation-only and not validated; updating them is optional polish (see OQ3).

Unlike every `qrspi-*` skill, this skill is **self-contained** — it does not delegate to a `.claude/agents/<name>.md` body, because it is reference/knowledge guidance rather than a phase orchestrator (see Decision 1). No agent `.md` file is created.

No DB queries, middleware, or scripts are involved.

## Pattern Decisions

### Decision 1: Where the skill body lives — agent-delegated wrapper vs self-contained skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin SKILL.md wrapper that delegates to a `.claude/agents/using-omlx-cli.md` body, mirroring every `qrspi-*` skill (ref: Q1) | Maximal consistency with the dominant repo pattern | The agents/ pattern exists for *phase orchestrators* spawned by the batch workflow; an agent body for static reference knowledge is a misuse — adds a second file and a frontmatter-shape footgun (ref: Q2, Inconsistencies) |
| B | Self-contained SKILL.md with bulk pushed to `references/`, mirroring `qrspi-work`'s `references/review-cascade.md` (ref: Q6) | Matches the in-repo overflow idiom; single discoverable artifact; avoids the agents/ frontmatter mismatch; agentskills.io standard treats SKILL.md as the primary doc | Diverges from the wrapper-vs-body split used by the other ten skills |

**Recommendation:** Option B
**Rationale:** The wrapper-to-`.claude/agents/` split exists specifically for QRSPI phase agents the batch workflow spawns (ref: Q1, Discovered Patterns). This skill is reference guidance, not an orchestrated phase, so the agent body adds nothing and risks the documented `allowed-tools` vs `claude:→tools:` frontmatter swap (ref: Q2, Inconsistencies). The `references/` offload is the repo's established mechanism for static long-form content (ref: Q6, ref: Q7) and aligns with the agentskills.io standard the ticket targets.
**NEW PATTERN?** Yes — no existing skill is fully self-contained (every one delegates to `.claude/agents/`). Justified because the agent-delegation pattern is purpose-built for phase orchestration, which this knowledge skill is not; reusing `references/` (an existing pattern) for the bulk keeps the divergence minimal.

### Decision 2: Skill name / identifier

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `using-omlx-cli` | Matches the external `using-graphite-cli` "using-…-cli" precedent (ref: Q4); kebab-case; clear; no collision with the ten `qrspi-*` folders (ref: Q4) | Breaks the repo's uniform `qrspi-*` namespace |
| B | `qrspi-omlx` or similar `qrspi-*` name | Stays inside the repo's only existing namespace | Misleading — implies a QRSPI workflow phase; the skill has nothing to do with the QRSPI lifecycle |

**Recommendation:** Option A
**Rationale:** Every existing repo skill is `qrspi-*` because they are all QRSPI phases (ref: Q1); this skill is not, so inheriting that namespace would mislead. `using-omlx-cli` follows the established `using-<tool>-cli` shape and the kebab-case convention, and the three-way identity (folder == `name` == `/command`) is preserved (ref: Q4). The ticket title itself ("using omlx cli") supports this name.
**NEW PATTERN?** No — `using-…-cli` is an existing external naming pattern (`using-graphite-cli`); only the namespace prefix differs from the in-repo `qrspi-*` set.

### Decision 3: How `references/` content is structured and linked

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One catch-all `references/reference.md` linked from SKILL.md by relative path (ref: Q6) | Simplest; one file to maintain; matches `qrspi-work`'s single-companion example | A large single file is harder to load selectively on demand |
| B | Topic-split companions (e.g. `references/serve-flags.md`, `references/troubleshooting.md`, `references/memory-tiers.md`), each linked by relative path | Agent loads only the relevant slice on demand; cleaner separation of the long flag list vs troubleshooting | More files; no in-repo precedent for multiple companions (only one exists) |

**Recommendation:** Option B
**Rationale:** The repo's companion convention is "name the relative file in the body, read on demand" with no manifest (ref: Q6). Topic-split files maximize the on-demand benefit the convention exists for and keep SKILL.md comfortably under the 500-line/5000-token budget the ticket requires (ref: Q7). The single-file precedent in `qrspi-work` is not a constraint — it is just the only example so far.
**NEW PATTERN?** No — multiple `references/` files extend the existing relative-reference convention; nothing structurally new.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` invocation contract is undocumented in-repo (out of scope), so the "built with skill builder" criterion cannot be mechanically verified here (ref: Q3) | high | med | Invoke `skill-creator` from the global harness; capture that it was used; OQ1 flags the contract gap for human confirmation |
| No in-repo validator for frontmatter, body size, or name collision — invalid output ships silently (ref: Q2, ref: Q7, ref: Q11) | med | med | Manually match the observed frontmatter field order and the three-way name identity; manually check body line/token budget; rely on `skill-creator`'s external validation |
| omlx CLI facts (flags, ports, endpoints) come entirely from the ticket — omlx is absent from the repo and from research (ref: Q3 searches: `find -iname '*omlx*'` → 0 hits) | med | high | Treat ticket text as the authoritative spec; do not invent flags beyond it; OQ2 asks for an upstream-docs source to validate against |
| Eval/triggering verification is non-functional (stub harness, empty golden set) so triggering accuracy can't be measured (ref: Q8, ref: Q10) | high | low | Encode strong "Use when…" trigger phrases per the repo convention; verify triggering manually rather than via the placeholder harness |
| Frontmatter-shape footgun if Decision 1 Option A were chosen (agents use `claude:→tools:`, skills use `allowed-tools:`) (ref: Q2) | low | med | Decision 1 recommends the self-contained skill, avoiding any agent `.md` and this footgun entirely |

## Open Questions

- OQ1: What is the exact invocation contract and expected inputs for the external `skill-creator` ("Anthropic skill builder") skill in this environment? It is not in the repo (ref: Q3), and the ticket mandates building the skill with it.
- OQ2: Is there an authoritative upstream omlx documentation source to validate the ticket's CLI flags, endpoints, and version requirements against? omlx returns zero hits in the repo (ref: Q3), so the ticket is currently the only source of truth.
- OQ3: Should the new skill be added to the human-facing skill catalog in `.claude/CLAUDE.md` and the slash-command list, or left out since those lists are unvalidated documentation (ref: Q4, Delta)?
- OQ4: Confirm the skill name `using-omlx-cli` (Decision 2) rather than a `qrspi-*` namespaced name — this is the one decision that breaks the repo's uniform namespace.
