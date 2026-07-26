# Lịch sử Thay đổi (Changelog)

## Phiên bản: Guided Style Voice Lab V1 & Multi-Style Production Engine (V6.0 Final) (2026-07-26)
> **Tham chiếu kế hoạch phê duyệt:**  
> - [docs/2026-07-26-guided-style-voice-lab-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-26-guided-style-voice-lab-plan-final.md)  
> - [docs/2026-07-25-multi-editable-style-upgrade-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-25-multi-editable-style-upgrade-plan-final.md)

- **Trình Quản Trị Giọng Văn Guided Style Voice Lab V1 (`engine/voice_lab/`)**:
  - Triển khai trọn vẹn gói 8 module: `models.py`, `analyzer.py`, `interview.py`, `compiler.py`, `overrides.py`, `migration.py`, `archive.py`.
  - Phân tích Voice DNA & Bằng chứng dẫn chứng (Evidence Claims) theo 12 chiều đặc trưng văn phong.
  - Xây dựng ma trận kề Adjacency Matrix (`DIMENSION_AGENTS`) để biên dịch Canonical IR thành Effective YAML.
- **Việt Hóa 100% Phỏng Vấn & A/B Calibration**:
  - Việt hóa hoàn toàn trích xuất DNA, câu hỏi phỏng vấn (`DIMENSION_VI`), và 2 bản văn mẫu A/B tương phản trong `analyzer.py` và `interview.py`.
- **Sửa Lỗi Khớp Tên File Biên Dịch (`AGENT_FILENAME_MAP`)**:
  - Khắc phục triệt me lỗi lệch tên file khi biên dịch bằng `AGENT_FILENAME_MAP` trong `compiler.py`, giúp các file skill biên dịch khớp 100% với tên file quy định bởi hợp đồng `flow/*.yaml` (`story_architect.yaml`, `writing_agent.yaml`, `sensory_capture.yaml`, `cosmic_signal_reader.yaml`...).
- **Quy Trình Xuất Bản An Toàn (Publish Safety Pipeline)**:
  - Tích hợp pipeline 4 bước trong `ui/app.py`: `Staging` -> `Contract Validation` -> `Backup` -> `Atomic Replace / Rollback`, giúp nút Publish an toàn tuyệt đối, loại bỏ nguy cơ làm hỏng hợp đồng phong cách.
- **Động Cơ Gemini API Direct Client (`engine/gemini_client.py`)**:
  - Thêm client kết nối trực tiếp đến Gemini API (`gemini-3.5-flash`), hỗ trợ router gán client động per-stage.
- **Thực Hiện Viết Thực Tế Qua Antigravity Bridge Local Quota (`--client antigravity`)**:
  - Chạy thành công workflow Moment mode với style `va-natural` (Vân Anh Natural) bằng Local Model Quota (`examples/moment_1.md`), tạo ra bản blog khoảnh khắc đạt tiêu chuẩn chất lượng cao.
- **Bộ Kiểm Thử Hợp Đồng & Zero-Cost Smoke Test (`tests/test_voice_lab.py`)**:
  - Thêm test suite kiểm thử 100% độ phủ ma trận kề `DIMENSION_AGENTS` và công cụ smoke test kiểm chứng độ phủ từ khóa không tốn API quota.

## Phiên bản: Hệ Thống Quản Trị & Nâng Cấp Phong Cách Viết Đa Năng (Multi-Editable-Style V5.0 Final) (2026-07-25)
> **Tham chiếu kế hoạch phê duyệt:** [docs/2026-07-25-multi-editable-style-upgrade-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-25-multi-editable-style-upgrade-plan-final.md)

- **Phân cấp Không gian tên 2 Chiều (`skills/<mode>/<slug>/`)**:
  - Di dời toàn bộ kỹ năng theo ma trận `Mode x Style`: `skills/deep/reflective/`, `skills/deep/provocative/`, và `skills/moment/reflective/`.
  - Thiết lập cơ chế bảo vệ (`is_protected: true`) trong `style_meta.yaml` cho các phong cách hệ thống.
  - Giữ nguyên `skills/editorial_learning.yaml` tại gốc `skills/` (Immutable System Exception).
