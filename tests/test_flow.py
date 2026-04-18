from flow import (
    STAGE_ASK_MORE,
    STAGE_CLOSE,
    STAGE_INIT,
    STAGE_POST,
    STAGE_PRIMARY,
    STAGE_SECONDARY,
    FlowState,
    advance_after_reply,
    next_stage,
)


def test_init_to_primary_when_need_appears():
    assert (
        next_stage(STAGE_INIT, "피로해요", ["피로 개선"], has_new_need=True)
        == STAGE_PRIMARY
    )


def test_init_stays_when_no_need():
    assert next_stage(STAGE_INIT, "안녕하세요", [], has_new_need=False) == STAGE_INIT


def test_ask_more_to_secondary_on_new_need():
    assert (
        next_stage(STAGE_ASK_MORE, "눈도 침침해요", ["눈 건강"], has_new_need=True)
        == STAGE_SECONDARY
    )


def test_ask_more_to_close_on_negative():
    assert (
        next_stage(STAGE_ASK_MORE, "없어요 충분해요", [], has_new_need=False)
        == STAGE_CLOSE
    )


def test_ask_more_to_close_on_alt_negative():
    assert (
        next_stage(STAGE_ASK_MORE, "괜찮아요", [], has_new_need=False)
        == STAGE_CLOSE
    )


def test_ask_more_holds_on_unclear():
    assert (
        next_stage(STAGE_ASK_MORE, "음...", [], has_new_need=False)
        == STAGE_ASK_MORE
    )


def test_close_to_post_on_any_input():
    assert (
        next_stage(STAGE_CLOSE, "더 궁금한 게 있어요", [], has_new_need=False)
        == STAGE_POST
    )


def test_advance_after_reply_promotes_terminal_turns():
    assert advance_after_reply(STAGE_PRIMARY) == STAGE_ASK_MORE
    assert advance_after_reply(STAGE_SECONDARY) == STAGE_CLOSE
    assert advance_after_reply(STAGE_INIT) == STAGE_INIT
    assert advance_after_reply(STAGE_CLOSE) == STAGE_CLOSE


def test_flow_state_defaults():
    s = FlowState()
    assert s.stage == STAGE_INIT
    assert s.identified_needs == []
    assert s.recommended_products == []
    assert s.asked_additional is False


def test_full_happy_path_transitions():
    """Walk through a realistic INIT → CLOSE conversation."""
    s = FlowState()
    s.stage = next_stage(s.stage, "피로해요", ["피로 개선"], True)
    assert s.stage == STAGE_PRIMARY
    s.stage = advance_after_reply(s.stage)
    assert s.stage == STAGE_ASK_MORE
    s.stage = next_stage(s.stage, "눈도", ["눈 건강"], True)
    assert s.stage == STAGE_SECONDARY
    s.stage = advance_after_reply(s.stage)
    assert s.stage == STAGE_CLOSE
    s.stage = next_stage(s.stage, "고마워요", [], False)
    assert s.stage == STAGE_POST
