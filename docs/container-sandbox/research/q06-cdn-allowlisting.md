# Q6: How Are CDN-Hosted Resources Handled in an Egress Allowlist?

**Research question:** Many documentation and package registry resources share CDN infrastructure (e.g., fastly.net, cloudfront.net). Allowlisting at the CDN domain defeats the purpose (too broad); allowlisting by resolved IP is brittle (CDN IPs change constantly). Is there a workable approach, or is this an accepted gap?

---

## Summary and Recommendation

**The workable approach is SNI-based hostname allowlisting, not IP-based allowlisting and not CDN-domain allowlisting.**

When a container makes a TLS connection to `pypi.org`, the TLS Client Hello packet contains an unencrypted SNI field with the value `pypi.org`. Modern firewalls (AWS Network Firewall, Palo Alto NGFW, Vercel Sandbox, mitmproxy sidecars) can inspect this SNI field and permit or deny the connection based on the requested hostname, completely independent of what IP address the CDN resolves to. This means allowlisting `pypi.org` works correctly even though it resolves to a Fastly IP that is shared with thousands of other customers.

**However, SNI-based allowlisting has a critical residual risk: domain fronting.** If an attacker can set the SNI to an allowed hostname (e.g., `pypi.org`) but route the request to a different backend via the HTTP Host header, the firewall passes the traffic based on the SNI while the CDN delivers attacker-controlled content. Fastly was historically vulnerable to this. Since 2024, Fastly has implemented anti-fronting protections. CloudFront, Cloudflare, and Google have longer-standing protections.

**Recommended architecture (ordered by strength):**

1. **Preferred: Private registry mirror** (Artifactory, Nexus, or Sonatype Nexus Repository). Host an internal mirror of pypi.org, registry.npmjs.org, etc. The container never talks to the public internet for packages. The mirror handles CDN egress once on cache-miss, which can be from a separate, less-restricted network zone. This eliminates the CDN problem entirely for sandboxed code execution.

2. **Acceptable: SNI-based hostname allowlisting** with TLS inspection to validate that the presented certificate matches the SNI. Use a terminating HTTPS proxy (e.g., mitmproxy, Squid with SSL bump, or a cloud-native proxy) that decrypts traffic, verifies SNI matches Host header, then re-encrypts. This closes the domain-fronting gap.

3. **Weaker but pragmatic: SNI-peek-only allowlisting** (no decryption). Use AWS Network Firewall domain rules, Vercel Sandbox SNI-peeking, or iptables + a sidecar proxy inspecting TLS handshakes. This is the most common approach today and is sufficient against opportunistic misuse. Domain fronting remains a theoretical gap against a determined attacker.

4. **Do not use: IP-based allowlisting** for CDN-hosted content. CDN IP ranges change without predictable schedules and are shared across all CDN customers (making them meaninglessly broad as access controls).

5. **Do not use: CDN domain allowlisting** (e.g., `*.fastly.net`). This allows any Fastly customer's content, including attacker-controlled origins.

---

## Detailed Findings

### 1. How Major CDNs Serve Content: Shared IPs and SNI Routing

All major CDNs (Fastly, Cloudflare, CloudFront, Akamai) serve multiple customers from shared IP addresses. The technical mechanism for distinguishing customers at the TLS layer is SNI (Server Name Indication), a TLS extension present in the unencrypted Client Hello packet that tells the CDN which customer's certificate to present.

**Fastly:** By default installs TLS certificates at a shared set of IP addresses. When a client connects, the correct certificate is selected using the SNI extension. Fastly publishes its public IP list via API (`https://api.fastly.com/public-ip-list`) and announces changes through its status page before deploying them. The IP list is described as "exhaustive" but does not carry a fixed change schedule.

**Cloudflare:** Similarly uses shared IPs across all proxied hostnames. Cloudflare publishes IP ranges at `https://www.cloudflare.com/ips/` and states changes are added to the list before being put into production. Enterprise customers can purchase Bring Your Own IP (BYOIP) or Cloudflare Aegis (dedicated egress IPs) if they need stable IP-based allowlisting at their origin.

