# Questions — Add a standalone slugify utility

**Ticket:** RUS-44
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What is the exact transformation order applied to the input string (lowercasing, non-alphanumeric replacement, hyphen stripping) and at which step is each acceptance-criteria case satisfied?
  **Target:** `scripts/slugify.py` — the `slugify(text: str) -> str` function
- Q2: How is "non-alphanumeric" defined for the run-collapsing step — does it operate on ASCII only, or on the full Unicode notion of alphanumeric, and how does that determine the output for unicode input?
  **Target:** `scripts/slugify.py` — the character-classification logic inside `slugify`

## API Surface

- Q3: What is the signature, return type, and docstring contract of the public `slugify` function, and does it expose any parameters beyond `text`?
  **Target:** `scripts/slugify.py` — the `slugify` function definition
- Q4: How does the CLI entry point read its argument, invoke `slugify`, print the result, and set the exit code, and is it guarded by an `if __name__ == "__main__"` block?
  **Target:** `scripts/slugify.py` — the module-level CLI / `main` block

## State Management

- Q5: Is `slugify` implemented as a pure function with no module-level mutable state, caches, or side effects beyond returning a value?
  **Target:** `scripts/slugify.py` — module-level scope and the `slugify` function body
- Q6: Which standard-library modules does `scripts/slugify.py` import, and does it import any module from elsewhere in the repository?
  **Target:** `scripts/slugify.py` — the import statements

## Edge Cases

- Q7: What does `slugify` return for empty input `""` and for all-symbol input (e.g. a string of only punctuation), and where in the function is the empty-result case produced?
  **Target:** `scripts/slugify.py` — the hyphen-stripping and empty-string handling
- Q8: How does the function handle leading, trailing, and consecutive runs of non-alphanumeric characters so that no leading, trailing, or consecutive hyphens appear in the output?
  **Target:** `scripts/slugify.py` — the hyphen-collapsing and strip logic
- Q9: How is unicode input (e.g. accented or non-Latin characters) treated — preserved, transliterated, or dropped — and what slug does the corresponding test expect?
  **Target:** `scripts/slugify_test.py` and `scripts/slugify.py` — the unicode handling path

## Testing

- Q10: Which input/output cases does `scripts/slugify_test.py` assert, and does it cover the three documented examples plus unicode and all-symbol input?
  **Target:** `scripts/slugify_test.py` — the assert-based test cases
- Q11: How is the test invoked and what defines pass/fail — is it a plain `python3 scripts/slugify_test.py` run using bare `assert` statements with no third-party test framework?
  **Target:** `scripts/slugify_test.py` — the runner/entry structure and imports

## Observability

- Q12: When the CLI is run, what exactly is written to stdout versus stderr, and what exit codes are produced for valid input, missing arguments, or other failure modes?
  **Target:** `scripts/slugify.py` — the CLI output and exit-code handling
