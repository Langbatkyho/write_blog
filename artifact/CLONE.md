# Tạo bản Mindful Blog Workflow cho riêng bạn

Mỗi người trong team dùng một bản Artifact riêng trên claude.ai. Lịch sử viết của bạn nằm trong vùng riêng của tài khoản bạn; người khác, kể cả người chia sẻ file cho bạn, không đọc được. Mỗi lần chạy tốn quota Claude của chính bạn.

Bản của bạn là **một file HTML** (`artifact/dist/index.html`) được publish thành Artifact dưới tài khoản của bạn.

## Cần có

- Tài khoản trong tổ chức Claude Team.
- Claude Code (bản desktop, web hoặc dòng lệnh). Đây là cách đã dùng để publish bản của owner. Cách publish từ cửa sổ chat thường của claude.ai chưa được kiểm chứng.

## Tạo bản lần đầu

1. **Lấy file trang**, chọn một trong hai cách:
   - Có quyền đọc repo `write_blog`: mở repo trong Claude Code rồi chạy
     ```
     python artifact/build_html.py
     ```
     File được tạo ở `artifact/dist/index.html`.
   - Không có repo: nhận file `index.html` từ owner, đặt vào thư mục làm việc của Claude Code.
2. **Nhắn cho Claude Code:**
   > Publish file `artifact/dist/index.html` thành một Artifact mới. Capabilities: `{"sample": {}, "downloads": true, "db": {}, "user": {}}`. Icon: `pen`.

   Claude Code trả về một link dạng `https://claude.ai/artifact/...`.
3. **Lưu link này lại.** Đây là bản của bạn; lịch sử viết gắn với đúng link này.
4. **Mở link và kiểm tra:**
   - Chip "Claude: sẵn sàng" và "Lưu trữ: sẵn sàng".
   - Chạy thử một bài; sau khi xong, bài xuất hiện trong mục "Lịch sử".
   - Tải lại trang: mục "Lịch sử" vẫn còn bài đó.

## Cập nhật khi có bản mới

1. Lấy file `index.html` mới (build lại từ repo, hoặc nhận từ owner).
2. Nhắn cho Claude Code:
   > Cập nhật Artifact `<link của bạn>` bằng file `artifact/dist/index.html`, giữ nguyên capabilities.
3. Mở lại link, xem chip "Phiên bản" khớp với phiên bản owner thông báo. Lịch sử cũ vẫn còn.

**Luôn cập nhật vào đúng link cũ.** Publish thành link mới sẽ tạo một bản khác với lịch sử trống; dữ liệu ở bản cũ không tự chuyển sang.

## Lưu ý

- **Không cần chia sẻ** bản của bạn cho ai. Nếu lỡ chia sẻ, người khác cũng không đọc được lịch sử của bạn, nhưng họ sẽ dùng quota của chính họ khi chạy.
- **Giới hạn lưu trữ:** mỗi Artifact giữ tối đa 25.000 document. Mỗi lần chạy dùng 1 document cho lần chạy, cộng 6 (Moment) hoặc 7 (Deep) document cho các bước.
- **Giữ bản sao ngoài claude.ai:** nút "Tải zip (thư mục run)" xuất đúng bố cục thư mục run của engine Python. Có thể giải nén vào `runs/` của repo để chạy learning loop bằng Python.
- **Style của riêng bạn** (Voice Lab) sẽ có ở bản sau; hiện tại trang dùng các style hệ thống có trong repo.
