# Testing strategies

Depth content for the SKILL.md "Testing" section. Layer these from fast/cheap to
slow/live.

## 1. Lint

```bash
helm lint ./chart --strict
helm lint ./chart -f values.prod.yaml      # lint with real values + schema
```

Catches template syntax, missing required values (against
`values.schema.json`), and chart metadata problems. Fast, run on every commit.

## 2. helm-unittest (template unit tests)

Plugin: `helm plugin install https://github.com/helm-unittest/helm-unittest`.
Define expectations against rendered templates without a cluster:

```yaml
# chart/tests/deployment_test.yaml
suite: deployment
templates:
  - templates/deployment.yaml
tests:
  - it: sets the image tag
    set:
      image.tag: "1.4.2"
    asserts:
      - equal:
          path: spec.template.spec.containers[0].image
          value: registry.example.com/app:1.4.2
      - isKind:
          of: Deployment
```

```bash
helm unittest ./chart
```

Fast, deterministic, no cluster — the workhorse for chart logic.

## 3. Template-against-policy

Render and assert org policy with conftest (OPA) or kyverno CLI:

```bash
helm template ./chart -f values.prod.yaml | conftest test -
helm template ./chart -f values.prod.yaml | kyverno apply policies/ --resource -
```

Enforces things like "all containers set resource limits", "no `latest` tags",
"runAsNonRoot". Runs in CI before publish.

## 4. Schema validation

`values.schema.json` is exercised automatically by `lint`, `template`, and
`install`; keep schema tests in the helm-unittest suite (assert that invalid
values fail). See `values-patterns.md`.

## 5. Live `helm test`

```bash
helm test my-release -n prod --logs
```

Runs resources annotated `helm.sh/hook: test` (typically a Job that curls the
service or runs a connectivity check) against the **actually deployed** release.
Use as a post-deploy smoke gate; keep these tests fast and idempotent.

## Suggested CI ordering

`lint` → `helm unittest` → `helm template | policy` → publish → deploy to staging
→ `helm test` smoke. Fail fast on the cheap stages.
