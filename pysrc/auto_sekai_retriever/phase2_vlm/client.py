from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from auto_sekai_retriever.phase2_vlm.prompt import build_system_prompt, build_user_prompt


load_dotenv()


@dataclass(frozen=True)
class Phase2ClientConfig:
    api_key: str
    base_url: str | None
    model: str
    reasoning_effort: str
    retries: int


def load_client_config() -> Phase2ClientConfig:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return Phase2ClientConfig(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        reasoning_effort=os.getenv("REASONING_EFFORT", "medium"),
        retries=int(os.getenv("ASR_REQUEST_RETRIES", "3")),
    )


class Phase2VLMClient:
    def __init__(self, config: Phase2ClientConfig | None = None) -> None:
        self.config = config or load_client_config()
        self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

    @staticmethod
    def _image_data_url(image_path: Path) -> str:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def tag_image(self, image_id: str, character: str, image_path: Path) -> str:
        content = [
            {"type": "text", "text": build_user_prompt(image_id, character)},
            {"type": "image_url", "image_url": {"url": self._image_data_url(image_path)}},
        ]
        last_error: Exception | None = None
        for attempt in range(1, self.config.retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": build_system_prompt()},
                        {"role": "user", "content": content},
                    ],
                    response_format={"type": "json_object"},
                    reasoning_effort=self.config.reasoning_effort,
                )
                message = response.choices[0].message.content
                if not message:
                    raise RuntimeError("empty model response")
                return message
            except Exception as exc:  # pragma: no cover - exercised in real integration
                last_error = exc
                if attempt < self.config.retries:
                    time.sleep(0.5 * attempt)
        raise RuntimeError(f"failed to tag {image_id}: {last_error}") from last_error


def serialize_raw_response(image_id: str, raw_text: str) -> str:
    return json.dumps({"image_id": image_id, "raw_text": raw_text}, ensure_ascii=False)

