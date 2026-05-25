# Q15: How Should the Test Runner Be Sandboxed?

**Question**: Test code runs with full container permissions. An adversarial agent could write a test that exfiltrates data or makes unauthorized network connections. How should the test runner be sandboxed?

**Options**:
- **(a)** Accept test execution within the existing container boundary
- **(b)** Run the test runner in a nested sandbox with tighter constraints
- **(c)** Disallow test execution entirely (agent ships code, human runs tests)

---

## Summary and Recommendation

**Recommended approach: Option (b) — nested sandbox with tighter constraints, but scoped pragmatically.**

The key insight is that the threat model for test code is meaningfully different from the threat model for general agent activity. The agent writes tests; tests are then executed by a subprocess that the test framework spawns. This creates a distinct code-execution vector that warrants its own constraint envelope.

However, the practical implementation should be proportionate:

1. **Network egress is the highest-value control**. If the outer container already applies deny-by-default egress (no arbitrary outbound TCP/UDP/DNS), test code can exfiltrate data only through allowed channels. This eliminates the primary exfiltration risk.

2. **A lightweight nested sandbox using Linux namespaces + seccomp is feasible and cheap**. Using `bwrap` (bubblewrap) or Landlock + seccomp BPF, the test runner subprocess can be given a read-only filesystem view (except a scratch tmpfs), its own network namespace with no external connectivity, and a tighter syscall allowlist. This requires no nested virtualization and imposes minimal overhead.

3. **Full nested containers (Docker-in-Docker within Kata/Firecracker) are not recommended**. They are architecturally complex, require privileged mode or nested KVM support that many cloud VMs do not provide, and Bazel's own sandboxing documentation notes that linux-sandbox does not work in nested scenarios. The security gain does not justify the operational complexity.

4. **Disallowing test execution (option c) is a significant quality penalty** and should be a last resort. AI coding agents rely heavily on the test-feedback loop to validate patches; benchmarks like SWE-bench require agents to iterate on test results. Removing this degrades agent output substantially.

**Practical implementation target**: Run the test subprocess inside a `bwrap` or Landlock + seccomp envelope that adds:
- A separate network namespace (`--unshare-net`) with no external connectivity
- Read-only root bind mount except for a limited writable tmpfs scratch area
- A restrictive seccomp profile that blocks `ptrace`, raw socket creation, `mount`, `unshare`, `clone` with namespace flags, and module loading

This is the approach Anthropic's own `sandbox-runtime` takes for agent code execution.

---

## Detailed Findings

### 1. What a Nested Sandbox for Test Execution Would Look Like

There are three practical techniques for sandboxing a test subprocess within an existing container:

#### 1a. Bubblewrap (bwrap) sub-sandbox

