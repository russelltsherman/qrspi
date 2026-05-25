# Q9: What Prevents a Credential Injected as an Environment Variable from Being Exfiltrated?

## Summary and Recommendation

**Bottom line:** Environment variables are a poor mechanism for injecting Git credentials into a container running a potentially adversarial agent. They are readable by any process in the container via `/proc/self/environ`, visible in `ps` output, inherited by all child processes, and frequently captured in logs. The raw token will be visible.

**The recommended approach for this threat model is a layered defense:**

1. **Primary: Use a custom git credential helper backed by a mounted secret file on a tmpfs (in-memory) volume.** Configure `git config credential.helper` to point to a small script that reads from `/run/secrets/github-token`. The token never appears in the environment or process list; it is consumed only by the git subprocess during the clone/push.

2. **Secondary: Use a short-lived, minimally scoped GitHub App installation token.** A 1-hour token scoped to a single repository limits the blast radius of any exfiltration to a narrow window. If the agent exfiltrates it, the attacker can only push/pull that one repo for at most one hour.

3. **Tertiary: Revoke the token immediately after the task completes.** GitHub App installation tokens can be revoked via the REST API (`DELETE /installation/token`). Call this from the host orchestrator once the container exits.

4. **Do not use environment variables as the delivery mechanism** if you have any alternative. If you must use env vars (e.g., due to orchestration constraints), treat it as a known residual risk mitigated entirely by the short TTL and narrow scope.

Advanced mitigations (Unix socket credential agent, Vault integration, confidential computing) are documented below but involve significant operational complexity for marginal gain given the 1-hour TTL.

---

## 1. Why Environment Variables Are a Poor Secret Injection Mechanism

### 1.1 `/proc/self/environ` Exposure

On Linux, every process's initial environment is exposed at `/proc/<pid>/environ` as a null-delimited string. Inside a container, PID 1's environment — which typically inherits the Docker/container launch environment including injected secrets — is readable at `/proc/1/environ` by any process running as the same user. An agent with shell access can trivially execute:

```bash
cat /proc/1/environ | tr '\0' '\n' | grep TOKEN
```

This is not a theoretical risk: a 2022 Trend Micro study found that environment variables containing secrets are routinely exfiltrated through LFI (local file inclusion) and SSRF vulnerabilities that allow reading `/proc/self/environ`. Detection tools like Falco can monitor for this access pattern, but prevention is not possible without eliminating env vars as the injection mechanism.

**Key risk:** `/proc/<pid>/environ` exposes the environment variables set at process launch. Variables added after launch do not appear here, but most injection schemes set them at startup.

### 1.2 `ps aux` and `/proc/<pid>/cmdline` Exposure

If the token is passed as a command-line argument (e.g., `git clone https://oauth2:TOKEN@github.com/...`), it is visible in `ps aux` output via `/proc/<pid>/cmdline`. Any process on the system can read this. This is a separate attack vector from env var exposure and is exploited differently — URL-embedded tokens are a particularly common mistake in CI/CD pipelines.

Git's credential helper system is specifically designed to avoid this: the token is passed via stdin/stdout to the helper process, not via command-line arguments or env vars.

### 1.3 Child Process Inheritance

Every child process spawned (via `fork()`/`exec()`) inherits the parent's full environment unless the parent explicitly clears it. In an agentic container running shell commands, any subprocess — including potentially untrusted tools invoked by the agent — will inherit all environment variables set on the container. This is the "environment variable inheritance" threat: a compromised tool in the PATH or a prompt-injected shell command can dump `env` and exfiltrate every variable.

### 1.4 Logging Risks

Application frameworks and debugging tools routinely log environment variables on startup or on error. Node.js, Python, Java, and shell scripts all have common patterns that dump env. GitHub's own documentation warns: "avoid passing secrets through command-line processes when possible, as they may be visible via `ps` commands or captured in audit logs." A 2024 large-scale extortion campaign demonstrated the real-world impact: attackers harvested over 90,000 unique env variables from misconfigured applications that exposed `.env` files or logged their environment.

### 1.5 Container Inspection

Anyone with `docker inspect` or `kubectl exec <pod> -- env` access to the running container can dump all environment variables. This is trivial for anyone with container platform access and is not protected by any container isolation mechanism.

---

