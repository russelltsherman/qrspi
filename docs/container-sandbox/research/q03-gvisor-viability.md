# Q3: Is gVisor a Viable Middle Ground for Adversarial Container Sandboxing?

**Research Date:** 2026-04-18
**Project:** Container sandbox for agentic AI tasks with hard security boundaries

---

## Summary and Recommendation

**Short answer: gVisor is a credible middle ground, but "kernel exploits out of scope" is only a defensible position in specific, bounded threat models — not for a fully adversarial agent.**

gVisor reduces the host kernel attack surface dramatically (from 300+ syscalls to roughly 70-80 host-visible syscalls), is written in a memory-safe language, and is proven at Google-scale in Cloud Run, GKE Sandbox, and at Cloudflare and Ant Group. For a threat model where the risk is accidental exploitation or opportunistic escape — i.e., a misconfigured but not deliberately weaponized agent — gVisor is sufficient and operationally simpler than Kata/Firecracker.

For a fully adversarial threat model — where the agent is assumed to actively probe for escape vectors, may execute deliberately crafted exploit payloads, or where multi-tenancy means a successful escape compromises other tenants — gVisor's user-space kernel boundary is weaker than hardware VM isolation. A determined attacker who compromises the Sentry (gVisor's Go kernel) still runs code with access to the host kernel through the ~70-80 syscalls the Sentry is permitted, and the Sentry has had exploitable logic bugs despite being written in Go.

**Recommendation tiers:**

| Threat Level | Recommendation |
|---|---|
| Accidental/opportunistic misuse | gVisor is sufficient with defense-in-depth (network egress proxy, resource limits, no privilege escalation path) |
| Moderately adversarial (untrusted but not weaponized code) | gVisor + extra hardening is acceptable; accept residual risk consciously |
| Fully adversarial (actively malicious agent trying to escape) | Kata Containers or Firecracker; hardware VM boundary is mandatory |
| Multi-tenant with blast radius concerns | Kata/Firecracker; never gVisor alone |

The key question to answer before choosing gVisor: "Is the agent generating and executing code that might deliberately probe kernel/sentry boundaries?" If yes, the "kernel exploits out of scope" assumption fails because the agent's behavior can be weaponized toward that exact boundary.

---

## 1. gVisor Architecture: Sentry and Gofer

### The Sentry

The Sentry is gVisor's user-space application kernel — a complete reimplementation of the Linux system call interface written in Go. It is not a thin shim; it reimplements memory management, filesystem operations, networking (with its own TCP/IP stack), process management, signal handling, and namespaces. Critically, the Sentry **never passes syscalls through to the host kernel**. Every syscall from a sandboxed process is intercepted and handled entirely within the Sentry.

The Sentry itself is sandboxed: it runs under a strict seccomp-BPF filter that limits it to approximately 53-70 host-visible syscalls (without networking; ~211 with networking). This is the second isolation layer — even if an attacker compromises the Sentry, they are confined to these ~70 host syscalls rather than the full ~300+ syscall Linux ABI.

Because the Sentry is written in Go (a memory-safe language), an entire class of memory corruption vulnerabilities endemic to C-based kernels (buffer overflows, use-after-free, format strings) does not apply. However, Go's memory safety does not prevent **logic bugs**, and at least one exploitable shmctl logic bug has been demonstrated (see Section 3).

### The Gofer

The Gofer process is responsible for filesystem operations. It is a separate, isolated process that mediates all file I/O for the container. The Sentry communicates with the Gofer through a Unix domain socket (UDS) using a version of the 9P protocol. The Gofer validates and executes file operations on behalf of the container — this design means that even a fully compromised Sentry cannot directly open arbitrary host files; it must go through the Gofer.

This design provides meaningful defense-in-depth: the filesystem attack surface from a compromised Sentry is limited to what the Gofer is configured to expose.

### Platform Mechanisms (How Syscalls Are Intercepted)

gVisor has three platforms, of which two are current:

**Systrap (default since mid-2023):** Uses `seccomp`'s `SECCOMP_RET_TRAP` feature. When a sandboxed process executes a syscall, the kernel sends `SIGSYS` to the process. A custom signal handler in the sandboxed thread transfers control to the Sentry via shared memory. The Sentry handles the call and reflects the result back. Systrap replaced ptrace as the default due to significantly better performance (7x throughput improvement on some workloads).

**KVM platform:** Uses Linux's KVM functionality to run the Sentry as both guest OS and VMM, leveraging hardware virtualization extensions. Best performance on bare metal; degrades under nested virtualization.

**ptrace (deprecated):** Used `PTRACE_SYSEMU` to intercept syscalls. Slower than systrap due to high context-switch overhead. No longer supported; scheduled for removal.

**Sources:**
- [gVisor Architecture Guide: Security](https://gvisor.dev/docs/architecture_guide/security/)
- [gVisor Architecture Guide: Platforms](https://gvisor.dev/docs/architecture_guide/platforms/)
- [Releasing Systrap - A high-performance gVisor platform](https://gvisor.dev/blog/2023/04/28/systrap-release/)

---

## 2. Syscall Interception Model

The interception chain for the Systrap platform (default):

1. Sandboxed application executes a syscall instruction.
2. The seccomp-BPF filter installed on the process fires, returning `SECCOMP_RET_TRAP`.
3. The kernel sends `SIGSYS` to the triggering thread.
4. The custom signal handler (installed by gVisor) runs in the same thread, populating a shared memory region with the syscall arguments and signaling the Sentry.
5. The Sentry reads the syscall request, validates it, and executes the semantics in user space (e.g., managing its own PID table, routing I/O to the Gofer, handling its own virtual network stack).
6. The result is written back to the shared memory region, and the Sentry resumes the sandboxed thread.

**Key property:** The host kernel never sees the sandboxed application's syscalls. From the host kernel's perspective, the sandboxed process only makes requests through the Sentry's seccomp-filtered set of ~70 host syscalls. An attacker who wants to exploit the host kernel from within the sandbox must first escape the Sentry — a two-layer requirement.

**io_uring:** gVisor disables `io_uring` by default. This is a deliberate security decision: `io_uring` has been a major source of Linux kernel CVEs (it was responsible for >45% of all Linux kernel CVEs in 2023 by some counts), and blocking it at the seccomp layer prevents an entire category of kernel exploit paths. Most language runtimes fall back to standard I/O syscalls automatically.

**Sources:**
- [gVisor Architecture Guide: Security](https://gvisor.dev/docs/architecture_guide/security/)
- [Optimizing seccomp usage in gVisor](https://gvisor.dev/blog/2024/02/01/seccomp/)
- [How to handle people dismissing io_uring as insecure? (Hacker News)](https://news.ycombinator.com/item?id=44632240)

---

## 3. Known Bypass Techniques and CVEs

### The shmctl Logic Bug (2018)

The most widely cited gVisor escape proof-of-concept, documented by Max Justicz and analyzed by the Nabla Containers project, exploited a bug in gVisor's implementation of the `shmctl` syscall. The bug allowed targeted memory writes within the gVisor process address space. This was not a host escape but a **sandbox-to-sandbox lateral movement** attack: a process in one container could write to the memory of another container sharing the same gVisor instance.

Mitigation: Best practices call for each container to run in its own gVisor instance (one Sentry per container), not sharing a Sentry across processes. With per-instance isolation, this bug's practical impact is sharply limited — it cannot reach the host kernel.

**Lesson:** Logic bugs in Go remain exploitable. Memory safety prevents certain exploit classes but not semantic/logic vulnerabilities. The Sentry's attack surface, while much smaller than the Linux kernel, is not zero.

**Source:** [Discussing Exploitation and Priv Escalation - Analysis of gVisor exploit (Nabla Containers)](https://nabla-containers.github.io/2018/12/05/exploit-model/)

### CVE-2020-14386 (Contained by gVisor)

This Linux kernel vulnerability in the `PACKET_RX_RING` socket implementation could cause an out-of-bounds write, enabling privilege escalation on unprotected systems. gVisor was not vulnerable because:

1. It does not implement `PACKET_RX_RING`.
2. Raw sockets are disabled by default (require explicit `--net-raw` flag).
3. Even if reached, the vulnerability would affect the Sentry, not the host kernel directly.

This demonstrates the positive side of gVisor's approach: Linux kernel vulnerabilities that have no analog in gVisor's reimplementation simply do not exist in the sandbox.

**Source:** [How gVisor protects Google Cloud services from CVE-2020-14386](https://cloud.google.com/blog/products/containers-kubernetes/how-gvisor-protects-google-cloud-services-from-cve-2020-14386)

### CVE Policy and Known CVE Count

gVisor maintains a tiered CVE policy. A bug is eligible for a CVE only if it crosses the sandbox boundary (enables host code execution, lateral movement to other sandboxes, data exfiltration from the host, etc.) and the attacker has only SandboxUser/SandboxRoot/SandboxImage-level access. Bugs confined to a single sandbox are not assigned CVEs by default.

Publicly searchable CVE databases show very few gVisor-specific CVEs (fewer than 10 confirmed as of the research date), which reflects both the smaller attack surface and the tight CVE eligibility policy. This is not the same as "no bugs have been found" — it means bugs that don't cross the sandbox boundary are handled without CVEs.

**Source:** [Security and Vulnerability Reporting - gVisor](https://gvisor.dev/security/)

### Two-Layer Escape Requirement

A critical architectural property: escaping gVisor requires **two sequential exploits**:

1. Escape the Sentry (exploit a bug in gVisor's Go kernel).
2. Exploit the host kernel using only the ~70 host syscalls the Sentry is permitted.

This two-layer model is gVisor's strongest security claim. It is not equivalent to hardware VM isolation, but it is substantially stronger than standard container namespaces + seccomp. The 2018 shmctl bug demonstrated step 1 was achievable; no public demonstration of the full two-step escape (Sentry → host) exists as of this writing.

**Sources:**
- [Defending Kubernetes Clusters against Container Escape Attacks](https://www.appsecengineer.com/blog/defending-kubernetes-clusters-against-container-escape-attacks)
- [Let's discuss sandbox isolation](https://www.shayon.dev/post/2026/52/lets-discuss-sandbox-isolation/)

---

## 4. Syscall Compatibility Surface

### Overall Syscall Coverage

gVisor implements approximately 274 of 350 Linux syscalls (full or partial implementation as of the documentation). The unimplemented subset is largely composed of:

- Alternative syscalls for operations where a supported equivalent exists (e.g., some `io_uring` operations when standard I/O syscalls are available).
- Specialized hardware/device interfaces.
- Features that would compromise the security model (raw sockets, `PACKET_RX_RING`, etc.).

In practice, most applications do not fail on unimplemented syscalls because language runtimes and libraries probe for availability and fall back automatically.

**Source:** [gVisor Compatibility Guide](https://gvisor.dev/docs/user_guide/compatibility/)

### Language Runtimes

gVisor's release regression tests run against: Python, Java, Node.js, PHP, and Go. These runtimes work. In practice:

- **Python:** Works. `pip install` works (confirmed by Anthropic's Claude Code sandbox using gVisor with PyPI access).
- **Node.js / npm:** Works. npm installs against npm registries work; Anthropic's sandbox uses an egress proxy that allows npm registry traffic.
- **Go:** Works (gVisor itself is written in Go; toolchain compatibility is well-tested).
- **Java:** Works.

### Developer Tools

- **git:** Works. Standard git operations (clone, pull, push, commit) function under gVisor; there are no known blocking syscall issues with git.
- **Compilers (gcc, clang, rustc):** Generally work; ptrace-based debuggers have complications.
- **Docker inside gVisor:** KVM is not available from within a gVisor sandbox, so nested Docker (or any nested container runtime requiring KVM) will not function. This is a hard limitation.

### Known Limitations for Dev/Agent Workloads

| Feature | Status | Notes |
|---|---|---|
| `io_uring` | Disabled by default | Can be partially enabled; most runtimes fall back to standard I/O |
| KVM from within sandbox | Not supported | Blocks nested virtualization, nested Docker |
| Block device filesystem mount (ext4, FAT32) | Not supported from sandbox | Must be mounted on host |
| `iptables` / `nftables` | Partial | Basic networking works; advanced firewall manipulation does not |
| Raw sockets | Disabled by default | Requires explicit `--net-raw` flag |
| `ptrace` (from inside sandbox) | Limited | Affects debuggers like gdb/lldb; profiling tools may be impaired |
| Resource limits via cgroups inside sandbox | Not enforced | Must be applied from host |
| Custom hardware devices | Not supported | Except GPU and TPU |

**Sources:**
- [gVisor Compatibility Guide](https://gvisor.dev/docs/user_guide/compatibility/)
- [Reverse-engineering Claude's sandbox, then building my own](https://michaellivs.com/blog/sandboxed-execution-environment/)

---

## 5. Performance Overhead vs. Kata/Firecracker

### Startup Latency

| Runtime | Cold Start Latency | Notes |
|---|---|---|
| gVisor (Systrap) | 50–100ms | No VM boot; just Sentry initialization |
| Firecracker | 100–200ms | Optimized microVM boot; pre-warming reduces to <100ms |
| Kata Containers | 150–300ms | Full VM boot + guest kernel |
| Standard container (runc) | <10ms | No isolation overhead |

gVisor's startup advantage over Kata/Firecracker is real but narrowing, especially with Firecracker pre-warming. For agent workloads where cold starts are hidden behind LLM inference latency (typically 1–30s), the 100–200ms difference is not a determining factor.

**Anthropic's measured cold start (Claude Code sandbox):** 439–595ms total container start, of which gVisor Sentry initialization is a minority. The rest is image pull, process startup, and runtime initialization.

### Runtime Overhead

| Workload Type | gVisor Overhead | Kata/Firecracker Overhead |
|---|---|---|
| CPU-bound | 5–10% | 2–8% |
| Syscall-intensive | 20–50% | 5–15% |
| I/O-heavy | 10–30% | 5–15% |
| Network throughput | Significant (custom TCP stack) | Near-native |

gVisor's overhead is most pronounced for syscall-intensive and network-heavy workloads. Its custom network stack (not passing through the host network stack) imposes overhead on high-throughput networking. For typical agent workloads (code execution, file I/O, package installs), the overhead is acceptable — 10–30% worse than native.

### Memory Overhead

| Runtime | Additional Memory per Instance |
|---|---|
| gVisor Sentry | 10–50MB per sandbox |
| Kata Containers | 50–150MB (guest kernel + kata-agent) |
| Firecracker | 5–10MB hypervisor + guest kernel (~20–40MB total) |

gVisor's per-sandbox memory overhead is moderate — less than Kata but comparable to Firecracker when accounting for the guest kernel in both cases.

**Sources:**
- [Kata Containers vs Firecracker vs gVisor (Northflank)](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)
- [gVisor vs Kata vs Firecracker on VPS (onidel.com, 2025)](https://onidel.com/blog/gvisor-kata-firecracker-2025)
- [Reverse-engineering Claude's sandbox](https://michaellivs.com/blog/sandboxed-execution-environment/)
- [Performance and isolation analysis of RunC, gVisor and Kata Containers runtimes (Springer)](https://link.springer.com/article/10.1007/s10586-021-03517-8)

---

## 6. gVisor in Production: What Google Cloud Run Tells Us

Google Cloud Run (first-generation execution environment) and GKE Sandbox both use gVisor as their container isolation layer. This is the most significant real-world signal for gVisor's production viability.

### What Google Cloud Run's Use Tells Us

**The trust model matches agent sandboxing:** Cloud Run executes arbitrary user-provided container images from the general internet. Google is implicitly accepting that the code inside these containers could be adversarial, yet gVisor is the isolation boundary. This is the same threat profile as an agentic AI sandbox.

**The defense-in-depth stack:** Google does not rely on gVisor alone. Cloud Run wraps gVisor sandboxes inside a VM boundary (a VMM per-instance). This is a critical detail: Google uses gVisor as a layer within a VM, not as the sole isolation boundary. This is defense-in-depth, not gVisor-alone-is-sufficient.

**Scale and battle-testing:** Millions of Cloud Run invocations per day have been running through gVisor for several years. This is meaningful evidence that gVisor is operationally stable, compatible with a very wide range of workloads, and its attack surface has been subjected to substantial real-world adversarial pressure without publicly disclosed escapes.

**GKE Sandbox documented protections:** Google's security bulletins regularly show Linux kernel CVEs that gVisor prevents in GKE Sandbox. This empirical track record demonstrates the concrete security value.

### Other Production Deployments

- **Cloudflare Workers:** Cloudflare uses a different sandbox model (V8 isolates) but evaluated and respects gVisor's approach.
- **DigitalOcean App Platform:** Uses gVisor as part of their container runtime.
- **Ant Group:** Deployed gVisor for financial workload isolation.
- **Dangerzone (Freedom of the Press Foundation):** As of v0.7.0, uses gVisor to remove direct Linux kernel access from the document conversion sandbox. This is specifically a security-hardening use case, not just a performance tradeoff.

**Sources:**
- [Security design overview - Cloud Run](https://docs.cloud.google.com/run/docs/securing/security)
- [GKE Sandbox concepts](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods)
- [Safe Ride into the Dangerzone - gVisor blog](https://gvisor.dev/blog/2024/09/23/safe-ride-into-the-dangerzone/)
- [Why regulated industries are turning to Google Cloud Run with gVisor](https://medium.com/@sonal.sadafal/why-regulated-industries-are-turning-to-google-cloud-run-with-gvisor-for-secure-scalable-and-6adbe30e073f)

---

## 7. Isolation Comparison: gVisor vs. Kata/Firecracker for an Adversarial Threat Model

### What Each Technology Protects Against

| Attack Class | gVisor | Kata Containers | Firecracker |
|---|---|---|---|
| Standard container escapes (namespace exploits) | Yes | Yes | Yes |
| Linux kernel CVEs affecting standard containers | Yes (Sentry does not implement many buggy features) | Yes (guest kernel, isolated from host) | Yes (guest kernel, isolated from host) |
| Linux kernel 0-day via host syscall surface | Partial (reduced to ~70 syscalls; still exposed) | No (VM boundary; host kernel not reachable from guest) | No (VM boundary; host kernel not reachable from guest) |
| gVisor Sentry logic bugs | In scope / possible | N/A | N/A |
| Hardware side channels (Spectre, L1TF) | Not protected (relies on host) | Not protected (relies on host) | Not protected (relies on host) |
| Resource exhaustion (CPU, memory) | Partial (external cgroups needed) | Partial | Partial |
| Network-based attacks | Reduced (custom network stack) | Standard VM networking | Minimal VM networking |

### The Fundamental Difference

The fundamental difference between gVisor and Kata/Firecracker is not the number of syscalls or the language the kernel is written in — it is the **nature of the isolation boundary**:

- **gVisor:** Software boundary. An attacker who escapes the Sentry runs code under the host kernel with the Sentry's seccomp filter. Exploiting the host kernel from this position requires finding a vulnerability in the permitted ~70 syscalls. This is hard but not impossible.

- **Kata/Firecracker:** Hardware boundary (KVM/Intel VT-x/AMD-V). An attacker who achieves guest kernel code execution is still inside a virtual machine. Crossing the hypervisor boundary requires exploiting a VMM (QEMU, Cloud Hypervisor, or Firecracker's Rust-based VMM), a qualitatively different and much more difficult attack surface. Hardware VM boundaries stop entire classes of kernel exploits dead.

### When gVisor Is "Good Enough"

gVisor's two-layer model (Sentry escape + host kernel exploit from restricted syscall set) represents a real, high barrier. The probability of a real-world agent code escape through this path is low — not zero, but low enough that for many threat models it is acceptable, especially with additional controls.

**Factors that make gVisor acceptable:**
- The agent is generating plausible code but is not assumed to be constructing deliberate kernel exploits.
- Network egress is proxied and restricted (limits what an escaped process can do).
- The "blast radius" of an escape is limited (one customer's data, not all customers' data, is at risk).
- Defense-in-depth controls exist at other layers (audit logging, behavioral monitoring, rate limiting).
- The operational complexity of running Kata/Firecracker is prohibitive in the target environment (e.g., nested VM contexts where KVM is unavailable).

**Factors that make gVisor insufficient:**
- The agent's code output could include deliberate kernel exploit payloads.
- Multi-tenancy where a successful escape from Tenant A reaches Tenant B.
- Compliance requirements specifying hardware isolation (PCI DSS, FedRAMP, etc.).
- High-value targets where the effort of a two-step exploit is justified.

**Sources:**
- [Firecracker vs gVisor: Which isolation technology should you use? (Northflank)](https://northflank.com/blog/firecracker-vs-gvisor)
- [How to sandbox AI agents in 2026 (Northflank)](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Let's discuss sandbox isolation](https://www.shayon.dev/post/2026/52/lets-discuss-sandbox-isolation/)
- [Choosing a Workspace for AI Agents (DEV Community)](https://dev.to/agentsphere/choosing-a-workspace-for-ai-agents-the-ultimate-showdown-between-gvisor-kata-and-firecracker-b10)

---

## 8. When Is "Kernel Exploits Out of Scope" Reasonable vs. Reckless?

### Reasonable Conditions

Accepting "kernel exploits out of scope" is a defensible engineering decision when:

1. **The attacker is not assumed to be kernel-exploit-capable.** An LLM agent generating Python scripts to accomplish task goals is not equivalent to an attacker with a custom kernel exploit payload. The threat model must distinguish between "code that might accidentally trigger a vulnerability" and "code deliberately crafted to exploit kernel bugs."

2. **You have the two-step barrier.** With gVisor, a kernel exploit requires first escaping the Sentry. This is not a free assumption — the attacker needs two separate vulnerabilities. If you accept this residual risk, you are accepting a compound probability, not a single vulnerability.

3. **You have compensating controls.** A restricted network egress proxy, behavioral monitoring, audit logging, and workload-level rate limiting reduce the value of a successful escape even if one occurs. If an escaped process can only reach allowlisted URLs and cannot exfiltrate large data volumes, the impact is bounded.

4. **Your deployment environment makes VM isolation impractical.** If you are running on a platform that does not provide KVM access (many managed cloud environments, GitHub Actions-style shared runners, certain Kubernetes services), Kata and Firecracker are operationally unavailable. gVisor runs anywhere Docker runs. In this environment, gVisor is not a compromise — it is the only available strong isolation mechanism.

5. **Anthropic does this for Claude Code.** Anthropic's own production agent sandbox (as reverse-engineered) uses gVisor, with a network egress proxy. This is a meaningful data point: one of the most security-focused organizations building agentic AI has evaluated this tradeoff and chosen gVisor.

### Reckless Conditions

Accepting "kernel exploits out of scope" becomes reckless when:

1. **The agent can execute arbitrary native code with exploit-construction primitives.** An agent that can compile and run C programs, load kernel modules, or use specialized exploit frameworks is a qualitatively different threat than one running Python scripts.

2. **You have high-value multi-tenant data co-located with untrusted workloads.** A successful two-step escape in a gVisor-only setup could reach other tenants' data. For regulated industries or high-value data, this is unacceptable.

3. **You are in scope for compliance frameworks requiring hardware isolation.** PCI DSS, FedRAMP High, and HIPAA high-sensitivity environments may require hardware VM boundaries. "We use gVisor" is not an acceptable compliance answer in these contexts.

4. **The threat model explicitly includes adversarial agents.** If your design brief says "assume the agent is attempting to escape," then the two-layer gVisor model is being tested by a sophisticated adversary who has time and motivation to work through both layers. The 2018 shmctl bug demonstrated Sentry escape is achievable; a motivated researcher or adversary can find more.

5. **No additional hardening exists.** gVisor alone, without network egress control, without resource limits, without monitoring, and without additional seccomp filtering, is not the same as gVisor as part of a defense-in-depth stack. "We use gVisor" is not a complete security statement.

**Sources:**
- [gVisor Security Model](https://gvisor.dev/docs/architecture_guide/security/)
- [Firecracker, gVisor, Containers, and WebAssembly - Comparing Isolation Technologies for AI Agents (SoftwareSeni)](https://www.softwareseni.com/firecracker-gvisor-containers-and-webassembly-comparing-isolation-technologies-for-ai-agents/)
- [Reverse-engineering Claude's sandbox](https://michaellivs.com/blog/sandboxed-execution-environment/)

---

## 9. Operational Considerations

### Where gVisor Cannot Run

- **Nested VM environments without KVM passthrough.** gVisor's KVM platform requires bare-metal KVM access. The Systrap platform works inside VMs without KVM passthrough, but at reduced performance. Many managed Kubernetes offerings (EKS, some GKE node pools) do not expose KVM to worker nodes.
- **Environments requiring nested container runtimes.** An agent that needs to run Docker inside the sandbox (e.g., building and testing container images) cannot do so under gVisor because KVM is not available within the sandbox.

### Deployment Simplicity

gVisor's deployment simplicity advantage over Kata/Firecracker is real:

- gVisor runs as a standard container runtime (`runsc`), integrable into Docker and Kubernetes with a `RuntimeClass` annotation.
- No hypervisor binary, no guest kernel image, no additional VM infrastructure required.
- Compatible with all environments where Docker and seccomp work.

Kata Containers require a VMM (QEMU or Cloud Hypervisor), a guest kernel image, and either bare-metal KVM or hardware-assisted virtualization passthrough. Firecracker requires bare-metal KVM. Both have more complex operational requirements.

**Sources:**
- [Production guide - gVisor](https://gvisor.dev/docs/user_guide/production/)
- [Building Secure, Scalable, and Isolated AI Agent Runtimes on GKE](https://medium.com/@derrickchwong/building-secure-scalable-and-isolated-ai-agent-runtimes-on-gke-3cc82b0511ff)

---

## 10. Decision Framework

```
Is this a fully adversarial threat model (agent deliberately crafting escapes)?
├── Yes → Use Kata Containers or Firecracker. Hardware VM boundary is required.
└── No → Is KVM available in your deployment environment?
    ├── No → gVisor (Systrap) is your best available option. Add defense-in-depth.
    └── Yes → Choose based on operational cost vs. security confidence:
        ├── If highest security confidence needed → Kata/Firecracker
        └── If operational simplicity matters and risk is bounded → gVisor + defense-in-depth
```

**Defense-in-depth stack if using gVisor:**
1. Network egress proxy with allowlist (critical — limits blast radius of escape)
2. No KVM passthrough to sandbox
3. Resource limits via host cgroups
4. Per-agent gVisor instance (no Sentry sharing between agents)
5. Behavioral monitoring / audit logging
6. Minimal capabilities (drop all unnecessary Linux capabilities)
7. Read-only root filesystem where possible

---

## Sources

- [gVisor Architecture Guide: Security](https://gvisor.dev/docs/architecture_guide/security/)
- [gVisor Architecture Guide: Platforms](https://gvisor.dev/docs/architecture_guide/platforms/)
- [gVisor Architecture Guide: Performance](https://gvisor.dev/docs/architecture_guide/performance/)
- [gVisor Security and Vulnerability Reporting](https://gvisor.dev/security/)
- [gVisor Compatibility Guide](https://gvisor.dev/docs/user_guide/compatibility/)
- [gVisor Production Guide](https://gvisor.dev/docs/user_guide/production/)
- [gVisor Security Basics - Part 1](https://gvisor.dev/blog/2019/11/18/gvisor-security-basics-part-1/)
- [Releasing Systrap - A high-performance gVisor platform](https://gvisor.dev/blog/2023/04/28/systrap-release/)
- [Optimizing seccomp usage in gVisor](https://gvisor.dev/blog/2024/02/01/seccomp/)
- [Safe Ride into the Dangerzone: Reducing attack surface with gVisor](https://gvisor.dev/blog/2024/09/23/safe-ride-into-the-dangerzone/)
- [Containing a Real Vulnerability (CVE-2020-14386)](https://gvisor.dev/blog/2020/09/18/containing-a-real-vulnerability/)
- [How gVisor protects Google Cloud services from CVE-2020-14386](https://cloud.google.com/blog/products/containers-kubernetes/how-gvisor-protects-google-cloud-services-from-cve-2020-14386)
- [Security design overview - Cloud Run](https://docs.cloud.google.com/run/docs/securing/security)
- [GKE Sandbox concepts](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods)
- [Discussing Exploitation and Priv Escalation - Analysis of gVisor exploit (Nabla Containers)](https://nabla-containers.github.io/2018/12/05/exploit-model/)
- [Kata Containers vs Firecracker vs gVisor (Northflank)](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)
- [Firecracker vs gVisor (Northflank)](https://northflank.com/blog/firecracker-vs-gvisor)
- [How to sandbox AI agents in 2026 (Northflank)](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [What is gVisor? (Northflank)](https://northflank.com/blog/what-is-gvisor)
- [gVisor vs Kata vs Firecracker on VPS (onidel.com, 2025)](https://onidel.com/blog/gvisor-kata-firecracker-2025)
- [Choosing a Workspace for AI Agents: gVisor vs Kata vs Firecracker (DEV Community)](https://dev.to/agentsphere/choosing-a-workspace-for-ai-agents-the-ultimate-showdown-between-gvisor-kata-and-firecracker-b10)
- [Firecracker, gVisor, Containers, and WebAssembly - Comparing Isolation Technologies for AI Agents (SoftwareSeni)](https://www.softwareseni.com/firecracker-gvisor-containers-and-webassembly-comparing-isolation-technologies-for-ai-agents/)
- [Reverse-engineering Claude's sandbox, then building my own](https://michaellivs.com/blog/sandboxed-execution-environment/)
- [Let's discuss sandbox isolation](https://www.shayon.dev/post/2026/52/lets-discuss-sandbox-isolation/)
- [Building Secure, Scalable, and Isolated AI Agent Runtimes on GKE](https://medium.com/@derrickchwong/building-secure-scalable-and-isolated-ai-agent-runtimes-on-gke-3cc82b0511ff)
- [Performance and isolation analysis of RunC, gVisor and Kata Containers runtimes (Springer)](https://link.springer.com/article/10.1007/s10586-021-03517-8)
- [Enhancing Container Security with gVisor (Medium)](https://medium.com/@GiteshWadhwa/enhancing-container-security-with-gvisor-a-deeper-look-into-application-kernel-isolation-585af4652781)
- [Defending Kubernetes Clusters against Container Escape Attacks](https://www.appsecengineer.com/blog/defending-kubernetes-clusters-against-container-escape-attacks)
- [Google Gvisor CVE list (CVEDetails)](https://www.cvedetails.com/product/69948/Google-Gvisor.html?vendor_id=1224)
