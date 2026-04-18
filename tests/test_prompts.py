from data import load_products, recommend_for_need
from prompts import build_system_prompt


def _build(stage="PRIMARY", profile=None, recommended=None):
    products = load_products()
    analysis = recommend_for_need("피로해요", products)
    return build_system_prompt(
        all_products=products,
        analysis=analysis,
        mentioned=[],
        stage=stage,
        stage_label="1차 상담",
        already_recommended=recommended or [],
        user_profile=profile,
    )


def test_prompt_contains_full_catalog():
    sp = _build()
    products = load_products()
    for p in products:
        assert p["제품명"] in sp


def test_prompt_includes_disclaimer_rule():
    sp = _build()
    assert "전문의와 상담" in sp


def test_prompt_includes_chain_rule():
    sp = _build()
    assert "건기식 고시 기능성 원료" in sp
    assert "자사 보유 원료" in sp


def test_prompt_renders_user_profile():
    sp = _build(profile={"age_band": "40대", "pregnant": True})
    assert "40대" in sp or "임신" in sp


def test_prompt_renders_already_recommended():
    sp = _build(recommended=["뉴트리시파이 에너지 부스트업"])
    assert "에너지 부스트업" in sp


def test_prompt_close_stage_mentions_base_product():
    sp = _build(stage="CLOSE")
    assert "데일리 베이스" in sp
