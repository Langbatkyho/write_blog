# Báo cáo spike ART-0

> **Ngày:** 2026-11-14
> **Trang spike:** https://claude.ai/artifact/7bTDoeSTwPPpbFZc2VeHtF (build `fe0926c94cf6`)
> **Trạng thái:** chờ owner duyệt để đóng ART-0.
> **Kế hoạch:** `docs/2026-11-14-claude-artifact-plan.md`

## 1. Phương pháp

- Owner và tài khoản kiểm tra thứ hai (Contributor) mở trang và bấm chạy; trang tự lưu kết quả vào `db`.
- Tổng cộng 10 lần gọi Claude: owner 7, tài khoản thứ hai 3. Thêm 1 lần ghi/đọc `db`.
- Prompt dựng bằng hàm Python của repo từ fixture trong `examples/`: `build_step_prompt` cho `writing_agent` (deep, style `reflective`, input `examples/blog_1.md`) và `build_analysis_prompt` cho Voice Lab với 4 bài mẫu.
- Không gọi `run_workflow()`, không gọi API, `runs/` không đổi. Dữ liệu thô nằm trong `db` của trang spike và thư mục tạm; **không đưa vào repo** vì chứa văn bản cá nhân.
- Kết quả JSON Voice Lab được kiểm lại ngoài trang bằng `parse_analysis_response` của repo (Pydantic `extra="forbid"`) và so quote với bài mẫu.

## 2. Kết quả

### A. Gọi model theo tên (cả hai tài khoản)

| Tài khoản | Model gọi | Model trả lời | Hạng | Chữ đầu | Tổng |
|---|---|---|---|---|---|
| Owner | `claude-haiku-5-5` | `claude-haiku-5-5` | quick | 3383 ms | 3715 ms |
| Owner | `claude-sonnet-5-5` | `claude-sonnet-5-5` | default | 894 ms | 1847 ms |
| Owner | `claude-opus-5-5` | `claude-opus-5-5` | complex | 857 ms | 1128 ms |
| Thứ hai | `claude-haiku-5-5` | `claude-haiku-5-5` | quick | 3354 ms | 3359 ms |
| Thứ hai | `claude-sonnet-5-5` | `claude-sonnet-5-5` | default | 2397 ms | 2401 ms |
| Thứ hai | `claude-opus-5-5` | `claude-opus-5-5` | complex | 1282 ms | 1284 ms |

- **6/6 lần model trả lời đúng tên model đã gọi**, không bị hạ hạng, `truncated: false`.
- Haiku đều chậm hơn ở cả hai tài khoản, nhưng nó luôn được chạy đầu tiên trong mỗi phiên nên có thể dính độ trễ của lần gọi đầu (consent, khởi động). Chưa đủ dữ liệu để kết luận Haiku chậm hơn thật.
- Effort `low`, câu trả lời rất ngắn; các con số này không đại diện cho stage thật.

### B. Bài dài (owner, Opus 5.5, effort high)

| Chỉ số | Giá trị |
|---|---|
| Model trả lời | `claude-opus-5-5` |
| Chữ đầu / tổng | 2984 ms / 9862 ms |
| Bị cắt | Không |
| Hai section `## Artifact` + `## Handoff` | Đủ; qua `parse_stage_response(strict=True)` của repo |
| Số từ bài / handoff | 721 / 236 (Python đếm: 718 / 236) |
| Kích thước phản hồi | khoảng 6 KB |

### C. Voice Lab, JSON phân tích (owner, Opus 5.5, effort high, `sample.json`)

| Lần | Qua Pydantic | Số chiều | Bằng chứng | Quote khớp nguyên văn | Chữ đầu | Tổng |
|---|---|---|---|---|---|---|
| 1 | Có | 12/12 | 44 | 44/44 | 12.7 s | 35.9 s |
| 2 | Có | 12/12 | 43 | 43/43 | 15.2 s | 38.1 s |
| 3 | Có | 12/12 | 36 | 36/36 | 7.5 s | 28.6 s |

