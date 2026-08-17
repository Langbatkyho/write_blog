"""
Client Router — Định tuyến LLM client theo stage_id.

Module này cung cấp:
- build_client_map(): Parse chuỗi --client-map thành dict.
- resolve_client(): Trả về LlmClient callable từ tên client.
- create_routing_client(): Tạo một LlmClient duy nhất có khả năng
  dispatch theo stage_id.
"""

from typing import Any, Callable

LlmClient = Callable[[str, dict[str, Any], str | None], str]

def _get_openai() -> LlmClient:
    from engine.openai_client import call_openai
    return call_openai

def _get_antigravity() -> LlmClient:
    from engine.antigravity_bridge import call_antigravity
    return call_antigravity

def _get_gemini() -> LlmClient:
    from engine.gemini_client import call_gemini
    return call_gemini

def _get_deepseek() -> LlmClient:
    from engine.deepseek_client import call_deepseek
    return call_deepseek

# Registry: tên client -> hàm import lazy
_CLIENT_REGISTRY: dict[str, Callable[[], LlmClient]] = {
    "openai": _get_openai,
    "antigravity": _get_antigravity,
    "gemini": _get_gemini,
    "deepseek": _get_deepseek,
}

_PROVIDER_API_CAPABILITY = {
    "openai": True,
    "gemini": True,
    "antigravity": False,
    "deepseek": True,
}

VALID_CLIENTS = set(_CLIENT_REGISTRY.keys())


def build_client_map(
    client_map_str: str | None,
    fallback: str = "openai",
) -> dict[str, str]:
    """
    Parse chuỗi CLI thành dict {stage_id: client_name}.

    Args:
        client_map_str: Chuỗi dạng "stage1=client,stage2=client" hoặc None.
        fallback: Client mặc định (không dùng trong dict, chỉ để validate).

    Returns:
        Dict mapping stage_id -> client_name.
        Trả về dict rỗng nếu client_map_str là None hoặc rỗng.

    Raises:
        ValueError: Nếu format sai hoặc client_name không hợp lệ.
    """
    if fallback not in VALID_CLIENTS:
        raise ValueError(
            f"Unknown fallback client '{fallback}'. "
            f"Valid clients: {sorted(VALID_CLIENTS)}."
        )
    if not client_map_str:
        return {}

    result: dict[str, str] = {}
    for pair in client_map_str.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(
                f"Invalid client-map entry: '{pair}'. "
                f"Expected format: 'stage_id=client_name'."
            )
        stage_id, client_name = pair.split("=", 1)
        stage_id = stage_id.strip()
        client_name = client_name.strip()
        if client_name not in VALID_CLIENTS:
            raise ValueError(
                f"Unknown client '{client_name}' for stage '{stage_id}'. "
                f"Valid clients: {sorted(VALID_CLIENTS)}."
            )
        if not stage_id:
            raise ValueError("Stage ID cannot be empty in client-map.")
        result[stage_id] = client_name
    return result


def validate_client_map(
    client_map: dict[str, str], valid_stage_ids: set[str]
) -> None:
    unknown = sorted(set(client_map) - valid_stage_ids)
    if unknown:
        raise ValueError(f"Client map chứa stage không tồn tại: {unknown}")


def resolve_client(client_name: str) -> LlmClient:
    """
    Trả về LlmClient callable từ tên client.

    Raises:
        ValueError: Nếu client_name không hợp lệ.
    """
    if client_name not in _CLIENT_REGISTRY:
        raise ValueError(
            f"Unknown client: '{client_name}'. "
            f"Valid clients: {sorted(VALID_CLIENTS)}."
        )
    return _CLIENT_REGISTRY[client_name]()


def create_routing_client(
    client_map: dict[str, str],
    fallback: str = "openai",
) -> LlmClient:
    """
    Tạo một LlmClient duy nhất dispatch theo stage_id.

    Cách hoạt động:
    1. Khi được gọi với stage_id, tra cứu client_map.
    2. Nếu stage_id có trong map → dùng client tương ứng.
    3. Nếu không → dùng fallback client.

    Args:
        client_map: Dict {stage_id: client_name} từ build_client_map().
        fallback: Tên client mặc định.

    Returns:
        Một LlmClient callable tương thích signature
        Callable[[str, dict[str, Any], str | None], str].
    """
    if fallback not in VALID_CLIENTS:
        raise ValueError(
            f"Unknown fallback client '{fallback}'. "
            f"Valid clients: {sorted(VALID_CLIENTS)}."
        )
    invalid_clients = sorted(set(client_map.values()) - VALID_CLIENTS)
    if invalid_clients:
        raise ValueError(f"Client map chứa provider không hợp lệ: {invalid_clients}")

    # Cache các client đã resolve để tránh import lặp
    _cache: dict[str, LlmClient] = {}

    def _get_client(name: str) -> LlmClient:
        if name not in _cache:
            _cache[name] = resolve_client(name)
        return _cache[name]

    def routing_client(
        prompt: str,
        config: dict[str, Any],
        stage_id: str | None = None,
    ) -> str:
        client_name = client_map.get(stage_id or "", fallback)
        client = _get_client(client_name)
        print(f"[ROUTER] Stage '{stage_id}' → client '{client_name}'")
        return client(prompt, config, stage_id)

    # Preserve name for metadata logging
    routing_client.__name__ = "routing_client"
    routing_client.client_map = client_map
    routing_client.fallback_name = fallback
    routing_client.provider_name = "routing"
    routing_client.api_capable = True

    def describe_stage(
        stage_id: str, config: dict[str, Any]
    ) -> dict[str, str | bool]:
        provider = client_map.get(stage_id, fallback)
        if provider in {"openai", "antigravity"}:
            from engine.openai_client import get_openai_options

            model = str(get_openai_options(config, stage_id).get("model"))
        elif provider == "deepseek":
            from engine.deepseek_client import get_deepseek_options

            model = str(get_deepseek_options(config, stage_id).get("model"))
        else:
            from engine.gemini_client import get_gemini_model

            model = get_gemini_model(config, stage_id)
        return {
            "provider": provider,
            "model": model,
            "api_capable": _PROVIDER_API_CAPABILITY[provider],
        }

    routing_client.describe_stage = describe_stage
    return routing_client
