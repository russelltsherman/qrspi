# Q16: Where Does the Policy Catalog Live and Who Can Modify It?

**Project context:** Container sandbox for agentic AI tasks. Each agent invocation is governed by a declarative constraint policy derived from its QRSPI role. Policies must live outside the repository to maintain a separate trust domain — an agent that can read its own policy can reason about how to circumvent it.

---

## Summary and Recommendation

**Recommended architecture:** A dedicated private policy repository (separate from the agent code repo), served to the orchestrator at invocation time via signed OPA bundles distributed through an OCI-compatible registry or an HTTP bundle server.

The canonical pattern is:

1. **Separate private Git repo** for all Rego/YAML constraint policies, inaccessible to the agent workload and its code repo.
2. **CI/CD pipeline** on the policy repo builds, signs, and publishes an OPA bundle to an OCI registry on every merge to `main`.
3. **Orchestrator** (not the agent) fetches the current signed bundle at container invocation time, verifies the cryptographic signature, and passes the policy to a local OPA sidecar or embedded evaluator.
4. **OPA decision logs** record the bundle revision (Git SHA) alongside every allow/deny decision, providing a tamper-evident audit trail mapping each invocation to the exact policy version that governed it.
5. **Branch protection + CODEOWNERS + required multi-party review** on the policy repo enforces separation of duties: no single person can push a policy change to production without a second approver from a designated security/platform team.

This approach combines the auditability of GitOps, the integrity guarantees of bundle signing, and the operational simplicity of OCI artifact distribution — without requiring a standalone policy service in the critical path.

A fully managed OPA control plane (Styra DAS) or OPAL server is worthwhile at scale (hundreds of OPA instances), but adds operational complexity that is unnecessary for a single-orchestrator deployment.

---

## Detailed Findings

### 1. Why a Separate Trust Domain Is Non-Negotiable

An agent that can read its own constraint policy can enumerate the exact rules it must satisfy and reason about inputs that would yield `allow = true` without performing the prohibited action — or find gaps in the policy logic. This is analogous to a prisoner being handed the guard's rule book.

The separation requirement means:

- The policy repo must not be mounted, cloned, or otherwise readable inside the agent container.
- The orchestrator (the entity that starts the container) must be the sole consumer of the policy at invocation time, not the agent process itself.
- The agent container image and its source repository must have no dependency on, or network path to, the policy storage system.

OPA's security model supports this: OPA authorization policies restrict which data paths different client identities can access. By giving the orchestrator a privileged identity and denying all access to the agent's network namespace, the policy is enforced externally without ever being exposed to the agent. OPA's diagnostic listener can be bound to a separate port with separate auth, keeping observability data away from the agent as well.

### 2. Separate Trust Domain Options

#### 2a. Dedicated Private Policy Repository (Recommended for Most Teams)

A private Git repository (GitHub, GitLab, or Gitea) containing only policy files (Rego, YAML, or Cedar) is the most widely adopted approach. Key properties:

- **Write access**: Restricted to a `policy-admins` team. No agent developer, CI system for the agent code repo, or deployed workload has write access.
- **Review enforcement**: GitHub branch rulesets (GA as of February 2026) allow requiring review from a specific named team before merge, independent of general CODEOWNERS. GitLab has equivalent `CODEOWNERS` + protected branch rules.
- **Audit trail**: Every change has an author, timestamp, and PR discussion thread stored permanently in Git history.
- **Deployment**: CI/CD on the policy repo (GitHub Actions, GitLab CI) builds and publishes the bundle on merge.

Goldman Sachs' Cloud Entitlements Service (OCES) uses exactly this pattern: application owners author policies in GitLab, which are pushed to OPA Policy Decision Points (PDPs) via a GitLab CI/CD pipeline. Policies go through standard SDLC gating (approval, testing, baking in lower environments) before reaching production.

#### 2b. Secrets Manager (HashiCorp Vault, AWS Secrets Manager)

Secrets managers are designed for credentials, not structured policy logic. They work against this use case in several ways:

- No native diff/PR review workflow.
- No line-level version history.
- Versioning is per-secret, not across an entire policy catalog that may span dozens of files.
- HashiCorp Vault now supports AI agent authentication and dynamic secrets (Project Infragraph), but it positions Vault as a consumer of OPA policy, not the policy store itself.

