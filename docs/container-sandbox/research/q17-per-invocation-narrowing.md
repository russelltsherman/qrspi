# Q17: Per-Invocation Policy Narrowing

**Research date:** 2026-04-18
**Question:** The role sets a base policy. The QRSPI plan knows the slice scope (e.g., "only touches src/api/"). Can the container orchestrator apply additional constraints on top of the role policy per invocation, without modifying the base role policy?

---

## Summary and Recommendation

**Recommendation: Yes, implement per-invocation narrowing, but only at the filesystem layer. Skip the policy-engine layer.**

Per-invocation policy narrowing is both technically feasible and materially improves security for agentic workloads. The most cost-effective pattern for this system is:

1. **Use bind-mount narrowing as the primary per-invocation constraint.** Mount the full repo read-only, then mount only the declared slice directories as read-write. This is two Docker/Firecracker API calls at container start; it requires no policy engine changes and no profile reloading.

2. **Skip AppArmor per-invocation customization.** AppArmor accepts exactly one profile per container at startup and cannot compose profiles. Writing a new profile per invocation (one that encodes `src/api/**` in path rules) requires loading a kernel module, is not portable across hosts, and adds a build/deploy step per slice. The bind-mount approach achieves the same isolation with far less machinery.

3. **Use OPA/Gatekeeper for role-level validation at admission time.** The base policy defines what a `qrspi-implement` role may do (allowed capabilities, seccomp profile, network policy, resource limits). A second, parameterized constraint applied at admission can check that the pod annotation `qrspi.io/slice-paths` contains only paths the invoker is authorized to declare. These two constraints compose via logical AND without touching each other.

4. **Issue per-invocation Vault credentials scoped to the slice's resource needs.** If the slice touches only `src/api/`, the credential it receives should grant only the scoped DB role, S3 prefix, or GitHub token scope for that path — not the credentials of the broader `qrspi-implement` role.

5. **Per-invocation narrowing is worth the complexity for the filesystem layer.** The marginal cost is low (two extra mount declarations per container launch), but the security value is high: a misguided or prompt-injected agent cannot write to `src/core/` even if its LLM output tries to. The cost-benefit is less favorable for policy-engine or kernel-profile changes per invocation.

---

## 1. Policy Composition Patterns: How Base + Narrowing Layers Are Expressed

### OPA / Rego

OPA uses a declarative language (Rego) where multiple rule definitions for the same output combine as logical OR (incremental rules) or all-must-pass conjunction when queried through different entry points. The standard pattern for base + narrowing is:

- **Base policy package** (`policy.base`): defines what the `qrspi-implement` role can do — allowed syscall profile, network egress rules, image whitelist, etc.
- **Invocation-scoped constraint** (`policy.invocation`): uses `input.context.slice_paths` passed in per request to validate that the declared write paths are within bounds.
- **A combining policy** queries both and returns `allow = true` only when both pass.

OPA's per-request `input` document is the key mechanism. Each policy evaluation call provides a JSON input object that can carry invocation-specific context (e.g., `input.slice_paths = ["src/api/"]`). The base policy logic never needs to change; only the data injected at query time changes.

OPA also supports **partial evaluation**: the base policy can be pre-compiled into a residual set of rules that are then evaluated against per-request input, reducing per-call compute overhead.

**Dynamic policy composition pattern (Styra/OPA):** A main policy routes each request to one or more target sub-policies based on `input` fields. The base role policy handles role-level checks; an invocation context policy handles slice-scoped checks. Both run, and the result is their AND.

### OPA Gatekeeper (Kubernetes)

Gatekeeper separates logic (`ConstraintTemplate` containing Rego) from binding (`Constraint` with match scope and parameters). Multiple constraints applied to the same resource evaluate as **logical AND** — all must pass for a pod to be admitted. This is the exact model needed:

- **Constraint 1** (`QrspiRolePolicy`): enforces the `qrspi-implement` base role — capabilities, seccomp profile, non-root execution, etc. Applied cluster-wide to all `qrspi.io/role=implement` pods.
- **Constraint 2** (`QrspiSlicePathPolicy`): parameterized per invocation. The `Constraint` resource includes `parameters.allowed_write_paths` populated from the QRSPI plan at launch time. The Rego checks that every `hostPath` or bind-mount target in the pod spec is on the allowlist.

These two constraints are independent resources. Adding or changing the slice-path constraint never touches the role constraint.

### Kyverno

Kyverno policies are YAML-native (no Rego). Multiple `ClusterPolicy` resources targeting the same pod kind all apply simultaneously. The evaluation model is also AND: all matching policies must pass. A base `ClusterPolicy` can enforce the role-level invariants, and a second, injected `Policy` (namespace-scoped) can narrow write paths per-invocation namespace.

Kyverno also supports `MutatingPolicy` to inject an annotation or volume constraint at admission time, which a validating policy then checks — enabling an orchestrator to declare slice scope at launch and have Kyverno enforce it automatically.

### Kubernetes ValidatingAdmissionPolicy (CEL, GA in 1.30)

As of Kubernetes 1.30 (April 2024), `ValidatingAdmissionPolicy` using CEL expressions is generally available. This is an in-process alternative to Gatekeeper/Kyverno webhooks with lower latency. Path narrowing can be expressed as:

```yaml
validations:
  - expression: >
      object.spec.volumes.all(v,
        !has(v.hostPath) ||
        params.allowedPaths.exists(p, v.hostPath.path.startsWith(p))
      )
    message: "hostPath volumes must be within the declared slice scope"
```

The `params` object comes from a referenced `ConfigMap` or CRD instance populated per-invocation. The base constraint and the slice-path constraint are separate `ValidatingAdmissionPolicy` resources that both bind to the same pods; both must pass.

---

## 2. Filesystem Path Narrowing

### Bind Mounts: The Primary Mechanism

Docker and container runtimes (including Firecracker virtio-fs) support per-mount `readonly` flags and per-path targeting:

```
# Read-only mount of entire repo
--mount type=bind,source=/workspace/repo,target=/workspace,readonly

# Read-write overlay for the declared slice path only
--mount type=bind,source=/workspace/repo/src/api,target=/workspace/src/api
```

This pattern — read-only root mount, writable bind-mounts for declared paths — is the simplest, most portable, and most reliable per-invocation filesystem narrowing technique. The container sees the full source tree for reading but can only write within the declared slice paths. No policy engine is involved at runtime; enforcement is in the kernel's VFS layer.

**Known caveat:** Docker's `readonly` flag on a parent bind-mount is not inherited by subdirectory mountpoints that are separately mounted as read-write on the host. The workaround is to mount the specific subdirectory directly rather than relying on inheritance. This is handled naturally by the pattern above.

### OverlayFS

OverlayFS provides an alternative: mount the full repo as `lowerdir` (read-only image layer) and provide a `tmpfs` or scoped directory as `upperdir` (writable layer). Writes to any path in the overlay go to `upperdir`; if `upperdir` is a bind-mount of only `src/api/`, writes to paths outside that directory fail at the filesystem level.

This is how container runtimes already layer image and container layers. Repurposing the mechanism for per-slice scope narrows writes without the agent needing to be aware of it.

### AppArmor Path Rules

AppArmor profiles support fine-grained path rules:

```apparmor
profile qrspi-implement-src-api {
  /workspace/**   r,       # allow reads everywhere
  /workspace/src/api/**  rw,  # allow writes only in slice scope
  deny /workspace/** w,    # deny writes to all other paths
}
```

**Critical limitation:** Only one AppArmor profile can be active per container at runtime. Profiles cannot be composed or stacked. If you want per-invocation path rules, you must generate a unique profile per invocation (embedding the slice paths) and load it into the kernel before container start. This works but adds a kernel load step, requires the profile to exist on the host node, and is not portable across a node pool. It is more operationally complex than bind-mount narrowing for equivalent security.

