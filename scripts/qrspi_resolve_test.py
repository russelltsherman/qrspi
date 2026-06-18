#!/usr/bin/env python3
"""Unit tests for qrspi_resolve pure helpers (name/owner split, artifact detection,
tip-branch picking, envelope assembly). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_resolve_test.py

The subprocess-backed parts (gh/git/gt, build_state) are intentionally NOT tested
here — same convention as qrspi_pr_state_test.py — and are verified by a manual
end-to-end run against a real ticket.
"""

import os
import subprocess
import sys
import tempfile

import qrspi_resolve
from qrspi_resolve import (
    parse_name_with_owner,
    detect_existing,
    pick_tip,
    slice_branches,
    build_envelope,
    comment_targets_of,
    ci_failing_of,
    ci_failing_checks_of,
    red_branches_of,
    coerce_cap,
    load_ci_revise_cap,
    worktree_is_healthy,
    teardown_orphan_worktree,
    setup_worktree,
    select_source,
    references_me,
    resolve_reviewers,
    ARTIFACTS,
    CI_REVISE_CAP_DEFAULT,
    ENGINE_ROOT,
    REPO_ROOT,
)
import qrspi_config
import qrspi_paths

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
# RESUME GUARANTEE (phase boundary): detect_existing is the deterministic skip
# gate. A phase is reused iff its artifact is present AND non-empty; a missing OR
# zero-byte (truncated/aborted-write) artifact reads False and recomputes — the
# safe direction. See docs/testing-dynamic-workflows.md "Resume guarantee".
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
# RESUME GUARANTEE (slice boundary): pick_tip selects the highest present slice
# (max N), gap-agnostic — it never synthesizes a missing slice, so a worktree is
# reused on the real tip. Which slice runs *next* is the JS/LLM alreadyCommitted
# decision (inspection-only). See docs "Resume guarantee".
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
# RESUME GUARANTEE (slice boundary): slice_branches lists exactly the present
# slice branches in ascending order, gap-agnostic — it never fabricates a missing
# slice number, so the land/resume path enumerates only real slices. See docs
# "Resume guarantee".
check("no slice branches -> empty list", slice_branches(set(), "RUS-1"), [])
check("plan/design only -> no slices",
      slice_branches({"RUS-1/design", "RUS-1/plan"}, "RUS-1"), [])
