# Q1: Kata Containers vs. Firecracker — Which Runtime?

**Research date:** 2026-04-18
**Question:** For a container sandbox running short-lived agentic AI tasks with hard security boundaries against potentially adversarial agents, should we use Kata Containers or Firecracker as the isolation runtime?

---

## Summary and Recommendation

**Recommendation: Firecracker (run directly), not Kata Containers.**

For a purpose-built adversarial sandbox where security constraints are enforced at the VM, OS, and network layers — not the application layer — Firecracker is the superior choice. The reasons:

1. **Firecracker has a dramatically smaller attack surface.** ~83,000 lines of Rust vs. QEMU's 1.4M+ lines of C. Fewer lines of code means fewer places for exploitable bugs to hide. A formal Trail of Bits security audit in 2023 found zero critical vulnerabilities in the VMM itself.

2. **The jailer is a purpose-built adversarial containment mechanism.** The Firecracker jailer applies chroot, cgroups, seccomp-BPF, privilege dropping, and fd scrubbing to the VMM process itself — meaning even a VMM compromise faces a second containment barrier. Kata has no equivalent host-side jailer for the VMM process.

3. **Short-lived workloads are Firecracker's design target.** AWS Lambda has run Firecracker in production for 7+ years across trillions of invocations. Snapshot/restore brings boot times to 28ms. This project's workload profile (minutes to a few hours, short-lived invocations) maps exactly to Firecracker's design envelope.

4. **Kata Containers is an orchestration framework, not a new isolation primitive.** Kata wraps VMMs like Firecracker or QEMU inside Kubernetes-compatible tooling. If you run Kata with its Firecracker backend, you still get Firecracker's isolation — but you add Kata's complexity layers. For a custom sandbox (not a general Kubernetes cluster), this overhead is pure cost with no benefit.

5. **The production AI sandbox ecosystem has standardized on Firecracker.** E2B (200M+ sandboxes, Fortune 100 customers), Northflank, and Amazon Bedrock AgentCore all use Firecracker directly. Kata is used in multi-tenant Kubernetes environments where developer workflow compatibility matters more than raw security minimalism.

**The one caveat:** Running Firecracker directly requires building orchestration infrastructure (VM lifecycle, network plumbing, image management). This is non-trivial. Kata provides this out of the box for Kubernetes workloads. For this project, where custom orchestration is explicitly in scope and security minimalism is paramount, the operational investment is justified.

---

## 1. Architecture Differences

### Firecracker

Firecracker is a lightweight Virtual Machine Monitor (VMM) written in Rust by AWS, purpose-built for short-lived multi-tenant workloads. It uses the Linux KVM interface directly to create microVMs. Key architectural properties:

- **Minimal device model:** Only 5 virtio devices are supported — networking (virtio-net), block storage (virtio-blk), shared filesystem (virtio-fs), vsock, and a minimal serial console. No USB, no PCI bus, no BIOS, no UEFI. This is intentional: every emulated device is an attack surface.
- **Single process per VM:** Each microVM runs as a single Firecracker process on the host. There is no daemon, no shared state between VM instances.
- **Direct kernel boot:** Guest kernels boot directly without BIOS or UEFI firmware phases. This eliminates a significant class of firmware-layer vulnerabilities and speeds up boot.
- **Rust memory safety:** The entire VMM codebase is in Rust, eliminating buffer overflows, use-after-free, and other memory corruption bugs that have historically been the source of VM escape vulnerabilities in QEMU.
- **The jailer:** A companion process that wraps each Firecracker VMM in an additional layer of OS-level containment (see Section 3).

Isolation is hardware-enforced via Intel VT-x or AMD-V CPU virtualization extensions, with Extended Page Tables (EPT) providing separate memory address spaces for each guest.

### Kata Containers

Kata Containers is not an isolation technology — it is an **orchestration framework** that makes microVM-based isolation work within standard container workflows (Kubernetes, containerd, CRI-O). Its architecture:

- **VMM backends:** Kata supports multiple VMM backends: QEMU (default), Firecracker, and Cloud Hypervisor. The security properties of a Kata deployment depend entirely on which backend is chosen.
- **Guest agent:** A `kata-agent` process runs inside each VM, accepting commands from the host-side `kata-runtime` via a vsock channel. This agent manages container processes, namespaces, and mounts inside the VM.
- **shimv2 interface:** Kata implements the containerd shimv2 API, making it look like a standard container runtime from the Kubernetes perspective. Pods are scheduled normally; Kata transparently upgrades each pod to a microVM.
- **Network bridging:** Kata requires additional network plumbing to bridge the VM's virtual network interface into the host's pod network (typically via TC redirect or macvtap).
- **No per-VMM jailer:** Kata does not apply a jailer around the VMM process. When using the Firecracker backend, the VMM runs without the jailer's chroot/seccomp hardening unless explicitly configured.

The key insight: **Kata with Firecracker backend gives you Firecracker isolation minus the jailer, plus Kubernetes compatibility.** For a dedicated sandbox platform, this tradeoff is unfavorable.

### When Kata Adds Value

Kata makes the most sense when:
- You need to drop microVM isolation into an existing Kubernetes cluster with minimal changes (just add a `RuntimeClass`)
- You need to support workloads that depend on standard OCI image tooling (Docker Hub images, standard container build pipelines)
- You want flexibility to swap VMM backends over time without changing your application layer
- Your team lacks deep virtualization expertise and wants the orchestration complexity abstracted away

---

## 2. The Firecracker Jailer

The jailer (`firecracker-jailer`) is a companion binary that wraps each Firecracker VMM process in a multi-layer OS containment barrier. It is invoked instead of Firecracker directly and applies security measures before exec-ing the VMM. It is the component that makes Firecracker suitable for adversarial multi-tenant environments.

### What the Jailer Does

**Chroot isolation (mount namespace + pivot_root):** The jailer uses `unshare()` and `pivot_root()` to place the Firecracker process inside a dedicated chroot. The Firecracker binary is copied into the jail directory — each VMM instance has its own copy, preventing cross-VM memory sharing at the binary level.

**Privilege dropping:** The jailer starts as root to create device nodes (`/dev/kvm`, `/dev/net/tun`), then irrevocably drops to a specified unprivileged UID/GID before exec-ing Firecracker. The VMM process cannot re-acquire privileges.

**Cgroup-based resource limits:** Via the `--cgroup` flag, operators bind each VMM to specific cgroup hierarchies (supporting both v1 and v2). This enforces per-VM CPU, memory, and I/O limits, preventing any one adversarial VM from exhausting host resources (denial-of-service resistance).

**File descriptor scrubbing:** Before exec, the jailer closes all file descriptors except stdin/stdout/stderr and explicitly wipes environment variables. This prevents accidental capability leakage from the parent process — a critical property when orchestrating many VMs from a privileged parent.

**Process resource limits (setrlimit):** Via `--resource-limit`, the jailer applies `setrlimit()` restrictions including maximum file size (`fsize`) and maximum open file descriptors (`no-file`, defaults to 2048). This bounds the damage a compromised VMM can do to the host filesystem.

**Optional PID namespace:** The `--new-pid-ns` flag spawns Firecracker as a pseudo-init process in a new PID namespace, preventing PID-based attacks that cross VM boundaries.

**Network namespace:** The jailer supports joining pre-configured network namespaces via `--netns`, enabling per-VM network isolation from the host.

### Defense-in-Depth Model

The jailer creates a two-boundary model for adversarial workloads:

```
[untrusted agent code]
        |
  [guest kernel]        <- hardware-virtualized boundary (KVM/EPT)
        |
  [Firecracker VMM]    <- minimal Rust codebase, ~83K lines
        |
  [jailer containment] <- chroot, seccomp-BPF, cgroups, dropped privs
        |
  [host OS]
```

An attacker who escapes the guest kernel must still compromise the VMM, then escape the jailer's chroot and seccomp filters to reach the host. Each layer is independently defensible.

### Jailer Operational Notes

