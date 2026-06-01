# Questions — [e2e-throwaway] Add a standalone slugify utility

**Ticket:** RUS-44
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does an input string travel from the CLI argument through to the printed slug, and what transformation steps occur in between (lowercasing, non-alphanumeric replacement, hyphen stripping)?
  **Target:** `scripts/slugify.py` — the `slugify(text: str) -> str` function
- Q2: What regular expression or character-class logic identifies a "run of non-alphanumeric characters," and does it operate on the raw input before or after lowercasing?
  **Target:** `scripts/slugify.py` — the `slugify` transformation body

## API Surface

- Q3: What is the exact signature, return type, and docstring of the public `slugify` function, and is anything else exported from the module?
  **Target:** `scripts/slugify.py` — the `slugify` function definition
- Q4: How does the CLI entrypoint parse the title argument, invoke `slugify`, print the result, and set the exit code to 0?
  **Target:** `scripts/slugify.py` — the `__main__` / CLI block

## State Management

- Q5: Is `slugify` implemented as a pure function with no module-level mutable state, caching, or side effects beyond the CLI print path?
  **Target:** `scripts/slugify.py` — module-level scope and the `slugify` function

## Edge Cases

- Q6: How are the empty string, leading/trailing whitespace, and consecutive non-alphanumeric runs handled so that `slugify("")` returns `""` and `slugify("  Hello,  World!! ")` returns `"hello-world"` with no consecutive or edge hyphens?
  **Target:** `scripts/slugify.py` — the hyphen-collapsing and stripping logic
- Q7: How is an all-symbol input (e.g. a string containing only punctuation) handled, and what does the function return when every character is non-alphanumeric?
  **Target:** `scripts/slugify.py` — the `slugify` function
- Q8: How are unicode characters classified as alphanumeric or non-alphanumeric, and does the chosen regex/character test treat accented or non-ASCII letters as alphanumeric or as separators?
  **Target:** `scripts/slugify.py` — the non-alphanumeric matching logic

## Testing

- Q9: How do the assert-based tests cover the ticket's specified cases (`""`, `"  Hello,  World!! "`, `"RUS-44: Add a thing"`) plus the unicode and all-symbol cases, and are they stdlib-only with no third-party test framework?
  **Target:** `scripts/slugify_test.py`
- Q10: How does `scripts/slugify_test.py` import the `slugify` function under test without importing any other repository module?
  **Target:** `scripts/slugify_test.py` — its import statements
- Q11: How are the tests executed and what signals pass versus failure (exit code, assertion error output)?
  **Target:** `scripts/slugify_test.py` — its `__main__` / runner block

## Observability

- Q12: What does the CLI emit on stdout versus stderr, and how would a caller distinguish a successful slug output from an invocation error (e.g. missing argument)?
  **Target:** `scripts/slugify.py` — the CLI output and exit-code handling
