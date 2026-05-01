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


# --- T7a.5 fixer tests -----------------------------------------------------


def test_build_html_body_escapes_script() -> None:
    """build_html_body must autoescape user-supplied data (XSS defense)."""
    html = email_mod.build_html_body(
        "<p>안녕하세요 {{ vendor }}님,</p><p>{{ message }}</p>",
        {"vendor": "<script>alert(1)</script>", "message": "ok"},
    )
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_build_html_body_supports_korean() -> None:
    """Korean text passes through autoescape unchanged; HTML metachars escaped."""
    html = email_mod.build_html_body(
        "<p>{{ greeting }}</p>",
        {"greeting": "안녕하세요 & 환영합니다"},
    )
    assert "안녕하세요" in html
    assert "&amp;" in html  # & must be escaped


def test_build_html_body_strict_undefined() -> None:
    """Missing context variables must raise (StrictUndefined parity with template)."""
    import jinja2

    with pytest.raises(jinja2.UndefinedError):
        email_mod.build_html_body("<p>{{ missing }}</p>", {})


def test_build_message_invalid_sender_format_raises() -> None:
    with pytest.raises(ValueError, match=r"valid email"):
        email_mod.build_message(
            to="r@example.com",
            subject="x",
            body_text="body",
            sender="not-an-email",
        )


def test_build_message_sender_with_display_name_ok() -> None:
    msg = email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
        sender="AX상사 <sales@ax.example.com>",
    )
    assert msg["From"] == "AX상사 <sales@ax.example.com>"


def test_build_message_invalid_to_format_raises() -> None:
    with pytest.raises(ValueError, match=r"to field"):
        email_mod.build_message(
            to="garbage",
            subject="x",
            body_text="body",
            sender="s@example.com",
        )


def test_build_message_to_multiple_addresses_ok() -> None:
    msg = email_mod.build_message(
        to="a@b.com, c@d.com",
        subject="x",
        body_text="body",
        sender="s@example.com",
    )
    assert msg["To"] == "a@b.com, c@d.com"


def test_build_message_to_one_invalid_in_multiple_raises() -> None:
    with pytest.raises(ValueError, match=r"to field"):
        email_mod.build_message(
            to="a@b.com, garbage",
            subject="x",
            body_text="body",
            sender="s@example.com",
        )


def test_build_message_zero_byte_attachment_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")

    captured: list[str] = []

    class _StubLogger:
        def info(self, msg: str) -> None: ...
        def success(self, msg: str) -> None: ...
        def warning(self, msg: str) -> None:
            captured.append(msg)

        def error(self, msg: str) -> None: ...

    from core.common import demo_logger as dl

    monkeypatch.setattr(dl, "demo_logger", lambda _case_id: _StubLogger())

    email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
        attachments=[empty],
        sender="s@example.com",
    )
    assert any("0 bytes" in m and "empty.pdf" in m for m in captured)


def test_build_message_zero_byte_attachment_still_added(tmp_path: Path) -> None:
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    msg = email_mod.build_message(
        to="r@example.com",
        subject="x",
        body_text="body",
        attachments=[empty],
        sender="s@example.com",
    )
    pdf_parts = [p for p in _all_parts(msg) if p.get_content_type() == "application/pdf"]
    assert len(pdf_parts) == 1
    assert pdf_parts[0].get_filename() == "empty.pdf"
