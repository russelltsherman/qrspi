# Q5: What is the Right Granularity for the Network Allowlist?

**Research question:** Hostname/SNI-level enforcement is achievable without TLS inspection. Path-level enforcement requires a MITM proxy with an injected CA cert. Is path-level control required, or is hostname sufficient for the threat model of an adversarial agent?

---

## Summary and Recommendation

**Hostname/SNI-level filtering is sufficient for the agentic sandbox threat model.** Path-level enforcement via TLS inspection is not justified and introduces a new attack surface that is worse than the one it closes.

The core reasoning:

1. **The primary threat is exfiltration to unauthorized destinations.** An adversarial agent attempting to exfiltrate data must send it somewhere. Hostname-level filtering prevents egress to any destination not on the allowlist. For an agent whose job is, say, writing code against `api.github.com`, path-level control over what GitHub endpoints it accesses adds marginal security compared to simply not allowing egress to `attacker.com`.

2. **Path-level filtering does not stop a motivated agent from exfiltrating through allowed hostnames.** If `api.github.com` is allowed, an agent can encode data in issue comments, gist bodies, or commit messages regardless of whether the proxy inspects paths. Allowing a hostname implicitly trusts the agent to behave within that service's semantics. Path filtering narrows the surface but does not close it.

3. **CA cert injection creates a concrete new attack vector.** The proxy's CA private key must reside in or near the container. An adversarial agent that can read the filesystem or environment (which it frequently can in code-execution sandboxes) can extract this key and use it to fabricate certificates trusted by any process on the sandbox — subverting the very control it was meant to enforce.

4. **Operational complexity of TLS inspection is substantial** — certificate lifecycle, compatibility with certificate-pinning libraries, breaking mutual TLS, memory overhead, and performance cost. For a sandbox with a narrow, role-defined allowlist (tens of hostnames, not thousands), this complexity is not warranted.

**Recommended architecture:** Transparent SNI-based egress proxy (Envoy or nginx stream module) with a default-deny policy and an explicit hostname allowlist. Pair with DNS filtering through the same proxy and HTTPS-only enforcement. No TLS inspection.

---

## 1. How SNI-Based Filtering Works

### What is SNI?

Server Name Indication (SNI) is a TLS extension sent in the plaintext `ClientHello` message at the start of every TLS handshake. It contains the target hostname the client intends to reach. Because it precedes any encrypted data exchange, it is visible to any network element that can observe the connection — without decrypting anything.

SNI was introduced to allow a single IP address to host multiple HTTPS domains (virtual hosting). Its visibility is a design feature, not an oversight.

### What a firewall or proxy can see without decryption

From a TLS handshake alone, a middlebox can observe:

- **SNI field** — the target hostname
- **IP address** — the destination IP
- **Port** — typically 443
- **TLS version and cipher suite** — from the `ClientHello`
- **Certificate** (after the server responds) — includes the Subject and Subject Alternative Names

What it cannot see without decryption:

- **HTTP path** — e.g., `/repos/org/repo/issues`
- **HTTP headers** — including `Authorization`, `Content-Type`, `User-Agent`
- **Request body**
- **Response body**

### How SNI filtering is implemented

A network device acting as a transparent proxy can:

1. Intercept TCP connections destined for port 443.
2. Parse the first bytes of the TLS `ClientHello` to extract the SNI field (before forwarding any data).
3. Look up the hostname in an allowlist. If denied, tear down the TCP connection (RST). If allowed, proxy the raw TCP stream to the destination — preserving end-to-end TLS.

This approach requires no TLS termination and no certificate manipulation. The agent's TLS session goes through unmolested.

### Limitations of SNI-only filtering

**SNI spoofing.** A process can send an arbitrary SNI value while connecting to a different IP. Standard iptables string matching does not cross-validate the SNI against the server certificate. More sophisticated tools (e.g., AWS Network Firewall with TLS inspection enabled, or a proxy that performs Server Identity Probe) can detect mismatches. For a container sandbox where the network namespace is fully controlled, IP-level validation alongside SNI provides adequate defense: if `api.github.com` resolves only to known GitHub IP ranges, a spoofed SNI pointing to a malicious IP will be caught by IP allowlisting.

**No SNI for non-443 traffic.** Plain HTTP and non-standard ports are not covered by SNI filtering. This is addressed by requiring HTTPS-only egress and blocking all other outbound TCP by default.