## 2. Git Credential Helpers: How They Work

### 2.1 The Credential Helper Protocol

Git's credential helper system (`gitcredentials(7)`) is specifically designed to avoid exposing secrets in the environment or process list. When Git needs a credential, it:

1. Invokes the configured helper with the operation (`get`, `store`, or `erase`) as a command-line argument.
2. Writes credential context (protocol, host, path) to the helper's **stdin** in key=value format.
3. Reads the response from the helper's **stdout**.

The helper returns `username=...` and `password=...` lines. The token is passed via stdin/stdout IPC, never via environment variables or command-line arguments. From the `ps` perspective, the helper process is visible but its arguments contain only the operation name, not the token.

```
# What ps sees:
git-credential-my-helper get

# What the helper receives on stdin:
protocol=https
host=github.com

# What the helper writes to stdout:
username=x-access-token
password=ghs_xxxxxxxxxxxxxxxxxxxxx
```

### 2.2 `git-credential-cache`: Socket-Based In-Memory Storage

The built-in `git-credential-cache` stores credentials in memory inside a daemon process and communicates via a **Unix domain socket**. The socket is created at `$XDG_CACHE_HOME/git/credential/socket` (or `~/.git-credential-cache/socket`) with filesystem permissions restricted to the current user.

Key security properties:
- Credentials are held **only in the daemon's memory**, never written to disk.
- Communication happens over the Unix socket — the raw token does not appear in the process environment of the caller or the daemon.
- Credentials are forgotten after a configurable timeout (default 15 minutes).
- The socket's directory permissions prevent other users from connecting.

This is well-suited to the sandbox use case: pre-load the token into the cache before launching the agent, then delete the socket entry after use.

### 2.3 Custom Credential Helpers Backed by Mounted Files

A more controlled approach for containers is a custom credential helper that reads from a **mounted secret file** rather than an environment variable:

```bash
#!/bin/sh
# /usr/local/bin/git-credential-container-secret
# Configured via: git config credential.helper container-secret
if [ "$1" = "get" ]; then
  echo "username=x-access-token"
  echo "password=$(cat /run/secrets/github-token)"
fi
```

Then configure git globally in the container:
```
git config --global credential.helper container-secret
git config --global credential.https://github.com.helper container-secret
```

The token never enters the environment. The file at `/run/secrets/github-token` is mounted read-only from a tmpfs volume (see section 3).

### 2.4 GitHub App-Specific Credential Helpers

Several open-source helpers exist that take a GitHub App private key (stored as a mounted file) and **dynamically generate installation tokens on demand**, so the short-lived token is never persisted anywhere at rest:

- `git-credential-github-app` (Go): Reads the App ID and private key path from its own configuration or flags, calls the GitHub API to generate an installation token, and outputs it to Git's stdin/stdout pipeline.
- `git-credential-github-app-auth` (Rust): Similar approach, generates tokens at credential-request time.

With this approach, the private key (long-lived, more sensitive) is injected as a mounted file, and the ephemeral installation token is generated in-process by the helper. The raw token is briefly in the helper's memory but never in the container's environment or process list.

---

## 3. Mounted Secret Files vs. Environment Variables

### 3.1 How tmpfs Mounts Work

Docker secrets and Kubernetes secret volumes both mount credentials as **files on a tmpfs (memory-backed) filesystem**, typically at `/run/secrets/<name>`. Key properties:

- **Not stored on disk.** tmpfs exists only in RAM; nothing is written to the container's writable layer or the host's disk.
- **Disappear on container stop.** When the container exits, the memory is freed and the data is gone.
- **Never committed to images.** A `docker commit` of the running container does not include tmpfs mounts.
- **File permission control.** The file can be mode `0400` (owner read-only), restricting access even within the container to the specific UID that needs it.
- **Not visible as environment variables.** There is no analog of `/proc/<pid>/environ` for mounted files; an attacker must know the path and have filesystem read access.

Docker Swarm secrets and Docker's `--mount type=secret` BuildKit syntax both use this mechanism. The Docker documentation explicitly states that this approach avoids environment variable exposure and prevents accidental leakage through container linking.

### 3.2 Comparison Table

