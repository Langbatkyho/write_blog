"""
Gemini Client — Gọi Google Gemini API (Free Tier) với rate limiting và key rotation.

Rate limits (gemini-2.0-flash free tier):
  - 5 RPM (requests per minute)
  - 250k TPM (tokens per minute)  
  - 20 RPD (requests per day)
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from engine.app_logger import log as app_log

# ---------- Key Rotation ----------

_keys: list[str] = []
_key_index: int = 0

def _mask_key(k: str) -> str:
    """Return first 4 + last 4 chars for safe logging."""
    if len(k) <= 10:
        return k[:2] + "***"
    return k[:4] + "..." + k[-4:]


def _load_keys() -> list[str]:
    """Load all GEMINI_API_KEY_* from environment or .env file."""
    global _keys
    if _keys:
        return _keys

    # Try loading from .env file first
    env_path = Path(__file__).resolve().parents[1] / ".env"
    env_loaded = False
    if env_path.exists():
        env_loaded = True
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip().strip('\'"')
            if name.startswith("GEMINI_API_KEY") and value and value != "YOUR_KEY_HERE":
                os.environ.setdefault(name, value)

    # Log diagnostic info
    is_render = bool(os.environ.get("RENDER"))
    app_log("KEY", f"Platform: {'Render' if is_render else 'Local'}, .env: {'found' if env_loaded else 'not found'}")

    # Collect all keys from env
    matched_vars = []
    for key_name in sorted(os.environ.keys()):
        if key_name.startswith("GEMINI_API_KEY"):
            val = os.environ[key_name].strip().strip('\'"')
            matched_vars.append((key_name, val))
            if val and val != "YOUR_KEY_HERE":
                # Handle comma-separated keys in a single variable
                if "," in val:
                    for k in val.split(","):
                        k = k.strip()
                        if k and k != "YOUR_KEY_HERE":
                            _keys.append(k)
                else:
                    _keys.append(val)

    app_log("KEY", f"Matched vars: {[(name, _mask_key(val)) for name, val in matched_vars]}")

    # Fallback: single key
    if not _keys:
        single = os.environ.get("GEMINI_API_KEY", "").strip().strip('\'"')
        if single and single != "YOUR_KEY_HERE":
            _keys.append(single)
            app_log("KEY", f"Fallback single key: {_mask_key(single)}")

    app_log("KEY", f"Total keys loaded: {len(_keys)}")
    if not _keys:
        app_log("KEY", "WARNING: No keys found!", level="ERROR")

    return _keys


def _next_key() -> str:
    """Round-robin key rotation."""
    global _key_index
    keys = _load_keys()
    if not keys:
        raise RuntimeError(
            "Không tìm thấy Gemini API Key. "
            "Hãy điền key vào file .env (GEMINI_API_KEY_1=...) "
            "hoặc set biến môi trường GEMINI_API_KEY."
        )
    key = keys[_key_index % len(keys)]
    _key_index += 1
    return key


# ---------- Rate Limiter (5 RPM) ----------

_request_timestamps: list[float] = []
_RPM_LIMIT = 14  # Stay safely under the 15 RPM limit
_WINDOW = 60.0  # seconds

def _rate_limit():
    """Block until we are within the 14 RPM window (safe buffer under 15 RPM)."""
    now = time.time()
    _request_timestamps[:] = [t for t in _request_timestamps if now - t < _WINDOW]

    if len(_request_timestamps) >= _RPM_LIMIT:
        wait = _WINDOW - (now - _request_timestamps[0]) + 0.5
        if wait > 0:
            print(f"[GEMINI] Rate limit reached ({_RPM_LIMIT} RPM). Waiting {wait:.1f}s...")
            time.sleep(wait)

    _request_timestamps.append(time.time())


# Try importing Google GenAI official SDK
try:
    from google import genai
    from google.genai import types
    _HAS_GENAI_SDK = True
except ImportError:
    _HAS_GENAI_SDK = False

# ---------- API Call ----------

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.5-flash"


def get_gemini_model(
    config: dict[str, Any] | None,
    stage_id: str | None = None,
) -> str:
    gemini_config = (config or {}).get("gemini", {})
    if not isinstance(gemini_config, dict):
        raise ValueError("Cấu hình 'gemini' phải là object.")
    model = gemini_config.get("model", DEFAULT_MODEL)
    stages = gemini_config.get("stages", {})
    if not isinstance(stages, dict):
        raise ValueError("Cấu hình 'gemini.stages' phải là object.")
    stage_config = stages.get(stage_id or "", {})
    if stage_config and not isinstance(stage_config, dict):
        raise ValueError(
            f"Cấu hình Gemini cho stage '{stage_id}' phải là object."
        )
    if isinstance(stage_config, dict):
        model = stage_config.get("model", model)
    model_name = str(model).strip()
    if not model_name:
        raise ValueError("Gemini model không được để trống.")
    return model_name


def call_gemini(
    prompt: str,
    config: dict[str, Any] | None = None,
    stage_id: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
    thinking_budget: int = 1024,
    max_retries: int | None = None,
) -> str:
    """
    Call Gemini API with rate limiting, key rotation, and High Thinking Mode.
    Compatible signature with call_openai / call_antigravity.
    """
    keys_count = len(_load_keys())
    if max_retries is None:
        max_retries = max(3, keys_count + 1)
    config = dict(config or {})
    model = model or get_gemini_model(config, stage_id)
    _rate_limit()
    api_key = _next_key()
    response_mime_type = config.get("response_mime_type") or config.get("responseMimeType")
    response_schema = config.get("response_schema") or config.get("responseSchema")
    is_json_schema = isinstance(response_schema, dict) and (
        "$defs" in response_schema or "$schema" in response_schema
    )

    stage_label = stage_id or "unknown"
    budget_str = f" (Thinking: {thinking_budget})" if thinking_budget > 0 else ""
    app_log("GEMINI", f"⚡ {model} → '{stage_label}' | Key: {_mask_key(api_key)}{budget_str}")

    # Strategy 1: Use official google.genai SDK if available
    if _HAS_GENAI_SDK:
        for attempt in range(max_retries):
            try:
                client = genai.Client(api_key=api_key)
                config_kwargs = {
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    "response_mime_type": response_mime_type,
                }
                if is_json_schema:
                    config_kwargs["response_json_schema"] = response_schema
                else:
                    config_kwargs["response_schema"] = response_schema
                gen_config = types.GenerateContentConfig(**config_kwargs)
                if thinking_budget and thinking_budget > 0:
                    gen_config.thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=gen_config,
                )
                if response and response.text:
                    result = response.text.strip()
                    print(f"[GEMINI] [OK] Response received via SDK ({len(result)} chars)")
                    return result
            except Exception as exc:
                if attempt < max_retries - 1:
                    api_key = _next_key()
                    wait = 2 if keys_count > 1 else 2 ** attempt
                    print(f"[GEMINI SDK] Retry {attempt+1}/{max_retries} due to: {exc}. Rotating & waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"[GEMINI SDK] Fallback to REST API due to: {exc}")

    # Strategy 2: Fallback to REST API via urllib
    endpoint = GEMINI_ENDPOINT.format(model=model)
    url = f"{endpoint}?key={api_key}"

    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if thinking_budget and thinking_budget > 0:
        generation_config["thinkingConfig"] = {
            "thinkingBudget": thinking_budget
        }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type
    if response_schema and is_json_schema:
        generation_config["responseJsonSchema"] = response_schema
    elif response_schema:
        generation_config["responseSchema"] = response_schema

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": generation_config,
    }

    for attempt in range(max_retries):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                texts = [p.get("text", "") for p in parts if "text" in p]
                if texts:
                    result = "\n".join(texts).strip()
                    print(f"[GEMINI] [OK] Response received ({len(result)} chars)")
                    return result
            # If no candidates, return raw
            return json.dumps(data, ensure_ascii=False, indent=2)

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            is_quota_error = exc.code == 429 or (exc.code in (400, 403) and ("quota" in body.lower() or "rate limit" in body.lower()))
            
            if is_quota_error and attempt < max_retries - 1:
                # Rate limited — try next key and wait
                api_key = _next_key()
                url = f"{endpoint}?key={api_key}"
                wait = 2 if keys_count > 1 else 12 * (attempt + 1)
                print(f"[GEMINI] {exc.code} Quota/Rate limit. Rotating key & waiting {wait}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            elif exc.code in (500, 503) and attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[GEMINI] Server error {exc.code}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini API failed: HTTP {exc.code}\n{body}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[GEMINI] Network error: {exc}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini API network error: {exc}") from exc

    raise RuntimeError("Gemini API: all retries exhausted")
