#!/usr/bin/env python3
"""Unit tests for qrspi_resolve pure helpers (name/owner split, artifact detection,
tip-branch picking, envelope assembly). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_resolve_test.py

The subprocess-backed parts (gh/git/gt, build_state) are intentionally NOT tested
here — same convention as qrspi_pr_state_test.py — and are verified by a manual
end-to-end run against a real ticket.
"""

import os
import sys
import tempfile

from qrspi_resolve import (
    parse_name_with_owner,
    detect_existing,
    pick_tip,
    slice_branches,
    build_envelope,
    comment_targets_of,
    select_source,
    references_me,
    resolve_reviewers,
    ARTIFACTS,
    REPO_ROOT,
)

failures = 0
total = 0


def check(name, got, want):
    global failures, total
    total += 1
    if got != want:
        print("FAIL: %s\n      expected %r\n      got      %r" % (name, want, got))
        failures += 1
    else:
        print("ok: %s" % name)


def check_raises(name, fn):
    global failures, total
    total += 1
    try:
        fn()
    except Exception:
        print("ok: %s" % name)
        return
    print("FAIL: %s\n      expected an exception, none raised" % name)
    failures += 1


# --- parse_name_with_owner --------------------------------------------------
check("splits owner/repo", parse_name_with_owner("russelltsherman/qrspi"),
      ("russelltsherman", "qrspi"))
check("tolerates trailing newline", parse_name_with_owner("a/b\n"), ("a", "b"))
check_raises("rejects missing slash", lambda: parse_name_with_owner("noslash"))
check_raises("rejects empty owner", lambda: parse_name_with_owner("/repo"))
check_raises("rejects empty repo", lambda: parse_name_with_owner("owner/"))
check_raises("rejects too many slashes", lambda: parse_name_with_owner("a/b/c"))
check_raises("rejects None", lambda: parse_name_with_owner(None))

# --- detect_existing --------------------------------------------------------
check("missing dir -> all False", detect_existing("/no/such/dir/anywhere"),
      {name: False for name in ARTIFACTS})

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

# --- pick_tip ---------------------------------------------------------------
check("no branches -> None", pick_tip(set(), "RUS-1"), None)
check("design only", pick_tip({"RUS-1/design"}, "RUS-1"), "RUS-1/design")
check("plan beats design", pick_tip({"RUS-1/design", "RUS-1/plan"}, "RUS-1"),
      "RUS-1/plan")