| Property | Environment Variable | tmpfs-Mounted File |
|---|---|---|
| Visible in `/proc/<pid>/environ` | Yes | No |
| Visible in `ps aux` | If passed as arg | No |
| Inherited by all child processes | Yes | Only via explicit file read |
| Logged by frameworks on error | Frequently | Only if app explicitly reads and logs |
| Accessible after container restart | No (must re-inject) | No (mount gone) |
| Writable layer / `docker commit` exposure | No | No |
| Revocable without container restart | No | Yes (if using a credential helper that re-reads) |
| Complexity of setup | Low | Medium |

### 3.3 CNCF Recommendation

The Cloud Native Computing Foundation (CNCF) explicitly recommends: "secrets should be injected at runtime within the workloads through non-persistent mechanisms that are immune to leaks via logs, audit, or system dumps (i.e., in-memory shared volumes instead of environment variables)."

---

## 4. The Kubernetes Secrets Model

Kubernetes supports both injection mechanisms but explicitly recommends volume mounts for sensitive data.

### 4.1 Environment Variable Injection (Discouraged)

```yaml
env:
  - name: GITHUB_TOKEN
    valueFrom:
      secretKeyRef:
        name: github-token
        key: token
```

Once the container starts, the token is a normal environment variable with all the risks described in section 1. The Kubernetes documentation notes: "it is reasonably common for application code to log out its environment (particularly in the event of an error). This will include any secret values passed in as environment variables."

### 4.2 Volume Mount Injection (Recommended)

```yaml
volumes:
  - name: github-token
    secret:
      secretName: github-token
      defaultMode: 0400
volumeMounts:
  - name: github-token
    mountPath: /run/secrets/github-token
    subPath: token
    readOnly: true
```

Kubernetes mounts the secret as a tmpfs file inside the pod. The Kubernetes documentation states: "Injecting a Secret by means of a file in a volume can be more secure in the scope of the Pod, since you can make the file only selectively available to components within a container."

An additional benefit of volume mounts: if the secret is rotated in Kubernetes (new Secret object), the mounted file updates **without a pod restart** (subject to kubelet sync period, typically 60 seconds). Environment variables require a container restart to pick up a new value.

### 4.3 etcd Encryption

Kubernetes Secrets are stored base64-encoded in etcd by default, which is not encryption. The Kubernetes documentation is explicit: "base64 encoding provides no confidentiality." Production clusters should enable [encryption at rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/) for the Secrets resource type.

---

## 5. Short-Lived Token Mitigations

### 5.1 GitHub App Installation Token Properties

GitHub App installation tokens have the following characteristics:
- **TTL: 1 hour** (3600 seconds), hardcoded by GitHub.
- **Repo-scoped:** Can be restricted to specific repository IDs at generation time using the `repository_ids` parameter in the `POST /app/installations/{id}/access_tokens` API.
- **Permission-scoped:** Can be restricted to specific permissions (e.g., `contents: read, pull_requests: write`) even below the App's granted permissions.
- **Revocable on demand:** `DELETE /installation/token` revokes the token immediately using the token itself as the bearer credential.

### 5.2 Risk Analysis: Does Short TTL Matter?

If the token is exfiltrated by the agent, the attacker has:
- A maximum of 1 hour to use it.
- Access only to the specific repository (or repositories) scoped at generation.
- Only the permissions granted at generation (e.g., cannot delete the repo if only `contents: write` was granted).

**What this means in practice:** The exfiltration risk from a 1-hour, single-repo token is substantially lower than from a long-lived PAT. The attacker cannot pivot to other repositories or escalate to organization-level access. The primary concern is data exfiltration from the target repo (if `contents: read` was granted) or unauthorized commits/PRs.

**Residual risks even with short TTL:**
- The agent could exfiltrate the repository's source code to an external location during the 1-hour window.
- If the sandbox lacks egress filtering, the token could be used from outside the container before it expires.
- If the agent is sophisticated enough to exfiltrate and immediately hand off, even a 15-minute window is sufficient.

**Recommendation:** Short TTL is a meaningful mitigation but not a complete defense. Combine it with egress network controls that whitelist only the GitHub API and the specific repository host. If the container has no outbound internet access except to `api.github.com` and `github.com`, an exfiltrated token is far less useful.

### 5.3 Immediate Revocation Pattern