**Encrypted Client Hello (ECH).** A newer TLS extension (successor to ESNI, standardized in 2024–2025) encrypts the SNI field using a public key published in the target's DNS record. ECH is currently deployed primarily through CDN providers (Cloudflare, Fastly) and is not widely supported by API endpoints a sandbox would typically reach. If ECH adoption grows, SNI-level filtering degrades. However, for a controlled allowlist of specific API hostnames, an ECH-encrypted SNI that doesn't decrypt to an allowed hostname can simply be blocked by default. Cisco's Secure Firewall (VDB 416, October 2025) introduced ECH-aware detection, blocking connections to ECH-capable CDN endpoints as an undifferentiated group. For a sandbox with a narrow allowlist, a simpler rule (block ECH-enabled connections to unknown CDNs) works.

---

## 2. TLS Inspection (MITM Proxy) Architecture

### How it works

A TLS inspection proxy (also called SSL bump, HTTPS inspection, or TLS break-and-inspect) operates as a man-in-the-middle:

1. The client establishes a TLS connection to the proxy, believing it is talking to the target server.
2. The proxy terminates this TLS session and decrypts the application-layer traffic.
3. The proxy establishes a separate, independent TLS session to the real destination server.
4. The proxy now sees all plaintext HTTP headers, paths, and bodies in both directions.
5. It re-encrypts traffic before forwarding.

### CA certificate injection

For the client to trust the proxy's dynamically generated server certificate (which is signed by the proxy's own CA, not the real server's CA), the proxy's CA root certificate must be installed in the client's trust store. On a laptop, this means deploying the CA cert through Group Policy or MDM. In a container sandbox, it means either:

- Baking the CA cert into the container image at build time.
- Mounting it as a secret at runtime and calling `update-ca-certificates` or equivalent.
- Setting the `SSL_CERT_FILE` / `NODE_EXTRA_CA_CERTS` / `REQUESTS_CA_BUNDLE` environment variables pointing to the cert.

The proxy must also hold the **private key** for this CA. This private key is what allows it to sign arbitrary certificates. It is, as the NSA advisory puts it, "like a key to the kingdom."

### Operational complexity

- **Certificate pinning breakage.** Libraries and tools that pin certificates (e.g., certain AWS SDK versions, language runtimes, security-conscious clients) will reject the proxy's certificate. These must be individually accommodated by exempting them from inspection or disabling pinning.
- **Mutual TLS (mTLS).** If the agent uses client certificates to authenticate to an API, a MITM proxy breaks the client-side authentication handshake unless it actively forwards client certificates — an additional configuration surface.
- **Memory overhead.** Squid with SSL bump maintains a full SSL context per connection. At scale, the documentation warns total certificate cache capacity "may have to exceed several GBs."
- **Performance.** Asymmetric crypto is performed twice per connection instead of once.
- **Certificate lifecycle.** The proxy CA cert must be rotated periodically, requiring redeployment to all containers trusting it.

### Major proxy options for TLS inspection

| Proxy | Language | Strength | Weakness |
|---|---|---|---|
| **Squid with ssl-bump** | C | Mature, widely deployed | Config described as "black magic"; memory-heavy; legal/ethical warnings in its own docs |
| **mitmproxy/mitmdump** | Python | Excellent scriptability; active community; decade of feedback | Python throughput limitations at high connection rates; designed for dev/debug, not production egress control |
| **Envoy (HTTP dynamic forward proxy)** | C++ | High performance; RBAC; rate limiting; rich filter chain | Complex configuration; alpha status for SNI-passthrough variant |
| **Nginx (http_proxy_module)** | C | Simple config; low overhead | No built-in policy engine; path rules require custom Lua or njs scripting |

---

## 3. Hostname-Only vs. Path-Level: What Each Catches and Misses

### What hostname-only enforcement catches

- Connections to **any destination not on the allowlist** — the primary exfiltration threat
- Connections to **attacker-controlled domains** obtained through prompt injection or supply chain compromise
- Connections to **cloud metadata services** (e.g., `169.254.169.254`) if those IPs/hostnames are absent from the allowlist
- Connections to **DNS tunneling endpoints** if the DNS resolver is also filtered (which it should be)
- **Protocol downgrade** attempts if HTTPS-only is enforced alongside hostname filtering

