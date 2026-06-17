#!/usr/bin/env python3
"""Post one reviewer-comment reply (inline OR top-level) and print a ReplyEnvelope JSON.

Why this exists
---------------
The QRSPI `respond_comment` action (resolved in qrspi_resolve_state.py from the
`commentTargets` the gather emits) must actually WRITE a reply to a reviewer's PR
comment. Two shapes exist:

  - inline (a review-thread comment): replied to via the REST endpoint
    `POST /repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies`, so the reply
    lands threaded under the original line comment.
  - top-level (an issue-style PR comment): there is no threaded reply, so we post a
    fresh PR comment via `gh pr comment`.

Like every other write/amend helper in this harness (qrspi_persist.py,
qrspi_revise_amend.py, qrspi_pr_body.py) this script is SELF-LOCATING — the repo root and
owner/repo are derived from git, never typed by the weak worker model (which mangles the
"qrspi" path token across multi-step shell). The reply body is read from a `--body-file`
so the worker never has to quote arbitrary markdown on a command line.

The pure core (arg → request mapping, response → envelope) is unit-tested in
qrspi_comment_reply_test.py; the subprocess mechanics are exercised by the manual
end-to-end gh-write re-verification gate (the design-mandated check that gh PR comment
writes succeed in THIS runtime before orchestration relies on it).

Output: a single JSON ReplyEnvelope on stdout:
    { ok, replyId, inReplyToId, error? }
"""

import argparse
import json
import os
import subprocess
import sys

# ENGINE_ROOT: the dir holding this engine's scripts/ (from __file__) — used ONLY for
# sibling imports. REPO_ROOT: the HOST checkout root all host paths key off, resolved via
# the shared qrspi_paths.resolve_repo_root() (git-common-dir first — the MAIN checkout even
# from a worktree; __file__ parent last resort). validate=False keeps gh off the import
# path. This collapses the script's former private git-common-dir copy onto the shared
# resolver — behavior-preserving (ref: design.md Decision 2, §Delta).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

REPLY_MODE_INLINE = "inline"
REPLY_MODE_TOPLEVEL = "toplevel"
REPLY_MODES = (REPLY_MODE_INLINE, REPLY_MODE_TOPLEVEL)


# --- pure core (unit-tested) -----------------------------------------------

def mode_to_request(reply_mode, owner, repo, pr, comment_id, body):
    """Map (reply_mode, target coordinates, body) to a request descriptor. Pure — no I/O,
    so the mode→endpoint mapping is unit-testable without gh.

    inline   -> a `gh api` POST to the review-comment replies endpoint, carrying the body
                field. Threads the reply under the original line comment `comment_id`.
    toplevel -> a `gh pr comment` invocation (there is no threaded reply for an
                issue-style PR comment; we post a fresh one).

    Returns a dict:
      inline   -> {"kind": "api",
                   "method": "POST",
                   "path": "/repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies",
                   "fields": {"body": body}}
      toplevel -> {"kind": "gh",
                   "cmd": ["pr", "comment", str(pr), "--repo", "{owner}/{repo}",
                           "--body-file", "-"],
                   "stdin": body}
    """
    if reply_mode == REPLY_MODE_INLINE:
        return {
            "kind": "api",
            "method": "POST",
            "path": "/repos/%s/%s/pulls/%s/comments/%s/replies" % (
                owner, repo, pr, comment_id),
            "fields": {"body": body},
        }
    if reply_mode == REPLY_MODE_TOPLEVEL:
        return {
            "kind": "gh",
            "cmd": ["pr", "comment", str(pr),
                    "--repo", "%s/%s" % (owner, repo),
                    "--body-file", "-"],
            "stdin": body,
        }
    raise ValueError("unknown reply_mode: %r (expected one of %r)" % (reply_mode, REPLY_MODES))


def response_to_envelope(reply_mode, raw_response, in_reply_to_id):
    """Parse a gh/REST response into a ReplyEnvelope. Pure, so the response→envelope shape
    is unit-testable without running gh.

    `raw_response` is the gh stdout text. For inline replies it is the JSON body of the
    created review comment (carrying `.id`, the new reply id). For top-level comments
    `gh pr comment` prints the created comment's URL, not JSON, so there is no numeric id
    to capture — replyId is None but ok is still true.

    Returns ReplyEnvelope: {ok, replyId, inReplyToId, error}. On any parse problem for the
    inline case (non-JSON, missing/null `.id`) we fail closed with ok=false and a populated
    error, rather than silently reporting success with a null id.
    """
    in_reply_to_id = _as_int_or_none(in_reply_to_id)

    if reply_mode == REPLY_MODE_TOPLEVEL:
        # gh pr comment prints a URL, not JSON: success with no numeric reply id.
        return _envelope(ok=True, reply_id=None, in_reply_to_id=in_reply_to_id, error=None)

    if reply_mode != REPLY_MODE_INLINE:
        return _envelope(ok=False, reply_id=None, in_reply_to_id=in_reply_to_id,
                         error="unknown reply_mode: %r" % (reply_mode,))

    try:
        parsed = json.loads(raw_response)
    except (ValueError, TypeError) as exc:
        return _envelope(ok=False, reply_id=None, in_reply_to_id=in_reply_to_id,
                         error="could not parse inline reply response as JSON: %s" % exc)

    if not isinstance(parsed, dict) or parsed.get("id") is None:
        return _envelope(ok=False, reply_id=None, in_reply_to_id=in_reply_to_id,
                         error="inline reply response missing `.id`: %r" % (raw_response,))

    return _envelope(ok=True, reply_id=_as_int_or_none(parsed.get("id")),
                     in_reply_to_id=in_reply_to_id, error=None)


