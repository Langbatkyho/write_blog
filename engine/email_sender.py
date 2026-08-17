from __future__ import annotations

import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
from pathlib import Path

import requests

from engine.app_logger import log as app_log
from engine.utils import read_text


def _build_attachments(mode: str, human_edited: str, r_dir: Path | None) -> list[dict]:
    """Tạo danh sách attachment dạng Resend API format."""
    attachments = []

    def _make(filename: str, content: str) -> dict:
        return {
            "filename": filename,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }

    if mode == "deep":
        attachments.append(_make("final_blog.txt", human_edited))
        if r_dir and (r_dir / "coaching_report.md").exists():
            attachments.append(_make("coaching_report.txt", read_text(r_dir / "coaching_report.md")))
        if r_dir and (r_dir / "future_reflection.md").exists():
            attachments.append(_make("future_reflection.txt", read_text(r_dir / "future_reflection.md")))
    else:
        attachments.append(_make("final_moment.txt", human_edited))
        if r_dir and (r_dir / "witness_report.md").exists():
            attachments.append(_make("witness_report.txt", read_text(r_dir / "witness_report.md")))

    return attachments


def _build_body(mode: str, attachments: list[dict]) -> str:
    today_str = datetime.now().strftime("%d/%m/%Y")
    mode_label = "Deep Blog" if mode == "deep" else "Moment Blog"
    filenames = [a["filename"] for a in attachments]
    file_list = "\n".join(f"- {f}" for f in filenames)
    return (
        f"Xin chào,\n\n"
        f"happiLab gửi bạn kết quả bài viết {mode_label} vào ngày {today_str}.\n\n"
        f"Danh sách file đính kèm (.txt):\n{file_list}\n\n"
        f"Chúc bạn có những trải nghiệm viết đầy cảm hứng cùng happiLab!\n"
    )


def send_blog_email(
    *,
    recipient: str,
    mode: str,
    human_edited: str,
    run_dir: str | Path | None = None,
) -> bool:
    """Gửi email kết quả blog qua Resend HTTP API (tránh bị chặn SMTP trên Render)."""
    if not recipient or "@" not in recipient:
        raise ValueError("Địa chỉ email người nhận không hợp lệ.")

    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Chưa cấu hình RESEND_API_KEY trong biến môi trường. "
            "Đăng ký miễn phí tại resend.com, sau đó thêm key vào Render Dashboard."
        )

    sender_address = os.getenv("RESEND_FROM_EMAIL", "happilab@resend.dev").strip()
    r_dir = Path(run_dir) if run_dir else None
    mode_label = "Deep Blog" if mode == "deep" else "Moment Blog"
    today_str = datetime.now().strftime("%d/%m/%Y")

    attachments = _build_attachments(mode, human_edited, r_dir)
    body_text = _build_body(mode, attachments)

    payload = {
        "from": sender_address,
        "to": [recipient],
        "subject": f"[happiLab] Kết quả bài viết {mode_label} - {today_str}",
        "text": body_text,
        "attachments": attachments,
    }

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        if resp.status_code in (200, 201):
            app_log("EMAIL", f"Đã gửi email thành công tới {recipient}", level="INFO")
            return True
        else:
            err_msg = resp.json().get("message", resp.text)
            app_log("EMAIL", f"Resend API lỗi {resp.status_code}: {err_msg}", level="ERROR")
            raise RuntimeError(f"Gửi email thất bại ({resp.status_code}): {err_msg}")
    except requests.RequestException as exc:
        app_log("EMAIL", f"Lỗi kết nối Resend API: {exc}", level="ERROR")
        raise RuntimeError(f"Không thể kết nối Resend API: {exc}") from exc
