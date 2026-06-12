#!/usr/bin/env python3
"""Group-then-sort the deduped batch tickets array for deterministic within-phase order.

Why this exists
---------------
The qrspi-batch Query phase flattens + dedups assigned tickets across one or more
Linear projects, but the resulting order is non-deterministic (it depends on MCP
fan-out / merge order). The downstream `[i/total]` loop should consume tickets in a
stable, explainable order: grouped by phase (the `STATUSES` order the batch already
uses) and, within each phase group, FIFO by `createdAt` ascending. This makes the
"Found …" log line and the progression reproducible across runs
(ref: design.md Decision 2 Option A; AC3, AC6).

Sort contract
-------------
- `created_at_key(ticket)` returns a tuple sort key
  `(missing_flag, parsed_createdAt, id_numeric_suffix)`:
    * `missing_flag` is 0 when `createdAt` parses, 1 when it is absent OR unparseable
      — so such tickets sort LAST within their group (Decision 3 Option A, AC5);
    * `parsed_createdAt` is the ISO-8601 timestamp parsed ascending (a sentinel when
      missing, never compared against a real value because the flag dominates);
    * `id_numeric_suffix` is the trailing integer of the ticket `id` (e.g. `RUS-71`
      → 71), the deterministic tie-break on equal `createdAt`. It NEVER raises.
- `sort_tickets(tickets, statuses)` stable-partitions by `status` in `statuses` order
  (a final partition holds tickets whose status is not in `statuses`, order preserved),
  sorts each partition by `created_at_key`, concatenates, and returns a NEW list — the
  input is not mutated.

CLI contract (JS↔Python boundary)
---------------------------------
Reads a JSON envelope `{ "tickets": [...], "statuses": [...] }` on stdin and writes the
sorted `tickets` array as JSON to stdout — the same shell-out pattern the workflow uses
for qrspi_resolve.py / qrspi_persist.py / qrspi_pr_body.py.
"""

import datetime
import json
import re
import sys

# Sentinel datetime used when createdAt is absent/unparseable. It is never the
# deciding factor in a comparison because the leading missing_flag (1) already
# pushes such tickets after every parseable one within the group.
_MISSING_DT = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)


def _parse_created_at(value):
    """Parse an ISO-8601 string into an aware datetime, or None if unparseable.

    Accepts a trailing 'Z' (UTC) as well as explicit offsets. Naive timestamps are
    treated as UTC so all keys are comparable. Never raises.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    # datetime.fromisoformat (3.11+) handles 'Z'; older runtimes do not, so
    # normalise a trailing Z to +00:00 defensively.
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _id_suffix(ticket_id):
    """Trailing integer of an id (e.g. 'RUS-71' -> 71); sentinel when none present."""
    if not isinstance(ticket_id, str):
        return sys.maxsize
    match = re.search(r"(\d+)\s*$", ticket_id)
    if not match:
        return sys.maxsize
    return int(match.group(1))


def created_at_key(ticket):
    """Sort key: (missing_flag, parsed_createdAt, id_numeric_suffix). Never raises."""
    dt = _parse_created_at(ticket.get("createdAt"))
    if dt is None:
        return (1, _MISSING_DT, _id_suffix(ticket.get("id")))
    return (0, dt, _id_suffix(ticket.get("id")))


def sort_tickets(tickets, statuses):
    """Group-then-sort: partition by `statuses` order, sort each by created_at_key.

    Tickets whose status is not in `statuses` form a final partition (input order
    preserved before the createdAt sort). Returns a new list; does not mutate input.
    """
    # Buckets keyed by status order index; a trailing bucket for unknown statuses.
    buckets = {status: [] for status in statuses}
    leftover = []
    for ticket in tickets:
        status = ticket.get("status")
        if status in buckets:
            buckets[status].append(ticket)
        else:
            leftover.append(ticket)

    ordered = []
    for status in statuses:
        ordered.extend(sorted(buckets[status], key=created_at_key))
    ordered.extend(sorted(leftover, key=created_at_key))
    return ordered


def main():
    envelope = json.load(sys.stdin)
    tickets = envelope.get("tickets", [])
    statuses = envelope.get("statuses", [])
    json.dump(sort_tickets(tickets, statuses), sys.stdout)


if __name__ == "__main__":
    main()