- **3/3 lần** qua schema chặt của repo; không có chiều lạ; **123/123 quote khớp nguyên văn** với bài mẫu.
- Schema được nhúng vào chính nội dung prompt (Artifact không có tham số schema riêng như API Gemini) và vẫn cho kết quả đúng khung.
- Số lượng bằng chứng dao động 36–44 giữa các lần; `strength` của cùng một chiều lệch tối đa 0.05–0.1. Chất lượng ngữ nghĩa (ví dụ bằng chứng `contradict` có đúng nghĩa không) **chưa được đánh giá**; việc đó thuộc ART-8.2.
- Mô hình tự đưa ra cảnh báo hợp lý về outlier (`/-rose`, lỗi chính tả, nội dung thương hiệu) thay vì đưa chúng vào hồ sơ.

### D. Lưu trữ

- Ghi rồi đọc lại **một document 256.200 byte UTF-8** (200.000 ký tự tiếng Việt có dấu), nội dung giống hệt: ghi 638 ms, ghi + đọc 965 ms.
- Giới hạn của `db` là 256 KiB (262.144 byte), nên phép thử chỉ cách giới hạn khoảng 5,9 KB. Style hoàn chỉnh của Voice Lab ước 50–80 KB nên còn dư nhiều.

## 3. Đối chiếu tiêu chí chấp nhận

| AC | Kết quả |
|---|---|
| ART-0-AC1: bảng model × tài khoản | **Đạt.** Bảng ở mục 2A. |
| ART-0-AC2: bài dài không bị cắt, đủ hai section | **Đạt một phần.** Bài 721 từ + handoff 236 từ không bị cắt, đủ hai section. Tuy nhiên input mẫu yêu cầu "dưới 1000 từ" nên **chưa thử bài 1200–1800 từ** như kế hoạch ghi. Mô tả trên trang spike ghi "1200–1800 từ" là sai so với thực tế đã chạy. |
| ART-0-AC3: `sample.json` qua parser | **Đạt.** 3/3. |
| ART-0-AC4: ghi/đọc document khoảng 200 KB | **Đạt.** |

## 4. Quyết định và điều chỉnh rút ra

1. **D7 xác nhận:** gọi model theo tên chạy đúng trên cả hai tài khoản. Vẫn giữ telemetry `modelApplied` vs `model_requested` vì việc hạ hạng mà không báo lỗi là hành vi được tài liệu hóa.
2. **Thời gian chờ ngắn hơn ước lượng ban đầu.** Chữ đầu tiên về sau 1–15 giây và một stage viết dài xong trong khoảng 10 giây; Voice Lab phân tích khoảng 30–40 giây. Ước lượng "3–8 phút cho một run deep" trước đây có vẻ quá cao, nhưng mới đo một stage; chưa sửa số liệu cho tới khi có run thật ở ART-3.
3. **ART-2 phải port `count_words` đúng ngữ nghĩa Python (`\w+`).** Bản đếm trong trang dùng regex Unicode bao gồm ký tự dấu kết hợp, nên đếm thừa 3 từ trên bài này; con số lệch khớp với đúng 3 ký tự biến thể emoji (U+FE0F) trong bài. Giới hạn từ là ràng buộc cứng của moment mode (300–600 từ), nên lệch kiểu này sẽ làm sai kiểm tra.
4. **ART-8.1 nhúng JSON Schema vào prompt** thay vì truyền riêng như bản Gemini; cách này đã chạy 3/3 nên giữ.
5. **ART-3-AC2 bổ sung:** một run deep thật phải dùng input có `desired_length` 1200–1800 từ để đóng phần còn thiếu của AC2.
6. **Giới hạn của spike:** `writing_agent` chạy không có handoff từ các stage trước, nên chỉ đo được độ dài và cấu trúc, chưa đo chất lượng văn. Hai tài khoản chỉ so sánh ở phép thử A.

## 5. Việc cần làm để đóng ART-0

- [ ] Owner duyệt báo cáo này.
- [ ] Owner gỡ quyền chia sẻ của trang spike với tài khoản thứ hai (menu Share). Đồng thời xem xét xóa trang spike: `spike_results` là vùng dữ liệu dùng chung nên tài khoản thứ hai đọc được toàn bộ bài viết thô trong đó.
