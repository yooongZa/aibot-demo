import uuid

import chainlit as cl
from chainlit.input_widget import Select, Switch, TextInput

from config import AUTH_ENABLED, MAX_INPUT_CHARS, api_key_available, parse_auth_users
from data import (
    BASE_PRODUCT_NAME,
    find_mentioned_ingredients,
    get_base_product,
    load_products,
    recommend_for_need,
)
from db import init_db, log_feedback, log_session_start, log_turn
from flow import (
    STAGE_ASK_MORE,
    STAGE_CLOSE,
    STAGE_LABELS,
    STAGE_POST,
    STAGE_PRIMARY,
    STAGE_SECONDARY,
    FlowState,
    advance_after_reply,
    next_stage,
)
from llm import astream_reply
from prompts import WELCOME_MESSAGE, build_system_prompt

init_db()


if AUTH_ENABLED:
    @cl.password_auth_callback
    def auth_callback(username: str, password: str) -> cl.User | None:
        users = parse_auth_users()
        expected = users.get(username)
        if expected and expected == password:
            return cl.User(identifier=username, metadata={"role": "user"})
        return None

PURCHASE_URL = "mailto:sales@example.com?subject=뉴트리시파이 제품 구매 문의"
CATALOG_URL = "https://example.com/products"

QUICK_START_NEEDS = [
    ("피로", "요즘 피로가 너무 심해요"),
    ("눈", "눈이 뻑뻑하고 침침해요"),
    ("관절", "관절이 좋지 않아요"),
    ("장", "장 건강이 걱정돼요"),
    ("면역", "면역력이 약해진 것 같아요"),
]


def _get_flow() -> FlowState:
    flow = cl.user_session.get("flow")
    if flow is None:
        flow = FlowState()
        cl.user_session.set("flow", flow)
    return flow


def _get_history() -> list[dict]:
    history = cl.user_session.get("history")
    if history is None:
        history = []
        cl.user_session.set("history", history)
    return history


def _get_feedback() -> list[dict]:
    fb = cl.user_session.get("feedback")
    if fb is None:
        fb = []
        cl.user_session.set("feedback", fb)
    return fb


def _get_purchase_cart() -> list[str]:
    cart = cl.user_session.get("purchase_cart")
    if cart is None:
        cart = []
        cl.user_session.set("purchase_cart", cart)
    return cart


def _format_products_table(products: list[dict], title: str = "추천 제품") -> str:
    """Render a list of products as a single markdown comparison table."""
    if not products:
        return ""
    lines = [f"##### 📋 {title}", ""]
    lines.append("| 제품명 | 주요 원료 | 연관 니즈 |")
    lines.append("|---|---|---|")
    for p in products:
        name = f"**{p.get('제품명', '')}**"
        ings = "<br>".join(
            f"{i.get('이름', '')} · {i.get('함량', '')}".strip()
            for i in p.get("주요_원료", [])[:4]
        )
        needs = " · ".join(f"#{n}" for n in p.get("연관_니즈", []))
        lines.append(f"| {name} | {ings} | {needs} |")
    return "\n".join(lines)


def _format_base_product_table(base: dict) -> str:
    """Detailed table view for the base product shown in the CLOSE stage."""
    if not base:
        return ""
    lines = [
        f"##### 🌿 매일의 기본 영양 — {base.get('제품명', '')}",
        "",
        "| 항목 | 내용 |",
        "|---|---|",
        f"| **제품명** | {base.get('제품명', '')} |",
    ]
    ings = base.get("주요_원료", [])
    if ings:
        ing_text = "<br>".join(
            f"• {i.get('이름', '')} · {i.get('함량', '')}" for i in ings[:10]
        )
        lines.append(f"| **주요 원료** | {ing_text} |")
    needs = base.get("연관_니즈", [])
    if needs:
        lines.append(f"| **연관 니즈** | {' · '.join(needs)} |")
    lines.append("| **권장** | 종합 비타민·미네랄 베이스로 매일 꾸준히 섭취 |")
    return "\n".join(lines)