- **Style Service & Backend Layer (`engine/style_manager.py`)**:
  - Triển khai trọn vẹn 6 API CRUD (`list_styles`, `get_style_detail`, `save_style_file`, `create_style`, `rename_style`, `delete_style`).
  - Tích hợp Trình kiểm duyệt YAML theo Nhóm 2 Tầng (2-Tier Group-Based Validator), phân loại Hard Check theo nhóm A/B/Moment để tránh báo lỗi sai và Soft Warning cảnh báo thiếu guardrails.
  - Đảm bảo an toàn I/O tuyệt đối: Slug Allowlist Regex, Atomic Write (`.tmp` + `os.replace`), và cơ chế Rollback (`shutil.rmtree`) khi lỗi nhân bản.
  - Tích hợp hệ thống Quản lý Bí danh (`previous_slugs`) tự động giải quyết ánh xạ slug khi đổi tên style cho cả workflow lẫn learning loop.
- **Strict Discovery & Fail-Fast Routing (`engine/workflow.py` & `run_workflow.py`)**:
  - Loại bỏ hoàn toàn cơ chế "silent fallback" âm thầm chuyển về style `reflective`.
  - Quét hợp đồng Flow YAML (`flow/*.yaml`) để xác minh folder style buộc phải chứa đủ 100% file skill, báo lỗi Fail-Fast ngay lập tức nếu vi phạm.
- **Streamlit Local UI Experience (`ui/app.py` & `ui/styles.css`)**:
  - Xây dựng giao diện Dark Theme cao cấp (Slate Gray, Warm Gold, Electric Cyan) với 4 Tab chuyên biệt.
  - **Style Gallery**: Khám phá danh sách Card UI, khóa nút xóa với System Style, tích hợp Modal Đổi tên Style.
  - **Style Studio**: Hỗ trợ Manual Clone style V1 mượt mà.
  - **YAML Code Editor**: Tích hợp `streamlit-code-editor` kèm tự động fallback sang `st.text_area` monospace, Live Validator Alert hiển thị lỗi/warning khi lưu.
  - **Live Workbench**: Chạy kiểm chứng hợp đồng Flow và định tuyến mô phỏng trong 1-2 giây không tốn API quota.
- **Kiểm Thử Hồi Quy Toàn Diện**:
  - Cập nhật test suites `test_workflow_contract.py` và `test_moment_blog_mode.py` cho cấu trúc namespace mới.
  - Xây dựng bộ unit test mới `tests/test_style_manager.py` kiểm thử 100% CRUD API, Validator, Alias Wiring và Rollback.

## Phiên bản: Hệ Hai Writing Modes (Dual Writing Modes System) (2026-07-22)
> **Tham chiếu kế hoạch phê duyệt:** [docs/2026-07-22-mindful_writing_os-two-writing-modes-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-22-mindful_writing_os-two-writing-modes-final.md)

- **Hệ Thống Hai Chế Độ Viết (`deep_blog_mode` & `moment_blog_mode`)**:
  - Tách biệt hai quy trình: bài viết dài phản tư sâu (1000-1500 từ) và bài viết ngắn khoảnh khắc (300-600 từ).
- **Tạo 6 Skill YAML Cho Moment Mode (`skills/moment/reflective/`)**:
  - `sensory_capture.yaml`: Ghi nhận cảnh vật, âm thanh, cảm giác thân thể.
  - `inner_weather.yaml`: Gọi tên thời tiết bên trong gắn với biểu hiện cơ thể.
  - `cosmic_signal_reader.yaml`: Lắng nghe tín hiệu trực giác nhỏ có căn cứ.
  - `moment_writer.yaml`: Viết nháp ngắn (300-600 từ) giữ năng lượng hiện tại.
  - `breath_editor.yaml`: Cắt gọt nhẹ nhàng, làm bài thở ra.
  - `gentle_witness.yaml`: Ghi nhận điềm tĩnh độ tươi mới của bài viết.
- **Tạo & Tối Ưu Flow YAML (`flow/`)**:
  - Thêm `flow/write_moment_blog.yaml` định nghĩa quy trình 6 bước cho Moment Blog.
  - Thêm `mode: deep` vào `flow/write_blog.yaml` và loại bỏ file flow trùng lặp (`flow/write_deep_blog.yaml`).
