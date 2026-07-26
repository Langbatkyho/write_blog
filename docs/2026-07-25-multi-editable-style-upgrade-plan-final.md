# Kế hoạch Triển khai Multi-Editable-Style (User-Control-Style Đa Chế Độ) - Bản Chuẩn Chung Cuộc (Final Specification V5.0)

> **Ngày tài liệu:** 2026-07-25  
> **Phiên bản:** 5.0 - FINAL (Bản Hợp nhất Chuẩn Chung cuộc tối hậu từ 3 vòng phản biện giữa Gemini 3.1 Pro, Claude Opus 4.6 & GPT-5.6 Sol)  
> **Mục tiêu:** Xây dựng nền tảng quản lý phong cách viết (Style Manager) đa chế độ (`deep_blog` và `moment_blog`) trên giao diện trực quan Streamlit Local UI dành cho 1 người dùng, bảo toàn 100% tính tương thích ngược, an toàn I/O tuyệt đối và không gây regression.

---

## 1. TỔNG QUAN KIẾN TRÚC & CÁC QUYẾT ĐỊNH THỐNG NHẤT (ADRs)

Tài liệu này là đặc tả kỹ thuật chính thức và tối hậu, chắt lọc toàn bộ tinh hoa từ 3 vòng phản biện chuyên sâu. Toàn bộ hội đồng chuyên gia đã đạt sự đồng thuận tuyệt đối trên dữ liệu code thực tế thông qua 5 Quyết định Kiến trúc (ADRs) bất khả xâm phạm sau đây:

### ADR-1: Mô hình Dữ liệu cho 1 Người dùng & Đấu nối Bí danh (Single-User Namespacing & Alias Wiring)
* **Quyết định**: Loại bỏ hoàn toàn cơ chế đăng nhập, quản lý user ID và phân quyền author phức tạp. Hệ thống phục vụ 1 người dùng duy nhất làm chủ toàn bộ không gian style.
* **Cấu trúc lưu trữ chuẩn hóa**: `skills/<mode>/<style_slug>/`
* **File định danh metadata (`style_meta.yaml`)**: Chứa các trường bắt buộc: `name`, `slug`, `mode`, `description`, `created_at`, `updated_at`, `is_protected` (khóa bảo vệ system style), và **`previous_slugs`**.
* **Đấu nối Bí danh (Alias Wiring)**: Mảng `previous_slugs` không phải metadata chết mà được tích hợp thực thi trực tiếp vào `run_workflow.py` và `learning.py`. Khi hệ thống tìm kiếm style theo slug từ lịch sử `runs/`, nếu không thấy folder trùng slug, Resolver tự động quét trường `previous_slugs` trong tất cả `style_meta.yaml` để định tuyến chính xác về folder style mới nhất mà không cần sửa chữa I/O các bản ghi cũ.

### ADR-2: Bộ định tuyến Strict Khám phá Động từ Flow (Dynamic Strict Resolver - Single Source of Truth)
* **Quyết định**: Chấm dứt hoàn toàn cơ chế fallback âm thầm giữa các style (chống rủi ro "trộn style" lai tạp văn phong). Tháo gỡ 2 điểm nghẽn hardcode tại `engine/workflow.py` và `engine/run_workflow.py`.
* **Thuật toán Khám phá Strict (Strict Discovery)**: Khi chạy workflow cho một mode (`deep` hoặc `moment`) và style `slug`:
  1. Đọc file hợp đồng Flow YAML tương ứng (`flow/write_blog.yaml` hoặc `flow/write_moment_blog.yaml`).
  2. Chiết xuất danh sách toàn bộ các file skill `.yaml` trong block `step[].skill` (7 file cho Deep, 6 file cho Moment).
  3. Kiểm tra folder `skills/<mode>/<style_slug>/` buộc phải chứa đủ 100% các file này.
  4. Nếu thiếu dù chỉ 1 file hoặc style không tồn tại -> **Báo lỗi Fail-Fast ngay lập tức**, từ chối thi hành, tuyệt đối không âm thầm fallback về style `reflective`.

### ADR-3: Nguyên tắc File Bất khả xâm phạm (Immutable System Exceptions)
* **Quyết định**: File `skills/editorial_learning.yaml` là cấu hình học tập từ phản hồi biên tập (Learning Loop), hoàn toàn độc lập với phong cách viết bài. File này vĩnh viễn được giữ nguyên tại root `skills/` và bị loại trừ (excluded) khỏi toàn bộ các logic quét thư mục hay phân giải style.

