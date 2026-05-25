# Q13: Should Sensitive Files Be Explicitly Access-Blocked Even If Present in the Clone?

## Summary and Recommendation

**Recommendation: Prefer pre-clone scrubbing over runtime MAC-based blocking, but add a lightweight AppArmor deny layer as defense-in-depth if your threat model demands it.**

The core question is whether AppArmor or SELinux rules that deny reads to `*.env`, `*credentials*`, and `*.pem` files inside the agent's working directory are worth the added complexity. The answer is nuanced:

- **MAC does override DAC**: AppArmor and SELinux can deny a process read access to files it owns, and this works reliably for static, known paths. Mandatory Access Control (MAC) is enforced by the kernel and cannot be overridden by the process regardless of Unix ownership.
- **Glob-pattern blocking is workable but imperfect**: AppArmor's `**` glob can match `*.env` recursively across nested directories (e.g., `deny /workspace/**/.env r,`), but matching arbitrary filename *substrings* like `*credentials*` requires careful rule crafting and has edge cases.
- **Symlinks create bypass surface**: Because AppArmor resolves symlinks to their target path before checking rules, an agent that creates a symlink pointing to a blocked file from an allowed path can potentially bypass the restriction. Hardlinks create a similar bypass.
- **Pre-clone scrubbing is simpler and more reliable**: Removing or replacing sensitive files before handing the repository to the agent eliminates the need for runtime rules and avoids the complexity and bypass surface entirely.
- **Marginal security value depends on the broader stack**: If git credentials are already scoped (read-only, short-lived) and network egress is filtered, the main remaining threat is the agent reading secrets and exfiltrating them via an allowed channel. MAC file blocking addresses this only if exfiltration itself is prevented elsewhere.

**Bottom line**: For a container sandbox where the agent has write access to its working directory, implement pre-clone scrubbing as the primary control and add `deny /workspace/**/.env r,` style AppArmor rules as a defense-in-depth layer. Do not rely on MAC file blocking as the *sole* control for credential protection.

---

## Detailed Findings

### 1. AppArmor File Rules: Writing Deny Rules for Glob Patterns

AppArmor uses AARE (AppArmor Regular Expressions) for file path matching. The relevant glob operators are:

- `*` — matches any number of characters *excluding* `/`
- `**` — matches any number of characters *including* `/`
- `?` — matches exactly one character (excluding `/`)
- `{a,b}` — alternation

For denying `*.env` files recursively within a working directory, the correct syntax is:

```
deny /workspace/**/.env r,
```

The `**` matches any intermediate path segments, so this covers `/workspace/.env`, `/workspace/subdir/.env`, and `/workspace/deep/nested/.env`. A bare `*.env` pattern (without a leading path component) would only match in the profile's current path context and would not recurse.

For name-substring patterns like `*credentials*`:

```
deny /workspace/**/*credentials* r,
```

This works but has a subtle limitation: `*` in the filename position does not cross directory separators, so `/workspace/secrets/credentials.json` is caught by `/workspace/**/*credentials*` only if the `**` portion matches `secrets/` and the `*credentials*` portion matches `credentials.json`. This interaction is correct per the AppArmor spec, but complex patterns require careful testing with `apparmor_parser` and audit logging.

**Deny rule precedence**: Deny rules have higher precedence than allow rules. A `deny` qualifier explicitly blocks access and cannot be overridden by a subsequent `allow` rule in the same profile. Deny rules are also enforced in `complain` mode (they do not merely log; they still block).

