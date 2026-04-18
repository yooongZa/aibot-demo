from collections.abc import AsyncIterator, Iterator

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from tenacity import (
    AsyncRetrying,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import (
    GOOGLE_API_KEY,
    MAX_HISTORY_MESSAGES,
    MODEL_NAME,
    REQUEST_TIMEOUT,
    RETRY_ATTEMPTS,
)

_configured = False

_RETRYABLE = (
    google_exceptions.ServiceUnavailable,
    google_exceptions.DeadlineExceeded,
    google_exceptions.InternalServerError,
    google_exceptions.ResourceExhausted,
    TimeoutError,
    ConnectionError,
)


def configure_gemini() -> None:
    global _configured
    if _configured:
        return
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY가 설정되지 않았습니다.")
    genai.configure(api_key=GOOGLE_API_KEY)
    _configured = True


def _to_gemini_contents(history: list[dict]) -> list[dict]:
    contents: list[dict] = []
    for msg in history[-MAX_HISTORY_MESSAGES:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [msg["content"]]})
    return contents


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(_RETRYABLE),
    reraise=True,
)
def _open_stream(model: genai.GenerativeModel, contents: list[dict]):
    return model.generate_content(
        contents,
        stream=True,
        request_options={"timeout": REQUEST_TIMEOUT},
    )


def stream_reply(history: list[dict], system_prompt: str) -> Iterator[str]:
    """Yield response chunks from Gemini. Retries the stream-open call but not mid-stream failures."""
    configure_gemini()
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=system_prompt)
    contents = _to_gemini_contents(history)
    stream = _open_stream(model, contents)
    for chunk in stream:
        text = getattr(chunk, "text", None)
        if text:
            yield text


async def _aopen_stream(model: genai.GenerativeModel, contents: list[dict]):
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    ):
        with attempt:
            return await model.generate_content_async(
                contents,
                stream=True,
                request_options={"timeout": REQUEST_TIMEOUT},
            )


async def astream_reply(
    history: list[dict], system_prompt: str
) -> AsyncIterator[str]:
    """Async version of stream_reply for Chainlit's async runtime."""
    configure_gemini()
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=system_prompt)
    contents = _to_gemini_contents(history)
    stream = await _aopen_stream(model, contents)
    async for chunk in stream:
        text = getattr(chunk, "text", None)
        if text:
            yield text
