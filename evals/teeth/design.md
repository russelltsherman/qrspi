# Design — Widget retry wrapper (RUS-78 teeth-eval fixture)

> **DELIBERATELY FLAWED eval fixture, not a real design.** This single combined
> `design.md` carries THREE labelled defects, one per owning lens, each embedding a
> unique quotable marker the owning lens must cite when it catches the defect:
>
> 1. **completeness** → SILENTLY OMITS the ticket AC `AC-TEETH-COMPLETENESS` (the
>    final-failure audit-log requirement). The omission is the defect; the marker
>    `AC-TEETH-COMPLETENESS` appears in `ticket.md`, never below.
> 2. **internal-consistency** → states the retry-cap constant as TWO different
>    values (marker `TEETH-INCONSISTENCY`).
> 3. **edge-alignment** → claims `frobnicate_widget()` is ASYNCHRONOUS, contradicting
>    the verified synchronous-and-idempotent fact in `research.md` (marker
>    `frobnicate_widget()`).
>
> A correct, teeth-bearing panel returns `pass=false` from each owning lens, citing
> its marker. The labels above orient a human reader; the lenses must derive the
> defects from the design body against the upstream inputs, not from this banner.

## Current State

The widget subsystem exposes a single public entry point, `frobnicate_widget()`,
used directly by callers today with no retry handling. A transient widget failure
surfaces immediately to the caller.

## Desired End State

A retry wrapper sits directly in front of `frobnicate_widget()`, transparently
retrying transient failures with exponential backoff before surfacing an error.

## Delta

### Retry bound (covers AC-RETRY-BOUND)

The wrapper retries a failed widget call up to a fixed maximum.

<!-- DEFECT 2 (internal-consistency, marker TEETH-INCONSISTENCY): the retry cap
constant is stated with two contradicting values in the two paragraphs below. -->

We define the maximum retry count `MAX_RETRIES` as **3**. After 3 failed retries
the wrapper gives up and surfaces the original error to the caller. This satisfies
AC-RETRY-BOUND.

The control loop is sized off `MAX_RETRIES`: because `MAX_RETRIES` is **5**, the
loop iterates up to five times before surfacing the error. (TEETH-INCONSISTENCY:
`MAX_RETRIES` is given as 3 in the paragraph above and as 5 here — the same
constant has two different stated values, an internal contradiction.)

### Backoff (covers AC-RETRY-BACKOFF)

Between attempts the wrapper waits with exponential backoff (doubling the delay each
attempt), satisfying AC-RETRY-BACKOFF.

### Invocation of the widget entry point

<!-- DEFECT 3 (edge-alignment, marker frobnicate_widget()): contradicts research.md,
which verifies frobnicate_widget() is SYNCHRONOUS and idempotent. -->

The wrapper calls `frobnicate_widget()`, which is **asynchronous**: it returns a
promise/future immediately and runs the widget settling work in the background, so
the wrapper must `await` the promise and poll for completion before deciding whether
to retry. The retry timer is therefore armed off the promise-resolution callback.

*(This asynchronous claim is wrong: per `research.md`, `frobnicate_widget()` is
synchronous and idempotent — it returns the settled state inline on the same call
and does not return a promise or run in the background. The edge-alignment lens must
catch this contradiction with the verified research fact.)*

<!-- DEFECT 1 (completeness): the ticket's AC-TEETH-COMPLETENESS — emit a structured
audit-log record on FINAL failure (all retries exhausted), naming the widget id and
the exhausted attempt count — is SILENTLY OMITTED. There is intentionally NO section
covering final-failure audit logging anywhere in this design. The completeness lens,
anchored on the ticket ACs, must surface that the design drops AC-TEETH-COMPLETENESS. -->

## Out of Scope

- Changing the widget subsystem's own internals.
- Per-call configuration of the retry policy (the policy is fixed for this feature).
