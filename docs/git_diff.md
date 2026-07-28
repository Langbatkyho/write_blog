# Tổng hợp Git Diff và Thay đổi Code

## 12. P1 Architecture Hardening (2026-07-28)

- `ea7d08d`: UI acceptance; widget editor/workbench được namespace theo mode.
- `9a003ee`: strict `Artifact/Handoff`; Gemini model resolver dùng chung cho telemetry và request.
- `bebd980`: validate toàn style staging và alias namespace trước transaction commit.
- `7d2576d`: Voice Lab strict models; migration v1 tách khỏi runtime contract.
- Test tăng từ 111 lên **120**, toàn bộ pass; không gọi API thật; `runs/` bất biến.

## 11. Gemini 3.5 Flash High Thinking Mode & Profile DNA Extraction (2026-07-27)

### 1. Trích xuất & Cố định Dữ liệu Trung gian Voice Lab (`profile_dna.json`)
- **`ui/app.py`**:
  ```diff
  + # Save intermediate analysis & Voice DNA log
  + profile_log = {
  +     "name": st.session_state.vl_style_name,
  +     "slug": slug,
  +     "mode": mode,
  +     "updated_at": meta["updated_at"],
  +     "dna": st.session_state.vl_dna.model_dump() if st.session_state.vl_dna else {},
  +     "evidence": [c.model_dump() for c in st.session_state.vl_claims] if st.session_state.vl_claims else [],
  +     "interview_answers": st.session_state.vl_answers,
  +     "calibration_selected": st.session_state.vl_calibration.get("selected"),
  + }
  + write_text(staging_dir / "profile_dna.json", json.dumps(profile_log, ensure_ascii=False, indent=2))
  ```
- **`skills/moment/va-natural/profile_dna.json`** (File mới):
  Lưu vĩnh viễn cấu trúc Voice DNA (12 chiều), Evidence Claims (quotes, confidence), và danh sách quy tắc biên dịch 6 agents của phong cách Vân Anh Natural (Moment mode).

### 2. Kích hoạt Chế độ tư duy High cho Gemini 3.5 Flash (`thinking_budget=1024`)
- **`engine/gemini_client.py`**:
  ```diff
  + try:
  +     from google import genai
  +     from google.genai import types
  +     _HAS_GENAI_SDK = True
  + except ImportError:
  +     _HAS_GENAI_SDK = False

  - def call_gemini(..., max_retries: int = 3) -> str:
  + def call_gemini(..., thinking_budget: int = 1024, max_retries: int = 3) -> str:
  +     # Strategy 1: google.genai SDK
  +     gen_config = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_output_tokens)
  +     if thinking_budget and thinking_budget > 0:
  +         gen_config.thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
  +     # Strategy 2: REST API fallback
  +     if thinking_budget and thinking_budget > 0:
  +         generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
  -     print(f"[GEMINI] ✅ Response received ({len(result)} chars)")
  +     print(f"[GEMINI] [OK] Response received ({len(result)} chars)")  # Sửa UnicodeEncodeError
  ```

## 10. Voice Lab Schema v2 & Fail-Closed Refactor (2026-07-27)

> **Tham chiếu:** [docs/2026-07-27-voice-lab-refactor-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-27-voice-lab-refactor-plan-final.md)

### Schema và compatibility

- **`engine/voice_lab/models.py`**:
  ```diff
  - VoiceDNA: 12 trường str phẳng
  + VoiceDNA: 12 trường DimensionProfile
  + schema_version = 2
  + revision, analysis_status, warnings, interview_history, calibration_history
  + AnalysisResult / AnalysisError / CompileResult / MergeResult / PublishResult
  + compute_profile_confidence(profile)
  ```
- `EvidenceClaim.quote` được migrate sang `exact_quote`; active evidence bắt buộc truy được về `sample_id`.
- Canonical IR chỉ giữ invariant snapshot, overlays và `effective_skill`; xóa `prompt`/`style_rules` phẳng, cấm field ngoài contract.
- `migration.py` đọc v1 idempotent; legacy thiếu evidence trả `dna=None`, `incomplete_legacy_data`, draft.

### Gemini analysis và prompt

- **Thêm mới**:
  - `engine/voice_lab/prompts.py`: prompt builder và JSON response schemas.
  - `engine/voice_lab/parser.py`: strict parse, exact-quote validation và confidence deterministic.
- **`engine/voice_lab/analyzer.py`**:
  ```diff
  - nối sample trực tiếp + parse JSON thủ công + fallback DNA giả
  + JSON-serialize untrusted samples
  + structured Gemini output
  + adaptive single-pass / multi-pass theo token
  + fail-closed AnalysisError
  + confidence = 0.45*coverage + 0.35*consistency + 0.20*quote_validity
  ```
- **`engine/gemini_client.py`** chuyển `response_mime_type` và JSON schema cho cả SDK/REST, vẫn dùng retry/backoff/key rotation tập trung tại client.

### Interview, A/B và compile