### What hostname-only enforcement misses

**Exfiltration through allowed services.** This is the critical gap. An adversarial agent that has `api.github.com` in its allowlist can:

- POST data to a GitHub Gist, issue comment, or repository file
- Create a repository and push code containing exfiltrated data
- Use the GitHub Actions API to trigger workflows that relay data

Path-level filtering could restrict the agent to `GET /repos/{org}/{repo}/issues` only, blocking POSTs. However, this level of path control is the same as application-layer policy — it is more naturally enforced through API key scoping and least-privilege tokens than through a network proxy inspecting HTTP payloads.

**Exfiltration through legitimate-appearing webhook services.** Real-world attacks against CI/CD pipelines and npm packages have successfully exfiltrated data through `webhook.site`, `pipedream.net`, `burpcollaborator.net`, and `discord.com` — all legitimate services that would appear benign in broad hostname allowlists. The Checkmarx 2024 research documented malicious packages specifically choosing these services because "network traffic to these services will not raise red flags to defenders." Path filtering would not help here either — the entire service is a data-relay.

**Subdomain hijacking.** If the allowlist allows a wildcard like `*.s3.amazonaws.com`, an agent can write to any S3 bucket, including attacker-controlled ones. The correct response is precise hostname allowlisting (specific bucket endpoints), not path filtering.

### The honest limitation

Path-level enforcement addresses **a narrow slice of the exfiltration surface**: it can prevent an agent from calling specific API endpoints on an already-allowed hostname. For a well-scoped allowlist where each allowed hostname corresponds to a specific, narrow API, this adds marginal value. The bigger risks — exfiltration through the semantics of allowed services, subdomain precision, DNS tunneling — are not addressed by path filtering and require other controls.

---

## 4. Security Value of Path-Level Filtering

Path filtering has genuine value in specific scenarios:

**Scenario 1: Broad hostname in the allowlist.** If `s3.amazonaws.com` is allowed (and all buckets resolve to this), path filtering could restrict the agent to reads from `/<specific-bucket>/` only. But the correct fix is to replace `s3.amazonaws.com` with `<specific-bucket>.s3.amazonaws.com`, solving this at the hostname level.

**Scenario 2: Shared API domains.** `api.github.com` hosts both read endpoints (`/repos/{org}/{repo}/issues`) and write endpoints (`/user/gists`). Path filtering could allow reads but block writes. This is a legitimate use case — but it is better implemented by providing the agent with a **read-only API token** that has no write scopes, rather than relying on a network proxy to block POST requests.

**Scenario 3: Audit and compliance.** In regulated environments, path-level logging may be required to prove which API endpoints were called. This is a logging and compliance requirement, not a security enforcement requirement — and it can be addressed with path-level logging without necessarily enforcing path-based blocks.

**Scenario 4: Preventing SSRF pivot.** An agent with access to an internal HTTP service might use it to proxy requests to internal addresses. Path filtering could limit this. But again, the correct control is network segmentation (the agent cannot reach internal services at all), not path filtering on external services.

**Conclusion:** In each case where path filtering would provide real value, a more targeted control (hostname scoping, IAM/token least privilege, network segmentation) achieves the same outcome without the MITM complexity.

---

## 5. Tools for SNI-Based Filtering Without TLS Inspection

### Nginx stream module (ngx_stream_ssl_preread_module)

Nginx's stream module can parse the SNI field from a TLS `ClientHello` using `ssl_preread` and make routing decisions before proxying the raw TCP stream. This:
- Requires no TLS termination
- Preserves end-to-end encryption
- Supports exact-match and map-based hostname routing
- Can pass-through or reject based on SNI

Configuration is relatively simple — a `stream {}` block with `ssl_preread on` and a `map` directive. However, nginx stream itself has no native policy engine — allow/deny decisions must be encoded as proxy targets (forward allowed hosts, return a TCP RST for blocked ones).

### Envoy SNI dynamic forward proxy

Envoy's `sni_dynamic_forward_proxy` filter reads the SNI field via the TLS Inspector listener filter and uses it to resolve and forward the upstream connection. It supports:
- DNS caching with TTL enforcement
- Per-connection state overrides
- Integration with Envoy's full filter chain (RBAC, rate limiting, access logging)

