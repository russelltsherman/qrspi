# Q2: What kernel version/image is used inside the microVM?

## Summary and Recommendation

**The microVM guest kernel is a genuine attack surface, but it is substantially smaller and more controllable than the shared-kernel attack surface of standard containers.** The key insights are:

1. **Use an LTS kernel (Linux 6.1) pinned to a specific sub-version.** Both Firecracker and Kata Containers ship CI-tested configurations based on Linux 6.1 LTS (supported through 2026-09-02 per Firecracker's policy). Chasing the latest mainline kernel introduces instability without meaningful security gains for a sandboxing use case.

2. **Disable kernel modules entirely.** Firecracker's reference configs set `CONFIG_MODULES=n` and pass `nomodule` on the kernel command line. This is the single most impactful minimalism decision: it eliminates all post-boot kernel extension and limits the attack surface to what was compiled in at build time.

3. **Keep the kernel image immutable and version-pinned.** The image must be treated as an artifact in a CI pipeline — built reproducibly from a known source commit, stored by content digest, and never mutated in place. Rebuilds are triggered by upstream kernel point releases or upstream LTS security patches, not by traditional "patch the running system" workflows.

4. **Adopt a shared base image updated on a regular cadence, not per-invocation bespoke kernels.** The kernel image is identical for all invocations of the same runtime version; what changes per invocation is the rootfs overlay. This allows centralized patching with immediate fleet-wide effect.

5. **Run `kernel-hardening-checker` against any custom kernel config** before promoting it. The Firecracker CI config already enables the major KSPP mitigations (PTI, RETPOLINE, SRSO, ASLR, stack canaries) but operators building custom configs for additional functionality need to verify they have not inadvertently regressed any of these.

6. **Plan for a 7–14 day patch SLA for kernel CVEs rated CVSS >= 7.** The Linux kernel issued over 3,500 CVEs in 2024; the majority are low-severity attribution artifacts, but critical privilege-escalation issues appear several times per year. A reproducible build pipeline makes rapid iteration feasible.

---

## 1. How Firecracker Handles Kernel Images

### Supported kernel versions and the support policy

Firecracker maintains a formal kernel support policy: at least two major guest kernel versions are supported at any time, each for a minimum of two years. As of early 2026 the active guest kernel versions are:

- **5.10** (supported since v1.0.0; end-of-support 2024-01-31 — now deprecated)
- **6.1** (supported since v1.9.0; end-of-support 2026-09-02)

When a third version is added, the oldest is deprecated. Firecracker's CI validates all supported kernel combinations on every commit.

Sources: [Firecracker kernel-policy.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/kernel-policy.md)

### Kernel image format

- **x86_64**: uncompressed ELF (`vmlinux`)
- **aarch64**: PE-formatted image (`Image`)

Firecracker does not support compressed kernel images. The image is loaded directly by the VMM, bypassing traditional bootloader machinery. This removes an entire class of boot-chain attack surface (UEFI, BIOS, GRUB).

Sources: [Firecracker rootfs-and-kernel-setup.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md)

### Default kernel command line parameters

Firecracker unconditionally appends the following to the guest kernel command line:

```
reboot=k panic=1 nomodule 8250.nr_uarts=0 i8042.noaux i8042.nomux i8042.dumbkbd swiotlb=noforce
```

When PCI is disabled, `pci=off` is also appended. Notable security-relevant flags:

- `nomodule` — disables all kernel module loading, preventing post-boot kernel extension
- `panic=1` — forces immediate reboot on kernel panic, limiting fault persistence
- `reboot=k` — signals the VMM rather than issuing a real reboot, keeping reboot under VMM control

Sources: [Firecracker rootfs-and-kernel-setup.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md), [Production Host Setup](https://jonathanwoollett-light.github.io/firecracker/book/book/prod-host-setup.html)

### Where kernels come from in practice

AWS provides pre-built kernels via the `spec.ccfc.min` S3 bucket, versioned as `vmlinux-6.1.128` (point release embedded in the name). The Firecracker repository also provides a `./tools/devtool build_ci_artifacts kernels` command to compile the exact CI kernels from source. Amazon Linux publishes microVM-specific kernels under tags of the form `microvm-kernel-6.1.128-3.201.amzn2023` in its kernel repository, sometimes carrying backported patches not yet in mainline.

Sources: [Firecracker microVMs: the power behind AWS Lambda](https://www.anthony-balitrand.fr/2025/08/12/firecracker-microvms-the-power-behind-aws-lambda/), [Firecracker getting-started.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)

---

## 2. How Kata Containers Handles Kernel Images

### Kernel philosophy

Kata's default guest kernel is described as "highly optimized for kernel boot time and minimal memory footprint, providing only those services required by a container workload." It tracks the latest Linux LTS release. In recent releases this has been Linux 5.15 or 6.1 depending on the Kata version; the CI-tested version is locked in `versions.yaml` in the kata-containers repository.

### Build system

Kata uses a `build-kernel.sh` script that:
1. Clones the Linux kernel source at the version specified in `versions.yaml`
2. Applies Kata-specific patches from `tools/packaging/kernel/patches/`
3. Applies a config fragment from `tools/packaging/kernel/configs/` named by architecture and hypervisor target (e.g., `x86_64_kata_kvm_6.1.x`)
4. Compiles and installs to `/usr/share/kata-containers/`

Configuration file naming: `${arch}_kata_${hypervisor_target}_${major_kernel_version}.x`

A separate `kata_config_version` tracks config-level changes independently of the kernel point release; the full version string (e.g., `6.1.38-83`) combines both.

Sources: [Kata kernel README](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kernel/README.md), [Kata guest-assets design doc](https://github.com/kata-containers/kata-containers/blob/main/docs/design/architecture/guest-assets.md), [Building Custom Kernels for Kata Containers](https://vadosware.io/post/building-custom-kernels-for-kata-containers/)

### Security config options used by Kata

Key hardening parameters in Kata kernel configs and command line:

- `CONFIG_LEGACY_VSYSCALL_NONE=y` — eliminates legacy vsyscall interface
- `CONFIG_SPECULATION_MITIGATIONS=y`, `CONFIG_RETPOLINE=y` — Spectre mitigations
- `CONFIG_RANDOMIZE_BASE=y` — KASLR
- Boot params: `apparmor=1 security=apparmor page_poison=1 slub_debug=P vsyscall=none debugfs=off lockdown=confidentiality`

Sources: [Securing Containers at Scale: Deep Dive into Kata & Firecracker](https://evan.sh/blog/securing-containers), [Building Custom Kernels for Kata Containers](https://vadosware.io/post/building-custom-kernels-for-kata-containers/)

---

## 3. Minimal Kernel Builds: What to Strip

### Firecracker's reference config analysis

The `microvm-kernel-ci-x86_64-6.1.config` file in the Firecracker repository represents the authoritative minimal-but-functional configuration. Key findings from analysis of this config:

**Disabled (attack surface eliminated):**
- `# CONFIG_MODULES is not set` — no loadable kernel modules
- `# CONFIG_MICROCODE is not set` — no CPU microcode updates from guest
- `# CONFIG_IMA is not set` — integrity measurement architecture not needed
- `# CONFIG_KEXEC_SIG is not set` — no kernel-exec from within guest

**Enabled for functionality and security:**
- `CONFIG_SECCOMP=y`, `CONFIG_SECCOMP_FILTER=y` — syscall filtering (used by containerd/runc inside guest)
- `CONFIG_NAMESPACES=y` with all namespace types — needed to run containers inside the VM
- `CONFIG_CGROUPS=y` — resource limits
- `CONFIG_STRICT_KERNEL_RWX=y` — read-only kernel code
- `CONFIG_RANDOMIZE_BASE=y`, `CONFIG_RANDOMIZE_MEMORY=y` — KASLR/ASLR
- `CONFIG_STACKPROTECTOR_STRONG=y` — stack canaries
- `CONFIG_VMAP_STACK=y` — guard pages for kernel stacks
- `CONFIG_PAGE_TABLE_ISOLATION=y` — Meltdown mitigation
- `CONFIG_RETPOLINE=y`, `CONFIG_RETHUNK=y`, `CONFIG_CPU_SRSO=y`, `CONFIG_MITIGATION_RFDS=y`, `CONFIG_MITIGATION_SPECTRE_BHI=y` — Spectre class mitigations
- `CONFIG_AUDIT=y`, `CONFIG_AUDITSYSCALL=y` — auditd support
- `CONFIG_BPF=y`, `CONFIG_BPF_SYSCALL=y` — eBPF (needed for modern container runtimes)

Sources: [microvm-kernel-ci-x86_64-6.1.config](https://github.com/firecracker-microvm/firecracker/blob/main/resources/guest_configs/microvm-kernel-ci-x86_64-6.1.config)

### Key categories to strip for minimalism

The following are commonly disabled in microVM kernels with no loss of container-agent functionality:

| Category | Config knob | Reason to disable |
|---|---|---|
| Loadable modules | `CONFIG_MODULES=n` | Prevents post-boot kernel extension |
| USB/HID/legacy input | `CONFIG_USB=n`, `i8042.noaux` | No physical hardware |
| Sound | `CONFIG_SOUND=n` | Not needed |
| CPU microcode | `CONFIG_MICROCODE=n` | Host manages microcode |
| Bluetooth | `CONFIG_BT=n` | Not needed |
| Wireless | `CONFIG_WLAN=n` | VirtIO networking only |
| ACPI (optional) | `CONFIG_ACPI=n` | Firecracker has a no-ACPI build |
| kexec | `CONFIG_KEXEC=n` | No need to load another kernel |
| Legacy vsyscall | `CONFIG_LEGACY_VSYSCALL_NONE=y` | Removes exploitable legacy path |
| Debugfs | boot param `debugfs=off` | Removes debug interface |

### Automated hardening verification

The `kernel-hardening-checker` tool (formerly `kconfig-hardened-check`) evaluates compile-time Kconfig options, boot-time command line parameters, and runtime sysctl settings against recommendations from KSPP, grsecurity, CIS benchmarks, CLIP OS, and GrapheneOS. It supports x86_64, ARM64, ARM, x86_32, and RISC-V.

Sources: [kernel-hardening-checker on GitHub](https://github.com/a13xp0p0v/kernel-hardening-checker)

---

## 4. Kernel Attack Surface: microVMs vs. Standard Containers

### The shared-kernel problem

In standard containers, every container on a host issues syscalls directly to the same Linux kernel. The kernel exposes over 450 system calls. Docker's default seccomp profile blocks approximately 44, leaving 300+ available. The Linux kernel averages 40–60 CVEs per year (accelerating to over 3,500 in 2024 as the kernel team became a CVE Numbering Authority). A single kernel privilege-escalation exploit — CVE-2022-0847 (Dirty Pipe), CVE-2022-0185, CVE-2024-1086 — compromises all containers on the host simultaneously.

### What the microVM boundary achieves

A process inside a Firecracker microVM exploiting a Linux kernel vulnerability exploits only the **guest** kernel, confined to that VM's virtual hardware. The host kernel is not reachable through the guest's syscall interface; the guest and host are separated by the hardware virtualization boundary (Intel VT-x / AMD-V) enforced in CPU silicon.

This means:
- A guest kernel CVE cannot cross to the host or to sibling VMs
- The blast radius of a guest kernel escape is bounded to that single microVM instance
- Kernel exploits must additionally defeat the VMM layer to reach the host

### The VMM as a second boundary (Firecracker's jailer)

Firecracker ships a `jailer` process that confines the VMM itself:
- chroot jail with minimal filesystem view
- Dedicated cgroups
- Seccomp-BPF filter allowing only **24 host syscalls** (vs. 450+ available to container processes)

Even a successful exploit of Firecracker's Rust VMM code lands in an environment with no access to the host filesystem, no network beyond the configured TAP device, and restricted to 24 system calls. An attacker escaping hardware virtualization (requiring a CPU hardware bug or KVM kernel vulnerability) would still face this second barrier.

### Quantified attack surface comparison

| Isolation model | Host kernel syscalls exposed | Trusted computing base | CVE propagation |
|---|---|---|---|
| Standard container | 300+ (post-seccomp) | 40M+ lines of kernel C | Cross-container on same host |
| gVisor | Reduced via user-space kernel; some host paths remain | ~1M lines Go | Partial containment |
| Firecracker microVM | 24 (via jailer seccomp) | ~50K lines Rust VMM + KVM | Bounded to that VM instance |
| Kata Containers + Firecracker | Same as Firecracker | Same as Firecracker | Bounded to that VM instance |

Sources: [Firecracker seccomp.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/seccomp.md), [Docker vs. Firecracker security comparison](https://stealthcloud.ai/comparisons/docker-vs-firecracker/), [MicroVM Isolation for CDEs](https://infragap.com/microvm-isolation/), [Northflank: Kata vs Firecracker vs gVisor](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)

---

## 5. Image Management: Shared Base vs. Per-Invocation

### Shared base image (recommended)

**Pattern:** A single versioned kernel image (e.g., `vmlinux-6.1.128`) is the runtime-level kernel for all microVM invocations within a given deployment generation. Per-invocation variation lives in the rootfs overlay, not the kernel.

**Advantages:**
- Centralized patching: updating the kernel image once affects the entire fleet immediately on next instantiation
- Snapshot/restore efficiency: Firecracker snapshots embed the booted kernel state; all instances can share a single base snapshot, with copy-on-write overlays per task
- Reproducibility: one kernel artifact to audit, scan, and sign
- Storage efficiency: kernel image cached/mapped at host level, not duplicated per VM

**Firecracker snapshot model:** A pre-warmed "golden" microVM is booted once, its full state (including loaded kernel, initialized userspace, running guest agent) is snapshotted to disk, and each invocation restores from that snapshot via copy-on-write in approximately 5–28ms. The kernel binary is embedded in the snapshot state and shared read-only.

Sources: [Firecracker snapshot-support.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md), [How I built sandboxes that boot in 28ms](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k), [MicroVM Isolation for CDEs](https://infragap.com/microvm-isolation/)

### Per-invocation bespoke kernel

**Pattern:** A unique kernel image is built or selected per agent task invocation.

**Disadvantages:**
- Build latency incompatible with sub-second task start times
- No shared snapshot state possible; every invocation requires a cold boot
- Patching complexity: old invocations in flight may run unpatched kernels
- Marginal security benefit: the threat model for an adversarial agent does not change meaningfully based on which specific 6.1.x point release is running

**When it might make sense:** long-running persistent environments (hours+) where each tenant genuinely requires a different kernel feature set. This is rare for ephemeral agent sandboxes.

### Immutable image approach with version tagging

Treat the kernel image like a container image:
- Store in an OCI registry or content-addressed store by SHA256 digest
- Tag as `vmlinux-6.1.128-r0`, `vmlinux-6.1.128-r1` (rebuild counter)
- Never overwrite a tag; promote a new tag when a new build replaces it
- Deployments pin to a specific digest, not a floating tag

This pattern (popularized by Chainguard's Wolfi-based images) ensures every rebuild pulls the same bytes when needed, and rolling back to a previous kernel requires only pointing to the old digest.

Sources: [Achieving a 0-CVE OS for VMs](https://tuananh.net/2026/01/21/achieving-a-0-cve-os-for-vms-the-end-of-traditional-patching/), [No More Dockerfiles? Reproducible Secure Container Builds](https://debugg.ai/resources/no-more-dockerfiles-reproducible-secure-container-builds-nix-buildpacks-apko-2025)

---

## 6. Update Cadence and CVE Patching

### The kernel CVE landscape

After the Linux kernel team became a CVE Numbering Authority in 2024, disclosure rates accelerated dramatically — 2024 saw over 3,500 kernel CVEs, roughly a tenfold increase. The majority are low-severity attribution artifacts from the kernel team tracking every reported issue, but several critical privilege-escalation vulnerabilities appear each year. For a multi-tenant agent sandbox where guests may be adversarial, any privilege escalation in the guest kernel is a potential step in a broader attack chain.

The key risks in a microVM context are:
- **Guest kernel exploits** that allow full guest-kernel compromise (attacker can then attempt VMM escape)
- **vsock / virtio driver vulnerabilities** that exploit the guest/host interface
- **KVM vulnerabilities** in the host kernel (these are the most critical — they defeat the VMM boundary)

### Recommended update SLA

| Severity | CVSS range | Target patch SLA |
|---|---|---|
| Critical | 9.0–10.0 | 24–72 hours |
| High | 7.0–8.9 | 7 days |
| Medium | 4.0–6.9 | 30 days |
| Low | < 4.0 | Next scheduled rebuild |

### Automated rebuild pipeline

A practical pipeline:

1. **Monitor**: Subscribe to `linux-kernel-announce`, Amazon Linux ALAS, or use a tool like `digestbot` to detect upstream kernel point releases
2. **Build**: Trigger a CI job that rebuilds the kernel image from the pinned source commit + Kconfig (or bumps the source commit to the new point release)
3. **Scan**: Run `grype`, `trivy`, or `MergeBase` against the resulting kernel vmlinux and rootfs to verify CVE count
4. **Verify**: Run `kernel-hardening-checker` against the new config to verify no hardening regression
5. **Test**: Run Firecracker's own CI test suite against the new kernel
6. **Promote**: Update the image digest reference in deployment configuration; deploy to canary, then fleet

The immutable image model makes this safe: old instances continue running the old kernel until they are recycled; new instantiations get the patched kernel immediately.

Sources: [Linux Kernel Vulnerabilities Exploited in 2025: CISA KEV Insights](https://linuxsecurity.com/news/security-vulnerabilities/7-linux-kernel-vulnerabilities-exploited-in-2025), [Scanning a Firecracker microVM with MergeBase](https://mergebase.com/blog/scanning-a-firecracker-microvm/), [Achieving a 0-CVE OS for VMs](https://tuananh.net/2026/01/21/achieving-a-0-cve-os-for-vms-the-end-of-traditional-patching/)

---

## 7. AWS Lambda as Reference Implementation

AWS Lambda runs millions of Firecracker microVMs per day. The publicly disclosed aspects of their kernel strategy:

- **Amazon Linux kernel fork**: AWS maintains microVM-specific kernels in the Amazon Linux kernel repository, tagged as `microvm-kernel-6.1.128-3.201.amzn2023`. These may include backported patches not yet in upstream LTS releases.
- **Distributed via S3**: Pre-built kernel binaries are distributed from `spec.ccfc.min` S3 buckets, versioned by point release. Operators running their own Firecracker deployments commonly consume these rather than building kernels themselves.
- **Guest kernel treated as potentially untrusted**: The security architecture assumes a compromised guest kernel and relies on hardware virtualization + Firecracker's Rust VMM + the jailer as the actual trust boundary. The guest kernel being patched is defense-in-depth, not the primary security guarantee.
- **Snapshot-based provisioning**: Lambda uses VM snapshots extensively to achieve millisecond-range cold starts, meaning the kernel is embedded in a pre-warmed snapshot and shared read-only across invocations.
- **Short-lived invocations**: Lambda terminates VMs after fixed periods, naturally clearing any accumulated state and ensuring regular kernel refresh cycles.

The Aurora DSQL team (also running on Firecracker) uses a similar pattern: VMs are terminated after fixed periods rather than long-running, avoiding complex state accumulation and ensuring the latest kernel snapshot is used on every new instance.

Sources: [Firecracker microVMs: the power behind AWS Lambda](https://www.anthony-balitrand.fr/2025/08/12/firecracker-microvms-the-power-behind-aws-lambda/), [Seven Years of Firecracker](https://brooker.co.za/blog/2025/09/18/firecracker.html), [Firecracker NSDI 2020 paper](https://www.usenix.org/system/files/nsdi20-paper-agache.pdf)

---

## 8. Reproducible Builds for microVM Kernel Images

### Why reproducibility matters

A reproducible build means that given the same source inputs (kernel source commit, Kconfig file, toolchain version), the binary output is bit-for-bit identical. This enables:
- Verification that a deployed kernel binary matches its declared source
- Supply chain auditing (no build-time injection)
- Rollback by simply referencing a previously-built digest
- Diffing two kernel binaries to understand exactly what changed between patch levels

### Approaches

**1. Nix / microvm.nix**

`microvm.nix` is a Nix Flake project that builds entire NixOS-based microVMs (kernel + rootfs) as reproducible Nix derivations. Supported hypervisors include Firecracker, Cloud Hypervisor, QEMU, crosvm, kvmtool, and others. The kernel and filesystem are expressed declaratively; the same flake lock file produces the same binary outputs on any Nix system.

Filesystem options: squashfs (smaller) or erofs (faster), both read-only root with optional writable overlay.

Sources: [microvm.nix on GitHub](https://github.com/microvm-nix/microvm.nix), [microvm.nix intro](https://microvm-nix.github.io/microvm.nix/)

**2. Firecracker's devtool**

Firecracker's own `./tools/devtool build_ci_artifacts kernels` produces the exact kernel binaries used in CI from a pinned source. Running this from a container gives a reproducible environment. The resulting `vmlinux` and its `.config` are stored together, enabling auditability.

**3. Kata's build-kernel.sh**

Kata's script produces a deterministic output given a fixed `versions.yaml` (kernel version) and `kata_config_version`. CI caches pre-built kernels by the combined version identifier; a cache miss triggers a fresh build from source.

**4. Content-addressed storage**

Regardless of build tool, the resulting kernel binary should be stored and referenced by its SHA256 digest. Deployment systems should pin to the digest, not a symbolic version label. This is equivalent to how container image digests work in OCI registries.

Sources: [Firecracker rootfs-and-kernel-setup.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md), [Kata kernel README](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kernel/README.md), [microvm.nix on GitHub](https://github.com/microvm-nix/microvm.nix)

---

## 9. Functionality vs. Minimalism Tradeoff

The central tension is that a fully capable agent workload (running containers, using network namespaces, executing arbitrary code) requires a non-trivial kernel feature set, while security argues for stripping everything not strictly needed.

### What must stay in for a container-running agent

- Namespaces (UTS, IPC, USER, PID, NET, MNT) — required for container isolation inside the VM
- cgroups v2 — required for resource limits
- OverlayFS — required for container image layering
- virtio-net, virtio-blk — required for I/O
- eBPF + seccomp — required for modern container runtimes (runc, containerd)
- netfilter/conntrack — required for container networking (iptables/nftables)
- FUSE (optional) — required for some filesystems; can be omitted if not needed

### What can be removed

Everything not in the above list. The Firecracker CI config is a good baseline. Notable high-value removals:
- All loadable modules (`CONFIG_MODULES=n`) — eliminates runtime kernel extension
- USB, HID, legacy input drivers — no physical hardware
- Bluetooth, WiFi — virtio networking only
- Sound — not relevant
- CPU microcode update machinery — host manages microcode
- kexec — no need to load a second kernel
- Legacy vsyscall interface — old exploit path, no modern software needs it
- Debugfs exposed to guest — remove from boot params with `debugfs=off`

### The eBPF question

eBPF (`CONFIG_BPF_SYSCALL=y`) is needed by containerd, runc, and modern networking tools. It is also a well-known kernel attack surface. The tradeoff: disable eBPF and accept compatibility limitations with standard container runtimes, or keep it enabled and accept the exposure. For a controlled agent sandbox where the guest container runtime is chosen by the operator (not the agent), a restricted eBPF configuration (no unprivileged eBPF: `kernel.unprivileged_bpf_disabled=1` via sysctl) is a reasonable middle ground.

Sources: [Firecracker microvm-kernel-ci-x86_64-6.1.config](https://github.com/firecracker-microvm/firecracker/blob/main/resources/guest_configs/microvm-kernel-ci-x86_64-6.1.config), [Docker vs. Firecracker](https://stealthcloud.ai/comparisons/docker-vs-firecracker/), [Securing Containers at Scale](https://evan.sh/blog/securing-containers)

---

## Sources

- [Firecracker project homepage](https://firecracker-microvm.github.io/)
- [Firecracker on GitHub](https://github.com/firecracker-microvm/firecracker)
- [Firecracker kernel-policy.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/kernel-policy.md)
- [Firecracker rootfs-and-kernel-setup.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md)
- [Firecracker seccomp.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/seccomp.md)
- [Firecracker microvm-kernel-ci-x86_64-6.1.config](https://github.com/firecracker-microvm/firecracker/blob/main/resources/guest_configs/microvm-kernel-ci-x86_64-6.1.config)
- [Firecracker snapshot-support.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md)
- [Firecracker getting-started.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)
- [Kata Containers kernel README](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kernel/README.md)
- [Kata Containers guest-assets design doc](https://github.com/kata-containers/kata-containers/blob/main/docs/design/architecture/guest-assets.md)
- [Kata Containers Developer Guide](https://github.com/kata-containers/kata-containers/blob/main/docs/Developer-Guide.md)
- [Building Custom Kernels for Kata Containers — vadosware](https://vadosware.io/post/building-custom-kernels-for-kata-containers/)
- [microvm.nix on GitHub](https://github.com/microvm-nix/microvm.nix)
- [microvm.nix documentation](https://microvm-nix.github.io/microvm.nix/)
- [kernel-hardening-checker on GitHub](https://github.com/a13xp0p0v/kernel-hardening-checker)
- [MicroVM Isolation for CDEs — InfraGap](https://infragap.com/microvm-isolation/)
- [Securing Containers at Scale: Deep Dive into Kata & Firecracker — evan.sh](https://evan.sh/blog/securing-containers)
- [Northflank: Kata Containers vs Firecracker vs gVisor](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)
- [Docker vs. Firecracker: Container Isolation and Security Compared](https://stealthcloud.ai/comparisons/docker-vs-firecracker/)
- [Choosing a Workspace for AI Agents — DEV Community](https://dev.to/agentsphere/choosing-a-workspace-for-ai-agents-the-ultimate-showdown-between-gvisor-kata-and-firecracker-b10)
- [Firecracker microVMs: the power behind AWS Lambda](https://www.anthony-balitrand.fr/2025/08/12/firecracker-microvms-the-power-behind-aws-lambda/)
- [Seven Years of Firecracker — Marc Brooker's blog](https://brooker.co.za/blog/2025/09/18/firecracker.html)
- [Announcing Firecracker Open Source — AWS Open Source Blog](https://aws.amazon.com/blogs/opensource/firecracker-open-source-secure-fast-microvm-serverless/)
- [Enhancing Kubernetes workload isolation using Kata Containers — AWS Containers Blog](https://aws.amazon.com/blogs/containers/enhancing-kubernetes-workload-isolation-and-security-using-kata-containers/)
- [Scanning a Firecracker microVM with MergeBase](https://mergebase.com/blog/scanning-a-firecracker-microvm/)
- [Achieving a 0-CVE OS for VMs — Tuan-Anh Tran](https://tuananh.net/2026/01/21/achieving-a-0-cve-os-for-vms-the-end-of-traditional-patching/)
- [Attacks are Forwarded: Breaking the Isolation of MicroVM-based Containers — USENIX Security 2023](https://www.usenix.org/system/files/sec23fall-prepub-591-xiao-jietao.pdf)
- [Linux Kernel Vulnerabilities Exploited in 2025 — LinuxSecurity.com](https://linuxsecurity.com/news/security-vulnerabilities/7-linux-kernel-vulnerabilities-exploited-in-2025)
- [How I built sandboxes that boot in 28ms using Firecracker snapshots — DEV Community](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k)
- [No More Dockerfiles? Reproducible Secure Container Builds — debugg.ai](https://debugg.ai/resources/no-more-dockerfiles-reproducible-secure-container-builds-nix-buildpacks-apko-2025)
- [Supercharging AI isolation: microVMs with RamaLama & libkrun — Red Hat Developer](https://developers.redhat.com/articles/2025/07/02/supercharging-ai-isolation-microvms-ramalama-libkrun)
- [Production Host Setup — Firecracker book](https://jonathanwoollett-light.github.io/firecracker/book/book/prod-host-setup.html)
- [Exploring Firecracker MicroVMs for Multi-Tenant Dagger CI/CD Pipelines](https://www.felipecruz.es/exploring-firecracker-microvms-for-multi-tenant-dagger-ci-cd-pipelines/)
