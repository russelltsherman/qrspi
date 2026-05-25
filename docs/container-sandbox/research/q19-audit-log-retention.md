# Q19: Audit Log Retention and Access Policy

**Question:** Who can read audit logs? How long are they retained? Are they associated with the PR they produced? This matters for incident response and for training signal if logs are used to improve policies.

---

## Summary and Recommendations

For a container sandbox that generates tamper-resistant audit logs via eBPF/auditd for agentic AI invocations, the following policy is recommended:

**Retention:** Retain hot (queryable) logs for **90 days**, warm (compressed, indexed) for **1 year**, and cold (WORM-archived) for **3 years**. The 90-day hot tier satisfies NIST SP 800-171 and enables rapid incident response. The 1-year warm tier satisfies SOC 2, ISO 27001, and PCI DSS. The 3-year cold tier provides a training signal corpus and covers the 3-year SOC 2 lookback window that some auditors require.

**Correlation:** Every container invocation must carry a `session_id` injected at container startup that is immutable and flows through eBPF/auditd events, application logs, and the git commit/PR metadata. This is the primary correlation key linking log → invocation → PR → ticket.

**Access control:** Logs must be stored in a write-protected sink that the sandboxed agent cannot reach. Read access is granted only to: (1) security/incident-response team via break-glass procedure, (2) automated policy-refinement pipelines via a scoped service account, and (3) compliance auditors during reviews. No developer, no AI agent, and no CI/CD pipeline step other than the log collector should have write access.

**Immutability:** Use S3 Object Lock in Compliance mode (or equivalent WORM sink) for all tiers. The log collector (Falcosidekick / Vector / Fluent Bit) writes to an S3 bucket the agent container cannot access; the bucket denies all `s3:DeleteObject` and `s3:PutObject` calls except from the log-writer service account.

**Privacy / legal:** Behavioral logs of AI agents are likely to contain personal data (filenames, command arguments, network destinations) that triggers GDPR data-minimization obligations. Retention beyond 1 year should be justified by documented legitimate interest (security, policy improvement), and a Data Protection Impact Assessment (DPIA) should be performed. The EU AI Act Article 19 requires high-risk AI systems to retain auto-generated logs for at least 6 months.

---

## 1. Audit Log Data Models: Falco, Tetragon, and auditd

### 1.1 Falco (syscall + Kubernetes audit events)

Falco emits JSON events with these primary field groups:

| Group | Key Fields |
|---|---|
| Event metadata | `evt.num`, `evt.time` (nanosecond timestamp), `evt.type` (e.g. `openat`, `connect`), `evt.category` (file/net/memory), `evt.cpu` |
| Process | `proc.pid`, `proc.ppid`, `proc.name` (16-char truncated), `proc.cmdline` (full args), `proc.cwd`, `proc.aname[N]` (ancestor chain) |
| User | `user.uid`, `user.name`, `user.loginuid` (audit UID persists across su/sudo) |
| File operations | `fd.name` (full path), `fd.directory`, `fd.filename`, `fd.ino` (inode), `fs.path.name` |
| Network | `fd.cip`/`fd.sip` (client/server IPs), `fd.cport`/`fd.sport`, `fd.l4proto`, connection tuple (e.g. `192.168.1.1:47400->10.0.0.1:443`) |
| Container | `container.id` (12-char prefix), `container.name`, `container.image.repository` |
| Kubernetes | `k8s.pod.name`, `k8s.ns.name`, `k8s.pod.uid`, `k8s.pod.label[key]` |

Falco supports 400+ distinct syscall event types as of schema version 4.1.0. Events are emitted via Falcosidekick to output sinks including Elasticsearch, Loki, S3, Splunk, and 50+ other destinations. Falcosidekick supports JSON, Syslog, and CEF output formats for SIEM compatibility.

The k8saudit plugin captures Kubernetes API server audit events (stage, verb, user, resource, namespace, response code) separately from syscall events.

### 1.2 Tetragon (eBPF-native, Kubernetes-aware)

Tetragon emits structured JSON via stdout (or gRPC) with five primary event types:

| Event Type | Key Fields |
|---|---|
| `process_exec` | `exec_id`, `pid`, `uid`, `binary`, `arguments`, `flags`, `start_time`, `pod` (namespace/name/container), `parent` |
| `process_exit` | Same process fields plus `exit_code`, `exit_signal` |
| `process_kprobe` | Kernel probe details: `function_name`, `args[]` (syscall arguments with types), `return` |
| `process_tracepoint` | Tracepoint name, arguments |
| `process_loader` | Dynamic library loads |