**Amazon CloudFront:** Uses a large network of shared edge IPs. AWS publishes IP ranges via `https://ip-ranges.amazonaws.com/ip-ranges.json`, updated when ranges change. CloudFront has implemented domain-fronting protections since 2018: mismatched SNI and Host headers result in a 421 error.

**Akamai:** Operates ~298 IPv4 CIDR ranges covering over 842,000 addresses. Community members working with Palo Alto NGFWs have noted that IP-based allowlisting for Akamai is impractical at scale and recommend domain-name filtering instead. Automated tools exist that update Akamai IP lists hourly via ASN lookups, which is itself evidence of how volatile these ranges are.

**Key implication for egress filtering:** Because CDN IPs are shared, allowlisting by IP is simultaneously too broad (allows any CDN tenant) and brittle (IPs change). The correct unit of allowlisting is the hostname presented in SNI.

---

### 2. Which CDNs Power Which Package Registries and Doc Sites

| Service | CDN Provider(s) | Notes |
|---|---|---|
| **pypi.org** | Fastly | Fastly provides this service free of charge (>$1.8M/mo value). Files served from `files.pythonhosted.org` → CNAME `dualstack.python.map.fastly.net` |
| **registry.npmjs.org** | Fastly | npm has used Fastly since at least 2013. The `npm-fastly-purge` tool purges Fastly cache on every registry change |
| **crates.io** (index) | Fastly | The sparse index at `index.crates.io` is served via Fastly |
| **static.crates.io** (downloads) | CloudFront | Crate tarballs stored in S3, served through a CloudFront distribution |
| **static.rust-lang.org** (releases) | CloudFront + Fastly | Rust releases use both CDNs |
| **docs.python.org** | Fastly | Python Infrastructure Status page lists Fastly as the CDN for docs |
| **docs.rs** | CloudFront (likely) | Part of the Rust infrastructure which uses CloudFront for static content |

**Practical consequence:** For a container sandbox needing to `pip install` and `cargo add`, the SNI hostnames to allowlist are `pypi.org`, `files.pythonhosted.org`, `index.crates.io`, `static.crates.io`, and `crates.io`. All of these will resolve to Fastly or CloudFront IPs that are shared with other tenants and will change over time.

---

### 3. IP Allowlisting Brittleness

IP-based allowlisting for CDN-hosted content fails on two axes:

**Breadth problem:** A Fastly IP serves thousands of websites. Allowlisting `151.101.0.0/17` (a Fastly block) effectively permits access to any Fastly customer. This is not a useful security boundary.

**Volatility problem:** CDN operators grow their networks continuously. Fastly announces IP changes via its status page but does not commit to a minimum notice window or a maximum rate of change. Akamai community members maintain hourly-updated IP lists as a matter of necessity. Cloudflare adds new ranges as they expand. An organization maintaining IP allowlists must subscribe to CDN status feeds and update firewall rules reactively. Automation (pulling from CDN-published IP range APIs and updating rules) reduces operational burden but introduces its own failure modes (stale cache, API outage during a CDN expansion event).

The contrast with SNI-based allowlisting is sharp: `pypi.org` as an SNI allowlist rule does not change when Fastly adds a new data center. The hostname is stable; the IP behind it is not.

---

### 4. SNI/Hostname Allowlisting: Does Allowlisting `pypi.org` Work on a CDN?

Yes, with caveats.

When `pip install` connects to `pypi.org`, it performs a DNS lookup (returning a Fastly IP), then opens a TLS connection. The TLS Client Hello includes `SNI=pypi.org` in plaintext. A firewall or proxy that inspects SNI can:

1. Permit the connection because `pypi.org` is in the allowlist.
2. Block the connection before any data flows if the hostname is not allowed.

