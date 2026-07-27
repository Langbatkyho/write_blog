# Quy chuẩn vận hành Agentic

## 1. Phạm vi và mức độ bắt buộc

- Áp dụng cho mọi agent, sub-agent, phiên Codex/CLI và quy trình tự động làm việc trong repository này.
- Đây là chỉ dẫn bắt buộc. Nếu yêu cầu người dùng xung đột với tài liệu này, phải nêu rõ xung đột và chỉ thực hiện ngoại lệ khi người dùng phê duyệt cụ thể.
- Mọi agent phải đọc tài liệu này trước khi chạy test, dry-run, workflow viết blog hoặc bất kỳ lệnh nào có thể tạo artifact.

## 2. Phân loại dữ liệu

- `runs/` là dữ liệu chạy nghiệp vụ của người dùng, không phải thư mục tạm cho test.
- Dữ liệu bên trong `runs/` phải được xem là dữ liệu người dùng: mặc định chỉ đọc, không sửa, ghi đè, di chuyển hoặc xóa.
- Input trong `examples/` là fixture minh họa/kiểm thử, không phải input do người dùng cung cấp.
- Artifact do test, dry-run, smoke test, UI test hoặc agent validation tạo ra là dữ liệu tạm và phải được cô lập khỏi `runs/`.

## 3. Quy tắc bắt buộc khi chạy test và dry-run

1. Trước khi chạy, phải xác định lệnh có gọi `run_workflow()`, learning loop, Streamlit AppTest hoặc mã ghi log/artifact hay không.
2. Mọi test có khả năng ghi file phải dùng thư mục tạm riêng của phiên:
   - Ưu tiên fixture như `tmp_path` hoặc `TemporaryDirectory`.
   - Cấu hình `workflow.log_dir` phải trỏ tới thư mục tạm đã được xác minh.
   - Không dùng trực tiếp `engine/config.example.yaml` nếu cấu hình đó còn trỏ `log_dir` tới `runs`.
3. Không chạy test hoặc dry-run ghi vào `runs/`, kể cả khi `runs/` đã nằm trong `.gitignore`.
4. Không dùng input trong `examples/` để tạo run nghiệp vụ. Chỉ được dùng làm fixture trong môi trường tạm.
5. Nếu mã hiện tại chưa cho phép đổi thư mục output:
   - Không chạy lệnh gây ghi vào `runs/`.
   - Phải refactor điểm tiêm `log_root`/output path hoặc tạo config tạm trước.
6. Test phải tự dọn artifact do chính test tạo ra. Không được dọn dữ liệu có trước phiên làm việc.
7. Sau test, phải xác nhận `runs/` không thay đổi ngoài ý muốn.

## 4. Quy tắc gọi AI/API

- Unit test, regression test, smoke test và dry-run mặc định không được gọi API bên ngoài.
- Phải dùng fake, stub, mock hoặc deterministic dry-run response.
- Chỉ gọi API thật khi người dùng yêu cầu rõ ràng hoặc test integration thật đã được phê duyệt.
- Voice Lab hiện chỉ sử dụng Gemini API. Không tự thêm OpenAI API hoặc Antigravity Bridge vào Voice Lab.
- Không được suy luận rằng trường `provider` trong metadata chứng minh API đã được gọi; phải kiểm tra nhánh thực thi.

## 5. Quy tắc thiết kế workflow và logging

- Hàm workflow có khả năng ghi artifact phải hỗ trợ output root được tiêm từ bên ngoài.
- Dry-run nên hỗ trợ chế độ không lưu (`persist=False`) hoặc output tạm tách biệt.
- Run ID phải tránh va chạm; không chỉ dựa vào timestamp chính xác đến giây. Ưu tiên UUID hoặc timestamp có microsecond.
- Metadata của run mới phải phân biệt tối thiểu:
  - `run_source`: `user`, `test`, `dry_run`, `ui`, `cli` hoặc `agent_validation`.
  - `persisted`: có lưu bền vững hay không.
  - `api_called`: có thực sự gọi API hay không.
- Không ghi đè thư mục run đã tồn tại. Khi phát hiện trùng ID phải fail-fast hoặc sinh ID mới.

## 6. Bảo vệ dữ liệu và thao tác phá hủy

- Không xóa hoặc chỉnh sửa run cũ nếu người dùng chưa phê duyệt chính xác phạm vi.
- Trước mọi cleanup phải:
  1. Liệt kê và xác minh đường dẫn tuyệt đối.
  2. Phân loại run nghiệp vụ và artifact test bằng metadata.
  3. Báo số thư mục, số file và dung lượng dự kiến.
  4. Chỉ xóa đúng danh sách đã được phê duyệt.
- Không dùng glob rộng, biến đường dẫn chưa kiểm chứng hoặc lệnh xóa đệ quy tại workspace root.
- Không sửa hoặc dọn thay đổi không liên quan của người dùng.

## 7. Kiểm tra trước và sau khi thực thi

