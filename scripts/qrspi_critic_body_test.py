#!/usr/bin/env python3
"""Unit tests for qrspi_critic_body — the pure residual-findings splice core.
Stdlib-only, assert-based, no third-party deps, no test runner.
Run: python3 scripts/qrspi_critic_body_test.py

Covers (ref: structure §Slice 1 tests, plan §1.8, Decision 4):
  - empty findings        ⇒ message emitted UNCHANGED (no-op short-circuit)
  - single finding        ⇒ spliced body block between subject and trailers
  - multi-line findings    ⇒ each finding bulleted
  - idempotent re-splice  ⇒ re-running on an already-spliced message yields same output
  - JSON-array findings (synthesize output) and {text, lens} tags formatted
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_critic_body import format_body, parse_findings, splice  # noqa: E402

failures = 0
total = 0


def check(label, got, want):
    global failures, total
    total += 1
    if got == want:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))


def check_true(label, cond):
    global failures, total
    total += 1
    if cond:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s (condition false)" % label)


SUBJECT = "RUS-56 [D]: design for the critic panel"
TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"
MSG = SUBJECT + "\n\n" + TRAILER + "\n"


# --- empty findings ⇒ message emitted UNCHANGED (no-op) ---------------------
check("empty findings string ⇒ message unchanged",
      splice(MSG, ""),
      MSG)

check("whitespace-only findings ⇒ message unchanged",
      splice(MSG, "   \n\t  "),
      MSG)

check("None findings ⇒ message unchanged (no-op)",
      splice(MSG, None),
      MSG)

check("empty JSON array findings ⇒ message unchanged",
      splice(MSG, "[]"),
      MSG)

# --- parse_findings: text and JSON forms ------------------------------------
check("plain text, one finding per line",
      parse_findings("missing AC2\nscope drift\n"),
      ["missing AC2", "scope drift"])

check("blank lines are dropped",
      parse_findings("a\n\n  \nb\n"),
      ["a", "b"])

check("JSON array of bare strings",
      parse_findings('["missing AC2", "scope drift"]'),
      ["missing AC2", "scope drift"])

check("JSON array of {text, lens} dicts ⇒ text (lens) formatting",
      parse_findings('[{"text": "missing AC2", "lens": "completeness"}, '
                     '{"text": "overbuilt", "lens": "simplicity"}]'),
      ["missing AC2 (completeness)", "overbuilt (simplicity)"])

check("JSON array mixing tagged dict and bare string",
      parse_findings('[{"text": "drift", "lens": "edge-alignment"}, "bare"]'),
      ["drift (edge-alignment)", "bare"])

check("malformed JSON array falls back to one-per-line text parse",
      parse_findings('["unterminated'),
      ['["unterminated'])

# --- format_body ------------------------------------------------------------
check("format_body of empty list ⇒ empty string (no-op signal)",
      format_body([]),
      "")

check_true("format_body titles the block and bullets each finding",
           format_body(["a", "b"]).startswith("## Residual critic findings")
           and "- a" in format_body(["a", "b"])
           and "- b" in format_body(["a", "b"]))

# --- single finding ⇒ spliced body block ------------------------------------
single = splice(MSG, "missing AC2")
check_true("single finding: subject preserved as first line",
           single.splitlines()[0] == SUBJECT)
check_true("single finding: body block present",
           "## Residual critic findings" in single and "- missing AC2" in single)
check_true("single finding: trailer preserved at the bottom",
           single.rstrip().splitlines()[-1] == TRAILER)
check_true("single finding: body sits between subject and trailer",
           single.index("## Residual critic findings") > single.index(SUBJECT)
           and single.index("- missing AC2") < single.index(TRAILER))

# --- multi-line findings ⇒ each bulleted ------------------------------------
multi = splice(MSG, "missing AC2\nscope drift\nno rollback note")
check_true("multi-line findings: all three bulleted",
           "- missing AC2" in multi and "- scope drift" in multi
           and "- no rollback note" in multi)
check_true("multi-line findings: subject + trailer still intact",
           multi.splitlines()[0] == SUBJECT
           and multi.rstrip().splitlines()[-1] == TRAILER)

# --- idempotent re-splice ---------------------------------------------------
once = splice(MSG, "missing AC2\nscope drift")
twice = splice(once, "missing AC2\nscope drift")
check("re-splicing an already-spliced message with same findings is idempotent",
      twice, once)

# JSON-array findings from synthesize splice the same as the equivalent text.
json_spliced = splice(MSG, '["missing AC2", "scope drift"]')
text_spliced = splice(MSG, "missing AC2\nscope drift")
check("JSON-array findings splice identically to one-per-line text",
      json_spliced, text_spliced)


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
