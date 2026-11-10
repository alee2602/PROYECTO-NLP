import json
import os

import requests

# Default points at LM Studio's local server (OpenAI-compatible REST API).
# Override via env vars to switch to a cloud provider without touching the
# code — see DECISIONS.md for why LM Studio was chosen for development, and
# why this talks to the REST API directly instead of using the `openai` SDK
# (its `jiter` native dependency got blocked by Windows Smart App Control).
DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "local-model"
DEFAULT_TIMEOUT = 120


class LLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "lm-studio")
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.0,
        response_format: dict | None = None,
    ) -> dict:
        payload = {
            "model": model or os.getenv("LLM_MODEL", DEFAULT_MODEL),
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def get_client(base_url: str | None = None, api_key: str | None = None) -> LLMClient:
    return LLMClient(base_url=base_url, api_key=api_key)


def generate_json(
    client: LLMClient,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict,
    schema_name: str = "response",
    model: str | None = None,
    temperature: float = 0.0,
) -> dict:
    """Ask the model for an object matching json_schema and parse it. Uses
    the "json_schema" response format (grammar-constrained decoding), not
    the older "json_object" mode — LM Studio's server only accepts
    "json_schema" or "text", it rejects "json_object" with a 400."""
    data = client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        temperature=temperature,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": json_schema, "strict": True},
        },
    )
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)
