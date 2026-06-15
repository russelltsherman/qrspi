# Research — Teeth-eval companion fixture (RUS-78)

> **Eval fixture, not a real research artifact.** This file anchors the
> **edge-alignment** defect of the teeth eval: it documents one identifiable,
> quotable codebase fact that the deliberately-flawed `design.md` in this same
> directory CONTRADICTS. The edge-alignment lens, which judges the design against
> this research, must catch that contradiction and cite the marker
> `frobnicate_widget()`.
>
> **Digest non-vacuity (review finding #1):** the load-bearing fact below lives in
> PROSE, not inside a fenced code block. The shared research digest
> (`scripts/qrspi_research_digest.py`) strips only fenced ``` code blocks and keeps
> all prose verbatim, so a CORRECT digest RETAINS this fact and the edge-alignment
> lens still catches the contradiction digest-ON. A digest that wrongly trimmed
> this prose would make edge-alignment PASS and the eval FAIL — exactly the
> digest-risk this defect is designed to gate.

## Q1: What does the widget subsystem's core entry point do?

**Answer:** The widget subsystem's single public entry point is the function
`frobnicate_widget()`. Per the verified source, `frobnicate_widget()` is
**synchronous and idempotent**: it returns the widget's settled state directly to
its caller and calling it twice with the same input yields the same result with no
additional side effects. It does NOT enqueue work, spawn a background job, or
return a future/promise — callers receive the final value inline on the same call.

**Implicit contracts:** any design built on the widget subsystem must treat
`frobnicate_widget()` as a synchronous, idempotent call. A design that claims it is
asynchronous (returns a promise / runs in the background / requires polling for
completion) contradicts this verified fact and is wrong.

## Q2: How is widget state persisted?

**Answer:** Widget state is persisted by `frobnicate_widget()` itself before it
returns; there is no separate flush step and no eventual-consistency window. The
returned state is already durable.

## Discovered Patterns

- The widget subsystem follows the functional-core / imperative-shell idiom: the
  synchronous `frobnicate_widget()` is the imperative shell over a pure settling
  computation.

## Inconsistencies

- None observed. The synchronous-and-idempotent contract of `frobnicate_widget()`
  is consistent across every call site reviewed.
