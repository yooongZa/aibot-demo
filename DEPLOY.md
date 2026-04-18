# 공개 URL 배포 가이드

이 데모는 두 부분으로 구성됩니다:
- **랜딩 페이지** (`web/`) — 정적 HTML/CSS/JS
- **챗봇 서버** (`app.py`) — Chainlit (Python)

각각 따로 호스팅해도 되고, 한 군데(HF Spaces)에 같이 올려도 됩니다. 가장 빠른 무료 경로 두 가지를 정리합니다.

## 옵션 A. GitHub Pages + Hugging Face Spaces (추천, 둘 다 무료)

### A-1. 랜딩 페이지 → GitHub Pages

> ⚠️ **사전 준비 (필수)**: Pages가 리포 설정에서 활성화되지 않은 상태로 워크플로가 돌면
> `configure-pages` 단계가 실패합니다. 아래 1번을 먼저 해주세요.

1. https://github.com/<username>/<repo>/settings/pages 접속 →
   **Source: GitHub Actions** 선택 → 저장
2. `main` 브랜치에 `web/` 변경사항이 푸시되면 `.github/workflows/pages.yml`가
   자동으로 빌드·배포합니다 (또는 Actions 탭에서 "Run workflow" 수동 트리거)
3. 배포 완료 후 URL: `https://<username>.github.io/<repo>/`
   - 예: `https://yooongza.github.io/aibot/`

### A-2. 챗봇 → Hugging Face Spaces

1. https://huggingface.co/new-space 에서 Space 생성
   - **Space SDK**: Docker
   - **Space Hardware**: CPU basic (무료)
2. 리포의 `Dockerfile`이 그대로 사용됨 (이미 포함되어 있음)
3. Settings → **Variables and secrets**에 `GOOGLE_API_KEY` 추가
4. 업로드 방법:
   ```bash
   git remote add hf https://huggingface.co/spaces/<username>/aibot-chat
   git push hf claude/health-supplement-chatbot-VFtOr:main
   ```
5. URL: `https://<username>-aibot-chat.hf.space`

### A-3. 두 서비스 연결

랜딩 페이지가 챗봇 위젯을 호출할 수 있도록 `web/static/copilot.js`의 `CHAINLIT_SERVER`를 HF Spaces URL로 수정한 뒤 다시 푸시:

```js
window.CHAINLIT_SERVER = "https://<username>-aibot-chat.hf.space";
```

또는 환경별로 분기:
```js
window.CHAINLIT_SERVER = location.hostname === "localhost"
  ? "http://localhost:8000"
  : "https://<username>-aibot-chat.hf.space";
```

## 옵션 B. Render (한 곳에 다, 5분)

1. https://render.com 가입 → **New → Web Service**
2. 이 GitHub 리포 연결 → Build Command: `pip install -r requirements.txt`
3. Start Command: `chainlit run app.py --host 0.0.0.0 --port $PORT --headless`
4. Environment에 `GOOGLE_API_KEY` 추가
5. Free 플랜으로 배포 → URL: `https://aibot-xxx.onrender.com`

랜딩 페이지를 함께 서빙하려면 `app.py`에 정적 라우트를 추가하거나, 별도 `serve_web.py`를 함께 호스팅하세요.

## 옵션 C. Cloudflare Pages + Workers

비슷하게 무료, 더 빠른 CDN. 워크플로 파일은 비슷한 구조로 작성하면 됩니다.

## 로컬에서 둘 다 띄우기

```bash
# 터미널 1
chainlit run app.py -w

# 터미널 2
python3 serve_web.py
```

방문: http://localhost:8080 (랜딩) + 챗봇 위젯이 http://localhost:8000 으로 연결

## 체크리스트

- [ ] `.env` 에 `GOOGLE_API_KEY` 설정
- [ ] HF Spaces secret에 동일한 키 설정
- [ ] 배포된 챗봇 URL을 `web/static/copilot.js`에 반영
- [ ] `.chainlit/config.toml`의 `allow_origins`를 와일드카드(`*`) 대신 실제 랜딩 도메인으로 변경
- [ ] 도메인 연결 시 HTTPS 필수 (HF Spaces는 기본 HTTPS)
