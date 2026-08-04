# Kế hoạch tích hợp đăng nhập Google OAuth (Cập nhật theo phản biện)

Kế hoạch này mô tả cách tối ưu hóa luồng xác thực Google OAuth đã có sẵn trong dự án thay vì sử dụng thư viện ngoài, nhằm đảm bảo tính ổn định, ít rủi ro và cải thiện trải nghiệm người dùng.

## Mục tiêu thay đổi

- Sửa lỗi thiếu dependencies có thể gây sập ứng dụng khi deploy.
- Cải thiện trải nghiệm đăng nhập (không bắt buộc người dùng ấn đồng ý nhiều lần).
- Bổ sung tính năng đăng xuất cho ứng dụng.

## Chi tiết các thay đổi (Proposed Changes)

### 1. Cập nhật Dependencies

#### [MODIFY] requirements.txt
- Thêm thư viện `python-dotenv` để ứng dụng có thể đọc biến môi trường từ file `.env` hoặc cấu hình trên Render mà không bị lỗi `ModuleNotFoundError`.

### 2. Tối ưu UX xác thực

#### [MODIFY] ui/auth.py
- Chỉnh sửa tham số `prompt="consent"` thành `prompt="select_account"` trong hàm `get_login_url()`. Việc này giúp người dùng chỉ cần chọn tài khoản thay vì phải cấp quyền lại từ đầu mỗi lần đăng nhập.

### 3. Bổ sung tính năng Đăng xuất và User Info

#### [MODIFY] ui/app.py
- Bổ sung logic hiển thị thông tin người dùng đang đăng nhập (Avatar, Email) vào thanh Sidebar.
- Thêm một nút **Đăng xuất (Logout)**. Khi nhấn nút này, hệ thống sẽ xóa thông tin `user_info` khỏi `st.session_state` và làm mới trang để trở về màn hình đăng nhập.

## Hướng dẫn thiết lập dành cho người dùng

### Cấu hình Google Cloud Console

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo Project mới (hoặc chọn Project hiện có).
3. Vào **APIs & Services** > **OAuth consent screen**:
   - Chọn **External** và điền tên ứng dụng (vd: "happiLab Blog").
   - Lưu và tiếp tục cho đến khi hoàn thành.
4. Vào **APIs & Services** > **Credentials**:
   - Bấm **Create Credentials** > **OAuth client ID**.
   - Application type: **Web application**.
   - Authorized JavaScript origins: Thêm URL trang web của bạn (vd: `https://ten-app-cua-ban.onrender.com`).
   - Authorized redirect URIs: Thêm URL trang web (vd: `https://ten-app-cua-ban.onrender.com/`). Với local: `http://localhost:8501`.
   - Bấm Create và lưu lại **Client ID** cùng **Client Secret**.

### Cấu hình Render.com

Trong Dashboard của Render, vào phần **Environment Variables** của ứng dụng và thêm:

- `GOOGLE_CLIENT_ID`: (Lấy từ bước trên)
- `GOOGLE_CLIENT_SECRET`: (Lấy từ bước trên)
- `REDIRECT_URI`: `https://ten-app-cua-ban.onrender.com/`
- `ALLOWED_EMAILS`: `email1@gmail.com,email2@gmail.com`
