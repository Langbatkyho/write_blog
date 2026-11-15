# ADR: Bảng model Claude mặc định sau ART-6.2 (2026-11-15)

- **Trạng thái:** Đã chốt (owner đóng ART-6.2 ngày 2026-11-15).
- **Bối cảnh:** ART-6.2 dự kiến so sánh A/B mù trên 3–5 input thật giữa phương án Cân bằng (khối `claude:` trong `engine/config.example.yaml`) và mốc "Opus 5.5 ở mọi bước, effort medium", rồi chốt bảng model. Owner đóng ART-6.2 sau **1 cặp A/B thật** (Moment/reflective, 2026-11-15): owner chọn bài của Mốc Opus 5.5 · medium. Tổng thời gian các bước: Mốc Opus 57,6 s, Cân bằng 66,6 s; cả 12 bước đúng model, không bị hạ hạng.

## Quyết định

1. **Giữ nguyên bảng Cân bằng làm mặc định trong repo.** Khối `claude:` không đổi, bundle không đổi.
2. Một cặp A/B không đủ để đổi mặc định cho mọi tác giả và mọi style. Ai muốn dùng mốc Opus 5.5 · medium thì tự chọn preset này trong khung "Model cho từng bước" (ART-6.1). Cấu hình đó lưu riêng cho từng tài khoản.
3. Muốn đổi mặc định về sau: sửa khối `claude:`, build và publish lại. Không cần mở lại ART-6.2.

## Hệ quả

- AC1 của ART-6.2 (ít nhất 3 cặp) không đạt. Owner chủ động bỏ qua tiêu chí này khi đóng PRD.
- AC2 đạt bằng ADR này. AC3 không phát sinh vì bundle không đổi.
- Dữ liệu A/B sau này vẫn lưu tại `data/users/<uid>/blog/ab/` trong Artifact của từng tác giả. Có thể dùng lại nếu muốn xét lại bảng.
