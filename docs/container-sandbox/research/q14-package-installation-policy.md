# Q14: Should the Implement Role Be Allowed to Install New Packages?

**Research date:** 2026-04-18
**Context:** Container sandbox for agentic AI tasks — the "implement" role runs an AI agent to write code and run tests.

---

## Summary and Recommendation

**Recommended approach: Option (a) with option (b) as a fallback — pre-populate a vendor directory or lockfile before the agent starts, and if dynamic installation is genuinely required, restrict it to an approved private registry mirror.**

Option (c) — unrestricted package installation — is not acceptable for a security-focused sandbox. The threat landscape in 2025–2026 has made unrestricted `npm install` / `pip install` during agent execution a high-severity risk, for reasons that compound each other:

1. The supply chain attack surface is enormous and actively exploited at scale.
2. AI coding agents introduce a *new and unique* risk vector — "slopsquatting" — where agents hallucinate package names that attackers have pre-registered with malicious code.
3. Package managers execute arbitrary code during installation (npm pre/postinstall hooks, pip setup.py), meaning installation itself is an attack surface.
4. A sandboxed container can be fully escaped or exfiltrated through package installation even when outbound network egress is otherwise restricted, because the malicious code executes *inside* the sandbox.

The practical reality of AI coding agent workflows supports option (a): agents implementing features in an existing codebase overwhelmingly use packages already declared in the project's manifest. When a design document has been approved before implementation begins (as in the QRSPI workflow), any new dependencies should be identified at design/structure time and pre-populated before the agent runs. The agent should only need to resolve and install what is already declared.

---

## Detailed Findings

### 1. Supply Chain Attack Surface

#### Scale and Trend

The supply chain attack problem has worsened dramatically. Malicious package incidents on npm and PyPI grew from 38 reports in 2018 to 2,168 in 2024. In 2025, a single campaign published 280 malicious npm packages over one weekend. In the first three months of 2026 alone, four significant software supply chain attacks were disclosed, targeting packages including Axios (compromised by a North Korea-linked actor), LiteLLM, and Telnyx.

CISA issued an alert in September 2025 titled "Widespread Supply Chain Compromise Impacting npm Ecosystem" describing a mass compromise of 18 widely-used npm packages with a combined 2.6 billion weekly downloads. The attack used targeted phishing to compromise maintainer accounts and inject malicious code into official releases.

#### How Packages Execute During Installation

npm `preinstall` and `postinstall` scripts run automatically during `npm install`. This is not hypothetical — many legitimate packages use install scripts (node-gyp, sqlite3, etc.), and attackers abuse this mechanism. The "Shai-Hulud 2.0" campaign in 2025 shifted from post-install to pre-install execution to widen impact. A sandboxed container running `npm install` on a malicious package will execute attacker code inside the sandbox before any other guardrail can activate.

pip's `setup.py` and PEP 517 build hooks have a similar property for packages not distributed as pre-built wheels.

#### Post-Install Execution in an Agent Context

For an AI agent in a container sandbox, malicious install-time code can:
- Exfiltrate secrets already present in the container (API keys, tokens passed as environment variables)
- Create reverse shells or call back to attacker infrastructure
- Modify source files the agent will subsequently commit
- Corrupt test harnesses so the agent cannot detect the compromise

---

### 2. The Slopsquatting Threat: AI-Specific Risk

AI coding agents introduce a novel supply chain risk that does not apply to human developers to the same degree: **slopsquatting**.

Research testing 16 major code-generation AI models across 576,000 code samples found that **19.7% of all recommended package names did not exist**. Open-source models hallucinated at 21.7%; commercial models at 5.2% (GPT-4 Turbo: 3.59%). Over 205,000 unique hallucinated package names were documented.

Critically, **58% of hallucinated package names reappear consistently across multiple runs**, and 43% appeared in ten consecutive attempts with the same prompt. This consistency makes the attack practical: an adversary can identify which non-existent package names a specific model reliably recommends, then register malicious packages under those names.

If the implement agent is permitted to run `npm install` or `pip install` on packages it chooses, and the sandbox has outbound access to public registries, slopsquatting is a live threat. The agent will confidently install a package that does not exist in the project's existing dependency tree — and if an attacker has registered that name, malicious code runs.

