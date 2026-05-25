# Q8: GitHub App Installation Tokens — Generation and Injection

## Summary and Recommendation

**Use a single GitHub App installed per organization (or enterprise), scoped to specific repos at invocation time.**

For a container sandbox that needs short-lived git credentials per agent invocation, GitHub App installation tokens are the correct mechanism. They are:

- **Short-lived**: expire in exactly 1 hour, hard limit set by GitHub
- **Narrowly scopeable**: can be restricted to a single repository at token generation time, even if the App installation covers the whole org
- **Machine-owned**: not tied to any human user account, do not consume a GitHub seat
- **Programmatically generated**: the full flow (JWT → installation token) can be automated in ~200 ms with a simple HTTP call
- **Auditable**: all activity appears in audit logs under the App's identity, not a user's

**Recommended architecture:**

1. Register one GitHub App per GitHub organization (or one enterprise-owned App for multi-org environments)
2. Install it with org-wide access but use per-invocation repository scoping when generating tokens
3. Store the App's private key in a secrets manager (HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager) outside all containers
4. At agent container invocation time, the orchestrator (not the container) fetches the private key, generates a JWT, exchanges it for a per-repo installation token, and injects the token into the container as a mounted secret or environment variable
5. The token expires automatically after 1 hour, ensuring it cannot be reused after the task completes

**Do not use:** deploy keys (no API access, cannot create PRs), classic PATs (user-bound, long-lived), fine-grained PATs (still user-bound, org-level automation limitations), or OAuth App tokens (overly broad scope).

---

## 1. GitHub App Installation Token Mechanics

### What They Are

A GitHub App installation token is a short-lived bearer token that authenticates the App as an installed entity on a specific user account or organization. It is distinct from:

- **JWT (JSON Web Token)**: used only to authenticate the App itself to the GitHub API (10-minute max lifetime), not for git operations
- **User access token**: authenticates a human user who has authorized the App via OAuth
- **Installation access token**: authenticates the App acting on behalf of its installation — this is the token used for git and API operations

### The Two-Token Flow

Generating an installation token is a two-step process:

**Step 1 — Generate a JWT (App → GitHub API auth):**

```
Header:  { "alg": "RS256", "typ": "JWT" }
Payload: {
  "iat": <now - 60 seconds>,   // issued at, backdated for clock skew
  "exp": <now + 600 seconds>,  // expires in 10 minutes, hard GitHub max
  "iss": "<app-client-id>"     // GitHub App's client ID (preferred over app ID)
}
Signed with: App's RSA private key (PEM), using RS256
```

The 60-second backdate on `iat` is required by GitHub to tolerate clock drift. The JWT itself must not exceed 10 minutes lifetime.

**Step 2 — Exchange JWT for installation token:**

```http
POST /app/installations/{installation_id}/access_tokens
Authorization: Bearer {JWT}
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28

{
  "repositories": ["my-repo"],          // optional: restrict to specific repos
  "permissions": {
    "contents": "write",
    "pull_requests": "write"
  }
}
```

Response includes:
```json
{
  "token": "ghs_...",
  "expires_at": "2024-01-01T13:00:00Z",
  "permissions": { "contents": "write", "pull_requests": "write" },
  "repositories": [...]
}
```

### Token Properties

| Property | Value |
|----------|-------|
| Lifetime | Exactly 1 hour (non-configurable) |
| Format | Bearer token (`ghs_...` prefix) |
| Scope | Can be restricted to specific repos and permissions at generation time |
| Upper bound | Cannot exceed the permissions the App installation was granted |
| Attribution | Activity logged as App identity in audit logs |
| Rate limit | 15,000 requests/hour per installation (vs 5,000 for PATs) |

### Using the Token for Git Operations

The token is used as an HTTPS password with the conventional username `x-access-token`:

```bash
git clone https://x-access-token:${TOKEN}@github.com/owner/repo.git
git push https://x-access-token:${TOKEN}@github.com/owner/repo.git
```

GitHub's API documentation confirms: "Your app must have the `Contents` repository permission. You can then use the installation access token as the HTTP password."

The `x-access-token` username string is conventional — GitHub ignores the username field when a valid installation token is provided in the password slot.

---

## 2. Step-by-Step: Creating and Installing a GitHub App

### Step 1: Register the App

