# Hướng dẫn Sử dụng Giao diện Quản trị Phong cách Viết (Mindful Writing OS UI)

Giao diện quản trị phong cách viết (Local UI) được xây dựng trên nền tảng Streamlit, cho phép bạn khám phá, tùy biến, và kiểm chứng các phong cách viết (Styles) một cách trực quan, an toàn mà không cần can thiệp trực tiếp vào mã nguồn.

## 🚀 Khởi chạy hệ thống

Mở terminal tại thư mục gốc của dự án (`write_blog`) và chạy lệnh sau:

```bash
streamlit run ui/app.py
```

Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ `http://localhost:8501`.

## 🧭 Cấu trúc Giao diện

Giao diện gồm **Sidebar (Ngăn Lựa chọn Chế độ)** và **4 Tab chức năng chính**.

### 1. Sidebar - Ngăn Lựa chọn Chế độ (Writing Mode Switcher)
Nằm ở góc trái màn hình, Sidebar cho phép bạn chuyển đổi linh hoạt giữa 2 chế độ viết:
- 🌊 **Deep Blog Mode (7 Agents):** Dành cho bài viết dài, phản tư sâu sắc.
- ⚡ **Moment Blog Mode (6 Agents):** Dành cho ghi chép khoảnh khắc nhanh, lắng đọng.

*Lưu ý: Khi bạn chuyển đổi chế độ, toàn bộ danh sách Style và các thiết lập ở các Tab bên phải sẽ tự động cập nhật tương ứng với chế độ đang chọn.*

### 2. Tab 1: 📚 Style Gallery (Bộ sưu tập Văn phong)
Nơi hiển thị toàn bộ các Style hiện có trong hệ thống dưới dạng thẻ (Card UI).
- **Phân loại Style:**
  - `🔒 SYSTEM STYLE`: Style mặc định của hệ thống (Ví dụ: `reflective`, `provocative`). Bạn **không thể xóa** hoặc **đổi slug** của System Style để đảm bảo an toàn hệ thống.
  - `✨ CUSTOM STYLE`: Style do bạn tự tạo. Có toàn quyền chỉnh sửa và xóa bỏ.
- **Thao tác nhanh:**
  - **✏️ Sửa Editor:** Chọn Style này và tự động chuyển sang Tab 3 (YAML Code Editor) để chỉnh sửa file cấu hình.
  - **🏷️ Đổi tên:** Mở hộp thoại (Modal) để thay đổi Tên hiển thị (Display Name) hoặc Slug hệ thống (tên thư mục). *Hệ thống quản lý bí danh (Alias) tự động ghi nhận slug cũ để đảm bảo các bài viết cũ vẫn tương thích 100%.*
  - **🗑️ Xóa:** Xóa vĩnh viễn Custom Style (có hộp thoại xác nhận).

### 3. Tab 2: 🎨 Style Studio (Kiến tạo Văn phong mới)
Cho phép bạn tạo ra một phong cách viết mới toanh bằng cách nhân bản (Clone) từ một phong cách đã có sẵn.
- **Cách thực hiện:**
  1. Nhập **Tên hiển thị** (Ví dụ: `Zen Minimalist`).
  2. Nhập **Slug hệ thống** (Ghi thường, không dấu, ngăn cách bằng gạch ngang, ví dụ: `zen-minimalist`).
  3. Chọn **Style gốc để nhân bản** (Ví dụ: `reflective`).
  4. Nhập Mô tả phong cách.
  5. Bấm **🚀 Kiến tạo Style mới**.
- Hệ thống sẽ sao chép toàn bộ prompt của Style gốc sang thư mục mới an toàn. Sau đó, bạn có thể sang Tab 3 để tùy chỉnh theo ý thích.

### 4. Tab 3: 💻 YAML Code Editor (Trình soạn thảo Cấu hình)
Nơi bạn trực tiếp chỉnh sửa "bộ não" (Prompts, Rules, Guardrails) của từng Agent.
- Tích hợp trình soạn thảo code cao cấp (có đánh số dòng, highlight cú pháp) hoặc chế độ dự phòng văn bản thuần (Fallback).
- **Quy trình chỉnh sửa an toàn:**
  - Khi bạn bấm **💾 Lưu thay đổi vào File**, hệ thống sẽ kích hoạt **Trình kiểm duyệt YAML (Validator)**.
  - Nếu file bị lỗi cú pháp, thiếu từ khóa tối quan trọng (như `tasks` hay `supreme_rule`), hệ thống sẽ **hiển thị cảnh báo đỏ và chặn lưu** để tránh làm sập luồng workflow.
  - Nếu file thiếu các quy tắc chống bịa đặt (như thiếu `rules` hay `do_not`), hệ thống hiển thị **cảnh báo vàng** nhắc nhở, nhưng vẫn cho phép lưu.

### 5. Tab 4: 🧪 Live Workbench (Bàn Kiểm chứng Hợp đồng)
Cho phép bạn kiểm tra nhanh (Dry-Run) xem Style bạn vừa tạo/sửa có định tuyến hợp lệ hay không **mà không hề tốn phí API (Quota)**.
- **Cách thực hiện:**
  1. Chọn Style cần kiểm chứng.
  2. Chọn sử dụng văn bản mẫu (Template) hoặc tự dán văn bản nháp của bạn vào.
  3. Bấm **⚡ Chạy Kiểm chứng Dry-Run ngay**.
- **Kết quả:** Quá trình chỉ mất 1-2 giây. Hệ thống sẽ báo cáo chi tiết nếu cấu trúc file hợp lệ, đồng thời hiển thị mô phỏng các Artifact (tệp kết quả) sẽ được tạo ra trong tiến trình thật.

## 🛡️ Cơ chế An toàn (Behind the Scenes)
- **Fail-Fast Routing:** Nếu Style bị thiếu bất kỳ file Agent nào, hệ thống sẽ phát cảnh báo rõ ràng thay vì tự động chạy lỗi.
- **Atomic Write & Rollback:** Các thao tác lưu file hoặc nhân bản luôn sử dụng tiến trình an toàn nhất (ghi ra file tạm `.tmp` trước khi lưu chính thức). Nếu có trục trặc, hệ thống sẽ hoàn tác (Rollback) 100% để bảo vệ toàn vẹn dữ liệu.