### Trước khi chạy

- Ghi nhận trạng thái hiện tại của `runs/` nếu lệnh có nguy cơ tạo artifact.
- Đọc config thực tế và xác nhận output path.
- Xác nhận test không dùng API thật.

### Sau khi chạy

- So sánh trạng thái `runs/` trước và sau.
- Kiểm tra artifact chỉ tồn tại trong thư mục tạm đã định.
- Báo rõ số test pass/fail, API có được gọi hay không và artifact được lưu ở đâu.
- Nếu `runs/` thay đổi ngoài ý muốn: dừng, không tự xóa, báo ngay danh sách thay đổi và nguyên nhân.

## 8. Quy tắc dành cho test suite hiện tại

- `tests/test_moment_blog_mode.py` không được dùng trực tiếp cấu hình có `log_dir: runs`.
- Các test gọi `run_workflow()` hoặc `run_learning_loop()` phải nhận config/output root tạm.
- Regression test cho Voice Lab vẫn phải tuân thủ quy tắc này khi chạy toàn bộ test suite dự án.
- Streamlit AppTest không được tự kích hoạt nút tạo workflow hoặc ghi artifact vào `runs/`.

## 9. Tiêu chí hoàn tất công việc agentic

Một tác vụ chỉ được coi là hoàn tất khi:

- Kiểm thử phù hợp đã chạy trong môi trường cô lập.
- Không có artifact test mới trong `runs/`.
- Không có API ngoài dự kiến được gọi.
- Không làm thay đổi dữ liệu hoặc mã ngoài phạm vi yêu cầu.
- Báo cáo cuối nêu ngắn gọn: thay đổi chính, kiểm thử, vị trí artifact và mọi rủi ro còn lại.

## 10. Học từ lịch sử dự án

- Trước khi thiết kế hoặc refactor workflow, agent, schema, prompt, routing, publisher hay learning loop, phải đọc:
  - `docs/current_architecture.md`.
  - `docs/workflow_analysis.md`.
  - Kế hoạch hoặc changelog liên quan trực tiếp đến module đang sửa.
- Các sai lầm lịch sử có liên quan phải được đưa vào mục rủi ro của kế hoạch triển khai.
- Dùng `rg` để tìm tài liệu và mã liên quan; không giả định kiến trúc chỉ từ tên file.

## 11. Vệ sinh kiến trúc

- Entrypoint/orchestrator chỉ điều phối; không chứa prompt tĩnh, parser, formatter hoặc logic domain chi tiết.
- Số dòng chỉ là tín hiệu review, không phải tiêu chí vi phạm duy nhất. Phải refactor khi module có nhiều trách nhiệm hoặc nhiều lý do độc lập để thay đổi.
- Mọi contract, utility, constant hoặc module chuẩn hóa mới phải:
  1. Có consumer thực tế trong cùng thay đổi.
  2. Có test hoặc bằng chứng tích hợp phù hợp.
  3. Không trùng nguồn chân lý đã tồn tại.
- Trước khi hoàn tất, phải tìm kiếm import/reference để phát hiện dead architecture, code cũ, import và biến không còn dùng.
- Chỉ dọn file tạm và code thừa do tác vụ hiện tại tạo ra; không dọn thay đổi hoặc dữ liệu ngoài phạm vi.

## 12. Kiểm chứng thay đổi UI

- Khi sửa Streamlit UI, phải chạy Streamlit AppTest hoặc kiểm tra tương đương.
- Thay đổi bố cục, trạng thái tương tác hoặc nội dung hiển thị phải có thêm screenshot/kiểm tra trực quan khi công cụ cho phép.
- Không báo hoàn tất UI chỉ dựa trên compile hoặc unit test không render giao diện.

## 13. Điều phối nhiều agent

- Chỉ dùng nhiều agent khi được yêu cầu hoặc chỉ dẫn hiện hành cho phép.
- Khi dùng nhiều agent, phải phân chia file ownership rõ ràng và tránh sửa song song cùng file dùng chung.
- Thứ tự mặc định cho thay đổi kiến trúc:
  1. Contract/schema và invariant.
  2. Engine, persistence và test nền tảng.
  3. Prompt, agent YAML và nội dung.
  4. Tích hợp UI.
  5. Regression và audit cuối.
- Ground truth và contract phải được chốt trước khi giao tác vụ prompt/content.

## 14. Skill kiến trúc bắt buộc

- Phải dùng skill `.agents/agentic-workflow-architect/SKILL.md` khi:
  - Thêm hoặc sửa workflow/agent.
  - Refactor orchestrator hoặc engine.
  - Thay đổi prompt contract, Pydantic schema hoặc Canonical IR.
  - Thay đổi provider, routing, context policy, learning loop.
  - Thay đổi compile, archive, publish hoặc rollback.
- Skill bổ sung quy trình kiến trúc; mọi quy tắc an toàn dữ liệu và test trong file này vẫn có hiệu lực cao hơn.
