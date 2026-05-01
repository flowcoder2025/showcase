"""Tests for core.messaging.email.build_message (T7a).

T7a scope: build_message — EmailMessage 객체 생성 (multipart + HTML + 첨부).
T7b: send 함수는 별도 task.
"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

from core.messaging import email as email_mod

# --- Helpers ---------------------------------------------------------------


def _all_parts(msg: EmailMessage) -> list[EmailMessage]:
    """Walk and return non-multipart leaf parts."""
    return [part for part in msg.walk() if not part.is_multipart()]


# --- Tests -----------------------------------------------------------------


def test_build_message_text_only() -> None:
    msg = email_mod.build_message(
        to="recipient@example.com",
        subject="Hello",
        body_text="Plain body",
        sender="sender@example.com",
    )
    assert msg["To"] == "recipient@example.com"
    assert msg["Subject"] == "Hello"
    assert msg["From"] == "sender@example.com"

    text_parts = [p for p in _all_parts(msg) if p.get_content_type() == "text/plain"]
    assert len(text_parts) >= 1
    assert "Plain body" in text_parts[0].get_content()


def test_build_message_with_html_alternative() -> None:
    html = "<p>Hello <b>World</b></p>"
    msg = email_mod.build_message(
        to="r@example.com",
        subject="HTML",
        body_text="Hello World",
        body_html=html,
        sender="s@example.com",
    )
    # multipart container expected when HTML alternative is added
    assert msg.is_multipart()
    html_parts = [p for p in _all_parts(msg) if p.get_content_type() == "text/html"]
    assert len(html_parts) >= 1
    assert "<b>World</b>" in html_parts[0].get_content()


def test_build_message_with_pdf_attachment(tmp_path: Path) -> None:
    pdf = tmp_path / "quote.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n0 0 obj\nendobj\n")

    msg = email_mod.build_message(
        to="r@example.com",
        subject="견적서",
        body_text="첨부드립니다",
        attachments=[pdf],
        sender="s@example.com",
    )
    pdf_parts = [p for p in _all_parts(msg) if p.get_content_type() == "application/pdf"]
    assert len(pdf_parts) == 1
    assert pdf_parts[0].get_filename() == "quote.pdf"


def test_build_message_with_multiple_attachments(tmp_path: Path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    xlsx = tmp_path / "b.xlsx"
    xlsx.write_bytes(b"PK\x03\x04fake-xlsx")
    png = tmp_path / "c.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")

    msg = email_mod.build_message(
        to="r@example.com",
        subject="multi",
        body_text="body",
        attachments=[pdf, xlsx, png],
        sender="s@example.com",
    )
    parts = _all_parts(msg)
    types = {p.get_filename(): p.get_content_type() for p in parts if p.get_filename()}
    assert types["a.pdf"] == "application/pdf"
    assert types["b.xlsx"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert types["c.png"] == "image/png"


def test_build_message_attachment_size_limit(tmp_path: Path) -> None:
    big = tmp_path / "big.bin"
    # Create a sparse file just over 100MB without writing actual bytes.
    with big.open("wb") as f:
        f.seek(email_mod.GMAIL_ATTACHMENT_LIMIT + 1)
        f.write(b"\0")

    with pytest.raises(ValueError, match=r"size|limit"):
        email_mod.build_message(
            to="r@example.com",
            subject="big",
            body_text="body",
            attachments=[big],
            sender="s@example.com",
        )


def test_build_message_attachment_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pdf"
    with pytest.raises(FileNotFoundError):
        email_mod.build_message(
            to="r@example.com",
            subject="x",
            body_text="body",
            attachments=[missing],
            sender="s@example.com",
        )


def test_build_message_unknown_extension_uses_octet_stream(tmp_path: Path) -> None:
    weird = tmp_path / "unknown.xyz"
    weird.write_bytes(b"random-bytes")
    msg = email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
        attachments=[weird],
        sender="s@example.com",
    )
    octet = [p for p in _all_parts(msg) if p.get_content_type() == "application/octet-stream"]
    assert len(octet) == 1
    assert octet[0].get_filename() == "unknown.xyz"


def test_build_message_sender_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GMAIL_SENDER", "alice@example.com")
    msg = email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
    )
    assert msg["From"] == "alice@example.com"


def test_build_message_sender_explicit_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GMAIL_SENDER", "alice@y.com")
    msg = email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
        sender="bob@x.com",
    )
    assert msg["From"] == "bob@x.com"


def test_build_message_no_sender_no_env_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GMAIL_SENDER", raising=False)
    with pytest.raises(ValueError, match=r"sender"):
        email_mod.build_message(
            to="r@example.com",
            subject="x",
            body_text="body",
        )


def test_build_message_korean_subject_and_body() -> None:
    msg = email_mod.build_message(
        to="r@example.com",
        subject="견적서 - AX상사",
        body_text="안녕하세요\n견적 첨부합니다.",
        sender="sales@axsangsa.com",
    )
    # Subject header must round-trip correctly via Python's email API
    assert msg["Subject"] == "견적서 - AX상사"

    text_parts = [p for p in _all_parts(msg) if p.get_content_type() == "text/plain"]
    assert any("안녕하세요" in p.get_content() for p in text_parts)
    assert any("견적 첨부합니다" in p.get_content() for p in text_parts)


def test_build_message_date_header_present() -> None:
    msg = email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
        sender="s@example.com",
    )
    date_hdr = msg["Date"]
    assert date_hdr is not None
    # RFC 2822 ish: Day, DD Mon YYYY ...
    assert "," in date_hdr
    assert any(
        mon in date_hdr
        for mon in (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        )
    )


def test_build_message_text_attachment_text_csv(tmp_path: Path) -> None:
    csv = tmp_path / "data.csv"
    csv.write_bytes(b"a,b,c\n1,2,3\n")
    msg = email_mod.build_message(
        to="r@example.com",
        subject="csv",
        body_text="body",
        attachments=[csv],
        sender="s@example.com",
    )
    csv_parts = [p for p in _all_parts(msg) if p.get_content_type() == "text/csv"]
    assert len(csv_parts) == 1
    assert csv_parts[0].get_filename() == "data.csv"


def test_build_message_jpg_jpeg_both_image_jpeg(tmp_path: Path) -> None:
    jpg = tmp_path / "a.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xe0")
    jpeg = tmp_path / "b.jpeg"
    jpeg.write_bytes(b"\xff\xd8\xff\xe0")
    msg = email_mod.build_message(
        to="r@example.com",
        subject="img",
        body_text="body",
        attachments=[jpg, jpeg],
        sender="s@example.com",
    )
    parts = _all_parts(msg)
    types = {p.get_filename(): p.get_content_type() for p in parts if p.get_filename()}
    assert types["a.jpg"] == "image/jpeg"
    assert types["b.jpeg"] == "image/jpeg"
