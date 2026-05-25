# Q21: Real-Time Alerting vs. Post-Hoc Analysis for Container Sandbox Security

**Question:** Is real-time alerting required, or is post-hoc analysis sufficient? Falco supports real-time rule-based alerting and can kill containers. auditd is primarily for post-hoc review. Does the system need to stop or kill a container mid-run if a violation is detected, or is it sufficient to flag it after the fact?

---

## Summary and Recommendation

**Recommendation: A hybrid approach is the right architecture.** Pure post-hoc analysis is insufficient for the highest-severity threat classes (active network exfiltration, privilege escalation, container escape attempts). Pure real-time enforcement for all events is operationally dangerous due to false positive costs in agentic AI workloads. The system should implement:

1. **Real-time enforcement for a small set of high-confidence, high-severity violations** — specifically: successful outbound connections to explicitly blocked IP ranges/ports, privilege escalation attempts (setuid, capability changes), and container escape indicators. These are the scenarios where even a few seconds of post-hoc lag materially worsens outcomes.

2. **Real-time alerting with human-in-the-loop response for medium-severity events** — suspicious file reads, unexpected process spawns, anomalous DNS query patterns. Falco + Falco Talon can act in milliseconds, but for ambiguous events an approval gate is safer than automatic kill.

3. **Post-hoc analysis (auditd/eBPF logs) for all other events** — baseline behavior tracking, forensics, retrospective investigation, and improving the real-time ruleset over time.

The PR review gate is a meaningful control for code-push threats but is insufficient on its own when network exfiltration is the threat model, since data can leave in seconds over a direct TCP connection before a PR is even created.

---

## Detailed Findings

### 1. Falco's Real-Time Kill/Response Capability

**Architecture.** Falco operates as a kernel-layer behavioral monitor. Its eBPF or kernel module driver captures syscalls in the kernel and pushes events to userspace, where libscap and libsinsp enrich and filter events before the rule engine evaluates them and generates alerts. The pipeline is detection-oriented, not enforcement-oriented: Falco itself cannot kill containers inline. It generates alerts and routes them to output channels (stdout, file, syslog, HTTP, gRPC API).

**Automated response via Falco Talon.** Falco Talon (officially integrated into the falcosecurity project as of 2024, v0.1.x) is the response engine that closes the gap. The event flow is:

```
Kernel event -> Falco rule match -> alert -> Falcosidekick -> Falco Talon -> Kubernetes API (kill pod / apply NetworkPolicy / add label)
```

Talon receives events from Falco via HTTP, processes them through an internal NATS JetStream-based queue for deduplication, and executes matched rule actions. Available actions include `kubernetes:terminate` (sends SIGTERM then SIGKILL), `kubernetes:networkpolicy` (isolates the pod), `kubernetes:label`, and forensic data collection.

**Latency.** Falco's kernel detection of a syscall violation occurs in milliseconds — the eBPF driver captures the event in the kernel immediately. The end-to-end pipeline (kernel capture → userspace enrichment → rule evaluation → Falcosidekick → Talon → Kubernetes API call → pod killed) adds several hundred milliseconds to a few seconds of additional latency due to the HTTP forwarding hops and the Kubernetes API round trip. Talon's own documentation states it can "react to events from Falco in milliseconds," which refers to Talon's internal processing time, not the full end-to-end wall-clock time from violation to pod termination. For practical purposes, a container performing a prohibited action will complete that individual syscall before it is killed — Falco + Talon is a detect-and-respond stack, not an inline enforcement stack.

**False positive handling.** Talon rules support exclusion conditions (e.g., exempting specific Kubernetes namespaces like `kube-system` from kill actions). Granular rule matching is required before enabling terminate actions in production.

