# Q20: Alertable Events vs. Expected Behavior — Per-Role Thresholds and Notification Routing

**Research date:** 2026-04-18
**Question:** A research agent making many outbound DNS queries is expected. The same pattern from an implement agent may indicate DNS exfiltration. How are alert thresholds set per role, and who is notified?

---

## Summary and Recommendation

**Core recommendation: Treat agent roles as first-class security principals. Every alert rule must carry role context.**

The fundamental challenge is that behaviors acceptable for one agent role are indicators of compromise in another. A research agent that resolves 500 unique FQDNs per hour is doing its job. The same pattern from an implement agent — whose job is to write code and run tests against a fixed local environment — is a high-confidence signal of DNS exfiltration or C2 beaconing.

The solution is a layered defense with role-aware rules at each layer:

1. **Static allowlisting** (KubeArmor or Tetragon `TracingPolicy`) — the outermost, cheapest enforcement layer. Each agent container image gets a policy that hard-blocks network connections, file paths, and process executions it has no business touching. Violations here are high-confidence alerts.

2. **Role-aware Falco rules** — a behavioral monitoring layer using `container.image.repository` and Kubernetes pod labels (`k8s.pod.label.role`) to apply different rule sets to different agent types. An implement agent making a TXT record query is an alert; a research agent making the same query is not.

3. **Statistical anomaly detection on DNS signals** — for the category of exfiltration that static rules cannot catch (e.g., a research agent going beyond its intended scope), monitor Shannon entropy of subdomain labels (threshold ~4.0), query length distribution (flag queries >122 chars), NXDOMAIN ratio (flag >20% per host per hour), and query volume baseline deviation (flag >3 standard deviations from the rolling hourly mean).

4. **UEBA/Agent Behavior Analytics (ABA)** — an emerging class of tool (Exabeam launched ABA in January 2026) that builds session-level behavioral baselines per AI agent identity, detecting anomalies like an agent that normally generates summaries suddenly issuing high-frequency external API calls.

**Alert routing by confidence and severity:**
- Hard enforcement violations (KubeArmor Block, Tetragon enforcement) → immediate PagerDuty + Slack `#security-incidents`
- High-confidence Falco Critical/Error rules → PagerDuty (wake on-call) + Slack
- Statistical anomaly alerts → Slack `#security-alerts` (business hours; escalate to PagerDuty if unresolved after 30 min)
- Info/Warning drift detection → Slack `#security-ops` with no pager escalation

**Baseline before you alert.** Run all roles in audit/observe mode for at least two weeks before enabling blocking or high-severity alerting. Every role's behavioral fingerprint will differ in ways you cannot predict from first principles.

---

## 1. Behavioral Baselining for Container Workloads

### What "normal" means and how to measure it

Behavioral baselining involves establishing a ground-truth behavioral profile for each distinct workload type, then treating deviations from that profile as anomaly candidates. For container workloads, the relevant dimensions are:

- **Syscall distribution:** Which syscalls are called, at what frequency, in what sequence. Tools: Falco, Tetragon, Tracee, Sysdig.
- **Process tree:** Which parent processes spawn which children. A web server parent spawning `bash` is anomalous. A CI runner parent spawning `bash` is not.
- **File access patterns:** Which directories are read or written, at what frequency.
- **Network connections:** Destinations (IP, FQDN, port), protocols, connection rates.
- **DNS query characteristics:** Volume, unique FQDN count, subdomain entropy, record types.

### Practical baselining approach

The industry-standard approach (supported by Sysdig, KubeArmor, and Calico Cloud) is to run workloads in **audit/observe mode** for 1–4 weeks before enabling enforcement:

1. Deploy the agent container with Falco, Tetragon, or KubeArmor in audit mode (log all events, block nothing).
2. Capture all syscall events, process executions, file accesses, and network connections.
3. Build a per-image behavioral profile: which binaries execute, which paths are accessed, which external IPs/FQDNs are contacted.
4. Convert the profile into allowlists (for enforcement tools) and expected-behavior macros (for Falco rules).
5. Calculate rolling baselines for rate-based signals (DNS queries/hour, unique destinations/hour) using moving-window statistics.
6. Set initial alert thresholds at 3 standard deviations above the rolling mean.