Navigate to: **GitHub.com → Organization Settings → Developer Settings → GitHub Apps → New GitHub App**

Required fields:
- **App name**: e.g., `my-org-agent-runner`
- **Homepage URL**: your org or tool URL
- **Webhooks**: disable (uncheck "Active") unless needed — agents don't need webhooks
- **Permissions**: set minimum permissions (see Section 5)
- **Where can this GitHub App be installed?**: choose "Only on this account" for org-scoped, or "Any account" if multi-org (then use separate installation tokens per org)

After creation, note:
- **App ID** (numeric)
- **Client ID** (string, `Iv1.xxx...`) — use this as the `iss` claim in JWTs

### Step 2: Generate a Private Key

On the App's settings page → "Private keys" → **Generate a private key**

A `.pem` file downloads immediately. GitHub stores only the public portion. The PEM file must be stored securely immediately — it cannot be retrieved again.

You may have up to 25 active private keys simultaneously, enabling zero-downtime rotation.

### Step 3: Install the App

On the App's settings page → **Install App** → select your organization → choose:
- "All repositories" — easier to manage, then scope per-token at invocation time
- "Only select repositories" — harder to maintain as repos are added

Note the **Installation ID** from the URL after installation: `https://github.com/organizations/{org}/settings/installations/{INSTALLATION_ID}`

Or retrieve it programmatically:
```http
GET /orgs/{org}/installation
Authorization: Bearer {JWT}
```

### Step 4: Programmatic Token Generation

Python example using PyJWT:

```python
import time, jwt, requests

def get_installation_token(app_client_id: str, private_key_pem: str,
                            installation_id: int, repo: str) -> str:
    # Generate JWT (valid 10 minutes, backdated 60s for clock skew)
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": app_client_id,
    }
    encoded_jwt = jwt.encode(payload, private_key_pem, algorithm="RS256")

    # Exchange for installation token scoped to one repo
    resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {encoded_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "repositories": [repo],
            "permissions": {"contents": "write", "pull_requests": "write"},
        },
    )
    resp.raise_for_status()
    return resp.json()["token"]
```

Shell example using OpenSSL:

```bash
#!/usr/bin/env bash
# Generate base64url-encoded JWT and exchange for installation token
APP_ID="<app-id>"
PRIVATE_KEY_PATH="/run/secrets/github-app-key.pem"
INSTALLATION_ID="<installation-id>"
REPO="<repo-name>"

now=$(date +%s)
iat=$((now - 60))
exp=$((now + 600))

header=$(echo -n '{"alg":"RS256","typ":"JWT"}' | openssl base64 -A | tr '+/' '-_' | tr -d '=')
payload=$(echo -n "{\"iat\":$iat,\"exp\":$exp,\"iss\":\"$APP_ID\"}" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
sig=$(echo -n "$header.$payload" | openssl dgst -sha256 -sign "$PRIVATE_KEY_PATH" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
JWT="$header.$payload.$sig"

TOKEN=$(curl -s -X POST \
  -H "Authorization: Bearer $JWT" \
  -H "Accept: application/vnd.github+json" \
  -d "{\"repositories\":[\"$REPO\"],\"permissions\":{\"contents\":\"write\",\"pull_requests\":\"write\"}}" \
  "https://api.github.com/app/installations/$INSTALLATION_ID/access_tokens" \
  | jq -r .token)

echo "$TOKEN"
```

---

## 3. Private Key Storage and Protection

The private key is the root credential for the entire GitHub App. It must never be stored in:
- Source code (any repository, public or private)
- Container images
- Kubernetes ConfigMaps
- Environment variables baked into container specs (as opposed to injected at runtime)
- CI/CD pipeline YAML files in plaintext

### Recommended Storage: Secrets Managers

**HashiCorp Vault — Transit Engine (sign-only)**

The most security-hardened approach: store the private key in Vault's Transit secrets engine configured for signing only. The key never leaves Vault; instead, the JWT signing operation is delegated to Vault:

```bash
# Store key in Vault transit engine
vault write transit/keys/github-app-key type=rsa-2048

# Sign JWT payload without key material leaving Vault
vault write transit/sign/github-app-key \
  input="base64-encoded-header.payload" \
  signature_algorithm="pkcs1v15" \
  hash_algorithm="sha2-256"
```

