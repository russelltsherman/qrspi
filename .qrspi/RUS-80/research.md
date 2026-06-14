# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Q1: How does `detect_existing` map each planning artifact (`questions, research, design, structure, plan, worktree`) to its `exists and non-empty` boolean, and what file path / read mechanism does it use to decide presence and non-emptiness?

**Answer:** `detect_existing(qrspi_dir)` iterates the module-level `ARTIFACTS` list (`["questions", "research", "design", "structure", "plan", "worktree"]`, `scripts/qrspi_resolve.py:58`) and for each name builds `<qrspi_dir>/<name>.md`. Presence-and-non-emptiness is decided by a single `os.path.getsize(path) > 0` call wrapped in `try/except OSError`: a `> 0` size yields `True`; any `OSError` (missing file, missing dir, unreadable) yields `False`. It does NOT open or read file contents — it only stats the size. A missing directory therefore yields all-`False`. The function is pure given a path. At its one call site (`main`), the path passed is `os.path.join(worktree, ".qrspi", args.ticket)` (`scripts/qrspi_resolve.py:393`), i.e. `<worktree>/.qrspi/<ticket>/`.

**Evidence:**

```python
def detect_existing(qrspi_dir):
    """Map each QRSPI artifact -> True iff `<qrspi_dir>/<name>.md` exists and is
    non-empty. A missing directory yields all-False. Pure given a path..."""
    out = {}
    for name in ARTIFACTS:
        path = os.path.join(qrspi_dir, "%s.md" % name)
        try:
            out[name] = os.path.getsize(path) > 0
        except OSError:
            out[name] = False
    return out
```

— `scripts/qrspi_resolve.py:141-152`

```python
        existing = detect_existing(os.path.join(worktree, ".qrspi", args.ticket))
```

— `scripts/qrspi_resolve.py:393`

**Dependencies:** Upstream caller `main()` provides the worktree path from `setup_worktree()`. Output is folded into the envelope via `build_envelope(..., existing, ...)` (`scripts/qrspi_resolve.py:396`). Downstream consumer is `.claude/workflows/qrspi-batch.js` (`r.existing`, see Q2).
**Implicit contracts:** Artifact filenames are exactly `<name>.md` for the six fixed `ARTIFACTS` names; the canonical directory is `<worktree>/.qrspi/<ticket>/`. Non-emptiness == byte size > 0 (stat only, no content/structural validation). The same `ARTIFACTS` constant is duplicated verbatim in `scripts/qrspi_persist.py:52` — the two must stay in sync.

## Q2: How does the orchestrator consume the artifact-existence map to skip an already-persisted phase, and where is that skip decision applied in the run loop?

**Answer:** The resolver's `existing` map arrives in the JS orchestrator as `r.existing` (the parsed resolve envelope). It is passed as the `existing` argument to `runPhase(...)` for each planning phase (questions, research, design, structure, plan, worktree — `qrspi-batch.js:1480, 1508, 1542, 1603, 1617, 1623`). Inside `runPhase`, the FIRST thing checked is `if (existing && existing[name]) { ... return true }` — i.e. if the resolver reported that phase's artifact present-and-non-empty, `runPhase` logs `reusing existing <name>.md` and returns `true` WITHOUT spawning the producer agent, the node-check, the critic loop, or `persistArtifact`. That early-return is the phase-skip. The skip is applied per-phase at the top of `runPhase`, which is called once per phase by `doDesign`/`doPlan`.

**Evidence:**

