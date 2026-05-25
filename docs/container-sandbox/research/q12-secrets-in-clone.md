# Q12: How Are Project Secrets (.env, Credentials) Handled in the Clone?

**Security Design Research — Container Sandbox for Agentic AI Tasks**

---

## Summary and Recommendations

When an agent performs a fresh shallow clone of a project repository, the working tree presents a distinct and underappreciated attack surface: any file that is **currently tracked by git** will appear verbatim in the clone, regardless of depth. Shallow cloning does not protect against secrets in the current HEAD commit; it only limits historical exposure.

The core risk is not history — it is the current working tree. A single `.env` file that was committed before `.gitignore` was configured, or a config file with embedded credentials that was never removed, will appear intact after `git clone --depth=1`.

### Recommended Controls (in priority order)

1. **Run a pre-flight secret scan of the clone before handing it to the agent.** Use `gitleaks dir` or `trufflehog filesystem` to scan the working tree for secrets in currently-checked-out files. Treat any finding as a gate: abort agent access until the owning team cleans the repo.

2. **Maintain a deny-list of sensitive path patterns for post-clone scrubbing.** After cloning and before agent access, delete or zero-out well-known sensitive file patterns (`.env`, `*.pem`, `credentials.*`, etc.). Document that this may break app config intentionally — the agent should not have live credentials.

3. **Do not treat `.gitignore` as a security boundary.** It only suppresses untracked files. It has no effect on already-tracked files and is completely bypassed by most AI agent file-reading tools.

4. **Adopt an `.agentignore` or `.uignore` file** in the repo to declare paths that agent tools should not read, independent of git tracking status. Enforce this at the sandbox level, not just in tooling.

5. **Inject credentials via environment variables or a secret broker at runtime**, scoped to the specific task. Never clone a repo that contains live credentials into the agent's working directory.

6. **AppArmor path-based deny rules are feasible but carry high operational overhead** — treat them as a defense-in-depth layer, not a primary control.

---

## Detailed Findings

### 1. What Appears in a Git Clone vs. What Is Excluded

A `git clone` (including `--depth=1`) materializes every file that is **tracked** in the target commit into the working tree. "Tracked" means the file was added with `git add` and committed at some point and has not been deleted in a subsequent commit.

Files that do **not** appear in the clone:

- **Untracked files**: Files that exist on the developer's machine but were never staged and committed.
- **Gitignored untracked files**: `.gitignore` entries prevent untracked files from being staged, but only if the file was never previously tracked.
- **Files deleted in earlier commits**: If a secret file was added and then removed in a later commit, it does not appear in the working tree of a `--depth=1` clone of the latest commit. However, it exists in the git object database and is accessible with `git log -p` on a full clone.

Critical nuance: `.gitignore` has **no retroactive effect**. If `.env` was tracked before `.gitignore` was updated to exclude it, it continues to appear in the working tree of every subsequent clone until it is explicitly deleted from the tree via `git rm`.

The `.git/` directory itself is present in all clones and may contain sensitive material: `~/.git/config` can contain embedded credentials (e.g., `https://user:token@github.com/...`), and `~/.git/hooks/` may contain arbitrary scripts.