For network events, Tetragon kprobe policies on `tcp_connect` / `tcp_accept` produce `sock_arg` fields containing: `saddr`, `daddr`, `sport`, `dport`, `protocol`, `family`, `state`, `cookie`. DNS/TLS/HTTP protocol metadata is also supported with policy configuration.

The `exec_id` field is globally unique per process invocation and provides a stable cross-event anchor for correlating all syscalls from a single process. All events include a `node_name` and nanosecond `time`.

### 1.3 auditd (kernel audit subsystem)

Linux auditd captures:
- **SYSCALL records:** syscall number, return value, UID/GID/EUID, PID, PPID, session ID, `auid` (login UID), command name, key (rule tag)
- **PATH records:** file path associated with a syscall, inode, device, permissions
- **SOCKADDR records:** socket address (IP/port) for network syscalls
- **EXECVE records:** argument list for exec() calls
- **CWD record:** current working directory at time of syscall

The `auid` (audit UID) field is especially valuable: it is set at login and inherited by all child processes, surviving su/sudo transitions. For container workloads, auditd captures the host-level view; the container runtime's `cgroup` and namespace IDs can be correlated with auditd's `pid` and `ppid` fields.

### 1.4 Cross-event correlation architecture

To correlate a syscall event in auditd with a Falco alert and a Tetragon kprobe event for a single container invocation:

```
Host kernel (PID namespace)
  auditd → auid + pid + ppid + session_id
  Falco  → container.id + proc.pid + evt.time
  Tetragon → exec_id + pid + pod.container + time
```

The container runtime (containerd / CRI-O) provides the mapping: `container_id → host_pid`. All three tools can be joined on `(container_id, host_pid, timestamp_window)`. The `session_id` from auditd and the `exec_id` from Tetragon serve as unique event-chain anchors.

---

## 2. Correlation ID Design

### 2.1 The invocation correlation chain

Every agent container invocation must emit a single `session_id` (UUIDv7 recommended for time-ordered sorting) that is:

1. **Generated** by the orchestrator before the container starts
2. **Injected** as an environment variable (`AGENT_SESSION_ID`) and as a Kubernetes pod label (`agent.qrspi.io/session-id`)
3. **Propagated** into:
   - Falco events: via `k8s.pod.label[agent.qrspi.io/session-id]`
   - Tetragon events: via pod metadata fields
   - auditd: via a custom audit rule tag (`-k agent_session_<id>`) added programmatically before container start, or via a container cgroup label
   - Application logs: injected into the log context by the agent runtime
   - Git commit metadata: written to the commit message footer (`Agent-Session-Id: <id>`) and to the PR description

The full correlation chain is:

```
QRSPI ticket ID
  └─ Worktree / plan artifact (stored in .qrspi/<ticket-id>/)
       └─ Container invocation
            └─ session_id (UUIDv7)
                 ├─ auditd records (matched by cgroup / audit tag)
                 ├─ Falco alerts (matched by pod label)
                 ├─ Tetragon events (matched by pod metadata)
                 ├─ Application logs (injected field)
                 └─ Git commit / PR (written to commit footer and PR body)
```

### 2.2 OpenTelemetry integration

OpenTelemetry context propagation (W3C `traceparent` header) can carry the `session_id` as a custom trace attribute when the agent makes outbound HTTP calls, enabling correlation with external service traces. The `trace_id` field in OTEL spans can be set equal to the first 16 bytes of the `session_id` for direct linkage. Logz.io, Datadog, and other OTEL-compatible backends automatically correlate OTEL traces with logs that carry matching `trace_id` and `span_id` fields.

### 2.3 Git/PR linkage

The CI/CD pipeline that merges the agent-produced PR should:
- Write `Agent-Session-Id: <id>` to the git commit trailer (via `git interpret-trailers`)
- Tag the PR with the session ID using a GitHub/GitLab label or custom field
- Store a pointer record in the log index: `{session_id, pr_number, commit_sha, ticket_id, timestamp}` — this small index record is itself stored in the WORM log bucket as a JSON object

---

## 3. Retention Periods

### 3.1 Compliance framework requirements