This is the mechanism used by:
- **AWS Network Firewall** domain list rule groups (HTTPS uses SNI, HTTP uses Host header)
- **Vercel Sandbox** "SNI-peeking firewall" (announced February 2026) that inspects the unencrypted TLS handshake bytes
- **Palo Alto NGFW** without decryption: reads SNI from Client Hello for URL categorization
- **Zscaler ZIA**: performs TLS inspection (full termination) and applies URL filtering policies

The critical caveat is **domain fronting**: an attacker could send a TLS Client Hello with `SNI=pypi.org` but include `Host: attacker.example.com` in the decrypted HTTP/1.1 request. The firewall (if not decrypting) allows the connection based on SNI; the CDN routes based on Host header. This allows an attacker to reach arbitrary origins on the same CDN using the SNI of an allowlisted hostname.

**Current status of domain fronting protections by CDN:**
- **Fastly:** As of 2024, Fastly enforces that the SNI in the TLS handshake matches a SAN on the presented certificate and that the Host header matches. The fix was implemented after the PyPI warehouse issue #10399 was filed. The error now returned is: "Requested host does not match any Subject Alternative Names (SANs) on TLS certificate." However, research papers (2023) still document Fastly as vulnerable in some configurations.
- **CloudFront (AWS):** Has enforced Host/SNI matching since April 2018 (returns HTTP 421). Considered protected.
- **Cloudflare:** Generally protected; enforces certificate SAN matching.
- **Akamai:** Mixed. Research from 2023 found Akamai still vulnerable in some configurations.

**Conclusion on SNI allowlisting:** Allowlisting `pypi.org` by SNI is functionally effective for legitimate use. It works regardless of which Fastly IP the hostname currently resolves to. The residual domain-fronting risk is real but has been substantially reduced by CDN-side protections implemented in 2023-2024.

---

### 5. How Enterprise Tools Handle CDN Traffic

**Palo Alto NGFW:**
- Without SSL decryption: reads SNI from TLS Client Hello. Uses App-ID to classify applications. Can create custom app-IDs that trigger on specific Host headers. Cannot see Host header in encrypted traffic without decryption.
- With SSL decryption: full TLS termination. Can compare SNI to Host header and detect domain fronting. Palo Alto documents "Domain Fronting Detection" as a feature available when decryption is enabled.
- Enterprise recommendation: enable SSL decryption for egress traffic to sensitive CDN-hosted resources; skip decryption for categories that present certificate pinning issues (banking, etc.).

**Zscaler ZIA:**
- Performs full TLS inspection by default for most traffic categories. Acts as a terminating HTTPS proxy: decrypts, inspects Host header and URL path, applies URL category policies, re-encrypts.
- CDN-specific handling: some CDN URLs may need to be excluded from SSL inspection if they use certificate pinning or unique root CAs.
- URL filtering is applied post-decryption, making Zscaler significantly more precise than SNI-only filtering. Can block `*.fastly.net` while permitting `pypi.org` because it sees the actual HTTP Host header.

**General enterprise model:**
Both tools converge on the same approach: use TLS inspection (full decryption) for precise, SNI+Host-header aware filtering. Organizations that cannot do full TLS inspection fall back to SNI-only, accepting the domain-fronting residual risk as an accepted gap.

---

### 6. CI/CD System Approaches

**GitHub Actions:**
GitHub Actions runners (hosted) have unrestricted internet access. Organizations using StepSecurity's Harden-Runner can instrument workflows to observe all outbound connections and generate per-workflow allowlists. The system identifies specific hostnames contacted during runs (e.g., `registry.npmjs.org`, `files.pythonhosted.org`) and allows teams to define cluster-wide default egress policies. Harden-Runner operates at the runner level, not at the CDN level, and filters by hostname.

**GitLab CI:**
GitLab's built-in package registry allows organizations to host their own npm and PyPI mirrors inside GitLab, eliminating outbound CDN traffic for package installation entirely. CI jobs authenticate via `CI_JOB_TOKEN` and `CI_PROJECT_ID`. The network egress problem for packages is solved by routing through the internal GitLab registry rather than the public CDN-backed registries.

