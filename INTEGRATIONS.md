# 외부 통합 가이드

추가 작업 항목 중 외부 서비스 연동·실험적 구조 변경에 해당하는 부분의 진입점과 참고 자료를 모아둡니다.

## #8 임베딩 기반 니즈 매칭

`embeddings.py`에 인터페이스 스텁(`match_need_semantically`)이 있고, 의존성이 없으면 자동으로 키워드 매칭으로 폴백합니다.

활성화 방법:
```bash
pip install sentence-transformers
# .env 에 모델/임계값 설정
echo "EMBEDDING_MODEL=jhgan/ko-sroberta-multitask" >> .env
echo "EMBEDDING_THRESHOLD=0.45" >> .env
```

`app.py`에서 사용하려면:
```python
from embeddings import match_need_semantically
needs = match_need_semantically(user_input)
```
현재는 `data.detect_needs`만 사용 중. 키워드와 임베딩 결과를 합치는 정책(가중치, 토픽 컷오프)은 도입 시 결정하세요.

## #11 카카오톡 / 네이버 톡톡 채널 연동

Chainlit은 웹 UI 전용입니다. 메신저 채널은 별도 webhook 엔드포인트가 필요합니다.

권장 구조:
1. **로직 분리** — `data.py`/`flow.py`/`prompts.py`/`llm.py`는 그대로 재사용
2. **FastAPI 엔드포인트 신설** — `messenger_webhook.py`에 카카오/네이버 webhook 핸들러
3. 핸들러가 `_process_user_turn`과 동일한 파이프라인을 호출하되, 응답을 메신저 SDK 포맷(JSON)으로 변환
4. 세션 상태는 Redis(`session_id` = 카톡 user_key) 또는 SQLite로 영속화

참고:
- 카카오 i 오픈빌더: https://i.kakao.com/docs/skill-response-format
- 네이버 톡톡 챗봇 API: https://developers.naver.com/docs/talktalk/

## #12 Literal AI (Chainlit 네이티브 통합)

Chainlit은 Literal AI를 1급으로 지원합니다. 코드 변경 없이 환경변수만 추가하면 모든 LLM 호출의 트레이스/토큰비용/지연시간이 자동 수집됩니다.

```bash
# https://literalai.com 가입 후 API 키 발급
echo "LITERAL_API_KEY=lsk-..." >> .env
chainlit run app.py -w
```

Literal 대시보드에서 가능한 것:
- 프롬프트 버저닝 + 비교 (A/B)
- 단계별 평가 (LLM-as-judge)
- 사용자별 세션 리플레이
- 비용/지연 시간 일별 집계

## #15 전문 상담사 연결 (인간 에스컬레이션)

CTA 버튼은 `app.py:on_escalate_human`에서 처리됩니다. 실제 상담사 연결을 자동화하려면:

1. **티켓 생성** — Zendesk/Freshdesk API로 티켓 자동 생성, 본문에 `db.session_summary(session_id)` 첨부
2. **Slack 알림** — 상담팀 채널에 webhook으로 "신규 에스컬레이션 + 세션 요약 + 입장 링크" 푸시
3. **상담사 인계 UI** — Chainlit `cl.User` + 별도 어드민 뷰에서 활성 세션 takeover (Chainlit 1.3+의 human-in-the-loop 패턴)

## #16 멀티에이전트 구조

현재 단일 LLM이 5단계를 모두 수행합니다. 분리하면 단계별 품질 관리가 쉬워집니다.

제안 구조:
```
NeedAgent       — 사용자 발화에서 니즈/심각도/긴급성 추출 (JSON 출력)
ProductAgent    — 추출된 니즈 + 분석 데이터를 받아 추천 메시지 생성
SafetyAgent     — ProductAgent 출력을 검토, 임신/약물 상호작용 등 위험 시 차단/수정
RouterAgent     — 위 셋을 호출하고 사용자에게 응답 조합
```

구현 옵션:
- **수동 파이프라인** — `app.py`에서 세 번의 `astream_reply()` 호출, 각각 다른 시스템 프롬프트
- **LangGraph** — 상태 그래프로 표현, 조건부 라우팅 자유로움
- **Claude Agent SDK / OpenAI Assistants API** — 도구 호출 기반

비용·지연시간이 N배가 되므로 진짜 필요해질 때 도입하세요. (현재 단일 LLM + 단계별 프롬프트로 충분히 구조적임)