The jailer documentation explicitly states: "all inputs to the jailer are considered trusted." This means the operator must:
- Ensure correct permissions on all paths passed to the jailer
- Pre-stage VM resources (disk images, kernels) with correct permissions inside the jail directory
- Handle cleanup of cgroup notifications and temporary files on VM teardown

This is an operational responsibility, not a security weakness — it means the threat model correctly assumes a trusted operator, not a trusted guest.

---

## 3. Startup Latency and Overhead

### Firecracker Performance Specifications

The Firecracker SPECIFICATION.md defines these hard performance contracts:

| Metric | Specification |
|--------|--------------|
| VMM process startup | ≤ 8 CPU ms, wall clock 6–60ms typical |
| Guest userspace boot | ≤ 125ms from `InstanceStart` API call |
| VMM memory overhead | ≤ 5 MiB per microVM |
| VM creation rate | ≥ 150 microVMs/second/host |

These numbers assume serial console disabled and minimal kernel/rootfs configuration.

### Snapshot/Restore: The Game Changer

For AI agent sandboxes, Firecracker's snapshot/restore capability transforms the performance profile:

- **Cold boot from scratch:** ~1 second (kernel load + init execution + agent startup)
- **Restore from snapshot:** ~28ms (memory-map snapshot, load CPU state, resume)

The snapshot mechanism captures complete VM state (memory contents, CPU registers, device state). On restore, the VM resumes from exactly the paused state. From the guest's perspective, time simply skips forward.

**Copy-on-Write efficiency:** Multiple VMs restored from the same snapshot share memory pages via CoW. A base snapshot for a Python agent environment might be shared across 50 concurrent instances, with each VM only allocating memory for pages it actually writes. This enables high-density operation.

**UFFD (userfaultfd) integration:** Firecracker supports Linux's userfaultfd mechanism (kernel >= 6.1 via `/dev/userfaultfd`, with syscall fallback). A host-side UFFD handler can serve memory pages on-demand rather than loading the entire snapshot upfront, further reducing time-to-first-instruction for large-memory VMs.

### Kata Containers Startup Latency

Kata Containers adds orchestration overhead on top of the VMM startup:

| Stage | Time |
|-------|------|
| containerd shim initialization | ~20–50ms |
| VMM boot (Firecracker backend) | ~100–200ms |
| Guest kernel boot | included above |
| kata-agent initialization | ~30–80ms |
| Container setup within guest | ~30–70ms |
| **Total (Kata + Firecracker backend)** | **~180–400ms** |

With QEMU backend, total Kata startup is typically 500ms–1s+.

Kata does not support Firecracker's snapshot/restore feature through its standard interface, so the 28ms restore path is not available to Kata users without significant custom work.

### Memory Overhead

- **Firecracker:** ~5 MiB VMM overhead per instance (plus guest RAM allocation)
- **Kata Containers:** ~10–20 MiB overhead per pod (kata-agent, shimv2, additional process state)

At scale (thousands of concurrent short-lived agents), the difference in per-instance overhead is meaningful for host density.

---

## 4. Operational Complexity

### Running Firecracker Directly

Firecracker deliberately has no built-in orchestration. Operators must build or adopt:

- **VM lifecycle management:** API calls to create/configure/start/stop VMs, cleanup of jailer directories after teardown
- **Kernel image management:** Maintaining guest kernel builds compatible with desired guest OS configurations
- **Root filesystem management:** Building and versioning minimal guest rootfs images; managing overlay filesystems for per-VM writable layers
- **Network configuration:** Creating tap interfaces, configuring routing/NAT, assigning network namespaces per VM
- **Snapshotter:** If using snapshot/restore, a system to create, store, and serve base snapshots; CoW layer management
- **Resource scheduling:** Deciding which host a new VM should land on, enforcing per-host VM density limits

This is substantial engineering. Teams building custom AI sandboxes (like E2B, CodeSandbox, Northflank) have each built their own orchestration layer on top of raw Firecracker.

