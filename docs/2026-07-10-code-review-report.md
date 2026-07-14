# Code Review Report — Mindful Blog Workflow

> **Reviewer**: Principal Code Reviewer & Solutions Architect  
> **Codebase**: `write_blog` (khởi tạo bởi Codex GPT 5.5)  
> **Ngày**: 2026-07-10

---

### 1. CHẤT LƯỢNG THIẾT KẾ SO VỚI MỤC ĐÍCH ĐẶT RA

**Đánh giá tổng: 8.5/10 — Thiết kế tốt, triển khai nhất quán, có vài điểm cần siết.**

| Khía cạnh | Đánh giá |
| :--- | :--- |
| **Workflow Architecture** | ✅ 6-stage pipeline + learning loop rõ ràng. Flow file là single source of truth cho `context_policy`. Separation of concerns tốt: YAML skills → flow graph → Python engine. |
| **Handoff Layer** | ✅ Đúng mục tiêu: tách `Artifact` (debug/review) và `Handoff` (compact context). Fallback handoff khi model quên emit `## Handoff`. Token estimation per-step. |
| **Cost Control** | ✅ 3 lớp: per-stage model selection, handoff-based context reduction, offline learning. |
| **Learning Loop** | ✅ Cả online (API) và offline (local diff). Learning dùng full artifacts, không dùng handoffs — đúng nguyên tắc. |
| **Observability** | ✅ `run_log.md`, `handoff_log.md`, `step_outputs.json`, `metadata.json` — đầy đủ audit trail. |
| **Điểm yếu chính** | ⚠️ Monolith 892 dòng, chưa module hóa. Không có retry/rate-limit. API key có thể bị hardcode trong YAML. Không validate schema YAML skill at runtime. |

---

### 2. 🔍 ĐỐI CHIẾU SỰ TUÂN THỦ (PLAN VS IMPLEMENTATION)