This ensures that even if the orchestration infrastructure is compromised, the raw private key is never exposed.

**AWS Secrets Manager**

Store the PEM content as a secret string:
```bash
aws secretsmanager create-secret \
  --name "github-app/private-key" \
  --secret-string "$(cat app.pem)"
```

Retrieve at invocation time with IAM role-based access (use IRSA in EKS, instance profiles in EC2, task roles in ECS). Apply least-privilege IAM policies scoped to the specific secret ARN.

**GCP Secret Manager**

```bash
gcloud secrets create github-app-private-key \
  --data-file=app.pem

gcloud secrets add-iam-policy-binding github-app-private-key \
  --member="serviceAccount:agent-orchestrator@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Azure Key Vault**

GitHub's own best practices documentation specifically recommends Azure Key Vault configured for sign-only access, so that the JWT signing operation is performed inside the vault without key material egress.

### Key Rotation

With up to 25 simultaneous private keys supported per App, zero-downtime rotation is straightforward:
1. Generate a new key in GitHub App settings (downloads new PEM)
2. Store new PEM in secrets manager under a new version
3. Update orchestration to use new key version
4. Delete old key from GitHub App settings and archive/destroy old secret version

---

## 4. One GitHub App per Org vs. per Repo

### Per-Org App (Recommended Default)

**Advantages:**
- Single registration to maintain (one app ID, one private key)
- Single installation to manage per org
- Per-repo scoping is applied at token generation time via the `repositories` array — not at installation time
- Enterprise-owned Apps (GA as of March 2025) allow one App to span multiple orgs with centralized permission management
- Permission updates to enterprise-owned Apps are automatically accepted by all orgs

**Disadvantages:**
- The App has potential access to all repos in the org/enterprise; misconfiguration of the `repositories` parameter at token generation time could grant broader access than intended
- A compromised private key gives access to all repos in the installation scope

### Per-Repo App

**Advantages:**
- Strict blast radius containment: a compromised key only affects one repo
- Cleaner audit trail — App identity maps 1:1 to a repo

**Disadvantages:**
- Multiplicative management overhead: N repos = N apps, N private keys, N installations
- Key rotation must be performed N times
- GitHub has no official tooling to manage many Apps at scale

### GitHub's Own Recommendation

GitHub recommends installing Apps with least-privilege repository access. The practical guidance is: **use one App per organization, but scope tokens tightly per invocation.** The `repositories` parameter on the `POST /app/installations/{id}/access_tokens` endpoint is the control point for per-invocation isolation.

For enterprises with multiple organizations, enterprise-owned Apps (available since March 2025) provide a centralized single-registration model with org-level installation isolation.

### Token-Level Scoping as the Isolation Mechanism

Even with an org-wide installation, each invocation generates a token restricted to a single repository:

```json
{
  "repositories": ["agent-target-repo"],
  "permissions": {
    "contents": "write",
    "pull_requests": "write"
  }
}
```

This token literally cannot be used to access any other repository, even if the installation has org-wide access. This provides equivalent isolation to per-repo apps with far less management overhead.

---

## 5. Minimum Permission Set

For the operations: **clone → push branch → create PR**, the minimum GitHub App permissions are:

| Permission | Level | Required For |
|------------|-------|-------------|
| **Contents** | Read & Write | Clone (read), push branch (write), create/update files |
| **Pull Requests** | Read & Write | Create a pull request, read PR status |
| **Metadata** | Read-only | Mandatory for all GitHub Apps; needed for basic repo info |

**No other permissions are needed.** Specifically:
- Workflows: NOT needed unless pushing `.github/workflows/` files
- Actions: NOT needed
- Checks: NOT needed (unless agent needs to read CI status)
- Issues: NOT needed
- Administration: NOT needed
- Secrets: NOT needed

The `Metadata` (read-only) permission is automatically granted to all GitHub Apps and cannot be removed — this is expected.

At the token generation level, further narrow permissions:
```json
{
  "permissions": {
    "contents": "write",
    "pull_requests": "write"
  }
}
```

This produces a token that cannot access org-level settings, secrets, actions, or any other resource.

---

## 6. Token Generation in Container Orchestration

The orchestrator (not the agent container itself) is responsible for token generation. This separation ensures:
- The private key never enters the agent container
- The token is single-use and task-scoped
- Token generation happens in a trusted control plane context

### Pattern 1: Pre-Start Token Injection (Simplest)

The orchestration layer (Lambda, ECS task launcher, Kubernetes controller, etc.) generates the token immediately before starting the container:

```python
# Pseudocode: orchestrator pre-start hook
def launch_agent(repo: str, task: dict) -> None:
    # 1. Fetch private key from secrets manager
    private_key = secrets_client.get_secret("github-app/private-key")

    # 2. Generate scoped installation token
    token = get_installation_token(
        app_client_id=APP_CLIENT_ID,
        private_key_pem=private_key,
        installation_id=INSTALLATION_ID,
        repo=repo,
    )

    # 3. Launch container with token as environment variable or mounted secret
    container_client.run(
        image="agent:latest",
        environment={"GITHUB_TOKEN": token},
        # or mount as tmpfs file
    )
