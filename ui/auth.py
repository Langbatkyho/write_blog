import os
import urllib.parse
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Cấu hình từ biến môi trường
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8501")

# Danh sách email được phép truy cập (nếu trống thì cho phép tất cả)
ALLOWED_EMAILS = os.environ.get("ALLOWED_EMAILS", "").split(",")
ALLOWED_EMAILS = [email.strip() for email in ALLOWED_EMAILS if email.strip()]

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_login_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    url_params = urllib.parse.urlencode(params)
    return f"{AUTHORIZE_URL}?{url_params}"


def exchange_code_for_token(code: str):
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()


def get_user_info(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(USERINFO_URL, headers=headers)
    response.raise_for_status()
    return response.json()


def require_login():
    """
    Hàm này dùng để bảo vệ ứng dụng.
    Sẽ hiển thị nút đăng nhập nếu chưa có session.
    Sẽ xử lý auth callback nếu có biến 'code' trên URL.
    Sẽ dừng script (st.stop()) nếu auth chưa hoàn tất.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        st.warning("Chưa cấu hình GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET. Tạm thời bỏ qua đăng nhập.")
        return

    # Nếu đã login thành công, bỏ qua bước auth
    if st.session_state.get("user_info") is not None:
        return

    # Xử lý callback nếu nhận được mã auth từ URL
    if "code" in st.query_params:
        code = st.query_params.get("code")
        try:
            tokens = exchange_code_for_token(code)
            access_token = tokens.get("access_token")
            user_info = get_user_info(access_token)
            
            # Validate whitelist
            email = user_info.get("email", "")
            if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
                st.error(f"Tài khoản {email} không có quyền truy cập.")
                # Xóa code để không bị kẹt ở popup lỗi nếu refresh
                if "code" in st.query_params:
                    del st.query_params["code"]
                st.stop()

            # Thành công: lưu vào state và xóa auth code trên URL
            st.session_state["user_info"] = user_info
            if "code" in st.query_params:
                del st.query_params["code"]
            st.rerun()

        except Exception as e:
            st.error(f"Đăng nhập thất bại: {e}")
            if "code" in st.query_params:
                del st.query_params["code"]
            st.stop()

    # Chưa login -> Vẽ UI yêu cầu đăng nhập
    st.markdown("### 🔐 Cần đăng nhập để sử dụng Nhà xuất bản happiLab")
    st.markdown("Vui lòng đăng nhập bằng tài khoản Google để tiếp tục.")
    
    login_url = get_login_url()
    st.markdown(
        f'<a href="{login_url}" target="_self" '
        f'style="display: inline-block; padding: 10px 20px; '
        f'background-color: #4285F4; color: white; text-align: center; '
        f'text-decoration: none; border-radius: 5px; font-weight: bold;">'
        f'Đăng nhập với Google</a>',
        unsafe_allow_html=True
    )
    st.stop()
