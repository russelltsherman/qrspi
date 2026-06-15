# Answered Questions — Teeth-eval fixture (RUS-78)

> **Eval fixture, not a real questions artifact.** Minimal answered-questions input
> so the **completeness** lens (which Reads `QUESTIONS_PATH`) has a well-formed
> source. Every question here is FULLY addressed by the flawed `design.md`, so the
> completeness lens fails ONLY on the omitted ticket AC (`AC-TEETH-COMPLETENESS`),
> never on a question gap. Keep this fixture covered by the design.

## Q1: How many retry attempts before giving up?

**Answer:** At most 3 retries, then surface the error to the caller. *(The flawed
design states this, so completeness is satisfied on this point.)*

## Q2: What backoff strategy between retries?

**Answer:** Exponential backoff. *(The flawed design states this, so completeness
is satisfied on this point.)*

## Q3: Where does the retry wrapper sit relative to the widget entry point?

**Answer:** Directly in front of the widget subsystem's public entry point,
wrapping each call. *(The flawed design states this, so completeness is satisfied
on this point.)*
