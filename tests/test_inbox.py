"""
tests/test_inbox.py — Telegram inbox update parsing. Pure, no network.

Covers the two forward shapes the Bot API uses (forward_origin on current
versions, forward_from on older ones), since forwarding is the whole point: the
API cannot return messages the bot itself sent, so a forward is the only way a
Claude recommendation reaches local storage.
"""

from __future__ import annotations

from paper.inbox import _extract, _slug


def _msg(**over) -> dict:
    m = {"date": 1_780_000_000, "chat": {"id": -100}, "from": {"username": "ronak"},
         "text": "BAND: keep 0.15-0.25"}
    m.update(over)
    return {"update_id": 42, "message": m}


def test_extracts_plain_message():
    r = _extract(_msg())
    assert r["update_id"] == 42
    assert r["sender"] == "ronak"
    assert r["origin"] == ""
    assert r["text"] == "BAND: keep 0.15-0.25"
    assert r["ts"].startswith("20")


def test_extracts_new_style_forward_origin():
    r = _extract(_msg(forward_origin={"type": "user",
                                      "sender_user": {"username": "ClaudeReviewer"}}))
    assert r["origin"] == "ClaudeReviewer"


def test_extracts_legacy_forward_from():
    r = _extract(_msg(forward_from={"first_name": "Claude"}))
    assert r["origin"] == "Claude"


def test_extracts_channel_forward_title():
    r = _extract(_msg(forward_origin={"type": "chat", "chat": {"title": "Poly Recs"}}))
    assert r["origin"] == "Poly Recs"


def test_caption_counts_as_text():
    m = _msg()
    del m["message"]["text"]
    m["message"]["caption"] = "screenshot of the rec"
    assert _extract(m)["text"] == "screenshot of the rec"


def test_non_text_updates_are_skipped():
    m = _msg()
    del m["message"]["text"]
    assert _extract(m) is None
    assert _extract({"update_id": 1}) is None          # no message at all
    m2 = _msg(text="   ")
    assert _extract(m2) is None                        # whitespace only


def test_channel_post_is_handled():
    r = _extract({"update_id": 7, "channel_post": {
        "date": 1_780_000_000, "chat": {"id": -5}, "text": "posted"}})
    assert r["text"] == "posted" and r["update_id"] == 7


def test_slug_is_filesystem_safe():
    assert _slug("BAND: keep 0.15-0.25!!") == "band-keep-0-15-0-25"
    assert _slug("") == "note"
    assert len(_slug("x" * 200)) <= 40