**Vercel Sandbox (February 2026):**
Vercel's sandbox product now offers an SNI-peeking egress firewall that rejects TLS connections before any data is transmitted if the SNI hostname is not on the allowlist. Supports wildcard patterns (`*.vercel.com`). Policies can be updated dynamically without restarting the sandbox. For non-TLS protocols, falls back to IP/CIDR rules.

**Pattern observed across CI/CD systems:** The practical answer is not CDN-level allowlisting but hostname-level allowlisting combined with phase separation:
1. Open egress during a dependency installation phase (or route through a private registry mirror).
2. Locked-down egress during untrusted code execution.
3. Selective re-opening for specific API calls post-execution if needed.

---

### 7. Private Registry Mirrors as an Alternative

Private registry mirrors (Artifactory, Nexus Repository, Sonatype Nexus, GitLab Package Registry) eliminate the CDN egress problem for containers by moving the package resolution inside the trust boundary.

**How it works:**
- The container's package manager is configured to point to `https://artifacts.internal/pypi/` instead of `https://pypi.org/`.
- The internal mirror proxies and caches packages from the upstream CDN-backed registry.
- Cache-miss requests from the mirror go out to the real CDN, but from a trusted, monitored, non-sandboxed network context.
- The sandboxed container never touches the public internet for packages.

**JFrog Artifactory:**
- Supports PyPI, npm, Cargo (Rust), Maven, Docker, and 30+ other formats as remote (proxy) repositories.
- Remote repositories cache artifacts locally after the first request.
- For fully air-gapped environments: supports two-instance "air-gap" deployment where an outer instance with internet access downloads to an external device, and the inner instance imports from that device.
- Smart Remote Repositories handle metadata and package resolution transparently.

**Sonatype Nexus Repository:**
- Similar capabilities; OSS version is free. Supports PyPI proxy, npm proxy.
- Widely used in enterprise Java environments; increasingly adopted for polyglot repos.

**Security benefits beyond CDN elimination:**
- Package scanning (JFrog Xray, Nexus Lifecycle) can block malicious packages before they reach containers.
- Pin package versions; the mirror does not fetch new versions unless explicitly requested.
- Complete audit log of what packages were installed in which container.
- No dependency on CDN uptime for production workloads.

**Operational cost:** Mirror infrastructure requires maintenance, storage, and periodic upstream syncs. For a small sandbox project, self-hosted Nexus or a cloud-hosted Artifactory SaaS is a reasonable tradeoff. GitLab's built-in registry is effectively free for GitLab users.

---

### 8. The Security Gap: What an Attacker Can Do If `fastly.net` is Allowlisted

If a broad CDN domain like `*.fastly.net` or `*.cloudfront.net` is in an egress allowlist (either SNI-based or IP-based), the attack surface is substantial:

**Domain fronting C2 (pre-2024, Fastly):** An attacker registers any Fastly service (free tier available). Malware running in the container connects using `SNI=files.pythonhosted.org` or any other allowlisted Fastly customer, but the decrypted Host header points to the attacker's Fastly service. The CDN routes the request to the attacker. The C2 channel is encrypted with a legitimate PyPI certificate. This technique was actively used in the wild and documented in the JFrog `importantpackage` malware case study:

> "The malware crafted HTTPS requests appearing to target PyPI while manipulating the Host header to redirect through Fastly CDN to attacker infrastructure... communication remained encrypted with PyPI's legitimate certificate throughout."

**General CDN abuse even with SNI matching (if `*.fastly.net` is allowed):**
- Register a Fastly CDN service for `attacker.net` (free tier).
- `attacker.net.global.ssl.fastly.net` is a Fastly SNI hostname.
- If `*.fastly.net` is allowlisted by SNI, the container can reach arbitrary content at `attacker.net`.
- Data exfiltration: encode data in URL paths, query strings, or POST bodies to a Fastly-fronted attacker endpoint. All traffic looks like normal CDN HTTPS to any network observer that does not decrypt.