**Critical rule for agentic workloads:** Different run phases have different behavioral fingerprints. A research agent's baseline during web-crawling is different from its baseline during synthesis. Capture baselines across a representative sample of full agent task completions, not just static idle state.

### Container drift detection

Container drift — executing binaries not present in the original container image — is a specialized form of behavioral deviation that Falco directly supports via `proc.is_exe_upper_layer`. An executable running from the OverlayFS upper layer was not present at image build time and should be treated as a near-certain compromise indicator for any immutable agent role.

---

## 2. Falco Rule Writing for Role-Aware Detection

Falco's rule engine supports role differentiation through several filtering mechanisms:

- `container.image.repository` — matches the container image name (e.g., `myregistry.io/agents/implement-agent`)
- `k8s.pod.label.<label-name>` — matches any Kubernetes pod label
- `k8s.ns.name` — matches the Kubernetes namespace
- `proc.name`, `proc.exepath` — matches the process binary

### Rule structure: exceptions and macros

Falco's `exceptions` syntax (added in Falco 0.28) is the preferred mechanism for role-aware carve-outs. The structure adds `and not ((field1 comp1 value1 and field2 comp2 value2) or ...)` semantics to any existing rule:

```yaml
- rule: Unexpected Outbound DNS over Non-Standard Port
  desc: DNS query on a port other than 53 from an implement agent
  condition: >
    evt.type in (sendto, sendmsg) and
    container and
    fd.sport != 53 and
    fd.l4proto = udp and
    k8s.pod.label.role = "implement"
  output: >
    Non-standard DNS from implement agent
    (pod=%k8s.pod.name image=%container.image.repository
     dport=%fd.dport dip=%fd.rip)
  priority: WARNING
  tags: [network, dns, implement-agent]
```

A research agent with the same behavior:

```yaml
- macro: research_agent_container
  condition: >
    container.image.repository startswith "myregistry.io/agents/research"
    or k8s.pod.label.role = "research"

- rule: DNS Volume Spike (Research Agent)
  desc: Research agent DNS volume anomaly — informational only
  condition: >
    evt.type in (sendto, sendmsg) and
    research_agent_container and
    fd.sport != 53 and fd.l4proto = udp
  output: >
    Research agent DNS on non-standard port
    (pod=%k8s.pod.name dport=%fd.dport)
  priority: INFO
  tags: [network, dns, research-agent]
```

### Maturity levels and false positive management

The Falco project publishes rules at four maturity levels: `stable` (25 rules, low FP rate), `incubating`, `sandbox`, and `deprecated`. Start with stable rules only and add incubating rules incrementally after testing in your environment. Falco's official guidance: "Do not disable rules just because they are noisy. Instead, add exceptions for legitimate behavior."

**Day-2 tuning pattern:**

```yaml
# Override an existing rule to add a per-image exception
- rule: Write below rpm database
  exceptions:
    - name: my_agent_writer
      fields: [container.image.repository, fd.name]
      comps: [startswith, startswith]
      values:
        - ["myregistry.io/agents/implement", "/workspace/"]
```

### Priority-based routing

Falco uses five priority levels that map directly to alert routing tiers:

| Priority  | Meaning                              | Routing target              |
|-----------|--------------------------------------|-----------------------------|
| CRITICAL  | Confirmed compromise indicator       | PagerDuty + Slack (all)     |
| ERROR     | High-confidence policy violation     | PagerDuty + Slack           |
| WARNING   | Suspicious but context-dependent     | Slack `#security-alerts`    |
| NOTICE    | Unexpected but not necessarily bad   | Slack `#security-ops`       |
| INFO/DEBUG | Informational, for baselines        | Log aggregator only         |

Tags further refine routing: a rule tagged `[dns, research-agent]` can route to a different Slack channel than one tagged `[process, implement-agent]`.

---

## 3. Tetragon: Kubernetes-Identity-Aware Policies

Tetragon's `TracingPolicy` applies eBPF enforcement directly in-kernel, performing filtering before the system call completes (preventing TOCTOU races that user-space enforcement cannot avoid).

