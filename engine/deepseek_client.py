import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

def get_api_key(config: dict[str, Any]) -> str:
    deepseek_config = config.get("deepseek", {})
    env_name = str(deepseek_config.get("api_key_env", "DEEPSEEK_API_KEY"))
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(
            f"DeepSeek API key not found. Set environment variable {env_name} "
            "or check .env file."
        )
    return api_key

def extract_response_text(response: dict[str, Any], config: dict[str, Any], stage_id: str | None = None) -> str:
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        reasoning_content = message.get("reasoning_content")

        # Lưu reasoning_content nếu có
        if reasoning_content and isinstance(reasoning_content, str):
            run_dir = config.get("_current_run_dir")
            if run_dir:
                reasoning_file = Path(run_dir) / f"{stage_id or 'unknown'}_reasoning.md"
                try:
                    with open(reasoning_file, "w", encoding="utf-8") as f:
                        f.write("## Reasoning Content\n\n")
                        f.write(reasoning_content)
                except Exception as e:
                    print(f"Failed to write reasoning content: {e}")
            else:
                print(f"[DeepSeek] {stage_id} reasoning_content generated but no run_dir to save.")

        if isinstance(content, str):
            return content.strip()

    return json.dumps(response, ensure_ascii=False, indent=2)

def get_deepseek_options(config: dict[str, Any], stage_id: str | None = None) -> dict[str, Any]:
    deepseek_config = config.get("deepseek", {})
    options: dict[str, Any] = {
        "endpoint": deepseek_config.get("endpoint", "https://api.deepseek.com/chat/completions"),
        "model": deepseek_config.get("model", "deepseek-v4-pro"),
        "max_output_tokens": deepseek_config.get("max_output_tokens", 8192),
        "timeout": deepseek_config.get("timeout", 300),
        "thinking": deepseek_config.get("thinking", {}),
    }

    if stage_id:
        stage_overrides = deepseek_config.get("stages", {}).get(stage_id, {})
        learning_overrides = deepseek_config.get("learning", {}).get(stage_id, {})
        if isinstance(stage_overrides, dict):
            options.update(stage_overrides)
        if isinstance(learning_overrides, dict):
            options.update(learning_overrides)
    return options

def call_deepseek(prompt: str, config: dict[str, Any], stage_id: str | None = None, max_retries: int = 3) -> str:
    options = get_deepseek_options(config, stage_id)
    endpoint = str(options["endpoint"])
    if not endpoint.rstrip("/").endswith("/chat/completions"):
        endpoint = endpoint.rstrip("/") + "/chat/completions"
        
    model = str(options["model"])
    max_output_tokens = int(options["max_output_tokens"])
    timeout = int(options.get("timeout", 300))
    thinking_opts = options.get("thinking", {})

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a careful Vietnamese reflective writing partner.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_output_tokens,
    }
    
    # Configure Thinking Mode
    if thinking_opts.get("enabled", True):
        payload["reasoning_effort"] = thinking_opts.get("reasoning_effort", "high")
    else:
        payload["temperature"] = float(options.get("temperature", 0.7))

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
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            return extract_response_text(json.loads(body), config, stage_id)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 503) and attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                print(f"DeepSeek request failed with {exc.code}. Retrying in {sleep_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek request failed: HTTP {exc.code}\n{body}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                print(f"DeepSeek request failed with URL error {exc}. Retrying in {sleep_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                continue
            raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

call_deepseek.provider_name = "deepseek"
call_deepseek.api_capable = True
