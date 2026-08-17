import json
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


def test_send_blog_email_missing_api_key(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with pytest.raises(ValueError, match="RESEND_API_KEY"):
        send_blog_email(
            recipient="test@example.com",
            mode="deep",
            human_edited="Nội dung bài viết",
        )


def test_send_blog_email_deep_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

    run_dir = tmp_path / "test_run"
    run_dir.mkdir()
    (run_dir / "coaching_report.md").write_text("Coaching feedback", encoding="utf-8")
    (run_dir / "future_reflection.md").write_text("Future reflection", encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "abc123"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = send_blog_email(
            recipient="user@example.com",
            mode="deep",
            human_edited="Bài viết Deep hoàn chỉnh",
            run_dir=run_dir,
        )

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]

        assert payload["to"] == ["user@example.com"]
        assert "Deep Blog" in payload["subject"]
        assert "[happiLab]" in payload["subject"]
        filenames = [a["filename"] for a in payload["attachments"]]
        assert "final_blog.txt" in filenames
        assert "coaching_report.txt" in filenames
        assert "future_reflection.txt" in filenames


def test_send_blog_email_moment_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

    run_dir = tmp_path / "test_run_moment"
    run_dir.mkdir()
    (run_dir / "witness_report.md").write_text("Witness report content", encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "def456"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = send_blog_email(
            recipient="user@example.com",
            mode="moment",
            human_edited="Bài viết Moment hoàn chỉnh",
            run_dir=run_dir,
        )

        assert result is True
        payload = mock_post.call_args.kwargs["json"]
        assert "Moment Blog" in payload["subject"]
        filenames = [a["filename"] for a in payload["attachments"]]
        assert "final_moment.txt" in filenames
        assert "witness_report.txt" in filenames


def test_send_blog_email_api_error(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_bad_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"message": "API key không hợp lệ"}

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="401"):
            send_blog_email(
                recipient="user@example.com",
                mode="deep",
                human_edited="Test content",
            )
