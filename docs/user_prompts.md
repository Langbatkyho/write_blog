# Lưu trữ User Prompts chính

Dưới đây là tổng hợp các yêu cầu cốt lõi (User Prompts) định hình nên kiến trúc hệ thống hiện tại, được phân loại theo từng giai đoạn phát triển.

## Giai đoạn 1: Khởi tạo và Thiết lập Learning Loop

1. *"Tôi muốn sử dụng các tài liệu dạng YAML trong thư mục skills của dự án để thiết lập một workflow viết blog với input của tôi và sự hỗ trợ của AI"*
2. *"Tôi muốn 1 engine cấu hình với API Key và Endpoint của OpenAI để chạy tự động workflow này đồng thời log lại toàn bộ các output từng bước vào 1 file riêng cho mỗi lần chạy."*
3. *"Tôi muốn mở rộng thiết kế như sau: Từ `final_blog.md` tôi sẽ là human editor chỉnh sửa bằng tay ra một bản `production_blog.md`. Dựa trên đó, AI học lại từ bản `production_blog.md` đó để tham chiếu lại toàn bộ workflow. Từ đó đưa ra các insight mới để giúp tôi tinh chỉnh từng giai đoạn workflow."*
4. *"Tôi muốn cấu hình để chọn model cho từng giai đoạn trong workflow. Mục đích là khai thác các model giá rẻ cho những giai đoạn không đòi hỏi suy luận và sáng tạo mức độ cao. Tôi cũng muốn bạn bổ sung cách chạy vòng lặp learning mà không cần OpenAI API."*

## Giai đoạn 2: Handoff Layer & Tối ưu Token

5. **Phân tích của User về lỗ hổng thiết kế cũ:** *"Stage 6 was reading too much repeated history. Instead of passing full outputs between all stages, each agent should output an `Artifact` for debug/review and a compact `Handoff` for downstream agents."*
6. *"PLEASE IMPLEMENT THIS PLAN: Thêm Handoff Layer Để Giảm Token Lặp Giữa Các Stage"*
7. *"Complete the handoff layer plan, then log the full work process into `docs` under: initial plan, current project architecture, change log, user prompts, workflow analysis and lessons for future implementations"*

## Giai đoạn 3: Phân định Ranh giới Đại lý (Editorial Workflow Redesign)

8. **Nhận định về xung đột vai trò:** *"Các agent đang dẫm chân lên nhau. Writing Agent vừa viết nháp vừa tối ưu. Reader Experience lại đóng vai reviewer. Coach Agent nhảy vào can thiệp quá sớm."*
9. *"Thiết lập nguyên tắc: Mỗi agent bảo vệ một chân lý và không trả lời thay câu hỏi của agent khác. Bổ sung thêm `editor_agent` để làm cầu nối giữa Reader và Coach."*

## Giai đoạn 4: Hỗ trợ Local Model Quota (Antigravity Bridge)

10. *"Bạn đang hiểu sai yêu cầu của tôi. Tôi muốn sử dụng model quota của chính bạn là model GPT-OSS 120B chạy ở đây mà không cần OpenAI API Key."*
11. *"Bạn hãy tạo thêm cho tôi một luồng riêng độc lập để chạy được workflow với model quota của Gemini thay vì dùng OpenAI API. /grill-me"*
12. *"Tôi đồng ý với phân tích và đề xuất của Claude Opus 4.6 (về Dependency Injection). Bạn hãy chỉnh sửa lại kế hoạch. Nếu không có câu hỏi nào khác thì bạn triển khai ngay /goal"*

## Giai đoạn 5: Client Routing theo Stage

29. *"Bạn hãy lập kế hoạch chi tiết theo hướng 1. Mở rộng --client thành --client-map trong run_workflow.py — cho phép gán model per-stage."*
30. *"Tôi muốn áp dụng cài đặt model theo stage như sau: story_architect (GPT-OSS-120B), reflection_engine (Claude Sonnet 4.6), v.v."*
31. *"Làm thế nào để tôi xác thực được rằng các thành quả này thực sự do model Claude Sonnet 4.6 (Thinking) tạo ra?"*

## Giai đoạn 6: Tối ưu Token và Prompt Caching (2026-07-15)

32. *"Bạn hãy tính toán lượng token input và output theo workflow này"*
33. *"Tôi muốn tối ưu hóa token của workflow nhất có thể để tiết kiệm chi phí khi gọi API các model AI. Bạn hãy rà soát lại tính toán token nói trên của Gemini 3.1 Pro và rà soát lại toàn bộ codebase."*
34. *"Bạn hãy đọc kỹ và phản biện với Token Optimization Report của Claude Opus 4.6"*
35. *"Bạn hãy đánh giá kỹ thuật Prompt Caching có hỗ trợ được gì cho dự án này?"*
36. *"Tôi đồng ý với 2 điểm dưới đây mà bạn đã phân tích bên trên: 1. Cắt author_input khỏi reader_experience... 2. Gom toàn bộ nội dung tĩnh (author_input, thông tin mô tả luồng) lên cùng cực trên (Prefix) của Prompt. Bạn lên kế hoạch thực hiện"*
37. *"Bạn hãy cập nhật toàn bộ các tài liệu trong thư mục docs... Sau đó bạn git push /goal"*
