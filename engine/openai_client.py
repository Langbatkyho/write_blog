import json
import os
import time
import urllib.error
import urllib.request
import warnings
from typing import Any

def get_api_key(config: dict[str, Any]) -> str:
    openai_config = config.get("openai", {})
    direct_key = openai_config.get("api_key")
    if direct_key:
        warnings.warn(
            "API key is hardcoded in config. Use api_key_env instead to avoid leaking keys.",
            UserWarning,
            stacklevel=2,
        )
        return str(direct_key)

    env_name = str(openai_config.get("api_key_env", "OPENAI_API_KEY"))
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(
            f"OpenAI API key not found. Set environment variable {env_name} "
            "or put api_key in engine/config.local.yaml."
        )
    return api_key

def extract_response_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"].strip()

    output = response.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
        if chunks:
            return "\n".join(chunks).strip()

    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()

    return json.dumps(response, ensure_ascii=False, indent=2)

def get_openai_options(config: dict[str, Any], stage_id: str | None = None) -> dict[str, Any]:
    openai_config = config.get("openai", {})
    options: dict[str, Any] = {
        "endpoint": openai_config.get("endpoint", "https://api.openai.com/v1/responses"),
        "model": openai_config.get("model", "gpt-4.1"),
        "temperature": openai_config.get("temperature", 0.7),
        "max_output_tokens": openai_config.get("max_output_tokens", 4096),
    }

    if stage_id:
        stage_overrides = openai_config.get("stages", {}).get(stage_id, {})
        learning_overrides = openai_config.get("learning", {}).get(stage_id, {})
        if isinstance(stage_overrides, dict):
            options.update(stage_overrides)
        if isinstance(learning_overrides, dict):
            options.update(learning_overrides)
    return options

def call_openai(prompt: str, config: dict[str, Any], stage_id: str | None = None, max_retries: int = 3) -> str:
    options = get_openai_options(config, stage_id)
    endpoint = str(options["endpoint"])
    model = str(options["model"])
    temperature = float(options["temperature"])
    max_output_tokens = int(options["max_output_tokens"])

    if endpoint.rstrip("/").endswith("/chat/completions"):
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful Vietnamese reflective writing partner.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
    else:
        payload = {
            "model": model,
            "input": prompt,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

    api_key = get_api_key(config)
    for attempt in range(max_retries):
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read().decode("utf-8")
            return extract_response_text(json.loads(body))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 503) and attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                print(f"OpenAI request failed with {exc.code}. Retrying in {sleep_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI request failed: HTTP {exc.code}\n{body}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                print(f"OpenAI request failed with URL error {exc}. Retrying in {sleep_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                continue
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
