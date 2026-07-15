# Tổng hợp Git Diff và Thay đổi Code

*Lưu ý: Kho lưu trữ Git mới được khởi tạo ở thời điểm hiện tại. Do đó, toàn bộ lịch sử và "diff" trong quá khứ đã được gom gọn vào Initial Commit. Dưới đây là tóm tắt các thay đổi về mã nguồn (Code Diff Summary) được tái tạo từ các Log trước.*

## 1. Modularization (Tách Monolith)
- **Xóa file cũ**: `run_workflow.py` (phiên bản monolith 892 dòng).
- **Thêm file mới**:
  - `engine/utils.py`: Thêm `read_text`, `write_text`, `load_yaml`, `resolve_path`.
  - `engine/parser.py`: Thêm `parse_stage_response`, `build_context_package`.
  - `engine/openai_client.py`: Thêm `call_openai` với cơ chế Exponential Backoff Retry.
  - `engine/learning.py`: Thêm các hàm `build_learning_prompt`, `build_offline_learning_report`.
  - `engine/workflow.py`: Chứa lõi `run_workflow` và `run_learning_loop`.

## 2. Thêm Handoff Layer
- **`engine/parser.py`**:
  ```diff
  + def parse_stage_response(response_text: str) -> tuple[str, str, bool]:
  +     # Regex phân tách ## Artifact và ## Handoff
  ```
- **`engine/workflow.py`**:
  ```diff
  + handoff_file = run_dir / str(step.get("handoff_output", f"{step_id}_handoff.md"))
  + write_text(handoff_file, handoff)
  ```

## 3. Tái thiết kế Editorial Workflow
- **`flow/write_blog.yaml`**:
  ```diff
  - - id: coach_agent
  + - id: editor_agent
  +   skill: skills/editor_agent.yaml
  + - id: coach_agent
  ```

## 4. Tích hợp Antigravity Bridge & Dependency Injection
- **`engine/workflow.py`**:
  ```diff
  + LlmClient = Callable[[str, dict[str, Any], str | None], str]
  
  - def run_workflow(config_path: Path, input_path: Path, dry_run: bool = False) -> Path:
  + def run_workflow(config_path: Path, input_path: Path, dry_run: bool = False, llm_client: "LlmClient | None" = None) -> Path:
  +     if llm_client is None:
  +         llm_client = call_openai
  ```
- **`engine/run_workflow.py`**:
  ```diff
  + parser.add_argument("--client", choices=["openai", "antigravity"], default="openai")
  + llm_client = call_antigravity if args.client == "antigravity" else None
  ```
- **`engine/antigravity_bridge.py`** (Mới thêm):
  ```diff
  + def call_antigravity(prompt: str, config: dict[str, Any], stage_id: str | None = None) -> str:
  +     temp_dir = Path(__file__).resolve().parents[1] / "runs" / "temp_llm"
  +     # Vòng lặp chờ file với Timeout 300s
  ```

## 5. Hỗ trợ Client Routing theo Stage
- **`engine/client_router.py`** (Mới thêm):
  ```diff
  + def create_routing_client(client_map: dict[str, str], fallback: str = "openai") -> LlmClient:
  +     # Lõi định tuyến dispatch request đến các client dựa trên stage_id
  ```
- **`engine/run_workflow.py`**:
  ```diff
  + parser.add_argument("--client-map", help="Per-stage LLM client mapping. Format: 'stage1=client,stage2=client'")
  + client_map = build_client_map(args.client_map, fallback_client_name)
  + llm_client = create_routing_client(client_map, fallback_client_name)
  ```
- **`engine/workflow.py`**:
  ```diff
  + "client_routing": getattr(llm_client, "__name__", "") == "routing_client",
  ```
- **`tests/test_client_router.py`** (Mới thêm):
  ```diff
  + # Unit tests kiểm thử build_client_map và resolve_client
  ```