def _format_final_summary(cart: list[str], products: list[dict]) -> str:
    """Final purchase summary table after the user finalizes selections."""
    by_name = {p["제품명"]: p for p in products}
    lines = [
        "#### 🎉 구매 내역 정리",
        "",
        "지금까지 선택해 주신 제품 목록입니다. 아래 링크에서 바로 구매를 진행하실 수 있어요.",
        "",
        "| 제품명 | 주요 원료 |",
        "|---|---|",
    ]
    if cart:
        for name in cart:
            p = by_name.get(name)
            ings = (
                ", ".join(i.get("이름", "") for i in p.get("주요_원료", [])[:3])
                if p
                else "—"
            )
            lines.append(f"| **{name}** | {ings} |")
    else:
        lines.append("| _선택된 제품이 없습니다._ | — |")

    lines.extend(
        [
            "",
            f"👉 **[구매 페이지로 이동]({CATALOG_URL})**",
            f"📩 [이메일로 구매 문의 보내기]({PURCHASE_URL})",
        ]
    )
    return "\n".join(lines)


def _quick_start_actions() -> list[cl.Action]:
    return [
        cl.Action(
            name="quick_start",
            label=f"#{label}",
            payload={"text": seed},
        )
        for label, seed in QUICK_START_NEEDS
    ]


def _recommendation_actions(product_names: list[str]) -> list[cl.Action]:
    """Three action buttons shown beneath every product recommendation table."""
    return [
        cl.Action(
            name="buy_products",
            label="🛒 구입",
            payload={"products": product_names},
        ),
        cl.Action(
            name="view_other_products",
            label="🔄 다른 제품 확인",
            payload={"products": product_names},
        ),
        cl.Action(
            name="free_inquiry",
            label="💬 자유 입력 (추가 문의)",
            payload={},
        ),
    ]


def _final_actions() -> list[cl.Action]:
    return [
        cl.Action(
            name="open_catalog",
            label="🛍 구매 페이지 열기",
            payload={"url": CATALOG_URL},
        ),
        cl.Action(
            name="purchase_inquiry",
            label="📩 구매 문의 이메일",
            payload={"url": PURCHASE_URL},
        ),
        cl.Action(
            name="escalate_human",
            label="🧑‍⚕️ 전문 상담사 연결",
            payload={},
        ),
        cl.Action(
            name="reset_chat",
            label="🔄 새 상담 시작",
            payload={},
        ),
    ]


async def _send_stage_step(flow: FlowState) -> None:
    label = STAGE_LABELS.get(flow.stage, flow.stage)
    detail_lines = [f"- **진행 단계**: {label}"]
    if flow.identified_needs:
        detail_lines.append("- **파악된 니즈**: " + ", ".join(flow.identified_needs))
    if flow.recommended_products:
        detail_lines.append(
            "- **추천 이력**: " + ", ".join(flow.recommended_products)
        )
    cart = _get_purchase_cart()
    if cart:
        detail_lines.append("- **구매 카트**: " + ", ".join(cart))
    profile = cl.user_session.get("user_profile")
    if profile:
        detail_lines.append("- **프로필**: " + str(profile))
    async with cl.Step(name="상담 상태", type="tool") as step:
        step.output = "\n".join(detail_lines)


async def _setup_chat_settings() -> None:
    await cl.ChatSettings(
        [
            Select(
                id="age_band",
                label="연령대",
                values=["선택안함", "10대", "20대", "30대", "40대", "50대", "60대 이상"],
                initial_index=0,
            ),
            Select(
                id="gender",
                label="성별",
                values=["선택안함", "여성", "남성"],
                initial_index=0,
            ),
            Switch(
                id="pregnant",
                label="임신/수유 중",
                initial=False,
            ),
            TextInput(
                id="medications",
                label="복용 중인 약 (있으면 적어주세요)",
                initial="",
            ),
        ]
    ).send()