| Framework | Minimum Retention | Notes |
|---|---|---|
| NIST SP 800-171 | 90 days | Required for CUI environments (DFARS 252.204-7012) |
| NIST SP 800-92 | Organization-defined; recommends archival with filtering | Revised draft (800-92r1) expected to update this |
| SOC 2 | 1 year (auditor expectation) | No mandated period; auditors typically review 12 months |
| ISO 27001:2022 | 12 months minimum (recommended) | Controls 8.15 and 8.16; exact period from risk assessment |
| PCI DSS 4.0 | 12 months total, 3 months immediately available | Applies to cardholder data environments |
| HIPAA | 6 years | For PHI-related audit logs |
| SOX | 7 years | For public companies; system change logs |
| EU AI Act Article 19 | 6 months minimum | High-risk AI systems; longer if required by other law |
| GDPR | Minimum needed for purpose | Storage limitation principle (Article 5(1)(e)) |

### 3.2 Recommended tiered retention for developer tooling

For a developer-facing agentic sandbox that is not handling PHI or financial data, the following three-tier strategy is practical:

| Tier | Duration | Storage | Query Latency | Purpose |
|---|---|---|---|---|
| Hot | 90 days | Elasticsearch or Loki | Seconds | Active incident response, debugging |
| Warm | 1 year total (90d–1yr) | S3 with Object Lock (Governance mode), Parquet files | Minutes | Compliance audits, retrospective analysis |
| Cold | 3 years total (1yr–3yr) | S3 with Object Lock (Compliance mode), compressed | Hours (Athena / S3 Select) | Training signal, long-term compliance, legal hold |

After 3 years: delete unless a legal hold has been applied (active incident, litigation, regulatory inquiry).

The 3-year cold retention enables a meaningful training corpus for policy refinement while not creating unlimited liability from perpetual behavioral log retention.

---

## 4. Access Control Policy

### 4.1 Role matrix

| Role | Read Hot | Read Warm | Read Cold | Write | Notes |
|---|---|---|---|---|---|
| Agent container (sandboxed) | No | No | No | No | Explicitly denied; logs written outside container |
| CI/CD pipeline (log collector) | No | No | No | Yes (append only) | Single-purpose service account; no delete |
| Developer (ticket author) | No | No | No | No | Privacy protection; use aggregate metrics only |
| Team lead / PR reviewer | No | No | No | No | Same as developer |
| Security engineer (on-call) | Yes (scoped to own sessions) | No | No | No | Scoped to session IDs they are investigating |
| Security incident responder | Yes (all) | Yes (all) | Yes (all) | No | Break-glass access; requires approval + MFA |
| Compliance auditor | Yes (sampled) | Yes | Yes | No | Time-bounded access grant |
| Policy refinement pipeline | Yes (anonymized) | Yes (anonymized) | No | No | Service account with read-only, anonymized view |
| Legal hold custodian | No | No | Yes (frozen) | No | Read-only access to specifically held sessions |

### 4.2 Segregation of duties

A core requirement: **the entity that produces a commit/PR must not be able to read or modify its own audit logs.** This prevents an agent or a compromised developer account from suppressing evidence of its own activity.

Enforce via separate AWS accounts (or GCP projects): the log storage account has no trust relationship with the agent execution account except for the one-way log-writer service account.

### 4.3 Break-glass access

Incident responders should access logs through a dedicated break-glass mechanism:
1. Request approval via a ticketing system (PagerDuty, Jira)
2. Receive a time-bounded (8-hour) IAM role assumption
3. All access itself is logged to a separate, higher-integrity audit stream
4. Access expires automatically; renewal requires re-approval

### 4.4 Preventing agent self-inspection

This is the most critical control for AI sandboxes. The eBPF/auditd log pipeline must run on the host (not in the container) and write to a network endpoint the container cannot reach:
- The log collector (Falcosidekick, Fluent Bit, Vector) runs as a privileged DaemonSet or host service
- The container's network egress policy (via Kubernetes NetworkPolicy or eBPF-enforced Cilium policy) blocks access to the log collector's endpoint and to the S3 log bucket
- The S3 bucket policy explicitly denies `s3:*` to the container's IAM role / service account

---

## 5. Immutable and Append-Only Log Storage

### 5.1 AWS S3 Object Lock

S3 Object Lock provides two retention modes:

- **Governance mode:** Protects against most users; users with `s3:BypassGovernanceRetention` permission can override. Suitable for warm tier (allows legal team to correct errors).
- **Compliance mode:** No user, including root, can delete or overwrite objects during the retention period. Suitable for cold tier and any logs that may be needed for litigation.