- **Nâng Cấp Engine & CLI (`engine/`)**:
  - `run_workflow.py`: Bổ sung tham số `--mode deep|moment` (mặc định `deep`), kiểm tra cờ `--mode` linh hoạt, tự động fallback `moment+provocative -> reflective`.
  - `workflow.py`: Định tuyến flow động (`resolve_workflow_file`), nạp skill theo mode/style (`resolve_step_skill_path`), đơn giản hóa `derive_artifact_file_contents`.
  - `learning.py`: Tách biệt báo cáo learning theo mode (`learning/<mode>/<timestamp>/`), đặt tên file kết quả dạng `deep_blog_patterns.md` và `moment_blog_patterns.md`.
  - `config.example.yaml`: Thêm cấu hình token/temperature riêng cho 6 agent của Moment Mode.
- **Kiểm Thử & Documentation**:
  - Thêm `examples/moment_blog_input_template.md` làm mẫu đầu vào cho Moment mode.
  - Thêm `tests/test_moment_blog_mode.py` với 8 test cases phủ hợp đồng flow, resolution, dry-run, offline learning, và kiểm thử chung 1 input cho cả 2 mode.
  - Cập nhật `README.md` với đầy đủ tài liệu hướng dẫn hai chế độ viết.

## Phiên bản: Đa Phong Cách Multi-Style Architecture (2026-07-20)
- **Tái Cấu Trúc Thư Mục Skill (`skills/`)**:
  - Tạo `skills/reflective/` lưu 7 agent YAML gốc (Style 1 mặc định).
  - Tạo `skills/provocative/` lưu 7 agent YAML với phong cách gai góc, khiêu khích (Style 2) cùng `STYLE_BRIEF.md`.
  - Giữ `skills/editorial_learning.yaml` ở root thư mục `skills/` do logic học tập độc lập với phong cách viết.
- **Dynamic Skill Path Resolution (`engine/workflow.py`)**:
  - Tự động nạp file skill theo phong cách: `Path(step["skill"]).parent / style / Path(step["skill"]).name`.
  - Ghi thông tin `"style"` vào `metadata.json` và tên thư mục chạy dạng `{timestamp}_{style}_{slug}`.
- **CLI & Validation (`engine/run_workflow.py`)**:
  - Thêm cờ `--style` với cơ chế fail-fast kiểm tra sự tồn tại của thư mục style.
  - Hỗ trợ trích xuất tự động `style` từ `metadata.json` khi chạy `--learn-from-run`.
- **Kiểm Thử Multi-Style (`tests/test_workflow_contract.py`)**:
  - Parametrize kiểm thử hợp đồng dữ liệu cho toàn bộ các phong cách (`reflective`, `provocative`).

## Phiên bản: Prompt Caching & Token Optimization (2026-07-15)
- **Tối ưu Hóa Token đầu vào (`flow/write_blog.yaml`)**:
  - Thêm cờ `needs_author_input: false` cho stage `reader_experience`. Điều này cắt bỏ khối lượng lớn bản nháp thô khỏi "độc giả mù", vừa tiết kiệm token, vừa đảm bảo tính chân thực (blind reading).
- **Cấu trúc Prompt Caching (`engine/workflow.py`)**:
  - Chia tách `build_step_prompt` thành Static Prefix (Phần tĩnh) và Dynamic Suffix (Phần động).
  - Tối ưu vị trí của `Instruction` và `Author Input` lên đầu để tận dụng Prefix Hashing trên OpenAI/Anthropic API, có khả năng tiết kiệm lên đến 90% chi phí cho các phần lặp lại.
  - Tối ưu vị trí của `Skill YAML` xuống phần kết thúc prompt, tận dụng triệt để "Recency Bias" nhằm nâng cao độ tuân thủ của LLM.