**Estimated effort to production-ready orchestration:** 2–6 engineer-months for a well-scoped custom sandbox, depending on required features.

### Running Kata Containers

Kata Containers provides everything Firecracker lacks in terms of orchestration, at the cost of coupling to Kubernetes:

- **Kubernetes integration:** Install Kata, create a `RuntimeClass`, reference it in pod specs. Container scheduling, networking (CNI), storage (CSI), and lifecycle are handled by Kubernetes.
- **Image management:** Standard OCI images from any registry work without modification.
- **Network:** Standard Kubernetes CNI plugins work; Kata handles the VM-level bridging.
- **Observability:** Standard Kubernetes tooling (metrics, logs, tracing) works.

**Infrastructure prerequisite:** Kata requires a working Kubernetes cluster with nodes that have KVM access. For bare-metal or dedicated hardware, this is straightforward. On cloud VMs, nested virtualization must be available (supported on AWS, GCP, Azure for specific instance types).

**Managed vs. self-managed:** AWS EKS with EC2 bare metal nodes, Azure AKS, and GKE all support Kata Containers. AWS specifically recommends managed node groups over self-managed bare metal for most users, noting that users running self-managed bare metal become responsible for patching the OS, Kubernetes, and hypervisor stack themselves.

---

## 5. Security Properties

### Comparative Isolation Strength

Both Firecracker and Kata (with Firecracker or Cloud Hypervisor backend) provide hardware-enforced VM-level isolation. The key differentiators are:

| Property | Firecracker (direct) | Kata + Firecracker backend | Kata + QEMU backend |
|----------|---------------------|---------------------------|---------------------|
| Hardware isolation (KVM) | Yes | Yes | Yes |
| Minimal device emulation | Yes (~5 devices) | Yes | No (full QEMU device model) |
| VMM codebase size | ~83K lines Rust | ~83K lines Rust + Kata layers | 1.4M lines C (QEMU) |
| Jailer containment | Yes (full jailer) | Not by default | Not by default |
| Shared kernel risk | Eliminated | Eliminated | Eliminated |
| Memory-safe VMM | Yes (Rust) | Yes (Rust) | No (C) |
| Seccomp on VMM process | Yes (jailer) | Optional, not default | Optional |
| Guest-per-VM kernel | Yes | Yes | Yes |

**Critical note on Kata + QEMU:** If Kata is deployed with its default QEMU backend, the attack surface is orders of magnitude larger than Firecracker. QEMU has had numerous VM escape CVEs (e.g., VENOM, CVE-2019-14378, CVE-2021-3527). Kata with QEMU backend should not be used for adversarial workloads.

### Known CVEs and Escape History

**Container escapes (shared kernel baseline):** Between 2019 and 2025, 17 container escape vulnerabilities rated CVSS 9.0+ were documented. Recent examples:
- CVE-2024-21626 ("Leaky Vessels"): runc filesystem escape
- CVE-2025-23266 ("NVIDIAScape"): NVIDIA container toolkit privilege escalation
- CVE-2025-31133: runc masked path race condition

These affect standard containers, not microVMs. They reinforce why VM-level isolation is required for adversarial workloads.

**Firecracker-specific vulnerabilities:** The 2023 Trail of Bits audit found zero critical vulnerabilities in the Firecracker VMM. The CVE database shows a small number of issues:
- CVE-2026-1386: Jailer symlink traversal enabling arbitrary host file overwrite under specific conditions. AWS services were not impacted because they restrict access to the jailer folder. This is the class of vulnerability the jailer is specifically designed to contain — the fix is operational hardening of jailer directory permissions.
- Microarchitectural attacks: A 2023 academic paper found that Firecracker's virtualization layer provides limited mitigation against certain cache side-channel attacks (a property shared with all KVM-based hypervisors, not specific to Firecracker).
- Operation forwarding attacks: Research found that microVM-based containers can be vulnerable to I/O-level resource interference attacks, causing measurable performance degradation. This is a DoS concern, not an isolation breach.

