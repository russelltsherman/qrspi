# Work Tree — [e2e-throwaway] Add a standalone slugify utility

**Plan basis:** plan.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1 files, plan.md §Slice 1
**Estimated context:** ~10% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/slugify.py` with shebang + module docstring (ASCII-only / lossy-unicode behavior + CLI run command) | — | §1 | S | pending |
| T2 | Add stdlib imports `re`, `sys`, `argparse` under the docstring | T1 | §2 | S | pending |
| T3 | Implement pure `slugify(text: str) -> str` via `re.sub(...).strip("-")` | T2 | §3 | S | pending |
| T4 | Add `main() -> None` with argparse one positional `text`, prints slug, exits 0 | T3 | §4 | S | pending |
| T5 | Append `if __name__ == "__main__": main()` guard | T4 | §5 | S | pending |
| T6 | Create `scripts/slugify_test.py` with shebang + module docstring (invocation command) | — | §6 | S | pending |
| T7 | Add cwd-independent import: `os`, `sys`, `sys.path.insert`, then `from slugify import slugify` | T6, T3 | §7 | S | pending |
| T8 | Add five assert checks (empty, mixed punctuation, ticket-id, unicode lossy `Café`→`caf`, all-symbol) | T7 | §8 | S | pending |
| T9 | Add `main()` pass-marker runner + entry guard | T8 | §9 | S | pending |
| T10 | Run `python3 scripts/slugify_test.py` — confirm exit 0 + pass marker | T9, T5 | §10 | S | pending |
| T11 | **Verify Slice 1** — run checkpoint commands + import-surface check | T10 | §11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Plan is a single slice (11 atomic steps, stdlib-only, two small files). Estimated context stays well under 40%, so one session covers the entire slice through verification. No further sessions required.
