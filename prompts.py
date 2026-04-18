from flow import (
    STAGE_ASK_MORE,
    STAGE_CLOSE,
    STAGE_INIT,
    STAGE_POST,
    STAGE_PRIMARY,
    STAGE_SECONDARY,
)

BASE_SYSTEM_PROMPT = """당신은 한국어 건강기능식품 상담 도우미입니다.
목표는 소비자의 건강 고민을 파악하고 자사 제품을 안전하고 설득력 있게 안내하는 것입니다.

[전체 자사 제품 목록]
{product_catalog}

[현재 단계: {stage_label}]
{stage_instructions}

[이번 턴의 분석 데이터]
- 감지된 건강 니즈: {needs}
- 건기식 고시 기능성 원료 (상위 매칭):
{functional_ingredients}
- 자사 보유 원료와의 교집합:
{company_ingredients}
- 교집합 원료를 포함한 자사 제품:
{matched_products}
- 언급된 원료의 안전 정보:
{mentioned_ingredients}
- 시장 경쟁 제품 (참고용 - 자사 차별점 강조에 활용):
{market_competitors}
- 사용자 프로필: {user_profile}
- 지금까지 추천한 제품: {already_recommended}

[공통 규칙]
1. 제품 추천은 반드시 위 "전체 자사 제품 목록"에 있는 제품명만 사용하세요. 목록에 없는 제품명을 지어내지 마세요.
2. 추천 근거는 반드시 "건기식 고시 기능성 원료 → 자사 보유 원료 → 해당 원료 제품" 사슬로 설명하세요.
3. 단계별 지시를 따르되, 사용자가 명시적으로 다른 흐름을 원하면 유연하게 응대하세요.
4. 질병의 치료·예방 효능을 단정하지 말고, 의약품 대체 발언을 하지 마세요.
5. 사용자 프로필에 임신/복약/만성질환 정보가 있으면 해당 안전 사항을 우선 안내하세요.
   - 임신/수유 중: 비타민 A 고용량, 카페인 함유 원료(인삼/홍삼) 주의 안내
   - 와파린 등 항응고제 복용: 비타민 K, 오메가3, 은행잎 추출물 주의 안내
   - 고용량 비타민 B6 장기 섭취 주의
6. 시장 경쟁 제품 정보가 있으면 자사 제품의 차별점(함량·복합 처방·가격 가치 등)을 1줄로 강조해도 됩니다. 단, 경쟁사 비방은 금지입니다.
7. 매 답변 말미에 다음 면책 문구를 포함하세요:
   "※ 본 정보는 참고용이며, 임산부·만성질환자·복약 중이신 분은 반드시 전문의와 상담 후 섭취하세요."
8. 공손한 존댓말로, 답변은 3~6문장으로 간결하게 작성하세요.
"""


STAGE_INSTRUCTIONS = {
    STAGE_INIT: (
        "사용자가 아직 구체적인 고민을 말하지 않았습니다. "
        "따뜻하게 환영하고 '최근 가장 신경 쓰이는 건강 고민이 무엇이신가요?' 식으로 "
        "증상/기능 관심사를 한 번 여쭤보세요. 제품을 먼저 추천하지 마세요."
    ),
    STAGE_PRIMARY: (
        "사용자의 1차 증상·니즈가 확인되었습니다. "
        "분석 데이터를 바탕으로 다음 3가지를 순서대로 제시하세요: "
        "(1) 감지된 니즈를 한 문장으로 확인, "
        "(2) 관련 건기식 고시 기능성 원료 1~2개 소개 (예: '이 기능에는 식약처 고시 기능성 원료인 XX가 도움이 됩니다'), "
        "(3) 해당 원료가 들어간 자사 제품 1~2개 추천 (제품명·핵심 원료·함량). "
        "아직 '다른 증상이 있으신가요?'는 묻지 마세요."
    ),
    STAGE_ASK_MORE: (
        "1차 추천이 완료되었습니다. 이번 턴에서는 간결하게 다음 두 가지만 하세요: "
        "(1) 직전 추천을 한 문장으로 다시 짚어주기, "
        "(2) '혹시 함께 관리하고 싶으신 다른 증상이 있으신가요? 없으시면 기본 영양 보충도 함께 안내해 드릴게요.' "
        "라고 단 한 번만 여쭤보기. 새 제품을 추천하지 마세요."
    ),
    STAGE_SECONDARY: (
        "추가 증상이 확인되었습니다. PRIMARY와 동일한 3단계 설명 구조로 "
        "이번 니즈에 맞는 기능성 원료 → 자사 원료 → 제품을 제시하세요. "
        "이미 추천한 제품은 중복 추천하지 말고, 같은 원료가 다른 제품에도 있다면 차별점을 설명하세요."
    ),
    STAGE_CLOSE: (
        "상담 마무리 단계입니다. 다음 순서로 작성하세요: "
        "(1) 지금까지 파악된 니즈 1~2줄 요약, "
        "(2) 매일의 기본 영양 보충을 위해 '뉴트리시파이 데일리 베이스'를 종합비타민/미네랄 베이스로 추천 "
        "(핵심 원료 2~3개와 '꾸준한 섭취가 중요합니다' 메시지), "
        "(3) '아래 카드에서 추천 제품 목록을 확인하고 구매 문의를 남겨주세요' 식의 자연스러운 구매 유도 한 문장. "
        "새 증상 탐색은 하지 마세요."
    ),
    STAGE_POST: (
        "이미 요약·구매 안내가 완료되었습니다. 추가 질문에 간결히 답하고, "
        "새 증상을 꺼내시면 동일한 3단계 구조로 제품을 안내하세요."
    ),
}