**Kata Containers CVEs:** CVE-2020-2024 and CVE-2020-2025 (fixed in 1.11.0) allowed malicious guest containers to access the host root filesystem and trick the runtime into unmounting host mount points. These were architectural issues in Kata's runtime, not the underlying VMM.

**Hypervisor escape economics:** A VM escape from Firecracker's KVM boundary would command $250K–$500K on the exploit market, reflecting their practical rarity. This is the operative security comparison vs. container escapes, which are routinely weaponized.

### Defense-in-Depth Hardening

For adversarial workloads, the recommended architecture (the "Matryoshka model") is:

1. Host OS: hardened, minimal packages, no unnecessary services
2. VMM: unprivileged, Rust-based, seccomp-jailed (Firecracker + jailer)
3. Guest kernel: isolated, ephemeral, built with KASLR/SMEP/SMAP
4. Optional container runtime inside guest (for image compatibility)
5. Untrusted agent code

Additional hardening recommendations for Firecracker deployments:
- Mount guest root filesystems read-only; use an overlayfs or tmpfs for writable layers with `noexec,nodev,nosuid`
- Run the VMM process as a dedicated unprivileged user, never root
- Protect the API socket path — only the orchestrator should have access
- Apply custom seccomp profiles to the jailer (the default profile is already restrictive, but can be further tightened)
- Build minimal guest kernels — disable unused kernel subsystems to reduce the guest kernel attack surface

---

## 6. Ecosystem Maturity and Container Tooling

### Firecracker Ecosystem

**Project status:** Firecracker is maintained by AWS, with 7+ years of production use in Lambda, Fargate, and Bedrock AgentCore. The GitHub repository has 27,000+ stars. AWS has published a formal SPECIFICATION.md that functions as a contractual performance and behavior guarantee — an unusual level of rigor for an open source project.

**Container tooling integration:** Firecracker does not natively speak the Docker or containerd APIs. The `firecracker-containerd` project (maintained by AWS) bridges this gap, providing:
- A containerd shim that creates a Firecracker microVM per container
- A devmapper-based snapshotter that creates OCI layer images as block devices for virtio-blk passthrough into the VM
- Support for standard OCI image pulls and standard `ctr` / `nerdctl` commands

This integration is functional but lower-level than Kata's. The devmapper snapshotter in particular has known operational friction (see GitHub issue #12558 in the Kata repo for a representative example of devmapper configuration challenges).

**AI sandbox ecosystem:** As of 2025-2026, Firecracker has become the de facto standard for AI agent sandboxes. E2B (200M+ sandboxes), Northflank, Amazon Bedrock AgentCore, CodeSandbox (with low-latency memory decompression), and Daytona (with Kata as optional upgrade) all build on Firecracker. The `awesome-sandbox` GitHub repository catalogs this ecosystem.

**Rust-vmm shared crates:** Both Firecracker and Cloud Hypervisor are built on the `rust-vmm` shared crate ecosystem, jointly maintained by AWS, Intel, Google, and Microsoft. This means foundational components are well-maintained and receive broad security review.

### Kata Containers Ecosystem

**Project status:** Kata Containers is a CNCF project under the OpenInfra Foundation. It reached version 3.x as of 2025 with active community involvement from Intel, Red Hat, IBM, and others. PTG (Project Teams Gathering) summaries indicate active work on community governance, integration with the Confidential Containers (CoCo) CNCF project, and a Rust rewrite of the runtime.

**Kubernetes integration:** First-class. Install via a package manager, create a `RuntimeClass`, annotate pods. The shimv2 interface for containerd is the recommended path. CRI-O is also supported.

**Documentation quality:** Kata's documentation is comprehensive and covers Kubernetes integration, multiple VMM backends, CI/CD integration, and security hardening. The docs are easier to follow for teams without deep virtualization backgrounds.

**Production adoption:** Kata powers production workloads in banking, payment systems, multi-tenant SaaS, and CI/CD pipelines. AWS EKS, Azure AKS, and GKE all offer Kata support. This is a mature, production-grade project.

