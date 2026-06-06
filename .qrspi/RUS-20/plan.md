# Implementation Plan — Create a new agent skill using aws cli

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Author the `aws-cli` skill (SKILL.md + references)

### Setup

1. ✨ Create `.claude/skills/aws-cli/references/jmespath.md` — `--query` JMESPath reference (single-topic, per Topic-partition contract). Cover: field selection/projection, list/map filters (`[?Key==`val`]`), date-range filtering, `--output text` column ordering with `--query`, multi-select hashes for `--output table`. Use placeholder tokens only (Content-hygiene contract).

2. ✨ Create `.claude/skills/aws-cli/references/waiters.md` — built-in waiter reference (single-topic). Cover: `aws <service> wait <condition>` form, common waiters per service (S3 `object-exists`, EC2 `instance-running`/`instance-status-ok`, ECS `services-stable`, Lambda `function-active`, CloudFormation `stack-create-complete`), and the exit-code-255 timeout handling note (ref: design §Delta). Placeholders only.

3. ✨ Create `.claude/skills/aws-cli/references/services.md` — per-service cheat sheets (single-topic: service operations). Cover: S3 high-level `s3` vs `s3api`; EC2 filters/tags/launch templates; ECS deploy/`execute-command`; Lambda deploy/invoke/`--log-type Tail` log decode; IAM `simulate-principal-policy`/least-privilege; CloudFormation `deploy`/change-set/drift detection. Placeholders only (e.g. `<bucket>`, `i-xxx`).

### Core Logic

4. ✨ Create `.claude/skills/aws-cli/SKILL.md` frontmatter — `---`-delimited block with exactly the five `SkillFrontmatter` fields: `name: aws-cli`, `description` (capability clause + "Use when…" trigger clause, per design §Current State Q4), `command: /aws-cli`, `argument-hint`, `allowed-tools`. Satisfies Frontmatter contract: `name == directory name == command (minus /)`.
   - **Note (A1/OQ1):** `allowed-tools` value is an unresolved design choice — a pure reference skill may need only `Bash(aws:*)` or none. Resolve before authoring; flagged in structure Unverified Assumptions.
   - **Note (A2/OQ2):** `argument-hint` value undetermined for a non-positional skill (e.g. empty hint or short topic hint). Resolve before authoring.

5. ✨ Add SKILL.md body — Authentication & Profiles section: SSO over IAM keys, `sts get-caller-identity` verification, named profiles, `role_arn`/`source_profile`/`external_id`, CI/CD assume-role (ref: design §Desired End State). Same file as step 4.

6. ✨ Add SKILL.md body — Environment & Config, Output Formatting & Filtering (`--query`, `--output`, `AWS_PAGER`), and Pagination sections; link `references/jmespath.md` by relative path (Reference-link contract). Same file.

7. ✨ Add SKILL.md body — Waiters section with concise guidance; link `references/waiters.md` by relative path. Same file.

8. ✨ Add SKILL.md body — per-service operations sections (S3, EC2, ECS, Lambda, IAM, CloudFormation), concise directives; link `references/services.md` by relative path (Body-coverage + Budget contracts: delegate deep detail). Same file.

9. ✨ Add SKILL.md body — Error Handling & Scripting (exit codes, retries, idempotency), Security (`Do NOT/Never` imperatives per Security-as-imperatives contract / Decision 2), and `## Scope` (raw `aws` CLI in-scope; Terraform/CDK/Pulumi out-of-scope) sections. Same file.

### Tests

10. ✨ Invoke the skill-creator (Anthropic skill builder) skill against `.claude/skills/aws-cli/` as the in-slice validation step; record its use for the PR description (ref: design Risk register, Q3/Q12).
    - **Note (A3/OQ3):** skill-creator is a harness-level/global skill, possibly absent from the implementing environment. If unavailable, hand-author to the same standard and note the substitution — this affects one verification checkbox.

11. Run: `python3 - <<'PY'` content-and-link check (frontmatter five fields, relative links resolve, hygiene grep) — or equivalent shell checks in step 14. See Verify.
    - **Expected:** five frontmatter fields present; every `references/<topic>.md` link resolves to an existing sibling; no account-ID/region/resource-name patterns, only placeholders.

### Verify Slice 1

12. **Checkpoint:** `test -f .claude/skills/aws-cli/SKILL.md && test -f .claude/skills/aws-cli/references/jmespath.md && test -f .claude/skills/aws-cli/references/waiters.md && test -f .claude/skills/aws-cli/references/services.md && echo OK`
    - [ ] All four files exist (SKILL.md + three single-topic references).

13. **Checkpoint:** `awk 'NR==1{exit !/^---$/} /^---$/{c++} c==1 && /^(name|description|command|argument-hint|allowed-tools):/{f++} c==2{print f; exit}' .claude/skills/aws-cli/SKILL.md` and `grep -oE 'references/[a-z-]+\.md' .claude/skills/aws-cli/SKILL.md | sort -u | while read p; do test -f ".claude/skills/aws-cli/$p" || echo "BROKEN: $p"; done`
    - [ ] Frontmatter contract: exactly five fields; `name`==`aws-cli`==`command` minus `/`.
    - [ ] Reference-link contract: every `references/*.md` link resolves (no BROKEN output).

14. **Checkpoint:** `wc -l .claude/skills/aws-cli/SKILL.md` and `grep -rniE '[0-9]{12}|us-(east|west)-[0-9]|eu-(west|central)-[0-9]|arn:aws:[a-z]+:[a-z0-9-]+:[0-9]{12}' .claude/skills/aws-cli/`
    - [ ] Budget contract: SKILL.md body under 500 lines (token estimate under 5000).
    - [ ] Body-coverage contract: sections present for auth, env/config, formatting, pagination, waiters, six services, error/scripting, security, scope.
    - [ ] Content-hygiene contract: grep returns no real account IDs / regions / ARNs — placeholders only.
    - [ ] skill-creator invoked (or hand-authored substitution noted per A3) and recorded for PR description.
    - [ ] Live trigger: in a Claude Code session, confirm `description` fires `/aws-cli` auto-invocation (manual end-to-end, ref: Q11).

---

## Rollback Notes

- Steps 1–9: all create new files under `.claude/skills/aws-cli/`. No existing file is modified and no loader registration exists (ref: structure Modified Types: None), so rollback is `rm -rf .claude/skills/aws-cli/` — no other code or config is affected.
- No DB migrations, config changes, or destructive operations in this plan.
