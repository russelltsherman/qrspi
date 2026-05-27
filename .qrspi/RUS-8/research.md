# Research — Argo CD CLI Codebase Map
**Questions source:** questions.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## Q1: What command-line output formats does the `argocd` CLI produce (JSON, YAML, table), and which formats are used by which subcommands?

**Answer:** The `argocd` CLI supports multiple output formats per subcommand, registered via `--output` / `-o` flags. Each subcommand defines its own format set.

- **`argocd app get`**: `json|yaml|wide|tree` (default: `wide`). The `wide` format renders a table. `tree` renders a resource tree view.
- **`argocd app list`**: `wide|name|json|yaml` (default: `wide`). The `name` format outputs only application names, one per line.
- **`argocd app diff`**: `json|yaml|wide|tree|tree=detailed` (default: `wide`). The `tree=detailed` format includes per-resource diff details.
- **`argocd app sync` / `argocd app wait`**: `json|yaml|wide|tree|tree=detailed`.

**Evidence:**
```go
// cmd/argocd/commands/app.go (NewApplicationGetCommand)
command.Flags().StringVarP(&output, "output", "o", "wide",
    "Output format. One of: json|yaml|wide|tree")

// cmd/argocd/commands/app.go (NewApplicationListCommand)
command.Flags().StringVarP(&output, "output", "o", "wide",
    "Output format. One of: wide|name|json|yaml")

// cmd/argocd/commands/app.go (NewApplicationDiffCommand)
command.Flags().StringVarP(&output, "output", "o", "wide",
    "Output format. One of: json|yaml|wide|tree|tree=detailed")
```

The output rendering is handled by `PrintResource()` in `common.go`:

```go
// cmd/argocd/commands/common.go
func PrintResource(resource interface{}, output string) error {
    switch output {
    case "json":
        jsonBytes, err := json.MarshalIndent(resource, "", "  ")
    case "yaml":
        yamlBytes, err := yaml.Marshal(resource)
    default:
        return fmt.Errorf("unknown output format: %s", output)
    }
}
```

**Dependencies:** `PrintResource` in `common.go` is called by every subcommand that supports `--output`. Each subcommand's `Run` function calls `PrintResource(result, output)` after fetching data from the server.

**Implicit contracts:** All structured output (json/yaml) serializes the same Go struct that the server returns. The table/wide formats derive from custom formatters, not the raw structs.

---

## Q2: How does the `ARGOCD_OPTS` environment variable work, and can it be set once at skill initialization to eliminate repetitive flags?

**Answer:** `ARGOCD_OPTS` is a space-separated string of CLI flags that the CLI parses at startup and merges into the flag resolution chain. It is the primary mechanism for setting global options once.

The parsing flow:

1. **`LoadFlags()`** (in `util/config/env.go`) reads `os.Getenv("ARGOCD_OPTS")`, tokenizes the string, and builds an in-memory `map[string]string` where keys are flag names (with or without leading `--`) and values are their arguments. It also normalizes `key=value` syntax.

2. **`config.GetFlag(key, fallback)`** (same file) first checks the parsed `ARGOCD_OPTS` map, then falls back to the provided default.

3. **Root command** (`cmd/argocd/commands/root.go`) registers persistent flags using this pattern:
```go
command.PersistentFlags().StringVar(&clientOpts.ServerAddr, "server",
    config.GetFlag("server", ""), "Argo CD server address")
```

Because these are `PersistentFlags`, every subcommand automatically inherits them. Setting `--server` or `--auth-token` in `ARGOCD_OPTS` applies to all subcommands.

**Evidence:**
```go
// util/config/env.go (LoadFlags summary)
func LoadFlags() {
    opts := os.Getenv("ARGOCD_OPTS")
    // Tokenize opts, build flags map:
    //   "--server https://argocd.example.com" -> flags["server"] = "https://argocd.example.com"
    //   "--auth-token=abc123" -> flags["auth-token"] = "abc123"
}

// util/config/env.go (GetFlag)
func GetFlag(key, fallback string) string {
    val, ok := flags[key]
    if ok {
        return val
    }
    return fallback
}

// cmd/argocd/commands/root.go (flag registration)
config.GetFlag("auth-token", env.StringFromEnv(common.EnvAuthToken, ""))
```