**DNS tunneling via CDN-hosted names:** Encode stolen data in subdomain queries to domains hosted on CDN-proxied DNS. Harder to filter at the CDN layer.

**Practical risk for a sandbox:** If the sandbox runs arbitrary agent-generated code, and the agent can exfiltrate data, CDN-hosted C2 is a realistic threat model. The `*.fastly.net` allowlist effectively gives attacker code a free exfiltration channel.

**Mitigation:** Never allowlist CDN domains (`*.fastly.net`, `*.cloudfront.net`). Only allowlist the specific hostnames you need (`pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org`). Pair with TLS inspection to detect domain-fronting attempts.

---

### 9. Recommended Allowlist for Common Development Registries

For a sandbox that needs to install Python, Node.js, and Rust packages during a build phase, the following hostname-level SNI allowlist covers the major registries:

**Python (pip):**
- `pypi.org`
- `files.pythonhosted.org`

**Node.js (npm):**
- `registry.npmjs.org`

**Rust (cargo):**
- `crates.io`
- `index.crates.io`
- `static.crates.io`

**Go modules:**
- `proxy.golang.org`
- `sum.golang.org`

**Documentation (read-only, lower risk):**
- `docs.python.org`
- `docs.rs`
- `doc.rust-lang.org`

These hostnames are stable even though the IP addresses behind them (Fastly or CloudFront) are not. They can be configured as SNI-based rules in AWS Network Firewall, Palo Alto domain lists, mitmproxy ACLs, or Vercel Sandbox allowlists without any IP management burden.

---

## Conclusion