check("ascending slice branch names",
      slice_branches({"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      ["RUS-1/slice-1", "RUS-1/slice-2"])
check("slices sorted ascending even when set is out of order",
      slice_branches({"RUS-1/slice-3", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      ["RUS-1/slice-1", "RUS-1/slice-2", "RUS-1/slice-3"])
# Non-contiguous set: a gap (slice-2 absent) must NOT synthesize the missing slice
# — only the present branches are listed, preserving gap-agnostic resume (AC2).
check("slice_branches non-contiguous",
      slice_branches({"RUS-1/slice-1", "RUS-1/slice-3"}, "RUS-1"),
      ["RUS-1/slice-1", "RUS-1/slice-3"])

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

# --- RESUME GUARANTEE (AC3): existing-map passthrough onto the envelope --------------
# Seed a real <tmp>/.qrspi/<ticket>/ worktree layout, build the `existing` map from
# it via detect_existing (the deterministic phase-skip gate), and assert build_envelope
# carries that map VERBATIM onto the envelope's `existing` field. This is a passthrough
# IDENTITY check, NOT a behavioral skip proof: the actual phase-skip causation is the JS
# runPhase early-return (`if (existing && existing[name]) return true`), which is
# harness-coupled and inspection-only, not unit-tested here. See design.md §Decision 2
# and docs/testing-dynamic-workflows.md "Resume guarantee".
with tempfile.TemporaryDirectory() as _wt:
    _qd = os.path.join(_wt, ".qrspi", "RUS-1")
    os.makedirs(_qd)
    # Seed two persisted (non-empty) upstream phases; leave the rest absent.
    with open(os.path.join(_qd, "design.md"), "w") as fh:
        fh.write("persisted design")
    with open(os.path.join(_qd, "plan.md"), "w") as fh:
        fh.write("persisted plan")
    _seeded_map = detect_existing(_qd)
    # Sanity: the seeded layout produces the expected skip map (design+plan present).
    check("AC3 seeded layout: design present", _seeded_map["design"], True)
    check("AC3 seeded layout: plan present", _seeded_map["plan"], True)
    check("AC3 seeded layout: research absent", _seeded_map["research"], False)
    _ac3_env = build_envelope(_wt, _dec, _seeded_map, ok=True)
    check("AC3 build_envelope carries the existing skip-map verbatim (passthrough)",
          _ac3_env["existing"], _seeded_map)

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

# --- RUS-60 host-root / engine-root divergence (Slice 2) --------------------------------
# The envelope's repoRoot must follow the HOST checkout root the resolver returns (passed
# to build_envelope as `repo_root`), NOT the engine dir. ENGINE_ROOT (used for sibling
# imports via sys.path.insert) stays the engine's own scripts/ dir. Prove the two diverge.
check("ENGINE_ROOT is the engine scripts/ dir",
      ENGINE_ROOT, os.path.dirname(os.path.abspath(qrspi_resolve.__file__)))
_SYNTH_HOST = "/synthetic/host-checkout"
div_env = build_envelope("%s/.worktrees/RUS-1" % _SYNTH_HOST, _dec, _ex, ok=True,
                         repo_root=_SYNTH_HOST)
check("envelope repoRoot follows the supplied host checkout root",
      div_env["repoRoot"], _SYNTH_HOST)
check("envelope worktreeDir follows the host checkout, not the engine dir",
      div_env["worktreeDir"], "/synthetic/host-checkout/.worktrees/RUS-1")
check("host root diverges from ENGINE_ROOT (engine != host)",
      div_env["repoRoot"] != ENGINE_ROOT, True)
# Default (no repo_root arg) still uses the module-level host root — back-compat.
check("build_envelope without repo_root defaults to module REPO_ROOT",
      build_envelope("/wt/RUS-1", _dec, _ex, ok=True)["repoRoot"], REPO_ROOT)

# --- --repo-root override flows through the shared resolver (validated) -----------------
# main() resolves the host root via qrspi_paths.resolve_repo_root(args.repo_root, ...).
# Stub the gh validation gate (swap qrspi_paths.subprocess.run) and assert an explicit
# --repo-root value wins and is returned absolute, exactly as build_envelope would receive
# it. This pins the wiring without spawning gh/git.
class _Fake:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


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

# A stale/wrong --repo-root must fail loud (HostRootError), never silently resolve.
try:
    qrspi_paths.subprocess.run = lambda cmd, **kw: (
        _Fake(1, "", "not a github repo") if cmd[:3] == ["gh", "repo", "view"]
        else _Fake(0, ""))
    check_raises("stale --repo-root raises (fail loud)",
                 lambda: qrspi_paths.resolve_repo_root("/synthetic/stale", cwd="/x"))
finally:
    qrspi_paths.subprocess.run = _real_run

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


# --- coerce_cap (config ciReviseCap -> positive int, default 3) -------------------
# RUS-81 Slice 3 (T21/T29a): the configurable CI-revise cap. A positive integer is
# honoured; absent / non-positive / non-integer / bool falls back to the default 3.
check("default constant is 3", CI_REVISE_CAP_DEFAULT, 3)
check("coerce_cap honours a positive int", coerce_cap(5), 5)
check("coerce_cap keeps 1", coerce_cap(1), 1)
check("coerce_cap None -> default", coerce_cap(None), 3)
check("coerce_cap zero -> default", coerce_cap(0), 3)
check("coerce_cap negative -> default", coerce_cap(-2), 3)
check("coerce_cap float -> default", coerce_cap(2.5), 3)
check("coerce_cap string -> default", coerce_cap("4"), 3)
check("coerce_cap True (bool) -> default, not 1", coerce_cap(True), 3)
check("coerce_cap False (bool) -> default", coerce_cap(False), 3)

# --- load_ci_revise_cap (reads the flat ciReviseCap from config.json) -------------
# Stub qrspi_config.read_config so the loader is exercised without touching disk: the
# cap is read from the SINGLE flat top-level `ciReviseCap` key (no dot-path), coerced.
_real_read_config = qrspi_config.read_config
try:
    qrspi_config.read_config = lambda repo_root=None: {"ciReviseCap": 7}
    check("load_ci_revise_cap reads the configured positive cap",
          load_ci_revise_cap("/x"), 7)
    qrspi_config.read_config = lambda repo_root=None: {}
    check("load_ci_revise_cap absent key -> default 3", load_ci_revise_cap("/x"), 3)
    qrspi_config.read_config = lambda repo_root=None: {"ciReviseCap": 0}
    check("load_ci_revise_cap non-positive -> default 3", load_ci_revise_cap("/x"), 3)
    qrspi_config.read_config = lambda repo_root=None: {"ciReviseCap": "nope"}
    check("load_ci_revise_cap non-int -> default 3", load_ci_revise_cap("/x"), 3)
finally:
    qrspi_config.read_config = _real_read_config

# --- ci_failing_of / ci_failing_checks_of (top-level envelope re-emit) ------------
# RUS-81 Slice 3 (T22/T29b): the helpers mirror comment_targets_of, surfacing the
# frontier CI signal at the envelope top level from the decision / phase shape.
check("ci_failing_of None -> False", ci_failing_of(None), False)
check("ci_failing_of non-dict -> False", ci_failing_of("oops"), False)
check("ci_failing_of decision without key -> False",
      ci_failing_of({"action": "wait"}), False)
check("ci_failing_of False flag -> False",
      ci_failing_of({"action": "run_design", "ciFailing": False}), False)
check("ci_failing_of True flag -> True",
      ci_failing_of({"action": "revise", "ciFailing": True}), True)

# ci_failing_checks_of: [] unless the decision is CI-driven; for a CI decision it
# re-aggregates the decision phase's gathered ciFailingChecks from `phases`.
check("ci_failing_checks_of non-CI decision -> []",
      ci_failing_checks_of({"action": "run_design", "ciFailing": False, "phase": "design"},
                           {"design": {"ciFailingChecks": [{"name": "ci"}]}}), [])
check("ci_failing_checks_of None decision -> []",
      ci_failing_checks_of(None, {}), [])
check("ci_failing_checks_of CI decision, None phases -> []",
      ci_failing_checks_of({"ciFailing": True, "phase": "design"}, None), [])
_design_checks = [{"name": "build", "detailsUrl": "https://x/1"}]
check("ci_failing_checks_of design CI decision surfaces the phase's checks",
      ci_failing_checks_of({"action": "revise", "ciFailing": True, "phase": "design"},
                           {"design": {"ciFailingChecks": _design_checks}}),
      _design_checks)
check("ci_failing_checks_of missing phase data -> []",
      ci_failing_checks_of({"ciFailing": True, "phase": "design"}, {}), [])
# implementation aggregates per-slice failing-check lists (stack reviewed as a whole).
_s1 = [{"name": "lint", "detailsUrl": "u1"}]
_s2 = [{"name": "test", "detailsUrl": "u2"}]
check("ci_failing_checks_of implementation concatenates per-slice checks",
      ci_failing_checks_of({"ciFailing": True, "phase": "implementation"},
                           {"implementation": {"slices": [
                               {"ciFailingChecks": _s1}, {"ciFailingChecks": _s2},
                               {"ciFailingChecks": []}]}}),
      _s1 + _s2)

# --- build_envelope top-level CI re-emit (additive; default False/[]) -------------
check("default envelope ciFailing is False", ok_env["ciFailing"], False)
check("default envelope ciFailingChecks is empty list", ok_env["ciFailingChecks"], [])
check("err envelope ciFailing default False", err_env["ciFailing"], False)
check("err envelope ciFailingChecks default empty", err_env["ciFailingChecks"], [])
_ci_dec = {"action": "revise", "phase": "design", "ciFailing": True,
           "changeRequested": False, "commentTargets": [], "reason": "red CI"}
_ci_phases = {"design": {"ciFailingChecks": _design_checks}}
ci_env = build_envelope("/wt/RUS-1", _ci_dec, _ex, ok=True, phases=_ci_phases)
check("envelope re-emits top-level ciFailing from a CI decision",
      ci_env["ciFailing"], True)
check("envelope re-emits top-level ciFailingChecks from the phase shape",
      ci_env["ciFailingChecks"], _design_checks)
# additive: the CI re-emit leaves pre-existing fields untouched.
check("CI re-emit leaves decision untouched", ci_env["decision"], _ci_dec)
check("CI re-emit leaves commentTargets default untouched", ci_env["commentTargets"], [])

# --- red_branches_of (top-level envelope re-emit; RUS-83 Slice 3) ------------------
# The deterministic list of branches doRevise must bump this pass. [] for any non-CI
# decision; per-red-slice branches (ascending) for implementation; the single phase
# branch for a red design/plan frontier.
check("red_branches_of None decision -> []", red_branches_of(None, {}, "RUS-1"), [])
check("red_branches_of non-dict decision -> []",
      red_branches_of("oops", {}, "RUS-1"), [])
check("red_branches_of non-CI decision -> []",
      red_branches_of({"action": "run_design", "ciFailing": False, "phase": "design"},
                      {"design": {"ciState": "red"}}, "RUS-1"), [])
check("red_branches_of CI decision, None phases -> []",
      red_branches_of({"ciFailing": True, "phase": "design"}, None, "RUS-1"), [])
# design/plan: the single frontier phase branch when its gathered ciState is red.
check("red_branches_of red design frontier -> [the design branch]",
      red_branches_of({"action": "revise", "ciFailing": True, "phase": "design"},
                      {"design": {"ciState": "red"}}, "RUS-1"),
      ["RUS-1/design"])
check("red_branches_of red plan frontier -> [the plan branch]",
      red_branches_of({"action": "revise", "ciFailing": True, "phase": "plan"},
                      {"plan": {"ciState": "red"}}, "RUS-1"),
      ["RUS-1/plan"])
check("red_branches_of design CI decision but phase not red -> []",
      red_branches_of({"action": "revise", "ciFailing": True, "phase": "design"},
                      {"design": {"ciState": "green"}}, "RUS-1"), [])
# implementation: each red slice branch, ascending. A [red, green, red] stack yields
# slice-1 + slice-3; the green slice-2 is excluded (no needless re-push).
check("red_branches_of implementation [red, green, red] -> slice-1 + slice-3",
      red_branches_of({"action": "revise", "ciFailing": True, "phase": "implementation"},
                      {"implementation": {"slices": [
                          {"n": 1, "ciState": "red"},
                          {"n": 2, "ciState": "green"},
                          {"n": 3, "ciState": "red"}]}}, "RUS-7"),
      ["RUS-7/slice-1", "RUS-7/slice-3"])
check("red_branches_of implementation no red slices -> []",
      red_branches_of({"action": "revise", "ciFailing": True, "phase": "implementation"},
                      {"implementation": {"slices": [
                          {"n": 1, "ciState": "green"},
                          {"n": 2, "ciState": "pending"}]}}, "RUS-7"),
      [])
check("red_branches_of implementation missing slices -> []",
      red_branches_of({"action": "revise", "ciFailing": True, "phase": "implementation"},
                      {"implementation": {}}, "RUS-7"), [])

# build_envelope re-emits ciRedBranches at the top level (additive; default []).
check("default envelope ciRedBranches is empty list", ok_env["ciRedBranches"], [])
check("err envelope ciRedBranches default empty", err_env["ciRedBranches"], [])
_rb_dec = {"action": "revise", "phase": "implementation", "ciFailing": True,
           "changeRequested": False, "commentTargets": [], "reason": "red CI"}
_rb_phases = {"implementation": {"slices": [
    {"n": 1, "ciState": "red"}, {"n": 2, "ciState": "green"}]}}
rb_env = build_envelope("/wt/RUS-7", _rb_dec, _ex, ok=True, phases=_rb_phases,
                        ticket="RUS-7")
check("envelope re-emits top-level ciRedBranches from a CI decision",
      rb_env["ciRedBranches"], ["RUS-7/slice-1"])
check("ciRedBranches re-emit leaves decision untouched", rb_env["decision"], _rb_dec)


# --- orphaned-worktree self-heal (hermetic real-git integration) -----------
# These exercise the subprocess-backed worktree path against a throwaway temp repo
# (not the pure helpers tested above). They pin the orphaned-worktree regression: a
# `.worktrees/<id>` dir whose `.git/worktrees/<id>` admin metadata was pruned must be
# detected as unhealthy and self-healed by setup_worktree, NOT reused (the bare reuse
# is what fed restack a "fatal: not a git repository" worktree).

def _git(args, cwd, check_rc=True):
    res = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check_rc and res.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), res.stderr.strip()))
    return res


def _seed_repo(root):
    """A minimal repo on `main` with one commit and a `RUS-1/design` branch."""
    _git(["init", "-b", "main"], root)
    _git(["config", "user.email", "t@t.t"], root)
    _git(["config", "user.name", "t"], root)
    with open(os.path.join(root, "f.txt"), "w") as fh:
        fh.write("seed\n")
    _git(["add", "."], root)
    _git(["commit", "-m", "seed"], root)
    _git(["branch", "RUS-1/design"], root)


def _run_worktree_selfheal_tests():
    with tempfile.TemporaryDirectory() as root:
        _seed_repo(root)
        wt = os.path.join(root, ".worktrees", "RUS-1")

        # 1. A freshly added worktree is healthy and reused verbatim.
        first = setup_worktree("RUS-1", repo_root=root)
        check("setup_worktree creates the worktree at the canonical path", first, wt)
        check("freshly created worktree is healthy", worktree_is_healthy(wt), True)
        reused = setup_worktree("RUS-1", repo_root=root)
        check("a healthy worktree is reused (same path)", reused, wt)
        check("reused worktree still healthy", worktree_is_healthy(wt), True)

        # 2. Orphan it: the working dir survives but the admin metadata is gone.
        admin = os.path.join(root, ".git", "worktrees", "RUS-1")
        import shutil as _sh
        _sh.rmtree(admin)
        check("orphaned worktree dir still exists on disk",
              os.path.isdir(wt), True)
        check("orphaned worktree is detected UNHEALTHY",
              worktree_is_healthy(wt), False)

        # 3. setup_worktree self-heals instead of reusing the orphan.
        healed = setup_worktree("RUS-1", repo_root=root)
        check("self-heal returns the canonical worktree path", healed, wt)
        check("self-healed worktree is healthy again", worktree_is_healthy(wt), True)
        # The recreated worktree must be checked out on the ticket's branch tip.
        head = subprocess.run(["git", "-C", wt, "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        check("self-healed worktree is on the branch tip", head, "RUS-1/design")

        # 4. teardown leaves a clean tree (no dangling admin entry).
        teardown_orphan_worktree(wt, root)
        pruned = subprocess.run(["git", "-C", root, "worktree", "list", "--porcelain"],
                                capture_output=True, text=True).stdout
        check("teardown removes the worktree from `git worktree list`",
              "RUS-1" in pruned, False)


_run_worktree_selfheal_tests()


def run():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
