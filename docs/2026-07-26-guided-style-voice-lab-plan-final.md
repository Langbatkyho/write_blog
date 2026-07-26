# Kế hoạch Triển khai Voice Lab V1 (Hợp nhất Kiến trúc & Multi-Agent)

> **Phiên bản:** Final (Đã bao gồm 8 điểm sửa đổi từ vòng phản biện cuối của Claude Opus 4.6)
> **Mục tiêu:** Định hình phong cách qua ngôn ngữ tự nhiên, tự động sinh cấu hình agents an toàn, tiết kiệm quota và phân chia rành mạch cho 4 Sub-agents thực thi.

---

## 1. Kiến trúc Hệ thống & Lõi Backend (`engine/voice_lab/`)

Hệ thống được thiết kế theo Clean Architecture, tách biệt nguồn chuẩn (Profile) và Runtime (YAML), tuân thủ nghiêm ngặt Invariant Contract.

### 1.1. Invariant Contract (Bất biến Runtime)
Compiler khi sinh YAML **TUYỆT ĐỐI KHÔNG ĐƯỢC** thay đổi các trường sau của Agent:
- `agent_id` và `filename`
- `output_contract` và `handoff_contract`
- `workflow_order` và `context_policy`

### 1.2. Các Modules Cốt lõi
- **`models.py`:** Pydantic schemas cho `StyleProfile`, `VoiceDNA`, `EvidenceClaim`, `CanonicalIR`.
- **`analyzer.py`:** Phân tích `samples` (bài mẫu). Dữ liệu đầu vào bị xem là **untrusted** (cô lập instruction, dùng structured output chống prompt injection).
- **`interview.py`:** Quản lý Phỏng vấn và A/B Calibration (**Blind & Randomize**).
- **`compiler.py`:** Sinh YAML dựa trên **Adjacency Matrix Tĩnh** (`DIMENSION_AGENTS`). Chỉ biên dịch lại agent bị ảnh hưởng (Incremental Compilation).
- **`overrides.py`:** Xử lý ghi đè. **Quy trình chuẩn:** Dùng Three-way diff trên Canonical IR trước. LLM chỉ được gọi để xử lý conflict không tự giải quyết được. Bắt buộc `validate_style_yaml` sau merge.
- **`migration.py` (Mới):** Cung cấp hàm `import_existing_style(mode, slug)` để convert style cũ (như `reflective`) thành Draft Profile với `provenance: inferred_from_yaml` (confidence thấp, không có evidence, chặn auto-publish).

### 1.3. API Signatures (Core)
```python
def analyze_samples(samples: list[str]) -> tuple[VoiceDNA, list[EvidenceClaim]]: ...
def generate_interview(profile: StyleProfile) -> list[InterviewQuestion]: ...
def calibrate_ab(dimension: str, profile: StyleProfile) -> tuple[str, str]: ... # Trả về bản A và B (Blind)
def compile_style(profile: StyleProfile, mode: str) -> dict[str, dict]: ... # Trả về dict Canonical IR
def merge_overrides(base_ir: dict, overrides_ir: dict) -> dict: ... # Three-way diff + LLM fallback
def import_existing_style(mode: str, slug: str) -> StyleProfile: ... # Inferred provenance
```

---

## 2. Lưu trữ, Phiên bản & Publish

### 2.1. Cấu trúc Storage & Versioning
- Nguồn chuẩn lưu tại `style_profiles/<slug>/`.
- Bổ sung thư mục `profile_history/` lưu immutable snapshots mỗi khi user bấm Save/Publish. 
- Đi kèm `manifest.json` ghi nhận `current_version`, phục vụ tính năng Rollback.
- Hỗ trợ đóng gói export/import `.voice-style.zip` (kèm manifest, SHA-256 checksum, schema version).

### 2.2. Publish Safety Pipeline (4 Bước)
1. **Staging:** Generate toàn bộ YAML ra thư mục tạm (staging).
2. **Validate:** Chạy `validate_style_contract` trên toàn mode trong staging.
3. **Backup:** Nén thư mục runtime `skills/<mode>/<slug>` hiện tại thành file backup tạm.
4. **Atomic Replace:** Dùng `os.replace` đè staging lên runtime. Nếu Exception, tự động Rollback từ file backup.

---

## 3. Giao diện Người dùng (UI - `app.py`)

1. **Wizard 5 Bước Rõ Ràng:**
   - Bước 1: **Samples** (Nhập bài mẫu).
   - Bước 2: **Evidence Review** (User duyệt các bằng chứng AI trích xuất).
   - Bước 3: **Guided Interview** (Trả lời phỏng vấn lấp chỗ trống).
   - Bước 4: **A/B Calibration** (Chọn bản A/B mù để tinh chỉnh).
   - Bước 5: **Profile Review & Publish** (Duyệt tổng thể DNA/Mode Profile và xem Quota/Diff trước khi Publish).
2. **Session Persistence:** Giữ trạng thái an toàn qua các lần Streamlit rerun.
3. **Quota Estimator:** Hiển thị chi phí (min-max tokens) động theo LLM provider hiện tại ở Bước 5.
4. **Layer Inspector:** Tab Nâng cao cho dân chuyên debug nguồn gốc YAML (Profile vs Overrides vs Default).

---

## 4. Phân chia Sub-Agents (Lập trình song song)

### 🎯 Agent 1: Data, Security & Legacy (Nền móng)
- **Files:** `models.py`, `migration.py`, logic đóng gói ZIP.
- **Nhiệm vụ:** Định nghĩa Pydantic/IR, thiết lập an toàn thư mục. Triển khai `.voice-style.zip` (SHA-256). Viết cơ chế `import_existing_style` sinh Draft Profile. Cơ chế cô lập prompt injection.

### 🎯 Agent 2: Backend Domain (Lõi Phân tích & Sinh mã)
- **Files:** `analyzer.py`, `interview.py`, `compiler.py`, `overrides.py`.
- **Nhiệm vụ:**
  - Viết API `analyze_samples`, `generate_interview`, `calibrate_ab` (blind random).
  - Hardcode Adjacency Matrix cho Incremental Compiler.
  - Viết logic ghi đè (Three-way diff ưu tiên, LLM fallback khi conflict).

### 🎯 Agent 3: UI/UX Integrator (Trải nghiệm)
- **Files:** `ui/app.py`.
- **Nhiệm vụ:** Nhúng luồng Wizard 5 Bước. Xây dựng Quota Estimator, Layer Inspector. Đảm bảo UI có đủ màn hình cho Evidence Review và Profile Review. Tích hợp pipeline Publish Safety 4 bước.

### 🎯 Agent 4: QA & Verification Bot (Kiểm thử nghiêm ngặt)
- **Files:** `tests/test_voice_lab.py`.
- **Nhiệm vụ:**
  - Contract Tests cho Adjacency Matrix.
  - **Zero-cost Smoke Test:** Kiểm tra (a) Keyword/synonym coverage của dimension trong `prompt`/`style_rules`; (b) Kiểm tra Invariant diff (Agent ID, workflow_order... phải y nguyên bản gốc). Không dùng LLM.
