# Matrix Strategy Examples

`strategy.matrix` fans one job definition out into parallel variants. Use it for
cross-version / cross-OS test grids and any "same steps, different parameters"
shape.

## Basic matrix

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false          # see below — usually what you want for test grids
      matrix:
        os: [ubuntu-24.04, macos-14, windows-2022]
        node: ['20', '22']
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
        with:
          node-version: ${{ matrix.node }}
          cache: npm
      - run: npm ci
      - run: npm test
```

This expands to 3 × 2 = 6 parallel jobs.

## `fail-fast`

- `fail-fast: true` (default) — the first failing variant **cancels all other
  in-progress variants**. Good for fast feedback / saving minutes.
- `fail-fast: false` — let every variant finish so you see the **full** matrix of
  pass/fail. Preferred for test grids where you want to know *which*
  OS/version combinations break, not just that one did.

## `include` — add or extend specific combinations

`include` appends extra combinations, or adds keys to combinations that already
match every listed key.

```yaml
strategy:
  matrix:
    os: [ubuntu-24.04, macos-14]
    node: ['20', '22']
    include:
      # extra one-off combination not in the base grid
      - os: ubuntu-24.04
        node: '23'
        experimental: true
      # add a key to an existing combination
      - os: macos-14
        node: '22'
        coverage: true
```

## `exclude` — prune combinations from the grid

```yaml
strategy:
  matrix:
    os: [ubuntu-24.04, macos-14, windows-2022]
    node: ['20', '22']
    exclude:
      # skip an unsupported/expensive combination
      - os: windows-2022
        node: '20'
```

Evaluation order: build the base product → remove `exclude` → append `include`.

## Cache-key isolation per matrix leg

Variants share a cache namespace unless you isolate keys, or one leg's cache
poisons another (e.g. Linux artifacts restored on Windows).

```yaml
- uses: actions/cache@6849a6489940f00c2f30c0fb92c6274307ccb58a # v4.1.2
  with:
    path: ~/.npm
    # include every matrix axis that changes the cache contents
    key: npm-${{ matrix.os }}-${{ matrix.node }}-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      npm-${{ matrix.os }}-${{ matrix.node }}-
```

Rules of thumb:

- Put every cache-affecting matrix axis (`os`, language version, arch) into the
  `key`.
- Anchor the key with a lockfile hash so dependency changes invalidate it.
- Use `restore-keys` for graceful partial-hit fallback **within the same leg**.

## Limits

- A matrix generates at most **256** jobs per workflow run.
- Cap concurrency with `strategy.max-parallel` when you must throttle runners.