The CDN allowlisting problem is real but has a workable solution: **allowlist by SNI hostname, not by IP range or CDN domain.** SNI-based allowlisting is stable (hostnames don't change when CDN IPs rotate), appropriately scoped (allows only the specific service you need, not all CDN tenants), and supported by all major network security tools.

The residual gap is domain fronting, which is addressed by either: (a) enabling TLS inspection on the egress proxy to validate Host header matches SNI, or (b) relying on CDN-side anti-fronting enforcement (now present in Fastly, CloudFront, and Cloudflare). For high-security sandboxes, the cleanest solution remains private registry mirrors, which eliminate CDN exposure entirely for the package installation use case.

---

## Sources

- [Advanced egress firewall filtering for Vercel Sandbox - Vercel Changelog](https://vercel.com/changelog/advanced-egress-firewall-filtering-for-vercel-sandbox)
- [Containers, Agents - Secure credential injection and dynamic egress policies for Sandboxes - Cloudflare Community](https://community.cloudflare.com/t/containers-agents-secure-credential-injection-and-dynamic-egress-policies-for-sandboxes/918586)
- [Use AWS Network Firewall to filter outbound HTTPS traffic from applications hosted on Amazon EKS](https://aws.amazon.com/blogs/security/use-aws-network-firewall-to-filter-outbound-https-traffic-from-applications-hosted-on-amazon-eks/)
- [Control which domains your AI agents can access - AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/control-which-domains-your-ai-agents-can-access/)
- [AWS Network Firewall Egress Filtering Bypass - Hacking The Cloud](https://hackingthe.cloud/aws/post_exploitation/network-firewall-egress-filtering-bypass/)
- [Stateful domain list rule groups in AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/stateful-rule-groups-domain-names.html)
- [Bypassing Web Filters Part 3: Domain Fronting - Compass Security Blog](https://blog.compass-security.com/2025/03/bypassing-web-filters-part-3-domain-fronting/)
- [Domain fronting - Wikipedia](https://en.wikipedia.org/wiki/Domain_fronting)
- [Consider using a CDN that is resistant to domain fronting - PyPI warehouse issue #10399](https://github.com/pypi/warehouse/issues/10399)
- [Python Malware Imitates Signed PyPI Traffic in Novel Exfiltration Technique - JFrog Blog](https://jfrog.com/blog/python-malware-imitates-signed-pypi-traffic-in-novel-exfiltration-technique/)
- [Measuring CDNs susceptible to Domain Fronting - arxiv.org](https://arxiv.org/pdf/2310.17851)
- [Domain Shadowing: Leveraging Content Delivery Networks - USENIX Security](https://www.usenix.org/system/files/sec21fall-wei.pdf)
- [Detecting and Measuring Security Implications of Entangled Domain Verification in CDN - arxiv.org](https://arxiv.org/html/2409.01887v1)
- [Public IP List - Fastly Documentation](https://www.fastly.com/documentation/reference/api/utils/public-ip-list/)
- [Routing traffic to Fastly - Fastly Documentation](https://www.fastly.com/documentation/guides/concepts/routing-traffic-to-fastly/)
- [Dedicated IP addresses - Fastly Products](https://docs.fastly.com/products/dedicated-ip-addresses)
- [Simplify allowlist management with Cloudflare Aegis - Cloudflare Blog](https://blog.cloudflare.com/aegis-deep-dive/)
- [Cloudflare IP addresses - Cloudflare Fundamentals docs](https://developers.cloudflare.com/fundamentals/concepts/cloudflare-ip-addresses/)
- [CDN - Rust Forge Infrastructure Documentation](https://forge.rust-lang.org/infra/docs/cdn.html)
- [crates.io development update - Rust Blog](https://blog.rust-lang.org/2026/01/21/crates-io-development-update/)
- [Python Infrastructure Status](https://status.python.org/)
- [Inspect SSL/TLS Handshakes - Palo Alto Networks Advanced URL Filtering](https://docs.paloaltonetworks.com/advanced-url-filtering/administration/url-filtering-features/inspect-ssl-tls-handshakes)
- [App-ID Overview - Palo Alto Networks](https://docs.paloaltonetworks.com/ngfw/administration/app-id/app-id-overview)
- [TLS/SSL Inspection with Zscaler Internet Access - Zscaler Reference Guide](https://www.zscaler.com/resources/reference-architectures/tls-ssl-inspection-zscaler-internet-access.pdf)
- [URL Filtering - Zscaler Help Portal](https://help.zscaler.com/zia/policies/url-filtering)
- [Unified Network Egress View: Centralize GitHub Actions Network Destinations - StepSecurity](https://www.stepsecurity.io/blog/unified-network-egress-view-centralize-github-actions-network-destinations-for-your-enterprise)
- [Remote execution environment sandbox - GitLab Docs](https://docs.gitlab.com/user/duo_agent_platform/environment_sandbox/)
- [No Internet? No Problem. Use Artifactory with an Air Gap - JFrog Blog](https://jfrog.com/blog/using-artifactory-with-an-air-gap/)
- [Remote Repositories - JFrog Artifactory Documentation](https://jfrog.com/help/r/jfrog-artifactory-documentation/remote-repositories)
- [Any thoughts on how to whitelist Akamai IP ranges? - Palo Alto Community](https://live.paloaltonetworks.com/t5/general-topics/any-thoughts-on-how-to-whitelist-akamai-ip-ranges/td-p/212327)
- [Egress policies - Cloudflare Zero Trust docs](https://developers.cloudflare.com/cloudflare-one/traffic-policies/egress-policies/)
- [12 Questions and Answers About Domain Fronting (T1090.004) - Security Scientist](https://www.securityscientist.net/blog/12-questions-and-answers-about-domain-fronting-t1090-004/)
- [npm-fastly-purge - GitHub (npm/npm-fastly-purge)](https://github.com/npm/npm-fastly-purge)
- [New npm Registry Architecture - npm Blog Archive](https://blog.npmjs.org/post/75707294465/new-npm-registry-architecture.html)
- [How to sandbox AI agents in 2026: MicroVMs, gVisor & isolation strategies - Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Domain fronting security warning - Claude Code GitHub Issues #20255](https://github.com/anthropics/claude-code/issues/20255)