**Verdict:** Use a secrets manager only for storing the cryptographic keys used to sign OPA bundles, not the policy content itself.

#### 2c. Open Policy Agent (OPA) with Bundle Distribution

OPA is the most appropriate policy engine for this use case. It is language-agnostic (Rego for complex logic, YAML for simpler declarative rules), widely deployed in production at scale, and purpose-built for policy-as-code separate from application code.

**How OPA bundles work:**

- A bundle is a gzipped tarball (`.tar.gz`) containing `.rego` policy files, `data.json` data files, and an optional `.manifest` with a `revision` field (typically the Git SHA of the policy commit).
- Bundles can be signed using HMAC, RSA, or ECDSA. When OPA loads a new bundle, it verifies the JWT-based `.signatures.json` file against a public key configured out-of-band. A bundle that fails signature verification is rejected — OPA continues using its existing (last-good) bundle.
- The public key used for verification is provisioned into the OPA sidecar by the orchestrator infrastructure at deployment time, not by the agent or the agent's code repo.

**Distribution methods:**

| Method | Immutability | Access Control | Complexity |
|---|---|---|---|
| OCI registry (e.g., ECR, GCR, Artifact Registry) | Digest-pinned, immutable | IAM/RBAC on the registry | Low–Medium |
| S3/GCS/Azure Blob HTTP bundle server | Immutable by naming convention | Bucket policies | Low |
| OPAL server (Git-watching pub/sub) | Via Git revision | OPAL server auth | Medium |
| Styra DAS (commercial control plane) | Full versioning | Enterprise RBAC | High (cost + ops) |

For a single-orchestrator deployment, an OCI registry is the simplest and most robust option. OPA v0.40+ can poll an OCI tag and detect digest changes, downloading the new bundle only when content changes (efficient caching via SHA256 digest comparison).

#### 2d. Policy Engines: OPA Gatekeeper and Kyverno (Kubernetes-Native Patterns)

These tools enforce policy at Kubernetes admission time — before a pod is scheduled. They are relevant as architectural patterns even if this project does not run on Kubernetes.

**OPA Gatekeeper:**
- Runs as a validating admission webhook in Kubernetes.
- Policies are `ConstraintTemplate` CRDs containing Rego logic plus `Constraint` CRDs for specific instances.
- Policies are stored in the cluster's etcd (written there via `kubectl apply`), not in the agent workload.
- The admission controller intercepts pod creation requests and evaluates them against all matching constraints before the pod is allowed to schedule.

**Kyverno:**
- Kubernetes-native, uses YAML instead of Rego — lower learning curve.
- Handles validation, mutation, and generation of Kubernetes resources in a single controller.
- CNCF Incubating (OPA is CNCF Graduate).
- Better for simple Kubernetes-specific policies; OPA/Gatekeeper is better for complex cross-system logic.

**Applicable pattern for this project:** Even outside Kubernetes, the admission controller model — intercepting the "create workload" API call, evaluating the policy before the container starts, and blocking or allowing the invocation — maps directly onto the orchestrator's role. The orchestrator is the admission controller. The policy engine (OPA) runs as a sidecar or embedded library in the orchestrator, not in the agent container.

#### 2e. Configuration Management Systems (Ansible, Chef, Puppet)

These are inappropriate for policy storage: they manage system configuration state, not versioned, signed, reviewable policy artifacts. They would add significant operational complexity for no benefit over a Git repo.

### 3. GitOps for Policy: Separate Repo Workflow

The recommended workflow:

```
[Security/Platform Engineer]
    |
    | opens PR in policy-repo
    |
[policy-repo CI pipeline]
    | runs opa test ./...
    | runs opa check --strict ./...
    | generates preview of allow/deny changes
    |
[Required Reviewer: policy-admins team]
    | approves PR
    |
[Merge to main]
    |
[policy-repo CI pipeline]
    | builds bundle: opa build --bundle ./policies -o bundle.tar.gz
    | signs bundle: opa sign --bundle bundle.tar.gz --signing-key private.pem
    | pushes to OCI registry:
    |   docker.io/org/policies:latest (mutable tag, points to current)
    |   docker.io/org/policies:sha-<git-commit> (immutable, for audit pinning)
    |
[Orchestrator at agent invocation time]
    | fetches bundle from OCI registry
    | verifies signature against public key (provisioned out-of-band)
    | passes bundle to OPA sidecar
    | OPA evaluates: allow_invocation(agent_role, requested_capabilities)?
    | if deny: reject with reason
    | if allow: start container with enforced constraints
```