### Per-role policy scoping

Tetragon supports three scoping mechanisms, composable:

**Pod label selector:**
```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: implement-agent-network-restrict
spec:
  podSelector:
    matchLabels:
      role: implement
  kprobes:
    - call: "tcp_connect"
      syscall: false
      args:
        - index: 0
          type: "sock"
      selectors:
        - matchArgs:
          - index: 0
            operator: "NotDAddr"
            values:
              - "127.0.0.1"
              - "10.0.0.0/8"
          matchActions:
          - action: Sigkill
```

**Namespace-scoped policy (`TracingPolicyNamespaced`):** Applied only to pods in the same namespace as the policy resource — no need to specify a label selector if all pods in a namespace share a role.

**Container selector:** For pods that contain multiple containers with different roles:
```yaml
spec:
  containerSelector:
    matchExpressions:
      - key: name
        operator: In
        values: ["implement-sidecar"]
```

Tetragon can also enforce at the process level — tracing which binaries are executed and by which parent — providing the same shell-spawning detection as Falco but with kernel-level blocking rather than post-hoc alerting.

---

## 4. DNS Query Anomaly Detection

DNS exfiltration tools (dnscat2, iodine, dns2tcp) encode data in subdomains and use legitimate DNS resolvers to tunnel it out. Detection relies on statistical analysis of DNS traffic characteristics:

### Shannon entropy of subdomain labels

Legitimate domain names are human-readable and have low entropy. Encoded payloads (base32/base64/hex) have high entropy.

| Entropy value | Interpretation                                     |
|---------------|----------------------------------------------------|
| < 2.5         | Human-readable, very likely legitimate             |
| 2.5 – 3.5     | Could be CDN tokens, UUIDs, hashed filenames       |
| 3.5 – 4.0     | Borderline — warrants additional signal correlation|
| > 4.0         | High confidence encoded payload; alert             |

**Threshold guidance:** A threshold of 4.0 is widely cited; a threshold of 3.1 correctly classifies 80% of NCSC malicious domains while misclassifying only 8% of the Alexa top 1000. Use ~3.5 as a soft alert and ~4.0 as a hard alert for implement/design/plan agents. Research agents may legitimately hit 3.5+ due to CDN or content-hash domains — their threshold should be raised to 4.5 or disabled.

### Query length distribution

RFC 1035 defines maximum DNS name length as 255 characters and maximum label length as 63 characters. Exfiltration tools maximize payload density, pushing names toward the 255-character ceiling.

| Metric                         | Suspicious threshold             |
|--------------------------------|----------------------------------|
| Total FQDN length              | > 122 characters                 |
| Single subdomain label length  | > 50 characters                  |
| Deviation from rolling mean    | > 3 standard deviations          |

Note: CDN and content-delivery systems can generate long, high-entropy domains for legitimate reasons. Whitelist known CDN domains (Akamai, Cloudflare, Fastly) before applying length-based alerts.

### Query volume and rate

| Metric                                  | Suspicious threshold                        |
|-----------------------------------------|---------------------------------------------|
| Unique FQDNs queried per hour           | > 1,000 for non-research agents             |
| Queries to a single apex domain         | > 500/hour (data encoded per subdomain)     |
| Consecutive queries, uniform interval   | Automated beacon cadence (e.g., every 30s)  |
| External DNS resolver connections       | > 100 connections to port 53 on external IP |

### NXDOMAIN ratio

Exfiltration tools frequently generate unique one-time subdomains, most of which do not resolve. A NXDOMAIN rate above ~20% for a sustained period is a strong signal.

| NXDOMAIN ratio per host per hour | Interpretation                          |
|----------------------------------|-----------------------------------------|
| < 5%                             | Normal                                  |
| 5% – 20%                         | Elevated — correlate with entropy        |
| > 20%                            | Alert: probable exfiltration or DGA use |

### Record type distribution

Legitimate traffic is dominated by A, AAAA, and CNAME records. DNS tunneling tools prefer TXT (large payload capacity) and NULL records, which are nearly absent in legitimate traffic. Alert on any spike in TXT or NULL queries from non-research agent containers.