## Phiên bản: Hỗ trợ Client Routing theo Stage (2026-07-15)
- **Client Router (`engine/client_router.py`)**: Thêm module định tuyến, cho phép gán LLM Client (openai, antigravity) riêng biệt cho từng Stage.
- **Mở rộng CLI (`run_workflow.py`)**: Bổ sung tham số `--client-map` để override client cho các Stage cụ thể (VD: `--client-map "story_architect=antigravity"`), với `--client` đóng vai trò fallback.
- **Metadata Logging**: Cập nhật file `metadata.json` thêm trường `client_routing` để theo dõi việc sử dụng Router.
- **Kiểm thử**: Viết thêm `tests/test_client_router.py` để đảm bảo độ tin cậy của bộ định tuyến mới.

## Phiên bản: Tích hợp Antigravity & Hoàn thiện Refactoring (2026-07-14)
- **Dependency Injection (DI)**: Bổ sung khả năng DI `LlmClient` cho hàm `run_workflow.py` và `engine/workflow.py`, giúp cô lập toàn toàn luồng xử lý LLM.
- **Antigravity Bridge**: Thêm `engine/antigravity_bridge.py` để giao tiếp với model Antigravity cục bộ thông qua cơ chế đọc/ghi file tạm thời (`temp_llm`). Xóa bỏ logic fallback hỗn tạp cũ từ `openai_client.py`.
- **Bảo mật và Tính ổn định**: 
  - Khởi tạo timeout 300 giây cho file-bridge để chống treo hệ thống.
  - Bổ sung `provider` string (`openai` hoặc `antigravity`) vào metadata để tăng tính minh bạch.
  - Chuyển TypeAlias `LlmClient` theo đúng chuẩn PEP 8.
- **Kiểm thử**: Viết thêm `tests/test_antigravity_bridge.py` với Mock Object giả lập đầy đủ luồng file I/O và Timeout.

## Phiên bản: Tái thiết kế Editorial Workflow (2026-07-14)
- **Phân định ranh giới tác vụ**: Tổ chức lại hệ thống Agent theo triết lý "Mỗi agent bảo vệ một chân lý và không trả lời thay câu hỏi của agent khác".
- **Agent mới (`editor_agent`)**: Đóng vai trò là Biên tập viên kết nối, đứng ngay sau `reader_experience`.
- **Cập nhật Skill YAML**: 
  - `writing_agent` trở thành Ghost Writer tạo bản nháp trung thành.
  - `reader_experience` trở thành Sổ tay độc giả (không phán xét hay đề xuất sửa lỗi).
  - `coach_agent` phân tích sâu các điểm mù sau khi bản nháp đã được edit.
  - `future_self` chỉ đưa ra quan sát tương lai, trả quyền quyết định bài viết cuối (`final_blog.md`) lại cho người viết.
- **Hỗ trợ Secondary Artifact**: Bổ sung cơ chế để sinh ra các file nhật ký phụ (như `edit_log.md` song song với `edited_blog.md`).

## Phiên bản: Engine Modularization (2026-07-10)
- **Tách Monolith**: Đập bỏ file script 892 dòng duy nhất thành các module con `utils.py`, `parser.py`, `openai_client.py`, `learning.py`, `workflow.py`.
- **Cơ chế Retry (Exponential Backoff)**: Thêm retry cho OpenAI Client khi gặp mã lỗi 429, 500, 503.
- **Bảo mật API Key**: Hiển thị UserWarning nếu nhúng cứng API Key thay vì dùng biến môi trường.
- **Chuẩn hóa YAML**: Sửa lại các key cấu trúc trong `future_self.yaml` cho đồng bộ với dự án (`sections`).

## Phiên bản: Handoff Layer (2026-07-10)
- **Artifact vs Handoff**: Thiết lập yêu cầu tách biệt hai luồng đầu ra cho mọi agent.
  - `Artifact`: Đầy đủ, lưu để audit và learning.
  - `Handoff`: Dạng nén gọn (120-250 từ), dùng làm input cho các bước tiếp theo.
- **Context Policy**: Chuyển mọi quyết định truyền Context vào file `write_blog.yaml`, thay vì code logic trong Python.
- **Cơ chế Fallback**: Đề phòng trường hợp AI sinh thiếu cấu trúc Handoff, hệ thống sẽ fallback an toàn thay vì crash.
- Tự động sinh `handoff_log.md` và theo dõi metrics qua `step_outputs.json` và `metadata.json`.