@cl.on_settings_update
async def on_settings_update(settings: dict) -> None:
    profile = {
        "age_band": settings.get("age_band") if settings.get("age_band") != "선택안함" else None,
        "gender": settings.get("gender") if settings.get("gender") != "선택안함" else None,
        "pregnant": bool(settings.get("pregnant")),
        "medications": (settings.get("medications") or "").strip() or None,
    }
    profile = {k: v for k, v in profile.items() if v}
    cl.user_session.set("user_profile", profile or None)
    session_id = cl.user_session.get("session_id")
    if session_id:
        log_session_start(session_id, profile)
    if profile:
        readable = ", ".join(f"{k}={v}" for k, v in profile.items())
        await cl.Message(content=f"✅ 프로필이 업데이트되었습니다: _{readable}_").send()


@cl.on_chat_start
async def on_chat_start() -> None:
    if not api_key_available():
        await cl.ErrorMessage(
            content=(
                "`GOOGLE_API_KEY`가 설정되지 않았습니다.\n\n"
                "프로젝트 루트의 `.env` 파일에 `GOOGLE_API_KEY=<Gemini API 키>` 를 추가한 뒤 "
                "`chainlit run app.py -w` 로 다시 실행해 주세요."
            )
        ).send()
        return

    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("flow", FlowState())
    cl.user_session.set("history", [])
    cl.user_session.set("feedback", [])
    cl.user_session.set("user_profile", None)
    cl.user_session.set("turn_index", 0)
    cl.user_session.set("purchase_cart", [])
    log_session_start(session_id, None)

    await _setup_chat_settings()
    await cl.Message(
        content=WELCOME_MESSAGE + "\n\n_아래 버튼으로 빠르게 시작하실 수 있어요._",
        actions=_quick_start_actions(),
    ).send()


async def _process_user_turn(user_input: str) -> None:
    user_input = (user_input or "").strip()
    if not user_input:
        return
    if len(user_input) > MAX_INPUT_CHARS:
        await cl.Message(
            content=f"입력이 너무 깁니다. {MAX_INPUT_CHARS}자 이내로 작성해 주세요."
        ).send()
        return

    flow = _get_flow()
    history = _get_history()
    history.append({"role": "user", "content": user_input})

    products = load_products()
    analysis = recommend_for_need(user_input, products, exclude_base=True)
    mentioned = find_mentioned_ingredients(user_input, products)

    new_needs = [n for n in analysis["needs"] if n not in flow.identified_needs]
    has_new_need = bool(new_needs)
    if has_new_need:
        flow.identified_needs.extend(new_needs)

    flow.stage = next_stage(
        current=flow.stage,
        user_text=user_input,
        detected_needs=analysis["needs"],
        has_new_need=has_new_need,
    )

    if flow.stage == STAGE_CLOSE:
        analysis["products"] = []

    system_prompt = build_system_prompt(
        all_products=products,
        analysis=analysis,
        mentioned=mentioned,
        stage=flow.stage,
        stage_label=STAGE_LABELS.get(flow.stage, flow.stage),
        already_recommended=flow.recommended_products,
        user_profile=cl.user_session.get("user_profile"),
    )

    reply_msg = cl.Message(content="")
    await reply_msg.send()

    try:
        async for token in astream_reply(history, system_prompt):
            await reply_msg.stream_token(token)
        await reply_msg.update()

        history.append({"role": "assistant", "content": reply_msg.content})

        if flow.stage in (STAGE_PRIMARY, STAGE_SECONDARY):
            new_cards = [
                p for p in analysis["products"][:3]
                if p["제품명"] not in flow.recommended_products
            ]
            for p in new_cards:
                flow.recommended_products.append(p["제품명"])
            if new_cards:
                title = "1차 추천 제품" if flow.stage == STAGE_PRIMARY else "추가 추천 제품"
                await cl.Message(
                    content=_format_products_table(new_cards, title=title),
                    actions=_recommendation_actions([p["제품명"] for p in new_cards]),
                ).send()

        elif flow.stage == STAGE_CLOSE:
            if BASE_PRODUCT_NAME not in flow.recommended_products:
                flow.recommended_products.append(BASE_PRODUCT_NAME)
            base = get_base_product(products)
            if base:
                await cl.Message(
                    content=_format_base_product_table(base),
                    actions=_recommendation_actions([BASE_PRODUCT_NAME]),
                ).send()

        await _send_stage_step(flow)

        session_id = cl.user_session.get("session_id") or ""
        turn_index = (cl.user_session.get("turn_index") or 0) + 1
        cl.user_session.set("turn_index", turn_index)
        log_turn(
            session_id=session_id,
            turn_index=turn_index,
            stage=flow.stage,
            user_text=user_input,
            assistant_text=reply_msg.content,
            detected_needs=analysis.get("needs", []),
            recommended_products=[p["제품명"] for p in analysis.get("products", [])[:3]],
        )

        flow.stage = advance_after_reply(flow.stage)
        cl.user_session.set("flow", flow)
        cl.user_session.set("history", history)

    except Exception as e:
        reply_msg.content = (
            "일시적으로 응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.\n\n"
            f"`{type(e).__name__}`"
        )
        await reply_msg.update()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    await _process_user_turn(message.content or "")


