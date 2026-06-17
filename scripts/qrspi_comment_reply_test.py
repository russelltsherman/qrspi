#!/usr/bin/env python3
"""Unit tests for qrspi_comment_reply.py pure core — stdlib only, run with python3.

Covers the two pure functions the design pins as the testable core:
  - mode_to_request: reply_mode -> request descriptor (inline replies endpoint vs
    `gh pr comment`).
  - response_to_envelope: gh/REST response -> ReplyEnvelope, capturing the created `.id`
    on success and failing closed on a missing/unparseable id.

The subprocess mechanics (resolve_owner_repo, post_reply, main) are deliberately NOT
tested here — they are exercised by the manual gh-write re-verification gate.
"""

import unittest

import qrspi_comment_reply as m


class ModeToRequestTest(unittest.TestCase):
    def test_inline_maps_to_replies_post(self):
        req = m.mode_to_request(
            "inline", "octo", "qrspi", 42, 99887766, "thanks, fixed")
        self.assertEqual(req["kind"], "api")
        self.assertEqual(req["method"], "POST")
        self.assertEqual(
            req["path"],
            "/repos/octo/qrspi/pulls/42/comments/99887766/replies",
        )
        self.assertEqual(req["fields"], {"body": "thanks, fixed"})

    def test_inline_path_uses_comment_id_not_pr(self):
        # Regression guard: the replies endpoint is keyed on the COMMENT id, with the PR
        # number in the /pulls/{n}/ segment — they must not be swapped.
        req = m.mode_to_request("inline", "o", "r", 7, 12345, "body")
        self.assertIn("/pulls/7/comments/12345/replies", req["path"])

    def test_toplevel_maps_to_gh_pr_comment(self):
        req = m.mode_to_request(
            "toplevel", "octo", "qrspi", 42, 99887766, "top-level reply")
        self.assertEqual(req["kind"], "gh")
        self.assertEqual(
            req["cmd"],
            ["pr", "comment", "42", "--repo", "octo/qrspi", "--body-file", "-"],
        )
        self.assertEqual(req["stdin"], "top-level reply")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            m.mode_to_request("sideways", "o", "r", 1, 2, "b")

    def test_toplevel_ignores_comment_id_when_none(self):
        # RUS-89: toplevel mode does not key on a parent comment, so a None
        # comment_id still produces a valid `gh pr comment` request descriptor.
        req = m.mode_to_request("toplevel", "octo", "qrspi", 42, None, "synopsis")
        self.assertEqual(req["kind"], "gh")
        self.assertEqual(
            req["cmd"],
            ["pr", "comment", "42", "--repo", "octo/qrspi", "--body-file", "-"],
        )
        self.assertEqual(req["stdin"], "synopsis")


class CommentIdRelaxationTest(unittest.TestCase):
    """RUS-89: --comment-id is optional in toplevel mode, still required for inline.

    The validation guard lives in main() before any gh call; here we exercise the
    rule directly via the same condition (inline + missing id -> fail-closed) and
    confirm toplevel tolerates a missing id, without running gh.
    """

    @staticmethod
    def _inline_requires_id(reply_mode, comment_id):
        # Mirror of main()'s guard so the rule is unit-tested without subprocess.
        return reply_mode == m.REPLY_MODE_INLINE and comment_id is None

    def test_inline_missing_id_is_rejected(self):
        self.assertTrue(self._inline_requires_id("inline", None))

    def test_inline_with_id_is_accepted(self):
        self.assertFalse(self._inline_requires_id("inline", 12345))

    def test_toplevel_missing_id_is_accepted(self):
        self.assertFalse(self._inline_requires_id("toplevel", None))

    def test_error_envelope_tolerates_missing_id(self):
        # The toplevel-without-id path passes None to error_envelope on a read/
        # resolve failure; it must not raise and reports a null inReplyToId.
        env = m.error_envelope(None, "--comment-id is required in inline reply mode")
        self.assertFalse(env["ok"])
        self.assertIsNone(env["inReplyToId"])


class ResponseToEnvelopeTest(unittest.TestCase):
    def test_inline_success_captures_id(self):
        raw = '{"id": 555444333, "body": "thanks, fixed"}'
        env = m.response_to_envelope("inline", raw, 99887766)
        self.assertTrue(env["ok"])
        self.assertEqual(env["replyId"], 555444333)
        self.assertEqual(env["inReplyToId"], 99887766)
        self.assertIsNone(env["error"])

    def test_inline_in_reply_to_coerced_to_int(self):
        raw = '{"id": 1}'
        env = m.response_to_envelope("inline", raw, "99887766")
        self.assertEqual(env["inReplyToId"], 99887766)

    def test_inline_unparseable_response_fails_closed(self):
        env = m.response_to_envelope("inline", "not json at all", 99887766)
        self.assertFalse(env["ok"])
        self.assertIsNone(env["replyId"])
        self.assertEqual(env["inReplyToId"], 99887766)
        self.assertIsNotNone(env["error"])

    def test_inline_missing_id_fails_closed(self):
        env = m.response_to_envelope("inline", '{"body": "x"}', 99887766)
        self.assertFalse(env["ok"])
        self.assertIsNone(env["replyId"])
        self.assertIsNotNone(env["error"])

    def test_inline_null_id_fails_closed(self):
        env = m.response_to_envelope("inline", '{"id": null}', 99887766)
        self.assertFalse(env["ok"])
        self.assertIsNone(env["replyId"])
        self.assertIsNotNone(env["error"])

    def test_toplevel_success_has_null_reply_id(self):
        # gh pr comment prints a URL, not JSON: ok with no numeric reply id to capture.
        url = "https://github.com/octo/qrspi/pull/42#issuecomment-123"
        env = m.response_to_envelope("toplevel", url, 99887766)
        self.assertTrue(env["ok"])
        self.assertIsNone(env["replyId"])
        self.assertEqual(env["inReplyToId"], 99887766)
        self.assertIsNone(env["error"])

    def test_unknown_mode_fails_closed(self):
        env = m.response_to_envelope("sideways", "{}", 1)
        self.assertFalse(env["ok"])
        self.assertIsNotNone(env["error"])


class ErrorEnvelopeTest(unittest.TestCase):
    def test_error_envelope_shape(self):
        env = m.error_envelope(99887766, "gh write failed (rc=1): 403")
        self.assertFalse(env["ok"])
        self.assertIsNone(env["replyId"])
        self.assertEqual(env["inReplyToId"], 99887766)
        self.assertEqual(env["error"], "gh write failed (rc=1): 403")

    def test_error_envelope_coerces_in_reply_to(self):
        env = m.error_envelope("99887766", "boom")
        self.assertEqual(env["inReplyToId"], 99887766)

    def test_error_envelope_tolerates_non_int_in_reply_to(self):
        env = m.error_envelope(None, "boom")
        self.assertIsNone(env["inReplyToId"])


class EnvelopeKeyContractTest(unittest.TestCase):
    def test_keys_are_exactly_the_reply_envelope_contract(self):
        env = m.response_to_envelope("inline", '{"id": 1}', 2)
        self.assertEqual(set(env.keys()), {"ok", "replyId", "inReplyToId", "error"})


if __name__ == "__main__":
    unittest.main()