AppArmor path rules are most useful for denying writes to sensitive paths that should never be writable regardless of slice scope (e.g., `/etc/**`, `/proc/**`, or credential-holding directories). A static "baseline deny" profile combined with bind-mount narrowing gives good coverage without per-invocation profile generation.

### Seccomp

Seccomp operates at the syscall level, not the path level. It cannot restrict which filesystem paths a process can open — only which syscall numbers it can invoke. Seccomp is therefore not a tool for per-invocation path narrowing. It is a valuable base-layer control (disable `ptrace`, `mount`, `setuid`, etc.) that remains static across all invocations of a given role.

### Mount Namespaces

Linux mount namespaces (created via `clone(CLONE_NEWNS)` or `unshare`) give a process a completely independent view of the filesystem mount table. Container runtimes already create a new mount namespace per container. Within that namespace, bind-mounting specific subdirectories as described above is the standard mechanism for path restriction.

---

## 3. Runtime Constraint Composition

The key insight from surveying these systems is that **policy engines (OPA, Gatekeeper, Kyverno, ValidatingAdmissionPolicy) operate at admission time** — when the pod spec is submitted — not at runtime. At runtime, enforcement is handled by kernel primitives: mount namespaces, bind mounts, cgroups, seccomp, and AppArmor.

This means constraint composition happens in two separate phases:

**Admission-time composition (policy engine):**
- All constraints apply simultaneously (logical AND).
- Base role constraint + invocation slice-path constraint are independent resources.
- Neither needs to know about the other; the engine runs both.
- Parameterized constraints (`ValidatingAdmissionPolicy` with `paramRef`, Gatekeeper `Constraint` with `parameters`) allow the same policy logic to be reused with different slice-path values per invocation.

**Runtime composition (kernel):**
- Mount namespace provides the isolated view.
- Multiple bind mounts with different `readonly` settings compose by union: the most specific mount path wins (as in standard VFS mount table semantics).
- A base seccomp profile + AppArmor base-deny profile remain constant; bind-mount narrowing adds invocation-specific write scoping on top.

**You do not need to rewrite or reload the base policy to apply per-invocation narrowing.** The base policy is static. The narrowing is expressed as additional admission-time constraints (new Constraint/Policy resources referencing new parameters) and additional runtime bind mounts declared in the pod spec.

---

## 4. Kubernetes Resource Quotas and Admission Webhooks as a Pattern

The Kubernetes namespace/pod policy layering model is the canonical example of base + narrowing composition:

- **ClusterPolicy** (Kyverno) or **ClusterConstraint** (Gatekeeper): applies cluster-wide to all pods matching a label selector. Enforces base role invariants.
- **Namespace-scoped Policy**: applies only within a specific namespace. Enforces narrower constraints for the workloads in that namespace.
- **Pod Security Admission**: configured per-namespace via labels (`pod-security.kubernetes.io/enforce: restricted`). Each namespace can independently select `privileged`, `baseline`, or `restricted` levels, narrowing the cluster default.

The PSA model demonstrates that **per-namespace (per-invocation) policy narrowing can be done with namespace-label annotations** — no custom webhook required for standard cases. For custom path constraints, a parameterized Gatekeeper/Kyverno constraint added to the invocation namespace achieves the same effect.

**Admission webhook pattern for dynamic narrowing:** A custom admission webhook can read an annotation on the pod spec (e.g., `qrspi.io/slice-paths: "src/api/"`) and dynamically validate or mutate the container mount specification at admission time. The webhook implements the base + narrowing logic in application code, avoiding the need for a separate policy resource per invocation. This is more operationally complex but allows richer logic (e.g., validating slice paths against the plan artifact before allowing the pod).

---

## 5. The Least-Privilege-Per-Invocation Principle in Other Systems

### Microsoft Agent Governance Toolkit

Microsoft's Agent Governance Toolkit (released April 2026) implements a privilege-ring model for AI agents. New agents start in Ring 3 (read-only, sandboxed). Trust scores determine which ring an agent occupies, and rings gate which capabilities are available. A parent agent with read+write permissions can delegate only read to a child agent — scope can only be narrowed through delegation, never escalated. Trust decay means trust scores decrease without positive signals, requiring continuous re-attestation rather than permanent grants.