### Timing uniformity

Human-driven DNS queries are bursty and irregular. Automated exfiltration operates at machine-regular intervals. A process issuing DNS queries at exactly 30-second intervals is a near-certain beacon or exfiltration indicator regardless of entropy or length.

---

## 5. Network Connection Anomaly Detection

### Destination IP allowlisting

For implement, plan, structure, and other non-research agents, the expected network connection graph is small and predictable:
- Local Kubernetes service IPs (registry, artifact store, test harness)
- A small list of permitted external package registries (npm, PyPI, crates.io, etc.)

Any connection to an IP outside this allowlist — even if the connection was blocked by network policy — should be logged and alerted. **Blocked but attempted connections are as informative as successful ones** for detecting agent misbehavior.

Recommended implementation: Cilium NetworkPolicy (or a Kubernetes NetworkPolicy) with `default-deny-egress` plus explicit allow entries, combined with Tetragon or Falco logging of all blocked connection attempts.

### High-frequency connections

| Metric                              | Suspicious threshold                    |
|-------------------------------------|-----------------------------------------|
| Unique external IPs per hour        | > 20 for non-research agents            |
| Connections to single IP per minute | > 60 (automated scanning or exfiltration)|
| Connections to new-seen IP          | Alert for implement/plan agents         |
| Long-lived connections              | > 2 hours for non-research agents       |

### Geolocation and ASN anomalies

Connections to IP ranges associated with hosting providers known for C2 infrastructure (e.g., bulletproof hosting ASNs) should alert immediately regardless of connection success. Threat intelligence feeds (e.g., Emerging Threats, Abuse.ch) can be integrated with Falco via the Falco plugin system.

---

## 6. File Access Anomaly Detection

### High-sensitivity paths for any agent role

These paths should generate CRITICAL or ERROR alerts from any agent container:

| Path pattern            | Why it matters                                      |
|-------------------------|-----------------------------------------------------|
| `/etc/shadow`, `/etc/passwd` | Credential dumping                            |
| `/proc/<pid>/mem`       | Memory scraping of other processes                  |
| `/proc/sysrq-trigger`   | Forced reboot / system disruption                   |
| `/sys/kernel/security/` | LSM policy inspection/bypass                        |
| `/var/run/docker.sock`  | Docker daemon access = container escape             |
| `/run/containerd/`      | Container runtime socket access                     |
| `~/.ssh/`, `~/.gnupg/`  | Key and credential theft                            |
| `/proc/<pid>/environ`   | Environment variable (secret) harvesting            |

### Role-specific path expectations

| Agent role   | Expected write scope          | Alert on write to              |
|--------------|-------------------------------|--------------------------------|
| research     | `/workspace/research/`        | Anything outside `/workspace/` |
| implement    | `/workspace/code/`, `/tmp/`   | System paths, `/etc/`, `/root/`|
| plan/design  | `/workspace/artifacts/`       | Executable paths, `/usr/`      |
| all          | (none outside workspace)      | `/proc/`, `/sys/`, sockets     |

KubeArmor policies provide the cleanest implementation: `action: Block` on any path outside the expected write scope, with `action: Audit` for read access to flag unexpected reconnaissance.

### OverlayFS upper-layer execution

As noted in Section 1, any execution from the OverlayFS upper layer (`proc.is_exe_upper_layer = true`) means a binary was written into the container at runtime and then executed — a high-confidence indicator of malware staging or agent escape. This should be a CRITICAL Falco rule for all agent roles.

---

## 7. Process Execution Anomaly Detection

### Shell spawning detection

Spawning an interactive shell (`bash`, `sh`, `zsh`, `fish`, etc.) inside an agent container is one of the most reliable indicators of a compromise or agent escape. Most production agent containers have no legitimate use for an interactive shell. Falco's default ruleset includes "Terminal shell in container" as a stable rule.

**Critical variant:** A shell spawned by a parent that is not a shell itself (e.g., `python` or `node` spawning `bash`) indicates code injection or a library exploit being used to execute arbitrary commands.

