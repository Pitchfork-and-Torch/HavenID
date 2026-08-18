from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.lists.match import ListHit

Action = Literal[
    "reject_silent",
    "reject_polite",
    "challenge",
    "voicemail",
    "forward",
    "accept",
]

Mode = Literal["strict", "balanced", "permissive"]


@dataclass(frozen=True)
class PolicyView:
    mode: Mode = "balanced"
    challenge_enabled: bool = True
    ai_enabled: bool = False
    record_voicemail: bool = False
    recording_legal_ack: bool = False
    ring_strategy: str = "simultaneous"
    reject_style: str = "polite"
    forward_e164: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CallContext:
    from_e164: str | None
    to_e164: str | None
    call_sid: str
    is_anonymous: bool
    is_contact: bool
    allow_hit: ListHit | None
    deny_hit: ListHit | None
    policy: PolicyView
    trial: bool
    ai_available: bool
    heuristic_score: float
    gather_digits: str | None = None
    challenge_passed: bool = False
    ai_label: str | None = None
    stage: str = "inbound"


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    spam_score: float
    needs_gather: bool = False
    needs_record: bool = False
    can_forward: bool = False
    can_voicemail: bool = False


def heuristic_score(*, is_anonymous: bool, is_contact: bool, recent_short_repeats: int = 0) -> float:
    score = 0.0
    if is_anonymous:
        score += 0.45
    if is_contact:
        score -= 0.35
    score += min(0.4, 0.15 * max(0, recent_short_repeats))
    return max(0.0, min(1.0, score))


def _reject_action(policy: PolicyView) -> Action:
    return "reject_silent" if policy.reject_style == "silent" else "reject_polite"


def decide(ctx: CallContext) -> Decision:
    policy = ctx.policy
    score = ctx.heuristic_score
    if ctx.deny_hit:
        score = max(score, 0.95)
    if ctx.allow_hit or ctx.is_contact:
        score = min(score, 0.2)
    if ctx.ai_label == "spam":
        score = max(score, 0.9)
    if ctx.ai_label == "human":
        score = min(score, 0.25)

    trial = ctx.trial
    can_forward = bool(policy.forward_e164) and not trial
    can_vm = policy.record_voicemail and policy.recording_legal_ack and not trial

    if ctx.deny_hit:
        return Decision(_reject_action(policy), f"denylist:{ctx.deny_hit.pattern}", score)

    if ctx.allow_hit:
        if can_forward:
            return Decision("forward", f"allowlist:{ctx.allow_hit.pattern}", score, can_forward=True)
        return Decision("accept", f"allowlist:{ctx.allow_hit.pattern}", score)

    if ctx.stage == "gather":
        if ctx.gather_digits == "1" or ctx.challenge_passed:
            return _post_challenge(ctx, score, can_forward, can_vm)
        return Decision(_reject_action(policy), "challenge_failed", max(score, 0.7))

    if ctx.stage == "ai":
        if ctx.ai_label == "spam":
            return Decision(_reject_action(policy), "ai_spam", score)
        return _post_challenge(ctx, score, can_forward, can_vm)

    if ctx.is_contact:
        if can_forward:
            return Decision("forward", "known_contact", score, can_forward=True)
        return Decision("accept", "known_contact", score)

    unknown = (not ctx.is_contact) and (not ctx.allow_hit)
    high = score >= 0.7
    mid = score >= 0.35

    if policy.mode == "strict":
        if ctx.is_anonymous or high:
            return Decision(_reject_action(policy), "strict_block", score)
        if unknown and policy.challenge_enabled:
            return Decision("challenge", "strict_unknown", score, needs_gather=True)
        return _terminal(policy, score, can_forward, can_vm, "strict_pass")

    if policy.mode == "permissive":
        if high and policy.challenge_enabled:
            return Decision("challenge", "permissive_high", score, needs_gather=True)
        if high:
            return Decision(_reject_action(policy), "permissive_high_no_challenge", score)
        return _terminal(policy, score, can_forward, can_vm, "permissive_pass")

    # balanced
    if high:
        return Decision(_reject_action(policy), "balanced_high", score)
    if (unknown or mid) and policy.challenge_enabled:
        return Decision("challenge", "balanced_challenge", score, needs_gather=True)
    return _terminal(policy, score, can_forward, can_vm, "balanced_pass")


def _post_challenge(ctx: CallContext, score: float, can_forward: bool, can_vm: bool) -> Decision:
    policy = ctx.policy
    if policy.ai_enabled and ctx.ai_available and ctx.stage != "ai" and not ctx.trial:
        return Decision(
            "challenge",
            "ai_screen",
            score,
            needs_record=True,
            can_forward=can_forward,
            can_voicemail=can_vm,
        )
    return _terminal(policy, score, can_forward, can_vm, "challenge_passed")


def _terminal(policy: PolicyView, score: float, can_forward: bool, can_vm: bool, reason: str) -> Decision:
    if can_forward:
        return Decision("forward", reason, score, can_forward=True)
    if can_vm:
        return Decision("voicemail", reason, score, can_voicemail=True)
    if policy.forward_e164:
        # trial or otherwise cannot dial: accept/log rather than silently drop
        return Decision("accept", f"{reason}_trial_no_dial", score)
    return Decision("accept", reason, score)