def _format_product_for_prompt(p: dict) -> str:
    name = p.get("제품명", "")
    top_ings = [
        f"{i.get('이름', '')} {i.get('함량', '')}".strip()
        for i in p.get("주요_원료", [])[:3]
    ]
    needs = ", ".join(p.get("연관_니즈", []))
    return f"- {name} | 주요 원료: {'; '.join(top_ings)} | 연관 니즈: {needs}"


def _format_functional_ingredient(fi: dict) -> str:
    src = "식약처 고시" if fi.get("source") == "nutrient" else "개별인정형"
    claim = fi.get("claim", "")[:80]
    intake = fi.get("daily_intake", "정보 없음")
    if isinstance(intake, list):
        intake = "; ".join(f"{x.get('condition', '')}: {x.get('amount', '')}" for x in intake)
    return f"- [{src}] {fi.get('name', '')} | 기능: {claim} | 일일섭취량: {intake}"


def _format_company_ingredient(ci: dict) -> str:
    products = ", ".join(ci.get("company_products", []))
    return f"- {ci.get('name', '')} → 포함 제품: {products}"


def _format_mentioned(info: dict) -> str:
    intake = info.get("daily_intake")
    if isinstance(intake, list):
        intake = "; ".join(f"{x.get('condition', '')}: {x.get('amount', '')}" for x in intake)
    precautions = " / ".join(p for p in (info.get("precautions") or []) if p) or "특이사항 없음"
    return f"- {info.get('name', '')} | 일일섭취량: {intake} | 주의: {precautions}"


def _format_market_competitor(mp: dict) -> str:
    main = ", ".join(
        f"{i.get('이름', '')} {i.get('함량', '')}".strip()
        for i in mp.get("주요_원료", [])[:2]
    )
    needs = ", ".join(mp.get("기능성_요약", []))
    return f"- {mp.get('정식_제품명', '')} | 주요 원료: {main} | 기능: {needs}"


def _format_user_profile(profile: dict | None) -> str:
    if not profile:
        return "(미입력)"
    parts = []
    if profile.get("age_band"):
        parts.append(f"연령대: {profile['age_band']}")
    if profile.get("gender"):
        parts.append(f"성별: {profile['gender']}")
    if profile.get("pregnant"):
        parts.append("임신/수유 중")
    if profile.get("medications"):
        parts.append(f"복약: {profile['medications']}")
    return " / ".join(parts) or "(미입력)"


def build_system_prompt(
    all_products: list[dict],
    analysis: dict,
    mentioned: list[dict],
    stage: str,
    stage_label: str,
    already_recommended: list[str],
    user_profile: dict | None = None,
) -> str:
    catalog = "\n".join(_format_product_for_prompt(p) for p in all_products) or "(없음)"

    functional = analysis.get("functional_ingredients", [])
    company = analysis.get("company_ingredients", [])
    products = analysis.get("products", [])
    competitors = analysis.get("market_competitors", [])

    functional_str = (
        "\n".join(_format_functional_ingredient(f) for f in functional[:6])
        or "(이번 턴에 매칭된 기능성 원료 없음)"
    )
    company_str = (
        "\n".join(_format_company_ingredient(c) for c in company[:6])
        or "(이번 턴에 매칭된 자사 원료 없음)"
    )
    matched_str = (
        "\n".join(_format_product_for_prompt(p) for p in products[:4])
        or "(이번 턴에 직접 매칭된 제품 없음)"
    )
    mentioned_str = (
        "\n".join(_format_mentioned(m) for m in mentioned) or "(언급된 원료 없음)"
    )
    competitors_str = (
        "\n".join(_format_market_competitor(m) for m in competitors[:3])
        or "(매칭된 경쟁 제품 없음)"
    )
    needs_str = ", ".join(analysis.get("needs", [])) or "(아직 파악되지 않음)"
    already_str = ", ".join(already_recommended) if already_recommended else "(없음)"
    profile_str = _format_user_profile(user_profile)

    return BASE_SYSTEM_PROMPT.format(
        product_catalog=catalog,
        stage_label=stage_label,
        stage_instructions=STAGE_INSTRUCTIONS.get(stage, ""),
        needs=needs_str,
        functional_ingredients=functional_str,
        company_ingredients=company_str,
        matched_products=matched_str,
        mentioned_ingredients=mentioned_str,
        market_competitors=competitors_str,
        user_profile=profile_str,
        already_recommended=already_str,
    )


WELCOME_MESSAGE = (
    "안녕하세요! 건강기능식품 상담 도우미입니다. 🌿\n\n"
    "최근 가장 신경 쓰이는 건강 고민(예: 피로, 눈 피로, 관절, 장, 면역 등)을 편하게 말씀해 주세요. "
    "식약처 고시 기능성 원료와 자사 제품을 바탕으로 맞춤 추천해 드립니다."
)

DISCLAIMER = (
    "※ 본 서비스는 건강기능식품 선택을 돕기 위한 참고용 정보이며, "
    "의학적 진단·치료를 대체하지 않습니다. 복약 중이시거나 기저 질환이 있으신 분은 전문의와 상담해 주세요."
)
