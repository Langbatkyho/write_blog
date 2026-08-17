from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from engine.app_logger import log as app_log
from engine.utils import read_text


def send_blog_email(
    *,
    recipient: str,
    mode: str,
    human_edited: str,
    run_dir: str | Path | None = None,
) -> bool:
    """Gửi email chứa bài viết đã sửa và các báo cáo phân tích đính kèm dạng .txt."""
    if not recipient or "@" not in recipient:
        raise ValueError("Địa chỉ email người nhận không hợp lệ.")

    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_APP_PASSWORD", "").strip()

    if not smtp_user or not smtp_password:
        raise ValueError(
            "Chưa cấu hình SMTP_USER hoặc SMTP_APP_PASSWORD trong biến môi trường. "
            "Vui lòng thiết lập trên Render Dashboard hoặc file .env."
        )

    r_dir = Path(run_dir) if run_dir else None
    today_str = datetime.now().strftime("%d/%m/%Y")
    mode_label = "Deep Blog" if mode == "deep" else "Moment Blog"

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = f"[happiLab] Kết quả bài viết {mode_label} - {today_str}"

    # Body email
    body_lines = [
        "Xin chào,\n",
        f"happiLab gửi bạn kết quả bài viết {mode_label} đã qua xử lý và chỉnh sửa vào ngày {today_str}.\n",
        "Danh sách file đính kèm dạng văn bản (.txt):",
    ]

    # Chuẩn bị danh sách attachment: (filename, content)
    attachments: list[tuple[str, str]] = []

    if mode == "deep":
        attachments.append(("final_blog.txt", human_edited))
        body_lines.append("- final_blog.txt: Bản bài viết hoàn thiện của bạn.")

        if r_dir and (r_dir / "coaching_report.md").exists():
            coaching_content = read_text(r_dir / "coaching_report.md")
            attachments.append(("coaching_report.txt", coaching_content))
            body_lines.append("- coaching_report.txt: Báo cáo phản hồi từ Coach Agent.")

        if r_dir and (r_dir / "future_reflection.md").exists():
            future_content = read_text(r_dir / "future_reflection.md")
            attachments.append(("future_reflection.txt", future_content))
            body_lines.append("- future_reflection.txt: Góc nhìn từ Future Self.")
    else:
        attachments.append(("final_moment.txt", human_edited))
        body_lines.append("- final_moment.txt: Bản bài viết khoảnh khắc hoàn thiện của bạn.")

        if r_dir and (r_dir / "witness_report.md").exists():
            witness_content = read_text(r_dir / "witness_report.md")
            attachments.append(("witness_report.txt", witness_content))
            body_lines.append("- witness_report.txt: Báo cáo phản hồi từ Gentle Witness.")

    body_lines.append("\nChúc bạn có những trải nghiệm viết đầy cảm hứng cùng happiLab!\n")
    body_text = "\n".join(body_lines)

    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # Đính kèm các file .txt
    for filename, content in attachments:
        part = MIMEText(content, "plain", "utf-8")
        part.add_header(
            "Content-Disposition",
            f"attachment; filename=\"{filename}\"",
        )
        msg.attach(part)

    # Gửi qua Gmail SMTP SSL (port 465)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        app_log("EMAIL", f"Đã gửi email kết quả thành công tới {recipient}", level="INFO")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        app_log("EMAIL", f"Lỗi xác thực SMTP: {exc}", level="ERROR")
        raise RuntimeError("Xác thực SMTP thất bại. Vui lòng kiểm tra lại SMTP_USER và App Password.") from exc
    except Exception as exc:
        app_log("EMAIL", f"Lỗi khi gửi email: {exc}", level="ERROR")
        raise RuntimeError(f"Không thể gửi email: {exc}") from exc