The documentation marks this as "alpha and not production ready" as of 2025, so operational stability should be validated. The HTTP dynamic forward proxy (which requires TLS termination but enables path-level routing) is more mature.

### iptables with xt_tls kernel module

The `xt_tls` and `xt_tlslist` kernel modules are iptables extensions that parse the TLS `ClientHello` to extract the SNI field, enabling rules like:

```
iptables -A OUTPUT -p tcp --dport 443 -m tls --tls-hostset allowed_hosts -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -j DROP
```

These operate inside network namespaces (compatible with container isolation) and require no userspace proxy. The tradeoff is that kernel module installation may require host privileges not available in all container runtimes, and the modules are not part of the mainline kernel.

### DNS-level enforcement

Filtering at DNS (resolving only allowed hostnames, returning NXDOMAIN for others) is a complementary control that works alongside SNI filtering. It prevents an agent from discovering attacker infrastructure via DNS. However, DNS-only filtering is insufficient because an agent with hardcoded IPs bypasses it entirely. SNI + DNS filtering in combination is stronger than either alone.

---

## 6. Forward Proxy Options for TLS Inspection: Comparison

If path-level filtering is decided to be required despite the above, here is a practical comparison:

| Dimension | Squid (ssl-bump) | mitmproxy | Envoy (HTTP forward proxy) |
|---|---|---|---|
| **TLS termination** | Yes | Yes | Yes |
| **Path filtering** | ACL rules | Python scripting | Lua filters / route config |
| **Performance** | Medium | Low-Medium (Python GIL) | High (C++) |
| **Certificate management** | Manual / OpenSSL | Built-in CA generation | External PKI integration |
| **Memory per connection** | High (GBs at scale) | Moderate | Low-medium |
| **Config complexity** | High ("black magic") | Moderate | High (YAML verbosity) |
| **Cert pinning breakage** | Yes | Yes | Yes |
| **mTLS support** | Partial | Partial | Full (but complex) |
| **Container-native** | No (VM-era design) | Yes (Python, flexible) | Yes (cloud-native) |
| **Production maturity** | High (decades) | Medium (dev tool origins) | High (HTTP proxy) / Low (SNI passthrough) |

For a sandbox with O(10) allowed hostnames, **mitmproxy** is the most operationally accessible option if TLS inspection is required. For production at scale, Envoy's HTTP dynamic forward proxy is preferred despite configuration complexity.

---

## 7. Real-World Deployment Patterns

### Enterprise egress security

Corporate security tools (Zscaler, Netskope, Cisco Umbrella, Cloudflare Gateway) universally offer TLS inspection as the mechanism for path and content-level policy enforcement. They deploy CA certificates through endpoint management (MDM, Group Policy). In this context, the CA is a corporate trust anchor installed before the device is provisioned — not injected at runtime into a sandbox.

Cloudflare Gateway's architecture illustrates the bifurcation cleanly: without TLS inspection, network policies can enforce on SNI, destination IP, user identity, and device posture. With TLS inspection, HTTP policies add URL, path, request body, DLP scanning, and remote browser isolation. The additional controls from TLS inspection are real — but they are designed for a managed device fleet, not an adversarial sandbox.

### CI/CD egress filtering (Actuated)

Actuated's egress filtering for CI microVMs uses hostname-level domain whitelisting with DNS co-filtering — precisely the architecture recommended here. They explicitly chose to avoid enterprise proxy solutions (Cisco Umbrella, Zscaler) as "costly" and operationally inappropriate for ephemeral build environments. Their allowlist includes specific hostnames (`api.github.com`, `*.actions.githubusercontent.com`, etc.) with no path-level granularity.

### AI agent sandboxes (Replicate, Northflank, Cloudflare)

Current-generation AI sandbox platforms (as of 2025–2026) universally use default-deny egress with explicit hostname allowlists — not TLS inspection. Cloudflare's sandbox auth model uses per-sandbox ephemeral CA certificates for credential injection but not for traffic inspection. The pattern is: network isolation first, then limited egress to declared API endpoints.

---

## 8. The CA Cert Injection Attack Surface

This is the pivotal security consideration.

A TLS inspection proxy operating inside or adjacent to the container sandbox must hold a CA private key that, if extracted, allows any TLS certificate for any domain to be forged. For desktop enterprise deployments, this key lives on a hardened appliance that employees cannot access. For a container sandbox, the situation is fundamentally different:

**Attack vectors for key extraction:**

- **Environment variables.** If the CA private key is passed as an environment variable (a common Kubernetes pattern for secrets), any process in the container can read it from `/proc/self/environ` or the application environment.
- **Mounted secret files.** Mounted secrets are files on the container filesystem. An agent that can read arbitrary filesystem paths can read the key.
- **Prompt injection.** Research demonstrates that private keys can be extracted from sandboxed LLM environments in under five minutes via prompt injection attacks. If the agent can be instructed to read and relay file contents, a mounted CA key is a direct exfiltration target.
- **Process introspection.** An agent with shell access can enumerate running processes and their open files, potentially locating the proxy process and its key material.

**What an extracted CA key enables:**

- Forging TLS certificates trusted by any process in the sandbox that uses the injected CA trust store
- MITM-ing the agent's own TLS connections from inside the sandbox (subverting the inspection proxy's purpose)
- If the key escapes the sandbox (through exfiltration), forging certificates trusted by any system that was provisioned with the same CA

The NSA advisory on TLS inspection explicitly warns: "An adversary can focus their exploitation efforts on a single device where potential traffic of interest is decrypted, rather than try to exploit each location where the data is stored." For a sandbox with a single inspection point, this is precisely the threat model.

**Conclusion:** Injecting a CA cert and key into an adversarial container creates a high-value cryptographic target co-located with an adversarial process. The attack surface introduced (key extraction leading to arbitrary certificate forgery) is plausibly worse than the surface closed (path-level filtering of allowed hostnames).

---

## 9. For the Specific Use Case: Agentic Sandbox with Role-Based Allowlists

The threat model for this project is:

- An adversarial agent (possibly compromised by prompt injection or running malicious code)
- Operating in a container with a role-specific allowlist (e.g., "this agent may call GitHub and npm APIs")
- Attempting to exfiltrate data, establish C2, or pivot to other systems

**What hostname filtering addresses:**
- Connections to any destination not in the role allowlist — ✓ blocked
- Exfiltration to attacker infrastructure — ✓ blocked (if attacker domain is not allowed)
- Reverse shell establishment — ✓ blocked (if C2 domain is not allowed)
- Lateral movement to internal services — ✓ blocked with network segmentation

**What hostname filtering does not address:**
- Exfiltration through semantics of allowed services (e.g., writing to a GitHub Gist)
- This is better addressed by: least-privilege API tokens, auditing egress content at the application layer, and behavioral monitoring

**What path filtering would add:**
- Restricting the agent to specific API endpoints on allowed hostnames
- This is functionally equivalent to API token scoping — achievable without a proxy

**What path filtering would cost:**
- CA cert co-located with adversarial process (key extraction risk)
- Certificate compatibility issues (pinning, mTLS)
- Operational complexity for a narrow allowlist
- Performance overhead