```yaml
- rule: Shell Spawned by Non-Shell Parent in Agent Container
  desc: Unexpected shell execution from non-shell parent process
  condition: >
    spawned_process and
    shell_procs and
    container and
    not proc.pname in (shell_procs) and
    k8s.pod.label.component = "agent"
  output: >
    Shell spawned by non-shell parent in agent container
    (shell=%proc.name parent=%proc.pname pod=%k8s.pod.name
     image=%container.image.repository cmd=%proc.cmdline)
  priority: CRITICAL
```

### Unexpected binary execution

Each agent role should have a known set of permitted binaries. Any execution of a binary not on the allowlist should be logged at WARNING or ERROR level. For implement agents, this includes interpreters (Python, Node), compilers, and test runners. For research agents, this includes a browser driver (Playwright, Puppeteer) and curl-like tools.

Binaries that should generate immediate CRITICAL alerts regardless of role:
- `nc`, `ncat`, `netcat` — network pivoting tools
- `wget`, `curl` with `-o` flag to executable paths — binary download
- `base64`, `xxd` writing to executable paths — encoding bypass
- `ptrace` invocations — process memory inspection
- Privilege escalation binaries (`sudo`, `su` where not expected)
- Package managers (`apt-get install`, `pip install`) making network connections during implement phase

---

## 8. Per-Role Alerting Thresholds: Summary Table

| Signal                          | Research agent  | Implement agent | Plan/Design agent |
|---------------------------------|-----------------|-----------------|-------------------|
| DNS queries/hour                | < 2,000 (alert) | < 200 (alert)   | < 50 (alert)      |
| Subdomain entropy threshold     | > 4.5 (alert)   | > 3.5 (alert)   | > 3.5 (alert)     |
| Subdomain length threshold      | > 150 chars     | > 80 chars      | > 80 chars        |
| NXDOMAIN rate                   | > 30% (alert)   | > 10% (alert)   | > 10% (alert)     |
| Unique external IPs/hour        | < 500 (alert)   | 0 (any = alert) | 0 (any = alert)   |
| Outbound connections to new IP  | Log only        | ERROR           | ERROR             |
| Shell spawning                  | CRITICAL        | CRITICAL        | CRITICAL          |
| Write to /etc/, /proc/, /sys/   | CRITICAL        | CRITICAL        | CRITICAL          |
| OverlayFS upper-layer execution | CRITICAL        | CRITICAL        | CRITICAL          |
| TXT/NULL DNS record query       | WARNING         | ERROR           | ERROR             |
| Execution of nc/netcat/ncat     | CRITICAL        | CRITICAL        | CRITICAL          |

---

## 9. Alert Fatigue Mitigation

Alert fatigue — where security teams stop treating alerts seriously because they are too frequent and mostly false positives — is the primary operational failure mode for runtime security monitoring.

### Tuning principles

**Start with stable rules only.** Falco's 25 stable rules are production-tested and have low false positive rates. Avoid enabling all 93 rules on day one.

**Test before deploying.** Run candidate rules against representative traffic captures or in staging before enabling in production. One noisy rule can train responders to ignore the entire alert stream.

**Use exceptions, not rule disablement.** When a rule fires legitimately (a known tool using a path that looks suspicious), add an exception with `fields`, `comps`, and `values` rather than disabling the rule entirely. Document every exception with a rationale.

**Priority filtering at the pipeline.** Use Falco's output tags and priorities to filter at the aggregator (Fluentd, Vector, Promtail) before events reach the alert router. NOTICE and INFO events should feed dashboards and SIEM, not pager alerts.

**Inhibition rules.** When a CRITICAL alert fires, suppress related WARNING alerts of the same type to prevent flooding. Alertmanager (Prometheus ecosystem) and PagerDuty's event orchestration both support alert inhibition.

**Maintenance windows.** During scheduled deployments and test runs, create silence matchers targeting `env=staging` or specific pod name patterns with a 30–60 minute duration.

**Rolling baseline updates.** As agent behavior legitimately evolves (new tools added, new dependencies), update macros and exception lists. Treat rule tuning as a recurring operational task, not a one-time setup.

---

## 10. Notification Routing and Response Playbook

### Severity-to-channel mapping

