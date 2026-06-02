# Design — Create a skill for auto-triaging

**Ticket:** INFRA-2059
**Research basis:** research.md @ 2026-06-02T14:35:00Z
**Generated:** 2026-06-02T14:40:00Z
**Status:** draft

## Current State

There is no existing auto-triager script in this codebase (ref: Q1). The entire repository under `/workspaces/qrspi/.worktrees/INFRA-2059/` is the QRSPI framework itself — a structured workflow system for AI-agent-driven software development. No Slack integration, no `#alerts-daytime` channel reference, and no alert ingestion pipeline exist anywhere in the repo (ref: Q1).

The closest analogy for triage/filtering logic exists within the eval system's regression guard in `scripts/report.py`, which evaluates version scores against promotion criteria (`test_score_no_regression`, `no_large_drops`, `acceptable_gap`) but operates on internal eval results rather than incoming alert payloads (ref: Q2). That filtering code uses hard-coded constants, not configurable rules (ref: Q2).

No auto-triager script produces outputs for `#alerts-daytime` or any external channel (ref: Q3). The closest output-producing script is `scripts/report.py`, which writes a JSON report file to a local filesystem path — never an external channel (ref: Q3). Output delivery in this codebase is always filesystem-local; there is no channel-messaging library or outbound network transport (ref: Q3).

No existing auto-triager calls any external APIs or services because no such script exists (ref: Q4). More broadly, none of the Python scripts in `scripts/` make any external HTTP/API calls — all are self-contained CLI tools that read/write local files (ref: Q4). The only external communication path is through the `gh` CLI (GitHub) and Linear MCP tool calls, both mediated through CLI wrappers (ref: Q4).

No auto-triager persists state between runs (ref: Q6). State in this codebase generally is filesystem-local JSON — e.g., `results/<version>/ledger.json` — with no shared cache, Redis, queue, or persistent database (ref: Q6). The entire Python ecosystem uses stdlib-only packages (`json`, `argparse`, `re`, `statistics`, `pathlib`) and has zero third-party dependencies (ref: pattern 1).

The auto-triager is expected to respond to alerts from the `#alerts-daytime` Slack channel. The ticket states there is a "very basic script" already in use by an auto-triager agent running in Devin; this script lives outside this codebase and must be extended, formalized as a reusable skill, and brought into version control (ref: Q5, Q7-Q12).

There is no test infrastructure for channel interactions because no channel interaction code exists yet (ref: Q9). No existing logging, metrics, or tracing is emitted — scripts use only `print()` statements to stdout; there are zero structured log imports (ref: Q11). The entire Python codebase is self-contained, fully testable without external services, and has no retry logic, dead-letter queues, or deduplication (ref: Q7, Q8).

The eval harness is a non-functional placeholder with all three critical execution paths as stubs returning `None` (ref: Q9, pattern 7). The batch orchestrator (`qrspi-batch.js`) delegates to typed phase agents and has no error handling for agent spawn failures (ref: pattern 10).

## Desired End State

After this feature ships, the following system behaviors will be in place:

**A1 — Auto-triage skill exists as a first-class Python module.** A new package `triage/` is added to the codebase with structured modules for alert ingestion, rule evaluation, and response dispatch. It follows stdlib-only convention (no third-party imports).

**A2 — Configurable triage rules replace hard-coded filters.** The auto-triager reads triage rules from a YAML or JSON config file (`triage/rules.json` or `triage/config.yaml`). Rules are expressed as declarative predicates (severity, source, keywords) rather than inline Python conditionals. This replaces the current one-shot approach of hard-coded constants in `report.py`.

**A3 — The skill responds to `#alerts-daytime` channel events.** When an alert arrives in `#alerts-daytime`, the skill ingests the payload (Slack event object), runs it against the rule engine, and produces a human-readable response that is posted back to the channel. This requires a new Slack webhook or bot API integration layer.

