# Ticket — Teeth-eval fixture: Widget retry feature (RUS-78)

> **Eval fixture, not a real Linear ticket.** This file carries the acceptance
> criterion the deliberately-flawed `design.md` in this directory SILENTLY OMITS.
> The **completeness** lens anchors on this ticket's ACs (it Reads
> `TICKET_CONTENT_PATH`), so the omitted-AC defect must live HERE. The completeness
> lens must catch the omission and cite the marker `AC-TEETH-COMPLETENESS`.

## Summary

Add a bounded retry wrapper around the widget subsystem so transient widget
failures are retried automatically before surfacing an error to the caller.

## Acceptance Criteria

- **AC-RETRY-BOUND:** the retry wrapper retries a failed widget call at most 3
  times before giving up and surfacing the error.
- **AC-RETRY-BACKOFF:** retries use exponential backoff between attempts.
- **AC-TEETH-COMPLETENESS:** on FINAL failure (all retries exhausted), the wrapper
  MUST emit a structured audit-log record naming the widget id and the exhausted
  attempt count, so an operator can trace which widget call gave up. This audit
  record is a hard requirement of this ticket. *(This is the acceptance criterion
  the flawed design omits — the completeness lens must surface that omission and
  cite `AC-TEETH-COMPLETENESS`.)*

## Notes

The retry wrapper sits in front of the existing widget entry point. See the
companion research fixture for the verified behavior of that entry point.