**Decision:** Hostname/SNI-level filtering is the right granularity. Complement it with:
1. Precise hostname allowlists (no wildcard domains unless necessary; `specific-bucket.s3.amazonaws.com`, not `*.s3.amazonaws.com`)
2. DNS filtering through the same egress proxy
3. HTTPS-only enforcement (block port 80 and non-443 TCP)
4. Least-privilege API tokens for allowed services (don't grant write access if read is sufficient)
5. Egress logging at the SNI level for audit and anomaly detection
6. Rate limiting on egress connections to detect data-dump behavior

---

## Sources

- [TLS decryption — Cloudflare One docs](https://developers.cloudflare.com/cloudflare-one/traffic-policies/network-policies/)
- [AWS Network Firewall: Filter outbound HTTPS traffic with SNI (Amazon EKS)](https://aws.amazon.com/blogs/security/use-aws-network-firewall-to-filter-outbound-https-traffic-from-applications-hosted-on-amazon-eks/)
- [AWS Network Firewall Egress Filtering Bypass — Hacking The Cloud](https://hackingthe.cloud/aws/post_exploitation/network-firewall-egress-filtering-bypass/)
- [TLS inspection configuration for encrypted egress — AWS Network Firewall](https://aws.amazon.com/blogs/security/tls-inspection-configuration-for-encrypted-egress-traffic-and-aws-network-firewall/)
- [How mitmproxy works — mitmproxy docs](https://docs.mitmproxy.org/stable/concepts/how-mitmproxy-works/)
- [SSL Inspection Comes with Great Responsibility — Zscaler](https://www.zscaler.com/blogs/product-insights/ssl-inspection-comes-great-responsibility)
- [The NSA Warns of TLS Inspection — Schneier on Security](https://www.schneier.com/blog/archives/2019/11/the_nsa_warns_o.html)
- [Managing Risk from TLS Inspection — NSA Information Sheet](https://media.defense.gov/2019/Dec/16/2002225460/-1/-1/0/INFO%20SHEET%20%20MANAGING%20RISK%20FROM%20TRANSPORT%20LAYER%20SECURITY%20INSPECTION.PDF)
- [The Sorry State of TLS Security in Enterprise Interception Appliances — ACM](https://dl.acm.org/doi/fullHtml/10.1145/3372802)
- [Encrypted Client Hello — Cloudflare Blog](https://blog.cloudflare.com/announcing-encrypted-client-hello/)
- [Encrypted Client Hello Defense Strategies — Cisco Secure Firewall](https://secure.cisco.com/secure-firewall/docs/encrypted-client-hello-defense-strategies-how-cisco-secure-firewall-tackles-ech)
- [SNI dynamic forward proxy — Envoy documentation](https://www.envoyproxy.io/docs/envoy/latest/configuration/listeners/network_filters/sni_dynamic_forward_proxy_filter)
- [Dynamic forward proxy — Envoy documentation](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/dynamic_forward_proxy_filter)
- [Features: SSL Bump — Squid Web Cache wiki](https://wiki.squid-cache.org/Features/SslBump)
- [Practical Security Guidance for Sandboxing Agentic Workflows — NVIDIA Technical Blog](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)
- [Sandbox Patterns — AI Runtime Security](https://airuntimesecurity.io/infrastructure/agentic/sandbox-patterns/)
- [How to sandbox AI agents in 2026: MicroVMs, gVisor & isolation strategies — Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Containers, Agents: Secure credential injection and dynamic egress policies — Cloudflare Community](https://community.cloudflare.com/t/containers-agents-secure-credential-injection-and-dynamic-egress-policies-for-sandboxes/918586)
- [Egress Filtering for CI to mitigate data exfiltration — Actuated](https://actuated.com/blog/egress-filtering)
- [Webhook Party: Malicious packages caught exfiltrating data via legit webhook services — Checkmarx](https://checkmarx.com/blog/webhook-party-malicious-packages-caught-exfiltrating-data-via-legit-webhook-services/)
- [Exfiltration Over Webhook (T1567.004) — MITRE ATT&CK](https://attack.mitre.org/techniques/T1567/004/)
- [Silent Egress: When Implicit Prompt Injection Makes LLM Agents Leak Without a Trace — arXiv](https://arxiv.org/html/2602.22450)
- [xt_tls: Filter TLS traffic with iptables — GitHub (Lochnair)](https://github.com/Lochnair/xt_tls)
- [xt_tlslist: iptables extension for TLS hostname filtering — GitHub (gibbon4ik)](https://github.com/gibbon4ik/xt_tlslist)
- [nginx TLS SNI routing based on subdomain pattern — GitHub Gist](https://gist.github.com/kekru/c09dbab5e78bf76402966b13fa72b9d2)
- [Understanding SNI in NGINX Reverse Proxies — Medium](https://medium.com/@sandeeppesala123/understanding-sni-in-nginx-reverse-proxies-a-practical-guide-6bb54a839114)
- [Envoy Dynamic Forward Proxy with Downstream SNI for Google APIs — blog.salrashid.dev](https://blog.salrashid.dev/articles/2022/envoy_dynamic_forward_proxy_with_sni/)
- [Server Name Indication — Wikipedia](https://en.wikipedia.org/wiki/Server_Name_Indication)
- [What is Encrypted SNI? — Cloudflare Learning](https://www.cloudflare.com/learning/ssl/what-is-encrypted-sni/)
- [fluxzy CLI benchmark vs mitmproxy / Squid — fluxzy.io](https://www.fluxzy.io/resources/blogs/performance-benchmark-fluxzy-mitmproxy-mitmdump-squid)
- [Control which domains your AI agents can access — AWS Machine Learning Blog](https://aws.amazon.com/blogs/machine-learning/control-which-domains-your-ai-agents-can-access/)