### ADR-4: Phạm vi Giao diện Streamlit V1 & Bàn Kiểm chứng Hợp đồng (Streamlit UI V1 & Contract Workbench)
* **Quyết định**: Xây dựng ứng dụng Local UI bằng **Streamlit** (`ui/app.py` & `ui/styles.css`), tích hợp `streamlit-code-editor` (kèm cơ chế tự động chuyển sang `st.text_area` font monospace nếu lỗi dependency) trên nền Dark Theme hiện đại (Slate Gray, Warm Gold, Electric Cyan).
* **Chốt Phạm vi V1 Thực dụng**: Tách biệt rõ ràng tính năng V1 và V1.1 nhằm bảo đảm hệ thống chạy mượt mà, không lỗi:
  * **Các tính năng V1**: Style Gallery theo mode, Tạo style mới bằng Clone thủ công từ `reflective`, Sửa tên hiển thị (`name`), Sửa slug của custom style (khóa slug của system style), Code Editor sửa YAML + Fallback, Xóa custom style (khóa xóa system style), và **Tab 4 Dry-Run Contract Test**.
  * **Tái định vị Tab 4 (Dry-Run Contract Test)**: Trang bị 1 nút bấm **"🧪 Kiểm tra Hợp đồng Định tuyến (Dry-Run Test)"** (~25 dòng code wrapper gọi `run_workflow(..., dry_run=True)`). Bản chất là mô phỏng kiểm thử I/O, kiểm chứng style vừa tạo/sửa có đủ file hợp lệ và định tuyến thành công hay không trong 1-2 giây mà không tốn API quota hay gây treo Streamlit. (Không quảng cáo là "xem trước bài viết thật").
  * **Dời sang V1.1**: Tính năng AI Style Generator và Real Engine Execution trên UI chính thức được chuyển sang Giai đoạn V1.1.

### ADR-5: Kiểm duyệt YAML theo Nhóm Schema & An toàn I/O (Group-Based Validator & I/O Safety)
* **Quyết định 5.1 (YAML Validator theo Nhóm Schema Thực tế)**: Chấm dứt sai lầm áp đặt key `tasks` cho toàn hệ thống dựa trên xác minh code thực tế:
  * **Universal Hard Check** (áp dụng cho cả 13 agents): File YAML cú pháp hợp lệ + tồn tại key `name` (giá trị khớp tên file) + tồn tại key `output`.
  * **Specific Hard Check theo Nhóm**:
    * *Group Deep A* (`story_architect`, `reflection_engine`, `coach_agent`, `future_self`): Bắt buộc có root key `tasks`.
    * *Group Deep B* (`writing_agent`, `reader_experience`, `editor_agent`): Bắt buộc có root key `supreme_rule`.
    * *Moment Mode* (cả 6 agents): Bắt buộc có root key `tasks`.
  * **Soft Warning**: Phát ra cảnh báo màu vàng trên UI nếu file thiếu các từ khóa bảo vệ chống hallucination: `do_not` (Moment) hoặc `rules`/`style_rules` (Deep), nhưng vẫn cho phép lưu file.
* **Quyết định 5.2 (An toàn I/O & Rollback)**:
  * **Slug Sanitization & Guardrails**: Áp dụng allowlist regex `^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$` cho mọi slug. Chặn triệt để directory traversal (`../../`).
  * **Atomic Writes**: Khi lưu file YAML hay metadata, ghi vào file tạm `.tmp` rồi sử dụng `os.replace` để bảo đảm tính toàn vẹn I/O.
  * **Rollback on Failure**: Khi Clone hoặc Rename style gặp lỗi giữa chừng, tự động dọn dẹp và khôi phục trạng thái ban đầu (`shutil.rmtree` folder lỗi).

---

## 2. BẢNG THIẾT KẾ CẤU TRÚC LƯU TRỮ & DỮ LIỆU CHUẨN

