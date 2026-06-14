# Project: qrspi

## QRSPI Workflow

This project uses the QRSPI structured workflow for feature development.
Tickets are created as Linear issues. Ticket IDs follow Linear's format
(e.g., RUS-42). Artifacts are stored locally in `.qrspi/<ticket-id>/` — not
uploaded as attachments.

### Setup — Linear MCP

The harness talks to Linear through an MCP server it references by the fixed name
**`linear`** (tools `mcp__linear__*`) — no per-user server name is hard-coded
anywhere. The binding is committed in the project-scoped `.mcp.json` (the public
`https://mcp.linear.app/mcp` endpoint, no secrets); on first use Claude Code prompts
you to approve it, then you authenticate (OAuth) into **your** Linear workspace — the
one holding your QRSPI team/project. That OAuth/workspace selection is the only
per-user step; the repo stays portable.

`/qrspi-feature` (the front door) and `/qrspi-ticket` (direct single-ticket entry) both
materialize issues through the **same shared writer** (`.claude/skills/qrspi-ticket/references/writer.md`),
which files under the team/project from `.qrspi/config.json` (`linearTeam` / `linearProject`,
default project `QRSPI`; see `.qrspi/config.example.json`). If `linearTeam` is unset it
discovers/asks. No team name is hard-coded in the harness.

`linearProject` scopes **both** ticket creation **and** `qrspi-batch` runs: by default the
batch Query phase sweeps only the mapped project's assigned tickets (precedence
`input.ticket` > `input.allProjects` > `input.project` > config `linearProject` > `QRSPI`).
Pass `{"project":"..."}` to override for one run, or `{"allProjects":true}` to restore the
all-projects sweep (an absent project no longer means "all projects"). A concrete scope
that matches no Linear project aborts the run (fail loud) rather than sweeping empty.
Pass `{"ticket":"RUS-XX"}` to scope a run to a **single** ticket: the Query phase fetches
that one issue via `mcp__linear__get_issue` and skips project-scope resolution / the
`list_issues` sweep / the ordering step, running just that ticket through the identical
loop (a nonexistent id aborts, fail loud) — e.g.
`Workflow({ name: "qrspi-batch", args: { ticket: "RUS-58" } })`. The single ticket is still
re-fetched and re-decided by the resolver, so a gated (unassigned / not-`Selected`) ticket
still surfaces `entry_blocked`/`wait` as a recorded result.

### Lifecycle — PR-gated

**PR review state — not Linear status — is the authority for advancement.** Linear has
exactly two roles: an **entry gate** (a ticket may only begin if it is *assigned* and in
`Selected`) and a **best-effort reporting projection** (agents update status to reflect the
active phase; a failed Linear write never blocks work). See
`docs/qrspi-pr-gated-lifecycle-design.md` for the full design.

Each ticket is one Graphite stack, built bottom-up and **held open** until the whole feature
is approved, then landed bottom-up:

```
Selected (assigned)
  → design PR   [Questions·Research·Design]   ──approved──┐
  → plan PR     [Structure·Plan·WorkTree]      (stacked)  ──approved──┐
  → slice PRs   [Implementation]               (stacked)   ──all approved──→ land stack → Done
```

- **Branches:** `<id>/design` → `<id>/plan` → `<id>/slice-1..N`, each its own PR, stacked.
  (Replaces the old single `<id>/planning` branch.)
- **Advance** is automatic: approving a phase PR (`reviewDecision == APPROVED` **and** zero
  unresolved review threads) builds the next phase on top.
- **Reset** is automatic: a formal `CHANGES_REQUESTED` on an upstream phase PR discards every
  downstream phase (PRs closed, branches deleted, stale artifacts removed) and returns the
  ticket to that phase. **Revise** is also automatic and is the **unified feedback action** (it
  subsumes the former *respond-comment*, RUS-54): a *frontier* phase PR carrying a formal
  `CHANGES_REQUESTED` **and/or** unaddressed reviewer **comments** is addressed in place, in one
  pass. The worker (1) engages **each comment per-intent** — answers / applies+amends / declines
  with rationale — and posts an in-thread reply via `scripts/qrspi_comment_reply.py`, then (2)
  **only when a formal change request is present** also addresses the review summary, amends the
  phase commit, and re-requests review (which clears the change request — the loop-safe
  termination signal). A comment-only PR (no formal change request, even when APPROVED) is
  answered in place **without** re-requesting review (gh comment writes succeed with the bot's
  classic PAT — the old cross-account write block is gone). Review *threads* still cannot be
  auto-**resolved** (only the reviewer resolves a thread), and a thread the reviewer already
  resolved is excluded from the comment set (the gather drops resolved threads, RUS-69), so a PR
  whose only outstanding signal is unresolved threads with neither a change request nor an
  unaddressed reviewer comment is left for the reviewer and resolves to `wait`.
- **`*Approved` Linear states were dropped** — approval lives in the PR. Reporting statuses:
  `Selected` → `Design Review` → `Plan Review` → `Code Review` → `Done`.
- The decision is computed by a tested resolver (`scripts/qrspi_resolve_state.py`, unit-tested);
  the orchestrator and batch both call it rather than re-deriving state logic.
- The `qrspi-batch` workflow drives the autonomously-runnable actions across assigned tickets
  (run_design, advance, submit, land, automatic reset, and revise — addressing a frontier
  `CHANGES_REQUESTED` PR then re-requesting review); it skips only `wait` (not-yet-approved or
  thread-only PRs awaiting the reviewer).

### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-feature <feature description>` — **The front door for new feature work.** Elicits
  requirements, proposes a *reviewed* ticket decomposition (one ticket vs N, a dependency DAG, and
  an overlap scan against in-flight tickets), gates on human approval **before any Linear write**,
  then creates the ticket(s) via the shared writer with `blockedBy` edges under a Linear parent
  issue. Bias is hard toward one ticket with slices. Use this whenever a feature has no ticket yet.
- `/qrspi-ticket <initial description>` — Direct single-ticket entry: draft and file **one**
  already-scoped ticket through a guided interview (and the shared writer `qrspi-feature` reuses).
  For a whole feature that might split or carry dependencies, use `/qrspi-feature` instead.
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket (fetched from Linear)
- `/qrspi-research <ticket-id>` — Map the codebase (ticket is hidden from this phase)
- `/qrspi-design <ticket-id>` — Produce a design document (ticket fetched from Linear)
- `/qrspi-structure <ticket-id>` — Define vertical slices and contracts
- `/qrspi-plan <ticket-id>` — Write tactical implementation steps
- `/qrspi-worktree <ticket-id>` — Build a session-aware task DAG
- `/qrspi-implement <ticket-id> <slice-number>` — Implement one vertical slice
- `/qrspi-pr <ticket-id>` — Prepare pull request summary
- `/using-terraform-cli <what you want to do>` — Operate Terraform/OpenTofu safely from the CLI (lifecycle, remote state, version pinning, import/moved/removed, CI/CD with OIDC, secrets, workspaces, modules + testing)

### Workflow rules

- Phases run sequentially. Never skip ahead.
- Each artifact must exist and be reviewed before the next phase starts.
- Start a fresh `/clear` session between implementation slices.
- Use `/compact` if context grows large within a phase.
- Use `/context` to check utilization. If over 40%, compact or start fresh.

### Worktrees

Each ticket gets an isolated git worktree at `.worktrees/<ticket-id>/`. This allows
multiple agents to work on different tickets concurrently. The main repo checkout
stays on `main`; all ticket work happens in worktrees. `.worktrees/` is gitignored.

### Codebase conventions

- Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`
- The batch orchestrator workflow lives in `.claude/workflows/qrspi-batch.js`
- The PR-gated decision logic lives in `scripts/qrspi_resolve_state.py` (the tested resolver)
  and `scripts/qrspi_pr_state.py` (gathers PR review state via gh GraphQL). `scripts/qrspi_resolve.py`
  is the one-shot orchestrator that folds worktree setup + OWNER/REPO + the gather + the decision +
  artifact detection into a SINGLE deterministic command (it self-locates the repo root from its own
  path), so the resolve worker types one invocation instead of ~6 path-sensitive shell steps.
- Phase artifacts are persisted with **Fix A** (staging + deterministic move): each phase agent writes
  to a short, token-free staging path (`/tmp/phase-stage/<id>/<artifact>.md`, the `stg()` helper in
  qrspi-batch.js) — never the `qrspi`-laden canonical path — and `scripts/qrspi_persist.py` (self-locating,
  like the resolver) verifies the staged file is non-empty and moves it to `.worktrees/<id>/.qrspi/<id>/`.
  This removes the path-mangling root cause (a weak worker model corrupting the `qrspi` token in a Write
  target) and turns persistence into the real per-phase success gate, caught in `runPhase`.
- PR **reviewers** are resolved (not hard-coded) so the harness is shareable: `qrspi_resolve.py`
  returns `reviewers`/`teamReviewers` in its envelope and the finalize prompts splice them behind
  `gt submit --reviewers`/`--team-reviewers` via the `reviewerFlags()` helper. Source:
  `.qrspi/config.json` (gitignored; see `.qrspi/config.example.json`), falling back to the `@me`
  default, which expands to the gh-authenticated user (set `"reviewers": []` to opt out). Requesting
  a reviewer is what surfaces a PR in that user's Graphite review queue.
- PR **bodies default to Graphite-creation seeding**: `gt submit` has no body flag and seeds the
  PR description from the branch commit message *at creation only*, so the commit message remains
  the primary non-interactive lever and the orchestrator authors bodies that way. **A PR body MAY
  now be set or corrected after creation via the GitHub REST API** — `gh api
  repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@<file>` (the old "never edit a PR body with gh"
  rule is lifted; the bot's classic PAT writes PR bodies fine — see RUS-54 / the gh-cross-account
  note). Prefer the REST API PATCH over `gh pr edit`, which can abort on the Projects-classic
  GraphQL deprecation (`repository.pullRequest.projectCards`) and leave the body unchanged. This
  lifts only body/title editing; **publishing PRs still goes through `gt submit`, never `gh`**.
  Design/plan PRs use their heredoc commit message as the body; for implementation,
  `scripts/qrspi_pr_body.py` (self-locating, like the resolver) splices `pr-summary.md` into the
  slice-1 commit message before `gt submit`, and slices 2..N carry a focused "Part N/total" body
  from their own commit messages.
- All of the above have stdlib-only unit tests as `_test.py` siblings (`scripts/*_test.py`, run with `python3`).
  Run the whole suite with the aggregating runner `python3 scripts/run_tests.py` (`--list` to enumerate,
  a substring arg to filter, e.g. `python3 scripts/run_tests.py resolve`); it runs every `scripts/*_test.py`
  as its own subprocess and exits non-zero if any fails. The same command is the regression gate in CI
  (`.github/workflows/tests.yml`, on every PR + push to `main`). JS coverage of `qrspi-batch.js` is
  deferred (the file is harness-coupled — top-level `return`, injected globals, no import support — so it
  is not unit-testable in isolation without a refactor).
- Artifact templates live in `.qrspi/templates/` (reference only — not written locally)
- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