[Bubblewrap](https://github.com/containers/bubblewrap) is a low-level unprivileged sandboxing tool used by Flatpak and—critically—Anthropic's own `sandbox-runtime`. It uses Linux namespaces to construct isolated execution environments without requiring root privileges on the host.

Key bubblewrap flags for a test runner:
- `--unshare-net`: Creates an isolated network namespace with only a loopback device. All external network access is severed.
- `--unshare-pid`: Prevents the test process from seeing other host processes.
- `--ro-bind / /`: Mounts the entire filesystem read-only.
- `--bind /tmp/test-scratch /tmp`: Provides a writable tmpfs scratch area.
- Seccomp filter via the `apply-seccomp` binary: Applies a BPF filter before user command execution, blocking specific syscalls (e.g., Unix domain socket creation).

[Anthropic's sandbox-runtime](https://deepwiki.com/anthropic-experimental/sandbox-runtime/6.3.1-bubblewrap-integration) implements exactly this pattern. The `wrapCommandWithSandboxLinux` function translates high-level sandbox configuration into bubblewrap arguments, with `needsNetworkRestriction` toggling network isolation and `enableWeakerNestedSandbox` disabling `--proc` when already inside an unprivileged Docker container.

#### 1b. Landlock LSM + seccomp BPF

[Landlock](https://landlock.io/) is a Linux Security Module available since kernel 5.13 that allows any process—including unprivileged ones—to restrict its own filesystem access. It is stackable on top of existing LSMs and inherits automatically to all child processes via `fork()` and `exec()`.

OpenAI's Codex CLI uses Landlock in combination with seccomp on Linux for its sandboxing layer. A test runner wrapped with Landlock can be given a filesystem ruleset that:
- Permits reads only within the project checkout directory
- Permits writes only to a designated output directory
- Denies all other filesystem access

Combined with seccomp BPF (blocking raw socket creation, `ptrace`, namespace creation syscalls), this provides strong constraint without requiring a separate process tree or container runtime.

#### 1c. Seccomp BPF subprocess profile

A test runner child process automatically inherits the parent's seccomp filter. However, it is also possible to apply *additional, tighter* filters to a child process using `prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ...)`. According to the [Linux kernel documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html):

> "If prctl(2) is allowed by the attached filter, additional filters may be layered on which will increase evaluation time, but allow for further decreasing the attack surface during execution of a process. Furthermore, if multiple filters exist, the return value for the evaluation of a given system call will always use the highest precedent value."

This means a parent process can apply a tighter filter just before execing the test runner binary, and that filter will stack on the existing container-level filter and cannot be relaxed. The prerequisite `PR_SET_NO_NEW_PRIVS` must have already been set.

This approach can selectively block syscalls that are needed for the agent itself (e.g., `clone`, `unshare`, `socket`) but are not needed by a test subprocess.

---

### 2. Nested Containers/Sandboxes Inside Kata/Firecracker MicroVMs

Running a nested container runtime (a Docker-in-Docker equivalent) inside a Kata or Firecracker microVM is technically possible but operationally difficult:

**Kata Containers limitations**:
- Kata does not support `--privileged` mode by design—this is the core of its isolation model. Docker-in-Docker typically requires privileged mode for the inner Docker daemon.
- When Kata uses QEMU, nested virtualization must be enabled on the host. Many cloud VMs (especially on AWS with Firecracker) do not support nested KVM by default.
- Kata works with containerd (shimV2), not Docker directly, as Docker deprecated the devicemapper storage driver that Kata depends on.

**Firecracker limitations**:
- Firecracker does not enable filesystem-level sharing between the microVM and the host; it requires a snapshotter (devmapper) that creates snapshots as filesystem images. Running a second container runtime inside this environment requires additional block device management.
- [Firecracker-in-Docker](https://github.com/fadams/firecracker-in-docker) is a proof-of-concept project that requires `--device=/dev/kvm` access, which in turn requires the host VM to support nested virtualization.

**Bazel's experience**: Bazel's `linux-sandbox` strategy, which uses Linux namespaces (User, Mount, PID, Network, IPC), explicitly notes in its documentation that "both implementations do not work in a 'nested' scenario" and will automatically fall back to `processwrapper-sandbox` when run inside Docker or nested sandbox contexts.

**Practical verdict**: Do not attempt Docker-in-Docker or nested Kata/Firecracker inside the agent microVM. Use namespace-based sandboxing (bubblewrap, Landlock, seccomp) as the lightweight nested layer. This is feasible without nested KVM and does not require the inner layer to run a full container runtime.

---

### 3. The Actual Risk: What Can Test Code Do When Egress Is Already Filtered?

If the outer container already applies deny-by-default network egress, what residual damage can adversarial test code cause?

**Primary exfiltration paths that egress filtering blocks**:
- Direct TCP connections to attacker-controlled servers
- HTTP/HTTPS POSTs to external endpoints
- Raw UDP exfiltration

**Residual risks that egress filtering does NOT block**:

1. **DNS-based exfiltration**: DNS is often whitelisted through firewalls. Data can be encoded in DNS query hostnames (e.g., `secret-data.attacker.com`). Mitigations: restrict DNS to a single trusted resolver; monitor/log DNS query patterns.

2. **Allowed-channel abuse**: If the agent's network policy permits access to, say, a package registry or artifact store, test code running as the agent has the same permission to POST data to that allowed endpoint.

3. **Filesystem modification of CI/CD artifacts**: Test code can modify `Makefile`, `package.json` scripts, `.github/workflows/`, Git hooks in `.git/hooks/`, and other files that execute later outside the sandbox when a human or CI pipeline runs them. Network filtering provides no protection against this.

4. **Environment variable and secret leakage through allowed channels**: If test code can read environment variables (API keys, tokens passed into the container), it can exfiltrate them via any allowed outbound channel. The NVIDIA AI Red Team calls environment variable leakage "the biggest security blind spot in agent sandboxing."

5. **Kernel vulnerability exploitation**: Containers share the host kernel. Test code that executes a kernel exploit can escape the container entirely, bypassing all network filtering. This is why Kata/Firecracker microVMs are used as the outer boundary—they provide a separate kernel.

6. **Process/memory inspection**: Without seccomp restrictions, test code can use `ptrace` to inspect other processes in the container, potentially extracting credentials from a running agent process or database connection.

**Summary**: With deny-by-default egress and a microVM outer boundary, the primary residual risks are: (a) DNS exfiltration, (b) filesystem modification of post-sandbox-execution artifacts, and (c) environment variable abuse through allowed channels. A nested namespace sandbox adds meaningful protection against (a) by severing all network (including DNS) from the test subprocess, and against (b) by making the filesystem read-only except for a scratch area.

---

### 4. Test Isolation in CI/CD Systems

#### Bazel

[Bazel's sandboxing](https://bazel.build/docs/sandboxing) is the most mature production example of build/test subprocess isolation:

- **linux-sandbox**: Uses Linux namespaces (User, Mount, PID, Network, IPC) for each action. Makes the entire filesystem read-only except the sandbox working directory. Uses PID namespaces to kill all spawned daemons at the end. Can block network access per-action.
- **processwrapper-sandbox**: A POSIX-compatible fallback that builds a directory of symlinks to inputs and runs the action within it. Weaker isolation but works everywhere.
- **darwin-sandbox**: Uses macOS `sandbox-exec` (Seatbelt) for similar constraints.

Critically, Bazel sandboxes **each test action individually**—not just the test runner, but each test invocation. This prevents test-to-test contamination as well as host contamination.

#### Pants

[Pants](https://www.pantsbuild.org/stable/docs/introduction/how-does-pants-work) uses a content-addressable cache and hermetic execution model similar to Bazel:

- Every process is sandboxed with only its declared inputs present.
- The engine caches processes based on input hashes and sandboxes execution to minimize side-effects.
- This ensures that cache keys are always accurate and builds/tests are always correct.

#### GitHub Actions

GitHub Actions does not sandbox test execution within a job—the entire job runner (a VM or container) is the isolation boundary. Each job runs in a fresh VM or container, providing inter-job isolation, but tests within a job share the same environment. GitHub Actions jobs are themselves isolated from each other and from the host using VMs (hosted runners) or containers (container jobs).

The supply chain attacks on GitHub Actions (see section 6) demonstrate that the *workflow level* is the attack surface, not the individual test level.

---

### 5. Language-Specific Test Sandboxing

#### pytest (Python)

Pytest has no built-in sandbox mode. The ecosystem has plugins:
- **[pytest-isolate](https://pypi.org/project/pytest-isolate/)**: Runs each test in an isolated subprocess using `fork()`, enabling per-test process isolation and resource limiting (memory/CPU). Does not provide network or filesystem isolation.
- **pytest-test-categories**: Plans for network isolation via a `NetworkBlockerPort` interface, but pytest hook integration was still in development as of the available documentation.
- Network isolation can be achieved by wrapping pytest invocation in a network-isolated subprocess (bubblewrap/Landlock), not through pytest itself.

#### Jest (JavaScript)

Jest runs tests in isolated V8 contexts using Node.js worker threads or child processes. Each test file gets its own module registry and V8 context, providing test-to-test module isolation. However, Jest does not provide OS-level network or filesystem isolation—all Jest workers share the same process's network stack and filesystem access.

#### Go test

`go test` provides no built-in sandbox mode. Tests run as a compiled binary with the same permissions as the invoking process. Go's standard library `testing` package provides no isolation primitives. Network and filesystem isolation must be applied at the process level (wrapping `go test` invocation).

**Common thread**: None of these frameworks provide OS-level network or filesystem isolation natively. The isolation must be applied *around* the test runner invocation, not within it. This supports the approach of wrapping the test runner in a bubblewrap/Landlock envelope.

---

### 6. Real Examples of Tests as a Code Execution Vector in CI/CD Attacks

#### XZ Utils Backdoor (CVE-2024-3094)

The most sophisticated known example of test files used as a code execution vector in CI/CD. The attacker (operating as "Jia Tan" over two years of trust-building) hid a backdoor in binary test fixture files (`bad-3-corrupt_lzma2.xz`, `good-large_compressed.lzma`). The build process—specifically the `build-to-host.m4` autoconf macro—decoded these "test" files into shell scripts during the build, which then extracted and injected a malicious shared object into the liblzma compilation process. The backdoor enabled remote code execution via OpenSSH on affected Linux distributions.

Key lesson: Test fixtures are not just code—they are data files that build automation processes. Sandboxing test execution does not protect against malicious build-time decoding of test fixtures.

#### tj-actions/changed-files (March 2025, CVE-2025-30066)

Attackers compromised the `tj-actions/changed-files` GitHub Action, retroactively modifying version tags to reference a malicious commit. The payload was a Python script that scanned GitHub Actions runner memory for secrets and printed them to workflow logs—using GitHub's own logging infrastructure as the exfiltration channel. This affected over 23,000 repositories.

Key lesson: The exfiltration channel was the CI/CD platform's own logging, not an outbound network connection. Network egress filtering would not have prevented this.

#### Trivy Supply Chain Attack (March 2025)

The attacker force-pushed malicious code to 76 of 77 previously released versions of `trivy-action`, a GitHub Actions workflow used to run security scans. Any CI pipeline referencing those versions would execute the malicious code instead of the legitimate scanner.

#### Shai-Hulud npm Campaign (November 2025)

A widespread npm supply chain attack compromising tens of thousands of GitHub repositories. Attackers leveraged stolen GitHub tokens to hijack GitHub Actions and self-hosted runners, deploying backdoored "formatter" workflows that exfiltrated GitHub's entire secret store via `toJSON(secrets)` and enabled remote command execution.

**Pattern**: Most real CI/CD attacks exploit the workflow/action level, not individual test files. However, the XZ Utils attack demonstrates that test fixtures embedded in source repositories can be weaponized at build time.

---

### 7. Impact of Disallowing Test Execution on Agent Output Quality

The test-feedback loop is central to how modern AI coding agents achieve high resolution rates on software engineering tasks.

[SWE-bench](https://www.swebench.com/) is the primary benchmark for coding agents. Its evaluation requires agents to propose patches for real GitHub issues, with success measured by whether the patch makes failing tests pass without breaking existing tests. The benchmark provides agents with a Docker environment and access to the repository, and top agents (including Verdent at 93.9% on SWE-bench Verified) explicitly treat test execution as a first-class stage: "run type checks, perform static analysis, and execute tests as needed after meaningful edits."

**Performance data**:
- Most top agents on SWE-bench Verified score over 70%; the same models drop to ~23% on SWE-bench Pro (harder, more realistic tasks). The gap is partly attributable to agents' ability to iterate on test feedback.
- Research on iterative tasks ([SlopCodeBench](https://huggingface.co/papers/2603.24755)) shows that quality erosion rises in 80% of agent trajectories when agents cannot close feedback loops.
- Agents without test execution feedback generate code from "static file analysis without runtime observability," producing "brittle selectors, implicit timing assumptions, and schema drift that compound into flaky, unreliable test suites."

**Conclusion**: Disallowing test execution is not a viable option for a general-purpose AI coding agent. The quality degradation is severe and measurable.

---

### 8. Seccomp Subprocess Profiles: Applying Tighter Filters to Test Runner Processes

This is feasible and is the mechanism underpinning multiple production sandboxing implementations.

**Kernel mechanics** ([Linux kernel seccomp documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html)):
- Filters are inherited by all child processes via `fork()`/`clone()` and `exec()`.
- Additional filters can be layered using `prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ...)`.
- Stacked filters always use the most restrictive result—a child process **cannot relax** a filter set by its parent.
- `PR_SET_NO_NEW_PRIVS` must be set before applying a filter without `CAP_SYS_ADMIN`.

**Practical approach** for a test runner:
1. The agent process runs with a base seccomp profile (applied by the container runtime—e.g., Docker's default or a custom profile).
2. Before exec-ing the test runner, the agent process calls `prctl(PR_SET_SECCOMP, ...)` with an additional filter that blocks:
   - `socket(AF_INET, ...)`, `socket(AF_INET6, ...)`, `socket(AF_UNIX, ...)` — prevents new network and Unix socket creation
   - `ptrace` — prevents process inspection
   - `clone` with `CLONE_NEWUSER`, `CLONE_NEWNET`, etc. — prevents namespace escape attempts
   - `mount`, `umount2` — prevents filesystem remounting
   - `init_module`, `finit_module` — prevents kernel module loading
3. The test runner and all its children inherit this tighter profile.

**gVisor optimization note**: gVisor itself generates optimized seccomp BPF filters as part of its runtime. Its fuzzer verifies that every branch of the optimized cBPF bytecode is exercised ([gVisor seccomp blog, 2024](https://gvisor.dev/blog/2024/02/01/seccomp/)). If gVisor is used as the outer sandbox, its seccomp implementation may already provide much of this protection, but explicit per-subprocess tightening still adds defense-in-depth.

---

## Recommendation Matrix

| Concern | Option (a): Accept existing boundary | Option (b): Nested sandbox | Option (c): Disallow tests |
|---|---|---|---|
| Network exfiltration (if outer egress filtered) | Low–medium risk | Low risk | No risk |
| Filesystem modification of CI artifacts | Medium risk | Low risk (with ro-bind) | No risk |
| Kernel exploit via test code | Protected by microVM | Protected by microVM | No risk |
| DNS exfiltration | Medium risk | Low risk (net namespace severed) | No risk |
| Agent output quality | Full | Full | Severely degraded |
| Operational complexity | Lowest | Low–medium | Low |
| Nested KVM required | No | No (namespace-based) | No |

---

## Implementation Guidance

For a container sandbox running agentic AI tasks, the recommended test runner sandboxing is:

1. **Wrap all test runner invocations** (`pytest`, `npm test`, `go test`, `cargo test`, etc.) in a bubblewrap command that adds `--unshare-net` and `--ro-bind / /` with a limited writable scratch bind mount.

2. **Apply a tighter seccomp profile** via `prctl` or by exec-ing through a wrapper binary that installs the filter before executing the test runner.

3. **Use Landlock** (kernel >= 5.13) to add a filesystem access ruleset that restricts the test subprocess to the project checkout directory and the scratch area.

4. **Do not attempt nested containers or nested microVMs**. They require either privileged mode (which breaks Kata's isolation model) or nested KVM (which is not universally available).

5. **Preserve the test-feedback loop**. Do not remove test execution capability from the agent—this severely degrades output quality on all realistic benchmarks.

6. **Log all test invocations** with syscall-level observability so anomalous patterns (unexpected DNS queries, unusual file writes) can be detected and reviewed.

---

## Sources

- [Sandboxes for Coding Agents — Penligent](https://www.penligent.ai/hackinglabs/sandboxes-for-coding-agents/)
- [Bubblewrap Integration in Anthropic sandbox-runtime — DeepWiki](https://deepwiki.com/anthropic-experimental/sandbox-runtime/6.3.1-bubblewrap-integration)
- [Bubblewrap GitHub — containers/bubblewrap](https://github.com/containers/bubblewrap)
- [Landlock: unprivileged access control — Linux Kernel Documentation](https://docs.kernel.org/userspace-api/landlock.html)
- [Landlock project site](https://landlock.io/)
- [Seccomp BPF — Linux Kernel Documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [seccomp(2) — Linux manual page](https://man7.org/linux/man-pages/man2/seccomp.2.html)
- [Optimizing seccomp usage in gVisor — gVisor Blog (2024)](https://gvisor.dev/blog/2024/02/01/seccomp/)
- [Bazel Sandboxing Documentation](https://bazel.build/docs/sandboxing)
- [How does Pants work? — Pantsbuild](https://www.pantsbuild.org/stable/docs/introduction/how-does-pants-work)
- [Hermetic Environments in Pantsbuild — Speaker Deck](https://speakerdeck.com/chrisjrn/hermetic-environments-in-pantsbuild-31d03419-8a15-4cd3-9041-b817b8924b3c)
- [Kata Containers on Kubernetes and Kata Firecracker VMM support — Medium](https://gokulchandrapr.medium.com/kata-containers-on-kubernetes-and-kata-firecracker-vmm-support-28abb3a196e7)
- [Kata Containers vs Firecracker vs gVisor — Northflank Blog](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)
- [Firecracker-in-Docker — GitHub (fadams)](https://github.com/fadams/firecracker-in-docker)
- [How to sandbox AI agents in 2026: MicroVMs, gVisor & isolation strategies — Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Best code execution sandbox for AI agents in 2026 — Northflank](https://northflank.com/blog/best-code-execution-sandbox-for-ai-agents)
- [Practical Security Guidance for Sandboxing Agentic Workflows — NVIDIA Technical Blog](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)
- [About GKE Agent Sandbox — Google Cloud Documentation](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/machine-learning/agent-sandbox)
- [Unleashing autonomous AI agents: Why Kubernetes needs a new standard — Google Open Source Blog](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html)
- [OpenAI Codex Sandboxing Architecture — Mintlify Wiki](https://mintlify.wiki/openai/codex/architecture/sandboxing)
- [OpenAI Codex Sandboxing Implementation — DeepWiki](https://deepwiki.com/openai/codex/5.6-sandboxing-implementation)
- [pytest-isolate — PyPI](https://pypi.org/project/pytest-isolate/)
- [Network Isolation Examples — pytest-test-categories](https://pytest-test-categories.readthedocs.io/en/latest/examples/network-isolation.html)
- [XZ Utils Backdoor — Wikipedia](https://en.wikipedia.org/wiki/XZ_Utils_backdoor)
- [XZ Utils Backdoor: Supply Chain Vulnerability — Logpoint/guardsix](https://logpoint.com/en/blog/emerging-threats/xz-utils-backdoor)
- [CVE-2024-3094 and XZ Upstream Supply Chain Attack — CrowdStrike](https://www.crowdstrike.com/en-us/blog/cve-2024-3094-xz-upstream-supply-chain-attack/)
- [tj-actions/changed-files CVE-2025-30066 — GitHub Advisory Database](https://github.com/advisories/ghsa-mrrh-fwg8-r2c3)
- [Maintainers' Guide: Securing CI/CD Pipelines After tj-actions and reviewdog Attacks — OpenSSF](https://openssf.org/blog/2025/06/11/maintainers-guide-securing-ci-cd-pipelines-after-the-tj-actions-and-reviewdog-supply-chain-attacks/)
- [Trivy Supply Chain Attack Targets CI/CD Secrets — Dark Reading](https://www.darkreading.com/application-security/trivy-supply-chain-attack-targets-ci-cd-secrets)
- [Shai-Hulud 2.0 Supply Chain Attack — Unit 42, Palo Alto Networks](https://unit42.paloaltonetworks.com/npm-supply-chain-attack/)
- [SWE-bench Leaderboard](https://www.swebench.com/)
- [SWE-bench, Agentic Coding, and What Changed from Claude Sonnet 4.5 to 4.6 — DEV Community](https://dev.to/blamsa0mine/swe-bench-agentic-coding-and-what-actually-changed-from-claude-sonnet-45-to-46-1gig)
- [SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks — Hugging Face Papers](https://huggingface.co/papers/2603.24755)
- [Why AI Coding Agents Fail E2E Tests — Augment Code](https://www.augmentcode.com/guides/why-ai-coding-agents-fail-e2e-tests)
- [Rootless Containers: The Next Trend in Container Security — Unit 42](https://unit42.paloaltonetworks.com/rootless-containers-the-next-trend-in-container-security/)
- [Kubernetes v1.33 Defaults to User Namespaces — Web crafting code](https://webcraftingcode.com/news/kubernetes-v1-33-defaults-to-user-namespaces-for-better-security/)
- [Seccomp security profiles for Docker — Docker Docs](https://docs.docker.com/engine/security/seccomp/)
- [Restrict a Container's Syscalls with seccomp — Kubernetes Documentation](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [2024 in Review: The Evolution of CI/CD Security — StepSecurity](https://www.stepsecurity.io/blog/2024-in-review-the-evolution-of-ci-cd-security-whats-next)