Legal holds can be applied per-object independently of retention periods; these block deletion indefinitely until the hold is removed, ideal for active incidents.

CloudTrail automatically logs all Object Lock API calls (retention changes, legal hold modifications), providing a meta-audit trail of the audit trail itself.

### 5.2 Azure Blob immutable storage

Azure offers time-based retention policies and legal hold policies on blob containers, with WORM semantics equivalent to S3 Object Lock. Supports locked policies that cannot be shortened, satisfying SEC 17a-4 requirements.

### 5.3 In-kernel cryptographic integrity (Nitro / Nitro-R)

The Nitro system (arxiv.org/html/2509.03821v1) implements forward-authenticating MAC-chain logging entirely within eBPF:
- Each log entry is tagged with a MAC derived from the previous tag (forward chain)
- Per-CPU parallel signing eliminates synchronization overhead
- Uses Chaskey (ISO-standard lightweight MAC), ~8x faster than AES without AES-NI
- Nitro-R adds in-kernel log deduplication via LRU hash maps, reducing I/O by 8x vs. eAudit-SEC
- Achieves 10-25x performance improvement over prior systems with near-zero data loss (vs. 31-98% loss in competing approaches)
- Provides tamper evidence: an auditor can extract all logs up to the point of tampering

For the container sandbox, deploying Nitro (or its open-source equivalent) at the host level provides cryptographic proof of log completeness, which is valuable both for incident response and for training signal integrity.

### 5.4 Append-only log aggregation pipeline

Recommended pipeline architecture:

```
Host kernel
  ├─ Falco daemon (syscall events)
  │    └─ Falcosidekick → JSON → S3 (Object Lock) + Elasticsearch/Loki
  ├─ Tetragon (eBPF events)  
  │    └─ tetra export → JSON → same pipeline
  └─ auditd (kernel audit)
       └─ audispd → audisp-remote → central auditd server
                                     └─ S3 (Object Lock)

Aggregation layer:
  Elasticsearch / Loki (hot/warm)
    └─ Index: session_id, container_id, ticket_id, pr_number
  S3 (cold, WORM)
    └─ Prefix: logs/<year>/<month>/<session_id>/
```

Integrity guarantees in the pipeline:
- TLS 1.3 for all transport (Falcosidekick → sink)
- Log collector authenticates to S3 via short-lived IAM role credentials (no long-lived keys)
- S3 bucket policy: deny `s3:DeleteObject`, `s3:PutObjectAcl`, `s3:PutBucketPolicy` to all except the compliance admin role
- Enable S3 Server-Side Encryption (SSE-KMS) with a customer-managed key; key policy restricts decryption to authorized roles only

---

## 6. Log Aggregation Pipeline

### 6.1 Component selection

| Component | Role | Integrity Feature |
|---|---|---|
| Falcosidekick | Falco event forwarding, fan-out to 50+ sinks | TLS mutual auth; JSON + CEF output |
| Vector (vectorized.dev) | High-throughput log routing from multiple sources | Disk buffer (prevents loss on restart); supports S3 with checksum |
| Fluent Bit | Lightweight agent for auditd and container logs | Supports TLS, output buffering |
| Elasticsearch | Hot/warm search and query | Role-based index access; field-level security |
| Grafana Loki | Cost-effective hot/warm log store (label-indexed, S3-backed) | S3 backend with Object Lock; cheaper than ES for append-only workloads |
| AWS S3 + Object Lock | Cold WORM archive | Compliance mode; CloudTrail meta-audit |
| AWS Athena | Ad-hoc cold-tier queries | Parquet + Snappy compression; no data movement |
| Splunk / Google Chronicle | Enterprise SIEM alternative | Built-in integrity checks; long retention |

### 6.2 Integrity guarantees in transit

- All log shippers must use TLS with certificate pinning or mutual TLS (mTLS) to prevent MITM interception
- Falco events should include a `sha256` hash of the raw event JSON before forwarding, stored as a field in the Elasticsearch document and also in the S3 object's user-defined metadata
- The S3 object's `ETag` (MD5 or SHA256 depending on upload type) provides an additional integrity check

### 6.3 Kubernetes-specific considerations