**Key pattern: delegation chains narrow scope.** The invocation context carries a delegated token that cannot exceed the parent's scope. Each invocation gets a fresh token with only the scope needed for that task.

### HashiCorp Vault Dynamic Credentials

Vault issues short-lived credentials per invocation. An AI agent authenticates with a JWT claim identifying its role (`qrspi-implement`), and Vault issues a dynamic credential scoped to the specific database role, S3 prefix, or GitHub token scope declared for that invocation. The credential has a TTL of minutes. After the invocation completes, the credential expires automatically.

This is the analogue of per-invocation filesystem narrowing applied to external service access: the base role defines what services are accessible; the per-invocation credential narrows which specific resources within those services are accessible.

### SPIFFE/SPIRE Workload Identity

SPIFFE SVIDs (short-lived X.509 or JWT certificates) are issued per workload with a URI that encodes the workload's namespace, service account, and optionally task context. SVIDs rotate approximately hourly. The trust domain enforces that a workload cannot obtain an SVID beyond its attested identity. Per-invocation narrowing is expressed by issuing a different SVID (with a different set of allowed audience claims) for each task variant.

### Lambda/Firecracker Snapshot Model

AWS Lambda and systems built on Firecracker use the snapshot/restore pattern for per-invocation isolation: each invocation restores from a clean snapshot of the VM state. The filesystem is ephemeral — destroyed completely after the invocation ends. Per-invocation path constraints are naturally enforced because there is no shared state. If the invocation's code touches paths outside its declared scope, the writes land in that invocation's ephemeral upperdir and are destroyed with it; they never reach the persistent store.

For QRSPI, this suggests an alternative to bind-mount narrowing: mount the persistent repo read-only and give the agent a writable ephemeral layer. Only paths that are explicitly committed back to the repo via a controlled exit path (e.g., a Git commit hook that validates changed files against `slice_paths`) actually persist. The agent can write anywhere it wants in the ephemeral layer; the constraint is at the commit-back gate, not in the filesystem itself.

---

## 6. Translating "Slice Scope" to a Filesystem Constraint in Practice

The QRSPI plan artifact records, for each slice, the set of paths the implementation is expected to touch. Translating this to a filesystem constraint involves the following decisions:

### What does "only touches src/api/" mean?

Two interpretations:
- **Soft constraint (read-only enforcement):** The agent can read everything but can only write within `src/api/`. Everything outside that directory is mounted read-only. This is the recommended interpretation: it does not prevent the agent from reading context from other parts of the codebase (which it legitimately needs), but prevents unintended writes.
- **Hard deny (no-access):** The agent cannot even read outside the slice. This is too restrictive for coding agents that routinely need to read shared types, interfaces, and test fixtures from other directories to understand the context of the code they are writing.

**Recommendation: read-only everything, read-write only the declared slice paths.**

### Implementation at container start

The orchestrator reads `slice.paths` from the plan artifact and constructs the mount specification:

```python
def build_mounts(repo_path: str, slice_paths: list[str]) -> list[dict]:
    mounts = [
        # Base: full repo read-only
        {"type": "bind", "source": repo_path, "target": "/workspace", "readonly": True}
    ]
    for path in slice_paths:
        mounts.append({
            "type": "bind",
            "source": os.path.join(repo_path, path),
            "target": f"/workspace/{path}",
            "readonly": False  # writable overlay for this path
        })
    return mounts
```

No policy engine call is needed at this step. The mounts are declared in the container run specification. The admission webhook (if used) validates that the declared writable mounts match the plan artifact before the container starts.

### What about generated files (e.g., build outputs, test fixtures)?

The plan should declare a `generated_paths` list in addition to `slice_paths`. The orchestrator mounts a writable tmpfs at each generated path location, so the agent can write test output and build artifacts without writing to the repo's persistent tree.

### What if the agent needs to touch a file outside the declared scope?