```text
skills/
├── editorial_learning.yaml   # [IMMUTABLE] Độc lập mode/style
├── deep/                     # Không gian style cho Deep Mode (7 Agents)
│   ├── reflective/           # Style hệ thống mặc định (is_protected: true)
│   │   ├── style_meta.yaml   # File định danh metadata
│   │   ├── story_architect.yaml
│   │   └── ... (6 file YAML khác)
│   ├── provocative/          # Style hệ thống gai góc (is_protected: true)
│   │   ├── style_meta.yaml
│   │   ├── STYLE_BRIEF.md    # [MIGRATED INTACT] Bảo toàn file brief hiện có
│   │   └── ... (7 file YAML)
│   └── custom-deep-style/    # Style tự tạo của người dùng (is_protected: false)
│       ├── style_meta.yaml
│       ├── STYLE_BRIEF.md
│       └── ...
└── moment/                   # Không gian style cho Moment Mode (6 Agents)
    ├── reflective/           # Style hệ thống mặc định (is_protected: true)
    │   ├── style_meta.yaml
    │   └── ... (6 file YAML)
    └── zen-minimalist/       # Style tự tạo cho khoảnh khắc tối giản
        ├── style_meta.yaml
        ├── STYLE_BRIEF.md
        └── ...
```

### Đặc tả file `style_meta.yaml` chuẩn V5.0:
```yaml
name: "Zen Minimalist"
slug: "zen-minimalist"
mode: "moment"                        # deep | moment
description: "Phong cách tối giản, nhịp thở chậm, tập trung tuyệt đối vào cảm giác giác quan."
created_at: "2026-07-25T17:30:00Z"    # Bổ sung trường bắt buộc theo phản biện
updated_at: "2026-07-25T18:00:00Z"     # Phục vụ sắp xếp giảm dần trên UI
is_protected: false                   # true với style hệ thống (khóa slug & nút Delete)
previous_slugs: []                    # Mảng lưu lịch sử slug khi đổi tên style
```

---

## 3. THIẾT KẾ GIAO DIỆN TRỰC QUAN (STREAMLIT LOCAL UI V1)

Ứng dụng được khởi chạy qua lệnh `streamlit run ui/app.py`, chia làm 4 khu vực chức năng:

* **Sidebar - Mode Switcher**: Nút gạt chuyển đổi tức thì giữa **Deep Blog Mode (7 Agents)** và **Moment Blog Mode (6 Agents)**. Toàn bộ UI động lọc theo mode đang chọn.
* **Tab 1 - Style Gallery (Khám phá & Quản lý)**:
  * Hiển thị danh sách các style dưới dạng Thẻ (Cards), sắp xếp theo `updated_at` mới nhất.
  * Hiển thị huy hiệu `[System Protected]` hoặc `[Custom Style]`.
  * **Nút Delete Style**: Khóa (disabled) nếu `is_protected: true`. Khi bấm với custom style, hiện hộp thoại xác nhận trước khi xóa toàn bộ folder.
  * **Nút Rename Style**: Mở modal nhập Tên mới và Slug mới. Khóa input Slug nếu `is_protected: true` (system style chỉ cho sửa Tên hiển thị). Với custom style, gọi API `rename_style`, tự động đổi tên folder atomic và ghi nhận slug cũ vào `previous_slugs`.
* **Tab 2 - Style Studio (Kiến tạo Style mới - Manual Clone V1)**:
  * Form nhập liệu: Tên Style, Slug (auto-validate regex allowlist & check trùng lặp), Mô tả.
  * **Chế độ Nhân bản (Manual Clone)**: Copy trọn bộ 7 file (Deep) hoặc 6 file (Moment) từ style `reflective` sang folder mới với cơ chế Rollback nếu I/O lỗi, sẵn sàng để người dùng tùy chỉnh trên Editor. *(Tính năng AI Generator dời sang V1.1)*.
* **Tab 3 - YAML Code Editor (Chỉnh sửa chuyên sâu)**:
  * Dropdown chọn Agent trong style đang mở.
  * Trình soạn thảo `streamlit-code-editor` (line numbers, syntax highlight, tab indent) kèm fallback tự động sang `st.text_area` khi lỗi dependency.
  * Nút **"💾 Lưu thay đổi"**: Gọi YAML Validator theo Nhóm Schema (Group-based Validator). Nếu vi phạm Hard Check -> Hiện Alert đỏ, từ chối lưu. Nếu vi phạm Soft Warning -> Hiện Alert vàng nhắc nhở, nhưng ghi file atomic thành công và cập nhật `updated_at`.