@cl.action_callback("quick_start")
async def on_quick_start(action: cl.Action) -> None:
    seed = action.payload.get("text", "")
    if not seed:
        return
    await cl.Message(content=seed, author="user").send()
    await _process_user_turn(seed)


@cl.action_callback("buy_products")
async def on_buy_products(action: cl.Action) -> None:
    selected: list[str] = list(action.payload.get("products", []) or [])
    cart = _get_purchase_cart()
    added = [p for p in selected if p not in cart]
    cart.extend(added)
    cl.user_session.set("purchase_cart", cart)

    flow = _get_flow()
    products = load_products()

    # 베이스 제품을 구입하면 상담 종료 → 최종 구매 요약
    if BASE_PRODUCT_NAME in selected or flow.stage == STAGE_POST:
        await cl.Message(
            content=_format_final_summary(cart, products),
            actions=_final_actions(),
        ).send()
        return

    # 그 외에는 다음 니즈를 묻고 SECONDARY 흐름으로 유도
    flow.stage = STAGE_ASK_MORE
    cl.user_session.set("flow", flow)

    msg_lines = []
    if added:
        msg_lines.append(f"🛒 장바구니에 담았어요: **{', '.join(added)}**")
    msg_lines.append("")
    msg_lines.append(
        "혹시 함께 관리하고 싶은 **다른 증상**이 있으신가요? "
        "있다면 편하게 말씀해 주세요. 없으시면 \"없어요\"라고 답해주시면 "
        "기본 영양 보충 제품을 안내해 드릴게요."
    )
    await cl.Message(content="\n".join(msg_lines)).send()


@cl.action_callback("view_other_products")
async def on_view_other_products(action: cl.Action) -> None:
    shown = list(action.payload.get("products", []) or [])
    products = load_products()
    others = [
        p
        for p in products
        if p["제품명"] not in shown and p["제품명"] != BASE_PRODUCT_NAME
    ]
    if not others:
        await cl.Message(
            content=(
                "현재 안내해 드릴 다른 제품이 없습니다. "
                "원하시는 다른 증상이나 원료를 직접 입력해 주세요."
            )
        ).send()
        return

    next_batch = others[:3]
    await cl.Message(
        content=_format_products_table(next_batch, title="다른 추천 제품"),
        actions=_recommendation_actions([p["제품명"] for p in next_batch]),
    ).send()


@cl.action_callback("free_inquiry")
async def on_free_inquiry(action: cl.Action) -> None:
    await cl.Message(
        content=(
            "💬 추가로 궁금하신 점이나 다른 증상을 자유롭게 입력해 주세요.\n"
            "_예: \"임신 중인데 안전한가요?\", \"변비도 같이 있어요\" 등_"
        )
    ).send()