**Limitation for this use case:** Kata's strength is its Kubernetes compatibility layer. For a custom-built sandbox platform not using Kubernetes, Kata's main value proposition disappears, leaving only its orchestration complexity as overhead.

---

## 7. AWS Lambda as a Reference Architecture

AWS Lambda is the most significant real-world validation of Firecracker's suitability for this project's use case.

**Scale:** Lambda serves trillions of invocations per month. Thousands of function instances run per host with hardware isolation between tenants.

**Workload profile:** Lambda functions are explicitly short-lived (configurable up to 15 minutes, typical invocations measured in seconds to minutes). This maps directly to agentic task invocations.

**Adversarial threat model:** Lambda explicitly considers customer workloads adversarial — customers are treated as untrusted tenants. The isolation model must withstand deliberate escape attempts, not just buggy code.

**Seven-year production record:** AWS's Marc Brooker published "Seven Years of Firecracker" in September 2025, noting:
- Virtualization moves the security-critical interface from OS to hardware-supported VMM boundary — a fundamentally stronger guarantee
- The platform handles workloads from millisecond to multi-hour sessions
- Snapshot cloning proved essential for economically viable density
- Simplicity (terminating VMs after fixed periods rather than complex GC) produces cleaner isolation than clever resource management

**Lambda tenant isolation mode (2026):** AWS added a `TenantIsolationMode` feature to Lambda that routes all invocations for a given tenant to exclusive execution environments, ensuring zero VM sharing across tenants. This is an application-layer policy built on top of Firecracker's VM-level isolation — demonstrating that Firecracker is the floor, not the ceiling, of isolation design.

**Bedrock AgentCore:** Amazon's managed AI agent infrastructure also uses Firecracker, extending the production validation directly to the agentic workload case.

---

## 8. Fit Assessment for This Project

This project builds a container sandbox for agentic AI tasks with hard security boundaries against potentially adversarial agents, enforced at VM, OS, and network layers.

| Criterion | Firecracker (direct) | Kata Containers |
|-----------|---------------------|-----------------|
| Adversarial isolation strength | Excellent (jailer + minimal VMM) | Good (no jailer by default) |
| Short-lived invocations | Excellent (design target, 28ms snapshots) | Good (no native snapshot/restore) |
| Attack surface minimization | Excellent (83K lines Rust, 5 devices) | Good with Firecracker backend, Poor with QEMU |
| Kubernetes not required | Yes — standalone operation | Kata is designed around Kubernetes |
| Container tooling (Docker/OCI) | Functional (firecracker-containerd) | Excellent (native OCI/CRI) |
| Operational complexity | High (must build orchestration) | Medium (K8s required but handles complexity) |
| Snapshot/restore for density | Native support | Not supported via standard interface |
| Production AI sandbox precedent | Strong (E2B, Lambda, Bedrock AgentCore) | Limited (primarily Kubernetes deployments) |
| Community/docs quality | Good (AWS-backed, formal spec) | Excellent (CNCF, broad enterprise adoption) |

**Bottom line:** The security profile, performance characteristics, and production precedent all point to Firecracker as the correct primitive for this use case. The operational investment in building orchestration is the real cost, and it is justified by the security and performance advantages that cannot be replicated through Kata.

The one scenario where Kata would be preferred: if this project's sandbox layer needs to integrate into an existing Kubernetes cluster and the team cannot justify the engineering investment to build custom orchestration. In that case, Kata with Cloud Hypervisor backend (not QEMU) is the right choice.

---

## Sources