The host orchestrator should follow this lifecycle:
1. Generate installation token immediately before container launch.
2. Inject into container (via mounted file, not env var).
3. Monitor container for task completion.
4. On container exit (success or failure), call `DELETE /installation/token` to revoke immediately — do not wait for natural expiration.

This shrinks the exposure window from 1 hour to the actual task duration, which is often minutes.

---

## 6. Hardware-Backed Secret Stores Inside Containers

### 6.1 TPM-Based Protection

A Trusted Platform Module (TPM) can seal secrets to a specific system state (PCR values), meaning the secret is only decryptable if the boot chain is unmodified. This provides strong protection against secrets being extracted if the host is compromised at rest, but does not provide meaningful protection against a running container reading its own mounted secrets.

Inside a container, the TPM (or vTPM) is not directly accessible unless the container is given explicit device access (`--device /dev/tpm0`). Giving a potentially adversarial agent access to the TPM device would be a significant escalation of privilege.

**Practical verdict:** TPM-based sealing is not a practical mitigation for the credential exfiltration threat model described here. It protects against offline extraction, not in-container runtime exfiltration.

### 6.2 Confidential Computing (AMD SEV-SNP / Intel TDX)

AMD SEV-SNP and Intel TDX provide hardware-level memory encryption for VMs/containers. Memory pages belonging to the protected VM are encrypted with a key held by the CPU; even the hypervisor cannot read them. Google Cloud's Confidential VMs and AWS's AWS Nitro Enclaves implement variants of this.

For the sandbox threat model:
- **Protects against:** A compromised hypervisor or co-tenant reading container memory.
- **Does not protect against:** The agent process reading its own memory. The encryption is transparent to the workload — the running process sees plaintext.

Confidential containers (Kata Containers + SEV-SNP, CoCo project) can be used to protect secrets from the host operator, not from code running inside the container. This is orthogonal to the intra-container exfiltration threat.

**Practical verdict:** Confidential computing is not a practical mitigation for this threat. It addresses a different attacker model (privileged host operator) than the one described (adversarial agent running inside the container).

### 6.3 Memory-Encrypted Regions (mlock, memfd_secret)

Linux 5.14 introduced `memfd_secret()`, which creates memory regions that are not accessible to the kernel itself (via direct map exclusion). The `mlock()` syscall prevents memory from being swapped to disk. These are not commonly available within containers without elevated capabilities and do not prevent the running process (or other processes with the same UID) from reading them.

**Practical verdict:** `memfd_secret` is a niche syscall not practically usable from a shell script or standard git credential helper. `mlock` is valuable to prevent swap exposure but requires `CAP_IPC_LOCK`.

---

## 7. The Specific Git Workflow: Token via Socket Agent

The cleanest architecture for this use case is:

1. **Host orchestrator** generates the installation token before container launch.
2. **Host-side credential daemon** (or a process inside a sidecar) holds the token in memory and listens on a Unix domain socket.
3. **Container** has the socket mounted as a volume (read-only path to the socket file).
4. **Inside container**, git is configured with a credential helper that connects to the socket to retrieve the token on demand.

This means:
- The raw token is never in the container's environment.
- The raw token is never written to disk.
- The token is fetched only when git actually needs it (during the specific `git clone` or `git push` operation).
- After the token is consumed, the socket connection is closed.

An alternative simpler pattern that achieves most of the same benefits:
1. Write the token to a tmpfs file at container startup (host injects via volume mount or init container).
2. Configure `git config credential.helper '!f() { echo username=x-access-token; echo password=$(cat /run/secrets/github-token); }; f'` in `~/.gitconfig`.
3. Set the file to mode `0400` owned by the agent's UID.
4. Optionally `shred` the file after the git operations complete.

The FIFO (named pipe) approach described in the Gitpod containerization article is an interesting variant: the credential is only "readable" once because a pipe is consumed on read. This prevents the agent from re-reading the token after initial use.

---

## 8. How CI/CD Systems Handle Credential Injection

### 8.1 GitHub Actions

GitHub Actions injects secrets as **environment variables** by default when accessed via `${{ secrets.MY_SECRET }}` in a `env:` block or passed as inputs. GitHub applies automatic **masking** in log output — if the raw token value appears in any log line, it is replaced with `***`. However, masking is best-effort: transformed values (base64-encoded, URL-encoded) are not masked.