| Alert severity  | Falco priority        | Primary channel      | Secondary channel     | Hours       |
|-----------------|-----------------------|----------------------|-----------------------|-------------|
| P1 Critical     | CRITICAL              | PagerDuty (wake)     | Slack `#sec-incidents`| 24x7        |
| P2 High         | ERROR                 | PagerDuty            | Slack `#sec-incidents`| 24x7        |
| P3 Medium       | WARNING               | Slack `#sec-alerts`  | PagerDuty (no wake)   | Business hrs|
| P4 Low          | NOTICE                | Slack `#sec-ops`     | —                     | Business hrs|
| P5 Info         | INFO / DEBUG          | SIEM / log store     | —                     | Never pages |

**P3 escalation rule:** If a P3 alert in `#sec-alerts` is not acknowledged within 30 minutes during business hours, auto-escalate to PagerDuty.

### Required alert fields

Every alert routed outside the log store must include:
- `severity` (critical|error|warning|notice|info)
- `env` (prod|staging|dev)
- `agent_role` (research|implement|plan|design|etc.)
- `pod_name` and `namespace`
- `container_image`
- `rule_name` (the Falco rule that fired)
- `runbook` URL
- `event_time` (UTC)

### Response playbook by event category

**Shell spawning / unexpected binary execution:**
1. Falco Talon or manual: isolate pod (apply `NetworkPolicy` deny-all, do not terminate yet).
2. Capture memory dump and active connections (Falco Talon: `kubernetes:tcpdump`).
3. Retrieve logs (`kubernetes:logs`).
4. Terminate pod.
5. Preserve OverlayFS upper layer for forensics.
6. File incident report; review which agent task was running.

**DNS exfiltration (statistical anomaly):**
1. Block pod egress to all DNS except internal resolver.
2. Capture full DNS query log for the pod (Tetragon or Falco + tcpdump).
3. Run entropy/length analysis on captured queries.
4. If confirmed: terminate pod, preserve artifacts, rotate any credentials the agent held.
5. Review agent task input for prompt injection (DNS exfiltration is commonly triggered by adversarial prompts).

**Unexpected network connection (implement/plan agent):**
1. Log the destination IP/FQDN.
2. Check against threat intelligence feeds.
3. If to a known malicious IP: immediate CRITICAL escalation, isolate pod.
4. If to an unknown but benign-looking IP: WARNING, review agent task, update allowlist if legitimate.

**File access outside workspace:**
1. Log the path accessed and whether it was a read or write.
2. For writes to sensitive system paths: CRITICAL, immediate pod isolation.
3. For reads of `/proc` or `/sys`: WARNING, correlate with recent process executions.
4. If `/var/run/docker.sock` or container runtime socket: treat as container escape attempt — CRITICAL.

### Automated response with Falco Talon

Falco Talon provides a no-code YAML-driven response engine that chains actions sequentially:

```yaml
- rule: Shell spawned in agent container
  matches:
    - output_fields:
        k8s.pod.label.component: agent
  actions:
    - action: kubernetes:label
      parameters:
        labels:
          quarantine: "true"
    - action: kubernetes:tcpdump
      parameters:
        duration: 30
    - action: kubernetes:logs
    - action: kubernetes:terminate
  notifications:
    - slack:
        channel: "#security-incidents"
        message: "CRITICAL: Shell spawned in agent pod {{k8s.pod.name}}"
    - pagerduty:
        routing_key: "{{env.PAGERDUTY_KEY}}"
```

Response actions available in Falco Talon: terminate pod, label pod (for quarantine), execute commands, retrieve logs, capture network traffic (tcpdump), delete resources, drain nodes, update Kubernetes/Cilium/Calico network policies, invoke AWS Lambda or GCP Cloud Functions.

---

## 11. UEBA and Agent Behavior Analytics (ABA)

### Traditional UEBA applicability

Traditional UEBA (User and Entity Behavior Analytics) tools like Splunk UBA, Securonix, or Microsoft Sentinel UEBA were designed for human user behavioral patterns: login times, data access volumes, geographic anomalies. They apply to agentic workloads only partially:

- **Applicable:** API call volumes, data access patterns, tool invocation frequency, access to novel resources.
- **Not applicable:** Human behavioral rhythms (circadian patterns, day-of-week effects), geographic impossible travel.

For agentic workloads, UEBA tools require retuning to treat each agent instance as an entity with its own behavioral profile, not as a proxy for the user who invoked it.

### Exabeam Agent Behavior Analytics (ABA)

In January 2026, Exabeam launched **Agent Behavior Analytics** — the first purpose-built behavioral analytics product for AI agent workloads. ABA's key design decisions relevant to this project:

- **Session data model:** Rather than treating individual events as the unit of analysis, ABA links related activity into a session with full causal history (prompt → tool call → data access → action → output). This is critical for detecting misuse that spans multiple steps and would not be visible at the event level.
- **Unified human + agent profile:** ABA profiles both the human user and the AI agents acting on their behalf, detecting deviations in either. An agent doing things its operator has never done is an anomaly.
- **Detection types:** Abnormal number of guardrail violations, first-time access to a resource by an agent, abnormal external API call frequency, unusual data upload patterns, access to previously untouched repositories.
- **OWASP Agentic Top 10 alignment:** Coverage explicitly maps to prompt manipulation, excessive privileges, insecure tool usage, and model misuse.

### Applying UEBA principles to this project's agent sandbox

Without a commercial UEBA platform, the following open-source/composable approach approximates ABA:

1. **Per-agent identity logging:** Tag all Falco/Tetragon events with the agent role, agent instance ID, and the task ID that spawned the agent.
2. **Session aggregation in SIEM:** Use a log aggregator (Loki, Elasticsearch, Splunk) to group events by task ID. Build dashboards showing the behavioral fingerprint per task.
3. **First-seen tracking:** Maintain a set of (agent_role, destination_ip) pairs that have been seen historically. Alert on any new pair for non-research agents.
4. **Behavioral drift detection:** Use the statistical anomaly detection from Section 4/5 applied to rolling 24-hour and 7-day windows per agent role.
5. **Prompt injection correlation:** When a DNS exfiltration or unexpected network connection alert fires, surface the agent's last received prompt in the alert context. Prompt injection is the primary attack vector causing agents to exceed their behavioral envelope.

---

## Sources