Đối chiếu theo Change Log trong [implementation-log.md](file:///D:/Nghiên cứu AI/write_blog/docs/2026-07-10-handoff-layer-implementation-log.md):

| Mã Task | Tên Task (Trong Plan) | Trạng thái | Ghi chú kỹ thuật nhanh |
| :--- | :--- | :--- | :--- |
| T1 | Thêm `handoff_output` & `context_policy` vào `flow/write_blog.yaml` | ✅ Đạt | Tất cả 6 step đều có `context_policy`, `handoff_output`. |
| T2 | Cập nhật skill YAML: `artifact_heading`, `handoff_heading`, handoff fields | ✅ Đạt | 6/6 main skills đã khai báo. `editorial_learning.yaml` không cần (là learning skill). |
| T3 | Engine: `parse_stage_response()` | ✅ Đạt | Regex tách `## Artifact` / `## Handoff`. Test coverage có. |
| T4 | Engine: `build_context_package()` | ✅ Đạt | Lọc đúng theo `context_policy`. Test coverage có. |
| T5 | Engine: fallback handoff khi thiếu `## Handoff` | ✅ Đạt | `truncate_words()` fallback + flag `handoff_used_fallback`. |
| T6 | Engine: ghi artifact/handoff file riêng | ✅ Đạt | `story_map.md` + `story_handoff.md` per step. |
| T7 | Engine: ghi `handoff_log.md` | ✅ Đạt | Append log per step. |
| T8 | Engine: `step_outputs.json` nested format | ✅ Đạt | Chứa artifact, handoff, metrics, fallback flag. |
| T9 | Engine: token metrics vào `metadata.json` | ✅ Đạt | `total_artifact_estimated_tokens`, `total_handoff_estimated_tokens`, per-step metrics. |
| T10 | Engine: learning loop dùng full artifacts | ✅ Đạt | `load_step_outputs_from_run()` đọc `artifact` key từ nested JSON. |
| T11 | Dry-run response có cả Artifact + Handoff | ✅ Đạt | `build_dry_run_response()` emit cả 2 section. |
| T12 | Tests: `test_handoff_parser.py` | ✅ Đạt | 3 test cases: parse, fallback, context_policy. |
| T13 | Verify: `py_compile`, `unittest`, `--dry-run`, `--offline-learning` | ✅ Đạt | Evidence trong implementation log. |
| T14 | README cập nhật handoff docs | ✅ Đạt | Mô tả artifact/handoff format, generated files, context policy. |
| — | Thư mục `runs/` cũ (trước handoff layer) | ⚠️ Sót | 4 run cũ (`20260710_170740` → `20260710_175333`) không có handoff files — là artifact từ trước khi implement. Không gây lỗi nhưng nên ghi chú hoặc dọn. |

---

### 3. ⚡ TỐI ƯU HÓA WORKFLOW & KIẾN TRÚC

- **Lỗi crash hệ thống / bảo mật nghiêm trọng:**
  1. **API key có thể bị hardcode trong YAML.** [config.example.yaml](file:///D:/Nghiên cứu AI/write_blog/engine/config.example.yaml) hỗ trợ `api_key` trực tiếp (dòng 77-79 trong engine). Nếu user đặt key vào `config.local.yaml` rồi commit → **rò rỉ key**. `.gitignore` đã exclude `config.local.yaml` nhưng không có warning trong code.
  2. **Không có timeout retry.** `urllib.request.urlopen(request, timeout=180)` — nếu API trả 429 (rate limit), engine crash ngay. Không có exponential backoff.
  3. **`SequenceMatcher` trên full blog text** ([run_workflow.py:450](file:///D:/Nghiên cứu AI/write_blog/engine/run_workflow.py#L450)) — O(n²) memory/time. Blog dài >10K từ có thể gây spike.

- **Lệch pha Data Contract:**
  1. **`future_self.yaml` có duplicate key `include`** (dòng 49 và 44). Key `include` thứ hai (`final_title`, `final_blog`, `brief_revision_notes`) ở dòng 49-52 sẽ **ghi đè** key `include` đầu tiên (dòng 44-48) theo YAML spec. Nghĩa là handoff contract thực tế bị sai so với ý đồ thiết kế.
  2. **`editorial_learning.yaml` không có `artifact_heading`/`handoff_heading`.** Đây là skill duy nhất không theo contract mới. Chấp nhận được vì nó không chạy trong pipeline chính, nhưng tạo inconsistency.

- **Trùng lặp / Thừa thãi:**
  1. **`outputs: dict[str, str] = {}` khai báo 2 lần** trong `load_step_outputs_from_run()` (dòng 707 và 712). Biến ở dòng 707 bị shadow ngay bởi dòng 712 — dead code.
  2. **4 thư mục runs cũ** (`20260710_170740` → `20260710_175333`) là artifact thừa từ quá trình phát triển, không có handoff files, format `step_outputs.json` cũ (flat string thay vì nested dict).
  3. **`output.sections` trong skill YAML trùng với `output.artifact.sections`** ở `story_architect.yaml`, `reflection_engine.yaml`, `reader_experience.yaml`, `coach_agent.yaml`. Engine không đọc `output.sections` — hoàn toàn thừa.

---

### 4. 🛠️ VECTOR TINH CHỈNH CODEBASE (REFACTOR VECTORS)

**Vector 1: YAML duplicate key gây mất dữ liệu**

- **Vị trí:** [future_self.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/future_self.yaml#L44-L52) — key `include` bị duplicate
- **Vấn đề:** Key `include` ở dòng 49-52 ghi đè key `include` ở dòng 44-48. Handoff contract bị sai.
- **Giải pháp Refactor gọn:**
```yaml
  handoff:
    description: 120-250 Vietnamese words summarizing final editorial choices for logs and learning.
    include:
      - final_editorial_intent
      - preserved_voice_choices
      - unresolved_space
      - future_learning_notes
  artifact_include:
      - final_title
      - final_blog
      - brief_revision_notes
```

---

**Vector 2: API key exposure warning**

- **Vị trí:** [run_workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/run_workflow.py#L75-L88) — hàm `get_api_key()`
- **Vấn đề:** Cho phép `api_key` trực tiếp trong YAML. Không cảnh báo khi key được hardcode.
- **Giải pháp Refactor gọn:**
```python
def get_api_key(config: dict[str, Any]) -> str:
    openai_config = config.get("openai", {})
    direct_key = openai_config.get("api_key")
    if direct_key:
        import warnings
        warnings.warn("API key is hardcoded in config. Use api_key_env instead.", stacklevel=2)
        return str(direct_key)
```

---

**Vector 3: Dead code — biến `outputs` khai báo 2 lần**

- **Vị trí:** [run_workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/run_workflow.py#L706-L712) — hàm `load_step_outputs_from_run()`
- **Vấn đề:** Dòng 707 `outputs: dict[str, str] = {}` bị shadow bởi dòng 712. Dead code.
- **Giải pháp Refactor gọn:**
```python
def load_step_outputs_from_run(run_dir: Path, workflow: dict[str, Any]) -> dict[str, str]:
    json_path = run_dir / "step_outputs.json"
    if json_path.exists():
        data = json.loads(read_text(json_path))
        if isinstance(data, dict):
            return {
                str(k): str(v.get("artifact", "")) if isinstance(v, dict) else str(v)
                for k, v in data.items()
            }
    outputs: dict[str, str] = {}
```

---

**Vector 4: Thiếu retry cho API call**

- **Vị trí:** [run_workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/run_workflow.py#L223-L231) — trong `call_openai()`
- **Vấn đề:** HTTP 429/500/503 crash ngay, không retry. Workflow 6 bước mất toàn bộ nếu 1 call tạm lỗi.
- **Giải pháp Refactor gọn:**
```python
import time

def call_openai(prompt, config, stage_id=None, max_retries=3):
    # ... existing setup code ...
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read().decode("utf-8")
            return extract_response_text(json.loads(body))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 503) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"OpenAI request failed: HTTP {exc.code}") from exc
```

---

**Vector 5: Monolith cần tách module**

- **Vị trí:** [run_workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/run_workflow.py) — 892 dòng, 1 file
- **Vấn đề:** Parser, API client, prompt builder, learning loop, CLI đều nằm chung. Khó test riêng, khó mở rộng.
- **Giải pháp Refactor gọn:** Tách thành 4 module:
```
engine/
├── __init__.py
├── cli.py            # argparse + main()
├── openai_client.py  # call_openai, get_api_key, extract_response_text
├── parser.py         # parse_stage_response, build_context_package, estimate_tokens
├── learning.py       # build_*_learning_*, build_*_tuning_*
└── workflow.py       # run_workflow, build_step_prompt
```
