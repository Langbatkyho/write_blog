# Hướng dẫn triển khai Google OAuth (Client-side Implicit Flow)

Tài liệu này mô tả chi tiết cách thức cấu trúc và triển khai tính năng Google OAuth bằng **implicit flow** (lấy thẳng access token trên trình duyệt) kết hợp với lưu trữ an toàn bằng **IndexedDB**. Cấu trúc này được trích xuất từ codebase của happiLab và có thể tái sử dụng cho các web app nội bộ khác.

## 1. Kiến trúc chung

- **Thư viện sử dụng**: `@react-oauth/google`
- **Flow**: Implicit flow (`flow: 'implicit'`). Trả về trực tiếp `access_token` thay vì `auth_code`. Không có refresh token. Khi token hết hạn, người dùng phải đăng nhập lại (hoặc thư viện GIS của Google sẽ tự động renew ngầm nếu session còn sống).
- **Lưu trữ bảo mật**: Token được lưu trữ trong **IndexedDB** thay vì `localStorage` hay `sessionStorage` để giảm thiểu rủi ro tấn công XSS đánh cắp token.

## 2. Các file cốt lõi và chức năng

### a) `lib/auth/google-oauth.ts`
Chịu trách nhiệm tương tác với IndexedDB và gọi các API trực tiếp của Google.

- **`openAuthDB()`**: Khởi tạo/Mở kết nối tới IndexedDB (database: `happilab_auth`).
- **`saveAuthState(state)`**, **`loadStoredAuth()`**, **`clearAuthState()`**: Các hàm tiện ích thao tác CRUD token với IndexedDB. Dữ liệu lưu bao gồm: `accessToken`, `expiresAt`, và `userInfo`.
- **`fetchUserInfo(accessToken)`**: Gửi request tới `https://www.googleapis.com/oauth2/v3/userinfo` kèm `Bearer token` để lấy dữ liệu profile của Google (bao gồm `email`, `name`, `picture`).
- **`isTokenExpired(state)`**: Kiểm tra token còn hạn hay không (sử dụng buffer time, ví dụ 5 phút trước khi thực sự hết hạn).

### b) `lib/auth/auth-context.tsx`
React Context quản lý auth state cho toàn bộ ứng dụng.

- **`AuthProvider`**: Bọc bên ngoài ứng dụng. Khi mount, nó gọi `loadStoredAuth()` để hydrate auth state từ IndexedDB. 
- **`login(tokenResponse)`**: Nhận `tokenResponse` từ hook đăng nhập, gọi `fetchUserInfo()`, sau đó lưu cả token và user info vào DB qua `saveAuthState()`. Tại đây, bạn có thể **thêm logic kiểm tra Whitelist Email** (chặn các email không được phép bằng cách throw error trước khi gọi `saveAuthState`).
- **`logout()` / `doLogout()`**: Xóa token khỏi state và IndexedDB thông qua `clearAuthState()`.
- **`getValidToken()`**: Cung cấp hàm lấy token cho các service/API calls. Nếu token hết hạn, tự động clear auth state.
- **`useAuth()`**: Custom hook để các component con sử dụng context.

### c) `components/auth/LoginBanner.tsx` (Hoặc bất kỳ Component UI nào)
Component gọi hàm login của Google.

- Sử dụng hook **`useGoogleLogin`** từ `@react-oauth/google`.
- Cấu hình hook:
  ```typescript
  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      // Gọi auth.login() từ Context
      await auth?.login(tokenResponse);
    },
    onError: () => { /* Xử lý lỗi */ },
    scope: 'openid email profile ...',
    flow: 'implicit',
  });
  ```
- Nút bấm đăng nhập gọi hàm `googleLogin()` khi `onClick`.

## 3. Cách tái sử dụng vào project mới

Để tái sử dụng cấu trúc này cho một project Next.js/React mới:

1. **Cài đặt thư viện**: `npm install @react-oauth/google`
2. **Khai báo Google Provider**: Bọc root app bằng `<GoogleOAuthProvider clientId="YOUR_CLIENT_ID">`.
3. **Copy các file logic**: 
   - Sao chép file thao tác IndexedDB (`google-oauth.ts`).
   - Sao chép file Context (`auth-context.tsx`) và bọc nó bên trong `GoogleOAuthProvider`.
4. **Tích hợp Whitelist**: Trong hàm `login` của `auth-context.tsx`, sau khi fetch user info:
   ```typescript
   const userInfo = await fetchUserInfo(tokenResponse.access_token);
   
   // Kiểm tra email whitelist
   const allowedEmails = ['user1@happilab.vn', 'user2@happilab.vn'];
   if (!allowedEmails.includes(userInfo.email)) {
       throw new Error('WHITELIST_REJECTED');
   }
   
   // Nếu hợp lệ mới lưu state
   await saveAuthState({ ... });
   ```
5. **Tạo Component UI**: Gọi `useGoogleLogin`, bắt các Exception như `WHITELIST_REJECTED` trong block `try-catch` của callback `onSuccess` để hiện popup từ chối truy cập.
