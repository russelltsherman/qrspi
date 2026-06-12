---
name: qrspi-critic
description: Judge a produced QRSPI phase artifact as a faithful derivation of its upstream input, returning a {pass, findings} edge-critic verdict. Use to critique a design/plan/etc. artifact against the upstream artifact it was derived from — reviewing the EDGE (the transformation), not the node. Normally spawned by runCriticLoop in qrspi-batch.js; invoke directly for a standalone critic check of one upstream→produced artifact pair.
command: /qrspi-critic
argument-hint: <upstream-path> <artifact-path> [rubric]
allowed-tools: Agent, Bash(pwd:*)
---

# /qrspi-critic

Thin wrapper that spawns the `qrspi-critic` agent. All prompt content lives in `.claude/agents/qrspi-critic.md`. The agent reads the upstream artifact (its rubric anchor) and the produced artifact, then returns a structured `{pass, findings}` verdict judging whether the produced artifact faithfully derives from its upstream input.

## Steps

1. Parse `$ARGUMENTS` into `<upstream-path>`, `<artifact-path>`, and an optional trailing `[rubric]` (everything after the second token is the rubric text; empty when omitted).
2. Resolve `REPO_ROOT` from `pwd`. Resolve any relative `<upstream-path>`/`<artifact-path>` against `REPO_ROOT` so both are absolute.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-critic`
   - Prompt body containing the inputs:
     - `UPSTREAM_PATH = <absolute upstream-path>`
     - `ARTIFACT_PATH = <absolute artifact-path>`
     - `RUBRIC = <rubric text, or omit the line when none was supplied>`
4. Report the returned verdict: `pass` (true/false) and the `findings` list. On `pass: false`, surface each finding so the upstream requirement it names is visible.
