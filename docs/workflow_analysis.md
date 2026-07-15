# Phân tích Workflow & Bài học Rút ra (Lessons Learned)

## Bài học 1: Tối ưu Token phải bắt đầu từ Kiến trúc Context

Việc chọn các mô hình giá rẻ giúp giảm chi phí, nhưng nguồn gốc lớn nhất của lãng phí là **sự lặp lại Context**. Ở thiết kế cũ, mỗi bước đều mang theo toàn bộ output của tất cả các bước trước đó. Các agent cuối chuỗi phải đọc lại hàng loạt thông tin mà chúng không hề cần.

**Giải pháp:**
- Giữ bản đầy đủ (Artifact) để con người review và dùng cho quá trình Learning.
- Chỉ truyền bản tóm tắt ngắn gọn (Handoff) cho máy thực thi.
- Khai báo luồng di chuyển context minh bạch ngay trong file YAML của workflow.

## Bài học 2: Output Debug và Context Thực thi phải tách biệt

Ban đầu, một file output gánh hai nhiệm vụ:
1. Cho con người đọc, gỡ lỗi.
2. Làm dữ liệu đầu vào cho máy ở bước sau.

Hai nhiệm vụ này yêu cầu độ lớn và độ chính xác khác nhau. Tách bạch `Artifact` và `Handoff` giúp hệ thống dễ dàng tối ưu lượng token mà không làm mất tính khả quan (observability).

## Bài học 3: File cấu hình Flow phải nắm giữ Context Policy

Đưa logic `context_policy` vào file `flow/write_blog.yaml` giúp workflow dễ dàng được kiểm tra trực quan. Người bảo trì tương lai có thể thấy rõ tại sao `future_self` nhận được bản nháp nhưng chỉ cần bản tóm tắt handoff từ các tác nhân khác. Việc giấu các quyết định này trong mã Python là một thực hành xấu (anti-pattern).

## Bài học 4: Learning Loop cần toàn bộ Bằng Chứng, không phải Handoff

Bản Handoff sinh ra để máy thực thi nhanh và rẻ, nhưng để học từ `production_blog.md` của con người, hệ thống cần toàn bộ bản `Artifact`. Nếu chỉ so sánh Handoff với bài đăng thực tế, AI có thể bỏ sót những chỉnh sửa quan trọng từ con người.
Việc tổ chức lại thư mục output với `step_outputs.json` đa tầng giúp duy trì bằng chứng nguyên vẹn phục vụ cho quá trình này.

## Bài học 5: Đừng để một Agent ôm đồm nhiều việc chỉ vì nó làm được

Ban đầu `writing_agent` vừa viết, vừa chỉnh văn phong; `reader_experience` vừa đóng vai độc giả, vừa đóng vai người bắt lỗi. Điều này khiến ranh giới trách nhiệm bị mờ nhạt, và prompt trở nên cực kỳ phức tạp.

**Quy tắc Vàng:** "Mỗi agent chỉ bảo vệ một chân lý và không trả lời thay câu hỏi của agent khác".
- Độc giả (Reader) chỉ nói cảm nhận lần đọc đầu.
- Biên tập (Editor) mới đưa ra chỉnh sửa.
- Việc xuất bản cuối cùng (`final_blog.md`) phải được trả về tay con người.

## Bài học 6: Code Dependency Injection (DI) hiệu quả hơn Fallback ngầm

Trong quá trình thiết lập Bridge để sử dụng Model Quota nội bộ (Antigravity), chúng ta từng mắc sai lầm chèn logic ghi file trực tiếp vào trong `openai_client.py` thông qua `try...except RuntimeError`. Điều này làm phá vỡ ranh giới module và gây rủi ro bảo mật rò rỉ key.

**Giải pháp tốt nhất:** Thiết lập TypeAlias `LlmClient` chuẩn và thực hiện Dependency Injection ở cấp cao nhất của hệ thống (`run_workflow.py`), thay vì vá lỗi ở tầng thấp.

## Bài học 7: Kiểm soát chi phí phải đi theo nhiều lớp (Layered)

Dự án hiện có 3 lớp kiểm soát chi phí:
1. Lựa chọn model theo từng giai đoạn (vd: xài model nhỏ cho bước tóm tắt).
2. Nén ngữ cảnh bằng Handoff Layer.
3. Chạy Offline Learning không cần gọi API.

Sự kết hợp nhiều lớp giúp hệ thống mạnh mẽ hơn nhiều so với việc chỉ dựa vào một thủ thuật cắt giảm token duy nhất. Đề xuất tương lai: Đo lường Token Telemetry trước khi gửi API request.

## Bài học 8: Router Pattern thay thế Hardcode Conditional Logic

Ban đầu, tham số `--client` chỉ hoạt động như một fallback đơn giản giữa OpenAI và Antigravity, được quyết định ở tầng ứng dụng (CLI) và cố định xuyên suốt workflow. Tuy nhiên, việc tối ưu chi phí và chất lượng thực tế yêu cầu từng stage sử dụng model (hoặc client) chuyên biệt. Thay vì thay đổi hàm thực thi LLM, sử dụng mô hình Router (với Dependency Injection) và Dictionary Map `--client-map` giúp tách bạch cấu hình khỏi logic workflow. `LlmClient` closure do Router trả về vẫn tuân thủ hoàn toàn signature cũ, đảm bảo tính đóng gói và mở rộng trong tương lai.

## Bài học 9: Hiểu đúng bản chất của Prompt Caching API

Việc tối ưu hóa token không chỉ đơn thuần là rút gọn (compression) văn bản, mà còn là nghệ thuật lợi dụng bộ nhớ đệm (Caching).
- **Tránh sai lầm "Đứt chuỗi"**: Các LLM API như Anthropic và OpenAI sử dụng **Prefix Hashing** phi trạng thái (stateless) cho Caching. Nếu một stage bất kỳ làm thay đổi prefix, cache của riêng stage đó sẽ miss, nhưng nó hoàn toàn không làm "đứt chuỗi" hay phá hỏng cache của các stage sau (những stage tiếp tục dùng chung prefix ban đầu).
- **Tối ưu vị trí dữ liệu**: 
  - Dữ liệu dài và tĩnh (như `author_input`) bắt buộc phải đẩy lên đầu file (Static Prefix) để API nhận dạng được và cache lại. Nếu đặt sai vị trí (ví dụ: ở giữa hoặc cuối prompt), phần dữ liệu này sẽ không bao giờ được cache.
  - Các chỉ thị mang tính tuân thủ cao (Skill YAML, định dạng đầu ra) nên đặt ở đuôi (Dynamic Suffix) để lợi dụng Recency Bias, giúp LLM không bị lạc lối sau khi đọc hàng ngàn token ngữ cảnh.