**Supported global flags via `ARGOCD_OPTS`:** `--server`, `--auth-token`, `--plaintext`, `--insecure`, `--server-crt`, `--client-crt`, `--client-crt-key`, `--grpc-web`, `--grpc-web-root-path`, `--logformat`, `--loglevel`, `--header`, `--port-forward`, `--port-forward-namespace`, `--http-retry-max`, `--core`, `--argocd-context`, `--server-name`, `--controller-name`, `--redis-haproxy-name`, `--redis-name`, `--repo-server-name`, `--redis-compress`, `--prompts-enabled`, `--kube-context`, `--config`.

**Environment variables used alongside `ARGOCD_OPTS`:**

```go
// cmd/argocd/commands/root.go (env var bindings)
env.StringFromEnv(common.EnvAuthToken, "")        // ARGOCD_AUTH_TOKEN
env.StringFromEnv(common.EnvServerName, ...)      // ARGOCD_SERVER_NAME
env.StringFromEnv(common.EnvAppControllerName, ...) // ARGOCD_APP_CONTROLLER_NAME
env.StringFromEnv(common.EnvRedisHaProxyName, ...)  // ARGOCD_REDIS_HAPROXY_NAME
env.StringFromEnv(common.EnvRedisName, ...)         // ARGOCD_REDIS_NAME
env.StringFromEnv(common.EnvRepoServerName, ...)    // ARGOCD_REPO_SERVER_NAME
env.StringFromEnv("REDIS_COMPRESSION", ...)         // REDIS_COMPRESSION
```

**Answer:** Yes — set `ARGOCD_OPTS="--server https://argocd.example.com --auth-token <token>"` once in the skill environment. All subcommands inherit these flags via the `PersistentFlags` + `ARGOCD_OPTS` resolution chain.

---

## Q3: What is the structure of an Argo CD Application manifest file, and what fields are required versus optional for `argocd app create` and for declarative manifests?

**Answer:** An Argo CD Application is a Kubernetes Custom Resource (CRD) of type `Application` in the `argoproj.io/v1alpha1` API group.

**API Types (from `pkg/apis/application/v1alpha1/types.go`):**

```go
type ApplicationSpec struct {
    Source      *ApplicationSource       `json:"source,omitempty"`
    Destination ApplicationDestination   `json:"destination"`
    Project     string                   `json:"project,omitempty"`
}

type ApplicationSource struct {
    RepoURL        string   `json:"repoURL"`
    Path           string   `json:"path,omitempty"`
    TargetRevision string   `json:"targetRevision,omitempty"`
}

type ApplicationDestination struct {
    Server    string `json:"server"`
    Namespace string `json:"namespace"`
}
```

**Required fields for `argocd app create` (flags):**
- `APPNAME` (positional argument)
- Source: `--repo <url>` (required) + `--path <path>` (required)
- Destination: `--dest-namespace <ns>` (required) + `--dest-server <url>` (required)
- `--project <project>` (default: "default")

**Optional `argocd app create` flags:**
- `--upsert` — override existing app even if spec differs
- `--label/-l` — apply labels
- `--annotations` — set metadata annotations
- `--set-finalizer` — cascade deletion
- `--app-namespace/-N` — target namespace for the App CRD
- `--file/-f` — read from manifest file/URL instead of flags
- Helm overrides: `--helm-set`, `--helm-set-string`, `--helm-set-file`
- Kustomize overrides: `--kustomize-image`, `--kustomize-enable-helm`, `--kustomize-settings`
- Directory recursion: `--directory-recurse`

**Evidence:**
```go
// cmd/argocd/commands/app.go (NewApplicationCreateCommand)
func NewApplicationCreateCommand(clientOpts *argocdclient.ClientOptions) *cobra.Command {
    var (
        appOpts    cmdutil.AppOptions
        fileURL    string
        appName    string
        upsert     bool
        labels     []string
        annotations []string
        setFinalizer bool
        appNamespace string
    )
    command.Flags().BoolVar(&upsert, "upsert", false,
        "Allows to override application with the same name even if supplied application spec is different")
    command.Flags().StringVarP(&fileURL, "file", "f", "",
        "Filename or URL to Kubernetes manifests for the app")
    command.Flags().BoolVar(&setFinalizer, "set-finalizer", false,
        "Sets deletion finalizer on the application")
    cmdutil.AddAppFlags(command, &appOpts) // helm, kustomize, dir-recurse flags
}
```

**Implicit contract:** The `ApplicationSource` requires `RepoURL` (no omitempty). `ApplicationDestination` requires both `Server` and `Namespace` (no omitempty). `Project` is optional and defaults to "default".