Kubernetes API audit events (from the API server) should be shipped alongside eBPF/auditd events. The API audit log captures pod creation, deletion, secret access, and RBAC changes—events that eBPF tools may not directly observe. Configuring `--audit-log-path`, `--audit-policy-file`, and `--audit-log-maxbackup` on the API server and shipping to the same pipeline ensures complete coverage.

---

## 7. Audit Logs as Training Signal for Policy Refinement

### 7.1 What patterns are useful

Audit logs from agent invocations provide a behavioral corpus for improving sandbox constraint policies:

| Log Pattern | Policy Signal |
|---|---|
| File paths accessed by successful invocations | Whitelist candidates for allowed paths |
| Network destinations contacted | Allowlist refinement for egress rules |
| Syscalls never triggered | Candidates for seccomp profile denial (reducing attack surface) |
| Syscalls only triggered during specific task types | Context-dependent policy rules |
| Failed syscalls (EPERM, EACCES) | Overly restrictive rules blocking legitimate operations |
| Anomalous process trees (unexpected children) | Detection rules for prompt injection / escape attempts |
| Volume/rate of file writes | Thresholds for resource limits |

The EASEAndroid approach (USENIX Security 2015) demonstrates that audit log analysis can automate policy refinement iteratively: start with a permissive policy, record what the agent actually does, tighten to the observed minimum, repeat.

### 7.2 Privacy and security implications of behavioral log retention

**Data sensitivity:** Agent command arguments, file paths, and network destinations may contain sensitive information: repository content, API keys passed as arguments, internal hostname patterns, or personal data in processed files.

**Mitigations before using logs as training data:**
- **Scrubbing:** Apply regex/NLP-based PII detection to `proc.cmdline`, `fd.name`, and network payload fields before writing to the training corpus
- **Aggregation:** Replace individual file paths with filesystem subtree labels (e.g., `/repo/src/**` → `source_file`) for policy training; preserve raw paths only in the incident-response-accessible hot tier
- **Differential privacy:** When training ML classifiers on behavioral logs, add calibrated noise to prevent memorization of specific invocation details
- **Purpose limitation:** The scrubbed training corpus must be stored separately from the raw audit logs, with its own access controls and retention schedule

**Risk of the agent reading its own training data:** If the policy refinement pipeline's output (updated seccomp profiles, network policies) is accessible to agents, a sufficiently capable agent could infer what behaviors the system is trying to detect and adapt accordingly. The training pipeline must be isolated from the agent runtime environment.

### 7.3 Labeling and feedback loop

For supervised policy refinement, logs need labels: was this invocation successful? Did it produce a correct PR? Was any security event flagged? These labels should be stored alongside the session ID in the correlation index, not embedded in the raw logs. A separate feedback service writes labels after PR review and merges them into the policy training dataset.

---

## 8. Legal and Compliance Considerations

### 8.1 GDPR

**Applicability:** Audit logs of AI agent activity are almost certainly personal data under GDPR if they contain: user-specific session information, filenames referencing individuals, network connections to user-identified services, or command-line arguments with personal identifiers.

