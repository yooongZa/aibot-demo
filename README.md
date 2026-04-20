---
title: Nutrify Consultation Chatbot
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
short_description: 식약처 고시 기능성 원료 기반 건기식 상담 챗봇
---

# 🌿 뉴트리시파이 건강기능식품 상담 챗봇

Chainlit + Gemini 기반 한국어 건강기능식품 맞춤 상담.

- 식약처 고시 기능성 원료 + 개별인정형 원료 데이터 매칭
- "고시 원료 → 자사 보유 원료 → 해당 원료 제품" 사슬로 근거 있는 추천
- 6단계 상담 퍼널 (INIT → PRIMARY → ASK_MORE → SECONDARY → CLOSE → POST)
- 임신/복약 정보 기반 안전성 가드 (비타민 A, 비타민 K+와파린 등)
- 문장 단위 부정어 처리
- SQLite 세션·피드백 로깅

## 실행

### 로컬

`pip install -r requirements.txt` 후 `.env`에 `GOOGLE_API_KEY` 추가하고 `chainlit run app.py -w`

### HF Spaces

Docker SDK로 실행. `GOOGLE_API_KEY`를 Space Settings → Variables and secrets에 등록하세요.

## 면책

본 서비스는 건강기능식품 선택을 돕는 참고용 정보이며 의학적 진단·치료를 대체하지 않습니다. 임산부·만성질환자·복약 중이신 분은 전문의와 상담 후 섭취하세요.