---

## Q4: How do sync waves, resource hooks (PreSync, Sync, PostSync, SyncFail), and resource tracking work together?

**Answer:** Argo CD organizes resource deployment into phases and waves:

- **SyncPhases** define the lifecycle stage: `PreSync`, `Sync`, `PostSync`, `SyncFail`.
- **SyncWaves** are integer ordering within each phase. Resources with lower wave numbers deploy first.
- **Resource Hooks** are annotations on Kubernetes resources that tell Argo CD how to treat them:
  - `hook: true` marks a resource as a hook (not a regular deployed resource).
  - `hookType` specifies the hook type (e.g., `PreSync`, `PostSync`).
  - `hookPhase` tracks execution state: `Pending`, `Running`, `Success`, `Failed`, `Skipped`, `Terminating`.

**Evidence:**
```go
// pkg/apis/application/v1alpha1/generated.proto
message ResourceStatus {
    optional int64 syncWave = 10;   // Ordering within a phase
    optional bool hook = 8;          // Is this a hook resource?
}

message ResourceResult {
    optional string hookType = 8;    // PreSync, PostSync, SyncFail, etc.
    optional string hookPhase = 9;   // Current execution phase
    optional string syncPhase = 10;  // Phase this result came from
}
```

**Resource tracking:** Argo CD tracks deployed resources by injecting a tracking label/annotation into each resource's metadata. On reconciliation, it compares the tracked state against the live cluster state to detect drift.

**Implicit contract:** Hooks with `hook: true` are not included in the application's resource list for drift detection — they are managed separately and deleted after completion. Sync waves are strictly ordered; resources in the same wave deploy concurrently.

**Dependencies:** The sync controller evaluates waves phase-by-phase, wave-by-wave. A resource in wave 2 cannot start until all wave 1 resources (including hooks) succeed.

---

## Q5: Which `argocd` subcommands require interactive prompts versus accepting all input via flags?

**Answer:** Most subcommands are fully flag-driven and suitable for automation. Only a few have interactive prompts:

**Subcommands with interactive prompts:**

1. **`argocd login`** — Prompts for username/password if not supplied via flags. Shows TLS warnings if `--skip-test-tls` is not set:
```go
// cmd/argocd/commands/login.go
cli.AskToProceed("WARNING: server is not configured with TLS. Proceed (y/n)? ")
cli.PromptCredentials() // interactive username/password prompt
```
No `--yes` or `--assume-yes` flag exists to bypass these. Automation requires pre-supplying `--username` and `--password`.

2. **`argocd account delete-token`** — Requires confirmation prompt before revoking a token.

3. **`argocd context`** (delete mode) — Asks for confirmation when deleting a context.

**Subcommands that are fully flag-driven (no prompts):**
- `argocd app create` / `app get` / `app list` / `app diff` / `app sync` / `app wait` / `app delete`
- `argocd context list` / `context switch`
- `argocd account list` / `account get` / `account generate-token` / `account can-i` / `account get-user-info`
- `argocd cluster list` / `cluster get` / `cluster add` / `cluster remove`
- `argocd repo list` / `repo add` / `repo remove`
- `argocd project create` / `project get` / `project list`
- `argocd version`
- `argocd tree`

**Evidence:**
```go
// cmd/argocd/commands/root.go (prompts control)
command.PersistentFlags().BoolVar(&clientOpts.PromptsEnabled, "prompts-enabled",
    localconfig.GetPromptsEnabled(true),
    "Force optional interactive prompts to be enabled or disabled")
```

The `--prompts-enabled` flag can disable optional prompts globally. The localconfig value defaults to `false`.

**Answer for automation suitability:** All subcommands except `login` and `account delete-token` are suitable for agent-driven automation when all required flags are supplied. `login` requires credentials pre-supplied or SSO configured.

---

## Q6: How does the `argocd context` subcommand work for switching between multiple Argo CD server instances?

**Answer:** The `argocd context` command manages server context aliases in the local config file.

**Commands:**
- `argocd context` (no args) — Lists all contexts with current context prefixed by `*`
- `argocd context <NAME>` — Switches to the named context
- `argocd context <NAME> --delete` — Deletes the context

**Config file location:** `~/.config/argocd/argocd.yaml` (path from `localconfig.DefaultLocalConfigPath()`). Can be overridden with `--config`.