**Key obligations:**
- **Article 5(1)(e) — Storage limitation:** Logs cannot be retained beyond what is necessary. Each retention tier must have a documented purpose that justifies it.
- **Article 5(1)(c) — Data minimization:** Collect only the fields needed. If network destination IPs are sufficient for security monitoring, avoid capturing full request bodies.
- **Article 13/14 — Transparency:** If the agent acts on behalf of end users (e.g., a developer's code), those users should be informed that behavioral logs are retained.
- **Article 32 — Security:** Encryption at rest and in transit, access controls, and integrity measures (WORM) satisfy the Article 32 "appropriate technical measures" requirement.

**Legal basis options:**
- **Legitimate interest (Article 6(1)(f)):** Security monitoring and incident response is a recognized legitimate interest for log retention. Document the balancing test showing security interest outweighs individual privacy impact.
- **Legal obligation (Article 6(1)(c)):** If the system is subject to NIS2, EU AI Act, or other regulations requiring log retention, this basis applies for that mandatory period.

**DPIA requirement:** A Data Protection Impact Assessment is required when processing involves "systematic monitoring" (Recital 91) — which automated eBPF logging of all agent actions arguably constitutes. Conduct the DPIA before deploying to production.

### 8.2 EU AI Act

**Article 12 (Record-keeping):** High-risk AI systems must be designed to automatically record events throughout their operation to ensure traceability. Logs must cover: system inputs, outputs, and operational parameters; events relevant to the system's risk level.

**Article 19 (Automatically generated logs):** Providers of high-risk AI systems must keep automatically generated logs for at least 6 months (or longer if required by other EU or national law). Deployers must keep logs for the period appropriate to their intended purpose, minimum 6 months.

**Classification:** An agentic AI system that writes code and submits PRs likely qualifies as high-risk under Annex III category 5 (employment/workers management) if used in employment contexts, or may be subject to transparency requirements under Article 52 if it interacts with humans. The sandbox itself, as critical infrastructure software, warrants high-risk treatment as a precaution.

**Applicability deadline:** Transparency and logging requirements of the AI Act apply from August 2026.

### 8.3 NIS2 Directive

NIS2 (effective October 2024 in EU member states) requires essential and important entities to implement security incident logging and to retain logs for at least 12 months in accessible form and 24 months in archived form. If the organization deploying this system qualifies as an essential/important entity, NIS2 sets a binding floor of 12 months hot + 24 months archived.

### 8.4 US considerations

- **CMMC / DFARS:** If handling Controlled Unclassified Information, NIST SP 800-171 requires 90-day minimum log retention (requirement 3.3.2).
- **SOC 2 Type II:** Most B2B SaaS customers will expect SOC 2 Type II, which requires demonstrating log retention and access controls over a 6–12 month audit period.
- **eDiscovery / litigation hold:** US Federal Rules of Civil Procedure require preservation of electronically stored information once litigation is reasonably anticipated. The legal hold mechanism in S3 Object Lock (or equivalent) should be triggerable by counsel without requiring engineering changes.

---

## 9. Implementation Checklist

- [ ] Assign `session_id` (UUIDv7) at container start; inject into pod labels and environment
- [ ] Write `Agent-Session-Id: <id>` to git commit trailers in every agent-produced commit
- [ ] Store correlation index record `{session_id, pr_number, commit_sha, ticket_id}` in log bucket at invocation close
- [ ] Deploy Falco + Tetragon as host-level DaemonSets; configure Falcosidekick to write to Elasticsearch (hot) and S3 (cold)
- [ ] Configure S3 bucket with Object Lock: Governance mode for warm tier, Compliance mode for cold tier
- [ ] Apply bucket policy denying all deletes and writes except from the log-writer service account
- [ ] Enable SSE-KMS on log bucket; restrict KMS key policy to authorized decryption roles
- [ ] Implement network egress deny rules preventing agent containers from reaching log endpoints or log bucket
- [ ] Define RBAC roles: log-writer (collector), log-reader-incident (security team, break-glass), log-reader-audit (compliance)
- [ ] Implement break-glass access with approval workflow and automatic 8-hour expiry
- [ ] Document retention schedule with per-tier purposes for GDPR legitimate interest balancing test
- [ ] Conduct DPIA before production deployment
- [ ] Scrub PII from logs before use as policy training signal; store scrubbed corpus separately
- [ ] Test log integrity by attempting deletion/modification as the agent's service account (should fail)

---

## Sources

- [Falco Supported Fields for Conditions and Outputs](https://falco.org/docs/reference/rules/supported-fields/)
- [Falco Kubernetes Audit Events plugin](https://falco.org/docs/concepts/event-sources/plugins/kubernetes-audit/)
- [Falco Supported Events (syscall types)](https://falco.org/docs/reference/rules/supported-events/)
- [Tetragon Events documentation](https://tetragon.io/docs/concepts/events/)
- [Container Runtime Security with Tetragon and Falco: A Modern Approach](https://mangohost.net/blog/container-runtime-security-with-tetragon-falco-a-modern-approach/)
- [How to Implement Security Monitoring with eBPF (Falco, Tetragon)](https://oneuptime.com/blog/post/2026-01-07-ebpf-security-monitoring-falco-tetragon/view)
- [Falcosidekick — Connect Falco to your ecosystem](https://github.com/falcosecurity/falcosidekick)
- [Falco vs. Tetragon: A Runtime Security Showdown for Kubernetes](https://medium.com/@mughal.asim/falco-vs-tetragon-a-runtime-security-showdown-for-kubernetes-a0e9fb9f30a0)
- [Rethinking Tamper-Evident Logging: A High-Performance, Co-Designed Auditing System (Nitro)](https://arxiv.org/html/2509.03821v1)
- [Security log retention: Best practices and compliance guide](https://optro.ai/blog/security-log-retention-best-practices-guide)
- [SOC 2 Data Retention Guide: Key Requirements, Steps, and Templates](https://www.konfirmity.com/blog/soc-2-data-retention-guide)
- [ISO 27001 Logging and Monitoring Policy: Requirements, Objectives, and Best Practices](https://sprinto.com/blog/iso-27001-logging-and-monitoring-policy/)
- [ISO 27001 Audit Record Retention Requirements](https://www.ignyteplatform.com/blog/iso-27001/iso-27001-record-retention/)
- [NIST Special Publication 800-92, Guide to Computer Security Log Management](https://csrc.nist.gov/pubs/sp/800/92/final)
- [NIST SP 800-92r1 (Draft), Cybersecurity Log Management Planning Guide](https://csrc.nist.gov/pubs/sp/800/92/r1/ipd)
- [AWS S3 Object Lock — Locking objects with Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
- [Protecting data with Amazon S3 Object Lock](https://aws.amazon.com/blogs/storage/protecting-data-with-amazon-s3-object-lock/)
- [Ensuring Compliance with Tamper-Proof Logging in AWS & Azure](https://pwnsentinel.org/2025/07/18/tamper-proof-logging/)
- [Immutable Audit Logs AWS S3 Read-Only Roles](https://hoop.dev/blog/immutable-audit-logs-aws-s3-read-only-roles-secure-your-data-and-compliance/)
- [Azure Blob immutable storage overview](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview)
- [OpenTelemetry Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [Correlate OpenTelemetry Traces and Logs](https://docs.datadoghq.com/opentelemetry/correlate/logs_and_traces/)
- [Zero-Code Distributed Tracing for Kubernetes with eBPF](https://logz.io/blog/ebpf-integration/)
- [Audit Trails in CI/CD: Best Practices for AI Agents](https://prefactor.tech/blog/audit-trails-in-ci-cd-best-practices-for-ai-agents)
- [How to Monitor and Audit AI Decisions in a CI/CD Pipeline](https://semaphore.io/how-to-monitor-and-audit-ai-decisions-in-a-ci-cd-pipeline)
- [The Critical Role of RBAC-Powered Audit Logs in Security and Compliance](https://hoop.dev/blog/the-critical-role-of-rbac-powered-audit-logs-in-security-and-compliance/)
- [How to Set Up RBAC for Logs (Datadog)](https://docs.datadoghq.com/logs/guide/logs-rbac/)
- [Bringing Cloud-Managed Kubernetes Audit Logs into Elasticsearch](https://www.elastic.co/observability-labs/blog/bringing-your-cloud-managed-kubernetes-audit-logs-into-elasticsearch)
- [Grafana Loki with AWS S3 backend](https://medium.com/techlogs/grafana-loki-with-aws-s3-backend-through-irsa-in-aws-kubernetes-cluster-93577dc482a)
- [AI Agent Compliance: GDPR, SOC 2, and Beyond](https://www.mindstudio.ai/blog/ai-agent-compliance)
- [How to Make AI Agents GDPR-Compliant](https://heydata.eu/en/magazine/how-to-make-ai-agents-gdpr-compliant/)
- [Engineering GDPR compliance in the age of agentic AI (IAPP)](https://iapp.org/news/a/engineering-gdpr-compliance-in-the-age-of-agentic-ai)
- [EU AI Act Article 12: Record-Keeping](https://artificialintelligenceact.eu/article/12/)
- [EU AI Act Article 19: Automatically Generated Logs](https://artificialintelligenceact.eu/article/19/)
- [EU AI Act Compliance: Requirements, Risks, and What to Document](https://goteleport.com/blog/eu-ai-act-requirements/)
- [EU AI Act 2026 Updates: Compliance Requirements and Business Risks](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks/)
- [Audit Logging for AI and LLM Systems: Essential Security](https://www.datasunrise.com/knowledge-center/ai-security/audit-logging-for-ai-llm-systems/)
- [EASEAndroid: Automatic Policy Analysis and Refinement for Security](https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-wang-ruowen.pdf)
- [WORM vs. Audit-Trail: How to Decide Which 17a-4 Storage Method Fits Your Architecture](https://www.luthor.ai/guides/worm-vs-audit-trail-17a-4-storage-method-2025-architecture)
- [Get started with eBPF log analytics in Kubernetes cluster](https://www.parseable.com/blog/ebpf-log-analytics-in-kubernetes-cluster)