def error_envelope(in_reply_to_id, message):
    """A failed ReplyEnvelope (ok=false, replyId=null) carrying `message`. Pure."""
    return _envelope(ok=False, reply_id=None,
                     in_reply_to_id=_as_int_or_none(in_reply_to_id), error=message)


def _envelope(ok, reply_id, in_reply_to_id, error):
    """Assemble the ReplyEnvelope dict in canonical key order. Pure."""
    return {
        "ok": ok,
        "replyId": reply_id,
        "inReplyToId": in_reply_to_id,
        "error": error,
    }


def _as_int_or_none(value):
    """Coerce a value to int, or None when it is None / not int-like. Pure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# --- subprocess-backed mechanics (manual e2e, not unit-tested) -------------

def _run(cmd, cwd=None, stdin=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def resolve_owner_repo(cwd=None):
    """Derive (owner, repo) from the GitHub remote via gh, so the worker never types it.

    Returns (owner, repo, error). On failure owner/repo are None and error is populated.
    """
    rc, out, err = _run(
        ["gh", "repo", "view", "--json", "owner,name",
         "-q", "[.owner.login, .name] | @tsv"],
        cwd=cwd)
    if rc != 0:
        return None, None, ("could not resolve owner/repo via gh: %s" % (err or out).strip())
    parts = (out or "").strip().split("\t")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None, ("unexpected `gh repo view` output: %r" % (out,))
    return parts[0], parts[1], None


def post_reply(request, cwd=None):
    """Execute a request descriptor from mode_to_request via subprocess.

    Returns (rc, stdout, stderr).
    """
    if request["kind"] == "api":
        cmd = ["gh", "api", "--method", request["method"], request["path"]]
        for key, val in request["fields"].items():
            cmd += ["-f", "%s=%s" % (key, val)]
        return _run(cmd, cwd=cwd)
    if request["kind"] == "gh":
        return _run(["gh"] + request["cmd"], cwd=cwd, stdin=request.get("stdin"))
    raise ValueError("unknown request kind: %r" % (request.get("kind"),))


def main():
    parser = argparse.ArgumentParser(
        description="Post one inline or top-level reviewer-comment reply and print a "
                    "ReplyEnvelope JSON (self-locating).")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-54")
    parser.add_argument("--pr", required=True, help="PR number to reply on")
    parser.add_argument("--comment-id", required=False, default=None,
                        help="Target comment id (the review-comment databaseId for inline; "
                             "the comment being addressed for top-level). REQUIRED in inline "
                             "mode; OPTIONAL in toplevel mode (a synopsis with no parent "
                             "comment posts a fresh PR comment).")
    parser.add_argument("--reply-mode", required=True, choices=list(REPLY_MODES),
                        help="inline -> threaded review-comment reply; toplevel -> fresh PR comment")
    parser.add_argument("--body-file", required=True,
                        help="Path to a file holding the reply body (avoids shell quoting)")
    args = parser.parse_args()

    # --comment-id is now optional at the parser level so a toplevel synopsis with no
    # parent comment can post (RUS-89). Inline mode still REQUIRES it — the replies
    # endpoint is keyed on the comment id — so enforce that here, fail-closed.
    if args.reply_mode == REPLY_MODE_INLINE and args.comment_id is None:
        _emit(error_envelope(
            None, "--comment-id is required in inline reply mode"))
        return 1

    repo_root = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
    worktree = os.path.join(repo_root, ".worktrees", args.ticket)
    cwd = worktree if os.path.isdir(worktree) else repo_root

    try:
        with open(args.body_file, "r", encoding="utf-8") as fh:
            body = fh.read()
    except OSError as exc:
        _emit(error_envelope(args.comment_id, "could not read --body-file: %s" % exc))
        return 1

    owner, repo, err = resolve_owner_repo(cwd=cwd)
    if err is not None:
        _emit(error_envelope(args.comment_id, err))
        return 1

    request = mode_to_request(args.reply_mode, owner, repo, args.pr, args.comment_id, body)
    rc, out, serr = post_reply(request, cwd=cwd)
    if rc != 0:
        _emit(error_envelope(
            args.comment_id,
            "gh write failed (rc=%d): %s" % (rc, (serr or out).strip())))
        return 1

    env = response_to_envelope(args.reply_mode, out, args.comment_id)
    _emit(env)
    return 0 if env["ok"] else 1


def _emit(envelope):
    json.dump(envelope, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    sys.exit(main())