**Persistence mechanism:** Uses `localconfig.ReadLocalConfig()` to read, modifies the struct, then `localconfig.WriteLocalConfig()` to serialize back to disk as YAML/JSON.

**State persisted:**

```go
// util/localconfig/localconfig.go
type LocalConfig struct {
    CurrentContext string       `json:"current-context"`
    Contexts       []ContextRef `json:"contexts"`
    Servers        []Server     `json:"servers"`
    Users          []User       `json:"users"`
    PromptsEnabled bool         `json:"prompts-enabled"`
}

type ContextRef struct {
    Name   string `json:"name"`
    Server string `json:"server"`
    User   string `json:"user"`
}

type Server struct {
    Server       string `json:"server"`
    Insecure     bool   `json:"insecure,omitempty"`
    GRPCWeb      bool   `json:"grpc-web,omitempty"`
    GRPCWebRootPath string `json:"grpc-web-root-path"`
    CACertificateAuthorityData string `json:"certificate-authority-data,omitempty"`
    ClientCertificateData string `json:"client-certificate-data,omitempty"`
    ClientCertificateKeyData string `json:"client-certificate-key-data,omitempty"`
    PlainText    bool   `json:"plain-text,omitempty"`
    Core         bool   `json:"core,omitempty"`
}

type User struct {
    Name       string `json:"name"`
    AuthToken  string `json:"auth-token,omitempty"`
    RefreshToken string `json:"refresh-token,omitempty"`
}
```

**Previous context tracking:** When switching contexts, the previous context name is saved to a `.prev-ctx` file in the config directory.

**Evidence:**
```go
// cmd/argocd/commands/context.go
func NewContextCommand(clientOpts *argocdclient.ClientOptions) *cobra.Command {
    // Reads localconfig, formats table output for list
    // Updates CurrentContext and persists for switch
    // Saves .prev-ctx file on context change
    // Removes context, user, and server entries on delete
    // Deletes config file entirely if empty
}
```

---

## Q7: What is the format and lifecycle of an `ARGOCD_AUTH_TOKEN`, and how do project-scoped role tokens differ from admin tokens?

**Answer:** Auth tokens are JWT strings issued server-side and stored in `~/.config/argocd/argocd.yaml` under `Users[].AuthToken`.

**Token lifecycle:**
- **Generation:** `argocd account generate-token --account <name> --id <uuid> --expires-in <duration>`
- **Expiration:** `--expires-in` defaults to unlimited (no expiration). Tokens carry issuance and expiration timestamps displayed in `argocd account list`.
- **Revocation:** `argocd account delete-token <token-id>` requires a confirmation prompt.
- **Password reset:** `argocd account update-password` triggers a new login sequence that retrieves and overwrites the local auth token.

**Evidence:**
```go
// cmd/argocd/commands/account.go
// generate-token: Issues credentials via CreateToken(account, id, expires-in)
// delete-token: Revokes credentials after confirmation prompt
// update-password: Resets credentials, triggers login, gets new JWT token
```

**Project-scoped vs admin tokens:** The CLI code does not distinguish between project-scoped and admin tokens in the generation or storage logic. Token permissions are enforced server-side by the Argo CD RBAC system. The `argocd account can-i <action> <resource> <subresource>` command checks permissions against the current token.

**JWT format:** The CLI treats tokens as opaque strings. The server generates JWT tokens (likely using a signing key configured in the server). The CLI does not inspect or modify the token structure.

**Implicit contract:** Tokens are stored in plaintext in the local config file. The `--auth-token` flag or `ARGOCD_AUTH_TOKEN` environment variable can be used instead of file storage for tokenless operation.

---

## Q8: What state does the `argocd` CLI client cache locally, and where is this cache stored?

**Answer:** The CLI stores the following state locally in `~/.config/argocd/`:

| State | Storage | Description |
|-------|---------|-------------|
| Server contexts | `argocd.yaml` (`Contexts`) | Named aliases mapping to server addresses and auth |
| Server config | `argocd.yaml` (`Servers`) | TLS settings, gRPC-web flags, certificate data |
| Auth tokens | `argocd.yaml` (`Users[].AuthToken`) | JWT tokens for each user |
| Refresh tokens | `argocd.yaml` (`Users[].RefreshToken`) | OAuth refresh tokens for SSO |
| Previous context | `.prev-ctx` | Last context before the current one |
| Server certificates | `argocd.yaml` (`Servers[].CACertificateAuthorityData`, `ClientCertificateData`) | PEM-encoded cert data (base64) |

