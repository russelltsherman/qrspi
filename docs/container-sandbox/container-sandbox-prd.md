# PRD: Agentic Task Container Sandbox

**Status:** Draft  
**Date:** 2026-04-18  
**Author:** Russell Sherman

---

## Overview

A per-invocation container sandbox that enforces hard security boundaries around agentic task execution. Each agent container runs with statically defined constraints — network egress, filesystem access, tool availability, git credentials — that are derived from the agent's QRSPI role and enforced at the network and OS levels, not the application level.

The system is designed against a threat model of a potentially adversarial agent: one that may attempt to exfiltrate data, reach unauthorized resources, modify files outside its scope, or exploit its execution environment. No trust is placed in the agent's self-reported behavior.

---

## Goals

- Hard security boundary per container invocation, not application-level soft constraints
- Static, declarative constraint policies defined before the agent starts
- Enforcement at VM, OS, and network layers
- Tamper-resistant, structured audit log written outside the container
- Role-derived policies — each QRSPI phase has a defined permission profile
- Human review gate via pull request for all agent work product

---

## Non-Goals

- Dynamic constraint negotiation at runtime
- Application-layer-only enforcement (Claude Code `settings.json`, etc.)
- Trusting the agent to self-police
- General-purpose container hardening unrelated to agentic workloads

---

## Threat Model

The agent is treated as potentially adversarial. Specific threats considered:

- **Data exfiltration** — via outbound network, DNS queries, PR contents, commit messages
- **Unauthorized resource access** — reaching domains, hosts, or file paths outside declared scope
- **Privilege escalation** — exploiting kernel vulnerabilities, capability abuse, symlink attacks
- **Supply chain compromise** — pulling in malicious packages during execution
- **Audit tampering** — modifying or suppressing logs of its own behavior
- **Covert channels** — DNS exfiltration, timing side-channels, encoding data in allowed outputs

The PR itself is a recognized exfiltration vector. An agent can encode stolen data in code, comments, commit messages, or file names. The human PR review is the intended defense.

---

## Architecture

### Container Runtime

Standard Docker namespace isolation is insufficient for this threat model — a kernel exploit escapes it. The target runtime is **Kata Containers** or **Firecracker microVMs**, providing a VM boundary per invocation. Each agent runs in its own microVM with an isolated kernel.

### Syscall Filtering

A custom restrictive seccomp profile is applied within the VM, blocking syscalls unnecessary for the agent's task: `ptrace`, `mount`, `mknod`, `keyctl`, capability manipulation, and others. Docker's default seccomp profile is not sufficient.

All Linux capabilities are dropped. No setuid binaries. No elevated process privileges.

### Filesystem

The agent performs a **fresh shallow clone** of the target repository at container start. It works directly on this clone. There is no host filesystem mounted into the container.

- The project checkout is the agent's working directory
- No host paths are bind-mounted
- The agent's git credentials are scoped to a single repository with minimum required permissions (see Git Credentials)
- Sensitive files (`.env`, secrets, credentials) should be excluded from the repo or gitignored — their presence in a cloned repo is a risk that exists independent of the sandbox

Write scope is limited to the cloned working directory. The agent publishes its work as a **pull request**, which becomes the human review gate before any changes reach the main branch.

### Network Egress

Two enforcement layers work together:

**DNS filtering:** All DNS traffic is forced through a controlled resolver. The resolver returns NXDOMAIN for domains not on the role's allowlist. Direct UDP port 53 outbound to external resolvers is blocked. DNS-over-HTTPS as a bypass vector is addressed by blocking outbound HTTPS to known DoH providers.

**IP-level firewall (iptables/nftables):** Per-container rules allowlist specific IP ranges and block everything else. This catches hardcoded-IP bypass attempts that would survive DNS filtering.

**TLS inspection proxy (optional):** For path-level URL control (beyond hostname), a forward HTTPS proxy with TLS inspection can be deployed. This requires injecting a CA certificate into the container. Without it, enforcement is at the hostname/SNI level only.

Network access is limited to what the role explicitly requires. See Role Policy Catalog.

### Git Credentials

Each invocation receives a **short-lived, single-repo-scoped git credential** generated at container start:

- GitHub App installation token (preferred) — expires in 1 hour, scoped to a single repository
- Permissions: `contents:write`, `pull_requests:write` only
- No access to other repositories, organization data, or administrative functions
- Token is injected as an environment variable or git credential helper, not written to disk

The token scope is treated as a hard constraint independent of network filtering.

### Audit Log

The audit log is written to a sink **outside the container** that the agent has no access to:

- Host-side collection via eBPF (Falco or Tetragon) or auditd
- Covers: syscalls, file access (read/write/exec), network connection attempts (allowed and denied), process spawning
- Structured format (JSON) for post-hoc analysis and alerting
- Append-only log destination — no process inside the container can write or delete entries
- Retained per-invocation with a correlation ID linking logs to the specific agent run

---

## Role Policy Catalog

Constraint policies are derived from the agent's QRSPI role. Policies live in a policy catalog **outside the repository** — in a separate trust domain the agent cannot read. The agent definition (`.qrspi/agents/`) and the enforcement policy are not co-located.

### Role Permission Matrix

| Role | Web Search | Filesystem | Git | Shell Exec |
|------|------------|------------|-----|------------|
| qrspi-questions | allowed (search) | read-only (ticket) | none | none |
| qrspi-research | allowed (search) | read-only (project) | none | none |
| qrspi-design | none | read-only (artifacts) | none | none |
| qrspi-structure | none | read-only (artifacts) | none | none |
| qrspi-plan | none | read-only (artifacts) | none | none |
| qrspi-worktree | none | read-only (artifacts) | none | none |
| **qrspi-implement** | package registry only | read/write (clone) | clone + push + PR | yes (test runner) |
| qrspi-pr | none | read-only (artifacts) | push + PR | none |

### Policy File Structure (per role)

```yaml
role: qrspi-implement
network:
  allowed_domains:
    - github.com
    - pypi.org          # example; varies by project stack
  dns: controlled-resolver
  tls_inspection: false # enable for path-level filtering
filesystem:
  mode: clone           # agent clones repo, works in clone
  write_scope: /workspace
git:
  credential_type: github-app-installation-token
  allowed_repos:
    - owner/repo        # injected per invocation
  allowed_operations:
    - clone
    - push
    - pull-request
tools:
  allowed_mcp_servers:
    - filesystem
    - git
resources:
  wall_clock: 7200      # seconds
  memory_mb: 4096
  cpu_cores: 2
syscalls:
  profile: restrictive
capabilities:
  drop_all: true
```

---

## Work Product Review Flow

1. Container is provisioned with role policy applied
2. Agent clones repository (shallow)
3. Agent performs its task within enforced constraints
4. Agent pushes a branch and opens a pull request
5. Human reviews the PR — this is the gate before changes merge
6. Container is destroyed; audit log is retained
7. Short-lived credential expires automatically

---

## Security Properties

| Property | Mechanism |
|----------|-----------|
| Filesystem isolation | No host mounts; agent works in fresh clone |
| Network isolation | DNS filtering + IP firewall; role-allowlisted egress |
| Privilege isolation | VM boundary (Kata/Firecracker) + seccomp + dropped capabilities |
| Credential isolation | Short-lived, single-repo, minimum-permission token |
| Audit integrity | eBPF/auditd outside container; append-only sink |
| Work product review | Pull request gate; human approval before merge |
| Policy integrity | Policy catalog outside repo trust domain |
