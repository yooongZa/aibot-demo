# 프로젝트 진행 상황

**프로젝트명**: 뉴트리시파이 건강기능식품 맞춤 상담 챗봇 + 데모 랜딩 사이트
**최종 업데이트**: 2026-04-18

## 🎯 목표

식약처 고시 기능성 원료와 자사 제품 데이터를 근거로 한국어 소비자에게 안전하고 설득력 있는 건강기능식품을 추천하는 1:1 챗봇. 제품 상세 페이지 + 구매 CTA 연결.

## 🌐 배포 URL

| 자원 | URL | 상태 |
|---|---|---|
| 공개 랜딩 페이지 | https://yooongza.github.io/aibot-demo/ | ✅ |
| Chainlit 챗봇 | https://yongza-aibot-demo.hf.space | ✅ |
| 원본 리포 (private) | https://github.com/yooongZa/aibot | 🔒 |
| 공개 리포 (public) | https://github.com/yooongZa/aibot-demo | ✅ |
| HF Space | https://huggingface.co/spaces/YongZa/aibot-demo | ✅ |

## 🏗 아키텍처

```
[브라우저]
    │
    ├── GitHub Pages (정적 랜딩)   — web/index.html, about, demo, products
    │       └── copilot.js 가 아래로 연결
    │
    └── HF Spaces (Docker)         — Chainlit + Gemini 2.5 Flash
            └── app.py / data.py / flow.py / prompts.py / db.py / llm.py / embeddings.py
                        ↓
                [Gemini API] (사용자 Secret)
```

## 🧠 핵심 로직

1. **소비자 니즈 파악** — 자유 입력을 NEED_KEYWORDS로 키워드 매칭, 절(clause) 단위 부정어 처리
2. **건기식 고시 기능성 원료 매칭** — 일반 영양소 26종 + 개별인정형 원료 200+ 검색
3. **자사 보유 원료 매칭** — Products.json 주요_원료와 교집합
4. **해당 원료 제품 추천** — 연관_니즈 재랭킹 + 다양성 제약
5. **시장 경쟁 제품 참조** — Market_Products.json으로 차별점 프롬프트에 주입
6. **베이스 제품 추천** — CLOSE 단계에서 뉴트리시파이 데일리 베이스 고정

## 🎭 상담 퍼널 (6단계 하이브리드 상태머신)

```
INIT → PRIMARY → ASK_MORE → SECONDARY → CLOSE → POST
(환영)  (1차추천)  (추가확인)  (2차추천)   (베이스 표+구매) (후속Q&A)
```

각 단계별로 프롬프트 지시 내용이 다름. 전이는 규칙 기반 (`flow.py:next_stage`).

## ✅ 구현된 기능

### 추천 품질
- 이해 가능한 원료 사슬 제시 ("식약처 고시 원료 → 자사 원료 → 제품")
- 문장 단위 부정어 처리 (`피로는 괜찮은데 눈이...` → 눈 건강만)
- 증상 시그널 오버라이드 (`관절이 안 좋아요` → 부정 아님, 증상 인식)
- 다양성 제약 (같은 1차 니즈 제품 중복 추천 방지)
- 시장 경쟁 제품 참조 (락토핏 등)