* **Tab 4 - Live Workbench (Bàn Kiểm chứng Hợp đồng Dry-Run V1)**:
  * Chọn bài viết mẫu từ folder `examples/` hoặc dán text nháp mới.
  * Nút **"🧪 Kiểm tra Hợp đồng Định tuyến (Dry-Run Test)"**: Kích hoạt `run_workflow(..., dry_run=True)`, kiểm chứng tức thì trong 1-2 giây việc folder style có đầy đủ 100% file theo hợp đồng Flow và định tuyến thành công hay không. Ghi chú rõ ràng: *Chức năng này chạy mô phỏng không tốn API quota để kiểm tra tính hợp lệ của style.*

---

## 4. KẾ HOẠCH TRIỂN KHAI MULTI-AGENT CHI TIẾT (FINAL V5.0 ROADMAP)

Hệ thống được chia cho **4 Agent chuyên biệt** thực thi liên hoàn, bảo đảm an toàn tuyệt đối và không gây regression:

### 🤖 Agent 1: Core Engine & Routing Refactoring Agent
* **Nhiệm vụ 1.1**: Tái cấu trúc hàm `resolve_step_skill_path` trong `engine/workflow.py` theo mô hình **Strict Discovery đọc từ Flow YAML** (ADR-2). Loại bỏ hoàn toàn fallback âm thầm.
* **Nhiệm vụ 1.2**: Xóa bỏ đoạn fallback cản trở `moment + provocative` trong `engine/run_workflow.py`. Nâng cấp logic khám phá danh sách style hợp lệ để quét trong `skills/<mode>/`.
* **Nhiệm vụ 1.3 (Migration)**: Di dời thư mục `skills/reflective/` -> `skills/deep/reflective/`, và `skills/provocative/` -> `skills/deep/provocative/` (bảo toàn `STYLE_BRIEF.md` và toàn bộ YAML). Khởi tạo `style_meta.yaml` (`is_protected: true`, có `created_at`) cho 3 system styles (`deep/reflective`, `deep/provocative`, `moment/reflective`).
* **Nhiệm vụ 1.4 (Refactor Test Suites - QUAN TRỌNG)**: Cập nhật các đường dẫn assert hardcode trong `tests/test_workflow_contract.py` và `tests/test_moment_blog_mode.py` sang đường dẫn mới `skills/<mode>/<style>/...`, bảo đảm bộ test chạy `100% Passed`.

### 🤖 Agent 2: Style Service & AI Architect Agent (Backend Layer)
* **Nhiệm vụ 2.1**: Triển khai module `engine/style_manager.py` với bộ 6 API Python chuẩn V5.0 tích hợp an toàn I/O (slug regex, atomic write, rollback):
  * `list_styles(mode) -> list[dict]`
  * `get_style_detail(mode, slug) -> dict`
  * `save_style_file(mode, slug, filename, content) -> tuple[bool, str, str]` (trả về status, error_msg, warning_msg)
  * `create_style(mode, name, slug, description, clone_from="reflective") -> tuple[bool, str]` (Rollback nếu lỗi)
  * `rename_style(mode, old_slug, new_name, new_slug) -> tuple[bool, str]` (Khóa slug nếu `is_protected`, cập nhật `previous_slugs`, atomic rename)
  * `delete_style(mode, slug) -> tuple[bool, str]` (Khóa nếu `is_protected=True`)
* **Nhiệm vụ 2.2**: Xây dựng **YAML Schema Validator theo Nhóm Schema** (ADR-5.1), phân định rõ Universal Hard Check, Specific Hard Check cho Deep A/Deep B/Moment và Soft Warnings.
* **Nhiệm vụ 2.3 (Alias Wiring)**: Đấu nối hàm `resolve_style_by_slug_or_alias()` vào `learning.py` và `run_workflow.py` để tự động định tuyến lại các run cũ từ mảng `previous_slugs`.