```

The token is valid for 1 hour. If agent tasks exceed 1 hour, the token must be refreshed — this is a forcing function for keeping tasks short.

### Pattern 2: Kubernetes Init Container

An init container runs the token generation script, writes the token to a shared `emptyDir` volume, and the main container reads it at startup:

```yaml
apiVersion: v1
kind: Pod
spec:
  volumes:
    - name: git-credentials
      emptyDir:
        medium: Memory   # in-memory tmpfs, not written to disk
  initContainers:
    - name: token-fetcher
      image: token-fetcher:latest
      env:
        - name: GITHUB_APP_KEY
          valueFrom:
            secretKeyRef:
              name: github-app-secret
              key: private-key
      volumeMounts:
        - name: git-credentials
          mountPath: /credentials
      command: ["/bin/sh", "-c"]
      args:
        - generate-github-token --repo $(REPO) > /credentials/github-token
  containers:
    - name: agent
      image: agent:latest
      volumeMounts:
        - name: git-credentials
          mountPath: /credentials
          readOnly: true
```

### Pattern 3: External Secrets Operator (GitOps / Continuous Token Refresh)

For persistent workloads (not single-invocation), the External Secrets Operator's `GithubAccessToken` generator can maintain a Kubernetes Secret with a valid GitHub App token, refreshing it before expiry:

```yaml
apiVersion: generators.external-secrets.io/v1alpha1
kind: GithubAccessToken
metadata:
  name: agent-github-token
spec:
  url: "https://api.github.com"
  appID: "12345"
  installID: "67890"
  auth:
    privateKey:
      secretRef:
        name: github-app-pem
        key: key
  repositories:
    - "target-repo"
  permissions:
    contents: "write"
    pull_requests: "write"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: agent-github-token
spec:
  refreshInterval: 45m   # refresh before the 60-minute expiry
  dataFrom:
    - sourceRef:
        generatorRef:
          apiVersion: generators.external-secrets.io/v1alpha1
          kind: GithubAccessToken
          name: agent-github-token
```

### Pattern 4: github-token-manager Operator (KMS-backed, No Key in Cluster)

For maximum security, the `github-token-manager` operator ([isometry/github-token-manager](https://github.com/isometry/github-token-manager)) delegates JWT signing to a cloud KMS (AWS KMS, Azure Key Vault, GCP Cloud KMS, HashiCorp Vault transit engine), so the private key material never enters the Kubernetes cluster:

```yaml
apiVersion: github.com/v1alpha1
kind: Token
metadata:
  name: agent-repo-token
spec:
  appID: 12345
  installationID: 67890
  repositories:
    - target-repo
  permissions:
    contents: write
    pullRequests: write
  keyRef:
    provider: aws-kms
    keyID: "arn:aws:kms:us-east-1:123456789:key/..."
```

This pattern is recommended for production environments where the cluster itself should not be considered a trust boundary for key material.

---

## 7. Token Injection Methods: Comparison

### Option A: Environment Variable

```bash
docker run -e GITHUB_TOKEN="ghs_..." agent:latest
```

**Pros:** Simple, universally supported by git and GitHub CLI (`GH_TOKEN`/`GITHUB_TOKEN` env vars).  
**Cons:** Environment variables are visible in `/proc/<pid>/environ`, in `docker inspect` output, in container logs if accidentally printed, and in Kubernetes pod specs if not using `secretKeyRef`. Weakest option but often acceptable for ephemeral containers that are destroyed after the task.

### Option B: Mounted Secret File (Preferred)

Mount the token as a file on an in-memory tmpfs volume:

```bash
# Docker
docker run \
  --mount type=tmpfs,destination=/run/secrets \
  --mount type=bind,source=/host/token-file,destination=/run/secrets/github-token,readonly \
  agent:latest

