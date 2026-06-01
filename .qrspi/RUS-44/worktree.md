# Work Tree — [e2e-throwaway] Add a standalone slugify utility

**Plan basis:** plan.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T14

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1, design.md §Delta, design.md Decisions 1–3
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/slugify.py` skeleton — shebang, docstring noting ASCII-only lossy-unicode behavior, `import re`, `import sys`, `import argparse` | — | §1 | S | pending |
| T2 | Add `slugify(text: str) -> str` — pure function, `re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")` | T1 | §2 | S | pending |
| T3 | Add `main() -> None` — argparse parser, required positional `text`, call slugify, print, `sys.exit(0)` | T2 | §3 | S | pending |
| T4 | Add `if __name__ == "__main__":` entrypoint guard calling `main()` | T3 | §4 | S | pending |
| T5 | Create `scripts/slugify_test.py` skeleton — shebang, docstring with run command, `import os`, `import sys` | T4 | §5 | S | pending |
| T6 | Add import-resolution block — `sys.path.insert(...)` then `from slugify import slugify` (see plan note re: Decision 3 Option A/B) | T5 | §6 | S | pending |
| T7 | Add assert cases + runner — `main()` with five `assert slugify(...) == ...` checks, pass marker, `sys.exit(0)`, entrypoint guard | T6 | §7 | S | pending |
| T8 | Run `python3 scripts/slugify_test.py` from repo root — expect exit 0 + pass marker | T7 | §8 | S | pending |
| T9 | **Verify Slice 1** — checkpoint: test exits 0, `slugify.py "Some Title"` prints `some-title`, no-arg exits non-zero, stdlib-only imports | T8 | §9 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (code + test) complete. Slice 2 is documentation-only and depends only on the existence of `scripts/slugify.py`, not on any in-memory state from Slice 1. Fresh context drops the Python implementation detail in favor of doc-discovery scope.

## Session 2

**Load:** structure.md §Slice 2, structure.md §Unverified Assumptions, plan.md §Slice 2, plan.md §Rollback Notes, design.md §Delta (documentation alignment), impl-log.md §Slice 1 (notes only — final `slugify.py` path + CLI usage)
**Estimated context:** ~8% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Discovery — `grep -rln -e "check_scope" -e "diagnose" -e "scripts/" --include="*.md" .`; inspect hits for `scripts/` utility lists. If none, Slice 2 is a no-op (record, skip T11–T12) | T9 | §10 | S | pending |
| T11 | Modify each doc found in T10 that enumerates `scripts/` utilities — add `scripts/slugify.py` entry (purpose + CLI usage). Docs-only, no code/SKILL/workflow/script edits | T10 | §11 | S | pending |
| T12 | Re-run T10 discovery search; visually confirm every `scripts/` enumeration now includes `scripts/slugify.py` | T11 | §12 | S | pending |
| T13 | **Verify Slice 2** — checkpoint: `grep -rln "slugify" --include="*.md" .`; all `scripts/` enumerations updated (or recorded none exist); `git diff --name-only` shows only `*.md` for this slice | T12 | §13 | S | pending |
| T14 | **Final gate** — confirm both checkpoints (T9, T13) satisfied; change set limited to `scripts/slugify.py`, `scripts/slugify_test.py`, and docs only | T13 | §14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of plan. No further sessions; T14 is the terminal gate.
