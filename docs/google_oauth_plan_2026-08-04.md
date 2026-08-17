# Kế hoạch triển khai Google OAuth thuần Python (Phương án B)

Triển khai luồng xác thực Google OAuth 2.0 trực tiếp bằng Python ngay trong Streamlit. Phương án này siêu tốc, không cần Node.js, không cần Custom Component.

## User Review Required

> [!IMPORTANT]  
> Chúng ta sẽ không sử dụng thư viện bên thứ 3 (như `streamlit-google-auth`) vì chúng dễ lỗi thời. Thay vào đó, tôi sẽ tự code luồng OAuth (chỉ khoảng 50 dòng) dùng module `requests` có sẵn. Luồng hoạt động:
> 1. Trình bày nút "Đăng nhập Google".
> 2. Chuyển hướng user tới Google để cấp quyền.
> 3. Google redirect về app kèm mã `code` trên URL.
> 4. App đọc `code`, đổi lấy thông tin user, lưu vào `st.session_state` và xóa URL param.

> [!WARNING]
> Theo yêu cầu của bạn, session sẽ chỉ lưu trong bộ nhớ của Streamlit. **Nếu user F5 trình duyệt, họ sẽ phải bấm đăng nhập lại.**

## Open Questions

> [!CAUTION]
> 1. **Môi trường Render**: Bạn cần đảm bảo cấu hình `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, và `REDIRECT_URI` (vd: `https://<ten-app>.onrender.com`) vào Environment Variables trên Render.
> 2. **Whitelist Email**: Tôi sẽ thêm một mảng `ALLOWED_EMAILS` trong code để bạn dễ dàng quản lý.

## Proposed Changes

---

### Xác thực & Xử lý OAuth

#### [NEW] `ui/auth.py`
Tạo file xử lý logic đăng nhập:
- Hàm `get_login_url()`: Tạo URL Google Auth.
- Hàm `get_user_info(code)`: Gọi Google API để đổi code lấy profile.
- Hàm `require_login()`: Component UI hiển thị giao diện đăng nhập nếu chưa có session. Hàm này sẽ chặn (st.stop()) mọi phần code phía dưới nếu chưa login thành công hoặc email không hợp lệ.

---

### Tích hợp vào Ứng dụng chính

#### [MODIFY] `ui/app.py`
- Import `require_login` từ `ui/auth.py`.
- Đặt `require_login()` ở ngay đầu script (hoặc đầu phần giao diện chính), sau `st.set_page_config` và khởi tạo state. Toàn bộ logic bên dưới sẽ được bảo vệ.

#### [MODIFY] `ui/state.py`
- Bổ sung biến trạng thái `st.session_state.user_info` để lưu email/tên của user.

## Verification Plan

### Automated Tests
- Kiểm tra syntax bằng Ruff/Pytest nếu có.

### Manual Verification
1. Chạy `streamlit run ui/app.py` ở local.
2. Thêm tạm `.env` (Client ID/Secret) và cấu hình Redirect URI là `http://localhost:8501`.
3. Bấm nút đăng nhập -> Chuyển hướng sang Google -> Xác nhận -> Trở về app.
4. App hiện nội dung gốc (bypass được màn hình khóa) và báo log thành công.
5. F5 trang -> Trang khóa lại như thiết kế.