**A4 — The skill can be reused across other channel triggers and services.** The same core rule engine and dispatch logic is parameterized so that different channels (e.g., `#alerts-nighttime`, PagerDuty webhooks) share the same code path with only config differences. No branch-by-variant code paths exist.

**A5 — Structured logging distinguishes triager output from existing print statements.** The skill emits structured JSON logs (using a lightweight Python stdlib approach or a minimal `python-json-logger` dependency for parsing). Log entries include an `agent` field (`auto_triager`) so that rollback or A/B comparison is trivially feasible (ref: Q12).

**A6 — Testable architecture separates pure logic from external dependencies.** The rule engine, alert parser, and response formatter are pure functions testable without live service connections (following the codebase's existing stdlib-only, file-based testing convention per pattern 1 and ref: Q10). Slack API calls and HTTP dispatch are injectable interface implementations with test doubles.

**A7 — Error handling covers failed channel deliveries.** When Slack returns an error or timeout on a response, the skill logs the failure to a local JSON "outbox" file (best-effort like `report.py`), providing replay capability if the Slack API becomes available again. This is consistent with the codebase's best-effort file-based state pattern (ref: Q8, pattern 6).

**A8 — The skill follows existing codebase patterns.** It uses stdlib-only Python where possible, self-locates its root from `__file__` (Fix A pattern for path robustness per pattern 3 and pattern 5), and is invokable as a CLI tool (`python -m triage --channel alerts-daytime`) with argparse-based flags (ref: Q5).

## Delta

### New Files

| Path | Purpose |
|------|---------|
| `triage/__init__.py` | Package root; exposes `run()` as entry point |
| `triage/engine.py` | Rule engine: reads rules config, evaluates alert against predicates, returns match result (pure functions) |
| `triage/parser.py` | Alert parser: normalizes incoming Slack event objects into a canonical dict schema |
| `triage/dispatch.py` | Response dispatcher: posts formatted response to the target channel (Slack webhook or bot API) |
| `triage/config.yaml` | Default triage rules file — severity thresholds, keyword filters, source routing, default responses |
| `triage/cli.py` | CLI entry point: argparse with flags for `--channel`, `--config`, `--dry-run`, `--simulate` |
| `triage/logging_config.py` | Structured log setup: JSON-formatted logger named `auto_triager` with version/timestamp metadata |
| `triage/outbox.json` | (Created at runtime) Best-effort replay buffer for failed Slack deliveries |
| `tests/triage/` | Test directory mirroring module structure; fixtures under `tests/fixtures/` |

### Modified Files

None. This is a greenfield addition — no existing files are modified. The codebase has no dependency on the auto-triager that would require updating import paths or configuration files.

### New Dependencies

- `pyyaml` (via `pip install pyyaml`) for config file parsing — this is the single non-stdlib dependency introduced by this ticket. Alternatively, use JSON config to maintain strict stdlib-only stance (decision 1 below).
- No network libraries required in the core package; Slack dispatch uses Python's built-in `http.client` or a separate thin adapter.

## Pattern Decisions

### Decision 1: Config format — JSON (stdlib) vs YAML (`pyyaml`)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: JSON config | Use native Python `json` module; no new dependency. Follows existing codebase pattern exactly (patterns 1, 6). Slightly less human-friendly comments/support. |
| B: YAML config | Better readability for non-engineers writing rules. Requires `pyyaml` — the single third-party dependency this feature introduces. Easier future extensibility for complex rule expressions. |

**Recommendation:** Option A (JSON)
**Rationale:** The codebase's dominant pattern is stdlib-only Python with file-based JSON state (patterns 1, 3, 6). Adding a third-party dependency violates that convention and creates a maintenance burden for a feature whose rules are likely simple key-value predicates. If complex rule expressions are needed later, migrate to YAML via an optional `pyyaml` install. The existing `report.py` hard-coded filters are simple enough that JSON config will suffice initially.
**NEW PATTERN?** No — follows the existing stdlib-only, JSON-file-based pattern.

### Decision 2: Slack integration — webhook URL vs bot API

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: Inbound webhook | Simplest to implement; requires only an incoming webhook URL config. Limited to posting to one configured channel; no ability to read messages or interact with threads. |
| B: Bot API (OAuth + event subscriptions) | Full capability: post to any channel, read messages for context, respond in threads. Requires OAuth setup, event subscription config, and a running service to receive events. More complex ops. |

**Recommendation:** Option A (webhook) for v1
**Rationale:** The ticket says "extend" a basic script, implying the existing Devin auto-triager already has some integration working. Webhook is sufficient for the stated use case: responding to `#alerts-daytime`. Bot API is overkill for a first version and adds operational complexity (event subscription registration, OAuth token management). This aligns with the codebase's "CLI-first, no daemon" pattern — webhook fits a CLI invocation model; bot API needs a long-running listener. If multi-channel routing becomes necessary, migrate to bot API in a follow-up.
**NEW PATTERN?** Yes — this is the first Slack integration in a codebase that has zero external integrations (pattern 9).

### Decision 3: Alert parsing — strict schema vs flexible dict

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: Strict schema with `dataclasses` | Enforces canonical shape for downstream rule matching. Fails fast on malformed input (consistent with `run_eval.py` pattern of raising `ValueError`). Requires upfront schema definition. |
| B: Flexible dict passthrough | Simpler initial implementation; handles unexpected alert shapes without code changes. Risks silent failures and inconsistent downstream behavior. |

**Recommendation:** Option A (strict schema)
**Rationale:** The existing codebase uses strict validation with `ValueError` for malformed input (`run_eval.py:42-57`, ref: Q7). This pattern produces faster failure detection and clearer debugging. For a triage system where incorrect alert parsing could cause missed responses or wrong-channel posts, strictness is preferable. Follows the principle that the codebase favors explicit over implicit.
**NEW PATTERN?** No — follows existing validation convention (ref: Q7, evidence from `run_eval.py`).

### Decision 4: Test doubles for Slack dispatch — module replacement vs protocol abstraction

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: Module-level monkey-patch in tests (`sys.modules['triage.dispatch'] = mock_module`) | Simple; no codebase changes needed. Brittle — breaks with refactoring or if dispatch is imported differently. |
| B: Interface protocol (ABC / Protocol) for `dispatchers` | Clean separation; easy to swap implementations (real Slack, test stub, dry-run). Requires adding a base class or Protocol at definition time. |

**Recommendation:** Option B (Protocol)
**Rationale:** Since this is greenfield code and the codebase follows functional purity patterns (pure functions in `grade.py`, `report.py`), defining an interface upfront prevents refactoring churn later. The existing test infrastructure (see eval harness placeholder, pattern 7) will need to exercise these interfaces when it becomes functional. Aligns with the design principle that pure logic should be separable from I/O.
**NEW PATTERN?** Yes — first use of an explicit interface/Protocol in a codebase that has no prior protocol definitions.

### Decision 5: Skill packaging — `python -m triage` vs `triage` entry script

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: `__main__.py`-backed package (`python -m triage`) | PEP 328 compliant; works from any working directory. Slightly more verbose CLI invocation. |
| B: Standalone script in `scripts/` or project root | Simpler to invoke; fits the existing `scripts/` convention for one-shot tools. Less modular; harder to import as a library for tests. |

**Recommendation:** Option A (`python -m triage`)
**Rationale:** The ticket says "put into the codebase so we can make updates that go through review and reuse it against other channel triggers, move to other services." Package-level structure supports both CLI usage and import-as-library patterns for downstream consumers. This also aligns with how QRSPI itself structures its phase agents (`.claude/agents/` packages) rather than one-off scripts. The codebase already has `scripts/` for one-shot CLI tools; a multi-module package is a natural extension.
**NEW PATTERN?** Partially — the codebase has no multi-module Python packages yet; all Python code is single-file scripts under `scripts/`.

### Decision 6: Structured logging format — full `structlog` vs lightweight JSON

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: Full `structlog` library | Rich formatting, context vars, processor pipeline. Third-party dependency. Overkill for this scope. |
| B: Lightweight JSON via `json.dumps` in a helper function | Stdlib-only; matches the existing `print()`-only observability baseline (ref: Q11). Sufficient for downstream log parsers to consume. Minimal code. |

**Recommendation:** Option B (lightweight JSON)
**Rationale:** The existing codebase has zero structured logging — only `print()` statements (ref: Q11, evidence from `report.py:159-168`). Introducing a third-party logging library would add a second non-stdlib dependency alongside `pyyaml` if chosen for config. A lightweight JSON logger via `json.dumps` in a helper function achieves the stated goal ("distinguishable log entries") with zero new dependencies. This is consistent with the "best-effort, minimal" philosophy evident throughout the codebase (patterns 1, 3, 6).
**NEW PATTERN?** No — this is the first structured log, but the format (JSON to stdout) follows the existing console output pattern and requires no external libraries.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Slack API changes or rate limits cause missed alerts | medium | high | Implement best-effort outbox (file-based retry queue) consistent with codebase pattern 6; add circuit-breaker-style config for rapid disable. Monitor dispatch latency in structured logs. |
| Introducing `pyyaml` dependency breaks the stdlib-only convention and creates a maintenance burden | medium | medium | Keep YAML as optional (`pip install pyyaml`). Default to JSON config (`triage/config.json`) which requires no extra install. Document the upgrade path clearly. |
| Slack webhook token is committed or leaked in version control | high | high | Ship only a `.example` config file with placeholder tokens; document where to obtain webhooks from Slack App settings. Add `.gitignore` entry for any real config. Use environment variable injection for secrets. |
| Alert schema evolves and breaks parser silently | medium | medium | Strict schema validation (`dataclasses`) with `ValueError` on malformed input (pattern from `run_eval.py`). Return early and log the error; do not silently drop alerts. |
| The skill becomes tightly coupled to `#alerts-daytime` Slack channel semantics, reducing reusability | medium | high | Enforce the Protocol interface for dispatch (Decision 4). Keep rule engine pure and channel-agnostic. Parameterize channel name via config, not code. |
| Existing print-based logging in `report.py` and other scripts pollutes any shared stdout the triager writes to | low | low | The triager runs as a separate process invocation, so its stdout is independent. If piped into a file later, prefix log lines with `[auto_triager]` for filterability. |
| The non-functional eval harness (pattern 7) means no automated tests exist to validate the new skill's behavior after merge | high | medium | Ship unit tests alongside the skill using `unittest.mock` for Slack dispatch. These do not depend on the broken eval harness — they are standard Python tests run via `python -m unittest`. Add a smoke-test fixture that exercises parser + engine end-to-end with mock data. |

## Open Questions

- OQ1: What is the exact structure of an alert payload from the `#alerts-daytime` channel? The ticket says there is a "very basic script" already in use by Devin; we need to inspect that script's expected input schema (JSON event envelope, text message format, attachments, etc.) to design the parser correctly.
- OQ2: Does the existing auto-triager in Devin use a Slack incoming webhook URL or an OAuth bot token? This determines which integration path (Decision 2) is appropriate and whether infrastructure changes (creating a new Slack App) are needed before implementation can proceed.
- OQ3: What triage rules does the current basic script encode? Understanding the existing ruleset (severity thresholds, keyword patterns, source routing) is essential to translate them into the configurable format — otherwise we risk changing triage behavior during migration.
- OQ4: Should the skill support both "respond in channel" and "create an issue/ticket" as triage outputs? The ticket mentions reusability across services; if some alerts should create Linear issues or Jira tickets, that output type needs design input now rather than as a follow-up.
