# Questions — Create a new agent skill called using graphite cli
**Ticket:** RUS-6
**Generated:** 2026-05-26T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the existing skill-creator skill discover and load a SKILL.md file — what directory structure, file naming, and frontmatter fields does it validate during skill ingestion?
  **Target:** the skill-creator skill (SKILL.md and associated loader/validator)

- Q2: When a skill is registered in `.claude/settings.json`, what exact schema and key structure does the harness expect for the skill entry, and how does it resolve the `SKILL.md` path relative to the project root?
  **Target:** `.claude/settings.json` and the skill registration mechanism

- Q3: What is the data flow when a skill's `references/` directory is loaded — are reference files injected into context at skill invocation time, on demand via explicit read, or pre-indexed at registration?
  **Target:** the module responsible for skill reference resolution

## API Surface

- Q4: What frontmatter fields does the agentskills.io standard require in SKILL.md, and which fields does the skill-creator skill enforce as mandatory vs. optional during generation?
  **Target:** the skill-creator skill's SKILL.md template and validation logic

- Q5: What is the maximum token budget the harness enforces for a skill's SKILL.md body content, and how is that limit measured (raw token count, line count, or both)?
  **Target:** the module responsible for skill size validation

- Q6: How does the skill-creator skill's eval loop work — what inputs does it accept, what assertions does it run, and what output format does it produce for pass/fail determination?
  **Target:** the skill-creator skill's eval harness (`evals/` or equivalent)

## State Management

- Q7: When multiple skills are registered, how does the harness determine trigger priority — is there an explicit ordering, a scoring mechanism based on the description field, or first-match semantics?
  **Target:** the module responsible for skill trigger matching and selection

- Q8: If a skill references CLI tools that may not be installed (e.g., `gt`), does the harness or skill loader perform any pre-invocation availability check, or is failure deferred to runtime execution?
  **Target:** the module responsible for skill pre-condition evaluation

## Edge Cases

- Q9: What happens when two registered skills have overlapping trigger descriptions — for example, if both a `using-graphite-cli` skill and a generic `git-workflow` skill match a user request involving branch creation?
  **Target:** the skill trigger matching and disambiguation module

- Q10: If a skill's SKILL.md body exceeds the 500-line or 5000-token limit specified in the acceptance criteria, does the skill-creator skill reject it at generation time, at registration time, or does it silently truncate?
  **Target:** the skill-creator skill's validation step

- Q11: How does the harness behave when a skill's SKILL.md references a `scripts/` or `assets/` subdirectory that does not exist on disk — does it fail loudly, skip silently, or produce a warning?
  **Target:** the skill loader and directory resolution module

## Testing

- Q12: What existing eval patterns or test fixtures exist for other skills in this project, and what is the expected structure of a skill eval (input prompt, expected behavior, assertion format)?
  **Target:** `evals/` directory and any existing skill test configurations

- Q13: Does the skill-creator skill produce eval cases automatically as part of skill generation, or must they be authored separately after the SKILL.md is created?
  **Target:** the skill-creator skill's generation pipeline

## Observability

- Q14: When a skill is triggered and executed, what logging or tracing does the harness emit — are there log lines indicating which skill was selected, why it matched, and how long execution took?
  **Target:** the module responsible for skill execution lifecycle logging