- Interview chỉ chọn tối đa 3 dimension yếu; patch cần người dùng xác nhận trước khi sửa profile.
- A/B lưu hidden `shuffle_mapping`; lựa chọn cập nhật strength/examples/history. Prompt nhắm `100–150` từ, validator cho dung sai `90–165`.
- Compiler bỏ base discovery bằng `iterdir()`, dùng `base_style_slug` xác định và full-template overlay.
- Contract scalar legacy được chuẩn hóa thành `{"reference": ...}`; invariant skill/IR được đặt tên và kiểm tra riêng.
- Overrides trả conflict explicit; không còn comment giả “LLM resolved”.

### Archive, publish và UI

- **Thêm `engine/voice_lab/publisher.py`**:
  ```text
  unique staging -> YAML/workflow/invariant validation -> immutable backup
  -> tombstone atomic replace -> rollback/cleanup
  ```
- Chặn profile chưa complete/confirmed và chặn ghi đè protected system style.
- Archive manifest v2 kiểm checksum/path traversal, migrate v1 trong bộ nhớ và reject future schema.
- `ui/app.py` dùng service mới; interview/A-B cập nhật profile thật; đổi mode sẽ reset Voice Lab session để tránh compile chéo Deep/Moment.

### Kiểm thử

- `tests/test_voice_lab.py`: 37 test cho schema, migration, injection, malformed output, Gemini JSON schema, quote, confidence, adaptive routing, interview, A/B, compiler, override, archive, Deep/Moment publish và rollback.
- Kết quả toàn dự án: **81/81 test pass**; Streamlit AppTest **0 exception**; `compileall` và `git diff --check` đạt.

## 9. Guided Style Voice Lab V1 & Multi-Style Production Engine (2026-07-26)
> **Tham chiếu kế hoạch phê duyệt:**  
> - [docs/2026-07-26-guided-style-voice-lab-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-26-guided-style-voice-lab-plan-final.md)  
> - [docs/2026-07-25-multi-editable-style-upgrade-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-25-multi-editable-style-upgrade-plan-final.md)

- **`engine/voice_lab/` (Package mới 8 modules)**:
  ```python
  # models.py: StyleProfile, VoiceDNA, EvidenceClaim, CanonicalIR, sanitize_sample
  # analyzer.py: analyze_samples(samples) -> VoiceDNA, EvidenceClaims (100% tiếng Việt)
  # interview.py: generate_interview(profile), calibrate_ab(dimension, profile), DIMENSION_VI (100% tiếng Việt)
  # compiler.py: compile_style(profile, mode), DIMENSION_AGENTS, AGENT_FILENAME_MAP
  # overrides.py: merge_overrides(base_ir, overrides_ir)
  # migration.py: import_existing_style(mode, slug)
  # archive.py: export_voice_style_archive, import_voice_style_archive (.voice-style.zip SHA-256)
  ```
- **`engine/voice_lab/compiler.py`**:
  ```diff
  + AGENT_FILENAME_MAP = {
  +     "story_architect": "story_architect.yaml",
  +     "reflection_engine": "reflection_engine.yaml",
  +     "writing_agent": "writing_agent.yaml",
  +     "reader_experience": "reader_experience.yaml",
  +     "editor_agent": "editor_agent.yaml",
  +     "coach_agent": "coach_agent.yaml",
  +     "future_self": "future_self.yaml",
  +     "sensory_capture": "sensory_capture.yaml",
  +     "inner_weather": "inner_weather.yaml",
  +     "cosmic_signal_reader": "cosmic_signal_reader.yaml",
  +     "moment_writer": "moment_writer.yaml",
  +     "breath_editor": "breath_editor.yaml",
  +     "gentle_witness": "gentle_witness.yaml",
  + }
  ```
- **`ui/app.py`**:
  ```diff
  + from engine.voice_lab.interview import DIMENSION_VI, generate_interview, calibrate_ab
  + from engine.voice_lab.compiler import compile_style
  + # Tích hợp 5-Step Guided Voice Lab Wizard & Publish Safety Pipeline (Staging -> Validate -> Backup -> Atomic Replace / Rollback)
  ```
- **`engine/gemini_client.py` (Mới thêm)**:
  ```python
  # Giao tiếp Gemini API trực tiếp bằng GEMINI_API_KEY với model default gemini-3.5-flash
  ```
- **`engine/client_router.py`**:
  ```diff
  + register_client("gemini", call_gemini)
  ```
- **`tests/test_voice_lab.py` (Mới thêm)**:
  ```python
  # Contract Test: test_adjacency_matrix_coverage (100% coverage)
  # Zero-cost Smoke Test: test_zero_cost_smoke_test (keyword search & invariant diffs)
  ```
- **`skills/moment/va-natural/*.yaml` (Style tùy biến mới)**:
  ```yaml
  # Cấu hình 6 agent YAML cho phong cách Vân Anh Natural (Moment Mode)
  ```

## 8. Hệ Hai Writing Modes (Dual Writing Modes System) (2026-07-22)
> **Tham chiếu kế hoạch phê duyệt:** [docs/2026-07-22-mindful_writing_os-two-writing-modes-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-22-mindful_writing_os-two-writing-modes-final.md)