**Additional env-dependent state:**
- `REDIS_COMPRESSION` env var controls whether the controller uses gzip-compressed Redis connections.
- TLS certificates can be provided via `--server-crt` / `--client-crt` / `--client-crt-key` flags instead of file storage.

**Evidence:**
```go
// util/localconfig/localconfig.go
type LocalConfig struct {
    CurrentContext string       `json:"current-context"`
    Contexts       []ContextRef `json:"contexts"`
    Servers        []Server     `json:"servers"`
    Users          []User       `json:"users"`
    PromptsEnabled bool         `json:"prompts-enabled"`
}
// Path: ~/.config/argocd/argocd.yaml (from localconfig.DefaultLocalConfigPath())
```

---

## Q9: How does `argocd app diff` compute the diff between Git state and cluster state?

**Answer:** The diff command compares the live cluster state against a desired state source. It supports two modes:

**Mode 1: Remote (default)**
- Connects to the Argo CD server
- Fetches the app's current Git revision (from `spec.source.targetRevision`)
- Fetches live cluster state from the API server
- Compares the desired manifests against live resources

**Mode 2: Local (`--local` flag)**
- `--local <path>` — Path to local manifest directory. No Git queries are made.
- `--revision <ref>` — Compare live app to a particular Git revision
- `--server-side-generate` — Send local manifests to the server for processing (requires `--local`)
- `--local-include` — Specify filename patterns to include with `--server-side-generate`

**Evidence:**
```go
// cmd/argocd/commands/app.go (NewApplicationDiffCommand)
command.Flags().StringVar(&localPath, "local", "",
    "Path to a local directory. When this flag is present no git queries will be made")
command.Flags().StringVar(&revision, "revision", "",
    "Compare live app to a particular revision")
command.Flags().BoolVar(&serverSideGenerate, "server-side-generate", false,
    "Used with --local, this will send your manifests to the server for diffing")
command.Flags().StringVar(&localInclude, "local-include", "",
    "Used with server-side-generate, specify patterns of filenames to send")
command.Flags().BoolVar(&exitCode, "exit-code", false,
    "Return non-zero exit code when there is a diff")
command.Flags().IntVar(&diffExitCode, "diff-exit-code", 20,
    "Return specified exit code when there is a diff. Typical error code is 20")
```

**Exit codes:**
- `0` — No diff found (in sync)
- `1` — Diff found (out of sync)
- `2` — General error

**Implicit contract:** The `--local` flag requires the local path to contain valid Kubernetes manifests. Without `--server-side-generate`, the diff is computed client-side using a local diff tool (respects `$KUBECTL_EXTERNAL_DIFF` environment variable).

---

## Q10: What happens when the `argocd` CLI runs behind an ingress with TLS termination, and when is `--grpc-web` required?

**Answer:** The CLI supports three connection modes:

1. **Direct gRPC (default)** — Connects to the Argo CD server via gRPC over HTTP/2. Requires direct network access to the server port (typically 443).

2. **gRPC-web (`--grpc-web`)** — Wraps gRPC calls in HTTP/1.1 with gRPC-web protocol. Required when the server is behind a proxy/load balancer that does not support HTTP/2.

3. **gRPC-web with root path (`--grpc-web-root-path`)** — Same as above but with a custom URL path prefix (e.g., `/argocd`). Useful when the server is deployed at a sub-path behind an ingress.

**Evidence:**
```go
// cmd/argocd/commands/root.go
command.PersistentFlags().BoolVar(&clientOpts.GRPCWeb, "grpc-web", config.GetBoolFlag("grpc-web"),
    "Enables gRPC-web protocol. Useful if Argo CD server is behind proxy which does not support HTTP2.")
command.PersistentFlags().StringVar(&clientOpts.GRPCWebRootPath, "grpc-web-root-path",
    config.GetFlag("grpc-web-root-path", ""),
    "Enables gRPC-web protocol. Useful if Argo CD server is behind proxy which does not support HTTP2. Set web root.")

// util/grpc/grpc.go (dialer utility)
// Standard grpc.Dial lacks visibility into handshake failures.
// Custom dialer provides connection error diagnostics.
```

**TLS handling:**
- `--insecure` — Skip server certificate and domain verification
- `--plaintext` — Disable TLS entirely (connect over plain HTTP)
- `--server-crt` — Provide a specific CA certificate file

