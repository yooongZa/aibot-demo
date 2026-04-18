"""Hybrid stage management for the consultation funnel.

The app tracks a coarse stage in session_state. Transitions are rule-based so
the flow is predictable, but the LLM can still decide mid-stage wording.
"""

from dataclasses import dataclass

STAGE_INIT = "INIT"                  # 환영, 첫 증상 묻기
STAGE_PRIMARY = "PRIMARY"            # 1차 증상 추천 진행
STAGE_ASK_MORE = "ASK_MORE"          # "다른 증상?" 1회 확인
STAGE_SECONDARY = "SECONDARY"        # 추가 증상 추천
STAGE_CLOSE = "CLOSE"                # 베이스 + 요약 + 구매 CTA
STAGE_POST = "POST"                  # 구매 후 QA / 재참여

NEGATIVE_TOKENS = ("없어", "없습니다", "없네", "괜찮", "충분", "그만", "됐", "아니")
POSITIVE_TOKENS = ("있어", "있습니다", "네", "응", "예", "맞아")


@dataclass
class FlowState:
    stage: str = STAGE_INIT
    identified_needs: list[str] | None = None
    recommended_products: list[str] | None = None
    asked_additional: bool = False

    def __post_init__(self) -> None:
        if self.identified_needs is None:
            self.identified_needs = []
        if self.recommended_products is None:
            self.recommended_products = []


def _is_negative(text: str) -> bool:
    t = text.strip()
    return any(tok in t for tok in NEGATIVE_TOKENS)


def _is_positive(text: str) -> bool:
    t = text.strip()
    return any(tok in t for tok in POSITIVE_TOKENS)


def next_stage(
    current: str,
    user_text: str,
    detected_needs: list[str],
    has_new_need: bool,
) -> str:
    """Rule-based stage transition after a user message is received.

    - INIT → PRIMARY when user first mentions a need
    - PRIMARY → ASK_MORE after recommendation is delivered (handled in app post-response)
    - ASK_MORE → SECONDARY if user volunteers a new need (positive or explicit need)
    - ASK_MORE → CLOSE if user declines
    - SECONDARY → CLOSE after recommendation delivered
    - CLOSE → POST once the user interacts after the close card
    """
    if current == STAGE_INIT:
        if has_new_need or detected_needs:
            return STAGE_PRIMARY
        return STAGE_INIT

    if current == STAGE_ASK_MORE:
        if has_new_need:
            return STAGE_SECONDARY
        if _is_negative(user_text) and not _is_positive(user_text):
            return STAGE_CLOSE
        if _is_positive(user_text) and not has_new_need:
            return STAGE_ASK_MORE
        return STAGE_ASK_MORE

    if current == STAGE_CLOSE:
        return STAGE_POST

    return current


def advance_after_reply(current: str) -> str:
    """Called after the assistant finishes a turn to move past turn-ending stages."""
    if current == STAGE_PRIMARY:
        return STAGE_ASK_MORE
    if current == STAGE_SECONDARY:
        return STAGE_CLOSE
    return current


STAGE_LABELS = {
    STAGE_INIT: "시작",
    STAGE_PRIMARY: "1차 상담",
    STAGE_ASK_MORE: "추가 증상 확인",
    STAGE_SECONDARY: "2차 상담",
    STAGE_CLOSE: "요약·구매 안내",
    STAGE_POST: "상담 후",
}