- **`flow/write_moment_blog.yaml`** (Mới thêm):
  ```yaml
  name: mindful_moment_blog_workflow
  mode: moment
  # Khai báo quy trình 6 bước: sensory_capture -> inner_weather -> cosmic_signal_reader -> moment_writer -> breath_editor -> gentle_witness
  ```
- **`flow/write_blog.yaml`**:
  ```diff
    name: mindful_blog_workflow
  + mode: deep
    description: >
  ```
- **`skills/moment/reflective/*.yaml`** (Mới thêm 6 file skills chuẩn hóa):
  ```yaml
  # sensory_capture.yaml, inner_weather.yaml, cosmic_signal_reader.yaml, moment_writer.yaml, breath_editor.yaml, gentle_witness.yaml
  name: <skill_name>
  mode: moment_blog_mode
  purpose: ...
  output:
    artifact: <file.md>
    handoff: ...
  ```
- **`engine/run_workflow.py`**:
  ```diff
  + parser.add_argument("--mode", choices=["deep", "moment"], default="deep")
  + if mode == "moment" and style == "provocative":
  +     print("[WARNING] Moment mode does not support provocative style. Falling back to 'reflective'.", file=sys.stderr)
  +     style = "reflective"
  + explicit_mode = args.mode if any(a.startswith("--mode") for a in sys.argv) else None
  ```
- **`engine/workflow.py`**:
  ```diff
  + def resolve_workflow_file(config: dict[str, Any], mode: str) -> Path:
  +     if mode == "moment": return resolve_path("flow/write_moment_blog.yaml")
  +     return resolve_path("flow/write_blog.yaml")
  +
  + def resolve_step_skill_path(step: dict[str, Any], style: str, mode: str) -> Path:
  +     if mode == "moment": return resolve_path(f"skills/moment/{style}/{original_path.name}")
  ```
- **`engine/learning.py`**:
  ```diff
  + report_name = f"{mode}_blog_patterns.md"
  + learning_dir = run_dir / "learning" / mode / timestamp
  ```
- **`engine/config.example.yaml`**:
  ```diff
  +   # Moment mode stages
  +   sensory_capture: { model: gpt-4.1-mini, temperature: 0.3, max_output_tokens: 1500 }
  +   ...
  ```
- **`tests/test_moment_blog_mode.py`** (Mới thêm):
  ```python
  # 8 test cases kiểm thử hợp đồng flow, mode routing, dry-run, offline learning, và cùng 1 input chạy cả 2 mode.
  ```

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

## 6. Prompt Caching & Token Optimization
- **`flow/write_blog.yaml`**: Loại bỏ input gốc khỏi reader mù.
  ```diff
    - id: reader_experience
      skill: skills/reader_experience.yaml
      purpose: Record a blind first-time reader diary without editing or diagnosing.
      output: reader_report.md
      handoff_output: reader_handoff.md
  +   needs_author_input: false
      context_policy:
  ```
- **`engine/workflow.py`**: Đẩy toàn bộ cấu trúc tĩnh (author_input, config) lên cực trên tạo thành Static Prefix, tách biệt Dynamic Context để tối đa hóa Prefix Hashing trên API.
  ```diff
  - return textwrap.dedent(
  -     f"""
  -     You are running one step of an automated reflective blog workflow.
  -     ...
  -     """
  - ).strip()
  + prompt_parts = []
  + prompt_parts.append("You are running one step of an automated reflective blog workflow.")
  + prompt_parts.append(f"Workflow name: {workflow.get('name')}")
  + prompt_parts.append(f"Workflow description: {workflow.get('description')}")
  + 
  + if step.get("needs_author_input", True):
  +     prompt_parts.append(f"Author input:\\n```markdown\\n{author_input}\\n```")
  + ...
  + return "\\n\\n".join(prompt_parts)
  ```

## 7. Đa Phong Cách Multi-Style Architecture (2026-07-20)
- **`engine/run_workflow.py`**:
  ```diff
  + parser.add_argument("--style", default=None, help="The writing style to use (e.g., reflective).")
  + if args.style is not None:
  +     style_dir = resolve_path(f"skills/{args.style}")
  +     if not style_dir.is_dir():
  +         raise ValueError(...)
  ```
- **`engine/workflow.py`**:
  ```diff
  - skill_path = resolve_path(step["skill"])
  + original_path = Path(step["skill"])
  + styled_path = original_path.parent / style / original_path.name
  + skill_path = resolve_path(str(styled_path))
  
  + "style": style,  # Ghi thông tin phong cách vào metadata.json
  ```
- **`tests/test_workflow_contract.py`**:
  ```diff
  - reader_skill = load_yaml("skills/reflective/reader_experience.yaml")
  + for style in ["reflective", "provocative"]:
  +     reader_skill = load_yaml(f"skills/{style}/reader_experience.yaml")
  ```
- **Thư mục `skills/`**:
  - Tạo `skills/reflective/` chứa 7 file YAML gốc.
  - Tạo `skills/provocative/` chứa 7 file YAML đã tinh chỉnh kèm `STYLE_BRIEF.md`.
