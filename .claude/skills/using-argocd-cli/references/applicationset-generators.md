# ApplicationSet Generators

Deep reference for templating many Applications from a single resource. Loaded on demand
from the skill body's App-of-Apps and ApplicationSets sections.

## When to move from app-of-apps to ApplicationSet

The **app-of-apps** pattern (one parent Application whose manifests are child
Applications) is fine for a small, hand-curated, mostly-static set of apps. Switch to an
**ApplicationSet** when:

- you are templating the *same* app across many targets (environments, clusters, teams,
  or repo directories) and copy-pasting child Application YAML;
- the set of apps is **dynamic** — it should grow/shrink as clusters register or as
  directories/branches appear in Git, without a human editing a parent manifest;
- you want one controller to add **and remove** Applications automatically as the
  generated set changes.

Rule of thumb: a fixed handful of distinct apps → app-of-apps; a fleet of structurally
identical apps fanned across N targets → ApplicationSet.

## Generators

An ApplicationSet has a `generators:` list that produces parameter sets, and a
`template:` rendered once per parameter set.

- **List** — hard-coded inline parameter sets. Simplest; good for a known, small,
  explicit list of targets.
- **Git** — generates one app per directory (`directories:`) or per matching file
  (`files:`, e.g. each `config.json`) in a repo. The fleet tracks Git: add a directory,
  get an app. Ideal for monorepo-of-environments layouts.
- **Cluster** — generates one app per cluster registered in Argo CD (optionally filtered
  by label selector). The fleet tracks cluster registration: register a cluster, the app
  deploys there automatically.
- **Matrix** — takes the **Cartesian product** of two child generators (e.g. Git
  directories × clusters → every app on every cluster). The standard tool for "deploy
  each of these apps to each of these clusters."

Other generators (SCM Provider, Pull Request, Cluster Decision Resource) exist for
repo-discovery and ephemeral PR-preview use cases.

## Controlling deletion

By default, removing a generated entry **deletes** the corresponding Application (and its
live resources). To keep the live resources when an app leaves the generated set:

```yaml
spec:
  syncPolicy:
    preserveResourcesOnDeletion: true
```

`preserveResourcesOnDeletion: true` removes the Application object but **leaves the
deployed workloads running** — a safety valve so a cluster de-registering or a directory
removal does not silently tear down production resources. Set it on any ApplicationSet
whose generated targets can churn unexpectedly.