# In the container:
git clone https://x-access-token:$(cat /run/secrets/github-token)@github.com/owner/repo.git
```

**Pros:** Not visible in environment, not logged by default, file permissions can be set to 0400. Using `tmpfs` means the token never touches disk.  
**Cons:** Slightly more complex setup.

### Option C: Git Credential Helper

Configure git to use a credential helper that reads the token from a file or environment:

```bash
# Configure git to use a helper script
git config --global credential.helper '/usr/local/bin/github-app-credential-helper'
git config --global credential.useHttpPath true  # important: scopes to specific path
```

The credential helper is invoked by git when it needs credentials, returning:
```
username=x-access-token
password=ghs_...
```

A purpose-built credential helper for GitHub Apps exists: [bdellegrazie/git-credential-github-app](https://github.com/bdellegrazie/git-credential-github-app). This helper can dynamically generate a fresh token using the App's private key, avoiding even token injection as a concern.

**Pros:** Token never in a URL (avoids accidental logging of HTTPS URLs with embedded credentials), can generate fresh tokens on demand.  
**Cons:** Requires the private key to be available inside the container — only appropriate if the container is running the token generation itself, not receiving a pre-generated token.

### Option D: `.git-credentials` File (Not Recommended)

Writing the token to `~/.git-credentials` or a custom `GIT_CREDENTIALS` file on disk is not recommended for ephemeral containers because: (1) it persists to disk, (2) file may be captured in forensic snapshots, (3) no benefit over env var for short-lived containers.

### Recommended Approach for Container Sandbox

For a single-invocation agent container:
1. Orchestrator generates token (Option B flow), writes to tmpfs
2. Container receives token as a mounted tmpfs secret file at a known path (e.g., `/run/secrets/github-token`)
3. Container's git configuration or startup script reads the token from this path
4. Container uses `https://x-access-token:$(cat /run/secrets/github-token)@github.com/...` for all git operations

---

## 8. Fine-Grained PATs vs. GitHub App Tokens: Security Comparison

| Dimension | Fine-Grained PAT | GitHub App Installation Token |
|-----------|-----------------|-------------------------------|
| Identity | Tied to a human user account | Independent App identity |
| Lifetime | Up to 366 days (or no expiry if org allows) | Hard 1-hour max |
| Rotation | Manual (or via API with admin token) | Automatic at each invocation |
| Scope granularity | Per-repo, 50+ permission types | Per-repo, same permissions model |
| Org permissions | Limited; cannot grant all org API access | Full org-level permissions available |
| Rate limits | 5,000 req/hr per user | 15,000 req/hr per installation |
| Blast radius on leak | Attacker has user's access for up to 366 days | Attacker has 1 hour of single-repo access |
| Auditability | Appears as user action | Appears as App action, distinguishable in logs |
| GitHub seat consumption | Yes | No |
| Org-level automation | Blocked or requires admin approval | Native use case |
| Required infrastructure | None beyond the PAT itself | GitHub App registration + secrets manager |

**Verdict:** For automation that runs in containers or CI/CD pipelines, GitHub App tokens are strictly superior on every security dimension. Fine-grained PATs remain useful for human developers' local tooling and quick scripts, but are inappropriate for production automation.

The only meaningful advantage of fine-grained PATs is reduced setup complexity (no App registration, no private key infrastructure). For a container sandbox platform, this one-time setup cost is worth the ongoing security benefits.

---

## 9. Why Deploy Keys Don't Work for PR Creation

Deploy keys are SSH key pairs associated with a single repository. They are designed for read access to production deployments. Their limitations make them unsuitable for this use case:

**Cannot create pull requests:** Deploy keys authenticate over SSH and provide only git protocol access (clone/push). Creating a pull request requires a call to the GitHub REST API (`POST /repos/{owner}/{repo}/pulls`). SSH keys have no mechanism to authenticate REST API requests — there is no equivalent of `Authorization: Bearer <ssh-key>`.

**No expiry:** Deploy keys have no expiration date. A leaked deploy key remains valid indefinitely until manually revoked.