**When `--grpc-web` is required:** When the Argo CD server is behind an ingress controller (nginx, AWS ALB, etc.) that terminates TLS and does not proxy HTTP/2. Many ingress controllers only support HTTP/1.1, making gRPC-web the only viable option.

**Implicit contract:** `--grpc-web` and `--grpc-web-root-path` must match the ingress configuration. If the ingress rewrites paths, the root path must include the rewrite prefix.

---

## Q11: How does `argocd app sync --force` interact with in-progress syncs, live overrides, and self-heal?

**Answer:** The `--force` flag is passed directly into the sync engine as `syncOp.SyncStrategy.Force()`.

**Behavior with in-progress syncs:**
- If the current operation phase is `OperationTerminating`, the sync executor calls `syncCtx.Terminate()` to abort the running operation before starting the new sync.
- Otherwise, `syncCtx.Sync()` executes the new sync immediately.

**Live overrides:** When `RespectIgnoreDifferences=true`, the sync applies a normalizer to live resources and patches target manifests accordingly. The sync preserves ownership of self-referenced objects via `isSelfReferencedObj` checks.

**Sync flags available:**

```go
// cmd/argocd/commands/app.go (NewApplicationSyncCommand)
command.Flags().BoolVar(&force, "force", false, "Use a force apply")
command.Flags().BoolVar(&replace, "replace", false, "Use a kubectl create/replace instead apply")
command.Flags().BoolVar(&serverSide, "server-side", false, "Use server-side apply while syncing")
command.Flags().BoolVar(&prune, "prune", false, "Allow deleting unexpected resources")
command.Flags().BoolVar(&dryRun, "dry-run", false, "Preview apply without affecting cluster")
command.Flags().StringVar(&strategy, "strategy", "", "Sync strategy (one of: apply|hook)")
command.Flags().BoolVar(&applyOutOfSyncOnly, "apply-out-of-sync-only", false,
    "Sync only out-of-sync resources")
command.Flags().StringVar(&resourceFilter, "resource", "",
    "Sync only specific resources as GROUP:KIND:NAME or !GROUP:KIND:NAME")
command.Flags().BoolVar(&async, "async", false, "Do not wait for application to sync")
command.Flags().StringVar(&timeout, "timeout", "", "Time out after this many seconds")
```

**State inconsistencies:** The sync controller logs a warning when it assesses resource health too quickly against stale objects, which can cause hooks to fire prematurely. Accurate health validation would require CRDs to expose `status.observedGeneration`.

**Implicit contract:** `--force` overrides resource locking and performs a force apply. Combined with `--replace`, it uses `kubectl create/replace` instead of `kubectl apply`. Combined with `--server-side`, it uses server-side apply. Multiple force flags can be combined.

---

## Q12: How does Argo CD handle concurrent `argocd app create` or `argocd app sync` from multiple agents?

**Answer:** Argo CD uses optimistic locking with automatic retry for concurrent modifications.

**Application create conflicts:**
- When a duplicate app is created, the server fetches the existing application and performs a deep comparison of spec, labels, annotations, and finalizers.
- If the specs match exactly, the operation is treated as idempotent and the existing application is returned.
- If specs differ and `--upsert` is not set: returns `InvalidArgument` with message `"existing application spec is different, use upsert flag to force update"`.
- If `--upsert` is set, proceeds with update.

**Concurrent sync/updates:**
- Uses an optimistic locking retry loop that re-fetches the current state on version conflict and retries the update.
- Retries up to **10 times**.
- After 10 exhausted retries: returns `Internal` with message `"Failed to update application. Too many conflicts"`.

**Error responses:**

| Scenario | gRPC Status | Message |
|----------|-------------|---------|
| Duplicate app, specs differ, no --upsert | `InvalidArgument` | "existing application spec is different, use upsert flag to force update" |
| Concurrent conflicts exhausted (10 retries) | `Internal` | "Failed to update application. Too many conflicts" |
| Server cannot fetch existing app during duplicate check | `Internal` | "unable to check existing application details" |

**Evidence:**
```go
// server/application/application.go (conflict handling summary)
// Create: deep compare existing vs incoming spec; idempotent if match
// Update: optimistic locking retry loop, up to 10 attempts
// Error: "Too many conflicts" after retry exhaustion
```

