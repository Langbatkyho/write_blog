# Hướng dẫn Deploy Streamlit lên Render.com tích hợp Auto Git Sync

Tài liệu này hướng dẫn chi tiết cách đưa codebase local (sử dụng giao diện Streamlit) lên nền tảng Render.com dưới dạng một **Web Service**, đồng thời xử lý triệt để vấn đề mất dữ liệu trên ổ cứng tạm (Ephemeral Disk) bằng kỹ thuật **Auto Git Sync** (Tự động commit & push các bài blog/style vừa tạo ngược trở lại GitHub repository).

> [!WARNING]
> Kỹ thuật Auto Git Sync yêu cầu Server trên Render có quyền đẩy code (push) ngược lại GitHub. Do đó, bạn cần tạo **GitHub Personal Access Token (PAT)** thay vì chỉ kết nối repo thông thường.

---

## Phần 1: Cài đặt tính năng Auto Git Sync vào Codebase

Bạn cần bổ sung một hàm chạy lệnh Git ngầm trong Python để tự động add, commit và push các thay đổi ở các thư mục như `runs/` (chứa blog log) hoặc `skills/` (chứa style configs).

### 1. Viết hàm `auto_git_sync`
Tạo hoặc mở file `engine/utils.py` (hoặc `engine/style_manager.py`) và thêm đoạn code sau:

```python
import subprocess
import os

def auto_git_sync(target_path: str, commit_message: str = "Tự động lưu thay đổi") -> bool:
    """
    Tự động Git Add, Commit và Push cho một thư mục hoặc file cụ thể.
    """
    # Chỉ chạy trên môi trường có biến RENDER (chạy trên server)
    # hoặc bạn có thể bỏ IF này nếu muốn chạy cả trên local
    if not os.environ.get("RENDER"):
        print("[Git Sync] Chạy ở Local, bỏ qua Auto Git Sync.")
        return False
        
    try:
        # Cấu hình user git (Tránh lỗi chưa setup author khi deploy lần đầu)
        subprocess.run(["git", "config", "user.name", "Render Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@render.com"], check=True)

        # Trỏ URL push sử dụng Token để có quyền write
        # Cấu trúc: https://<USERNAME>:<TOKEN>@github.com/<USERNAME>/<REPO_NAME>.git
        github_user = os.environ.get("GITHUB_USERNAME")
        github_token = os.environ.get("GITHUB_TOKEN")
        repo_name = os.environ.get("GITHUB_REPO_NAME") # VD: writeblog_madeinlangbatkyho
        
        if github_user and github_token and repo_name:
            remote_url = f"https://{github_user}:{github_token}@github.com/{github_user}/{repo_name}.git"
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)

        # 1. Git Add
        subprocess.run(["git", "add", target_path], check=True)
        
        # Kiểm tra xem có thay đổi nào để commit không
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("[Git Sync] Không có file nào thay đổi.")
            return True

        # 2. Git Commit
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # 3. Git Push
        subprocess.run(["git", "push", "origin", "HEAD:main"], check=True) # Thay 'main' nếu branch của bạn tên khác
        
        print(f"[Git Sync] Đã push thành công: {commit_message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Git Sync Lỗi] Quá trình git thất bại: {e}")
        return False
    except Exception as e:
        print(f"[Git Sync Lỗi] Lỗi hệ thống: {e}")
        return False
```

### 2. Tích hợp vào quy trình tạo Blog & tạo Style
Mỗi khi logic code của bạn kết thúc việc ghi file, hãy gọi hàm này:

```python
# Ví dụ ở cuối hàm lưu một bài blog mới vào folder `runs/`
from engine.utils import auto_git_sync

def save_blog_run(run_id, data):
    # ... code lưu file ...
    
    # Kích hoạt đồng bộ
    auto_git_sync(
        target_path="runs/", 
        commit_message=f"feat(run): Tự động lưu blog workflow {run_id}"
    )
```

---

## Phần 2: Chuẩn bị Codebase cho Render

1. **Tạo `requirements.txt`**:
   Đảm bảo tại thư mục gốc có file `requirements.txt` chứa các package cần thiết. Ví dụ:
   ```text
   streamlit>=1.20.0
   pydantic>=2.0.0
   pyyaml>=6.0.1
   requests>=2.31.0
   ```

2. **Cấu hình Streamlit (Tùy chọn nhưng khuyên dùng)**:
   Để Streamlit không hiện các thông báo rác khi chạy trên server, tạo file `.streamlit/config.toml` (nếu chưa có) và thêm:
   ```toml
   [server]
   headless = true
   enableCORS = false
   enableXsrfProtection = false
   ```

---

## Phần 3: Lấy Token GitHub (Personal Access Token)

Render.com mặc định chỉ có quyền Đọc (Read) để pull code. Bạn cần cấp quyền Ghi (Write).
1. Đăng nhập GitHub, vào **Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**.
2. Bấm **Generate new token (classic)**.
3. Phần Note điền "Render Auto Sync".
4. Ở phần Select scopes, tích chọn ô **`repo`** (Full control of private repositories).
5. Bấm Generate. **Copy mã Token dài vừa tạo** (Nó chỉ hiện 1 lần).

---

## Phần 4: Thiết lập Web Service trên Render.com

1. Đăng nhập [Render.com](https://render.com/), tạo một **New Web Service**.
2. Kết nối với repo GitHub chứa codebase local của bạn.
3. Thiết lập các thông số sau trong phần Cấu hình:
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**: 
     > [!IMPORTANT]
     > Đây là lệnh ép Streamlit lấy động giá trị `$PORT` do hệ thống Render cấp phát, thay vì cổng 8501 mặc định:
     ```bash
     streamlit run ui/app.py --server.port $PORT --server.address 0.0.0.0
     ```

4. Vào mục **Environment Variables (Biến môi trường)**, tạo các biến sau:
   - `OPENAI_API_KEY`: API Key OpenAI của bạn
   - `GEMINI_API_KEY`: API Key Gemini của bạn
   - `PYTHON_VERSION`: `3.10.0` (Khuyến khích khai báo cụ thể để tránh lỗi không tương thích bản Python mặc định).
   - `GITHUB_USERNAME`: Tên user GitHub của bạn (VD: `nguyenhan1982`)
   - `GITHUB_TOKEN`: Mã Token dài bạn vừa copy ở Phần 3.
   - `GITHUB_REPO_NAME`: Tên của Repo trên GitHub (VD: `write_blog`)

5. Lưu lại và nhấn **Deploy**.

> [!TIP]
> **Kiểm tra thành quả:**
> Sau khi deploy hoàn tất, hãy mở trang web Streamlit của bạn do Render cung cấp. Thử tạo một Profile hoặc chạy sinh một bài Blog nháp. Chờ khoảng 10 giây, sau đó mở trang GitHub Repository của bạn và kiểm tra mục Commits. Bạn sẽ thấy một commit tự động với nội dung `"feat(run): Tự động lưu blog..."` do Render đẩy ngược lên.