- [Kata Containers vs Firecracker vs gVisor: Which container isolation tool should you use? — Northflank](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)
- [Firecracker vs Kata Containers: Isolation as a Defensive Strategy — Amritha Lal, Medium](https://medium.com/@amrithalalk/firecracker-vs-kata-containers-isolation-as-a-defensive-strategy-910e1ebfee9b)
- [gVisor vs Kata Containers vs Firecracker MicroVMs on VPS (2025) — onidel.com](https://onidel.com/blog/gvisor-kata-firecracker-2025)
- [Kata, gVisor, or Firecracker? Container Isolation Guide — Edera](https://edera.dev/stories/kata-vs-firecracker-vs-gvisor-isolation-compared)
- [Choosing a Workspace for AI Agents: gVisor, Kata, and Firecracker — DEV Community](https://dev.to/agentsphere/choosing-a-workspace-for-ai-agents-the-ultimate-showdown-between-gvisor-kata-and-firecracker-b10)
- [Securing Containers at Scale: Deep Dive into Kata & Firecracker — evan.sh](https://evan.sh/blog/securing-containers)
- [Firecracker jailer documentation — GitHub](https://github.com/firecracker-microvm/firecracker/blob/main/docs/jailer.md)
- [Firecracker SPECIFICATION.md — GitHub](https://github.com/firecracker-microvm/firecracker/blob/main/SPECIFICATION.md)
- [Firecracker snapshot support documentation — GitHub](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md)
- [How I built sandboxes that boot in 28ms using Firecracker snapshots — DEV Community](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k)
- [Seven Years of Firecracker — Marc Brooker's Blog](https://brooker.co.za/blog/2025/09/18/firecracker.html)
- [Firecracker: Lightweight Virtualization for Serverless Computing — AWS News Blog](https://aws.amazon.com/blogs/aws/firecracker-lightweight-virtualization-for-serverless-computing/)
- [Tenant isolation — AWS Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/tenant-isolation.html)
- [Enhancing Kubernetes workload isolation and security using Kata Containers — AWS Containers Blog](https://aws.amazon.com/blogs/containers/enhancing-kubernetes-workload-isolation-and-security-using-kata-containers/)
- [Kata Containers on Kubernetes and Kata Firecracker VMM support — Gokul Chandra, Medium](https://gokulchandrapr.medium.com/kata-containers-on-kubernetes-and-kata-firecracker-vmm-support-28abb3a196e7)
- [Kata Containers at the October 2025 PTG — katacontainers.io](https://katacontainers.io/blog/kata-community-ptg-updates-october-2025/)
- [Your Container Is Not a Sandbox: The State of MicroVM Isolation in 2026 — emirb.github.io](https://emirb.github.io/blog/microvm-2026/)
- [What's the best code execution sandbox for AI agents in 2026? — Northflank](https://northflank.com/blog/best-code-execution-sandbox-for-ai-agents)
- [Firecracker, gVisor, Containers, and WebAssembly: Comparing Isolation Technologies for AI Agents — SoftwareSeni](https://www.softwareseni.com/firecracker-gvisor-containers-and-webassembly-comparing-isolation-technologies-for-ai-agents/)
- [Microarchitectural Security of AWS Firecracker VMM — arXiv (2023)](https://arxiv.org/pdf/2311.15999)
- [CVE-2026-1386: Arbitrary Host File Overwrite via Symlink in Firecracker Jailer — AWS Security Bulletin](https://aws.amazon.com/security/security-bulletins/rss/2026-003-aws/)
- [Kata Containers CVE-2020-2025 — community repository](https://github.com/kata-containers/community/blob/main/VMT/KCSA/KCSA-CVE-2020-2025.md)
- [firecracker-containerd snapshotter documentation — GitHub](https://github.com/firecracker-microvm/firecracker-containerd/blob/main/docs/snapshotter.md)
- [How to sandbox AI agents in 2026: Firecracker, gVisor, runtimes & isolation strategies — Manveer Crasto, Substack](https://manveerc.substack.com/p/ai-agent-sandboxing-guide)
- [Top AI Code Sandbox Products in 2025 — Modal](https://modal.com/blog/top-code-agent-sandbox-products)
- [Daytona vs E2B in 2026 — Northflank](https://northflank.com/blog/daytona-vs-e2b-ai-code-execution-sandboxes)
- [awesome-sandbox: Awesome Code Sandboxing for AI — GitHub](https://github.com/restyler/awesome-sandbox)
- [Firecracker internals: a deep dive inside the technology powering AWS Lambda — Tal Hoffman](https://www.talhoffman.com/2021/07/18/firecracker-internals/)