This is a plan error. The recommended enforcement is: let the write fail (the agent tries to write to a read-only mount and gets EACCES), the agent reports the error, and the human reviewer updates the plan to add the path before re-running. Alternatively, the agent can annotate its output with "I need write access to X" and a human gates the re-launch with an updated plan.

---

## 7. Is Per-Invocation Narrowing Worth the Complexity?

### The security case for it

Without per-invocation path narrowing, a `qrspi-implement` container has write access to the entire repository. A prompt-injected or hallucinating agent can silently modify files outside its declared scope — changing dependencies, configuration, or other modules — without the human reviewer noticing unless they do a careful diff.

With bind-mount narrowing:
- Writes outside the slice fail immediately with EACCES.
- The agent cannot silently touch files outside scope.
- The blast radius of a compromised or misbehaving invocation is bounded to the declared paths.
- The human review diff is automatically scoped to the declared paths.

This is a real security improvement, not a theoretical one. It converts a silent, hard-to-detect failure mode (scope creep in generated code) into a loud, immediately visible one (the agent reports write errors).

### The complexity cost

For filesystem narrowing via bind mounts:
- **Cost:** Two to five additional lines in the container launch specification. The orchestrator reads `slice.paths` from the plan artifact (which it already reads) and emits mount entries. This is low complexity.
- **Operational risk:** Near zero. Bind mounts are a standard, well-understood container primitive with decades of production use.

For policy-engine per-invocation constraints (OPA/Gatekeeper/Kyverno):
- **Cost:** Higher. Requires creating a new `Constraint` or `Policy` resource per invocation, referencing per-invocation parameters. Requires a Kubernetes API call at launch time. Adds admission webhook latency.
- **Value:** The admission-time check validates that the declared mounts in the pod spec are within scope — useful as a defense-in-depth layer but not the primary enforcement mechanism.
- **Verdict:** Worthwhile only if you already have Gatekeeper/Kyverno deployed. If you are running Firecracker outside Kubernetes, this layer is not applicable.

For AppArmor per-invocation profiles:
- **Cost:** High. Requires generating a unique profile, loading it into the kernel on the target node before container start, and cleaning it up afterward. Not portable across nodes.
- **Value:** Marginal on top of bind-mount narrowing (which is already enforced at the VFS layer).
- **Verdict:** Not recommended. Use a static AppArmor base-deny profile for categories of paths that should never be writable (credential files, `/etc`, `/proc`) and leave per-slice narrowing to bind mounts.

For per-invocation Vault credentials:
- **Cost:** Medium. Vault integration is non-trivial to set up but pays dividends across all secrets management. Once the pattern is established, per-invocation scope declaration is low-cost.
- **Value:** High for external service access. Analogous to filesystem bind-mount narrowing, but for database, S3, and API credentials.
- **Verdict:** Worthwhile for production deployments. Start with the filesystem layer; add Vault per-invocation scoping in a second phase.

### Industry consensus

Research on agentic AI security (Unit 42, AWS Security, Microsoft Agent Governance Toolkit) consistently recommends per-task least privilege over session-wide role grants. The consensus is that while complexity increases, the security improvement is material — particularly for AI agents with nondeterministic behavior, which can take unexpected actions even without adversarial intent. The key is to implement per-invocation constraints at the layer where cost is lowest: the filesystem mount layer, not the policy engine or kernel profile layer.

---

## Sources

