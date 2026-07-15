# Báo cáo Tối ưu hóa Token & Prompt Caching

> **Tài liệu phân tích chuyên gia cho Workflow `write_blog`**
> **Model thực hiện:** Gemini 3.5 Flash (đối chiếu và tổng hợp phản biện từ Gemini 3.1 Pro và Claude Opus 4.6)

---

## 1. Tổng quan lượng Token thực tế (Run: 20260714_182136_raw-notes)

### 1.1. Bảng số liệu tổng quát
*   **Total Input Tokens:** 23,718
*   **Total Output Tokens:** 8,750
*   **Tổng cộng (Grand Total):** 32,468

### 1.2. Phân rã lượng Token tiêu thụ qua 7 Stage

| Stage | Template | Skill YAML | Author Input | Handoff Ctx | Artifact Ctx | **Total Input** | **Total Output** |
|:---|---:|---:|---:|---:|---:|---:|---:|
| **story_architect** | 209 | 221 | 1,244 | 0 | 0 | **1,674** | **708** |
| **reflection_engine** | 209 | 220 | 1,244 | 295 | 0 | **1,968** | **890** |
| **writing_agent** | 209 | 577 | 1,244 | 589 | 0 | **2,619** | **1,888** |
| **reader_experience** | 209 | 444 | 1,244 | 0 | 1,501 | **3,398** | **1,263** |
| **editor_agent** | 209 | 533 | 1,244 | 968 | 2,385 | **5,339** | **2,030** |
| **coach_agent** | 209 | 253 | 1,244 | 886 | 1,733 | **4,325** | **998** |
| **future_self** | 209 | 315 | 1,244 | 894 | 1,733 | **4,395** | **973** |

*Ghi chú:*
*   **Author Input lặp lại:** 1,244 tokens × 7 stages = 8,708 tokens (chiếm 36.7% tổng input).
*   **Template Preamble:** 209 tokens × 7 stages = 1,463 tokens (chiếm 6.2% tổng input).
*   **Skill YAML:** Tổng cộng 2,563 tokens cho cả luồng (chiếm 10.8% tổng input).

---

## 2. Phân tích & Phản biện các điểm chưa hiệu quả

Một số phân tích trước đó (của Claude Opus 4.6) đề xuất nén token cơ học thông qua cắt giảm dữ liệu đầu vào. Tuy nhiên, dưới góc nhìn chuyên môn, các đề xuất đó **gây tổn hại nghiêm trọng đến triết lý thiết kế (Design Philosophy)** của một hệ thống Mindful & Reflective. 

Dưới đây là đối chiếu và phản biện chi tiết:

### 2.1. Việc lặp lại Author Input (`raw_notes`)
*   **Nhận định chưa chuẩn của Opus:** Đề xuất bỏ `author_input` khỏi `editor_agent`, `coach_agent`, `future_self` và giữ lại ở `reader_experience`.
*   **Phản biện chuyên gia:** 
    *   `reader_experience` đóng vai trò là độc giả mù (blind reader). Nó **BẮT BUỘC KHÔNG ĐƯỢC ĐỌC** ý đồ gốc (`author_input`) để phản hồi khách quan nhất trên bản thảo của `writing_agent`.
    *   `coach_agent` và `future_self` ngược lại **BẮT BUỘC PHẢI ĐỌC** `author_input` để so sánh giữa "suy nghĩ ban đầu" với "sản phẩm cuối cùng", từ đó chỉ ra những điểm né tránh, mâu thuẫn nội tâm của tác giả. Cắt bỏ ở đây sẽ vô hiệu hóa chức năng phản tư (reflection).

### 2.2. Sự dư thừa Context tại `editor_agent`
*   **Vấn đề thực tế:** `editor_agent` đang nhận cả `reader_experience` artifact (884 tokens) lẫn handoff (379 tokens).
*   **Giải pháp hợp lý:** Handoff của `reader_experience` chỉ mang tính tóm tắt. Editor cần biết chính xác điểm khựng (friction) trong bản thảo, nên **cần giữ lại Artifact (Reader Report)** nhưng **có thể bỏ Handoff** để giảm trùng lặp. Đồng thời, `story_architect` handoff có thể lược bỏ vì ý đồ cốt lõi đã được phản ánh trong bản thảo của `writing_agent`.

