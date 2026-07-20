import time
from pathlib import Path
from typing import Any

def call_antigravity(prompt: str, config: dict[str, Any], stage_id: str | None = None) -> str:
    """
    Sử dụng file-based bridge để chờ Antigravity agent xử lý prompt.
    Trả về response_text hoặc raise TimeoutError nếu quá thời gian.
    """
    stage = stage_id or "unknown"
    timeout_seconds = config.get("antigravity", {}).get("timeout", 300)
    
    print(f"[ANTIGRAVITY] Requesting LLM generation for stage '{stage}'...")
    temp_dir = Path(__file__).resolve().parents[1] / "runs" / "temp_llm"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    ts = int(time.time() * 1000)
    prompt_file = temp_dir / f"prompt_{stage}_{ts}.txt"
    response_file = temp_dir / f"response_{stage}_{ts}.txt"
    
    prompt_file.write_text(prompt, encoding="utf-8")
    
    # Write model info to help verification if needed
    model = config.get("openai", {}).get("model", "antigravity-internal")
    model_info_file = temp_dir / f"model_{stage}_{ts}.txt"
    model_info_file.write_text(model, encoding="utf-8")
    
    print(f"[REQUEST_LLM] {prompt_file.resolve()} -> {response_file.resolve()} (model info: {model_info_file.name})", flush=True)
    
    start_time = time.time()
    print(f"[WAITING] Waiting for response file: {response_file.name}", flush=True)
    while not response_file.exists():
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(f"Antigravity did not respond within {timeout_seconds} seconds for stage {stage}.")
        time.sleep(1)

    print(f"[RECEIVED] Found response file: {response_file.name}", flush=True)
    response_text = response_file.read_text(encoding="utf-8")
    
    try:
        prompt_file.unlink(missing_ok=True)
        model_info_file.unlink(missing_ok=True)
    except Exception:
        pass
        
    return response_text