**Pros:**
- Full change history in Git.
- Every merge requires at least one non-author approval from a restricted team.
- Pipeline enforces policy unit tests before merge.
- OCI tags provide both a rolling `latest` pointer and an immutable digest-pinned reference for audit.
- No new policy service to operate — the OCI registry already exists.

**Cons:**
- Policy changes have a deployment lag (minutes) equal to CI/CD pipeline duration plus OPA bundle poll interval.
- Requires discipline in keeping the policy repo access list correct over time.
- Bundle signing key management is a new operational responsibility.

### 4. Separation of Duties: Who Should Modify Policies?

The principle: the people who write agent code should not be the same people who define the constraints on agent behavior. This is a classic separation of duties (SoD) control.

Recommended access tiers for the policy repo:

| Role | Permissions | Notes |
|---|---|---|
| `policy-admins` (security/platform team) | Write + required reviewer | Can author and approve policy changes |
| `policy-readers` (agent developers) | Read (if even that) | May review but cannot approve policy PRs |
| CI/CD service account for policy repo | Write to OCI registry only | Cannot modify Git history |
| Agent workload | No access | Enforced by network policy + IAM |
| Orchestrator service account | Read from OCI registry | Fetches signed bundles; cannot write |

**Multi-party approval:** GitHub's required reviewer rulesets (GA February 2026) and GitLab's `CODEOWNERS` with protected branches both support requiring at least one approval from a named team. For high-assurance environments, two-person integrity (TPI) can be enforced by requiring two approvals from `policy-admins`, preventing any single person from unilaterally deploying a policy change.

### 5. Policy Versioning for Audit

The audit requirement is: for any agent invocation, determine exactly which policy was in force and reproduce the allow/deny decision.

OPA satisfies this through two complementary mechanisms:

**Bundle revision in decision logs:**
OPA's decision log event structure includes a `bundles` field:
```json
{
  "decision_id": "abc-123",
  "timestamp": "2026-04-18T12:00:00Z",
  "path": "qrspi/sandbox/allow",
  "input": { "agent_role": "researcher", "capabilities": ["web_search"] },
  "result": true,
  "bundles": {
    "qrspi-policies": {
      "revision": "sha-446bc9d"
    }
  }
}
```

The `revision` field is set from the bundle's `.manifest` file, which the CI/CD pipeline populates with the Git commit SHA that triggered the bundle build. This creates a direct, queryable link: `decision_id` → `bundle_revision` → `git commit` → exact policy source at that moment.

**Immutable bundle references:**
Publishing bundles to OCI with both a mutable `latest` tag and an immutable `sha-<commit>` tag means any bundle used in production can be re-fetched by its content digest even years later. Replaying a historical decision requires only the decision log event (which contains the input) and the bundle revision (to retrieve the policy). OPA supports `opa eval` with a bundle file for offline replay.

**Decision log forwarding:** OPA can POST decision log events to a remote HTTP endpoint (e.g., Splunk, Elasticsearch, a SIEM). Decision logs should be write-only from the orchestrator's perspective — no mechanism to delete historical decisions.

### 6. Integration with Container Runtime at Invocation Time

The orchestrator's policy enforcement sequence at invocation time:

1. **Receive invocation request** containing: agent role, requested capabilities, network egress targets, filesystem mounts, environment variables.
2. **Fetch current policy bundle** from OCI registry (OPA polls for digest changes on a configurable interval, e.g., 60s; the bundle is cached locally between polls).
3. **Evaluate policy** by calling OPA's REST API or Go library: `POST /v1/data/qrspi/sandbox/decision` with the invocation request as input.
4. **OPA returns** a structured decision: `{ "allow": true/false, "applied_constraints": { "network_egress": "none", "filesystem": "read-only", "cpu_limit": "0.5" } }`.
5. **Orchestrator applies constraints** when starting the container: sets `seccomp` profile, `AppArmor` profile, network namespace, cgroup limits, and read-only filesystem mounts as specified by the policy decision.
6. **Decision is logged** with bundle revision, input, and result.