**Sources:**
- [Falco documentation](https://falco.org/docs/)
- [Falco Talon v0.1.0 announcement](https://falco.org/blog/falco-talon-v0-1-0/)
- [Falco Talon GitHub](https://github.com/falcosecurity/falco-talon)
- [Why Falco's new response engine is a game changer (CNCF, 2024)](https://www.cncf.io/blog/2024/11/06/why-falcos-new-response-engine-is-a-game-changer-for-open-source-cloud-native-security/)
- [What is Falco? (Sysdig)](https://www.sysdig.com/learn-cloud-native/what-is-falco)

---

### 2. Tetragon's Enforcement Mode: True Inline Blocking

**Architecture difference.** Tetragon (Cilium project) is architecturally distinct from Falco in enforcement capability. Tetragon uses eBPF hooks at the kernel function level (not just syscall boundaries) and performs filtering, blocking, and enforcement entirely within the kernel — no userspace round-trip is needed to make an enforcement decision.

**Two enforcement mechanisms:**
- **Return value override:** Tetragon overrides the return value of a kernel function so that the function never actually executes. The calling process receives an error code. This is truly inline — the operation is prevented, not just detected.
- **Signal-based enforcement:** Tetragon issues a SIGKILL to the offending process. If triggered through a syscall, the application never returns from that syscall and is immediately terminated. The Tetragon documentation notes that SIGKILL alone does not always prevent the operation from completing, and recommends combining it with return-value override for full prevention.

**Performance.** Tetragon runs at less than 1% overhead via eBPF kernel hooks. Its in-kernel filtering also reduces the volume of events transmitted to userspace, improving observability throughput for the events that do get forwarded.

**Practical enforcement examples:**
- **Network egress blocking:** A tracing policy (`network_egress_cluster_enforce.yaml`) can block all TCP connections outside the cluster. When a pod's `curl` command attempts an egress connection violating the policy, it receives SIGKILL before the TCP handshake completes. The `tetra` CLI annotates the event as blocked.
- **File access restriction:** Policies preventing reads of `/etc/shadow` or other sensitive paths result in process termination before the read completes.
- **Kubernetes-aware scoping:** Tetragon policies can target specific namespaces, pod labels, or workload identities, enabling fine-grained enforcement rather than cluster-wide blocking.

**When enforcement is appropriate vs. observation-only:**
- Observation-only: establishing behavioral baselines, forensic analysis, understanding what "normal" looks like before writing enforcement policies, troubleshooting.
- Enforcement: when the violation class is well-defined, high-confidence, and the cost of a false kill is lower than the cost of allowing the action to complete.

**Sources:**
- [Tetragon enforcement documentation](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon getting started: enforcement](https://tetragon.io/docs/getting-started/enforcement/)
- [Tetragon overview](https://tetragon.io/docs/overview/)
- [Isovalent Tetragon introduction](https://isovalent.com/blog/post/2022-05-16-tetragon/)
- [Falco vs. Tetragon comparison (Medium)](https://medium.com/@mughal.asim/falco-vs-tetragon-a-runtime-security-showdown-for-kubernetes-a0e9fb9f30a0)

---

### 3. The Damage Window Problem

**How fast can an adversarial agent cause harm?**

The damage window question depends heavily on the threat class:

**Direct TCP/HTTP exfiltration (fastest).** A process with outbound network access can open a TCP connection, send data, and close the connection in milliseconds to seconds. A small secret (API key, private key, environment variables) is under 4KB and can be exfiltrated in a single TCP segment — wall-clock time under 100ms on a LAN or under 1 second to a remote server. By the time Falco + Talon detects and kills the container (seconds), the exfiltration is complete. **Post-hoc detection does not prevent this; it only confirms it happened.**

**DNS exfiltration (slower, stealthier).** DNS-based exfiltration encodes data in query subdomains (e.g., `base64encodeddata.attacker.com`). DNS queries are small (each carries ~50-200 bytes of exfiltrated data) and must wait for DNS resolution timeouts and response cycles. Transfer of meaningful data (e.g., an SSH private key at ~3KB) requires tens to hundreds of queries. Real-world DNS exfiltration tools operate at low throughput intentionally to evade volume-based detection. This threat model favors detection over time rather than instant response — the damage window is longer, but so is the detection window. Post-hoc analysis is more viable here if DNS query logging is comprehensive.

**Malicious code push.** An agent that pushes a commit to a repository has a different threat model. The agent must: (1) stage changes, (2) commit, (3) push to remote, and (4) hope a CI/CD pipeline or human merges the code without scrutiny. Steps 1–3 are git operations that complete in seconds and are fully captured in the audit trail. Step 4 requires a PR review gate. **The PR review gate is meaningful here** — it breaks the threat's blast radius at the point where code enters a shared branch. However, if the agent has permissions to push directly to main (bypassing review), the gate is absent, and the code could be deployed before post-hoc review catches it. Real-time monitoring of git push operations can alert immediately, but the actual harm (code execution in production) may not occur for minutes or hours.

**Privilege escalation / container escape.** These are the most time-sensitive. A successful container escape gives an attacker access to the host. This can happen in sub-second to a few seconds depending on the exploit. Post-hoc detection is far too slow to prevent the escape from completing. Real-time enforcement (Tetragon blocking the relevant syscalls or capability changes) is materially better here.

**Unauthorized sensitive file reads.** Reading `/etc/passwd`, `/proc/*/environ`, or a mounted secret happens in a single `open()`/`read()` syscall. The data is read before any userspace detection tool can react. However, the attacker must then exfiltrate that data (covered above). Real-time blocking of the read prevents the attacker from obtaining the data even if they already have code execution.

**Summary of damage window by threat class:**

| Threat | Data stolen before kill? | Post-hoc sufficient? | Real-time value |
|---|---|---|---|
| Direct TCP exfiltration (small secret) | Yes, likely | No | High — block the connection |
| DNS exfiltration | Partial (slow) | Yes, with comprehensive DNS logging | Medium |
| Malicious git push (with PR gate) | N/A — gate holds | Yes | Low-Medium |
| Malicious git push (direct to main) | N/A | No | Medium |
| Privilege escalation | Exploit completes in ms | No | Very high |
| Container escape | Escape completes in ms | No | Very high |
| Sensitive file read | Read completes before kill | No | High — block at open() |

**Sources:**
- [Data exfiltration speed: attackers steal data in under 2 days (Vectra AI)](https://www.vectra.ai/topics/exfiltration)
- [DNS exfiltration mechanics (Akamai)](https://www.akamai.com/glossary/what-is-dns-data-exfiltration)
- [DNS tunneling throughput (Palo Alto Unit 42)](https://unit42.paloaltonetworks.com/dns-tunneling-how-dns-can-be-abused-by-malicious-actors/)
- [DNS exfiltration detection (BlackFog)](https://www.blackfog.com/dns-exfiltration-how-hackers-use-your-network-to-steal-data-without-detection/)
- [Supply chain attack PR manipulation (GitHub Blog)](https://github.blog/security/supply-chain-security/securing-the-open-source-supply-chain-across-github/)

---

### 4. Real-Time Response Tradeoffs: The Cost of False Positive Kills

**What happens when an agent container is incorrectly killed.**

For agentic AI workloads, killing a container mid-run is significantly more disruptive than killing a typical stateless web server replica. An agent container:
- May have accumulated expensive intermediate state (LLM context, partial tool results, in-progress file writes)
- Is not trivially replaceable — the task must restart from scratch or from a checkpoint
- May have already performed irreversible external actions (sent an email, pushed a commit) that are now inconsistent with the aborted task state
- Will require the orchestrating human or system to re-queue and re-run the task, costing compute time and LLM API spend

This means the false-positive cost for agent containers is higher than for short-lived stateless workloads.

**Industry practice for managing false positives.**

All major CWPP vendors (Aqua Security, Prisma Cloud/Palo Alto, Wiz) implement a two-mode architecture:
- **Audit mode:** alert only, never block. Used to establish baselines, tune rules, validate that the ruleset is not noisy before enabling enforcement.
- **Enforce/Block mode:** active blocking. Only enabled once the team has high confidence in the rule quality.

Aqua Security's workshop documentation explicitly describes this: "Any violation of the policy automatically generates an alert and is blocked if the policy is in Enforce mode." The recommended onboarding is always to start in Audit mode.

Prisma Cloud uses behavioral modeling (learning mode) to establish what "normal" looks like for a specific container image, then enforcement policies are anchored to the learned baseline rather than generic rules. This reduces false positives for known workloads.

The industry consensus from Falco's own documentation, Aqua Security, and platform engineering practitioners is that **enforcement should be reserved for high-confidence, high-severity violations** — typically privilege escalation, container escape attempts, and connections to explicitly blocked network destinations.

**Sources:**
- [Aqua Security runtime policy enforcement modes](https://aqua.awsworkshop.io/runtime_security/runtime_policies.html)
- [Runtime security monitoring: protecting production without slowing developers](https://platformengineering.org/blog/runtime-security-monitoring-and-threat-detection-protecting-production-without-slowing-developers)
- [Prisma Cloud runtime defense for containers](https://docs.prismacloud.io/en/compute-edition/30/admin-guide/runtime-defense/runtime-defense-containers)
- [Container security monitoring (ShieldNet360)](https://shieldnet360.com/resources/blog/container-security-monitoring-signals-alerts-automation-en-853)

---

### 5. Real-Time Response per Threat Scenario

**Scenario A: DNS exfiltration**

DNS exfiltration operates slowly by design. Volume-based or entropy-based detection (identifying base64-encoded data in subdomains, unusually long query names, high query rates to a single domain) is the primary countermeasure. Because individual queries carry little data, real-time kill on the first suspicious query would generate false positives (many legitimate tools make unusual DNS queries). The better approach is:
- Log all DNS queries (auditd or eBPF network events)
- Apply heuristic/ML detection post-hoc or with a short time window (5–60 seconds)
- If the heuristic fires with high confidence, kill the container in real-time via Falco Talon or Tetragon
- Block DNS for all containers except an allow-listed resolver, preventing custom DNS over arbitrary port 53 to attacker-controlled servers

**Conclusion:** Post-hoc with delayed real-time response (detect pattern over seconds, then kill) is appropriate. Pure instant kill on first query is too aggressive.

**Scenario B: Unauthorized outbound TCP/HTTP connection**

This is the scenario where real-time enforcement provides the most material value. If a container makes a TCP connection to an address outside the allowed egress list, the data is gone within the time it takes to send a single packet. Tetragon's egress enforcement policy can prevent the TCP connection from being established at all — the connect() syscall is denied before the handshake completes. This is categorically better than post-hoc detection.

**Conclusion:** Real-time enforcement (Tetragon egress policy, or a strict Kubernetes NetworkPolicy as a first layer) is the right control. Falco + Talon detection-and-kill is a slower fallback but still valuable for detecting policy bypass attempts.

**Scenario C: Reading sensitive files (secrets, credentials)**

A single `open()` + `read()` completes in microseconds. No post-hoc or detect-and-respond system is fast enough to prevent the read from completing. However, if the egress network path is blocked, the attacker must still get the data out — and that exfiltration is where real-time enforcement can stop the threat. The defense-in-depth model here is: (1) restrict sensitive file mounts to only what the agent legitimately needs, (2) enforce egress network restrictions to prevent exfiltration even if a read succeeds, (3) use auditd/eBPF to log all sensitive file reads for post-hoc forensics.

**Conclusion:** Post-hoc logging plus real-time network enforcement together are sufficient. Real-time blocking of the read itself requires Tetragon enforcement on `security_file_permission`, which is feasible but requires careful policy definition to avoid blocking legitimate agent operations.

**Scenario D: Privilege escalation or container escape attempt**

These are the clearest case for real-time enforcement. A setuid execution or kernel exploit can succeed in milliseconds. Post-hoc analysis will confirm what happened but cannot roll back a host compromise. Tetragon's capability enforcement (blocking `CAP_SYS_ADMIN`, preventing namespace crossings, blocking known escape syscall sequences) is the appropriate tool. Falco's rules for privilege escalation (detecting `ptrace` anti-debug, `nsenter`, `mount` of host filesystem) plus Talon's kill action is a reasonable fallback if Tetragon is not deployed.

**Conclusion:** Real-time enforcement is strongly preferred. Post-hoc analysis is insufficient.

---

### 6. Hybrid Approach in Practice

The industry-standard hybrid model is well-established across Aqua Security, Prisma Cloud, Falco/Talon, and Tetragon deployments:

**Phase 1 — Audit mode only (initial deployment).**
Deploy Falco and/or Tetragon in observation-only mode. Collect all events. Establish what the agent containers legitimately do. Identify which rules produce false positives. Tune the ruleset. This phase typically takes 2–4 weeks for a new workload type.

**Phase 2 — Real-time alerting, no auto-kill.**
Enable Falco rules and route alerts to human reviewers. Falco Talon is configured to log and notify but not terminate. Validates that the alert stream is actionable and not noisy.

**Phase 3 — Selective enforcement for highest-severity events.**
Enable real-time enforcement (Tetragon enforcement policies or Falco Talon kill actions) only for rules that have demonstrated high confidence and low false positive rate. Typical candidates:
- Outbound connection to explicitly blocked IP/port (high confidence — either it's on the block list or it isn't)
- Privilege escalation attempts (high confidence — agent containers should never need setuid)
- Container escape indicators (high confidence — legitimate agents don't need `nsenter` or host filesystem mounts)

**Phase 4 — Post-hoc analysis pipeline for all other events.**
All eBPF/auditd events flow into a SIEM or log store. Analysts review aggregate patterns (anomalous DNS queries over time, unusual process tree structures, repeated failed read attempts on sensitive paths). Post-hoc findings drive new rules for Phase 3.

**Key design principle from practitioners:** Enforce selectively on events where the action is irreversible and the confidence is high. For everything else, alert and investigate. The `platformengineering.org` guidance articulates this as: automate actions that are "reversible and scoped (such as isolating a single pod, applying a temporary network policy, or revoking a suspicious session)" rather than blanket blocking.

---

### 7. How Production Security Systems Handle Real-Time vs. Post-Hoc

**Aqua Security.** Implements Audit and Enforce modes per policy. Policies are first deployed in Audit to collect baselines, then switched to Enforce for specific high-confidence rule sets. Aqua's eBPF-based detection (via Aqua Nautilus research) provides real-time visibility; the Enforcer agent implements actual blocking. False positives are managed by anchoring policies to profiled container behavior.

**Prisma Cloud (Palo Alto Networks).** Offers both agentless (post-hoc, slower) and agent-based (real-time, deeper) protection from the same management plane. Runtime defense includes a learning mode that profiles expected process, network, and filesystem behavior, then surfaces anomalies. Enforcement is opt-in per workload, not default-on. The agent-based mode enables preventive policies.

**Microsoft Defender for Containers.** Primarily a detect-and-alert platform with integration to Azure Policy for enforcement. Leans heavily on post-hoc analysis and integration with Microsoft Sentinel for SIEM-based response. Real-time response relies on automation rules in Sentinel, not inline kernel enforcement.

**Wiz (agentless CSPM/CWPP).** Agentless scanning means detection is inherently post-hoc — Wiz snapshots cloud resources and scans them out-of-band. Wiz does not perform real-time enforcement. It is explicitly a post-hoc detection and risk prioritization tool. This is appropriate for many threat classes (misconfiguration, vulnerability scanning) but not for runtime behavior enforcement.

**CrowdStrike Falcon (container sensor).** Combines EDR-style behavioral detection with automated response playbooks. The Falcon sensor operates at the kernel level and can terminate processes in real-time. CrowdStrike's approach is closer to Tetragon in architecture — kernel-level agent with enforcement capability — though proprietary.

**Common pattern across all vendors:** The default deployment is audit/detect-only. Enforcement is a deliberately configured opt-in, typically restricted to the highest-severity violation classes. No production CWPP vendor ships with kill-on-any-violation as the default.

**Sources:**
- [Prisma Cloud container security](https://www.paloaltonetworks.com/prisma/cloud/container-security)
- [Aqua Security cloud workload protection](https://www.aquasec.com/products/cwpp-cloud-workload-protection/)
- [Top container security solutions 2026 (SentinelOne)](https://www.sentinelone.com/cybersecurity-101/cloud-security/container-security-solutions/)
- [Microsoft Defender for Containers](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-containers-introduction)
- [Runtime visibility and AI-powered security (Cloud Native Now)](https://cloudnativenow.com/features/runtime-visibility-ai-powered-security-in-cloud-native-environments/)

---

### 8. eBPF Enforcement (Tetragon, Cilium) vs. Audit-Only eBPF (Falco): Architectural Difference

Both Falco and Tetragon use eBPF to capture kernel events, but they differ fundamentally in where the enforcement decision is made:

**Falco (audit-oriented eBPF).**
- eBPF program captures events and sends them to a userspace ring buffer
- Userspace process (libsinsp) applies rules, generates alerts
- Response (if any) requires an external tool (Falco Talon) making a Kubernetes API call
- The syscall that triggered the alert has already completed by the time the alert fires
- Latency from event to kill: seconds (kernel capture → userspace enrichment → alert → Sidekick → Talon → Kubernetes API → pod kill)
- Appropriate for: broad behavioral visibility, integration with existing SIEM/alerting, detection of complex multi-step patterns

**Tetragon (enforcement-capable eBPF).**
- eBPF program hooks kernel functions at the exact point of execution
- Enforcement decision is made in-kernel, synchronously
- The syscall is either blocked (return value override) or the process is killed before returning from the syscall
- No userspace round-trip for the enforcement decision
- Latency from violation to enforcement: sub-millisecond (in-kernel)
- Appropriate for: categorical policies where false positives are low (block connection to blocked-list IP, kill process if it attempts to escape namespace), especially where the first occurrence of the violation is itself unacceptable

**KubeArmor** (not covered in depth here) is another enforcement-capable eBPF tool that implements Linux Security Module (AppArmor/SELinux) enforcement via eBPF, providing an alternative enforcement mechanism.

**The key architectural question is: can you tolerate even one occurrence of the violation before detection?**
- If yes (e.g., one DNS query is tolerable; you care about patterns): Falco + post-hoc analysis is appropriate.
- If no (e.g., one successful egress connection to an attacker server is unacceptable): Tetragon egress enforcement is required.

**Sources:**
- [Falco vs. Tetragon (Medium)](https://medium.com/@mughal.asim/falco-vs-tetragon-a-runtime-security-showdown-for-kubernetes-a0e9fb9f30a0)
- [Best eBPF security solutions (ARMO)](https://www.armosec.io/blog/best-ebpf-security-solutions-runtime-protection/)
- [How to implement security monitoring with eBPF (OneUptime)](https://oneuptime.com/blog/post/2026-01-07-ebpf-security-monitoring-falco-tetragon/view)
- [Tetragon eBPF observability (CoreWeave)](https://docs.coreweave.com/security/tutorials/ebpf-observability)

---

## Decision Framework for the Container Sandbox System

Based on the above findings, the container sandbox system should implement:

| Event Class | Tool | Mode | Rationale |
|---|---|---|---|
| Outbound TCP to blocked IP/port | Tetragon (or NetworkPolicy) | Inline enforce — block connection | Single packet can complete exfiltration; post-hoc too slow |
| Privilege escalation (setuid, cap changes) | Tetragon | Inline enforce — kill process | Escape completes before post-hoc response |
| Container escape indicators (nsenter, host mount) | Tetragon | Inline enforce — kill process | Host compromise is irreversible |
| DNS queries (all) | auditd / eBPF observability | Post-hoc analysis + pattern detection | DNS exfiltration is slow; false kill risk high on single query |
| Sensitive file reads | auditd / eBPF observability | Post-hoc logging; pair with egress block | Read completes in microseconds; egress block is the real control |
| Unexpected process spawns | Falco | Alert + human review | Context-dependent; false kill risk for agent workflows |
| Git operations (push, commit) | auditd / eBPF observability | Post-hoc + PR gate | PR review gate is effective; audit trail sufficient |
| Anomalous network volume | Falco + Talon | Alert → human-gated kill | Pattern requires time window; not instant |

**The PR review gate is sufficient for code push threats provided:** (1) branch protection prevents direct pushes to main, (2) the CI/CD pipeline runs SAST/scanning on PR content, and (3) the agent container's outbound network is restricted so it cannot exfiltrate credentials that would enable bypassing the gate. The gate alone is not sufficient if the agent has unrestricted network egress, because secrets can be sent out before the PR is reviewed.

---

## Sources

All URLs cited in this document:

- [Falco documentation](https://falco.org/docs/)
- [Falco GitHub](https://github.com/falcosecurity/falco)
- [Falco Talon v0.1.0 announcement](https://falco.org/blog/falco-talon-v0-1-0/)
- [Falco Talon GitHub](https://github.com/falcosecurity/falco-talon)
- [Why Falco Talon is a game changer (CNCF, 2024)](https://www.cncf.io/blog/2024/11/06/why-falcos-new-response-engine-is-a-game-changer-for-open-source-cloud-native-security/)
- [What is Falco? (Sysdig)](https://www.sysdig.com/learn-cloud-native/what-is-falco)
- [Tetragon home](https://tetragon.io/)
- [Tetragon enforcement concepts](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon getting started: enforcement](https://tetragon.io/docs/getting-started/enforcement/)
- [Tetragon overview](https://tetragon.io/docs/overview/)
- [Tetragon GitHub](https://github.com/cilium/tetragon)
- [Isovalent Tetragon introduction (2022)](https://isovalent.com/blog/post/2022-05-16-tetragon/)
- [Falco vs. Tetragon comparison (Medium)](https://medium.com/@mughal.asim/falco-vs-tetragon-a-runtime-security-showdown-for-kubernetes-a0e9fb9f30a0)
- [How to implement security monitoring with eBPF: Falco and Tetragon](https://oneuptime.com/blog/post/2026-01-07-ebpf-security-monitoring-falco-tetragon/view)
- [Best eBPF security solutions for Kubernetes (ARMO)](https://www.armosec.io/blog/best-ebpf-security-solutions-runtime-protection/)
- [Tetragon eBPF observability (CoreWeave)](https://docs.coreweave.com/security/tutorials/ebpf-observability)
- [eBPF security with Tetragon (mylinux.work)](https://mylinux.work/guides/ebpf-security-with-tetragon/)
- [DNS exfiltration: how attackers steal data (DeepStrike)](https://deepstrike.io/blog/what-is-dns-data-exfiltration)
- [What is DNS data exfiltration? (Akamai)](https://www.akamai.com/glossary/what-is-dns-data-exfiltration)
- [DNS exfiltration without detection (BlackFog)](https://www.blackfog.com/dns-exfiltration-how-hackers-use-your-network-to-steal-data-without-detection/)
- [DNS tunneling: how DNS can be abused (Palo Alto Unit 42)](https://unit42.paloaltonetworks.com/dns-tunneling-how-dns-can-be-abused-by-malicious-actors/)
- [DNS exfiltration attack prevention (Indusface)](https://www.indusface.com/learning/dns-exfiltration-attack/)
- [Data exfiltration attackers steal in under 2 days (Vectra AI)](https://www.vectra.ai/topics/exfiltration)
- [Data exfiltration threats and defenses (OffensiveBytes)](https://offensivebytes.com/data-exfiltration-in-modern-environments)
- [Aqua Security runtime policy enforcement](https://aqua.awsworkshop.io/runtime_security/runtime_policies.html)
- [Aqua Security cloud workload protection](https://www.aquasec.com/products/cwpp-cloud-workload-protection/)
- [Aqua Security container security](https://www.aquasec.com/products/container-security/)
- [Prisma Cloud container security](https://www.paloaltonetworks.com/prisma/cloud/container-security)
- [Prisma Cloud runtime defense for containers](https://docs.prismacloud.io/en/compute-edition/30/admin-guide/runtime-defense/runtime-defense-containers)
- [Runtime security monitoring: protecting production without slowing developers](https://platformengineering.org/blog/runtime-security-monitoring-and-threat-detection-protecting-production-without-slowing-developers)
- [Top container security solutions 2026 (SentinelOne)](https://www.sentinelone.com/cybersecurity-101/cloud-security/container-security-solutions/)
- [Microsoft Defender for Containers](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-containers-introduction)
- [Runtime visibility and AI-powered security in cloud-native environments (Cloud Native Now)](https://cloudnativenow.com/features/runtime-visibility-ai-powered-security-in-cloud-native-environments/)
- [Container security monitoring: signals, alerts, automation (ShieldNet360)](https://shieldnet360.com/resources/blog/container-security-monitoring-signals-alerts-automation-en-853)
- [Securing Kubernetes runtime with Falco (Skyu)](https://skyu.io/blogs/securing-kubernetes-runtime-with-falco/)
- [Kubernetes runtime security with Falco (nCluster)](https://ncluster.tech/blog/kubernetes-runtime-security-falco/)
- [How to sandbox AI agents in 2026 (Northflank)](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Agent sandbox security (AgentWiki)](https://agentwiki.org/agent_sandbox_security)
- [Supply chain attacks on GitHub Actions (GitHub Blog)](https://github.blog/security/supply-chain-security/securing-the-open-source-supply-chain-across-github/)
- [AI-assisted supply chain attack targets GitHub (Dark Reading)](https://www.darkreading.com/application-security/ai-assisted-supply-chain-attack-targets-github)
- [Understanding current threats to Kubernetes environments (Palo Alto Unit 42)](https://unit42.paloaltonetworks.com/modern-kubernetes-threats/)