- [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs/latest/)
- [OPA Policy Language - Incremental Rules](https://www.openpolicyagent.org/docs/policy-language)
- [OPA External Data - Per-Request Input](https://www.openpolicyagent.org/docs/external-data)
- [OPA Gatekeeper: How to Use Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/howto/)
- [Gatekeeper Constraint Templates](https://open-policy-agent.github.io/gatekeeper/website/docs/constrainttemplates/)
- [OPA Gatekeeper: Policy and Governance for Kubernetes - Kubernetes Blog](https://kubernetes.io/blog/2019/08/06/opa-gatekeeper-policy-and-governance-for-kubernetes/)
- [Kyverno Policies](https://kyverno.io/policies/)
- [Kyverno vs Kubernetes Policies - CNCF Blog 2025](https://www.cncf.io/blog/2025/10/16/kyverno-vs-kubernetes-policies-how-kyverno-complements-and-completes-kubernetes-policy-types/)
- [Kubernetes Validating Admission Policy - GA in 1.30](https://kubernetes.io/blog/2024/04/24/validating-admission-policy-ga/)
- [Kubernetes ValidatingAdmissionPolicy Reference](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Pod Security Admission - Kubernetes Docs](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Pod Security Standards - Kubernetes Docs](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [AppArmor Profiles for Container Restriction](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [AppArmor Security Profiles for Docker](https://docs.docker.com/engine/security/apparmor/)
- [Bind Mounts - Docker Docs](https://docs.docker.com/engine/storage/bind-mounts/)
- [OverlayFS - Linux Kernel Documentation](https://docs.kernel.org/filesystems/overlayfs.html)
- [Seccomp Security Profiles for Docker](https://docs.docker.com/engine/security/seccomp/)
- [Restrict Container Syscalls with Seccomp - Kubernetes](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [Container Security Fundamentals: Isolation and Namespaces - Datadog Security Labs](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-2/)
- [Mount Namespaces - Red Hat Blog](https://www.redhat.com/en/blog/mount-namespaces)
- [How to Sandbox AI Agents in 2026 - Northflank Blog](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Ephemeral Execution Environments for AI Agents - Northflank Blog](https://northflank.com/blog/ephemeral-execution-environments-ai-agents)
- [Your Container Is Not a Sandbox: State of MicroVM Isolation in 2026](https://emirb.github.io/blog/microvm-2026/)
- [Kubernetes Agent Sandbox - kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox)
- [Unleashing Autonomous AI Agents: Kubernetes Standard for Agent Execution - Google Open Source Blog](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html)
- [Isolate AI Code Execution with Agent Sandbox - GKE Docs](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/agent-sandbox)
- [Agent Governance Toolkit Architecture Deep Dive - Microsoft Tech Community](https://techcommunity.microsoft.com/blog/linuxandopensourceblog/agent-governance-toolkit-architecture-deep-dive-policy-engines-trust-and-sre-for/4510105)
- [Introducing the Agent Governance Toolkit - Microsoft Open Source Blog](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)
- [Least Privilege and Capability Containment: Designing Agents That Cannot Exceed Their Mandate](https://notes.muthu.co/2026/04/least-privilege-and-capability-containment-designing-agents-that-cannot-exceed-their-mandate/)
- [Navigating Security Tradeoffs of AI Agents - Unit 42, Palo Alto Networks](https://unit42.paloaltonetworks.com/navigating-security-tradeoffs-ai-agents/)
- [Four Security Principles for Agentic AI Systems - AWS Security Blog](https://aws.amazon.com/blogs/security/four-security-principles-for-agentic-ai-systems/)
- [Agentic Runtime Security - HashiCorp Blog](https://www.hashicorp.com/en/blog/agentic-runtime-security-solving-agentic-ai-identity-and-access-gaps)
- [Secure AI Agent Authentication Using HashiCorp Vault Dynamic Secrets - HashiCorp Developer](https://developer.hashicorp.com/validated-patterns/vault/ai-agent-identity-with-hashicorp-vault)
- [SPIFFE/SPIRE Concepts](https://spiffe.io/docs/latest/spire-about/spire-concepts/)
- [How I Built Sandboxes That Boot in 28ms Using Firecracker Snapshots - DEV Community](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k)
- [Zero-Trust Kubernetes: Enforcing Security with Custom Admission Webhooks - Microsoft Tech Community](https://techcommunity.microsoft.com/blog/azureinfrastructureblog/zero-trust-kubernetes-enforcing-security--multi-tenancy-with-custom-admission-we/4466646)
- [Security and Complexity Slow Enterprise AI Agent Adoption - Help Net Security](https://www.helpnetsecurity.com/2026/02/24/ai-agents-business-processes-security-complexity/)
