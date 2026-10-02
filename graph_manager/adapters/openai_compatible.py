"""OpenAI-compatible chat adapter for a locally served VLM, such as vLLM."""

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from ..domain.models import ChatMessage
from ..ports import ModelPortError


class ModelAdapterError(ModelPortError):
    """The model endpoint did not return usable chat content."""

    def __init__(self, message: str, raw_content: str | None = None):
        self.raw_content = raw_content
        super().__init__(message, partial_output=raw_content)


class OpenAICompatibleModel:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        max_tokens: int = 4096,
    ):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("base_url must be an HTTP(S) API URL without query or fragment")
        if not model.strip():
            raise ValueError("model must be nonempty")
        if timeout <= 0 or max_tokens <= 0:
            raise ValueError("timeout and max_tokens must be positive")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(self, messages: tuple[ChatMessage, ...]) -> str:
        wire_messages = []
        for message in messages:
            if message.role not in {"system", "user", "assistant"}:
                raise ValueError(f"unsupported model message role: {message.role}")
            content: str | list[dict] = message.text
            if message.image is not None:
                encoded = base64.b64encode(message.image).decode("ascii")
                content = [
                    {"type": "text", "text": message.text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{message.image_mime};base64,{encoded}"},
                    },
                ]
            wire_messages.append({"role": message.role, "content": content})
        payload = {
            "model": self.model,
            "messages": wire_messages,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            self.url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read(1024).decode("utf-8", errors="replace")
            raise ModelAdapterError(f"model HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise ModelAdapterError(f"model request failed: {exc}") from exc
        try:
            choice = json.loads(body)["choices"][0]
            message = choice["message"]
            content = message["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelAdapterError("model response has no choices[0].message.content") from exc
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and finish_reason != "stop":
            raise ModelAdapterError(
                f"model completion ended with finish_reason={finish_reason}",
                raw_content=content if isinstance(content, str) else None,
            )
        if not isinstance(content, str) or not content.strip():
            raise ModelAdapterError("model response content must be nonempty text")
        return content