### UX
- 빠른 시작 버튼 5개 (#피로 / #눈 / #관절 / #장 / #면역)
- 제품 추천을 마크다운 **표**로 노출 (PRIMARY / SECONDARY / CLOSE 베이스 제품)
- 추천마다 🛒 구입 · 🔄 다른 제품 확인 · 💬 자유 입력 **3-버튼** 액션
- 세션 **구매 카트**: 구입 버튼 → 카트 누적 → 베이스 제품 구매 시 최종 요약 표 + 구매 페이지/문의 링크
- 피드백 👍/👎 버튼 (SQLite 로깅, 호환 유지)
- 사용자 프로필 입력 (연령·성별·임신·복약) → 안전 가이드 프롬프트 주입
- 단계·니즈·추천 이력·구매 카트 접이식 Step 패널

### 안전성
- 임신·복약(와파린) 기반 원료 금기 안내
- 고용량 비타민 A·B6 장기섭취 주의
- 의약품 대체 발언 금지 프롬프트 규칙
- 면책 문구 매 답변 말미 포함

### 운영
- SQLite 로깅 (sessions / turns / feedback 3테이블)
- 옵션형 password 인증 (`AUTH_ENABLED=1`)
- Docker + HF Spaces 배포
- **main push → HF Space 자동 동기화** (`.github/workflows/hf-sync.yml`, HF_TOKEN secret 필요)
- 36 pytest 테스트 (detect_needs, pipeline, flow, prompts, db)

## 📁 파일 구조

```
aibot-demo/
├── app.py                          Chainlit 핸들러
├── config.py                       환경변수 / 인증 설정
├── data.py                         원료 매칭 파이프라인
├── db.py                           SQLite 로깅
├── embeddings.py                   (선택) 임베딩 매칭 스텁
├── flow.py                         상담 단계 상태머신
├── llm.py                          Gemini 스트리밍 (sync + async)
├── prompts.py                      단계별 시스템 프롬프트
├── serve_web.py                    로컬 개발 정적 서버
├── Products.json                   자사 제품 7종
├── Market_Products.json            시장 경쟁 제품 3종
├── Nutrient ... Data.json          식약처 고시 일반 영양소 26종
├── Individually_Recognized_...json 개별인정형 원료 200+
├── chainlit.md                     Chainlit 환영 페이지
├── .chainlit/config.toml           Chainlit 설정 (allow_origins 등)
├── .github/workflows/pages.yml     GH Pages 자동 배포
├── .github/workflows/hf-sync.yml   main → HF Space 자동 동기화
├── Dockerfile                      HF Spaces 실행 (포트 7860)
├── README.md                       HF Spaces 프론트매터 + 프로젝트 소개
├── web/
│   ├── index.html                  히어로 + 기능 + 퍼널
│   ├── about.html                  기술 스택 · 데이터 출처
│   ├── demo.html                   6가지 테스트 시나리오
│   ├── products.html               제품 카탈로그 (products-data.json 동적 로드)
│   ├── products-data.json          Products.json 스냅샷
│   └── static/styles.css, copilot.js
└── tests/                          pytest 스위트 (36 테스트)
```

## 💰 운영 비용 (Gemini 2.5 Flash)

| 트래픽 | 월 비용 (근사) |
|---|---|
| 일 50명 | ~2만원 |
| 일 500명 | ~20만원 |
| 일 5,000명 | ~200만원 |

무료 티어: 일 1,500 요청 이내. 초기 데모는 무료 범위.

## 🚨 해결한 주요 이슈

1. **GCP 서비스 계정 키 유출** — `.streamlit/secrets.toml`이 git 히스토리에 있던 건 사용자가 GCP 콘솔에서 폐기. 새 public repo (`aibot-demo`)는 클린 히스토리로 별도 생성.
2. **Pages 워크플로 첫 빌드 실패** — Pages 미활성 + feature 브랜치 트리거 → `main` 전용으로 제한, `enablement: true` 추가.
3. **HF Spaces 업로드 실패** — `colorTo: emerald`가 유효하지 않아 `blue`로 변경.
4. **zsh 파싱 에러** — `interactive_comments` off 환경이라 `#` 주석이 에러. `CLAUDE.md`에 "복붙용 셸 스니펫 규칙" 기록.
5. **`NotFound` from Gemini** — `gemini-2.0-flash` 접근 불가 → Space 환경변수 `GEMINI_MODEL=gemini-2.5-flash` 로 변경.
6. **HF Space가 main과 동기화되지 않음** — 초기에는 `git push hf` 수동 푸시만 가능했음. `.github/workflows/hf-sync.yml` 추가해 GitHub Actions에서 자동 푸시하도록 함 (HF_TOKEN secret 필요).

## 🔮 후속 제안

### 즉시 효과적
- **Context Caching** 도입 → 시스템 프롬프트 70% 절감 (토큰 비용 절감)
- `.chainlit/config.toml` `allow_origins` 를 `*` → 실제 랜딩 도메인으로 타이트닝
- CTA 링크 (`mailto:`·`example.com/products`) 실제 URL로 교체

### 품질 향상
- 임베딩 매칭 활성화 (`pip install sentence-transformers` + `EMBEDDING_MODEL` 설정)
- 사용자 피드백 로그 기반 추천 품질 대시보드
- A/B 프롬프트 테스트 (Literal AI 연동)

### 비즈니스
- 실제 자사몰 / 카카오톡 채널 연동 (`INTEGRATIONS.md` 참고)
- 정기구독 주문 시스템 실제 연결
- 상담사 에스컬레이션 Slack 알림 자동화

## 📚 주요 문서

- `README.md` — 프로젝트 소개 + HF Spaces 설정
- `DEPLOY.md` — 공개 URL 배포 경로 (GH Pages / HF Spaces / Render / Cloudflare)
- `INTEGRATIONS.md` — 외부 통합 가이드 (카톡 / Literal AI / 멀티에이전트)
- `CLAUDE.md` — Claude Code 작업 시 프로젝트 선호사항
- `PROGRESS.md` — 이 파일
