#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_order_tickets.py — run with `python3`.

Covers the pure comparator + group-then-sort with in-memory dicts. Five cases:
(a) ascending createdAt within a group; (b) phase grouping/order preserved across
STATUSES (AC3); (c) missing createdAt sorts last (AC5); (d) unparseable createdAt
sorts last with no raise (AC5); (e) id numeric-suffix tie-break on equal createdAt
(RUS-7 before RUS-71, Decision 3)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrspi_order_tickets import created_at_key, sort_tickets  # noqa: E402

STATUSES = ["Selected", "Design Review", "Plan Review", "Code Review"]


def _t(tid, status, created=None):
    ticket = {"id": tid, "title": tid.lower(), "status": status}
    if created is not None:
        ticket["createdAt"] = created
    return ticket


def _ids(tickets):
    return [t["id"] for t in tickets]


class AscendingWithinGroupTests(unittest.TestCase):
    def test_ascending_created_at_within_a_group(self):
        tickets = [
            _t("RUS-3", "Selected", "2026-01-03T00:00:00Z"),
            _t("RUS-1", "Selected", "2026-01-01T00:00:00Z"),
            _t("RUS-2", "Selected", "2026-01-02T00:00:00Z"),
        ]
        self.assertEqual(_ids(sort_tickets(tickets, STATUSES)), ["RUS-1", "RUS-2", "RUS-3"])


class PhaseGroupingTests(unittest.TestCase):
    def test_grouping_and_status_order_preserved(self):
        # Interleaved input; expect grouped by STATUSES order, ascending within each.
        tickets = [
            _t("RUS-10", "Plan Review", "2026-01-01T00:00:00Z"),
            _t("RUS-11", "Selected", "2026-01-02T00:00:00Z"),
            _t("RUS-12", "Design Review", "2026-01-05T00:00:00Z"),
            _t("RUS-13", "Selected", "2026-01-01T00:00:00Z"),
            _t("RUS-14", "Design Review", "2026-01-04T00:00:00Z"),
        ]
        self.assertEqual(
            _ids(sort_tickets(tickets, STATUSES)),
            ["RUS-13", "RUS-11", "RUS-14", "RUS-12", "RUS-10"],
        )

    def test_unknown_status_partition_sorts_last(self):
        tickets = [
            _t("RUS-20", "Mystery", "2026-01-01T00:00:00Z"),
            _t("RUS-21", "Selected", "2026-01-02T00:00:00Z"),
        ]
        self.assertEqual(_ids(sort_tickets(tickets, STATUSES)), ["RUS-21", "RUS-20"])


class MissingCreatedAtTests(unittest.TestCase):
    def test_missing_created_at_sorts_last(self):
        tickets = [
            _t("RUS-31", "Selected"),  # no createdAt key
            _t("RUS-30", "Selected", "2026-01-01T00:00:00Z"),
        ]
        self.assertEqual(_ids(sort_tickets(tickets, STATUSES)), ["RUS-30", "RUS-31"])

    def test_missing_key_does_not_raise(self):
        # created_at_key on a ticket with no createdAt must not raise.
        created_at_key({"id": "RUS-99", "status": "Selected"})


class UnparseableCreatedAtTests(unittest.TestCase):
    def test_unparseable_created_at_sorts_last_no_raise(self):
        tickets = [
            _t("RUS-41", "Selected", "not-a-date"),
            _t("RUS-40", "Selected", "2026-01-01T00:00:00Z"),
        ]
        # Must not raise, and the garbage value sorts last.
        self.assertEqual(_ids(sort_tickets(tickets, STATUSES)), ["RUS-40", "RUS-41"])

    def test_non_string_created_at_sorts_last(self):
        tickets = [
            _t("RUS-50", "Selected", "2026-01-01T00:00:00Z"),
        ]
        weird = {"id": "RUS-51", "status": "Selected", "createdAt": 12345}
        self.assertEqual(
            _ids(sort_tickets(tickets + [weird], STATUSES)), ["RUS-50", "RUS-51"]
        )


class IdTieBreakTests(unittest.TestCase):
    def test_id_numeric_suffix_tie_break(self):
        # Equal createdAt -> deterministic tie-break by numeric id suffix: 7 < 71.
        tickets = [
            _t("RUS-71", "Selected", "2026-01-01T00:00:00Z"),
            _t("RUS-7", "Selected", "2026-01-01T00:00:00Z"),
        ]
        self.assertEqual(_ids(sort_tickets(tickets, STATUSES)), ["RUS-7", "RUS-71"])


class PurityTests(unittest.TestCase):
    def test_input_not_mutated(self):
        tickets = [
            _t("RUS-61", "Selected", "2026-01-02T00:00:00Z"),
            _t("RUS-60", "Selected", "2026-01-01T00:00:00Z"),
        ]
        before = _ids(tickets)
        sort_tickets(tickets, STATUSES)
        self.assertEqual(_ids(tickets), before)


if __name__ == "__main__":
    unittest.main()