Sources: [Ubuntu AppArmor manpage](https://manpages.ubuntu.com/manpages/xenial/man5/apparmor.d.5.html), [Debian AppArmor manpage](https://manpages.debian.org/unstable/apparmor/apparmor.d.5.en.html), [SUSE AppArmor Profile Syntax](https://doc.opensuse.org/documentation/leap/security/html/book-security/cha-apparmor-profiles.html)

---

### 2. SELinux File Context Rules: Labeling for Fine-Grained Restrictions

SELinux uses a label-based model rather than AppArmor's path-based model. Every file and process has a security context of the form `user:role:type:level`. Access decisions are made based on the *type* field (type enforcement) and optional MCS category labels.

**Restricting specific files within a container working directory** using SELinux requires:

1. Assigning a custom SELinux type to the sensitive files (e.g., `secret_file_t`)
2. Writing a policy module that denies the container process domain (`container_t` or a custom type) read access to `secret_file_t`
3. Applying the label with `chcon` or `semanage fcontext` + `restorecon`

Example label application:
```bash
chcon -t secret_file_t /workspace/.env
chcon -t secret_file_t /workspace/credentials.json
```

The policy module would include:
```
# Deny container_t from reading secret_file_t
neverallow container_t secret_file_t:file { read open };
```

Tools like **udica** can generate baseline container SELinux policies from a container's JSON configuration, which can then be extended with custom type restrictions.

**Practical limitation**: SELinux labeling is file-by-file, not pattern-based at the policy level. You cannot write an SELinux rule that says "all files named `*.env`." Instead, you must explicitly label individual files or directories, then have a policy for those labels. This makes SELinux *more* precise than AppArmor for known sensitive files, but *less* amenable to catching dynamically-named credential files.

Sources: [Red Hat SELinux File Contexts](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/selinux_users_and_administrators_guide/sect-security-enhanced_linux-working_with_selinux-selinux_contexts_labeling_files), [Red Hat Creating SELinux Policies for Containers](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/using_selinux/creating-selinux-policies-for-containers_using-selinux), [Datadog Container Security Fundamentals Part 5](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-5/), [How SELinux separates containers using MLS](https://www.redhat.com/en/blog/how-selinux-separates-containers-using-multi-level-security)

---

### 3. The Ownership Problem: MAC Overrides DAC

This is the most important property: **Mandatory Access Control operates independently of and above Discretionary Access Control.**

When a process runs as a user who owns a file, Unix DAC would normally permit that process to read the file. AppArmor (and SELinux) operate at the LSM (Linux Security Module) hook layer in the kernel. The kernel checks DAC *first*, then passes the decision to LSMs. However, because AppArmor can only *restrict* permissions (it cannot grant more than DAC allows), a `deny` rule in an AppArmor profile will block access even if DAC would permit it.

Practical demonstration (from Datadog Security Labs research): A root process inside a container with the rule `deny /etc/** wl` cannot write to `/etc/` despite running as root. The deny rule is absolute — the user "may not be able to modify the constraints that are placed on the resources they own."

The AppArmor `owner` qualifier adds a conditional: `owner /workspace/**/.env r,` would grant read access *only* when the process's effective UID matches the file's UID. Conversely, `deny owner /workspace/**/.env r,` would deny read access specifically to the owning user, while potentially allowing others (a more exotic use case). For our scenario — blocking the agent process from reading files in its own working directory — a plain `deny /workspace/**/.env r,` (without the `owner` qualifier) is correct and sufficient.

Sources: [Datadog Container Security Fundamentals Part 5](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-5/), [Beyond DAC: Why SELinux and AppArmor Are Essential](https://dohost.us/index.php/2025/10/05/beyond-dac-why-selinux-and-apparmor-are-essential-for-modern-linux-security/), [AppArmor Wikipedia](https://en.wikipedia.org/wiki/AppArmor), [AppArmor DAC override discussion](https://apparmor.narkive.com/EJZiNK1H/dac-override-questions)

---

### 4. Practical Limitations: Reliability of Pattern Matching

#### AppArmor

**What works reliably:**
- Exact paths: `deny /workspace/.env r,`
- Directory-scoped globs: `deny /workspace/**/.env r,` (all `.env` files recursively)
- Extension patterns: `deny /workspace/**.pem r,` (all `.pem` files at any depth)

**What is tricky:**
- Substring filename matching: `deny /workspace/**/*credentials* r,` works syntactically but requires validation that the `*` in the filename position does not accidentally match path separators in unexpected combinations
- Files without extensions: `deny /workspace/**/id_rsa r,` is fine, but enumerating all possible credential file names is an ongoing maintenance burden
- Dynamically-named credential files (e.g., `token-$(date +%s)`) cannot be caught by static patterns

**Nested path coverage**: Using `**` in an AppArmor path rule does cover arbitrarily nested subdirectories. A rule like `deny /workspace/**/*.pem r,` will match `/workspace/certs/server.pem`, `/workspace/a/b/c/key.pem`, etc.

#### SELinux

SELinux file context rules use extended regular expressions (ERE) for path matching in the `fcontext` database:

```bash
semanage fcontext -a -t secret_file_t '/workspace(/.*)*/\.env'
```

This labels all `.env` files under `/workspace` as `secret_file_t`. The ERE syntax is more expressive than AppArmor's glob for certain patterns (e.g., `/workspace(/.*)*/.env` for nested `.env` files), but it still operates on filesystem paths, not arbitrary name patterns.

**Critical limitation for both**: Neither AppArmor nor SELinux can block access to a file based solely on its *content* (e.g., "this file looks like it contains an API key"). They work on path and type labels only.

Sources: [Ubuntu AppArmor manpage](https://manpages.ubuntu.com/manpages/xenial/man5/apparmor.d.5.html), [Red Hat SELinux File Contexts](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/selinux_users_and_administrators_guide/sect-security-enhanced_linux-working_with_selinux-selinux_contexts_labeling_files)

---

### 5. Symlink Attack Surface

This is a meaningful bypass risk that warrants careful consideration.

#### How AppArmor Handles Symlinks

AppArmor's behavior with symlinks is determined by the kernel. There are two competing accounts in the literature, and this ambiguity itself is a risk:

- The AppArmor documentation and kernel LSM hooks indicate that the kernel resolves symlinks before querying security modules. This means AppArmor checks the **resolved target path**, not the symlink's own path.
- The Launchpad bug #1485055 discussion (Seth Arnold, AppArmor maintainer) states this is a consequence of kernel internals and cannot be changed.

**Security implication**: If AppArmor evaluates the *target* path of a symlink, then:
- An agent creates `/workspace/safe_file.txt` as a symlink pointing to `/workspace/.env`
- The agent reads `/workspace/safe_file.txt`
- AppArmor resolves the symlink and checks permissions on `/workspace/.env`
- The deny rule `deny /workspace/**/.env r,` catches this — the agent is blocked

This is the *desirable* behavior. However, the inverse risk exists:
- If an agent creates `/workspace/.env.bak` as a symlink to `/workspace/.env`, and the deny rule only covers `**/.env`, the `.env.bak` symlink resolves to `/workspace/.env`, which *is* caught by the rule
- But if the agent creates `/workspace/reading_env` (no `.env` extension) as a symlink to `/workspace/.env`, and the deny rule is `**/.env`, AppArmor checks the target `/workspace/.env` — which is still blocked

The real risk scenario is the **reverse**: an agent creates a symlink from the *allowed* namespace to a *blocked* file. Because AppArmor resolves to the target, the block on the target still applies. This is actually protective.

#### Hardlink Bypass

Hardlinks are a different and more serious concern. A hardlink to a file is a second directory entry pointing to the same inode. AppArmor rules match on *path names*, not inodes. If an agent creates a hardlink at `/workspace/notasecret` pointing to the same inode as `/workspace/.env`, and the deny rule only covers paths matching `**/.env`, the hardlink path `/workspace/notasecret` does not match the pattern — the block fails.

**Mitigation**: Enable `fs.protected_hardlinks=1` (default on modern Linux and Ubuntu). This kernel sysctl prevents users from creating hardlinks to files they do not own. Since in our scenario the agent *does* own the files in the working directory (they were cloned under the agent's UID), this protection does not fully apply — the agent can still create hardlinks to its own files.

A deeper mitigation is to deny the `l` (link) permission in the AppArmor rule: `deny /workspace/**/.env rl,` — this prevents both reading and linking (hardlinking). Combined with a network and process namespace that prevents the hardlink from being exposed outside the sandbox, this significantly reduces the bypass surface.

**CVE-2023-28642** (runc AppArmor bypass via symlinked `/proc`) is a related case study: symlink manipulation combined with mount configuration allowed AppArmor bypass. This was fixed in runc v1.1.5 by moving symlink checks before path resolution.

Sources: [AppArmor/SELinux bypass with symlinked /proc (GHSA-g2j6-57v7-gm8c)](https://github.com/opencontainers/runc/security/advisories/GHSA-g2j6-57v7-gm8c), [CVE-2023-28642 Miggo](https://www.miggo.io/vulnerability-database/cve/CVE-2023-28642), [AppArmor symlink support bug](https://bugs.launchpad.net/apparmor/+bug/1485055), [AppArmor hardlink question](https://apparmor.narkive.com/aBSP5Lc8/profile-name-and-hard-link-question), [fs.protected_hardlinks sysctl](https://sysctl-explorer.net/fs/protected_hardlinks/)

---

### 6. Alternative Approach: Pre-Clone Scrubbing

Instead of blocking file reads at runtime with MAC, sensitive files can be removed or replaced *before* the agent ever sees the repository. This is the approach Anthropic uses in Claude Code's cloud sandbox: "sensitive credentials are never inside the sandbox with Claude Code."

**Scrubbing strategies:**

1. **Delete known sensitive files**: After cloning, scan for `*.env`, `*.pem`, `**/id_rsa`, `**/credentials.json`, etc. and delete them before mounting the workspace into the container.

2. **Replace with stubs**: Replace `.env` with a file containing only placeholder values (`API_KEY=REDACTED`). This allows the agent to understand the project's configuration structure without exposing actual credentials.

3. **Content-based secret scanning**: Run gitleaks or TruffleHog against the clone before handing it to the agent. Flag or remove files that contain patterns matching known secret formats (API keys, tokens, PEM blocks). Tools like gitleaks use hundreds of regex patterns and can detect secrets embedded in files regardless of filename.

4. **Git history scrubbing**: If the agent has access to `git log` or `git show`, secrets in historical commits are exposed even if the working tree is clean. For agent sandboxes, consider shallow clones (`--depth=1`) or git history scrubbing with `git-filter-repo`.

**Advantages over runtime MAC:**
- No bypass surface: once deleted, the file cannot be accessed via symlinks, hardlinks, or alternative paths
- No ongoing maintenance of deny-rule lists as new credential filename patterns emerge
- Simpler audit: absence of file is easier to verify than MAC rule coverage
- Works regardless of what the agent's container runtime supports (no AppArmor/SELinux dependency)

**Disadvantages:**
- Requires a pre-processing pipeline step on every clone
- Some files the agent legitimately needs may be incorrectly scrubbed (false positives)
- Does not protect credentials that the agent *generates* during its task (e.g., it creates a new `.env` file mid-task)

Sources: [Anthropic Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing), [Gitleaks vs TruffleHog comparison](https://appsecsanta.com/sast-tools/gitleaks-vs-trufflehog), [GitHub: Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

### 7. Docker Seccomp and AppArmor Interaction

Docker applies two independent security layers to containers by default:

- **AppArmor** (`docker-default` profile): Loaded from tmpfs into the kernel at container start. Controls file, network, and capability access by path and permission type. Applied as `--security-opt apparmor=docker-default` unless overridden.

- **Seccomp** (default profile): Blocks approximately 44 of 300+ system calls that are known dangerous. Controls *which syscalls* the container process can invoke.

These two mechanisms operate at different levels and are complementary:
- AppArmor controls *what resources* a process can access (files, network, capabilities)
- Seccomp controls *what kernel interfaces* a process can invoke

**For file blocking specifically**: AppArmor is the right tool. Seccomp cannot selectively block reads on specific files — it operates at the syscall level and can only block `open(2)`, `read(2)`, etc. entirely, not conditionally based on the file path argument.

**Custom profiles for containers**: To enforce file pattern denials, you must write a custom AppArmor profile and apply it with `--security-opt apparmor=custom-agent-profile`. The Docker default profile does not include any file-level denials for the working directory.

Example custom profile skeleton for an agent sandbox:

```
#include <tunables/global>
profile agent-sandbox flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>

  # Allow full access to workspace
  /workspace/** rwkl,

  # Deny reads on sensitive file patterns within workspace
  deny /workspace/**/.env r,
  deny /workspace/**/.env.* r,
  deny /workspace/**/*credentials* r,
  deny /workspace/**/*.pem r,
  deny /workspace/**/*.key r,
  deny /workspace/**/id_rsa r,
  deny /workspace/**/id_ed25519 r,

  # Deny hardlinking sensitive files
  deny /workspace/**/.env l,
  deny /workspace/**/*.pem l,
  deny /workspace/**/*.key l,

  # Standard container restrictions
  deny @{PROC}/* w,
  deny @{PROC}/{[^1-9],[^1-9][^0-9],...} w,
  deny mount,
  deny /sys/[^f]*/** wklx,
}
```

Sources: [Docker AppArmor documentation](https://docs.docker.com/engine/security/apparmor/), [Docker Seccomp documentation](https://docs.docker.com/engine/security/seccomp/), [Understanding Seccomp vs AppArmor](https://medium.com/@mughal.asim/understanding-seccomp-and-how-it-compares-to-apparmor-for-container-security-5317b3e9b1d6), [Kubernetes AppArmor tutorial](https://kubernetes.io/docs/tutorials/security/apparmor/)

---

### 8. Is the Complexity Justified? Marginal Security Value Analysis

The value of MAC-based file blocking depends entirely on what other controls are in place.

#### Scenario: Well-hardened sandbox (scoped credentials + network filtering)

If:
- The agent's git credential is read-only and scoped to a single repository
- Network egress is filtered to a blocklist/allowlist preventing arbitrary HTTP exfiltration
- The agent cannot spawn outbound connections outside approved domains

Then the attack chain for credential theft is: agent reads `.env` → agent attempts to exfiltrate via network → **blocked by egress filter**.

In this scenario, MAC file blocking provides defense-in-depth but is not load-bearing. The marginal value is protection against:
- A compromised egress filter
- An approved outbound channel that can carry exfiltrated data (e.g., a whitelisted API that accepts arbitrary payloads)
- The agent encoding secrets into its output artifacts (files committed to the repo, PR descriptions, etc.)

NVIDIA's AI Red Team explicitly recommends blocking reads from sensitive paths even in otherwise-hardened sandboxes, specifically as a defense against indirect prompt injection causing the agent to include secrets in its output.

#### Scenario: Minimal sandbox (agent is mostly trusted)

If the agent is expected to work legitimately with environment configuration, MAC file blocking becomes a usability obstacle that may need to be relaxed, reducing its value.

#### The Claude Code precedent

Anthropic's own implementation avoids the problem entirely by ensuring "sensitive credentials are never inside the sandbox." A git proxy handles authentication, so there is no `.env` file with a real token for the agent to find. This is the cleanest solution: the sensitive file simply does not exist in the agent's filesystem.

The Knostic.ai research documented that Claude Code automatically reads `.env` files from project directories without explicit user permission — demonstrating that an unguarded AI agent will access credential files opportunistically, even without malicious intent.

Sources: [NVIDIA Practical Security Guidance for Sandboxing Agentic Workflows](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/), [Anthropic Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing), [Knostic: Claude Code Loads Secrets Without Permission](https://www.knostic.ai/blog/claude-loads-secrets-without-permission), [Defense in Depth for AI Code Execution Agents](https://dev.to/ksankar/defense-in-depth-tenant-isolation-for-an-agent-that-executes-code-375j), [Swiss Cheese Model for AI Agent Security](https://www.apistronghold.com/blog/swiss-cheese-model-ai-agent-security)

---

### 9. Real-World AppArmor Profiles for Container Workloads

Production container AppArmor profiles typically use deny rules for system-level paths rather than application-level file patterns. Examples from real deployments:

**Docker's default profile (`docker-default`)**: Does not deny any file paths within the container's working directory. Focuses on denying sensitive system paths (`/proc/sysrq-trigger`, `/proc/kcore`, etc.) and capabilities.

**Nginx example profile (from Docker docs)**:
```
deny /bin/** wl,
deny /boot/** rwklx,
deny /dev/** rwklx,
deny /etc/** rwklx,
```

**Kubernetes deny-write example**:
```
deny /** wl,
```

**Production hardened profile patterns**:
```
deny /etc/shadow r,
deny /root/** rw,
deny /tmp/** x,
deny mount,
deny network raw,
deny ptrace,
```

None of these production examples include application-specific file extension patterns like `*.env` or `*.pem` — this kind of application-layer credential protection is typically handled at the application or pipeline level rather than in MAC profiles.

Sources: [Docker AppArmor documentation](https://docs.docker.com/engine/security/apparmor/), [How to implement AppArmor profiles for container process restriction](https://oneuptime.com/blog/post/2026-02-09-apparmor-profiles-container-restriction/view), [Kubernetes AppArmor tutorial](https://kubernetes.io/docs/tutorials/security/apparmor/), [Google Cloud AppArmor for containers](https://cloud.google.com/container-optimized-os/docs/how-to/secure-apparmor)

---

## Decision Framework

Use this checklist to decide whether to implement MAC-based file blocking:

| Condition | Add MAC rules? |
|-----------|---------------|
| Sensitive files can be scrubbed before clone | No — scrub instead |
| Network egress is strictly filtered | Optional — low marginal value |
| Network egress allows broad HTTP | Yes — MAC adds meaningful protection |
| Agent legitimately needs to read .env for task | No — MAC would break functionality |
| Agent never needs raw credential files | Yes — add deny rules |
| Threat model includes prompt injection causing exfiltration in output | Yes — NVIDIA recommends it |
| Running on SELinux (RHEL/Fedora) vs AppArmor (Ubuntu/Debian) | Prefer native MAC system |

---

## Sources

- [Ubuntu AppArmor manpage (apparmor.d.5)](https://manpages.ubuntu.com/manpages/xenial/man5/apparmor.d.5.html)
- [Debian AppArmor manpage (unstable)](https://manpages.debian.org/unstable/apparmor/apparmor.d.5.en.html)
- [Docker AppArmor security profiles](https://docs.docker.com/engine/security/apparmor/)
- [Docker Seccomp security profiles](https://docs.docker.com/engine/security/seccomp/)
- [Kubernetes: Restrict Container Access with AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [Datadog Container Security Fundamentals Part 5: AppArmor and SELinux](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-5/)
- [AppArmor - ArchWiki](https://wiki.archlinux.org/title/AppArmor)
- [AppArmor - Wikipedia](https://en.wikipedia.org/wiki/AppArmor)
- [Beyond DAC: Why SELinux and AppArmor Are Essential](https://dohost.us/index.php/2025/10/05/beyond-dac-why-selinux-and-apparmor-are-essential-for-modern-linux-security/)
- [AppArmor DAC override discussion (narkive)](https://apparmor.narkive.com/EJZiNK1H/dac-override-questions)
- [SUSE Security Guide: AppArmor Profile Syntax (Leap 15.6)](https://doc.opensuse.org/documentation/leap/security/html/book-security/cha-apparmor-profiles.html)
- [Red Hat: SELinux File Contexts and Labeling](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/selinux_users_and_administrators_guide/sect-security-enhanced_linux-working_with_selinux-selinux_contexts_labeling_files)
- [Red Hat: Creating SELinux Policies for Containers (RHEL 8)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/using_selinux/creating-selinux-policies-for-containers_using-selinux)
- [How SELinux separates containers using Multi-Level Security](https://www.redhat.com/en/blog/how-selinux-separates-containers-using-multi-level-security)
- [Red Hat Developer: My advice on SELinux container labeling (2025)](https://developers.redhat.com/articles/2025/04/11/my-advice-selinux-container-labeling)
- [Understanding SELinux labels for container runtimes](https://opensource.com/article/18/2/selinux-labels-container-runtimes)
- [runc AppArmor/SELinux bypass with symlinked /proc (GHSA-g2j6-57v7-gm8c)](https://github.com/opencontainers/runc/security/advisories/GHSA-g2j6-57v7-gm8c)
- [CVE-2023-28642: runc AppArmor bypass (Miggo)](https://www.miggo.io/vulnerability-database/cve/CVE-2023-28642)
- [AppArmor symlink support bug (Launchpad #1485055)](https://bugs.launchpad.net/apparmor/+bug/1485055)
- [AppArmor hardlink/profile name question (narkive)](https://apparmor.narkive.com/aBSP5Lc8/profile-name-and-hard-link-question)
- [fs.protected_hardlinks sysctl documentation](https://sysctl-explorer.net/fs/protected_hardlinks/)
- [CVE-2018-6553: AppArmor cupsd sandbox bypass via hardlinks](https://bugzilla.redhat.com/show_bug.cgi?id=CVE-2018-6553)
- [LWN: Linux security non-modules and AppArmor](https://lwn.net/Articles/240255/)
- [Anthropic: Making Claude Code More Secure and Autonomous](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Knostic: Claude Code Automatically Loads .env Secrets Without Telling You](https://www.knostic.ai/blog/claude-loads-secrets-without-permission)
- [NVIDIA: Practical Security Guidance for Sandboxing Agentic Workflows](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)
- [Defense in Depth: Tenant Isolation for an Agent That Executes Code](https://dev.to/ksankar/defense-in-depth-tenant-isolation-for-an-agent-that-executes-code-375j)
- [Swiss Cheese Model for AI Agent Security](https://www.apistronghold.com/blog/swiss-cheese-model-ai-agent-security)
- [Container Escape Vulnerabilities: AI Agent Security 2026 (Blaxel)](https://blaxel.ai/blog/container-escape)
- [How to Sandbox AI Agents in 2026 (Northflank)](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Gitleaks vs TruffleHog 2026 comparison](https://appsecsanta.com/sast-tools/gitleaks-vs-trufflehog)
- [GitHub: Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Google Cloud: Securing containers with AppArmor](https://cloud.google.com/container-optimized-os/docs/how-to/secure-apparmor)
- [Understanding Seccomp vs AppArmor for Container Security](https://medium.com/@mughal.asim/understanding-seccomp-and-how-it-compares-to-apparmor-for-container-security-5317b3e9b1d6)
- [HackTricks: AppArmor](https://book.hacktricks.xyz/linux-hardening/privilege-escalation/docker-security/apparmor)
- [How to implement AppArmor profiles for container process restriction](https://oneuptime.com/blog/post/2026-02-09-apparmor-profiles-container-restriction/view)
- [Creating and Managing AppArmor Profiles on Ubuntu](https://oneuptime.com/blog/post/2026-01-07-ubuntu-apparmor-profiles/view)
