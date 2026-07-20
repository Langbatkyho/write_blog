# Nhật ký Triển khai & Hoạt động Agent: Kiến trúc Đa Phong Cách Multi-Style (2026-07-20)

## 1. Bối cảnh & Mục tiêu (Context & Goal)
Dự án cần hỗ trợ nhiều phong cách viết blog khác nhau (Style 1: `reflective`, Style 2: `provocative`, và mở rộng Style 3+ về sau). Mục tiêu kiến trúc mấu chốt:
- Giữ nguyên duy nhất một file workflow `flow/write_blog.yaml` (bất biến luồng dữ liệu & trình tự agent).
- Đổi mới cấu hình prompt/identity/supreme_rules của từng Agent theo từng phong cách thông qua các thư mục riêng trong `skills/<style>/`.
- Bổ sung tham số CLI `--style` linh hoạt.

---

## 2. Quá trình Thiết kế tương tác (/grill-me)
Qua quá trình phỏng vấn định hình yêu cầu với người dùng:
1. **Cấu trúc thư mục**: Dùng tên ngữ nghĩa (`skills/reflective/`, `skills/provocative/`) thay vì số thứ tự (`style1/`, `style2/`).
2. **Hành vi mặc định**: Nếu không truyền `--style`, engine tự động chọn phong cách `reflective`.
3. **Phân tách file**: File `skills/editorial_learning.yaml` được giữ lại ở root `skills/` vì logic học tập độc lập với phong cách viết.

---

## 3. Quá trình Lập Kế hoạch & Phản biện (Planning & Reviews)
- **Kế hoạch ban đầu**: Đề xuất dùng string replacement `skills/` -> `skills/{style}/` và chạy song song 2 agent.
- **Phản biện từ Claude Opus 4.6**: Chỉ ra 10 lỗ hổng nghiêm trọng (Path replace dễ gãy, bỏ sót `editorial_learning.yaml`, làm hỏng unit tests, thiếu metadata `style`, rủi ro race condition giữa các agent, thiếu `STYLE_BRIEF.md` cho Agent 2, v.v.).
- **Tái phản biện**: Tích hợp 100% đề xuất của Claude Opus 4.6 vào Kế hoạch cập nhật.
- **Quy trình Multi-Agent mới**: Đổi sang điều phối **tuần tự** (Agent 1 hoàn thành refactoring -> Agent 2 mới tiến hành Prompt Engineering dựa trên Ground Truth).

---

## 4. Hoạt động của các Agent (Agent Activities & Execution)

### Agent 1: Core & Refactoring Agent
- **Nhiệm vụ**: Tái cấu trúc thư mục, sửa engine và tests.
- **Hành động**:
  1. Tạo thư mục `skills/reflective/` và di chuyển 7 file YAML gốc vào đây.
  2. Cập nhật `engine/run_workflow.py` thêm `--style` và logic fail-fast validation.
  3. Cập nhật `engine/workflow.py` dùng `Path(step["skill"]).parent / style / Path(step["skill"]).name` để nạp file skill an toàn.
  4. Ghi `"style": style` vào `metadata.json` và cập nhật tên folder chạy dạng `{timestamp}_{style}_{slug}`.
  5. Cập nhật `tests/test_workflow_contract.py` sửa lại các đường dẫn hardcode.

### Agent 2: Prompt Engineering Agent
- **Nhiệm vụ**: Kiến tạo phong cách `provocative`.
- **Hành động**:
  1. Tạo `skills/provocative/STYLE_BRIEF.md` làm Ground Truth.
  2. Copy 7 file YAML từ `reflective` sang `provocative`.
  3. Điều chỉnh prompt, identity, supreme_rules cho 7 agent (tập trung vào sự gai góc, bóc trần sự thật, loại bỏ từ ngữ xoa dịu/bảo vệ tác giả).

### Hotfix (Sửa lỗi phát sinh)
- Trong quá trình dry-run kiểm thử phong cách `provocative`, phát hiện lỗi cú pháp YAML tại `skills/provocative/editor_agent.yaml` dòng 108 (`"maybe", "perhaps"...` gây ParserError).
- Đã khắc phục bằng cách bao bọc chuỗi trong dấu nháy đơn `' "maybe", "perhaps"... '`.

---

## 5. Áp dụng 5 Vector Tinh chỉnh Kiến trúc (Refactor Vectors)
Sau khi nghiệm thu nghiêm ngặt theo 3 khía cạnh, 5 refactor vectors đã được thi hành:

1. **Vector 1 (`engine/workflow.py`)**: Bổ sung `"style": style` vào `metadata.json` của `run_learning_loop` để bảo toàn khả năng truy vết audit.
2. **Vector 2 (`engine/run_workflow.py`)**: Đặt `--style` default là `None` trên CLI. Khi chạy `--learn-from-run`, nếu user không truyền `--style`, engine tự động đọc `style` từ file `metadata.json` của run cũ thay vì ép về `reflective`.
3. **Vector 3 (`docs/current_architecture.md`)**: Cập nhật cây thư mục thêm `skills/provocative/`.
4. **Vector 4 (`README.md`)**: Bổ sung ví dụ chạy `--style provocative` và dry-run cụ thể.
5. **Vector 5 (`tests/test_workflow_contract.py`)**: Parametrize toàn bộ test hợp đồng dữ liệu chạy qua tất cả các phong cách (`reflective`, `provocative`).

---

## 6. Kết quả Kiểm thử & Xác nhận (Verification & Results)
- **Unit Tests**: `python -m unittest tests.test_workflow_contract` -> **PASSED (3/3 tests)**.
- **Dry-run Reflective**: `python engine/run_workflow.py --input examples/blog_input_template.md --dry-run` -> **PASSED** (`runs/20260720_113554_reflective_raw-notes`).
- **Dry-run Provocative**: `python engine/run_workflow.py --input examples/blog_input_template.md --style provocative --dry-run` -> **PASSED** (`runs/20260720_113646_provocative_raw-notes`).
- **Fail-fast Validation**: `python engine/run_workflow.py --input examples/blog_input_template.md --style unknown --dry-run` -> **PASSED** (Bắt lỗi chính xác `ValueError: Style 'unknown' not found. Available: ['provocative', 'reflective']`).