The agent container never has a network path to the OPA sidecar or the policy bundle server. It runs with the constraints that were already applied to its namespace before it started.

For Kubernetes deployments, OPA Gatekeeper handles steps 1-5 automatically as a validating admission webhook. For non-Kubernetes orchestrators, OPA runs as an out-of-process sidecar alongside the orchestrator (not the agent), or OPA's Go library is embedded in the orchestrator binary.

### 7. OPA vs. Simple Static YAML Files: The Complexity Tradeoff

| Consideration | Simple Static YAML | OPA + Bundle Pipeline |
|---|---|---|
| Authoring effort | Low: any text editor | Medium: Rego requires learning curve |
| Expressiveness | Limited: key-value lookups | High: full logic, conditionals, data joins |
| Testing | None built-in | `opa test` with unit tests |
| Signing/integrity | Requires custom tooling | Built into OPA bundle spec |
| Audit (which version?) | Manual convention | Built-in via bundle revision in decision logs |
| Update propagation | Manual file replacement | Automated via CI/CD + OCI pull |
| Operational cost | Minimal | OCI registry + CI/CD pipeline |
| Kubernetes integration | kubectl configmap | Native Gatekeeper/Kyverno CRDs |

**When simple static YAML is sufficient:**
- Fewer than ~10 agent roles with non-overlapping, non-conditional constraints.
- No need to prove which policy version governed a specific historical invocation.
- The orchestrator reads the YAML file at startup (not per-invocation), and the file is stored in a location the agent cannot access.
- Acceptable risk: no cryptographic integrity guarantee (a compromised orchestrator host could modify the YAML).

**When OPA is warranted:**
- Policies need to express logic (e.g., "allow web search only if the ticket is in `research` phase AND the agent has not already exceeded its daily API call budget").
- Audit requirements mandate a tamper-evident record of which exact policy version governed each invocation.
- Multiple agent roles share overlapping policies that must be maintained without duplication.
- The team already operates Kubernetes with Gatekeeper or Kyverno.

For a project with the security model described (separate trust domain, declarative constraint policies derived from QRSPI role), OPA is recommended. The bundle signing, OCI distribution, and decision log revision tracking address all three of the stated requirements (storage, change review, write access control) with well-tested, production-proven tooling.

### 8. Microsoft Agent Governance Toolkit (April 2026)

Microsoft open-sourced the Agent Governance Toolkit in April 2026, directly addressing this problem domain. Its `Agent OS` component is a stateless policy engine that intercepts every agent action before execution at sub-millisecond latency. It supports YAML rules, OPA Rego, and Cedar policy languages. Key architectural properties relevant to Q16:

- Policies are externalized to YAML configuration files, not embedded in agent code.
- The engine is stateless, enabling horizontal scaling and auditability.
- The toolkit uses decentralized identifiers (DIDs) with Ed25519 cryptography for trust domain separation between agent identities.
- Delegation chains enforce scope narrowing: parent agents cannot escalate permissions to child agents.

This toolkit confirms that the separate-trust-domain policy pattern described in this document reflects current production best practice in the agentic AI space.

---

## Sources