GitHub Actions also supports:
- **OIDC federation:** Workflows authenticate to cloud providers (AWS, GCP, Azure) using a JWT issued by GitHub's OIDC provider, exchanging it for a short-lived cloud credential. The static secret never exists; only the ephemeral derived credential does.
- **Ephemeral runners (JIT):** Just-in-time runners that handle exactly one job and are then destroyed, limiting the window for credential persistence.

The GitHub documentation explicitly warns against passing secrets via command-line arguments and recommends using them as environment variables (the lesser evil vs. command-line args) or via dedicated credential helpers.

### 8.2 GitLab CI

GitLab CI injects secrets as **masked environment variables** with log masking applied. GitLab CI also fully supports OIDC token generation (generally available since GitLab 15.9), allowing pipelines to exchange a job-scoped JWT for temporary cloud credentials without any static secrets in the repository or project settings.

For git operations within GitLab CI, the platform automatically injects a `CI_JOB_TOKEN` that is scoped to the current job and expires when the job ends. This is functionally equivalent to a GitHub App installation token — short-lived and job-scoped.

### 8.3 CircleCI

CircleCI injects secrets as environment variables in the job environment. It supports OIDC tokens (`CIRCLE_OIDC_TOKEN`) that can be exchanged with Vault or cloud providers for short-lived credentials. The OIDC token contains job-specific claims (project, organization, branch) enabling fine-grained access policies.

A notable 2024 security finding: CircleCI initially generated OIDC tokens for fork PR workflows, granting fork owners access using the target repository's identity. This was fixed by disabling OIDC generation for forks by default.

### 8.4 Common Theme: The Trend Toward OIDC/Secretless

All three major CI/CD platforms are converging on **OIDC-based workload identity** as the preferred credential injection model: instead of injecting a secret, inject a short-lived, job-scoped JWT that the workload exchanges for the actual credential at runtime. The raw credential never exists in the environment at rest — it is fetched and used within a narrow window.

For the agentic container sandbox, an analogous pattern would be a **credential proxy service** running outside the container that issues short-lived tokens to the container based on the job's identity, rather than pre-injecting a token.

---

## 9. Recommended Architecture for the QRSPI Sandbox

Given the threat model (adversarial agent, shell access, credential exfiltration risk), the recommended implementation is:

```
┌─────────────────────────────────────────────────────┐
│ Host Orchestrator                                    │
│  1. Generate GitHub App installation token          │
│     (scoped to target repo, contents+PRs only)      │
│  2. Write token to tmpfs file                       │
│  3. Mount tmpfs into container at /run/secrets/     │
│  4. Configure git credential.helper in container    │
│  5. On exit: revoke token via DELETE /installation/ │
│              token                                   │
└─────────────────────────────────────────────────────┘
                          │
                          │ tmpfs volume mount (read-only)
                          ▼
┌─────────────────────────────────────────────────────┐
│ Agent Container                                     │
│  /run/secrets/github-token (mode 0400, tmpfs)       │
│  ~/.gitconfig:                                      │
│    [credential "https://github.com"]                │
│      helper = "!cat /run/secrets/github-token |     │
│               sed 's/^/password=/'; echo            │
│               username=x-access-token"              │
│  Egress: whitelist api.github.com only              │
└─────────────────────────────────────────────────────┘
```

This gives:
- No token in environment variables
- No token in process list
- Token in tmpfs (RAM only, deleted on container exit)
- Token auto-expires in 1 hour
- Token immediately revoked on job completion
- Egress-limited so exfiltrated token has nowhere to go

---

## Sources