### 🤖 Agent 3: Streamlit Local UI Experience Agent (Frontend Layer)
* **Nhiệm vụ 3.1**: Khởi tạo `ui/app.py` và `ui/styles.css` với Custom Dark Theme hiện đại.
* **Nhiệm vụ 3.2**: Xây dựng Sidebar Switcher và Tab 1 - Style Gallery (Thẻ Card UI, nút Delete có bảo vệ, tích hợp Modal Đổi tên Style khóa slug với system style).
* **Nhiệm vụ 3.3**: Xây dựng Tab 2 - Style Studio với chế độ Nhân bản thủ công (Manual Clone V1).
* **Nhiệm vụ 3.4**: Xây dựng Tab 3 - YAML Code Editor tích hợp `streamlit-code-editor` kèm fallback sang `st.text_area` khi lỗi dependency. Tích hợp thanh phản hồi Alert đỏ/vàng khi bấm nút Save.
* **Nhiệm vụ 3.5**: Xây dựng Tab 4 - Live Workbench (Phiên bản V1 Dry-Run Contract Test), gắn kết mượt mà với hàm `run_workflow(..., dry_run=True)` để kiểm chứng hợp đồng I/O tức thì.

### 🤖 Agent 4: Quality Assurance, Integration & Audit Agent
* **Nhiệm vụ 4.1**: Viết mới bộ Unit Test `tests/test_style_manager.py` kiểm thử tự động 100% các API trong `style_manager.py`: kiểm thử Validator Group-based (xác nhận `writing_agent` không bị reject vì thiếu `tasks`), kiểm thử Alias Resolver (`previous_slugs`), kiểm thử I/O Rollback và guardrail khóa slug system styles.
* **Nhiệm vụ 4.2**: Thực thi toàn bộ bộ kiểm thử hồi quy của dự án (`test_workflow_contract.py`, `test_moment_blog_mode.py`, `test_style_manager.py`), xác nhận vượt qua `100% Passed` với coverage đầy đủ.
* **Nhiệm vụ 4.3**: Cập nhật tài liệu kiến trúc tại `docs/current_architecture.md` và nhật ký thay đổi tại `docs/changelog.md`.

---

## 5. KẾ HOẠCH KIỂM THỬ & TIÊU CHÍ NGHIỆM THU (VERIFICATION MATRIX)

| Đối tượng Kiểm thử | Lệnh thực thi / Phương pháp | Tiêu chí Nghiệm thu Chuẩn V5.0 (Passed Condition) |
| :--- | :--- | :--- |
| **Strict Discovery & Tương thích ngược** | `python -m unittest tests/test_workflow_contract.py tests/test_moment_blog_mode.py` | 100% Test Cases vượt qua. Hợp đồng trong `flow/*.yaml` tự động kiểm tra đủ 7/6 file trong folder style. Nếu thiếu 1 file -> Fail-fast báo lỗi rõ ràng, tuyệt đối không âm thầm fallback về `reflective`. |
| **Style Manager & Group-based Validator** | `python -m unittest tests/test_style_manager.py` | Đạt 100% Passed. Kiểm chứng: File `writing_agent.yaml` vượt qua Validator mà không cần key `tasks`; Xóa/sửa slug system style bị từ chối; Đổi tên custom style tự động thêm slug cũ vào `previous_slugs`; Rollback folder thành công khi clone lỗi. |
| **Alias Wiring (Định tuyến bí danh)** | `python -m unittest tests/test_style_manager.py -k test_alias_resolution` | Quét `previous_slugs` thành công, Learning Loop (`--learn-from-run`) tìm đúng style mới nhất từ metadata của run cũ. |
| **Fail-fast CLI Validation** | `python engine/run_workflow.py --mode moment --style non_existent --dry-run` | CLI báo lỗi Fail-fast ngay lập tức, liệt kê danh sách các style hợp lệ hiện có của riêng Moment mode. |
| **Giao diện Trực quan Local UI** | Khởi chạy `streamlit run ui/app.py` và thao tác thử nghiệm | UI load mượt mà Dark Theme. Chuyển đổi mode Deep/Moment cập nhật đúng danh sách style. Sửa display name của `reflective` thành công nhưng ô Slug bị khóa. Tab 4 bấm nút Dry-run trả về xác nhận hợp đồng định tuyến hợp lệ trong 1-2 giây mà không treo app. |

---
**Bản Đặc tả Kế hoạch V5.0 Final này có hiệu lực tối hậu. Toàn bộ hội đồng chuyên gia đã hoàn tất thẩm định, sẵn sàng 100% cho giai đoạn thi hành mã nguồn (Code Execution).**