check("highest slice wins",
      pick_tip({"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      "RUS-1/slice-2")
check("slice beats plan even out of order",
      pick_tip({"RUS-1/plan", "RUS-1/slice-3", "RUS-1/slice-1"}, "RUS-1"),
      "RUS-1/slice-3")

# --- slice_branches (ascending slice branch names from the normalized branch set) --
check("no slice branches -> empty list", slice_branches(set(), "RUS-1"), [])
check("plan/design only -> no slices",
      slice_branches({"RUS-1/design", "RUS-1/plan"}, "RUS-1"), [])
check("ascending slice branch names",
      slice_branches({"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      ["RUS-1/slice-1", "RUS-1/slice-2"])
check("slices sorted ascending even when set is out of order",
      slice_branches({"RUS-1/slice-3", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      ["RUS-1/slice-1", "RUS-1/slice-2", "RUS-1/slice-3"])

# --- build_envelope ---------------------------------------------------------
_dec = {"action": "run_design", "reason": "x"}
_ex = {name: False for name in ARTIFACTS}
ok_env = build_envelope("/wt/RUS-1", _dec, _ex, ok=True)
check("ok envelope ok flag", ok_env["ok"], True)
check("ok envelope carries decision", ok_env["decision"], _dec)
check("ok envelope repoRoot is derived REPO_ROOT", ok_env["repoRoot"], REPO_ROOT)
check("ok envelope has no error key", "error" in ok_env, False)
check("ok envelope worktreeDir", ok_env["worktreeDir"], "/wt/RUS-1")

err_env = build_envelope("/wt/RUS-1", None, _ex, ok=False, error="boom")
check("err envelope ok flag", err_env["ok"], False)
check("err envelope error message", err_env["error"], "boom")
check("envelope default reviewers empty", ok_env["reviewers"], "")
check("envelope default teamReviewers empty", ok_env["teamReviewers"], "")
rev_env = build_envelope("/wt/RUS-1", _dec, _ex, ok=True,
                         reviewers="alice,bob", team_reviewers="org/team")
check("envelope carries reviewers", rev_env["reviewers"], "alice,bob")
check("envelope carries teamReviewers", rev_env["teamReviewers"], "org/team")

# --- root-level tip/slices (additive; the land worker reads the slice list from the
# contract instead of reconstructing <id>/slice-1 from the ticket id; RUS-70) --------
check("default envelope tip is None", ok_env["tip"], None)
check("default envelope slices is empty list", ok_env["slices"], [])
check("err envelope tip default None", err_env["tip"], None)
check("err envelope slices default empty", err_env["slices"], [])
_slices = ["RUS-1/slice-1", "RUS-1/slice-2"]
ts_env = build_envelope("/wt/RUS-1", _dec, _ex, ok=True,
                        tip="RUS-1/slice-2", slices=_slices)
check("envelope carries root-level tip", ts_env["tip"], "RUS-1/slice-2")
check("envelope carries root-level slices (ascending)", ts_env["slices"], _slices)
# tip/slices are additive — pre-existing root fields are byte-for-byte unchanged.
check("tip/slices addition leaves decision untouched", ts_env["decision"], _dec)
check("tip/slices addition leaves repoRoot untouched", ts_env["repoRoot"], REPO_ROOT)
check("tip/slices addition leaves worktreeDir untouched",
      ts_env["worktreeDir"], "/wt/RUS-1")
check("tip/slices addition leaves existing untouched", ts_env["existing"], _ex)
check("tip/slices addition leaves reviewers default untouched", ts_env["reviewers"], "")
check("tip/slices addition leaves commentTargets default untouched",
      ts_env["commentTargets"], [])

# --- ticketContentPath handoff (decouple: the script emits the PATH, never the body, so
# the fragile ticket text — e.g. Linear <issue> mention tags — is read file->file by the
# design agents and never echoed through the weak resolve worker, which HTML-escaped
# `>`->`&gt;` and broke JSON.parse; see RUS-69) ----------------------------------------
check("envelope default ticketContentPath empty", ok_env["ticketContentPath"], "")
check("envelope no longer carries body-embedding ticketContent field",
      "ticketContent" in ok_env, False)
tcp_env = build_envelope("/wt/RUS-1", _dec, _ex, ok=True,
                         ticket_content_path="/tmp/phase-stage/RUS-1/ticket.md")
check("envelope carries ticketContentPath",
      tcp_env["ticketContentPath"], "/tmp/phase-stage/RUS-1/ticket.md")
check("ticketContentPath envelope carries no ticketContent field",
      "ticketContent" in tcp_env, False)
check("err envelope still carries ticketContentPath",
      build_envelope("/wt/RUS-1", None, _ex, ok=False, error="boom",
                     ticket_content_path="/tmp/phase-stage/RUS-1/ticket.md")["ticketContentPath"],
      "/tmp/phase-stage/RUS-1/ticket.md")

# --- top-level commentTargets (re-emitted from the decision for doRespondComment) --
check("non-respond decision -> empty top-level commentTargets",
      ok_env["commentTargets"], [])
check("err envelope -> empty top-level commentTargets",
      err_env["commentTargets"], [])
_tgts = [{"commentId": 7, "author": "rev", "body": "fix?", "threadType": "inline",
          "threadId": "PRT_1", "lastReplyAuthor": "rev"}]
_rc_dec = {"action": "revise", "phase": "design", "changeRequested": False,
           "commentTargets": _tgts, "reason": "y"}
rc_env = build_envelope("/wt/RUS-1", _rc_dec, _ex, ok=True)
check("revise decision surfaces top-level commentTargets",
      rc_env["commentTargets"], _tgts)
check("comment_targets_of None -> []", comment_targets_of(None), [])
check("comment_targets_of decision w/o key -> []",
      comment_targets_of({"action": "wait"}), [])
check("comment_targets_of non-list value -> []",
      comment_targets_of({"commentTargets": "oops"}), [])
check("comment_targets_of passes a list through",
      comment_targets_of({"commentTargets": _tgts}), _tgts)

# --- select_source (config > default; no env override) ----------------------
check("config used (list)",
      select_source({"reviewers": ["zed", "amy"]}, "reviewers", ["@me"]),
      ["zed", "amy"])
check("config used (csv string)",
      select_source({"reviewers": "zed, amy"}, "reviewers", ["@me"]),
      ["zed", "amy"])
check("config empty list is opt-out",
      select_source({"reviewers": []}, "reviewers", ["@me"]), [])
check("default when key absent from config",
      select_source({}, "reviewers", ["@me"]), ["@me"])
check("team default empty", select_source({}, "teamReviewers", []), [])

# --- references_me ----------------------------------------------------------
check("default references @me", references_me({}), True)
check("config without @me does not", references_me({"reviewers": ["alice"]}), False)
check("config with @me does", references_me({"reviewers": ["@me", "alice"]}), True)
check("config opt-out does not reference @me", references_me({"reviewers": []}), False)
check("@me is case-insensitive", references_me({"reviewers": ["@ME"]}), True)

# --- resolve_reviewers ------------------------------------------------------
check("default expands @me to login",
      resolve_reviewers({}, "carol"), (["carol"], []))
check("@me dropped when no login (gh unauthenticated)",
      resolve_reviewers({}, None), ([], []))
check("explicit config reviewers ignore login expansion",
      resolve_reviewers({"reviewers": ["alice", "bob"]}, "carol"),
      (["alice", "bob"], []))
check("config @me mixes with explicit, expanded + deduped",
      resolve_reviewers({"reviewers": ["@me", "alice", "Alice"]}, "carol"),
      (["carol", "alice"], []))
check("@me dedupes against an explicit same login",
      resolve_reviewers({"reviewers": ["@me", "carol"]}, "carol"),
      (["carol"], []))
check("team reviewers from config",
      resolve_reviewers({"reviewers": ["alice"], "teamReviewers": ["org/eng", "org/sec"]}, None),
      (["alice"], ["org/eng", "org/sec"]))
check("config opt-out yields no reviewers",
      resolve_reviewers({"reviewers": []}, "carol"), ([], []))


def run():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
