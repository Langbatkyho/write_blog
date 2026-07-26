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

# ---------- Key Rotation ----------

_keys: list[str] = []
_key_index: int = 0

def _load_keys() -> list[str]:
    """Load all GEMINI_API_KEY_* from environment or .env file."""
    global _keys
    if _keys:
        return _keys

    # Try loading from .env file first
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip()
            if name.startswith("GEMINI_API_KEY") and value and value != "YOUR_KEY_HERE":
                os.environ.setdefault(name, value)

    # Collect all keys from env
    for key_name in sorted(os.environ.keys()):
        if key_name.startswith("GEMINI_API_KEY"):
            val = os.environ[key_name].strip()
            if val and val != "YOUR_KEY_HERE":
                _keys.append(val)

    # Fallback: single key
    if not _keys:
        single = os.environ.get("GEMINI_API_KEY", "").strip()
        if single and single != "YOUR_KEY_HERE":
            _keys.append(single)

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


# ---------- API Call ----------

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.5-flash"


def call_gemini(
    prompt: str,
    config: dict[str, Any] | None = None,
    stage_id: str | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
    max_retries: int = 3,
) -> str:
    """
    Call Gemini API with rate limiting and key rotation.
    Compatible signature with call_openai / call_antigravity.
    """
    _rate_limit()
    api_key = _next_key()

    endpoint = GEMINI_ENDPOINT.format(model=model)
    url = f"{endpoint}?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }

    stage_label = stage_id or "unknown"
    print(f"[GEMINI] Calling {model} for stage '{stage_label}'...")

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
                    print(f"[GEMINI] ✅ Response received ({len(result)} chars)")
                    return result
            # If no candidates, return raw
            return json.dumps(data, ensure_ascii=False, indent=2)

        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < max_retries - 1:
                # Rate limited — try next key and wait
                api_key = _next_key()
                url = f"{endpoint}?key={api_key}"
                wait = 12 * (attempt + 1)
                print(f"[GEMINI] 429 Rate limited. Rotating key & waiting {wait}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            elif exc.code in (500, 503) and attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[GEMINI] Server error {exc.code}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API failed: HTTP {exc.code}\n{body}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[GEMINI] Network error: {exc}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini API network error: {exc}") from exc

    raise RuntimeError("Gemini API: all retries exhausted")
