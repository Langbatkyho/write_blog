import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engine.email_sender import send_blog_email


def test_send_blog_email_invalid_recipient():
    with pytest.raises(ValueError, match="Địa chỉ email người nhận không hợp lệ"):
        send_blog_email(
            recipient="invalid_email",
            mode="deep",
            human_edited="Nội dung bài viết",
        )


def test_send_blog_email_missing_credentials(monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="Chưa cấu hình SMTP_USER"):
        send_blog_email(
            recipient="test@example.com",
            mode="deep",
            human_edited="Nội dung bài viết",
        )


def test_send_blog_email_deep_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "secretapppwd")

    # Tạo mock run_dir với các file report
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()
    (run_dir / "coaching_report.md").write_text("Coaching feedback content", encoding="utf-8")
    (run_dir / "future_reflection.md").write_text("Future reflection content", encoding="utf-8")

    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_server

        success = send_blog_email(
            recipient="user@example.com",
            mode="deep",
            human_edited="Nội dung bài viết Deep hoàn chỉnh",
            run_dir=run_dir,
        )

        assert success is True
        mock_server.login.assert_called_once_with("sender@gmail.com", "secretapppwd")
        mock_server.send_message.assert_called_once()

        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["To"] == "user@example.com"
        assert sent_msg["From"] == "sender@gmail.com"
        assert "Deep Blog" in sent_msg["Subject"]

        # Kiểm tra attachments
        payloads = sent_msg.get_payload()
        filenames = [p.get_filename() for p in payloads if p.get_filename()]
        assert "final_blog.txt" in filenames
        assert "coaching_report.txt" in filenames
        assert "future_reflection.txt" in filenames


def test_send_blog_email_moment_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "secretapppwd")

    # Tạo mock run_dir với file witness report
    run_dir = tmp_path / "test_run_moment"
    run_dir.mkdir()
    (run_dir / "witness_report.md").write_text("Witness report content", encoding="utf-8")

    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_server

        success = send_blog_email(
            recipient="user@example.com",
            mode="moment",
            human_edited="Nội dung bài viết Moment hoàn chỉnh",
            run_dir=run_dir,
        )

        assert success is True
        mock_server.login.assert_called_once_with("sender@gmail.com", "secretapppwd")
        mock_server.send_message.assert_called_once()

        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["To"] == "user@example.com"
        assert "Moment Blog" in sent_msg["Subject"]

        # Kiểm tra attachments
        payloads = sent_msg.get_payload()
        filenames = [p.get_filename() for p in payloads if p.get_filename()]
        assert "final_moment.txt" in filenames
        assert "witness_report.txt" in filenames
