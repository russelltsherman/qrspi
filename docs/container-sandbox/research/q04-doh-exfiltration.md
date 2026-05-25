# Q4: DNS-over-HTTPS (DoH) Exfiltration Risk

## Summary and Recommendation

**Risk level: Medium — address with a layered response, not a single mitigation.**

DNS-over-HTTPS is a real exfiltration vector that bypasses traditional DNS filtering, including a controlled resolver that returns NXDOMAIN for non-allowlisted domains. An adversarial agent can circumvent that control entirely by sending DNS queries as HTTPS requests directly to a public DoH provider (Cloudflare 1.1.1.1, Google 8.8.8.8, etc.) on port 443, where the traffic is indistinguishable from ordinary web browsing at the packet level.

The recommended mitigation for a container sandbox is a combination of:

1. **Allowlist-only HTTPS egress** — block all outbound TCP/443 except explicitly approved destinations. This is the single control that subsumes the DoH threat, the DoT threat, direct-IP HTTPS exfiltration, and most other encrypted tunnel variants. If you are already doing this for your general threat model, DoH is already mitigated.
2. **Explicit DoT block** — drop all outbound TCP/UDP port 853 (a one-line iptables rule).
3. **Known DoH provider IP block as defense-in-depth** — maintain an ipset of major provider IPs (Cloudflare, Google, Quad9, Mullvad, NextDNS, AdGuard) and block TCP/443 to them. This is not sufficient on its own but is low-cost and raises the bar.
4. **Post-hoc DNS audit logging** — log all DNS queries made to the controlled resolver; anomalously high entropy or volume in subdomains indicates traditional DNS tunneling. DoH to an allowlisted domain requires that domain to have been explicitly permitted, which limits the attack surface.

For short-lived containers (sub-10-minute lifetime) the realistic exfiltration bandwidth via DNS tunneling is low enough (a few KB/min through a controlled resolver) that the primary risk is DoH to an unblocked public resolver. If the HTTPS allowlist is tight, this risk collapses.

**The risk is material and worth addressing. The recommended mitigation cost is low.**

---

## 1. How DNS-over-HTTPS Works and Why It Bypasses Traditional DNS Filtering

Traditional DNS resolves names over UDP/TCP port 53, unencrypted. Network defenders can:
- Redirect all port-53 traffic to a controlled resolver (DNAT iptables rule)
- Inspect query contents in plaintext
- Return NXDOMAIN for non-allowlisted domains

DNS-over-HTTPS (DoH), standardized in RFC 8484 (2018), wraps DNS wire-format messages in HTTP/2 POST or GET requests sent over TLS to port 443. The DNS payload is transported as the HTTP body with content type `application/dns-message`. The target URL follows the pattern `https://<resolver>/dns-query`.

Because this uses port 443 — the same port as all HTTPS web traffic — it is invisible to any network control that operates at the transport layer (IP/port). The only network-layer signal available to a firewall without TLS interception is:
- The destination IP address
- The TLS SNI field (in the ClientHello handshake), which names the resolver host before encryption

When a resolver uses Encrypted Client Hello (ECH, standardized in TLS 1.3 extensions), even the SNI is encrypted, eliminating that signal entirely. ECH deployment is nascent but growing.

The practical consequence for container egress filtering: a DNAT rule that redirects port 53 to a controlled resolver has zero effect on DoH traffic. The agent connects directly to 1.1.1.1:443 or 8.8.8.8:443 without using the controlled resolver at all.