- [Falco Default Rules Documentation](https://falco.org/docs/reference/rules/default-rules/)
- [Falco Rule Exceptions Documentation](https://falco.org/docs/concepts/rules/exceptions/)
- [Falco Rules Repository — falcosecurity/rules](https://github.com/falcosecurity/rules)
- [Falco Rules Explained: Writing Custom Detection for Container Security](https://www.gocodeo.com/post/falco-rules-explained-writing-custom-detection-for-container-security)
- [Day 2 Falco Container Security – Tuning the Rules (Sysdig)](https://www.sysdig.com/blog/day-2-falco-container-security-tuning-the-rules)
- [Container Drift Detection with Falco (Sysdig)](https://www.sysdig.com/blog/container-drift-detection-with-falco)
- [Falco Network Security and Talon Automated Response](https://falco.org/blog/falco-network-security/)
- [Falco Talon — falcosecurity/falco-talon (DeepWiki)](https://deepwiki.com/falcosecurity/falco-talon)
- [Falco Talon GitHub Repository](https://github.com/falcosecurity/falco-talon)
- [Securing Kubernetes Runtime with Falco (skyu.io)](https://skyu.io/blogs/securing-kubernetes-runtime-with-falco/)
- [Tetragon — eBPF-based Security Observability and Runtime Enforcement](https://tetragon.io/)
- [Tetragon Kubernetes Identity Aware Policies](https://tetragon.io/features/kubernetes-identity-aware-policies/)
- [Tetragon Kubernetes Identity-Aware Policy k8s-filtering Documentation](https://tetragon.io/docs/concepts/tracing-policy/k8s-filtering/)
- [Tetragon Network Monitoring Documentation](https://tetragon.io/docs/getting-started/network/)
- [KubeArmor Runtime Security Enforcement](https://kubearmor.io/)
- [KubeArmor Security Policy Examples](https://docs.kubearmor.io/kubearmor/documentation/security_policy_examples)
- [KubeArmor Security Policies Overview](https://docs.kubearmor.io/kubearmor/quick-links/kubearmor_overview/security_policy)
- [Policy as Code for Runtime Enforcement — AccuKnox](https://accuknox.com/blog/policy-as-code-for-runtime-enforcement-a-20-point-checklist-that-ships-security-by-default)
- [Runtime Security for Containers: Detect Threats by Identifying Anomalies (Tigera/Calico)](https://www.tigera.io/blog/deep-dive/runtime-security-for-containers-detect-threats-by-identifying-anomalies-in-container-behavior/)
- [Hybrid Runtime Detection of Malicious Containers Using eBPF (ScienceDirect)](https://www.sciencedirect.com/org/science/article/pii/S1546221826000615)
- [An Abnormal File Access Detection Model for Containers Based on eBPF (MDPI)](https://www.mdpi.com/2227-7390/14/6/991)
- [eBPF for AI Agent Enforcement: What Kernel-Level Security Catches (ARMO)](https://www.armosec.io/blog/ebpf-based-ai-agent-enforcement/)
- [DNS Exfiltration Detection: What Is DNS Data Exfiltration? (DeepStrike)](https://deepstrike.io/blog/what-is-dns-data-exfiltration)
- [DNS Tunneling Detection Techniques (CyberDefenders)](https://cyberdefenders.org/blog/dns-tunneling-detection/)
- [DNS Query Length Analysis — SANS ISC](https://isc.sans.edu/diary/22326)
- [DNS Entropy Hunting and You — Hurricane Labs](https://hurricanelabs.com/blog/dns-entropy-hunting-and-you/)
- [Random Words on Entropy and DNS (Splunk)](https://www.splunk.com/en_us/blog/security/random-words-on-entropy-and-dns.html)
- [DNS Tunnelling, Exfiltration and Detection over Cloud (PMC/NIH)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007605/)
- [An Overview of the Concept and Use of Domain-Name Entropy (CircleID)](https://circleid.com/posts/20230703-an-overview-of-the-concept-and-use-of-domain-name-entropy)
- [Exabeam Agent Behavior Analytics: First-of-Its-Kind Behavioral Detections for AI Agents](https://www.exabeam.com/blog/siem-trends/exabeam-agent-behavior-analytics-first-of-its-kind-behavioral-detections-for-ai-agents/)
- [What's New in Exabeam New-Scale April 2026: Securing the Agentic Enterprise With Behavioral Analytics](https://www.exabeam.com/blog/company-news/whats-new-in-new-scale-april-2026-securing-the-agentic-enterprise-with-behavioral-analytics/)
- [UEBA Complete 2025 Guide (Exabeam)](https://www.exabeam.com/explainers/ueba/what-ueba-stands-for-and-a-5-minute-ueba-primer/)
- [A Survey of Agentic AI and Cybersecurity (arXiv)](https://arxiv.org/html/2601.05293v1)
- [Routing Alerts in Slack/PagerDuty by Severity (DataOps.tech)](https://medium.com/dataops-tech/routing-alerts-in-slack-pagerduty-by-severity-so-noise-doesnt-kill-you-874060ef2996)
- [High-Priority Alerting: Integrating IDS Notifications with Slack, Discord, or PagerDuty](https://dohost.us/index.php/2025/12/28/high-priority-alerting-integrating-ids-notifications-with-slack-discord-or-pagerduty/)
- [PagerDuty Incident Response Documentation](https://response.pagerduty.com/)
- [Detection: Kubernetes Falco Shell Spawned (Splunk Security Content)](https://research.splunk.com/cloud/d2feef92-d54a-4a19-8306-b47c6ceba5b2/)
- [Falco in 2025: Real-Time Security Monitoring with eBPF](https://mangohost.net/blog/falco-in-2025-real-time-security-monitoring-with-ebpf/)
- [Hardening eBPF for runtime security: Lessons from Datadog Workload Protection](https://www.datadoghq.com/blog/engineering/ebpf-workload-protection-lessons/)
- [eBPF-PATROL: Protective Agent for Threat Recognition (arXiv)](https://arxiv.org/html/2511.18155v1)
