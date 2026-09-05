from __future__ import annotations

from app.lists.match import ListHit
from app.pipeline.engine import CallContext, PolicyView, decide, heuristic_score


def _ctx(**kwargs) -> CallContext:
    base = dict(
        from_e164="+15551230000",
        to_e164="+15550001111",
        call_sid="CA1",
        is_anonymous=False,
        is_contact=False,
        allow_hit=None,
        deny_hit=None,
        policy=PolicyView(),
        trial=True,
        ai_available=False,
        heuristic_score=0.2,
        stage="inbound",
    )
    base.update(kwargs)
    return CallContext(**base)


def test_denylist_wins():
    d = decide(
        _ctx(deny_hit=ListHit("deny", "exact", "+15551230000"), heuristic_score=0.1)
    )
    assert d.action in {"reject_silent", "reject_polite"}
    assert "denylist" in d.reason


def test_allowlist_skips_challenge():
    d = decide(_ctx(allow_hit=ListHit("allow", "exact", "+15551230000"), trial=True))
    assert d.action == "accept"
    assert d.needs_gather is False


def test_allowlist_forwards_when_upgraded():
    d = decide(
        _ctx(
            allow_hit=ListHit("allow", "exact", "+15551230000"),
            trial=False,
            policy=PolicyView(forward_e164=["+15559990000"]),
        )
    )
    assert d.action == "forward"


def test_balanced_unknown_challenges():
    d = decide(_ctx(is_contact=False, heuristic_score=0.4, policy=PolicyView(mode="balanced")))
    assert d.action == "challenge"
    assert d.needs_gather


def test_strict_anonymous_rejects():
    d = decide(_ctx(is_anonymous=True, heuristic_score=0.5, policy=PolicyView(mode="strict")))
    assert d.action in {"reject_silent", "reject_polite"}


def test_permissive_low_score_accepts():
    d = decide(_ctx(heuristic_score=0.1, policy=PolicyView(mode="permissive")))
    assert d.action in {"accept", "forward", "voicemail"}


def test_gather_wrong_digit_rejects():
    d = decide(_ctx(stage="gather", gather_digits="9"))
    assert d.action in {"reject_silent", "reject_polite"}


def test_gather_one_accepts_on_trial():
    d = decide(_ctx(stage="gather", gather_digits="1", trial=True))
    assert d.action == "accept"


def test_contact_no_challenge():
    d = decide(_ctx(is_contact=True, heuristic_score=0.0))
    assert d.needs_gather is False
    assert d.action in {"accept", "forward"}


def test_heuristic_bounds():
    assert 0 <= heuristic_score(is_anonymous=True, is_contact=False, recent_short_repeats=3) <= 1
    assert heuristic_score(is_anonymous=False, is_contact=True) < 0.3


def test_trial_cannot_voicemail():
    d = decide(
        _ctx(
            stage="gather",
            gather_digits="1",
            trial=True,
            policy=PolicyView(record_voicemail=True, recording_legal_ack=True, forward_e164=[]),
        )
    )
    assert d.action != "voicemail"


def test_upgraded_voicemail():
    d = decide(
        _ctx(
            stage="gather",
            gather_digits="1",
            trial=False,
            policy=PolicyView(record_voicemail=True, recording_legal_ack=True, forward_e164=[]),
        )
    )
    assert d.action == "voicemail"
    assert d.can_voicemail