**Sources:**
- [Cloudflare: DNS over TLS vs. DNS over HTTPS](https://www.cloudflare.com/learning/dns/dns-over-tls/)
- [Cloudflare: DNS Encryption Explained](https://blog.cloudflare.com/dns-encryption-explained/)
- [DNS over TLS - Wikipedia](https://en.wikipedia.org/wiki/DNS_over_TLS)

---

## 2. Traditional DNS Exfiltration: Encoding, Volume, and Entropy

Before examining DoH, it is worth understanding the traditional DNS exfiltration problem the controlled resolver is designed to address.

### Encoding Technique

Data is base32 or base64 encoded and embedded as subdomains of a domain the attacker controls. Example:
```
aGVsbG8gd29ybGQ.ns1.attacker.com
```
The authoritative nameserver for `attacker.com` receives the query, decodes the subdomain, and reassembles the original data. Tools include dnscat2, iodine, DNSExfiltrator, and many custom implementations.

Key constraints per query:
- Maximum DNS name length: 253 characters total
- Maximum label (subdomain segment) length: 63 characters
- Base64 overhead: ~1.33x (0.75 bytes of data per encoded character)
- Practical data per query: ~150–180 bytes after encoding and label framing

### Bandwidth

Published measurements:
- Controlled/realistic environments: **4 KB/s** (40 bytes/query × 100 queries/second)
- Practical stealth-mode operation: **50–200 KB/hour** (low rate to evade anomaly detection)
- Optimized lab environments (iodine raw mode to a cooperating resolver): up to 50 Mbit/s
- Typical adversarial rate for covert exfiltration: ~1–2 minutes per 50 KB

For a 10-minute container lifetime at stealth rates: roughly 8–33 KB of data exfiltrable via traditional DNS without triggering rate alerts. This is a meaningful constraint on what can be stolen but is not zero.

### Detection Signals for Traditional DNS Exfiltration

The controlled resolver captures all port-53 traffic, enabling these detection methods:

| Signal | Threshold indicating tunneling | Notes |
|--------|-------------------------------|-------|
| Shannon entropy of subdomain | > 4.0 bits/char | Legitimate domains rarely exceed this |
| Average subdomain label length | > 50 characters | Normal: ~10–15 chars |
| Query volume per domain per minute | Unusual spike | Highly domain-specific baseline needed |
| Record types used | High proportion of TXT, NULL records | Normal traffic is predominantly A/AAAA |
| TTL values | Near-zero TTL | Avoids caching to maintain live channel |
| Response time delta | > 50ms sustained | Authoritative resolver processing data |
| New unique subdomains per domain | Large count in short window | Fingerprints exfiltration session |

These signals are effective because they operate at the resolver where traffic is plaintext. Research using the Elastic Stack demonstrated these detection thresholds with high accuracy in lab settings.

**Sources:**
- [DNS Tunnelling, Exfiltration and Detection over Cloud Environments (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007605/)
- [Palo Alto Unit 42: DNS Tunneling how DNS can be abused](https://unit42.paloaltonetworks.com/dns-tunneling-how-dns-can-be-abused-by-malicious-actors/)
- [Splunk: Detect DNS Data Exfiltration Using Deep Learning](https://www.splunk.com/en_us/blog/security/machine-learning-in-security-detect-dns-data-exfiltration-using-deep-learning.html)
- [Akamai: Detecting Low Throughput Malicious DNS Exfiltration](https://blogs.akamai.com/2018/04/effectively-detecting-low-throughput-and-malicious-dns-exfiltration.html)
- [CyberDefenders: DNS Tunneling Detection Techniques](https://cyberdefenders.org/blog/dns-tunneling-detection/)

---

## 3. DNS Exfiltration via DoH: Why It Is Harder to Detect and Block

### The Core Problem

When an agent uses DoH, it does not make a query to the controlled resolver at all. The DNS payload is sent inside an HTTPS session to a public resolver's IP on port 443. From the network's perspective, this looks identical to the agent loading a web page from Cloudflare's CDN.

There is no plaintext query for the controlled resolver to see. The NXDOMAIN filtering strategy is completely bypassed.

### Detection Challenges Without TLS Interception

Without terminating the TLS session (man-in-the-middle), an observer can only see:
- Destination IP (may be a shared CDN IP hosting both DoH and legitimate content)
- SNI hostname in the TLS ClientHello (visible until ECH is deployed)
- TCP session metadata: timing, size distributions, connection frequency

DoH traffic is not distinguishable from regular HTTPS at the packet level without decryption. Even with TLS interception, identifying exfiltration within DoH requires analyzing the decrypted DNS query contents for high-entropy subdomains — essentially the same analysis applied to traditional DNS, but with the added overhead of a MITM proxy.

### DoH Exfiltration Rate

The per-query data capacity is the same as traditional DNS tunneling (subdomains are still constrained to DNS label limits). The difference is the transport: DoH typically uses HTTP/2 which supports multiplexing, allowing many queries in a single TLS connection. An adversary using DoH can achieve the same ~4 KB/s rate as traditional DNS tunneling, but with no risk of detection at the resolver level.

The adversary trades traditional-DNS detectability for DoH obscurity. The bandwidth is similar; the detection surface is far smaller.

**Sources:**
- [Infosec Institute: Bypassing Security Products via DNS Data Exfiltration](https://www.infosecinstitute.com/resources/general-security/bypassing-security-products-via-dns-data-exfiltration/)
- [DeepStrike: What Is DNS Data Exfiltration?](https://deepstrike.io/blog/what-is-dns-data-exfiltration)
- [ACM: Detecting DNS over HTTPS based data exfiltration](https://dl.acm.org/doi/abs/10.1016/j.comnet.2022.108919)

---

## 4. Real-World Examples of DoH Used for Exfiltration and C2

### ChamelDoH (ChamelGang, 2022–2023)

The most documented real-world case of DoH-based C2 and exfiltration. ChamelDoH is a C++ Linux implant attributed to the Chinese APT group ChamelGang, targeting energy, aviation, and government organizations.

**Technical mechanism:**
1. Data is AES-128 encrypted and base64 encoded
2. The encoded payload is prepended as a subdomain: `<encoded_data>.ns2.attacker.com`
3. A DoH query is made to a public resolver (Cloudflare or Google) requesting TXT records for that subdomain
4. The public DoH resolver forwards the query to the attacker's authoritative nameserver
5. The attacker's nameserver returns response data encoded in the TXT record
6. The agent receives the response through the same DoH channel

The TXT record type is chosen because it carries larger payloads than A records. Ten ChamelDoH samples were confirmed in VirusTotal.

**Why it evaded detection:** DoH providers cannot feasibly be blocked enterprise-wide without disrupting legitimate traffic. HTTPS prevents inspection without MITM. The traffic destination (1.1.1.1 or 8.8.8.8) appears in every organization's logs as routine.

### DNSExfiltrator (Red Team Tool)

The open-source tool DNSExfiltrator explicitly supports DoH mode, using Google's or Cloudflare's DoH APIs as the transport. This is a documented red team technique, not just theoretical. It is available on GitHub and used in penetration testing engagements.

### OilRig/APT34

Iran-attributed APT group OilRig has used DNS tunneling for C2 in multiple campaigns. Observed TTPs include: reusing long-lived TLS sessions to major public resolvers, chunking payloads to fit DNS label constraints, using HTTP/2 multiplexing to batch queries, and jittered timing and padding to evade volume-based detection.

**Sources:**
- [Stairwell: ChamelGang and ChamelDoH - A DNS-over-HTTPS implant](https://stairwell.com/resources/chamelgang-and-chameldoh-a-dns-over-https-implant/)
- [BleepingComputer: Chinese hackers use DNS-over-HTTPS for Linux malware](https://www.bleepingcomputer.com/news/security/chinese-hackers-use-dns-over-https-for-linux-malware-communication/)
- [The Hacker News: ChamelDoH New Linux Backdoor Utilizing DNS-over-HTTPS](https://thehackernews.com/2023/06/chameldoh-new-linux-backdoor-utilizing.html?m=1)
- [GitHub: DNSExfiltrator - Data exfiltration over DNS covert channel](https://github.com/Arno0x/DNSExfiltrator)
- [NEC Security Blog: ChamelDoH Tunnelling or DNS-over-HTTPS](https://www.nec.com/en/global/solutions/cybersecurity/blog/240920/index.html)

---

## 5. Practical Mitigations

### 5.1 Allowlist-Only HTTPS Egress (Recommended Primary Control)

The most effective and architecturally clean mitigation is to block all outbound TCP/443 except to explicitly allowlisted destination IPs or domains. This control:
- Catches DoH to any provider not on the allowlist (including unknown/future providers)
- Catches direct-IP HTTPS exfiltration channels
- Does not require maintaining a blocklist of DoH providers
- Aligns with the existing iptables egress filtering architecture described in the threat model

If a domain is on the allowlist, an agent can still use that domain's DoH endpoint if the domain happens to operate one. This residual risk is limited to allowlisted domains — which are, by definition, expected outbound destinations. An agent exfiltrating data via DoH to `cloudflare.com` (if allowlisted) is a different threat scenario (content-level exfiltration over an approved channel) not uniquely addressed by DNS controls.

### 5.2 Block All Outbound Port 853 (DoT)

DNS-over-TLS (DoT) uses a dedicated port: TCP/853. Unlike DoH, this can be blocked with a single iptables rule:
```
iptables -A OUTPUT -p tcp --dport 853 -j DROP
```
This has no collateral impact on legitimate HTTPS traffic. DoT is therefore easier to block than DoH and should be blocked unconditionally.

### 5.3 Known DoH Provider IP Blocklist (Defense-in-Depth)

As a supplementary control, maintain an ipset of known DoH provider IPs and block TCP/443 to them. Major providers and their IPs:

| Provider | IPv4 Addresses |
|----------|---------------|
| Cloudflare | 1.1.1.1, 1.0.0.1, 1.1.1.2, 1.1.1.3 |
| Google | 8.8.8.8, 8.8.4.4 |
| Quad9 | 9.9.9.9, 149.112.112.112 |
| OpenDNS | 208.67.220.220, 208.67.222.222 |
| Mullvad | (multiple, see provider docs) |
| NextDNS | (multiple, see provider docs) |
| AdGuard | 94.140.14.14, 94.140.15.15 |

The Hagezi `dns-blocklists` project (GitHub) maintains a curated FQDN-level encrypted DNS bypass list with approximately **3,941 entries** covering DoH, DoT, and DoQ providers, updated daily. This is the most maintainable community-sourced reference available.

**Maintainability assessment:** This is a real operational burden. DoH providers change IPs, new providers emerge, CDN-hosted providers share IPs with legitimate content. The NxFilter community list documents 250+ IPs; the Hagezi domain list covers ~3,941 domains. Neither is complete or stable. IP-only blocking is particularly fragile for CDN-hosted resolvers (e.g., Cloudflare DoH and Cloudflare CDN share IP ranges). **This control should not be relied on as the sole mitigation.**

### 5.4 DNS-over-QUIC and DNS-over-TLS Comparison

| Protocol | Port | Blockability | Notes |
|----------|------|-------------|-------|
| Traditional DNS | 53 (UDP/TCP) | Easy — redirect or drop port 53 | Already handled by controlled resolver |
| DoT | 853 (TCP) | Easy — drop port 853 | Single iptables rule |
| DoH | 443 (TCP) | Hard — shared with all HTTPS | Requires allowlist or IP blocklist |
| DoQ | 853 (UDP) | Medium — port 853 UDP | Drop UDP/853 alongside TCP/853 |

DoT is far easier to block than DoH precisely because of its dedicated port. From a defender's perspective, if an organization could have standardized on DoT instead of DoH, the blocking problem would be trivial. The choice of port 443 for DoH was made to ensure DoH survives in restrictive networks — which is exactly what makes it difficult to block in security contexts.

**Sources:**
- [CleanBrowsing: How to Prevent DNS Filter Bypass](https://cleanbrowsing.org/learn/how-to-prevent-filter-bypass)
- [Cloudflare: DNS over TLS vs. DNS over HTTPS](https://www.cloudflare.com/learning/dns/dns-over-tls/)
- [DNS over TLS vs DNS over HTTPS — DNSFilter](https://help.dnsfilter.com/hc/en-us/articles/4415250133779-DNS-over-TLS-vs-DNS-over-HTTPS)
- [NxFilter: List of DNS over HTTPS server IPs to block](https://nxfilter.org/archive/list-of-dns-over-https-doh-server-ips-to-be-blocked-by-your-firewall.html)
- [GitHub: Hagezi dns-blocklists](https://github.com/hagezi/dns-blocklists)
- [Pi-hole: DNS-over-HTTPS DoH Blocklist](https://discourse.pi-hole.net/t/dns-over-https-doh-blocklist/73182)
- [GitHub: ckuethe DNS-over-HTTPS Block List](https://gist.github.com/ckuethe/f71185f604be9cde370e702aa179fc2e)

---

## 6. How Enterprise Security Tools Handle DoH

### NSA Guidance (2021)

NSA's "Adopting Encrypted DNS in Enterprise Environments" guidance (January 2021) takes a pragmatic position:
- Enterprises should **designate an internal DoH resolver** and block external DoH providers
- Block TCP/443 to known DoH provider IPs for unmanaged endpoints
- Use browser/OS group policies to disable DoH on managed endpoints
- Deploy decrypting TLS inspection proxies for comprehensive visibility

The NSA explicitly recommends that enterprises not rely on clients self-selecting DoH endpoints, as this undermines enterprise DNS policy and security monitoring.

### CISA Guidance (2024)

CISA's Encrypted DNS Implementation Guidance (April 2024) mandates federal agencies route all encrypted DNS through CISA's Protective DNS (PDNS) service. Key points:
- Encrypted DNS traffic should go to a monitored, enterprise-controlled resolver
- Organizations should use CISA's PDNS for egress DNS resolution
- PDNS provides interactive dashboards, anomaly alerting, and policy controls

This guidance is consistent with the controlled-resolver architecture in the container sandbox threat model — the container should be forced through a controlled encrypted resolver rather than being allowed to choose its own.

### Cisco Umbrella

Umbrella operates as a DNS-layer security product. Its Roaming Client intercepts DNS queries on endpoints and routes them through Umbrella's resolvers. It does not inherently block DoH — it is itself a DoH provider. Umbrella addresses the DoH bypass problem by also deploying as an HTTPS proxy on endpoints to intercept DoH traffic, but this requires endpoint agent deployment (not applicable in container contexts).

### Zscaler

Zscaler Internet Access (ZIA) is a cloud-native Secure Web Gateway using a proxy architecture. All outbound HTTPS is routed through Zscaler's proxy, which performs TLS inspection. This effectively intercepts DoH traffic because DoH queries pass through the proxy and can be decoded and inspected. This is the most comprehensive approach but requires redirecting all outbound HTTPS through the proxy — which is architecturally equivalent to the allowlist-only HTTPS egress model with an inspection capability added.

**Sources:**
- [NSA: Adopting Encrypted DNS in Enterprise Environments (PDF)](https://media.defense.gov/2021/Jan/14/2002564889/-1/-1/0/CSI_ADOPTING_ENCRYPTED_DNS_U_OO_102904_21.PDF)
- [CISA: Encrypted DNS Implementation Guidance](https://www.cisa.gov/sites/default/files/2024-05/Encrypted%20DNS%20Implementation%20Guidance_508c.pdf)
- [CISA: Publishes Encrypted DNS Implementation Guidance](https://www.cisa.gov/news-events/news/cisa-publishes-encrypted-dns-implementation-guidance-federal-agencies)
- [SEI CMU: DNS over HTTPS — 3 Strategies for Enterprise Security Monitoring](https://www.sei.cmu.edu/blog/dns-over-https-3-strategies-for-enterprise-security-monitoring/)
- [Dope Security: Zscaler vs Cisco Umbrella comparison](https://dope.security/post/zscaler-vs-cisco-umbrella)

---

## 7. Detection Approaches

### 7.1 At the Network Boundary (Without TLS Interception)

**IP-level blocking with logging:** Log all TCP/443 connection attempts to known DoH provider IPs. Even if you block these IPs, logging them provides forensic evidence of exfiltration attempts.

**SNI inspection:** The TLS ClientHello SNI field names the target host in plaintext (absent ECH). Firewalls can match SNI values against a blocklist of DoH provider hostnames (`dns.google`, `cloudflare-dns.com`, `dns.quad9.net`, etc.) and block or alert on matches. This works until ECH deployment makes SNI encrypted.

**TLS fingerprinting (JA3/JA4):** The TLS handshake parameters (cipher suites, extensions, curves) can fingerprint the client library. DNS libraries making DoH calls may have distinctive handshake profiles. This is a weak signal for generic sandboxing but is used in enterprise NDR products.

**Timing and volume anomalies:** DoH exfiltration to a fixed resolver IP will create a persistent connection or rapid reconnection pattern that differs from normal browsing behavior (which connects to many different IPs). A container making many HTTP/2 requests to a single IP with high throughput is anomalous.

### 7.2 At the DNS Resolver (Traditional DNS Tunneling)

These signals are only visible for traffic that reaches the controlled resolver. DoH traffic bypasses this entirely.

- Shannon entropy of subdomain > 4.0 bits/character
- Subdomain length > 50–60 characters
- High proportion of TXT or NULL record queries
- Near-zero TTL values
- Query rate spikes to a previously unqueried domain

### 7.3 Post-Hoc Audit

Container network flow logs should capture source/destination IP and port for all TCP connections. This enables post-hoc identification of connections to known DoH provider IPs even if the content was encrypted. For short-lived containers, post-hoc audit is a compensating control: it may not prevent exfiltration in a single session, but it enables incident detection and response.

**Sources:**
- [SEI CMU: DNS over HTTPS — 3 Strategies for Enterprise Security Monitoring](https://www.sei.cmu.edu/blog/dns-over-https-3-strategies-for-enterprise-security-monitoring/)
- [Heimdal Security: DNS Tunneling Detection and Prevention](https://heimdalsecurity.com/blog/dns-tunneling/)
- [Fidelis Security: DNS Tunneling Detection and Mitigation](https://fidelissecurity.com/threatgeek/learn/dns-tunneling-detection/)
- [ExtraHop: DNS Tunneling Attack Definition and Prevention](https://www.extrahop.com/resources/attacks/dns-tunneling)

---

## 8. Risk Assessment in Context

### Threat Model Constraints That Reduce Risk

The sandbox design includes several constraints that reduce the practical risk of DoH exfiltration:

**Short container lifetime.** If containers run for seconds to minutes, the exfiltration bandwidth is severely constrained. At 4 KB/s (optimistic DoH rate), a 5-minute container can exfiltrate ~1.2 MB. At realistic stealth rates (~50 KB/hour), a 5-minute window yields ~4 KB. For most workloads, this is not material for secrets (API keys, short strings) but is insufficient for exfiltrating large datasets.

**iptables egress filtering already in place.** The existing architecture blocks non-allowlisted destinations. If DoH providers are not on the allowlist, DoH exfiltration is already blocked by the existing HTTPS egress controls — the controlled DNS resolver is not the relevant control.

**Post-hoc audit capability.** Network flow logs captured after container teardown enable detection of anomalous connections even if they were not blocked in real-time.

**Rate limiting.** If request rate limits are applied at the container level, the exfiltration channel is further constrained.

### Residual Risk Assessment

If the egress control is allowlist-only HTTPS: **DoH risk is very low.** An agent can only reach DoH providers that are explicitly allowlisted. A DoH query to an allowlisted provider is a different threat (content exfiltration via an approved channel) that requires other controls (application-layer monitoring).

If the egress control is an IP-range blocklist (non-allowlist): **DoH risk is medium to high.** The attack surface is the universe of all DoH providers not on the blocklist. As documented above, there are thousands of DoH providers; a blocklist approach is not completable.

If there is no egress filtering beyond the controlled DNS resolver: **DoH risk is high.** An agent can trivially bypass the resolver by using any public DoH provider on port 443, which is likely reachable.

### Accepted Risk Scenarios

The following residual risks may be accepted with justification:

- **DoH to allowlisted CDN domains:** If an allowlisted domain (e.g., `cloudflare.com`) also provides DoH service, an agent can use it for DoH. The risk here is exfiltration via a domain you intended to allow — which requires content-level controls to address.
- **ECH-obscured DoH:** Future deployments where SNI is encrypted eliminate the SNI-based detection signal. This risk is currently low but will increase as ECH deploys.
- **Novel/unknown DoH providers:** Any DoH provider not on a blocklist. Mitigated by allowlist-only HTTPS egress.

---

## 9. Implementation Recommendations for the Container Sandbox

### Minimum Viable Controls (Recommended)

```bash
# 1. Drop all DNS-over-TLS (port 853 TCP and UDP)
iptables -A OUTPUT -p tcp --dport 853 -j DROP
iptables -A OUTPUT -p udp --dport 853 -j DROP

# 2. Allowlist-only HTTPS egress (primary DoH mitigation)
# This rule structure blocks everything and allows only approved destinations
iptables -A OUTPUT -p tcp --dport 443 -m set ! --match-set ALLOWED_HTTPS dst -j DROP

# 3. Defense-in-depth: block known DoH provider IPs even if general HTTPS is open
ipset create DOH_PROVIDERS hash:ip
ipset add DOH_PROVIDERS 1.1.1.1
ipset add DOH_PROVIDERS 1.0.0.1
ipset add DOH_PROVIDERS 8.8.8.8
ipset add DOH_PROVIDERS 8.8.4.4
ipset add DOH_PROVIDERS 9.9.9.9
ipset add DOH_PROVIDERS 94.140.14.14
ipset add DOH_PROVIDERS 94.140.15.15
# ... extend from Hagezi or NxFilter lists
iptables -A OUTPUT -p tcp --dport 443 -m set --match-set DOH_PROVIDERS dst -j DROP
```

### Logging for Post-Hoc Audit

```bash
# Log before dropping to capture forensic evidence
iptables -A OUTPUT -p tcp --dport 443 -m set --match-set DOH_PROVIDERS dst -j LOG --log-prefix "DOH_BLOCKED: "
iptables -A OUTPUT -p tcp --dport 443 -m set --match-set DOH_PROVIDERS dst -j DROP
```

### Controlled DoH Resolver Option

Rather than blocking DoH entirely, an alternative is to run an internal DoH resolver (e.g., `dnsdist`, `CoreDNS`) that:
- Accepts DoH requests on port 443
- Applies the same NXDOMAIN filtering as the traditional resolver
- Logs all queries for audit

Configure an iptables DNAT rule to redirect all TCP/443 connections to the internal DoH resolver when the destination is a known DoH provider. This intercepts DoH rather than blocking it, maintaining the filtering policy.

---

## Sources

- [Stairwell: ChamelGang and ChamelDoH — A DNS-over-HTTPS implant](https://stairwell.com/resources/chamelgang-and-chameldoh-a-dns-over-https-implant/)
- [BleepingComputer: Chinese hackers use DNS-over-HTTPS for Linux malware](https://www.bleepingcomputer.com/news/security/chinese-hackers-use-dns-over-https-for-linux-malware-communication/)
- [The Hacker News: ChamelDoH New Linux Backdoor Utilizing DNS-over-HTTPS](https://thehackernews.com/2023/06/chameldoh-new-linux-backdoor-utilizing.html?m=1)
- [NEC Security Blog: ChamelDoH Tunnelling or DNS-over-HTTPS](https://www.nec.com/en/global/solutions/cybersecurity/blog/240920/index.html)
- [Cloudflare: DNS over TLS vs. DNS over HTTPS](https://www.cloudflare.com/learning/dns/dns-over-tls/)
- [Cloudflare: DNS Encryption Explained](https://blog.cloudflare.com/dns-encryption-explained/)
- [DNS over TLS — Wikipedia](https://en.wikipedia.org/wiki/DNS_over_TLS)
- [Infosec Institute: Bypassing Security Products via DNS Data Exfiltration](https://www.infosecinstitute.com/resources/general-security/bypassing-security-products-via-dns-data-exfiltration/)
- [DeepStrike: What Is DNS Data Exfiltration?](https://deepstrike.io/blog/what-is-dns-data-exfiltration)
- [ACM: Detecting DNS over HTTPS based data exfiltration (Computer Networks 2022)](https://dl.acm.org/doi/abs/10.1016/j.comnet.2022.108919)
- [PMC / MDPI: DNS Tunnelling, Exfiltration and Detection over Cloud Environments](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007605/)
- [Palo Alto Unit 42: DNS Tunneling how DNS can be abused](https://unit42.paloaltonetworks.com/dns-tunneling-how-dns-can-be-abused-by-malicious-actors/)
- [Splunk: Detect DNS Data Exfiltration Using Deep Learning](https://www.splunk.com/en_us/blog/security/machine-learning-in-security-detect-dns-data-exfiltration-using-deep-learning.html)
- [Akamai: Detecting Low Throughput Malicious DNS Exfiltration](https://blogs.akamai.com/2018/04/effectively-detecting-low-throughput-and-malicious-dns-exfiltration.html)
- [CyberDefenders: DNS Tunneling Detection Techniques](https://cyberdefenders.org/blog/dns-tunneling-detection/)
- [CleanBrowsing: How to Prevent DNS Filter Bypass (VPN, DoH and DoT Blocking)](https://cleanbrowsing.org/learn/how-to-prevent-filter-bypass)
- [NxFilter: List of DNS over HTTPS server IPs to block](https://nxfilter.org/archive/list-of-dns-over-https-doh-server-ips-to-be-blocked-by-your-firewall.html)
- [GitHub: Hagezi dns-blocklists](https://github.com/hagezi/dns-blocklists)
- [GitHub: Hagezi DoH domain list (doh.txt, 3,941 entries)](https://github.com/hagezi/dns-blocklists/blob/main/domains/doh.txt)
- [Pi-hole: DNS-over-HTTPS DoH Blocklist](https://discourse.pi-hole.net/t/dns-over-https-doh-blocklist/73182)
- [GitHub: ckuethe DNS-over-HTTPS Block List](https://gist.github.com/ckuethe/f71185f604be9cde370e702aa179fc2e)
- [SEI CMU: DNS over HTTPS — 3 Strategies for Enterprise Security Monitoring](https://www.sei.cmu.edu/blog/dns-over-https-3-strategies-for-enterprise-security-monitoring/)
- [NSA: Adopting Encrypted DNS in Enterprise Environments (PDF)](https://media.defense.gov/2021/Jan/14/2002564889/-1/-1/0/CSI_ADOPTING_ENCRYPTED_DNS_U_OO_102904_21.PDF)
- [CISA: Encrypted DNS Implementation Guidance (PDF, 2024)](https://www.cisa.gov/sites/default/files/2024-05/Encrypted%20DNS%20Implementation%20Guidance_508c.pdf)
- [CISA: Publishes Encrypted DNS Implementation Guidance](https://www.cisa.gov/news-events/news/cisa-publishes-encrypted-dns-implementation-guidance-federal-agencies)
- [NSA Guidance Release via CISA (2021)](https://www.cisa.gov/news-events/alerts/2021/01/15/nsa-releases-guidance-encrypted-dns-enterprise-environments)
- [Heimdal Security: DNS Tunneling Detection and Prevention](https://heimdalsecurity.com/blog/dns-tunneling/)
- [Fidelis Security: DNS Tunneling Detection and Mitigation](https://fidelissecurity.com/threatgeek/learn/dns-tunneling-detection/)
- [ExtraHop: DNS Tunneling Attack Definition and Prevention](https://www.extrahop.com/resources/attacks/dns-tunneling)
- [MITRE ATT&CK: Exfiltration Over Alternative Protocol T1048](https://attack.mitre.org/techniques/T1048/)
- [GitHub: DNSExfiltrator — Data exfiltration over DNS covert channel](https://github.com/Arno0x/DNSExfiltrator)
- [Vercara: DNS Infiltration and Exfiltration](https://vercara.digicert.com/resources/dns-infiltration-and-exfiltration)
- [Catchpoint: DNS over HTTPS vs TLS — Key Concepts](https://www.catchpoint.com/http2-vs-http3/dns-over-https-vs-tls)
- [Northflank: How to sandbox AI agents 2026](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [DEV Community: Application-Layer Defense — Stopping Exfiltration Inside the Sandbox](https://dev.to/uenyioha/application-layer-defense-stopping-exfiltration-inside-the-sandbox-4l6c)
- [AWS: Control which domains your AI agents can access](https://aws.amazon.com/blogs/machine-learning/control-which-domains-your-ai-agents-can-access/)
- [Performance Characteristics of DNS Tunneling](https://blog.safedns.com/performance-characteristics-of-dns-tunneling/)
- [DNS Tunneling Threat Landscape and Improved Detection (arxiv 2025)](https://arxiv.org/html/2507.10267v1)