- [Open Policy Agent: Best Practices for a Secure Deployment | CNCF](https://www.cncf.io/blog/2025/03/18/open-policy-agent-best-practices-for-a-secure-deployment/)
- [Open Policy Agent Homepage](https://www.openpolicyagent.org/)
- [OPA Documentation — Bundles](https://www.openpolicyagent.org/docs/management-bundles/)
- [OPA Documentation — Decision Logs](https://www.openpolicyagent.org/docs/management-decision-logs)
- [OPA Documentation — Security](https://www.openpolicyagent.org/docs/security)
- [OPA + GitOps: Enhancing Compliance, Security, and Automation for Platform Teams | Medium](https://medium.com/@debghosal01/opa-gitops-enhancing-compliance-security-and-automation-for-platform-teams-426bc53ce9c4)
- [OPA/Gatekeeper vs. Kyverno: Kubernetes Policy Comparison | Nirmata](https://nirmata.com/2025/02/07/kubernetes-policy-comparison-kyverno-vs-opa-gatekeeper/)
- [Kubernetes Policy as Code with OPA Gatekeeper | Medium](https://medium.com/@DynamoDevOps/kubernetes-policy-as-code-with-opa-gatekeeper-31084ba217cb)
- [OPA Gatekeeper: Policy and Governance for Kubernetes | Kubernetes Blog](https://kubernetes.io/blog/2019/08/06/opa-gatekeeper-policy-and-governance-for-kubernetes/)
- [Why Open Policy Agent is the Missing Guardrail for Your AI Agents | Codilime](https://codilime.com/blog/why-use-open-policy-agent-for-your-ai-agents/)
- [Introducing the Agent Governance Toolkit | Microsoft Open Source Blog](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)
- [Agent Governance Toolkit: Architecture Deep Dive | Microsoft Community Hub](https://techcommunity.microsoft.com/blog/linuxandopensourceblog/agent-governance-toolkit-architecture-deep-dive-policy-engines-trust-and-sre-for/4510105)
- [GitHub — microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit)
- [Agent Governance at Scale: Policy-as-Code Approaches in Action | Nexastack](https://www.nexastack.ai/blog/agent-governance-at-scale)
- [OPAL Architecture | OPAL Documentation](https://docs.opal.ac/overview/architecture/)
- [OPAL — Open Policy Administration Layer | GitHub](https://github.com/permitio/opal)
- [Scaling Open Policy Agent (OPA) — Goldman Sachs Developer Blog](https://developer.gs.com/blog/posts/scaling-opa-for-oces)
- [Manage Open Policy Agent with Styra DAS Control Plane](https://www.styra.com/manage-open-policy-agent-with-styra-das/)
- [Scaling GitOps in the Enterprise: Secure Secrets, Policy as Code | DEV Community](https://dev.to/vaib/scaling-gitops-in-the-enterprise-secure-secrets-policy-as-code-and-multi-cluster-strategies-6hb)
- [Policy as Code: The Platform Engineer's Guide | Platform Engineering](https://platformengineering.org/blog/policy-as-code)
- [GitOps Security: Enforcing Policy as Code in Flux and ArgoCD | policyascode.dev](https://policyascode.dev/blog/gitops-security-policy-as-code-flux-argocd/)
- [Secure AI Agent Authentication Using HashiCorp Vault | HashiCorp Developer](https://developer.hashicorp.com/validated-patterns/vault/ai-agent-identity-with-hashicorp-vault)
- [The Future of Secrets Management in the Era of Agentic AI | Aembit](https://aembit.io/blog/future-of-secrets-management-in-the-era-of-agentic-ai/)
- [OCI Artifacts Explained: Beyond Container Images | OneUptime Blog](https://oneuptime.com/blog/post/2025-12-08-oci-artifacts-explained/view)
- [Policy CLI — "docker" for your OPA policies | Open Policy Registry](https://openpolicyregistry.io/blog/docker-workflow-for-opa/)
- [OPA Bundle Signing Demo | GitHub — anderseknert/opa-sign-verify](https://github.com/anderseknert/opa-sign-verify)
- [Announcing OPA 1.0: A New Standard for Policy as Code](https://blog.openpolicyagent.org/announcing-opa-1-0-a-new-standard-for-policy-as-code-a6d8427ee828)
- [Top 12 Policy as Code Tools in 2026 | Spacelift](https://spacelift.io/blog/policy-as-code-tools)
- [Required Reviewer Rule Now Generally Available | GitHub Changelog](https://github.blog/changelog/2026-02-17-required-reviewer-rule-is-now-generally-available/)
- [Kubernetes Agent Sandbox | GitHub (kubernetes-sigs)](https://github.com/kubernetes-sigs/agent-sandbox)
- [Unleashing Autonomous AI Agents: Why Kubernetes Needs a New Standard | Google Open Source Blog](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html)
- [Container Runtime Security Comparative Insights 2025 | AccuKnox](https://accuknox.com/wp-content/uploads/Container_Runtime_Security_Tooling.pdf)
- [How to Implement Admission Controllers for Security | OneUptime Blog](https://oneuptime.com/blog/post/2026-01-25-admission-controllers-security/view)
- [Beyond Static Sandboxing: Learned Capability Governance for Autonomous AI Agents | arXiv](https://arxiv.org/html/2604.11839)