**Implicit contract:** The `--upsert` flag is essential for idempotent app creation in automated/agent-driven workflows. Without it, concurrent app creation for the same name will fail if specs differ.

---

## Q13: What testing infrastructure exists in this codebase for validating agent skills?

**Answer:** The codebase uses a JSON-based evaluation harness in `evals/suite.json` to validate QRSPI workflow artifacts.

**Suite structure (`evals/suite.json`):**

```json
{
  "name": "qrspi-agent-evals",
  "version": "0.1.0",
  "defaults": {
    "trials_per_case": 3,
    "timeout_ms": 120000,
    "max_tokens": 128000
  },
  "split": {
    "train_ratio": 0.65,
    "test_ratio": 0.35,
    "seed": 42
  },
  "cases": [ /* 15 test cases across 8 phases */ ]
}
```

**Test cases per phase:**

| Phase | Cases | Description |
|-------|-------|-------------|
| questions | case_001, case_002, case_015 | Happy path, complex ticket, budget stress |
| research | case_003, case_004 | Factual accuracy, NOT FOUND handling |
| design | case_005, case_006, case_014 | Citation compliance, new pattern flagging, illusion detection |
| structure | case_007, case_008 | Vertical slices, large feature splitting |
| plan | case_009 | Atomicity |
| worktree | case_010 | Session boundaries |
| implement | case_011, case_012 | Scope enforcement, deviation reporting |
| pr | case_013 | Acceptance criteria mapping |

**Assertion types used:**
- `programmatic` — File existence, section presence, line counts, code snippet limits, field validation
- `llm_judge` — Quality assessment by LLM (e.g., "Questions are specific and answerable by reading code")
- `script` — External script execution (e.g., `scripts/check_scope.py`)

**Key research assertions for RUS-8:**
```json
{
  "check": "all_questions_answered('research.md', 'questions.md')",
  "weight": 2.0
},
{
  "check": "all_answers_have_evidence('research.md')",
  "weight": 2.0
},
{
  "check": "all_evidence_has_file_citations('research.md')",
  "weight": 1.5
},
{
  "check": "no_solution_language('research.md')",
  "weight": 2.0
},
{
  "check": "has_section('research.md', 'Discovered Patterns')",
  "weight": 0.5
},
{
  "check": "has_section('research.md', 'Inconsistencies')",
  "weight": 0.5
},
{
  "check": "code_snippets_under_limit('research.md', 20)",
  "weight": 1.0
}
```

**Evidences:**
```
- evals/suite.json (all 15 test cases)
- evals/fixtures/ (ticket/question/design/research fixtures for each scenario)
- evals/golden/ (expected output references)
- evals/graphite-evals.json (Graphite-specific eval cases with command_check, flag_check, safety_check, content_check, workflow_check types)
```

**Implicit contract:** Each test case references fixture files in `evals/fixtures/` that represent the input artifacts (tickets, questions, research, design, etc.). The LLM-judged assertions require specific quality patterns in the output artifacts.

---

## Q14: Which `argocd` CLI subcommands provide health status, sync status, and operation state for monitoring?

**Answer:** Several subcommands provide observability data:

**`argocd app get`** (primary monitoring command):
- `--output json|yaml` — Full structured output including status fields
- `--show-operation` — Display the current operation state (sync/rollback in progress)
- `--show-params` — Show application parameters and overrides
- `--refresh` / `--hard-refresh` — Force refresh before retrieving

**Status fields returned (from `ApplicationStatus`):**

```go
// pkg/apis/application/v1alpha1/types.go
type ApplicationStatus struct {
    Resources []ResourceStatus `json:"resources,omitempty"`
    Sync      SyncStatus       `json:"sync,omitempty"`
    Health    HealthStatus     `json:"health,omitempty"`
    History   RevisionHistories `json:"history,omitempty"`
    Conditions []ApplicationCondition `json:"conditions,omitempty"`
    ReconciledAt *metav1.Time `json:"reconciledAt,omitempty"`
    OperationState *OperationState `json:"operationState,omitempty"`
}

type OperationState struct {
    Operation   Operation          `json:"operation"`
    Phase       synccommon.OperationPhase  // Pending, Running, Terminate, Error, Canceled, Success
    Message     string              `json:"message,omitempty"`
    SyncResult  *SyncOperationResult `json:"syncResult,omitempty"`
    StartedAt   metav1.Time         `json:"startedAt"`
    FinishedAt  *metav1.Time        `json:"finishedAt,omitempty"`
    RetryCount  int64               `json:"retryCount,omitempty"`
}
```

