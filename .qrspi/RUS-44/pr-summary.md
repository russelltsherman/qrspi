# PR: RUS-44 Add a standalone ASCII slugify utility + test

**Ticket:** RUS-44
**Design:** design.md @ 2026-06-01T00:00:00Z
**Structure:** structure.md @ 2026-06-01T00:00:00Z

## Summary

Adds a self-contained, stdlib-only slug utility to `scripts/`: a pure function
`slugify(text: str) -> str` that lowercases input, collapses each run of
non-`[a-z0-9]` characters into a single hyphen, and strips edge hyphens, plus a
thin `argparse` CLI and a co-located assert-based test. The behavior is
deliberately ASCII-only and lossy on non-ASCII input (`"Café"` -> `"caf"`) to
keep output unambiguously filesystem-safe; this is pinned by a unicode test
case. Reviewers should focus on (1) the ASCII-only unicode policy, since it
drops accented letters rather than transliterating, and (2) `slugify_test.py`,
which is the repo's first co-located `*_test.py` and establishes a new test-file
convention (flagged as a NEW PATTERN in design Decision 3). No existing files
were modified; the documentation-alignment slice was a verified no-op (see
Deviations).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Pure `slugify(text: str) -> str` lowercases, collapses non-alnum runs to one hyphen, strips edges, no consecutive hyphens, no side effects | `scripts/slugify.py:slugify` | `scripts/slugify_test.py:main` (all asserts) |
| AC2: `slugify("")` -> `""` | `scripts/slugify.py:slugify` | `scripts/slugify_test.py:main` (`slugify("") == ""`) |
| AC3: `slugify("  Hello,  World!! ")` -> `"hello-world"` | `scripts/slugify.py:slugify` | `scripts/slugify_test.py:main` (`"hello-world"` assert) |
| AC4: `slugify("RUS-44: Add a thing")` -> `"rus-44-add-a-thing"` | `scripts/slugify.py:slugify` | `scripts/slugify_test.py:main` (`"rus-44-add-a-thing"` assert) |
| AC5: All-symbol input returns `""` | `scripts/slugify.py:slugify` (`.strip("-")`) | `scripts/slugify_test.py:main` (`slugify("!!!") == ""`) |
| AC6: ASCII-only / lossy unicode (`"Café"` -> `"caf"`) | `scripts/slugify.py:slugify` (`[^a-z0-9]+`) | `scripts/slugify_test.py:main` (`slugify("Café") == "caf"`) |
| AC7: CLI prints slug to stdout, exits 0 | `scripts/slugify.py:main` | Manual: `python3 scripts/slugify.py "Some Title"` -> `some-title`, exit 0 |
| AC8: Missing CLI arg -> argparse usage/error to stderr, non-zero exit | `scripts/slugify.py:main` (positional `text`) | Manual: `python3 scripts/slugify.py` -> stderr, exit 2 |
| AC9: Stdlib only, no imports from other repo modules | `scripts/slugify.py` (`argparse`, `re`, `sys`); `scripts/slugify_test.py` (`os`, `sys`, sibling `slugify`) | Verification checkpoint (impl-log Session 1): imports are stdlib-only |
| AC10: Test is stdlib-only, assert-based, runner exits 0 on pass / non-zero on failure | `scripts/slugify_test.py:main` | `python3 scripts/slugify_test.py` -> `PASS: slugify_test`, exit 0 |

## Changes by Slice

### Slice 1: slugify module + co-located test

| File | Change | Lines |
|------|--------|-------|
| `scripts/slugify.py` | ✨ new (mode 100755) | +31 |
| `scripts/slugify_test.py` | ✨ new (mode 100755) | +29 |

### Slice 2: documentation alignment (no-op)

| File | Change | Lines |
|------|--------|-------|
| (none) | no qualifying doc enumerates `scripts/` utilities | 0 |

### Non-feature: QRSPI planning artifacts

These are workflow metadata committed on the ticket branch, not feature code.
Listed here so every file in `git diff main...HEAD` is accounted for.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-44/questions.md` | ✨ new | +47 |
| `.qrspi/RUS-44/research.md` | ✨ new | +181 |
| `.qrspi/RUS-44/design.md` | ✨ new | +90 |
| `.qrspi/RUS-44/structure.md` | ✨ new | +53 |
| `.qrspi/RUS-44/plan.md` | ✨ new | +83 |
| `.qrspi/RUS-44/worktree.md` | ✨ new | +43 |
| `.qrspi/RUS-44/impl-log.md` | ✨ new | +68 |

## Testing Summary

- [x] Slice 1: unit/assert tests — `python3 scripts/slugify_test.py` — 5 asserts passed, 0 failed (exit 0, prints `PASS: slugify_test`)
- [x] Slice 1: CLI happy path — `python3 scripts/slugify.py "Some Title"` — prints `some-title`, exit 0
- [x] Slice 1: CLI error path — `python3 scripts/slugify.py` (no arg) — argparse usage/error to stderr, exit 2 (non-zero)
- [x] Slice 1: dependency isolation — imports confirmed stdlib-only (`re`, `sys`, `argparse`, `os`); no imports from other repo modules
- [x] Slice 2: docs scan — `grep -rln -e "check_scope" -e "diagnose" -e "scripts/" --include="*.md" .` and `grep -rln "slugify" --include="*.md" .` — no project doc enumerates `scripts/` utilities; `git diff --name-only` empty for this slice (no-op confirmed)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Slice 2 doc edits | Update any doc enumerating `scripts/` utilities to add `scripts/slugify.py` | No edits made (no-op) | No project doc generically enumerates `scripts/` utilities. The only enumeration (`docs/eval-system.md`) is the eval pipeline's closed 5-stage list; `slugify.py` is not an eval stage, so adding it would inject false information. Matches structure §Slice 2 documented no-op contingency. (impl-log Session 2, T10/T11) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Unicode policy mismatch — reviewer expects accented letters preserved; design drops them (Option A) | accepted — lossy ASCII behavior documented in module docstring and pinned by `slugify("Café") == "caf"` assert | Revise regex to a unicode-aware pattern; update the unicode assert |
| Test import resolution fails depending on invocation cwd | mitigated — Option B `sys.path.insert(0, dirname(__file__))` makes the sibling import cwd-independent; run command documented in test docstring | Remove `sys.path` insert and run with `scripts/` on the path (Option A) |
| New `*_test.py` convention conflicts with a future repo-wide standard | accepted — first co-located test, greenfield; e2e-throwaway ticket, safe to discard | Delete `scripts/slugify_test.py`; no other file depends on it |
| CLI parses a leading-hyphen title as a flag | accepted — positional `text` argument; `--` separates flags from positionals | Pass titles after `--`, or add explicit handling |
| (Rollback for the whole change) | n/a | Both new files are self-contained and imported by nothing else; deleting `scripts/slugify.py` and `scripts/slugify_test.py` fully reverts the feature |

## Open Items

- Slice 2 made no documentation edits. If a future general `scripts/` index/README is created, that is the correct home for a `slugify.py` entry — `docs/eval-system.md`'s eval-pipeline list is not. (impl-log Session 2 notes)
- Decision 3 shipped Option B (`sys.path` insert) per the design recommendation; the reviewer may still prefer Option A's plain sibling import. Low-impact swap within `scripts/slugify_test.py` if desired.
- This is an `[e2e-throwaway]` ticket; the utility is intentionally not integrated into any QRSPI workflow, SKILL, or existing script (out of scope per ticket).