**This makes unrestricted installation categorically more dangerous in an AI agent context than in a human developer context.**

---

### 3. Typosquatting and Dependency Confusion

#### Typosquatting

Attackers register package names that differ by one or two characters from popular packages: `metamaks` vs `metamask`, `browser-cookies3` vs `browser-cookie3`. A March 2024 campaign inundated PyPI with nearly 200 such packages in a single day. In December 2024, 86.1% of flagged suspicious package names contained active malware.

Attackers now use AI to generate typosquatted names at scale and to obfuscate payloads to evade code scanners. The arms race has shifted decisively toward attackers in the public registry environment.

#### Dependency Confusion

Dependency confusion exploits how package managers resolve packages when both a private registry and a public registry are configured. The package manager may prefer the *higher version number*, which an attacker can exploit by publishing a public package with the same name as an internal package but a higher version.

**The canonical demonstration:** In 2021, Alex Birsan showed that uploading malicious packages to PyPI and npm with the same names as packages used internally at Apple, Microsoft, and dozens of other companies — but with higher version numbers — caused those companies' build systems to silently pull and execute his code.

49% of organizations have been found vulnerable to dependency confusion. The correct mitigation is:
- For npm: always use scoped packages (`@myorg/package`) for internal code; register scope on npmjs.org
- For pip: **never** use `--extra-index-url` alongside a trusted private index; use `--index-url` *only* (pointing to a private mirror that proxies PyPI) — [PEP 708](https://peps.python.org/pep-0708/) was written specifically to address this
- For all ecosystems: use a private registry that explicitly blocks or shadows public packages, rather than supplementing a public registry

---

### 4. Vendoring and Lockfile Strategies by Ecosystem

#### npm

- **`package-lock.json`**: Records exact resolved versions and SHA-512 integrity hashes for every package and transitive dependency. `npm ci` installs exactly what the lockfile specifies and fails if lockfile is inconsistent with `package.json`. Use `npm ci --offline` to prevent any network access.
- **`npm-shrinkwrap.json`**: Committed lockfile variant designed for published packages; carries the same integrity hashes.
- **Offline mirror**: Verdaccio can be run as a Docker container, pre-seeded by running `npm install` once with `--registry` pointing to it. Subsequent installs with `--registry http://localhost:4873` resolve from cache. Offline mode is enabled automatically once packages are cached.
- **Vendoring**: `npm pack` each dependency and store tarballs; use `--prefer-offline` or point npm to a local `file:` registry. Less common than lockfile + offline mirror.

#### pip

- **`requirements.txt` with hash pinning**: `pip-compile --generate-hashes` produces a requirements file with per-package `--hash=sha256:...` entries. Installing with `pip install --require-hashes -r requirements.txt` enforces that every package matches its expected digest; any deviation fails the install.
- **`--no-index --find-links /path/to/wheels`**: Completely disables PyPI; installs only from a local directory of pre-downloaded wheel files. This is the most restrictive and most hermetic option.
- **devpi**: A self-hosted PyPI mirror server. `devpi-server` runs a caching proxy; point `PIP_INDEX_URL` to it. Supports private indexes, access control, and offline operation after initial cache population.
- **Poetry / uv lockfiles**: `poetry.lock` and `uv.lock` pin transitive dependencies with hashes; equivalent security properties to hash-pinned `requirements.txt`.

#### Go

Go has the strongest built-in supply chain security of any major ecosystem:
- **`go.sum`**: Contains SHA-256 hashes of every module and its `go.mod` file. Any checksum mismatch aborts the build.
- **Checksum database (`sum.golang.org`)**: A globally append-only Merkle tree. When Go downloads a module, it verifies the hash against this database — ensuring every user of a given version receives identical code. An attacker who compromises a module host cannot serve different code to different users without the database detecting it.
- **`GONOSUMCHECK` / `GONOSUMDB`**: Allows excluding private modules from the public checksum database.
- **`GOFLAGS=-mod=vendor`** with **`go mod vendor`**: Copies all dependencies into a `vendor/` directory in the repository. Builds with `-mod=vendor` use only that directory; no network access occurs.
- **`GOFLAGS=-mod=readonly`**: Prevents `go` commands from modifying `go.mod` or `go.sum`; any required change fails the build.
- **Go has no install-time code execution.** This is a critical security property absent in npm and pip.
- **Athens proxy**: Open-source Go module proxy. Run it in front of `proxy.golang.org` to cache modules locally; set `GOPROXY=http://athens:3000,direct` or `GOPROXY=http://athens:3000,off` (the `off` suffix blocks fallback to the internet).

#### Cargo (Rust)

- **`Cargo.lock`**: Pins exact versions and checksums for all dependencies. `cargo build --locked` fails if `Cargo.lock` would need to change.
- **`cargo vendor`**: Copies all crate source into a `vendor/` directory; subsequent builds use `--offline` flag and read only from vendor.
- **`cargo fetch --locked`**: Pre-downloads all crates into the local registry cache without building.
- **Private registry**: Configurable via `.cargo/config.toml`; JFrog Artifactory supports Cargo as a private registry.
- Cargo does not execute arbitrary code during dependency download; build scripts (`build.rs`) run only during compilation, not during fetch.

---

### 5. Private Registry Mirrors

Private registry mirrors sit between the build environment and the public internet. They provide:
- **Caching**: Once a package is fetched, it is served locally even if the public registry goes down or is compromised.
- **Allowlisting**: Only approved packages are available; unapproved packages are blocked.
- **Immutability**: A mirrored registry can be frozen at a point in time, providing identical packages across all builds.
- **Audit trails**: All install requests are logged.

| Tool | Ecosystem | Key Properties |
|------|-----------|----------------|
| **Verdaccio** | npm | Lightweight Node.js server, Docker-friendly, caching proxy with YAML config, htpasswd auth, supports scoped packages, offline after initial cache fill |
| **devpi** | pip | PyPI-compatible caching mirror, private index support, access control per index, RESTful API, `PIP_INDEX_URL` integration |
| **Athens** | Go modules | GOPROXY-compatible, filters module paths, supports `GONOSUMDB`, can operate in "CDN only" mode (no direct VCS access) |
| **Artifactory** | All + more | Universal repository supporting npm, pip, Go, Cargo, Maven, Docker, etc.; enterprise SLA; replication; vulnerability scanning; integration with CI/CD |
| **Nexus Repository** | All | Similar to Artifactory; open-source core edition available |

**Operational requirements for a private mirror in an agent sandbox:**
- Mirror must be seeded before the sandbox starts (the pre-populate step)
- Sandbox's package manager must be configured to use the mirror as its sole index (`--registry`, `PIP_INDEX_URL`, `GOPROXY`, `.cargo/config.toml`)
- Outbound network from the sandbox to the public internet should be blocked at the network layer (not just configured away at the tool level) — defense in depth
- Mirror itself should be outside the sandbox network namespace to prevent the agent from reconfiguring it

---

### 6. Package Integrity Verification

| Ecosystem | Mechanism | Strength |
|-----------|-----------|----------|
| npm | SHA-512 hashes in `package-lock.json` `integrity` field; verified by `npm ci` | Strong if lockfile is not tampered with |
| pip | `--require-hashes` mode; SHA-256 hashes in `requirements.txt`; verified on install | Strong; fails on any digest mismatch |
| Go | `go.sum` with SHA-256; cross-referenced against `sum.golang.org` Merkle tree | Very strong; global consistency guarantee |
| Cargo | SHA-256 checksums in `Cargo.lock`; verified on `cargo build --locked` | Strong |
| All containers | Sigstore/cosign for container image signing; keyless signing tied to OIDC identity | Strong for image provenance, not package-level |

**Lockfile poisoning** is a separate threat: an attacker modifies the lockfile itself (e.g., in a PR) to substitute a legitimate package hash with a malicious one. Defense: require code review for lockfile changes and use CODEOWNERS to restrict who can approve them.

**npm audit signatures** (`npm audit signatures`) verifies that installed packages have valid npm registry signatures. This is a post-installation check and does not prevent execution of malicious install scripts.

**Sigstore and cosign** are increasingly used for container image signing (Kubernetes admission controllers can require it) and are beginning to be used for package-level attestation (npm provenance attestation — over 16,000 unique packages have now published with provenance). However, Sigstore does not prevent typosquatting or slopsquatting; it only provides a chain of custody for packages that are correctly identified.

---

### 7. How the Agent Use Case Differs from Human Development

In human development workflows, a developer adds a new dependency deliberately: they research it, add it to `package.json` or `requirements.txt`, run the install, and commit the updated manifest and lockfile. This is a reviewed, intentional act.

An AI coding agent in an automated pipeline:
- May decide to add a new dependency without explicit human instruction
- Will do so at machine speed, with no pause for review
- May hallucinate non-existent package names (slopsquatting risk)
- Is operating in an environment where the human reviewer sees only the output, not the install commands executed during the run

**Does the agent actually need to install new packages?**

In the QRSPI workflow, a design document and structure plan are approved before implementation begins. Any new external dependencies should be identified at design time. The implement role is executing a known, scoped task — not doing open-ended research. This means:

- The vast majority of implementation tasks use existing project dependencies
- New dependencies, if needed, can be identified in the structure/plan phase and pre-populated into the environment
- Allowing the agent to spontaneously install packages expands the attack surface without a corresponding increase in capability for well-scoped implementation tasks

The exception is scaffolding or greenfield projects where the full dependency tree is not yet known. Even here, a better workflow is: agent proposes dependencies → human approves → dependencies are pre-populated → agent implements.

---

### 8. How CI/CD Systems Handle This Problem

**GitHub Actions** does not solve this at the package level — it relies on caching and lockfiles:
- `npm ci` (not `npm install`) is the recommended command because it strictly follows `package-lock.json`
- Cache keys are keyed on `package-lock.json` hash so cache invalidates when lockfile changes
- Actions themselves must be pinned to full commit SHAs (not tag aliases) to prevent supply chain attacks on the workflow definition; the March 2025 `tj-actions/changed-files` compromise (23,000+ repositories affected) occurred because actions were pinned to mutable tags
- GitHub Actions policy (as of August 2025) now supports blocking actions and enforcing SHA pinning at the organization level
- Notably, GitHub Actions has **no offline installation mode** and no native vendoring mechanism

**Google Cloud Build / Hermeto**: Hermeto is a CLI tool used in Tekton/OpenShift CI pipelines that pre-fetches dependencies from a lockfile before the build starts, generating an SBOM. The build step runs with network disabled. Hermeto refuses to fetch any dependency not pinned to an exact version. It covers npm, pip, Go, Cargo, Bundler, and RPM.

**General CI best practice** (from multiple sources): Never run `pip install` or `npm install` without a pinned lockfile in CI. The seven-day cooldown before accepting new package versions in automated systems would have prevented 8 out of 10 major 2025 supply chain attacks.

---

### 9. Hermetic Builds: Definition and Applicability

A **hermetic build** is one where:
1. All inputs are declared explicitly (no implicit environment dependencies)
2. No network access occurs during the build step itself
3. Given the same inputs, the build always produces the same output

Bazel, the build tool developed at Google, enforces hermeticity by running each build action in a sandbox that contains only declared inputs and blocks network access (`--sandbox_default_allow_network=false`). Tools are treated as versioned inputs, not ambient environment.

**Applicability to the agent sandbox:** Full Bazel-style hermeticity is not typically achievable for general-purpose AI coding agents because:
- The project may use any build tool (npm scripts, Make, pytest, etc.)
- The agent generates code dynamically and then tests it

However, a **partial hermetic model** is both achievable and recommended:
- Network access is blocked during the build/test phase (network is only available during an explicit pre-fetch phase)
- Dependencies are pre-fetched and content-addressed before the agent starts
- The agent can read/use packages but cannot trigger new downloads
- The container image snapshot includes the pre-fetched package cache

This is exactly what Hermeto and similar tools provide: a pre-fetch phase with network, then a build phase without it.

---

### 10. Decision Matrix

| Option | Security | Operational Complexity | Agent Capability Impact |
|--------|----------|----------------------|------------------------|
| (a) Vendor / lockfile only, no install during agent run | High | Low-Medium (pre-populate step required) | Minimal — agent implements against declared deps |
| (b) Private registry mirror, restricted install | Medium-High | Medium-High (mirror infrastructure required) | Low — agent can install approved packages |
| (c) Unrestricted public registry install | Low | Low | None |

---

## Recommendation Details

**For the QRSPI implement role, the recommended policy is:**

1. **Before launching the implement container**: Run a dependency pre-fetch step (using the project's existing lockfile) that populates the package cache inside the container image or a mounted volume.

2. **Block outbound network to package registries** at the container network policy level (not just by configuration). If the container is Kubernetes-based, a NetworkPolicy or Cilium policy should deny egress to npm, PyPI, crates.io, proxy.golang.org, etc.

3. **If the agent truly needs a new package** (identified during the session): The agent should emit a structured request (e.g., write to a designated file or output a specific log line), the session ends, a human approves, the package is added to the lockfile and pre-fetched in a new pre-populate step, and a new implementation session begins. This is consistent with the QRSPI structure phase identifying dependencies before implementation.

4. **If a private registry is used (option b fallback)**: Configure the package manager to use the mirror as the sole source (`--registry`, `PIP_INDEX_URL`, `GOPROXY=http://mirror,off`). The `off` suffix / `--no-index` equivalent is critical — it prevents fallback to the public internet if a package is not in the mirror. The mirror should contain only pre-approved, pre-scanned packages.

5. **Lockfile flags**: Always use `npm ci`, `pip install --require-hashes`, `cargo build --locked`, `go build -mod=vendor` (or `-mod=readonly`). These flags cause the install to fail rather than silently resolve new versions if the environment differs from the lockfile.

---

## Sources

- [PyPI, npm, and the New Frontline of Software Supply Chain Attacks — RapidFort](https://www.rapidfort.com/blog/pypi-npm-and-the-new-frontline-of-software-supply-chain-attacks)
- [Supply Chain Worms 2026 — Dark Reading](https://www.darkreading.com/cyberattacks-data-breaches/supply-chain-worms-in-2026-what-shai-hulud-taught-attackers-and-how-to-prepare)
- [Widespread Supply Chain Compromise Impacting npm Ecosystem — CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem)
- [North Korea-Nexus Threat Actor Compromises Axios NPM Package — Google Cloud Blog](https://cloud.google.com/blog/topics/threat-intelligence/north-korea-threat-actor-targets-axios-npm-package)
- [Malicious PyPI and npm Packages Discovered Exploiting Dependencies — The Hacker News](https://thehackernews.com/2025/08/malicious-pypi-and-npm-packages.html)
- [npm Security Risks 2026: Vulnerable Packages & Fixes — CyberDesserts](https://blog.cyberdesserts.com/npm-security-vulnerabilities/)
- [Dependency Confusion: How I Hacked Into Apple, Microsoft and Dozens of Other Companies — Alex Birsan / Medium](https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610)
- [PEP 708 – Extending the Repository API to Mitigate Dependency Confusion Attacks](https://peps.python.org/pep-0708/)
- [Detect and Prevent Dependency Confusion Attacks on npm — Snyk](https://snyk.io/blog/detect-prevent-dependency-confusion-attacks-npm-supply-chain-security/)
- [Dependency Confusion Supply Chain Attacks: 49% of Organizations Are Vulnerable — Orca Security](https://orca.security/resources/blog/dependency-confusion-supply-chain-attacks/)
- [Understanding and Preventing Dependency Confusion Attacks — FOSSA](https://fossa.com/blog/dependency-confusion-understanding-preventing-attacks/)
- [Slopsquatting: How AI Hallucinations Are Fueling a New Class of Supply Chain Attacks — Socket](https://socket.dev/blog/slopsquatting-how-ai-hallucinations-are-fueling-a-new-class-of-supply-chain-attacks)
- [Slopsquatting: When AI Agents Hallucinate Malicious Packages — Trend Micro](https://www.trendmicro.com/vinfo/gb/security/news/cybercrime-and-digital-threats/slopsquatting-when-ai-agents-hallucinate-malicious-packages)
- [AI-Hallucinated Code Dependencies Become New Supply Chain Risk — BleepingComputer](https://www.bleepingcomputer.com/news/security/ai-hallucinated-code-dependencies-become-new-supply-chain-risk/)
- [Slopsquatting, Typosquatting, and the New Software Supply Chain Attacks — dsebastien.net](https://www.dsebastien.net/slopsquatting-typosquatting-and-the-new-software-supply-chain-attacks-how-ai-and-vibe-coding-are-making-package-registries-even-more-dangerous/)
- [Malicious Packages 2025 Recap — Xygeni](https://xygeni.io/blog/malicious-packages-2025-recap-malicious-code-and-npm-malware-trends/)
- [The Landscape of Malicious Open Source Packages: 2025 Mid-Year Threat Report — Socket](https://socket.dev/blog/malicious-open-source-packages-2025-mid-year-threat-report)
- [PyPI Inundated by Malicious Typosquatting Campaign — Check Point](https://blog.checkpoint.com/securing-the-cloud/pypi-inundated-by-malicious-typosquatting-campaign/)
- [Lockfiles Killed Vendoring — Andrew Nesbitt](https://nesbitt.io/2026/02/10/lockfiles-killed-vendoring.html)
- [Why Lockfiles Matter for Supply Chain Security — Aikido](https://www.aikido.dev/blog/why-we-need-lockfiles-to-secure-our-supply-chain)
- [The Design Space of Lockfiles Across Package Managers — arXiv](https://arxiv.org/pdf/2505.04834)
- [How Go Mitigates Supply Chain Attacks — The Go Programming Language](https://go.dev/blog/supply-chain)
- [Go modules: go.sum, SumDB, GOPROXY/GOSUMDB — Ask AppSec](https://askappsec.com/glossary/go-modules-go-sum-sumdb-goproxy-gosumdb/)
- [Module Mirror and Checksum Database Launched — The Go Programming Language](https://go.dev/blog/module-mirror-launch)
- [cargo vendor — The Cargo Book](https://doc.rust-lang.org/cargo/commands/cargo-vendor.html)
- [Why 90% of Rust Crates Have Supply Chain Risks — Markaicode](https://markaicode.com/rust-crate-supply-chain-security/)
- [How to Run a Private Cargo Registry — JFrog](https://jfrog.com/learn/devops/how-to-run-a-private-cargo-registry/)
- [Verdaccio Best Practices](https://www.verdaccio.org/docs/best/)
- [Verdaccio GitHub Repository](https://github.com/verdaccio/verdaccio)
- [How to Run Verdaccio in Docker](https://oneuptime.com/blog/post/2026-02-08-how-to-run-verdaccio-in-docker-private-npm-registry/view)
- [devpi-server — PyPI](https://pypi.org/project/devpi-server/)
- [Quickstart: Running a PyPI Mirror with devpi](https://devpi.net/docs/devpi/devpi/stable/+doc/quickstart-pypimirror.html)
- [Athens: A Go Module Datastore and Proxy — GitHub](https://github.com/gomods/athens)
- [Set Up Your Secure, Private Go Registries — JFrog Artifactory](https://jfrog.com/blog/goproxy-artifactory-go-registries/)
- [Hermeto — Hermeto Project](https://hermetoproject.github.io/hermeto/)
- [Lockfile Poisoning and How Hashes Verify Integrity in Node.js Lockfiles — Medium](https://medium.com/node-js-cybersecurity/lockfile-poisoning-and-how-hashes-verify-integrity-in-node-js-lockfiles-0f105a6a18cd)
- [package-lock.json — npm Docs](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/)
- [Sigstore / Cosign for Supply Chain Security — GitGuardian](https://blog.gitguardian.com/supply-chain-security-sigstore-and-cosign-part-ii/)
- [cosign Verification of npm Provenance — Sigstore Blog](https://blog.sigstore.dev/cosign-verify-bundles/)
- [GitHub Actions policy now supports blocking and SHA pinning actions — GitHub Changelog](https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/)
- [Pinning GitHub Actions for Enhanced Security — StepSecurity](https://www.stepsecurity.io/blog/pinning-github-actions-for-enhanced-security-a-complete-guide)
- [Why You Should Pin GitHub Actions by Commit-Hash](https://blog.rafaelgss.dev/why-you-should-pin-actions-by-commit-hash)
- [Hermeticity — Bazel](https://bazel.build/basics/hermeticity)
- [How to Do Hermetic Builds — Andreas Zwinkau](https://beza1e1.tuxen.de/hermetic_builds.html)
- [How to Sandbox AI Agents in 2026: MicroVMs, gVisor & Isolation Strategies — Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [A New Approach for Coding Agent Safety — Docker](https://www.docker.com/blog/docker-sandboxes-a-new-approach-for-coding-agent-safety/)
- [Package Managers Need to Cool Down — Andrew Nesbitt](https://nesbitt.io/2026/03/04/package-managers-need-to-cool-down.html)