- [Git Credential Helpers Documentation — git-scm.com](https://git-scm.com/docs/gitcredentials)
- [git-credential-cache Documentation — git-scm.com](https://git-scm.com/docs/git-credential-cache)
- [Generating an Installation Access Token for a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
- [Good Practices for Kubernetes Secrets — kubernetes.io](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [Kubernetes Secrets — kubernetes.io](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Manage Sensitive Data with Docker Secrets — Docker Docs](https://docs.docker.com/engine/swarm/secrets/)
- [Docker Secrets Explained — Wiz Academy](https://www.wiz.io/academy/container-security/docker-secrets)
- [Using Secrets in GitHub Actions — GitHub Docs](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [Secure Use Reference — GitHub Docs](https://docs.github.com/en/actions/reference/security/secure-use)
- [Secretless Access for GitHub Actions and Workflows — Aembit](https://aembit.io/blog/secretless-access-for-github-actions/)
- [Hardening GitHub Actions: Lessons from Recent Attacks — Wiz Blog](https://www.wiz.io/blog/github-actions-security-guide)
- [Using OpenID Connect Tokens in Jobs — CircleCI Docs](https://circleci.com/docs/openid-connect-tokens/)
- [OH-MY-DC: OIDC Misconfigurations in CI/CD — Unit 42, Palo Alto Networks](https://unit42.paloaltonetworks.com/oidc-misconfigurations-in-ci-cd/)
- [Configure OpenID Connect in AWS to Retrieve Temporary Credentials — GitLab Docs](https://docs.gitlab.com/ci/cloud_services/aws/)
- [Leaked Environment Variables Allow Large-Scale Extortion Operation — Unit 42, Palo Alto Networks](https://unit42.paloaltonetworks.com/large-scale-cloud-extortion-operation/)
- [Attackers Exploit Public .env Files to Breach Cloud Accounts — The Hacker News](https://thehackernews.com/2024/08/attackers-exploit-public-env-files-to.html)
- [Hacking with Environment Variables — elttam](https://www.elttam.com/blog/env)
- [Using Linux Process Environment Variables for Live Forensics — Sandfly Security](https://sandflysecurity.com/blog/using-linux-process-environment-variables-for-live-forensics)
- [Kubernetes Secrets: Best Practices for Secure Management — GitGuardian](https://blog.gitguardian.com/how-to-handle-secrets-in-kubernetes/)
- [Kubernetes ConfigMaps & Secrets: Why Mounting is Better Than Environment Variables — Medium](https://medium.com/@wangareirungu3/kubernetes-configmaps-secrets-why-mounting-is-better-than-environment-variables-454287a55fe5)
- [Containerizing Git Credential Helpers — Dataminded / Medium](https://medium.com/datamindedbe/containerizing-git-credential-helpers-5f7ef75849b4)
- [git-credential-github-app — GitHub (bdellegrazie)](https://github.com/bdellegrazie/git-credential-github-app)
- [git-credential-github-app-auth — GitHub (uw-ipd)](https://github.com/uw-ipd/git-credential-github-app-auth)
- [Secure CI/CD with GitHub Apps Short Lived Tokens — Medium](https://medium.com/@devopswithyoge/secure-ci-cd-with-github-apps-short-lived-tokens-227d6e05c5fa)
- [Protect Your GitHub App Private Keys with Azure Key Vault and Remote JWT Signing — Jeff Wilcox](https://jeffwilcox.name/2026/03/github-app-remote-jwt-signing/)
- [New Limits on Scoped Token Creation for GitHub Apps — GitHub Changelog](https://github.blog/changelog/2024-02-22-new-limits-on-scoped-token-creation-for-github-apps/)
- [Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges — arXiv](https://arxiv.org/html/2510.23883v1)
- [Agentic AI Threat Modeling Framework: MAESTRO — CSA](https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro)
- [Clone2Leak Exposes Credential Risks in Git Ecosystem — Dataconomy](https://dataconomy.com/2025/01/28/clone2leak-exposes-credential-risks-in-git-ecosystem/)
- [Git Vulnerabilities Led to Credentials Exposure — SecurityWeek](https://www.securityweek.com/git-vulnerabilities-led-to-credentials-exposure/)
- [Confidential VMs Explained: AMD SEV-SNP and Intel TDX — ACM SIGMETRICS](https://dl.acm.org/doi/10.1145/3700418)
- [Expanding Confidential Computing for AI Workloads — Google Cloud Blog](https://cloud.google.com/blog/products/identity-security/expanding-confidential-computing-for-ai-workloads-next24)
- [Add New Rule to Detect Retrieving Environment Variables from /proc Files — Falco GitHub](https://github.com/falcosecurity/falco/issues/2192)
- [Environment Variables Considered Harmful for Your Secrets — Hacker News](https://news.ycombinator.com/item?id=8826024)
- [Short-lived GitHub Access Token for Secure Local Development — DEV Community](https://dev.to/suzukishunsuke/introducing-ghtkn-your-safer-github-token-solution-347d)