@cl.action_callback("open_catalog")
async def on_open_catalog(action: cl.Action) -> None:
    url = action.payload.get("url", CATALOG_URL)
    await cl.Message(
        content=(
            "🛍 **구매 페이지로 이동하세요!**\n\n"
            f"👉 [{url}]({url})\n\n"
            "장바구니에 담긴 제품을 한 번에 확인하실 수 있습니다."
        )
    ).send()


@cl.action_callback("feedback")
async def on_feedback(action: cl.Action) -> None:
    payload = action.payload or {}
    rating = payload.get("rating", "")
    products = payload.get("products", [])
    turn_id = payload.get("turn_id", "")
    fb = _get_feedback()
    fb.append({"turn_id": turn_id, "rating": rating, "products": products})
    cl.user_session.set("feedback", fb)
    log_feedback(
        session_id=cl.user_session.get("session_id") or "",
        turn_id=turn_id,
        rating=rating,
        products=products,
    )
    label = "👍 좋은 평가" if rating == "up" else "👎 개선 의견"
    await cl.Message(
        content=f"{label} 감사합니다! 의견은 추천 품질 개선에 활용됩니다."
    ).send()


@cl.action_callback("purchase_inquiry")
async def on_purchase_inquiry(action: cl.Action) -> None:
    url = action.payload.get("url", PURCHASE_URL)
    await cl.Message(
        content=(
            "구매 문의를 도와드리겠습니다! 아래 링크로 접수해 주세요.\n\n"
            f"- 📩 이메일 문의: [{url}]({url})\n"
            "- 💬 카카오톡 상담: (채널 연결 예정)\n\n"
            "문의 시 **상담 번호**와 **관심 제품**을 함께 적어주시면 빠르게 안내드릴 수 있어요."
        )
    ).send()


@cl.action_callback("product_details")
async def on_product_details(action: cl.Action) -> None:
    url = action.payload.get("url", CATALOG_URL)
    await cl.Message(
        content=f"제품 카탈로그에서 상세 스펙과 섭취 방법을 확인하실 수 있어요.\n\n👉 [{url}]({url})"
    ).send()


@cl.action_callback("subscribe")
async def on_subscribe(action: cl.Action) -> None:
    await cl.Message(
        content=(
            "🎁 **정기구독 1개월 무료 체험**\n\n"
            "추천드린 제품을 매월 자동으로 받아보실 수 있습니다.\n"
            "- 첫 1개월 무료 (배송비 별도)\n"
            "- 언제든 해지 가능\n"
            "- 정기 구독 시 10% 할인 적용\n\n"
            f"신청은 [구매 문의 링크]({PURCHASE_URL})에서 '정기구독'이라고 적어주세요."
        )
    ).send()


@cl.action_callback("escalate_human")
async def on_escalate_human(action: cl.Action) -> None:
    await cl.Message(
        content=(
            "🧑‍⚕️ **전문 상담사 연결을 안내해 드립니다**\n\n"
            "복약 중이시거나 만성질환이 있으신 경우, 약사·영양사 상담을 권장드립니다.\n\n"
            "- 평일 09:00 ~ 18:00\n"
            f"- 📩 이메일: [상담 신청]({PURCHASE_URL.replace('구매 문의', '전문 상담 요청')})\n"
            "- 📞 전화 상담: 1588-0000 (대표번호)\n\n"
            "신청 시 지금까지의 상담 내역을 함께 전달해 드립니다."
        )
    ).send()


@cl.action_callback("reset_chat")
async def on_reset_chat(action: cl.Action) -> None:
    cl.user_session.set("flow", FlowState())
    cl.user_session.set("history", [])
    cl.user_session.set("feedback", [])
    cl.user_session.set("purchase_cart", [])
    await cl.Message(
        content="새 상담을 시작했습니다. 다시 건강 고민을 말씀해 주세요. 🌿",
        actions=_quick_start_actions(),
    ).send()