**`argocd app list`** — Provides a table overview of sync status and health for all applications (default `--output wide`):
- `--selector/-l` — Filter by label
- `--project/-p` — Filter by project
- `--cluster/-c` — Filter by cluster

**`argocd app diff`** — Reports drift between desired and live state:
- Exit code 1 = out of sync (useful for monitoring scripts)
- `--exit-code` — Explicit exit code signaling
- `--diff-exit-code <n>` — Custom exit code

**`argocd app wait`** — Wait for application to reach a target state:
- `--output json|yaml|wide|tree|tree=detailed`
- Blocks until sync is complete or timeout

**Health and sync info for agents:**
- `SyncStatus` contains `Status` (Synced/OutOfSync), `ComparedTo` (source info), and `Revision`
- `HealthStatus` contains `Status` (Healthy/Degraded/Unknown/Pending) and `Message`
- `OperationState.Phase` tracks sync progress: Pending → Running → (Success|Error|Canceled)
- `OperationState.Message` contains human-readable progress/error details
- `Conditions` list contains typed application-level conditions

---

## Discovered Patterns

1. **Persistent flag inheritance:** All global CLI options are registered as `PersistentFlags` on the root command, meaning every subcommand automatically inherits them. This creates a single configuration entry point (`root.go`) for server connection, auth, TLS, and logging.

2. **ARGOCD_OPTS + config.GetFlag dual-resolution:** The CLI resolves flags in a three-tier chain: (1) explicit CLI flag > (2) ARGOCD_OPTS parsed map > (3) environment variable fallback or hardcoded default. This enables progressive configuration override.

3. **Optimistic locking for concurrency:** Application CRUD operations use an optimistic locking pattern with up to 10 retry attempts. This is the standard mechanism for handling concurrent agent access.

4. **Uniform output rendering:** All subcommands that support structured output use `PrintResource()` from `common.go`, which dispatches on the format string. The wide/table format uses custom formatters, while json/yaml use standard Go marshaling.

5. **Local config as single source of truth:** `~/.config/argocd/argocd.yaml` stores all persistent state: contexts, servers, users, tokens, certificates, and prompt preferences. The context command reads/writes this file directly.

6. **Flag-driven automation:** The CLI is designed for flag-driven usage. Interactive prompts are opt-in (controlled by `--prompts-enabled` and `localconfig.PromptsEnabled`). Most subcommands have zero interactive paths when required flags are supplied.

7. **Phase-based sync model:** Sync operations follow a strict phase-waves model (PreSync → Sync → PostSync, each with ordered waves). Hooks are first-class resources marked with annotations, not special Kubernetes objects.

---

## Inconsistencies

1. **`--server-side-apply` vs `--server-side`:** The sync command flag is `--server-side` (not `--server-side-apply`), but its help text says "Use server-side apply". The flag naming is inconsistent with the kubectl convention.

2. **`--diff-exit-code` defaults to 20:** The diff command's default exit code for "diff found" is 1, but `--diff-exit-code` defaults to 20. This non-standard default (common convention is 1 or 2) may surprise monitoring scripts.

3. **`app get --output` differs from `app list --output`:** `app get` supports `tree` format but not `name`, while `app list` supports `name` but not `tree`. These are related subcommands with asymmetric output options.

4. **Project vs admin token distinction is invisible at CLI level:** The CLI generates all tokens identically regardless of account type. Project-scoped permissions are enforced purely server-side. The CLI cannot indicate whether a token is project-scoped or admin-level.

5. **`--local` diff has no Git verification:** When using `--local`, the CLI does not validate that the specified path is a Git repository or that the manifests are valid Kubernetes resources. It simply reads and processes whatever files exist at the path.

6. **No `--yes` flag on `login`:** The login command has no `--yes` or `--assume-yes` flag to bypass TLS warnings or credential prompts. The only automation path is pre-supplying all required flags (`--username`, `--password`, or `--sso`).

7. **Token expiration defaults to unlimited:** `argocd account generate-token --expires-in` defaults to no expiration. This is a security concern for automated workflows that may leave long-lived tokens in local config or environment variables.

8. **Config file format is opaque:** The local config (`argocd.yaml`) is serialized YAML/JSON with no version header or schema validation. Breaking changes in the struct definitions could corrupt existing config files.