### 2.3. Rút gọn Skill YAML
*   **Đề xuất cơ học của Opus:** Lược bỏ các phần triết lý thiết kế (`core_belief`, `supreme_rule`) thành các gạch đầu dòng ngắn gọn.
*   **Phản biện chuyên gia:** LLM hoạt động mạnh mẽ nhờ "vibe" (giọng điệu) được thiết lập trong prompt. Việc cắt bỏ các câu triết lý định hướng như *"Every edit has a cost. The highest cost is losing the writer's authentic voice"* sẽ hạ cấp tác nhân từ một Editor đồng cảm (Compassionate Editor) thành một bộ máy sửa ngữ pháp khô khan. Chỉ nên lược bỏ phần meta-data cấu trúc (như `input type`, `required`).

---

## 3. Đánh giá tính khả thi của Prompt Caching

Kỹ thuật Prompt Caching (Context Caching) là chìa khóa vàng để giảm chi phí khi gọi API, nhưng hiệu quả thực tế phụ thuộc lớn vào AI Provider:

### 3.1. Cơ chế hoạt động trong luồng
Nếu cấu trúc lại prompt, đưa phần dữ liệu tĩnh (`author_input` và Preamble) lên **đầu prompt (Prefix)** và giữ nguyên qua các bước, hệ thống có thể cache lại attention của đoạn văn bản này (~1,500 - 1,700 tokens).

### 3.2. Đánh giá theo từng Provider
1.  **Anthropic (Claude 3.5 Sonnet / Opus): Cực kỳ hiệu quả**
    *   Ngưỡng kích hoạt cache: **1,024 tokens**.
    *   Prefix của workflow (~1,700 tokens) hoàn toàn vượt qua ngưỡng này, giúp giảm tới 90% chi phí cho phần input lặp lại của các stage sau.
2.  **OpenAI (GPT-4o): Hiệu quả tự động**
    *   Ngưỡng kích hoạt cache: **1,024 tokens** (tự động cache). 
    *   Tiết kiệm ngay 50% chi phí input nếu cấu trúc prefix đồng nhất.
3.  **Google Gemini (Gemini 1.5/3.1/3.5): KHÔNG KHẢ THI**
    *   Ngưỡng kích hoạt Gemini Context Caching: Tối thiểu **32,768 tokens**.
    *   Workflow này có tổng input stage lớn nhất cũng chỉ ~6,000 tokens, hoàn toàn không đủ để kích hoạt cơ chế cache của Gemini.

---

## 4. Đề xuất cải tiến thực tế (Actionable Suggestions)

Để tối ưu hóa chi phí mà vẫn giữ nguyên tính nghệ thuật và triết lý của Mindful Blog Workflow:

### 4.1. Điều chỉnh nạp Context chọn lọc (Tiết kiệm ~25% chi phí)
*   **Stage 4 (`reader_experience`):** Loại bỏ hoàn toàn `author_input` khỏi prompt (Tiết kiệm ~1,244 tokens và tăng độ khách quan cho reader).
*   **Stage 5 (`editor_agent`):** Loại bỏ `reader_experience` handoff (giữ lại artifact) và loại bỏ `story_architect` handoff (Tiết kiệm ~670 tokens).
*   **Stage 6 & 7 (`coach_agent` & `future_self`):** Chỉ nạp phần văn bản blog đã sửa (lấy từ output `editor_agent`), loại bỏ phần `edit_log` (nhật ký chỉnh sửa của editor) để tránh nạp các phân tích kỹ thuật thừa thãi vào suy nghĩ phản tư (Tiết kiệm ~400 tokens/stage).

### 4.2. Định tuyến mô hình thông minh (Smart Model Routing - Tiết kiệm ~60% chi phí)
Cập nhật `config.local.yaml` để phân chia tác vụ:
*   Các stage mang tính cấu trúc/đọc thô như `story_architect` và `reader_experience`: Chuyển sang sử dụng **model mini** (`gpt-4.1-mini` hoặc `gemini-3.5-flash`).
*   Các stage đòi hỏi tư duy sâu sắc, thấu cảm như `reflection_engine`, `writing_agent`, `editor_agent`, `coach_agent`: Giữ nguyên **model lớn** (`gpt-4.1` hoặc `gemini-3.1-pro`).

### 4.3. Cấu trúc lại Prompt để hỗ trợ Caching
*   Sửa đổi hàm `build_step_prompt()` trong `engine/workflow.py` để đẩy phần dữ liệu chung (`author_input` và system instruction) làm prefix cố định ở đầu file prompt, giúp tự động kích hoạt tính năng cache trên OpenAI và Claude API.
