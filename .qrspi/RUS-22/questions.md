# Questions — Create `using-gemini-cli` Agent Skill

**Ticket:** RUS-22
**Generated:** 2026-06-02T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Where does the existing skill infrastructure live — specifically, what files and directories in `.claude/agents/` and `.claude/skills/` are read when Claude Code loads a slash-command skill, and how is `SKILL.md` parsed to determine which references/scripts/assets to expose?
   **Target:** `.claude/agents/`, `.claude/skills/`, and the CLAUDE.md parsing logic

- Q2: How does the batch orchestrator in `.claude/workflows/qrspi-batch.js` register and invoke skills, and what entrypoint mechanism links a skill name (e.g., `/qrspi-design`) to its underlying agent definition?
   **Target:** `.claude/workflows/qrspi-batch.js`

- Q3: What is the exact file layout of an existing skill in this repo (e.g., `qrspi-design`, `qrspi-research`), and does each follow a canonical directory structure under `.claude/skills/` or `.claude/agents/`?
   **Target:** `.claude/skills/`, `.claude/agents/`

- Q4: How are agent skills discovered at runtime — is there a manifest, glob pattern, or hardcoded registry that maps skill names to their `SKILL.md` files and any supplementary reference scripts?
   **Target:** The agent/skill discovery logic in the Claude Code harness configuration

## API Surface

- Q5: What CLI flags, environment variables, and configuration paths does the Gemini SDK expose (e.g., `GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`, approval modes like `--yolo` or `--sandbox`) that must be encoded as documented invocation patterns in the skill's `SKILL.md`?
   **Target:** The Gemini CLI binary and its published CLI interface

- Q6: How does the existing `qrspi-ticket` skill invoke Claude Code tools, and how should the new Gemini CLI skill encode tool usage (read/write/grep/replace/shell/subagent delegation) in a way that is compatible with the Claude Code harness?
   **Target:** `.claude/skills/qrspi-ticket/` or equivalent existing skill implementation

## State Management

- Q7: How should session management commands (`/chat save`, `/chat resume`, `/compact`) be encoded in `SKILL.md` when calling Gemini CLI non-interactively from another agent, given that non-interactive mode lacks session persistence?
   **Target:** The `SKILL.md` template and the non-interactive invocation path

- Q8: What is the configuration resolution priority (CLI args > env vars > project settings > global settings > defaults), and how should the skill surface this hierarchy to agents that need to locate or write a GEMINI.md context file?
   **Target:** The Gemini CLI configuration loading logic and GEMINI.md resolution

## Edge Cases

- Q9: How does the skill handle the deprecation notice — Google transitions free/personal accounts to Antigravity CLI after June 18, 2026, and the existing `gemini-cli` binary stops working. Should the skill encode a fallback or migration path?
   **Target:** The `SKILL.md` documentation section on limitations and caveats

- Q10: What happens when YOLO mode auto-approves but encounters a shell redirection operator prompt or Plan mode transition — how should agents detect and handle these known bugs at runtime?
   **Target:** The error handling path in the non-interactive invocation wrapper

- Q11: When running Gemini CLI as an autonomous subagent via `--sandbox`, what Docker/Podman sandbox profiles are available, and how does the `SANDBOX_MOUNTS` env var interact with external directory mounts?
   **Target:** The sandbox mode implementation in the Gemini CLI binary

## Testing

- Q12: How should the skill author validate that invoking Gemini CLI from a parent agent actually produces expected output — is there an existing test harness (e.g., `evals/` + `scripts/run_eval.py`) or a manual smoke-test pattern for cross-agent calls?
   **Target:** `evals/` directory and `scripts/run_eval.py`

- Q13: What integration tests exist for the existing skills (`qrspi-design`, `qrspi-research`, etc.), and how should the Gemini CLI skill's correctness be verified end-to-end before it is merged into the repository?
   **Target:** The test suite in `scripts/` (e.g., `_test.py` files) and the eval harness

## Observability

- Q14: How should agent calls to Gemini CLI be logged — is there an existing observability layer (logs, metrics, tracing hooks) that captures when a Claude Code skill invokes an external CLI tool, and what metadata fields should be attached?
   **Target:** The Claude Code harness logging or tracing infrastructure