```javascript
async function runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig) {
  if (existing && existing[name]) {
    log(`  ${id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:1238-1243`

```javascript
  if (!await runPhase('questions', 'qrspi-questions',
... TEMPLATE_PATH = ${tpl(wd, 'questions.md')}`, r.existing, t.id, 'Design', questionsCritic)) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:1475-1480` (and the analogous calls at 1508, 1542, 1603, 1617, 1623)

**Dependencies:** Upstream `parseResolveEnvelope` (`qrspi-batch.js:224`) supplies `r.existing` from `qrspi_resolve.py`'s envelope. Downstream `runPhase` gates `agent()`/`persistArtifact`.
**Implicit contracts:** `existing[name]` is a boolean keyed by the phase name string. A missing key or falsy `existing` object means "not present → run the phase" (`existing &&` short-circuits). The resolver's presence check (stat > 0) is treated as authoritative for skip — the orchestrator does NOT re-stat the file before reusing it. The coherence pre-check at `qrspi-batch.js:1829-1836` ALSO consumes `r.existing` (`const ex = r.existing || {}`) as the authoritative presence gate for the five planning artifacts before the implementation coherence critic runs.

## Q3: How does `persistArtifact` sequence relative to the producer and critic loop, such that it functions as the post-validation success gate that runs only after those pass?

**Answer:** Within `runPhase`, the order is strictly: (1) skip-if-existing early return; (2) producer `agent(prompt)` → `if (res === null) return false`; (3) optional design N-select stage (when `criticConfig.candidates > 1`) → `return false` on failure; (4) optional pre-critic node-check (`criticConfig.nodeCheck`, today only research's citation validator) → `return false` if `!nc.ok`; (5) optional edge-critic loop / panel (`criticConfig`) → `return false` if `!cr.ok`; (6) ONLY THEN `persistArtifact(id, name, phaseLabel)`. The producer writes to a token-free STAGING path (`stg(id, name)` = `/tmp/phase-stage/<id>/<name>.md`), and every intermediate stage (N-select, node-check, critic, reviser) operates on that still-staged file. `persistArtifact` shells to `scripts/qrspi_persist.py`, which calls `persist(src, dest)`: it `os.path.getsize(src)`, returns an error if the file is missing/unreadable or zero bytes, `os.makedirs` the canonical parent, `shutil.move`s it to `<repo>/.worktrees/<ticket>/.qrspi/<ticket>/<name>.md`, then re-verifies the destination size is > 0. A non-ok persist makes `runPhase` return `false`. Thus persist is the single, final success gate: nothing reaches the canonical worktree path until producer + all validations passed, and persist additionally proves the staged file is non-empty.

**Evidence:**

```javascript
  if (criticConfig) {
    const cr = criticConfig.lenses?.length
      ? await runCriticPanelLoop(name, id, criticConfig)
      : await runCriticLoop(name, id, criticConfig)
    if (!cr || !cr.ok) { ... return false }
    ...
  }
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
```

— `.claude/workflows/qrspi-batch.js:1280-1303`

```python
def persist(src, dest):
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    try:
        out = os.path.getsize(dest)
    except OSError:
        return 0, "destination not written: %s" % dest
    if out == 0:
        return 0, "destination is empty after move: %s" % dest
    return out, None
```

— `scripts/qrspi_persist.py:74-92`

**Dependencies:** `persistArtifact` (`qrspi-batch.js:651-664`) spawns a PERSIST worker that runs `python3 scripts/qrspi_persist.py --ticket <id> --artifact <name>` and returns the parsed `{ok, dest, bytes, error?}` envelope (validated against `PERSIST_SCHEMA`). `qrspi_persist.py` self-locates `repo_root` via `qrspi_paths.resolve_repo_root` (`scripts/qrspi_persist.py:115`).
**Implicit contracts:** Staging path (`STAGE_ROOT = "/tmp/phase-stage"`, `qrspi_persist.py:57`) must match the JS `stg()` helper (`/tmp/phase-stage/<id>/<name>.md`) — explicitly noted as a "kept in sync" contract (`qrspi_persist.py:54-57`). Persist is move-not-copy (`shutil.move`), so after persist the staged file is gone; a re-run that skips via `r.existing` reads the canonical file, not the stage. Empty == 0 bytes (the same non-emptiness definition as `detect_existing`).

## Q4: What is the signature and return shape of `slice_numbers` and `slice_branches`, and what input (`branch_set`) do they consume to derive the ascending slice set?

**Answer:** `slice_numbers(branch_lines)` lives in `scripts/qrspi_pr_state.py:266-274`. It takes an iterable of `git branch --list` output lines (raw, e.g. `'  RUS-1/slice-2'` or normalized bare names), regex-matches `r"/slice-(\d+)\s*$"` on each stripped line, collects the captured ints into a set, and returns `sorted(nums)` — a sorted, de-duplicated ascending list of ints. `slice_branches(branches, ticket)` lives in `scripts/qrspi_resolve.py:240-245`. It consumes a normalized `branch_set` (set of bare branch names) plus the ticket id, calls `slice_numbers(branches)`, and returns the ascending list of formatted branch-name strings `["%s/slice-%d" % (ticket, n) for n in slice_numbers(branches)]`, e.g. `["RUS-1/slice-1", "RUS-1/slice-2"]`. Empty list when no slice branches exist. Both are pure. The `branch_set` input is produced by `branch_set(branch_lines)` (`qrspi_pr_state.py:293-305`), which strips git's leading `* `/`+ `/`  ` markers and returns a set of bare names.

**Evidence:**

```python
def slice_numbers(branch_lines):
    """Extract slice numbers from `git branch --list` output lines for a ticket.
    Accepts raw lines like '  RUS-1/slice-2'. Returns a sorted unique int list."""
    nums = set()
    for line in branch_lines:
        m = re.search(r"/slice-(\d+)\s*$", line.strip())
        if m:
            nums.add(int(m.group(1)))
    return sorted(nums)
```

— `scripts/qrspi_pr_state.py:266-274`

```python
def slice_branches(branches, ticket):
    """The ascending list of slice branch names for `ticket` from a normalized
    `branch_set`, e.g. ["RUS-1/slice-1", "RUS-1/slice-2"]..."""
    return ["%s/slice-%d" % (ticket, n) for n in slice_numbers(branches)]
```

— `scripts/qrspi_resolve.py:240-245`

**Dependencies:** `slice_branches` imports `slice_numbers` from `qrspi_pr_state` (`qrspi_resolve.py:52`). `branch_set` feeds both (`_existing_branches` returns `branch_set(...)`, `qrspi_resolve.py:297-299`). `pick_tip` (`qrspi_resolve.py:155-170`) also calls `slice_numbers` to pick the highest slice. The envelope's root-level `slices` field is populated via `slice_branches(branches, args.ticket)` (`qrspi_resolve.py:400`).
**Implicit contracts:** Slice detection keys ONLY on the `/slice-<n>$` suffix; `plan`/`design` branches are excluded. Ordering is numeric-ascending via `sorted()` on ints (not lexical string sort), so `slice-10` sorts after `slice-2`. De-duplication via set.

## Q5: What is the existing test structure and assertion style for `detect_existing` in the current resolver test, that a new resume-contract test would extend or sit as a sibling to?

**Answer:** The test file is `scripts/qrspi_resolve_test.py` — stdlib-only, assert-based, no pytest. It defines a tiny harness: a module-global `failures`/`total` counter, `check(name, got, want)` which increments `total`, compares `got != want`, prints `FAIL:`/`ok:` lines, and a `check_raises(name, fn)` for expected exceptions. At the bottom, `run()` prints `"%d passed, %d failed"` and `sys.exit(run())` returns 1 if any failure (so the runner sees non-zero on failure). For `detect_existing` specifically (`qrspi_resolve_test.py:68-84`): one assertion that a missing dir yields all-`False`, then a `tempfile.TemporaryDirectory()` block that writes a non-empty `design.md` and `plan.md`, creates a zero-byte `research.md` (via `open(...).close()`), and asserts: non-empty design `True`, non-empty plan `True`, empty research `False`, absent questions `False`, and `sorted(got.keys()) == sorted(ARTIFACTS)`. This is the exact fixture pattern a new resume-contract test would mirror (pre-seed a temp dir with artifact files, assert the skip-map booleans).

**Evidence:**

```python
with tempfile.TemporaryDirectory() as d:
    # non-empty design + plan; empty research (0 bytes) must read as absent
    with open(os.path.join(d, "design.md"), "w") as fh:
        fh.write("content")
    with open(os.path.join(d, "plan.md"), "w") as fh:
        fh.write("more")
    open(os.path.join(d, "research.md"), "w").close()  # empty
    got = detect_existing(d)
    check("non-empty design detected", got["design"], True)
    check("non-empty plan detected", got["plan"], True)
    check("empty research not counted", got["research"], False)
    check("absent questions -> False", got["questions"], False)
    check("all six keys present", sorted(got.keys()), sorted(ARTIFACTS))
```

— `scripts/qrspi_resolve_test.py:72-84`

```python
def check(name, got, want):
    global failures, total
    total += 1
    if got != want:
        print("FAIL: %s\n      expected %r\n      got      %r" % (name, want, got))
        failures += 1
    else:
        print("ok: %s" % name)
```

— `scripts/qrspi_resolve_test.py:36-43`

**Dependencies:** Imports `detect_existing`, `slice_branches`, `ARTIFACTS`, etc. directly from `qrspi_resolve` (`qrspi_resolve_test.py:15-30`); imports `qrspi_paths`. The subprocess-backed parts (gh/git/gt, `build_state`) are explicitly NOT tested here (docstring `qrspi_resolve_test.py:1-9`) — only pure helpers.
**Implicit contracts:** Test convention: each `scripts/*_test.py` is a standalone `python3 scripts/<name>_test.py` exiting 0 on success / non-zero on failure (consumed by `run_tests.py`, Q12). Assertions use `check(...)` not `assert`. Pure helpers only; impure paths deferred to manual e2e.

## Q6: What persisted state on disk and in branch naming distinguishes a "done" phase or slice from one that must be (re)computed on a re-run, and where is that state read from?

**Answer:** Two distinct kinds of persisted state. (a) PLANNING-PHASE done-ness: a non-empty `<worktree>/.qrspi/<ticket>/<name>.md` file on disk. Read by `detect_existing` (Q1) via `os.path.getsize > 0`, surfaced as the envelope's `existing` map, and consumed by `runPhase`'s skip (Q2). (b) SLICE done-ness: branch naming — the presence of a committed `<ticket>/slice-<n>` git branch. The resolver reads branches via `_existing_branches` → `git branch --list <ticket>/*` → `branch_set` (`qrspi_resolve.py:297-299`), and derives slice numbers/branches via `slice_numbers`/`slice_branches`/`pick_tip`. At implementation time, the per-slice "already done" signal is the `alreadyCommitted` boolean on each slice setup entry, set "true ONLY if a `<ticket>/slice-N` branch already has its code committed — this is the SOLE legal per-slice skip, for resume" (`qrspi-batch.js:1786-1800`). `doSlices` skips a slice iff `s.alreadyCommitted` (`qrspi-batch.js:1850-1851`). So planning resume is FILE-driven; slice resume is BRANCH/commit-driven.

**Evidence:**

```python
def _existing_branches(ticket, repo_root=REPO_ROOT):
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=repo_root)
    return branch_set(out.splitlines()) if rc == 0 else set()
```

— `scripts/qrspi_resolve.py:297-299`

```javascript
  for (const s of setup.slices) {
    if (s.alreadyCommitted) { log(`  ${t.id}: slice ${s.n} already committed — skipping`); continue }
```

— `.claude/workflows/qrspi-batch.js:1850-1851`

**Dependencies:** Planning state flows `disk → detect_existing → existing map → runPhase skip`. Slice state flows `git branches → branch_set/slice_numbers → setup agent's alreadyCommitted → doSlices skip`. The `alreadyCommitted` flag is produced by the (non-deterministic) setup agent reading branch state, not by a pure helper.
**Implicit contracts:** A "done" planning phase == non-empty canonical `.md` exists. A "done" slice == its `<ticket>/slice-N` branch exists with code committed. Note the asymmetry: planning resume is decided deterministically by the resolver script; slice `alreadyCommitted` is decided by an LLM setup agent per its prompt instructions (the SOLE legal skip is a committed branch; "gated"/"optional" is explicitly NOT a skip reason).

## Q7: How is the resolver's decision / skip-map represented in its output envelope, and which fields encode that a persisted upstream phase is skippable?

**Answer:** `build_envelope` (`qrspi_resolve.py:190-237`) assembles the JSON envelope. The skip-map is the `existing` field — a dict of the six artifact names → boolean (from `detect_existing`). The action decision is the separate `decision` field (from `qrspi_resolve_state.resolve`). Other root fields: `ok`, `repoRoot`, `worktreeDir`, `commentTargets`, `reviewers`, `teamReviewers`, `ticketContentPath`, `tip`, `slices`, and an `error` key only when failing. The field that encodes "a persisted upstream phase is skippable" is `existing[<phase>] == true` — there is no separate "skip" flag; skippability == the existence boolean, interpreted by `runPhase` (Q2). On the error path, `existing` is `{name: False for name in ARTIFACTS}` (`qrspi_resolve.py:408`), i.e. nothing skippable.

**Evidence:**

```python
    env = {
        "ok": ok,
        "repoRoot": REPO_ROOT if repo_root is None else repo_root,
        "worktreeDir": worktree_dir,
        "existing": existing,
        "decision": decision,
        "commentTargets": comment_targets_of(decision),
        "reviewers": reviewers,
        "teamReviewers": team_reviewers,
        "ticketContentPath": ticket_content_path,
        "tip": tip,
        "slices": slices if slices is not None else [],
    }
    if error is not None:
        env["error"] = error
    return env
```

— `scripts/qrspi_resolve.py:222-237`

**Dependencies:** `existing` from `detect_existing` (Q1); `decision` from `resolve(state)` (`qrspi_resolve.py:389`); `slices`/`tip` from `slice_branches`/`pick_tip` (Q4). Consumed by `parseResolveEnvelope` in JS (`qrspi-batch.js:224`), which validates `ok`, `worktreeDir`, and `decision.action` but NOT `existing` (it is dereferenced later as `r.existing`).
**Implicit contracts:** `existing` always carries all six `ARTIFACTS` keys (even on error, all-False). Skippability is purely the boolean — there is no phase-ordering or dependency logic in the envelope; `runPhase` is called per-phase in fixed sequence and each independently checks its own `existing[name]`.

## Q8: How does `detect_existing` treat a present-but-empty (zero-byte) artifact versus a missing artifact — does a truncated/aborted write yield `False` (recompute) rather than a false `True` (skip)?

**Answer:** Both a zero-byte artifact and a missing artifact yield `False`. The check is `os.path.getsize(path) > 0`: a 0-byte file returns size 0, so `0 > 0` is `False`; a missing file/dir raises `OSError`, caught → `False`. So a truncated/aborted write that left a zero-byte file correctly reads as `False` (recompute), NOT a false `True` (skip). This is the safe direction. The resolver test pins exactly this: a zero-byte `research.md` (created via `open(...).close()`) must read `False` ("empty research not counted"). `qrspi_persist.py`'s `persist` enforces the same invariant on the write side: it refuses to move a 0-byte staged file and re-checks the destination is non-zero after move, so persist never produces a zero-byte canonical artifact in the first place.

**Evidence:**

```python
        try:
            out[name] = os.path.getsize(path) > 0
        except OSError:
            out[name] = False
```

— `scripts/qrspi_resolve.py:148-151`

```python
    open(os.path.join(d, "research.md"), "w").close()  # empty
    got = detect_existing(d)
    ...
    check("empty research not counted", got["research"], False)
```

— `scripts/qrspi_resolve_test.py:78-82`

**Dependencies:** Mirrors `qrspi_persist.persist`'s `if size == 0: return ... "empty"` guard (`qrspi_persist.py:82-83`) and its post-move re-check (`qrspi_persist.py:90-91`).
**Implicit contracts:** Non-emptiness is byte-count only — `detect_existing` does NOT validate that the bytes are well-formed markdown or contain expected sections. A 1-byte garbage file would read `True` and be skipped. The empty-vs-missing distinction is collapsed (both `False`); only "non-empty present" yields `True`. Fail-safe direction: ambiguity errs toward recompute.

## Q9: When `agent()` returns a bare `null` mid-phase or mid-slice, what code path causes that phase/slice to be recomputed on re-run rather than trusting a half-written artifact?

**Answer:** Two layers. (1) IN-RUN: `runPhase` checks `if (res === null) { log(...); return false }` immediately after the producer `agent()` call (`qrspi-batch.js:1244-1247`); a `false` return propagates up through the `if (!await runPhase(...)) return failTicket(t)` guards at the phase call sites (`qrspi-batch.js:1480` etc.), stopping the ticket. Critically, because the producer wrote to the STAGING path and `persistArtifact` runs only AFTER the producer (and all critics) succeed, a null producer means `persistArtifact` is never reached, so NOTHING is moved to the canonical worktree path — there is no half-written canonical artifact. (2) ON RE-RUN: because no canonical `<name>.md` was persisted, `detect_existing` returns `False` for that phase, `r.existing[name]` is falsy, and `runPhase` does NOT take the skip branch — it re-spawns the producer (recompute). For slices, `doSlices` checks `if (impl === null) { log('... stopping (prior slices preserved)') ; ... }` (`qrspi-batch.js:1873-1874`); since the slice never reaches the commit worker, no `<ticket>/slice-N` branch is created, so on re-run `alreadyCommitted` is false and the slice recomputes.

**Evidence:**

```javascript
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
```

— `.claude/workflows/qrspi-batch.js:1243-1247`

```javascript
    if (impl === null) {
      log(`  ${t.id}: slice ${s.n} implementation failed — stopping (prior slices preserved)`)
```

— `.claude/workflows/qrspi-batch.js:1873-1874`

**Dependencies:** The recompute-on-re-run guarantee is the JOINT property of (a) `persistArtifact` being the gate AFTER produce/critic (Q3) and (b) `detect_existing`'s file-presence skip (Q1/Q2). The slice analogue depends on branch creation happening only after a successful implement+commit.
**Implicit contracts:** `agent()` returning `null` is the failure sentinel — every `agent()` caller in the file guards `=== null` / `!result` (see runCriticLoop:726, runCriticPanelLoop:831, doSlices:1873, etc.). The staging-then-persist ordering is what makes a null safe: a null can never leave a partial canonical artifact. The PRECISE shape `agent()` returns on terminal failure (a bare `null` with discarded error text) is the subject of the probe in Q13 (which is out of scope here — see below).

## Q10: How do `slice_numbers` / `slice_branches` behave when `branch_set` contains a non-contiguous or partial set of slice branches (e.g. slice-1 and slice-3 present, slice-2 absent) — which next slice is derived?

**Answer:** Both functions are gap-agnostic: they report exactly the slice numbers that are present, sorted ascending, with no contiguity check and no inference of a "next" slice. For `{slice-1, slice-3}` (slice-2 absent), `slice_numbers` returns `[1, 3]` and `slice_branches` returns `["<ticket>/slice-1", "<ticket>/slice-3"]` — slice-2 is simply absent from the list; there is no synthesized "next slice = 2". `pick_tip` returns `<ticket>/slice-3` (it uses `max(snums)`, the highest present number, NOT highest-contiguous). The "which slice runs next" decision is NOT made by these helpers at all — it is made downstream by the setup agent's `alreadyCommitted` per-slice flag (Q6) iterating the slices the PLAN defines, not the branch set. So a gap in branches does not by itself drive next-slice derivation in the resolver; the resolver only reports the present set and the max tip.

**Evidence:**

```python
def pick_tip(branches, ticket):
    """Pick the highest existing phase branch ... slice-N (largest N) > plan > design..."""
    snums = slice_numbers(branches)
    if snums:
        return "%s/slice-%d" % (ticket, max(snums))
    for phase in ("plan", "design"):
        ...
```

— `scripts/qrspi_resolve.py:155-170`

Test confirming out-of-order / partial handling (sorted, not gap-filled):

```python
check("slices sorted ascending even when set is out of order",
      slice_branches({"RUS-1/slice-3", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      ["RUS-1/slice-1", "RUS-1/slice-2", "RUS-1/slice-3"])
check("slice beats plan even out of order",
      pick_tip({"RUS-1/plan", "RUS-1/slice-3", "RUS-1/slice-1"}, "RUS-1"),
      "RUS-1/slice-3")
```

— `scripts/qrspi_resolve_test.py:105-107, 94-96`

**Dependencies:** `pick_tip`/`slice_branches` consume `slice_numbers` (`qrspi_pr_state.py:266`). No existing test seeds a `{slice-1, slice-3}` gap specifically — current tests cover out-of-order-but-contiguous (`{1,2,3}` shuffled). A non-contiguous gap case is NOT directly asserted today (gap behavior is inferable from the implementation: present-only, `max`-tip).
**Implicit contracts:** These helpers REPORT branch state; they do not VALIDATE stack contiguity or compute the next action. The stack is assumed built bottom-up contiguously (`<id>/slice-1 → slice-2 → ...`), so a gap is an off-nominal state the helpers tolerate (report-as-is) rather than guard against. `max(snums)` for tip means a gap leaves the tip at the highest present number regardless of holes below it.

## Q11: How are existing resolver tests seeded against a temp worktree (pre-populated artifacts, fixture layout), so a new test can pre-seed persisted upstream artifacts and assert the skip-map marks those phases skippable?

**Answer:** The existing seeding pattern uses `tempfile.TemporaryDirectory()` as a context manager and writes artifact files directly into it with plain `open(...).write(...)`, then calls `detect_existing(d)` against that dir (`qrspi_resolve_test.py:72-84`). It does NOT construct a full `<worktree>/.qrspi/<ticket>/` nested layout — it passes the temp dir straight as the `qrspi_dir` argument (since `detect_existing` is pure over any directory path). Non-empty files are seeded via `fh.write("content")`; zero-byte files via `open(path, "w").close()`. A new resume-contract test would follow the same pattern: create a temp dir, write non-empty `questions.md`/`research.md`/etc., call `detect_existing(d)`, and `check(...)` that those keys are `True` (skippable) and absent ones `False`. For a higher-fidelity test mirroring the real path (`os.path.join(worktree, ".qrspi", ticket)`), one could `os.makedirs` that nested layout under the temp dir, but the current tests do not. The `qrspi_paths.subprocess.run` monkeypatch pattern (`qrspi_resolve_test.py:174-198`) shows how to stub the gh-validation seam when a test needs `resolve_repo_root` without spawning gh.

**Evidence:**

```python
with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "design.md"), "w") as fh:
        fh.write("content")
    ...
    open(os.path.join(d, "research.md"), "w").close()  # empty
    got = detect_existing(d)
    check("non-empty design detected", got["design"], True)
```

— `scripts/qrspi_resolve_test.py:72-80`

```python
_real_run = qrspi_paths.subprocess.run
try:
    qrspi_paths.subprocess.run = lambda cmd, **kw: (
        _Fake(0, "octo/host-repo\n") if cmd[:3] == ["gh", "repo", "view"]
        else _Fake(0, ""))
    check("--repo-root override resolves (validated) to the supplied root",
          qrspi_paths.resolve_repo_root("/synthetic/flag-root", cwd="/anywhere"),
          os.path.abspath("/synthetic/flag-root"))
finally:
    qrspi_paths.subprocess.run = _real_run
```

— `scripts/qrspi_resolve_test.py:179-188`

**Dependencies:** `tempfile`, `os`, the `check`/`check_raises` harness, and `qrspi_paths` for the monkeypatch seam. `qrspi_persist_test.py` (a sibling, not read in full here) is the analogous fixture model for persist's `staging_path`/`dest_path`/`persist` over temp dirs.
**Implicit contracts:** Tests operate on bare temp dirs, not a reconstructed worktree tree — they exploit `detect_existing`'s purity over any directory. A resume-contract test that wants to assert the FULL skip-then-reuse path (resolver → `runPhase` skip) cannot be a pure Python unit test, since the skip lives in `qrspi-batch.js` (harness-coupled, not unit-testable; see docs Q14); the Python test can only assert the `existing` map values.

## Q12: How does `scripts/run_tests.py` discover and run each `scripts/*_test.py`, and how does `.github/workflows/tests.yml` invoke that same suite as the CI regression gate?

**Answer:** `run_tests.py` is a stdlib-only aggregating runner, self-locating from `__file__` (`SCRIPT_DIR`, `run_tests.py:28`). `discover_tests(scripts_dir, pattern)` lists `scripts_dir`, keeps every name ending in `_test.py` (sorted), and optionally filters by a case-sensitive substring `pattern` (`run_tests.py:36-48`). `run_one(path)` runs `[python, path]` as a subprocess with `capture_output=True` and a per-file `DEFAULT_TIMEOUT = 180`s; `ok = returncode == 0`, a `TimeoutExpired` counts as failure (`run_tests.py:51-75`). `run_suite` runs each path, prints PASS/FAIL lines + an aggregate `"N passed, M failed"`, and returns `(passed, failures)` (`run_tests.py:78-104`). `main()` returns `1 if failures else 0`, so the runner exits non-zero if ANY test file fails. CLI: optional `pattern` arg, `--list`, `--timeout` (`run_tests.py:107-138`). CI: `.github/workflows/tests.yml` defines a `python` job (`runs-on: ubuntu-24.04`, `permissions: contents: read`) that checks out the repo, shows the Python version, and runs `python3 scripts/run_tests.py` as the gate (no dependency install — stdlib only). It triggers on `pull_request`, `push` to `main`, and `workflow_dispatch`. A separate `workflow-syntax` job runs `node scripts/check_workflows.js .claude/workflows/*.js`. Either job failing fails the check.

**Evidence:**

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(
        n for n in os.listdir(scripts_dir)
        if n.endswith("_test.py")
    )
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48`

```yaml
      - name: Run Python test suite
        run: python3 scripts/run_tests.py
```

— `.github/workflows/tests.yml:38-39`

**Dependencies:** Runner depends on each `*_test.py` being a self-contained, exit-coded subprocess (the repo convention). CI `tests.yml` triggers: `pull_request`, `push: branches: [main]`, `workflow_dispatch` (`tests.yml:9-13`); `concurrency` cancels superseded runs (`tests.yml:18-21`).
**Implicit contracts:** Any new test added as `scripts/<name>_test.py` is AUTO-discovered — no registration needed — and is automatically the CI gate. A new resume-contract test named e.g. `scripts/qrspi_resolve_test.py` (the existing file) or a sibling `*_test.py` is picked up by both the local runner and CI with zero config. Tests must exit 0/non-zero (not just print) since `ok` keys on returncode.

## Q13: What does `probe-agent-failure.js` emit/record as the evidentiary output of the `agent()` failure seam (the bare `null` with discarded error message), and in what form is that result captured for citation in docs?

**Answer:** NOT FOUND within project scope. `probe-agent-failure.js` does NOT exist anywhere under `REPO_ROOT` (`/workspaces/qrspi/.worktrees/RUS-80`). The only entry in `.claude/workflows/` is `qrspi-batch.js` (`ls .claude/workflows/`). `git ls-files | grep -i probe` returns nothing (not tracked in this branch). The file IS present as an UNTRACKED file in the MAIN checkout (`/workspaces/qrspi/.claude/workflows/probe-agent-failure.js`, per the session's git status), but that path is OUTSIDE `REPO_ROOT` and the research firewall forbids reading it. Searches attempted: `find . -name "probe-agent-failure*"` (no results), `find . -name "*.js" | grep -i probe` (no results), `git ls-files | grep -i probe` (no results), `grep -rn "probe-agent-failure" docs/ .qrspi/RUS-80/` (only the questions.md reference at lines 48-49). The associated `deep-research`-style skill name "probe-agent-failure" appears as a registered skill in the harness, but its `.js` artifact is not in this worktree.

**Answer (indirect, from in-scope code):** What the `agent()` seam returns on terminal failure can be inferred from the consuming code: every caller treats `null` as the failure sentinel and discards any error detail. `runPhase` logs only a generic `"${name} phase failed or was skipped"` (no error text) on `res === null` (`qrspi-batch.js:1244-1246`); the docstring at `qrspi-batch.js:701` states "a spawn failure (critic or reviser returns null)". The bare-`null`-with-discarded-error characterization in the question is consistent with the in-scope code but the probe artifact that records it empirically is not present in scope.

**Evidence:**

```
$ ls .claude/workflows/        → qrspi-batch.js   (only file)
$ git ls-files | grep -i probe → (empty)
$ find . -name "probe-agent-failure*" → (no results)
```

— shell, run in `REPO_ROOT`

**Dependencies:** n/a — artifact absent from scope.
**Implicit contracts:** n/a.

## Q14: What does `docs/testing-dynamic-workflows.md` currently state about resume semantics and the `qrspi-batch.js` testing seam, that this ticket must extend to document the phase/slice-boundary resume guarantee?

**Answer:** `docs/testing-dynamic-workflows.md` currently says NOTHING explicit about resume/skip semantics or the phase/slice-boundary resume guarantee — it is a TDD-strategy document about the Functional-Core/Imperative-Shell split, not about resume. Its relevant content for this ticket: (1) it asserts QRSPI already implements Functional Core (tested Python) / Imperative Shell (`qrspi-batch.js`), and the goal is to "keep starving the JS shell of logic, and test the residual deterministic seam deliberately" (lines 21-27). (2) It enumerates WHY `qrspi-batch.js` is not unit-testable: top-level `return`/`await`, harness-injected globals (`agent()`, `parallel()`, ...), only `export const meta`, and NO filesystem/import access — "dual-illegal outside the harness" (lines 29-45). (3) It lists the deterministic surface: ~10 JSON-envelope parsers (incl. `parseResolveEnvelope`), ~9 path/flag helpers (`reviewerFlags`, `engineCmdFor`, `stg`, `art`), ~17 `*_SCHEMA` constants, ~20 `agent()` seams (lines 46-63). (4) It recommends covering the residual JS seam via JS↔Python contract/golden fixtures (strategy #3, lines 124-131) and via vm-sandbox tests (#4). (5) The "Open experiment — RESOLVED" section (lines 152-177) records the zero-agent probe proving the harness has no `require`/`import`/`fs`. This ticket must EXTEND the doc to document the phase/slice-boundary resume guarantee — i.e. that `detect_existing` (file-presence) + `persistArtifact`-as-gate + `alreadyCommitted` (branch-presence) together make every phase/slice independently re-runnable, and how that guarantee is tested (Python unit tests for `detect_existing`/`slice_*`; the JS skip in `runPhase` covered only via the contract-fixture approach the doc already advocates).

**Evidence:**

```markdown
**QRSPI already does this — with Python as the functional core and
`qrspi-batch.js` as the imperative shell.** ...
So the goal is not "make the dynamic JS testable" — it is **keep starving the JS
shell of logic, and test the residual deterministic seam deliberately.**
```

— `docs/testing-dynamic-workflows.md:21-27`

```markdown
- **~10 pure JSON-envelope parsers** (`extractJsonObject`/`extractJsonArray`,
  `parseResolveEnvelope`, ...)
- **~9 pure path/flag helpers** (`reviewerFlags`, `engineCmdFor`, `stg`, `art`) ...
```

— `docs/testing-dynamic-workflows.md:50-55`

**Dependencies:** The doc is the companion to `scripts/run_tests.py` + `.github/workflows/tests.yml` (lines 8-11, the Python regression harness). It references `parseResolveEnvelope`, `stg`, `art` — all in `qrspi-batch.js`.
**Implicit contracts:** The doc establishes the WRITTEN convention that new deterministic logic must land in tested Python, not inline JS (strategy #1, lines 109-114). A resume-guarantee section must respect that framing: the resume LOGIC is already in Python (`detect_existing`, `slice_numbers`), and the JS only consumes it (`runPhase` skip) — so the doc-extension should frame the guarantee as "Python-tested core + thin JS skip", consistent with the existing thesis. The doc has a stated provenance-caution norm (some quotes search-verified, not directly read — line 101-105).

---

## Discovered Patterns

- **Staging-then-deterministic-move is the universal write pattern.** Both planning artifacts (`stg()` → `qrspi_persist.py`) and the resolve ticket-content handoff (`/tmp/phase-stage/<id>/ticket.md` → `ticketContentPath`) route fragile writes through a short, token-free `/tmp/phase-stage/<id>/...` path that a weak model cannot corrupt, then a self-locating Python script owns the `qrspi`-laden canonical path. The motivation is documented at length (`qrspi_persist.py:1-29`, `qrspi_resolve.py:1-31`): a small local model (qwen3.6:35b) mangles the literal `qrspi` token.
- **Persist is the SINGLE success gate.** The repeated design intent (CLAUDE.md "Fix A", `qrspi-batch.js:1296-1298`, `qrspi_persist.py` docstring) is that an agent reporting "done" is NOT trusted; the real per-phase gate is a non-empty file landing at the canonical path via `persistArtifact`. This is what makes resume safe (a half-run leaves no canonical artifact).
- **Non-emptiness == byte size > 0, consistently.** `detect_existing` (read side, `qrspi_resolve.py:149`) and `persist` (write side, `qrspi_persist.py:82,90`) both define "present" as `getsize > 0`. Neither validates content structure.
- **`null` is the universal `agent()` failure sentinel.** Every `agent()` caller guards `=== null` / `!result` and fails the ticket fail-closed (runCriticLoop:726, runCriticPanelLoop:831, runDesignSelectLoop:1053, runPhase:1244, doSlices:1873). Error detail is discarded — only a generic log line is emitted.
- **Pure-logic-in-Python / impure-glue-in-JS split** is enforced by convention (docs strategy #1) and by the test layout: every deterministic helper has a `scripts/*_test.py` sibling auto-discovered by `run_tests.py`; `qrspi-batch.js` is deliberately untested (harness-coupled).
- **Two resume mechanisms by phase type:** planning phases resume via FILE presence (deterministic, resolver-driven); slices resume via BRANCH/commit presence (decided by the LLM setup agent's `alreadyCommitted` flag, not a pure helper).
- **`ARTIFACTS` list is duplicated** in `qrspi_resolve.py:58` and `qrspi_persist.py:52` (same six names) — a hidden must-stay-in-sync coupling.

## Inconsistencies

- **`probe-agent-failure.js` is referenced by questions.md (Q13) but does not exist in this worktree.** It exists only as an untracked file in the MAIN checkout (outside `REPO_ROOT`), so Q13's evidentiary artifact cannot be cited from within scope. The questions phase assumed an in-repo, committed probe; the actual probe is uncommitted/out-of-scope.
- **Resume safety for slices is LLM-decided, not deterministically tested.** Planning resume (`detect_existing`) has pure unit tests; the slice-resume `alreadyCommitted` flag is produced by a non-deterministic setup agent per a prompt instruction (`qrspi-batch.js:1786-1800`). The "SOLE legal per-slice skip" rule lives in prose, not code — there is no pure helper or test asserting that a committed `<ticket>/slice-N` branch (and ONLY that) sets `alreadyCommitted`. This is an asymmetry between the two resume mechanisms.
- **`detect_existing` trusts byte-count, not content validity.** A 1-byte or syntactically-broken-but-nonempty artifact reads `True` and is skipped on re-run. The "non-empty" gate guards against truncated/zero-byte writes but not against a present-but-garbage artifact — a gap the resume guarantee documentation (Q14) should acknowledge.
- **No existing test covers a non-contiguous slice-branch gap** (Q10). Current tests cover out-of-order-but-complete sets (`{1,2,3}` shuffled, `qrspi_resolve_test.py:105-107`); a `{slice-1, slice-3}` gap (slice-2 absent) behavior is only inferable from the implementation (`max`-tip, present-only list), not asserted.
- **The resume/skip guarantee is undocumented in `docs/testing-dynamic-workflows.md`** despite being a core determinism property (Q14). The doc covers the testing strategy thesis but says nothing about phase/slice resume semantics — the exact gap this ticket appears scoped to fill.
