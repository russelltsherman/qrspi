# Q10: Branch Naming to Prevent Collisions in Concurrent Agent Execution

## Summary and Recommendation

**Use orchestrator-assigned, deterministic names of the form `agent/<ticket-id>-<slice>-<run-id>` and enforce a GitHub Ruleset that restricts all pushes outside that namespace.**

The orchestrator — not the agent — must choose the branch name before the container starts. The name should embed three uniqueness components: the ticket ID (human-readable, stable across retries), the slice number (distinguishes parallel work units within a ticket), and a short run identifier (a UUID prefix or the container/job ID assigned by the scheduler). An example: `agent/T-123-slice-2-a4f1b8`. This approach:

- Guarantees uniqueness without coordination between agents.
- Prevents agents from choosing names that trigger sensitive CI/CD paths or overwrite human branches.
- Allows GitHub Rulesets to scope agent push permissions to the `agent/**` namespace exclusively.
- Remains legible in PR lists and audit logs while still being machine-parseable.

---

## 1. Collision Risk: What Happens When Two Agents Push to the Same Branch

Git reference updates are not transactional in the way database writes are. The server accepts objects in a lockless phase, then attempts to atomically advance the ref pointer. If two agents push to the same branch simultaneously, one of two outcomes occurs:

1. **Non-fast-forward rejection** — If both agents start from the same parent commit, the second push will be rejected with a "non-fast-forward" error because the remote ref has already been moved by the first push. No data is silently lost, but the second agent's work is not recorded on the branch.
2. **Silent overwrite via force-push** — If either agent pushes with `--force` (common in rebase-based workflows), the second push silently discards the first agent's commits. This is the dangerous case: the earlier agent's work disappears with no warning.

The window for a race exists between the moment an agent clones the repo and the moment it pushes. With containers starting in parallel from the same scheduler event, this window can be seconds wide. Even with non-force pushes, the rejected agent will fail mid-task, requiring orchestrator-level retry logic.

**Conclusion:** Two agents must never target the same branch name. The simplest guarantee is ensuring names are assigned before containers start, making collision structurally impossible rather than probabilistically unlikely.

---

## 2. Git Branch Naming Constraints

### 2.1 Core Git Rules (`git check-ref-format`)

Git enforces the following rules for all reference names. A branch name that violates any rule is rejected at push time:

| Rule | Detail |
|------|--------|
| No component starts with `.` | `feature/.hidden` is invalid |
| No component ends with `.lock` | `feature/work.lock` is invalid |
| No consecutive dots `..` | `feature..fix` is invalid |
| No control characters (< 0x20 or 0x7F) | Tabs, null bytes, DEL are forbidden |
| No space, `~`, `^`, `:` | These characters are forbidden anywhere |
| No `?`, `*`, `[` | Shell glob metacharacters are forbidden |
| No leading or trailing `/` | `/feature` and `feature/` are invalid |
| No consecutive `//` | `feature//fix` is invalid |
| No trailing `.` | `feature.` is invalid |
| No `@{` sequence | Reserved for reflog notation |
| Cannot be the single character `@` | Reserved |
| No backslash `\` | Forbidden everywhere |
| Branch names cannot start with `-` | Stricter than the general ref rule |

### 2.2 GitHub-Specific Additional Restrictions

GitHub adds two restrictions beyond core Git:

1. Names that look like Git object IDs (40 hex characters) are rejected to prevent confusion with SHA references.
2. Names beginning with `refs/` are rejected because GitHub manages the full `refs/` namespace internally.

### 2.3 Length

Git itself imposes no explicit character count limit on ref names; the practical ceiling is filesystem path length (typically 255 bytes per component on most operating systems, with a 4096-byte overall path limit). GitHub imposes no documented hard limit shorter than this. However, names exceeding 100–120 characters become unwieldy in UI displays and command-line output. Keeping agent branch names under 80 characters is a practical target.

### 2.4 Safe Character Set for Agent-Generated Names

For machine-generated names, restrict to: `[a-z0-9]`, hyphens `-`, underscores `_`, and forward slashes `/` for hierarchy. Avoid uppercase (some case-insensitive filesystems can cause conflicts), and avoid all characters in the forbidden list above.

A safe regex for validating a generated name before use:

```
^agent/[a-z0-9][a-z0-9_-]{0,60}(/[a-z0-9][a-z0-9_-]{0,30})*$
```

---

## 3. Deterministic Naming Strategies

### 3.1 Ticket-ID-Based Names

**Pattern:** `agent/<ticket-id>-<slice>` — e.g., `agent/T-123-slice-2`

**Pros:**
- Human-readable; reviewers immediately know which ticket a branch belongs to.
- Deterministic: given the same inputs, you always get the same name, which aids idempotency.
- Easy to filter in GitHub UI by searching for the ticket ID.

**Cons:**
- Not unique across retries of the same slice. If slice 2 of T-123 is retried, it would push to the same branch, overwriting the previous failed attempt (which may be intentional but should be explicit).
- Requires ticket IDs to be normalized to branch-safe characters (e.g., spaces removed, Jira-style `PROJ-123` converted to `proj-123`).

### 3.2 UUID-Based Names

**Pattern:** `agent/<uuid4>` — e.g., `agent/4a7bc912-3ef1-4d2b-9a01-0f1e2b3c4d5e`

**Pros:**
- Statistically guaranteed unique with no coordination; UUID v4 collision probability is negligible (requires ~2.7 × 10¹⁸ generated IDs for a 50% collision probability).
- No dependency on ticket system being reachable at branch-creation time.

**Cons:**
- Opaque; branch lists become unreadable.
- No human can tell from the branch name what ticket or slice it represents.
- Previous runs produce different names, so re-running does not produce idempotent results.

GitHub Copilot's earlier strategy used UUID-style names (`copilot/fix-bdaf7923-9865-4ef5-8c17-05ae939937a3`) and has since moved away from them specifically because they were unreadable. The changelog notes the shift to descriptive names like `copilot/add-theme-switcher` for reviewer ergonomics.

### 3.3 Timestamp-Based Names

**Pattern:** `agent/T-123-20260418T143512Z`

**Pros:**
- Sortable and unique to the second within a single ticket.

**Cons:**
- Two containers starting within the same second (common in batch scheduling) can produce identical names.
- Timezone handling is error-prone; must use UTC and ISO 8601 format consistently.
- Does not encode slice identity, so parallel slices still collide.

### 3.4 Hybrid: Ticket + Slice + Short ID (Recommended)

**Pattern:** `agent/<normalized-ticket>-<slice>-<short-id>`

**Example:** `agent/t-123-s2-a4f1b8`

The short ID can be:
- The first 6–8 characters of a UUID v4 (extremely low collision probability for typical workloads).
- The container or Kubernetes job ID assigned by the scheduler (guaranteed unique by the scheduler).
- The `GITHUB_RUN_ID` if the agent runs inside GitHub Actions (a globally unique integer per workflow run).

This hybrid provides human readability via the ticket/slice portion and uniqueness guarantees via the short ID, while staying comfortably under the 80-character target.

---

## 4. Orchestrator-Assigned vs. Agent-Chosen Names

### 4.1 Why the Agent Must Not Choose Its Own Branch Name

Allowing an agent to select its own branch name at runtime introduces several security and correctness risks:

**CI/CD pipeline triggering:** GitHub Actions workflows trigger on push events filtered by branch patterns. An agent that names its branch `main`, `release/v2`, or any name matching an existing workflow's `on.push.branches` filter will fire those workflows — potentially with access to production secrets, deployment credentials, and environment-gated approvals. A misconfigured or compromised agent model could intentionally choose such a name.

**Overwriting human branches:** If an agent generates a name that collides with an existing human branch and is configured to force-push (or the branch has no protection), it will silently destroy the history on that branch.

**Branch protection bypass:** Certain GitHub Actions triggers (`pull_request_target`) historically ran with write permission and access to secrets regardless of the PR's origin. If an agent can push to a branch name that matches a pattern with elevated CI permissions, it can escalate privileges.

**Prompt injection / name injection:** If the branch name is derived from user input (e.g., the ticket title), an adversarial ticket title containing characters like `$(...)` or a name designed to match a protected pattern becomes a prompt injection vector.

### 4.2 The Orchestrator Should Assign Names Before Container Start

The orchestrator knows:
- The ticket ID.
- The slice number.
- Its own job/run identifier (assigned by the scheduler, not derived from AI output).

The branch name should be computed from these inputs using a pure function before the container is created. The name is passed to the container as an environment variable or mounted configuration file. The agent is instructed (via its system prompt or configuration) to use exactly this name and not to create any other branches.

This eliminates an entire class of privilege escalation attacks: the agent cannot choose a branch name to influence its own CI/CD permissions, because it never has that choice.

---

## 5. GitHub Branch Protection and Rulesets

### 5.1 Classic Branch Protection Rules

GitHub's classic branch protection rules use `fnmatch` syntax with `File::FNM_PATHNAME` semantics:
- `*` matches any string except `/`.
- `**` matches any string including `/`.
- `agent/*` matches `agent/T-123` but not `agent/T-123/slice-2`.
- `agent/**/*` matches arbitrarily nested paths under `agent/`.

A protection rule on `agent/*` can require:
- Status checks to pass before merge (preventing agents from merging their own PRs).
- No direct pushes without a PR (forces a review gate).
- No force pushes (prevents history rewriting).

### 5.2 GitHub Rulesets (Recommended over Classic Rules)

Rulesets, introduced as the successor to classic branch protection rules, offer more granular control:

- **Restrict creations:** Only users/apps with bypass permissions can create branches matching the target pattern. This prevents an agent from creating branches outside the `agent/` namespace.
- **Restrict updates (push restriction):** Only bypass actors can push to matching branches. This can be configured so only the designated agent GitHub App can push to `agent/**` branches.
- **Bypass actors:** Rulesets support three bypass actor types: roles (admin/maintain/write), teams, and GitHub Apps. The agent's GitHub App identity can be granted bypass on `agent/**` while humans are held to standard review requirements.
- **Restrict pushes that create files (regex):** For more complex name validation, the "Must match a given regex pattern" metadata rule can enforce that branch names follow the exact expected format.

**Recommended ruleset configuration:**

| Ruleset | Target pattern | Rule | Bypass |
|---------|---------------|------|--------|
| Protect main/release | `main`, `release/**` | No direct push, require PR, no force push | Admins only |
| Agent namespace | `agent/**` | No force push, require PR | Agent GitHub App |
| Restrict agent creation | `agent/**` | Restrict creations | Agent GitHub App only |
| Block out-of-namespace pushes | Everything except `agent/**` and protected branches | Restrict creations | Humans + App, block unknown identities |

The "restrict creations" rule on `agent/**` means that even if an agent tried to push to `human-feature/foo`, the ruleset would reject the push because the creating identity (the agent GitHub App) only has creation bypass on `agent/**`.

### 5.3 Requiring Status Checks Before Merge

A critical control: agent-created PRs should require passing CI before they can be merged, and the merge button should require human approval. This ensures that even if a branch name slips through naming controls, the code is reviewed before it lands on a protected branch.

---

## 6. Concurrent Execution Safety: Guaranteeing Uniqueness

### 6.1 The Check-Then-Act Problem

A naive "check if branch exists, then create" approach has a TOCTOU (time-of-check to time-of-use) race condition: two containers can both check for the same name, find it absent, and both attempt creation. Git's reference update is atomic at the server side — the second push will fail — but this means an agent fails mid-task unexpectedly rather than at startup.

### 6.2 Orchestrator-Level Uniqueness

The orchestrator has access to information unavailable to the agent:

- **Scheduler-assigned job/pod IDs:** Kubernetes uses `generateName` to produce unique pod names with a server-assigned suffix. The container orchestrator can incorporate this ID into the branch name before the pod starts, ensuring uniqueness by construction.
- **GitHub Actions `GITHUB_RUN_ID`:** This is a globally unique integer assigned by GitHub for each workflow run. A branch named `agent/T-123-s2-${{ github.run_id }}` is guaranteed unique across all concurrent runs in the repository.
- **UUID at dispatch time:** The orchestrator can generate a UUID v4 at the moment it dispatches the job, before any container is started. This requires no coordination between containers and is collision-resistant.

### 6.3 Idempotent Retry Strategy

If the requirement is that retries of the same slice reuse the same branch (to push additional commits rather than creating a new branch), the name should omit the run ID and use only the ticket and slice:

`agent/T-123-s2`

The orchestrator must then handle the case where the branch already exists by deciding whether to:
- Delete and recreate it (clean retry).
- Push on top of it (continuation).
- Fail with a conflict error (require human intervention).

The choice depends on the failure mode being retried. For clean retries after a code generation failure, deleting and recreating is safest. For network interruptions after successful generation, pushing on top is correct.

---

## 7. Namespace Isolation

### 7.1 The Case for a Dedicated `agent/` Prefix

Separating agent branches from human branches via a namespace prefix provides:

- **Access control boundary:** Rulesets can be scoped to `agent/**` without affecting human workflows.
- **Audit and filtering:** `git branch -r | grep agent/` immediately shows all agent branches. GitHub's PR search supports `head:agent/` filtering.
- **CI/CD scoping:** Workflow files can explicitly exclude or include `agent/**` branches using `branches` and `branches-ignore` patterns, giving precise control over which pipelines fire on agent pushes.
- **Cleanup hygiene:** A scheduled job can automatically delete branches matching `agent/**` older than N days after their PR is closed, without risk of touching human branches.

GitHub Copilot uses `copilot/` as its namespace. OpenAI Codex and similar systems use similar prefixes. This is becoming a de facto standard for distinguishing automated agent branches from human feature branches.

### 7.2 Sub-Namespacing

For organizations running multiple agent types, a sub-namespace adds another layer of isolation:

- `agent/qrspi/T-123-s2-a4f1b8` — QRSPI workflow agent
- `agent/review-bot/PR-456-a1b2c3` — automated review agent
- `agent/dependency-update/lodash-4.17.21` — dependency update agent

This allows rulesets and CI workflows to grant different permissions to different agent identities while maintaining a common `agent/**` namespace for general cleanup and monitoring.

---

## 8. GitHub Actions and CI/CD Identifier Patterns

### 8.1 Built-in Unique Identifiers in GitHub Actions

GitHub Actions provides several context variables relevant to unique branch naming:

| Variable | Description | Example |
|----------|-------------|---------|
| `github.run_id` | Unique integer per workflow run | `7890123456` |
| `github.run_number` | Sequential number per workflow in repo | `42` |
| `github.run_attempt` | Retry count for the run | `1` |
| `github.job` | Job ID within the workflow | `build-agent` |

A branch name constructed as `agent/T-123-s2-${{ github.run_id }}` is globally unique for the repository and has no collision risk even with hundreds of concurrent runs.

### 8.2 Concurrency Groups

GitHub Actions supports a `concurrency` key that can serialize workflows operating on the same branch:

```yaml
concurrency:
  group: agent-${{ github.event.inputs.ticket_id }}-${{ github.event.inputs.slice }}
  cancel-in-progress: false
```

This prevents two invocations for the same ticket/slice from running simultaneously without requiring unique branch names to resolve the conflict. However, it serializes rather than parallelizes, so it is better suited as a guardrail than as the primary uniqueness strategy.

### 8.3 Workflow Branch Filters and Agent Branch Security

A critical configuration concern: if you have workflows that trigger on `push` to any branch, an agent pushing to `agent/T-123-s2` will fire those workflows. Review every workflow's `on.push.branches` filter:

```yaml
on:
  push:
    branches:
      - main
      - 'release/**'
    branches-ignore:
      - 'agent/**'
```

The `branches-ignore: ['agent/**']` pattern prevents agent pushes from triggering workflows intended for human-authored code. Conversely, a dedicated CI workflow that only runs on `agent/**` branches can perform agent-specific checks (linting the generated code, running tests) with appropriately scoped secrets — typically read-only, not deployment credentials.

**Warning:** GitHub's `pull_request_target` event trigger runs with write permissions and access to secrets. Any workflow using `pull_request_target` must be reviewed to ensure it cannot be abused by an agent-opened PR. As of November 2025, GitHub changed `pull_request_target` to always use the default branch workflow definition, which mitigates the "zombie workflow" attack where an outdated vulnerable workflow on a non-default branch was exploited.

---

## 9. Practical Decision Matrix

| Scenario | Recommended Strategy |
|----------|---------------------|
| Single agent, single ticket | `agent/<ticket>-<slice>` (no run ID needed) |
| Multiple agents, same ticket, parallel slices | `agent/<ticket>-s<N>-<run-id>` |
| Retry of failed slice (clean) | Delete old branch, push to same `agent/<ticket>-s<N>` |
| Multiple agent types | `agent/<agent-type>/<ticket>-s<N>-<run-id>` |
| Audit trail required | Embed ticket + slice + run ID in all three components |
| Strict CI/CD isolation | `agent/**` branches-ignore in all human-targeted workflows |

---

## Sources

- [Dealing with special characters in branch and tag names - GitHub Docs](https://docs.github.com/en/get-started/using-git/dealing-with-special-characters-in-branch-and-tag-names)
- [Illegal Characters in Git References Like Branch and Tag Names - Baeldung on Ops](https://www.baeldung.com/ops/git-illegal-characters-ref-branch-tag)
- [git-check-ref-format Documentation - Git SCM](https://git-scm.com/docs/git-check-ref-format)
- [Managing a branch protection rule - GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [Creating rulesets for a repository - GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)
- [Available rules for rulesets - GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [About rulesets - GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [About protected branches - GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Control the concurrency of workflows and jobs - GitHub Docs](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs)
- [Variables reference - GitHub Docs](https://docs.github.com/en/actions/reference/workflows-and-actions/variables)
- [Contexts reference - GitHub Docs](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)
- [Copilot coding agent uses better branch names and pull request titles - GitHub Changelog](https://github.blog/changelog/2025-10-16-copilot-coding-agent-uses-better-branch-names-and-pull-request-titles/)
- [Customizing Branch Naming Convention in GitHub Copilot Agent - GitHub Community](https://github.com/orgs/community/discussions/173717)
- [Copilot PR Branch Naming Convention - GitHub Community](https://github.com/orgs/community/discussions/175103)
- [Keeping your GitHub Actions and workflows secure Part 1: Preventing pwn requests - GitHub Security Lab](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/)
- [Actions pull_request_target and environment branch protections changes - GitHub Changelog](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/)
- [Git push race condition? - git mailing list](https://git.vger.kernel.narkive.com/9Rkrrepp/push-race-condition)
- [Race condition between workflows that update gh-pages branch - GitHub](https://github.com/CQCL/tket/issues/63)
- [Agent Identity for Git Commits - DEV Community](https://dev.to/jpoehnelt/agent-identity-for-git-commits-53n1)
- [Each AI Agent Gets Its Own GitHub Identity - DEV Community](https://dev.to/agent_paaru/each-ai-agent-gets-its-own-github-identity-how-we-gave-every-bot-its-own-bot-commit-signature-1197)
- [Agent Platform Security Checklist - hi120ki](https://hi120ki.github.io/docs/ai-security/agent-platform-security-checklist/)
- [GitHub Rulesets - Microsoft Agent Package Manager](https://microsoft.github.io/apm/integrations/github-rulesets/)
- [Object Names and IDs - Kubernetes](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/)
- [Kubernetes generated names - zknill.io](https://zknill.io/posts/kubernetes-generated-names/)
- [Distributed UUID Generation System for Billion-Scale Traffic - Medium](https://dilipkumar.medium.com/design-a-system-to-generate-a-unique-id-1517dc624975)
- [Hardening GitHub Actions: Lessons from Recent Attacks - Wiz Blog](https://www.wiz.io/blog/github-actions-security-guide)
- [Understanding GitHub branch protection rules - Graphite](https://graphite.com/guides/github-branch-protection-rules)
- [Conductors to Orchestrators: The Future of Agentic Coding - O'Reilly](https://www.oreilly.com/radar/conductors-to-orchestrators-the-future-of-agentic-coding/)
- [Sandboxes for Coding Agents - Penligent](https://www.penligent.ai/hackinglabs/sandboxes-for-coding-agents/)
- [CI/CD Pipeline Security Best Practices - Wiz](https://www.wiz.io/academy/application-security/ci-cd-security-best-practices)