**Write access is binary:** Deploy keys can be read-only or read-write, but not scoped to specific git operations or branches.

**Single-repo only:** Each deploy key is bound to exactly one repository at registration time — similar to per-repo Apps but without any API capabilities.

**GitHub's documentation states explicitly:** "If you need to interact with multiple repositories, consider using a machine user or a GitHub App instead of a deploy key."

For the container sandbox use case, which requires both git push (SSH or HTTPS) and REST API calls (to open a PR), deploy keys fail at the REST API requirement.

---

## 10. GitHub's Official Guidance Summary

GitHub's documentation on best practices for creating GitHub Apps states:

> "Select the minimum permissions that your GitHub App needs. This limits the damage that could be done if your app's credentials are compromised."

> "Store private keys in a key vault, such as Azure Key Vault. [...] Only use environment variables if a key vault is not available. Avoid hard-coding your private key in your app's source code, even in a private repository."

> "GitHub Apps use short lived tokens. If the token is leaked, the token will be valid for a shorter amount of time, which reduces the damage that can be done."

> "Cache and reuse tokens: If you are making multiple API requests in a short period of time, cache your installation access token and reuse it rather than generating a new token for each request."

> "A GitHub App does not consume a GitHub seat."

GitHub's own `actions/create-github-app-token` Action demonstrates the canonical pattern in GitHub Actions contexts, which mirrors what custom orchestrators should implement outside Actions.

---

## Sources

- [Authenticating as a GitHub App installation — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation)
- [Generating an installation access token for a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
- [Generating a JSON Web Token (JWT) for a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app)
- [Managing private keys for GitHub Apps — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps)
- [Best practices for creating a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app)
- [Deciding when to build a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/deciding-when-to-build-a-github-app)
- [Registering a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
- [Permissions required for GitHub Apps — GitHub Docs](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps)
- [Choosing permissions for a GitHub App — GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)
- [REST API endpoints for GitHub App installations — GitHub Docs](https://docs.github.com/en/rest/apps/installations)
- [Managing deploy keys — GitHub Docs](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
- [Enterprise-owned GitHub Apps are now generally available — GitHub Changelog](https://github.blog/changelog/2025-03-10-enterprise-owned-github-apps-are-now-generally-available/)
- [GitHub Apps can now use the client ID to fetch installation tokens — GitHub Changelog](https://github.blog/changelog/2024-05-01-github-apps-can-now-use-the-client-id-to-fetch-installation-tokens/)
- [Still Using PATs in 2025? Time to move to Github Apps — Bruno Terra](https://bmterra.eu/articles/010625-using-github-apps/)
- [GitHub Authentication: Personal Access Tokens vs. GitHub Apps — Michael Kasingye, Medium](https://michaelkasingye.medium.com/github-authentication-personal-access-tokens-vs-github-apps-0f8fba446fbd)
- [Secure CI/CD with GitHub Apps Short Lived Tokens — DevOpsWithYoge, Medium](https://medium.com/@devopswithyoge/secure-ci-cd-with-github-apps-short-lived-tokens-227d6e05c5fa)
- [Access a repository from a GitHub App — Damir's Corner](https://www.damirscorner.com/blog/posts/20240913-AccessARepositoryFromAGitHubApp.html)
- [actions/create-github-app-token — GitHub](https://github.com/actions/create-github-app-token)
- [MShekow/github-app-installation-token — GitHub](https://github.com/MShekow/github-app-installation-token)
- [isometry/github-token-manager — GitHub](https://github.com/isometry/github-token-manager)
- [GithubAccessToken Generator — External Secrets Operator](https://external-secrets.io/latest/api/generator/github/)
- [bdellegrazie/git-credential-github-app — GitHub](https://github.com/bdellegrazie/git-credential-github-app)
- [Vault Agent Injector — HashiCorp Developer](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector)
- [Distribute Credentials Securely Using Secrets — Kubernetes Docs](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Introducing fine-grained personal access tokens for GitHub — GitHub Blog](https://github.blog/security/application-security/introducing-fine-grained-personal-access-tokens-for-github/)
- [Replacing a GitHub Personal Access Token with a GitHub Application — Aembit](https://aembit.io/blog/replacing-a-github-personal-access-token-with-a-github-application/)
