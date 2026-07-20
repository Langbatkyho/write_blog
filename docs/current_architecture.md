# Kiến trúc dự án hiện tại (Mindful Blog Workflow Engine)

Sau quá trình refactoring toàn diện và tái thiết kế biên giới (boundaries) của từng Agent, kiến trúc hiện tại đã được module hóa cao độ, hỗ trợ Dependency Injection (DI) và có cơ chế bảo vệ hợp đồng dữ liệu rõ ràng.

## 1. Cấu trúc thư mục (Directory Structure)

```text
write_blog/
├── engine/
│   ├── __init__.py           # Package definition
│   ├── utils.py              # Xử lý đường dẫn và đọc/ghi YAML, text
│   ├── parser.py             # Phân tích nội dung Artifact/Handoff, đếm tokens
│   ├── openai_client.py      # Giao tiếp OpenAI API, retry loops, bảo mật key
│   ├── antigravity_bridge.py # Giao tiếp qua file (File-based Bridge) dùng Local Model Quota
│   ├── learning.py           # Quản lý prompts và báo cáo cho learning loop
│   ├── workflow.py           # Quản lý Workflow & Step orchestrator
│   └── run_workflow.py       # CLI Entrypoint linh hoạt (Hỗ trợ cờ `--client`)
├── examples/
│   └── blog_input_template.md
├── flow/
│   └── write_blog.yaml       # Nguồn chân lý cho Context Policy và Định tuyến (Routing)
├── skills/
│   ├── reflective/
│   │   ├── story_architect.yaml  # Trung thành với sự thật câu chuyện
│   │   ├── reflection_engine.yaml# Sự thay đổi nội tâm của người viết
│   │   ├── writing_agent.yaml    # Viết bản nháp thô (Ghost Writer)
│   │   ├── reader_experience.yaml# Ghi chép trải nghiệm đọc (Reader Diary)
│   │   ├── editor_agent.yaml     # Biên tập viên kết nối (Giảm ma sát người đọc)
│   │   ├── coach_agent.yaml      # Khai phá điểm mù của người viết
│   │   └── future_self.yaml      # Suy ngẫm về tính toàn vẹn ở tương lai
│   ├── provocative/           # Phong cách viết gai góc, khiêu khích (cùng 7 agent YAML + STYLE_BRIEF.md)
│   └── editorial_learning.yaml
├── tests/
│   ├── test_handoff_parser.py
│   ├── test_openai_client.py
│   ├── test_workflow_contract.py
│   └── test_antigravity_bridge.py
├── docs/                     # Lưu trữ lịch sử triển khai và phân tích hệ thống
├── README.md
└── mindful_writing_os.md
```

## 2. Luồng dữ liệu và Context Policy

Tất cả các quyết định về việc truyền dữ liệu từ bước trước sang bước sau đều được khai báo rõ ràng trong `flow/write_blog.yaml` (Context Policy) thay vì giấu trong code Python.

- **story_architect**: Không nhận ngữ cảnh từ trước.
- **reflection_engine**: Nhận handoff từ `story_architect`.
- **writing_agent**: Nhận handoff từ story và reflection.
- **reader_experience**: Nhận duy nhất `draft_blog.md` để mô phỏng "đọc mù" (blind reading).
- **editor_agent**: Nhận bản nháp và báo cáo trải nghiệm đọc.
- **coach_agent**: Nhận bản đã biên tập (`edited_blog.md`) để rèn luyện người viết.
- **future_self**: Nhận bản đã biên tập và toàn bộ handoff từ editor, coach, reflection.
- **Human Writer**: Làm chủ bản xuất bản cuối cùng (`production_blog.md`).

Mỗi giai đoạn sinh ra 2 loại cấu trúc:
1. `Artifact`: Bản chi tiết đầy đủ (dùng cho vòng lặp học tập và debug).
2. `Handoff`: Bản tóm tắt súc tích (truyền cho bước sau để tối ưu lượng token sử dụng).

## 3. Cấu trúc Prompt và Prompt Caching (Mới)
Prompt cho từng Agent (`engine/workflow.py`) được thiết kế đặc biệt để tối ưu hóa tính năng **Prompt Caching** (như của Anthropic / OpenAI):
- **Static Prefix (Phần tĩnh đầu bảng):** Chứa các giới thiệu hệ thống, Author Input (nếu có), và các chỉ thị cố định (Instructions). Phần này chiếm khoảng ~1,700 tokens, không đổi giữa các stage (trừ `reader_experience`), giúp API tự động hit cache và tiết kiệm tới 90% chi phí input token lặp lại.
- **Dynamic Suffix (Phần động đuôi bảng):** Chứa các dữ liệu thay đổi liên tục (Handoffs, Artifacts, metadata hiện tại) và phần `Skill YAML`. Việc đặt `Skill YAML` ở cuối cùng cũng nhằm tận dụng hiệu ứng **Recency Bias** để ép LLM tuân thủ chặt chẽ định dạng đầu ra.

## 4. Hệ thống Dependency Injection (DI) Client

Codebase hỗ trợ đa dạng LLM Provider. Hàm `run_workflow` nhận một tham số `llm_client: LlmClient = None`. TypeAlias được định nghĩa tại `engine/workflow.py`:
`LlmClient = Callable[[str, dict[str, Any], str | None], str]`

Hệ thống cung cấp một bộ định tuyến (`engine/client_router.py`) cho phép gán model/client theo từng stage cụ thể:
- **Client Router (`create_routing_client`)**: Hàm trả về một Callable dispatch requests tới các client khác nhau dựa trên tham số `--client-map`.

Các client cơ sở (Base Clients) bao gồm:
- **OpenAI API** (`call_openai`): Quản lý qua `engine/openai_client.py`.
- **Antigravity Quota** (`call_antigravity`): Quản lý qua file-bridge trong `engine/antigravity_bridge.py` với cơ chế timeout 300 giây.
  - *Lưu ý*: Cơ chế File-Bridge này bắt buộc người dùng phải chọn một **Agentic Model** (như Gemini 3.1 Pro, Claude Sonnet 4.6) trên giao diện chat. Các model thuần text (không hỗ trợ Tool Calling) như GPT-OSS sẽ không thể tự động xử lý file, dẫn đến lỗi treo hệ thống.

## 4. Learning Loop

- Thu thập và phân tích sự chênh lệch (diff) giữa `final_blog.md` (hoặc `edited_blog.md`) do AI sinh ra và `production_blog.md` do con người biên tập thủ công lần cuối.
- Quá trình "học lại" sử dụng Artifact thay vì Handoff nhằm bảo toàn bằng chứng nguyên vẹn.
- Hỗ trợ cả **Offline Learning** (so sánh text local) và **API Learning** (gọi LLM trích xuất insights).