**Sources**: [GitHub Docs — Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository), [Git sparse-checkout docs](https://git-scm.com/docs/git-sparse-checkout)

---

### 2. Shallow Clone (`--depth=1`) and the History Exposure Question

`git clone --depth=1` fetches only the most recent commit and its tree. This means:

- Secrets that were committed and then deleted in a later commit are **not present** in the working tree.
- The git object database in the shallow clone does not contain historical commits; `git log` shows only the one commit.
- However, secrets present in the **current HEAD commit** appear in full.

Depth-1 cloning is primarily a bandwidth and storage optimization. It is not a security mechanism. Secret scanning tools handle this explicitly: GitLab's pipeline secret detection fetches with `--unshallow` before running history scans, precisely because shallow clones hide historical exposure.

The risk this research question is concerned with — "what if secrets ARE currently tracked?" — is not mitigated by shallow cloning at all. Depth=1 only addresses historical secrets, not present ones.

**Sources**: [Understanding shallow clones — Graphite](https://graphite.com/guides/git-shallow-clone), [GitLab Pipeline Secret Detection](https://docs.gitlab.com/user/application_security/secret_detection/pipeline/)

---

### 3. Common Patterns of Accidentally-Tracked Secrets

GitGuardian's 2026 State of Secrets Sprawl report found **28.65 million hardcoded secrets** added to public GitHub in 2025 alone, a 34% increase year-over-year. Private repositories are **6x more likely** to contain hardcoded secrets than public ones. AI-assisted commits leak secrets at **3.2% rate — roughly 2x the baseline rate** for human-authored commits.

Common scenarios where secrets become tracked:

- **`.env` committed before `.gitignore` was configured.** Developer initializes a project, adds credentials to `.env`, commits, and only later adds `.env` to `.gitignore`. The file is already tracked and `.gitignore` has no effect.
- **Config files with inline credentials.** Database connection strings, SMTP passwords, or API keys embedded in `config/database.yml`, `application.properties`, or similar framework config files that are legitimately tracked.
- **Secrets committed during rapid prototyping.** A developer hardcodes a token to test a feature quickly, commits it to show progress, and forgets to remove it before merging.
- **Auto-generated secrets in bootstrapped projects.** Some frameworks generate secret keys (e.g., Django's `SECRET_KEY`, Rails' `config/master.key`) in files that are sometimes tracked by default in project templates.
- **CI/CD configuration files.** `.travis.yml`, `.circleci/config.yml`, or similar files that were edited to include inline credentials before encrypted variable support was adopted.

Even if the owning team believes all secrets are excluded, the current git history of most production repositories contains at least one accidentally-committed credential that was rotated but never removed from tracked files.

**Sources**: [Snyk — State of Secrets 2025](https://snyk.io/articles/state-of-secrets/), [GitGuardian State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/), [Pentera — Exposed Git Repos](https://pentera.io/blog/git-repo-security-exposed-secrets/)

---

### 4. Tools for Detecting Secrets in the Current Working Tree

Three tools are relevant for pre-flight scanning of the clone's working tree. The key distinction is scanning **current files** versus **git history**.

#### 4.1 Gitleaks

Gitleaks is the most widely deployed open-source secret scanner. It offers two modes relevant here:

- `gitleaks git [path]` — scans commit history via `git log -p`. **This scans history, not just current files.**
- `gitleaks dir [path]` (aliases: `files`, `directory`) — scans the filesystem directory directly, without invoking git. This is the correct command for scanning the current working tree after a clone.

Usage for pre-flight current-tree scan:
```bash
gitleaks dir /path/to/clone --report-format json --report-path findings.json
```

Known limitation: the older `--no-git` flag (v7 and earlier) caused Gitleaks to scan the `.git/` directory itself, producing false positives on git commit SHA strings. The `dir` subcommand in v8+ is the correct approach. Excluding the `.git/` directory explicitly avoids this issue.

Gitleaks ships with 150+ rules covering AWS keys, GitHub tokens, generic API key patterns, private key headers, and entropy-based detection.

**Sources**: [Gitleaks GitHub](https://github.com/gitleaks/gitleaks), [Gitleaks — no-git false positives issue](https://github.com/gitleaks/gitleaks/issues/474), [Jit — Developer's Guide to Gitleaks](https://www.jit.io/resources/appsec-tools/the-developers-guide-to-using-gitleaks-to-detect-hardcoded-secrets)

#### 4.2 TruffleHog

TruffleHog provides two commands with distinct scopes:

- `trufflehog git file://path/to/repo` — traverses full commit history, handles packfiles and loose objects. **Scans history.**
- `trufflehog filesystem /path/to/clone` — scans files present in the directory. **Scans current files only.**

The filesystem command struggles with git packfiles (compressed object storage) but correctly scans all regular files in the working tree. For the specific use case of scanning a fresh clone's current tree, `trufflehog filesystem` is appropriate. Note that after `git gc` runs, historical secrets in packfiles become invisible to the filesystem scanner — but in a freshly cloned ephemeral sandbox, `git gc` is unlikely to have run.

TruffleHog additionally verifies found credentials by making live API calls, reducing false positive rates compared to pattern-only tools.

**Sources**: [TruffleHog — Git vs Filesystem](https://trufflesecurity.com/blog/trufflehog-commands-git-vs-filesystem), [TruffleHog GitHub](https://github.com/trufflesecurity/trufflehog), [TruffleHog Filesystem Docs](https://docs.trufflesecurity.com/filesystem)

#### 4.3 detect-secrets (Yelp)

detect-secrets operates differently from Gitleaks and TruffleHog. Its primary model is **baseline-driven**:

1. Run `detect-secrets scan` to generate a `baseline.json` of all current secrets.
2. In CI/pre-commit, compare against the baseline — new secrets fail; known ones pass.

For a pre-flight check on an unfamiliar clone, detect-secrets is less immediately useful because there is no prior baseline. However, it can generate a scan result for triage:

```bash
detect-secrets scan /path/to/clone > findings.json
detect-secrets audit findings.json  # interactive review
```

By default, detect-secrets scans only git-tracked files. To scan all files in the directory (including untracked), pass `--all-files`.

detect-secrets ships 27 built-in detectors using regex, entropy analysis, and keyword matching. It does not natively perform credential verification.

**Sources**: [detect-secrets GitHub](https://github.com/Yelp/detect-secrets), [AppSecSanta — detect-secrets 2026](https://appsecsanta.com/detect-secrets)

#### 4.4 Recommended Pre-flight Workflow

```bash
# After git clone --depth=1 <repo> /sandbox/workdir
# Before handing to agent:

gitleaks dir /sandbox/workdir \
  --report-format json \
  --report-path /audit/gitleaks-findings.json \
  --exit-code 1  # non-zero exit if findings found

# If exit code is non-zero: abort, alert repo owners, do not proceed
```

Combine with TruffleHog for verified findings if false positive rate is a concern:
```bash
trufflehog filesystem /sandbox/workdir --json --only-verified 2>/dev/null
```

**Sources**: [Rafter — Secret Scanning Tools Comparison](https://rafter.so/blog/secrets/secret-scanning-tools-comparison), [Scanning Git for Secrets 2024 — Truffle Security](https://trufflesecurity.com/blog/scanning-git-for-secrets-the-2024-comprehensive-guide)

---

### 5. Post-Processing the Clone: Scrubbing Sensitive Paths

After cloning and before granting agent access, a scrubbing step can delete or redact well-known sensitive file patterns. This is a practical defense layer even if pre-flight scanning passes (scanners have false negative rates).

#### What to scrub

```bash
# Remove common secret-bearing files from the working tree
# (does NOT affect git history — files still exist in .git/objects)

CLONE_DIR=/sandbox/workdir

find "$CLONE_DIR" -maxdepth 3 -type f \( \
  -name ".env" \
  -o -name ".env.*" \
  -o -name "*.pem" \
  -o -name "*.key" \
  -o -name "*.p12" \
  -o -name "*.pfx" \
  -o -name "credentials.json" \
  -o -name "credentials.yml" \
  -o -name "secrets.json" \
  -o -name "secrets.yml" \
  -o -name "*.secret" \
  -o -name ".netrc" \
  -o -name "*.token" \
\) -delete

# Remove .git/config to strip any embedded credentials
# (agent doesn't need to push anyway)
rm -f "$CLONE_DIR/.git/config"
```

#### Risks and trade-offs

- **Breaks app configuration intentionally.** This is by design — the agent should not have live credentials. If the agent needs to connect to a database, credentials must be injected via environment variables or a secret broker, not sourced from files in the working tree.
- **Pattern-based scrubbing has gaps.** A credential file named `db_config.yaml` or `production.json` will not match the patterns above. Supplement with scanner findings to expand the deny-list per-repo.
- **`.git/objects` still contains tracked file contents.** Removing files from the working tree does not remove them from the `.git/` object database. An agent with shell access can run `git show HEAD:.env` to recover a scrubbed file if it knows the path. Mitigate by either deleting the `.git/` directory entirely (converts to a non-repo) or mounting the working tree read-only over a tmpfs with the sensitive paths excluded.
- **Deleting `.git/` breaks version control context.** The agent loses `git log`, `git diff`, and other operations. Evaluate whether this is acceptable for the task type.

#### Alternative: git sparse-checkout with exclusions

`git sparse-checkout` with the non-cone mode supports exclusion patterns (`!.env`). This prevents sensitive files from being written to the working tree at clone time:

```bash
git clone --depth=1 --no-checkout <repo> /sandbox/workdir
cd /sandbox/workdir
git sparse-checkout init --no-cone
git sparse-checkout set '/*' '!.env' '!*.pem' '!*.key' '!credentials.*'
git checkout
```

This is cleaner than post-hoc deletion but requires knowing the patterns in advance and does not prevent recovery via `git show HEAD:<path>`.

**Sources**: [GitHub Docs — Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository), [git-sparse-checkout docs](https://git-scm.com/docs/git-sparse-checkout)

---

### 6. AppArmor / SELinux Deny Rules on Specific Paths

#### Feasibility

AppArmor uses a path-based access control model that is well-suited to denying access to specific files within a working directory. A profile can include:

```
deny /sandbox/workdir/.env r,
deny /sandbox/workdir/*.pem r,
deny /sandbox/workdir/credentials.* r,
```

AppArmor deny rules take precedence over allow rules. Even if the sandboxed process runs as root, AppArmor will block the read. Datadog's container security research confirms this: in a hardened container, deny rules on `/etc/**` blocked root-level write attempts.

SELinux uses a label-based model rather than path-based, which makes it harder to target specific files within an application's working directory without labeling those files specially during setup.

#### Operational overhead

The Datadog assessment is direct: "customizing MAC systems to work with containers at scale is a significant undertaking." For each repository an agent accesses, the AppArmor profile would need to encode the specific paths being protected. This requires:

- Per-repo or per-task profile generation (not static)
- Loading profiles into the host kernel before container start
- Maintaining profile correctness as repo structure evolves
- Testing profiles to avoid blocking legitimate agent operations

At scale — multiple agents, multiple repos, dynamic path structures — this becomes an operational burden that outweighs the marginal security benefit over simpler scrubbing and scanning controls.

**Verdict**: AppArmor path deny rules are technically valid as a defense-in-depth layer for a small set of well-known high-value paths (e.g., `deny /sandbox/workdir/.env r`). They are not practical as a primary control or as a general-purpose secret-protection mechanism.

**Sources**: [Datadog Security Labs — AppArmor and SELinux](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-5/), [AppArmor ArchWiki](https://wiki.archlinux.org/title/AppArmor), [TuxCare — SELinux vs AppArmor](https://tuxcare.com/blog/selinux-vs-apparmor/)

---

### 7. The `.gitignore`-as-Security-Boundary Problem

`.gitignore` is a convenience tool for preventing untracked files from being accidentally staged. It is not a security mechanism, and treating it as one is a documented, prevalent failure mode.

Specific limitations:

1. **No effect on already-tracked files.** If `.env` was ever committed, `.gitignore` has no effect until `git rm --cached .env` is explicitly run and committed.
2. **Bypassed entirely by AI agent read tools.** The OpenCode issue #12196 (filed February 2026) documents that AI agent `read` tools use absolute paths and do not respect `.gitignore` patterns, even when other tools in the same agent (`glob`, `grep`) do. Claude Code's architecture confirms this: filesystem isolation is enforced at the OS level via bubblewrap/seatbelt, not via gitignore parsing.
3. **No enforcement mechanism.** `.gitignore` is a text file with no cryptographic enforcement. Any process with filesystem access can read gitignored files; only OS-level permissions or MAC policies constrain this.
4. **False security signal for operators.** A repository owner who sees `.env` in `.gitignore` may assume the file is absent from clones and from agent context — both assumptions can be wrong.

The gitignore-as-security-boundary failure is well-documented in recent security literature as contributing directly to AI-assisted secret leaks. GitGuardian's finding that AI-assisted commits leak at 2x the baseline rate partly reflects agents reading sensitive files they were expected not to see.

**Sources**: [Mitigating Secret Leaks — earezki.com](https://earezki.com/ai-news/2026-04-11-oops-i-leaked-secrets-gitguardian-warned-me-/), [.gitignore Won't Save Your Secrets — AI Mindset](https://medium.com/ai-mindset/gitignore-wont-save-your-secrets-from-ai-coding-agents-35dddf892061), [OpenCode security issue #12196](https://github.com/anomalyco/opencode/issues/12196)

---

### 8. Best Practices for Repos That Contain Agents

Repositories that will be cloned into agent sandboxes warrant a hardened `.gitignore` and complementary files. The following patterns should be default entries:

#### Recommended `.gitignore` additions for agent-accessible repos

```gitignore
# Secret and credential files
.env
.env.*
!.env.example
!.env.sample
*.pem
*.key
*.p12
*.pfx
*.jks
credentials.json
credentials.yml
credentials.yaml
secrets.json
secrets.yml
secrets.yaml
*.secret
.netrc
*.token
.vault-token
kubeconfig
*.kubeconfig

# Cloud provider credentials
.aws/credentials
.aws/config
.gcp/
gcloud/
.azure/

# Framework-generated secrets
config/master.key
config/credentials.yml.enc
```

#### `.agentignore` / `.uignore` (emerging standard)

Beyond `.gitignore`, repos should include an `.agentignore` file (same syntax) that controls what AI agent tools are permitted to read, regardless of git tracking status. Supported by Cursor, Claude Code, Gemini CLI, and Windsurf as of 2025/2026:

```
# .agentignore
.env*
*.pem
*.key
credentials.*
secrets.*
.git/config
.aws/
.ssh/
```

The `.uignore` format (a superset) aims to be universally respected across all AI coding tools. Teams using multiple AI assistants should maintain a canonical list and generate tool-specific ignore files from it.

**Sources**: [Agent Ignore Files — ai-config](https://s-celles.github.io/ai-config/docs/agentignore/), [AI Ignore Rules — appga.pl](https://appga.pl/2025/11/22/ai-ignore-rules-protect-your-secrets-when-using-code-assistants/), [agentignore GitHub](https://github.com/tourcoder/agentignore), [uignore — DEV Community](https://dev.to/geekfarmer/uignore-a-gitignore-for-ai-coding-tools-3h7)

---

### 9. Auditing a Repo for Currently-Tracked Secrets Before Allowing Agent Access

Before admitting a repository to the agent sandbox pool, a one-time audit should verify that no live secrets are currently tracked. This is distinct from ongoing pre-flight scans (which happen per-clone) — this is a repo admission gate.

#### Audit procedure

```bash
# Step 1: Clone fully (not shallow) to enable history scanning
git clone https://github.com/org/repo /tmp/audit-clone

# Step 2: Scan current working tree (tracked files only)
gitleaks dir /tmp/audit-clone \
  --report-format json \
  --report-path /tmp/audit-current-tree.json

# Step 3: Scan full git history
gitleaks git /tmp/audit-clone \
  --report-format json \
  --report-path /tmp/audit-history.json

# Step 4: Cross-reference: are any history findings still live in HEAD?
# (manual review of audit-history.json vs audit-current-tree.json)

# Step 5: Verify no files that should be gitignored are tracked
git -C /tmp/audit-clone ls-files | grep -E '\.(env|pem|key|p12|pfx|secret)$'
```

#### Using `git ls-files` as a lightweight check

`git ls-files` lists all currently tracked files. Running it through a pattern filter is a fast, dependency-free way to catch obvious violations before invoking a full scanner:

```bash
git ls-files | grep -iE \
  '(\.env$|\.env\.|credentials|secrets|password|passwd|\.pem$|\.key$|\.p12$|\.pfx$|\.token$|api[_-]?key)'
```

Any match is a finding that warrants manual review or automated rejection.

#### Continuous monitoring

Repos admitted to the agent pool should be re-scanned on each new commit (via GitHub Advanced Security, GitGuardian, or gitleaks as a CI step) to catch newly tracked secrets before they reach production agent deployments.

**Sources**: [AWS Prescriptive Guidance — git-secrets scan](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/scan-git-repositories-for-sensitive-information-and-security-issues-by-using-git-secrets.html), [GitHub Secret Scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning), [Gitleaks GitHub](https://github.com/gitleaks/gitleaks)

---

### 10. Anthropic's Approach: Credential Isolation in Claude Code Sandboxing

Anthropic's published architecture for Claude Code on the web provides a reference implementation for the exact problem described:

- **Credentials are never placed inside the sandbox.** Git credentials and signing keys are kept outside the agent environment. A custom proxy service handles all git interactions transparently with scoped credentials injected at the proxy layer, not in the working directory.
- **Filesystem isolation** is enforced via OS primitives (Linux bubblewrap, macOS seatbelt), restricting the agent to its designated working directory. This operates at the syscall level, not via `.gitignore` parsing.
- **Network isolation** prevents exfiltration of any secrets the agent might encounter in the working tree.

This architecture treats the working tree as untrusted and credentials as infrastructure-layer concerns, not file-system concerns. It is the recommended model for a container sandbox design.

**Sources**: [Making Claude Code More Secure — Anthropic Engineering](https://www.anthropic.com/engineering/claude-code-sandboxing)

---

## Sources

- [How to Safely Remove Secrets from Git History — Microsoft Tech Community](https://techcommunity.microsoft.com/blog/azureinfrastructureblog/how-to-safely-remove-secrets-from-your-git-history-the-right-way/4464722)
- [Why 28 Million Credentials Leaked on GitHub in 2025 — Snyk](https://snyk.io/articles/state-of-secrets/)
- [The State of Secrets Sprawl 2026 — GitGuardian](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/)
- [The State of Secrets Sprawl 2025 — GitGuardian](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2025/)
- [Removing Sensitive Data from a Repository — GitHub Docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [GIT — Prevent Accidentally Pushing Credentials — DEV Community](https://dev.to/andreasaugustin/git-pretend-accidentally-pushing-git-credentials-11hh)
- [Exposed Git Repos: The Overlooked Threat to DevOps Security — Pentera](https://pentera.io/blog/git-repo-security-exposed-secrets/)
- [Gitleaks GitHub Repository](https://github.com/gitleaks/gitleaks)
- [Gitleaks — no-git false positives issue #474](https://github.com/gitleaks/gitleaks/issues/474)
- [The Developer's Guide to Using Gitleaks — Jit](https://www.jit.io/resources/appsec-tools/the-developers-guide-to-using-gitleaks-to-detect-hardcoded-secrets)
- [TruffleHog vs. Gitleaks — Jit](https://www.jit.io/resources/appsec-tools/trufflehog-vs-gitleaks-a-detailed-comparison-of-secret-scanning-tools)
- [TruffleHog GitHub Repository](https://github.com/trufflesecurity/trufflehog)
- [TruffleHog Commands: Git vs Filesystem — Truffle Security](https://trufflesecurity.com/blog/trufflehog-commands-git-vs-filesystem)
- [TruffleHog Filesystem Documentation](https://docs.trufflesecurity.com/filesystem)
- [Scanning Git for Secrets: The 2024 Comprehensive Guide — Truffle Security](https://trufflesecurity.com/blog/scanning-git-for-secrets-the-2024-comprehensive-guide)
- [detect-secrets GitHub Repository — Yelp](https://github.com/Yelp/detect-secrets)
- [detect-secrets 2026 — AppSecSanta](https://appsecsanta.com/detect-secrets)
- [Secret Scanning Tools Comparison — Rafter](https://rafter.so/blog/secrets/secret-scanning-tools-comparison)
- [Mitigating Secret Leaks: Why .gitignore is Not a Security Strategy — earezki.com](https://earezki.com/ai-news/2026-04-11-oops-i-leaked-secrets-gitguardian-warned-me-/)
- [.gitignore Won't Save Your Secrets from AI Coding Agents — AI Mindset / Medium](https://medium.com/ai-mindset/gitignore-wont-save-your-secrets-from-ai-coding-agents-35dddf892061)
- [Security: Read Tool Bypasses .gitignore Patterns — OpenCode Issue #12196](https://github.com/anomalyco/opencode/issues/12196)
- [Making Claude Code More Secure and Autonomous — Anthropic Engineering](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Practical Security Guidance for Sandboxing Agentic Workflows — NVIDIA Technical Blog](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)
- [How to Sandbox AI Agents in 2026 — Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Secure AI Agents at Runtime with Docker — Docker Blog](https://www.docker.com/blog/secure-ai-agents-runtime-security/)
- [Container Security Fundamentals Part 5: AppArmor and SELinux — Datadog Security Labs](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-5/)
- [AppArmor — ArchWiki](https://wiki.archlinux.org/title/AppArmor)
- [SELinux vs AppArmor — TuxCare](https://tuxcare.com/blog/selinux-vs-apparmor/)
- [Understanding Shallow Clones in Git — Graphite](https://graphite.com/guides/git-shallow-clone)
- [Get Up to Speed with Partial Clone and Shallow Clone — GitHub Blog](https://github.blog/open-source/git/get-up-to-speed-with-partial-clone-and-shallow-clone/)
- [Pipeline Secret Detection — GitLab Docs](https://docs.gitlab.com/user/application_security/secret_detection/pipeline/)
- [Git sparse-checkout Documentation](https://git-scm.com/docs/git-sparse-checkout)
- [Agent Ignore Files — AI Config](https://s-celles.github.io/ai-config/docs/agentignore/)
- [AI Ignore Rules: Protect Your Secrets When Using Code Assistants — appga.pl](https://appga.pl/2025/11/22/ai-ignore-rules-protect-your-secrets-when-using-code-assistants/)
- [agentignore GitHub Repository](https://github.com/tourcoder/agentignore)
- [uignore — A .gitignore for AI Coding Tools — DEV Community](https://dev.to/geekfarmer/uignore-a-gitignore-for-ai-coding-tools-3h7)
- [Claude Code Ignores Ignore Rules Meant to Block Secrets — The Register](https://www.theregister.com/2026/01/28/claude_code_ai_secrets_files/)
- [AWS Prescriptive Guidance — Scan Git Repositories with git-secrets](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/scan-git-repositories-for-sensitive-information-and-security-issues-by-using-git-secrets.html)
- [About Secret Scanning — GitHub Docs](https://docs.github.com/code-security/secret-scanning/about-secret-scanning)
- [How to Implement Secret Scanning with Gitleaks — OneUptime Blog](https://oneuptime.com/blog/post/2026-01-25-secret-scanning-gitleaks/view)
- [Is Your Repo Ready for the AI Agents Revolution? — Medium](https://domizajac.medium.com/is-your-repo-ready-for-the-ai-agents-revolution-926e548da528)
