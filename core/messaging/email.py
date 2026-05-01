"""이메일 메시지 빌드 + 발송 (Gmail API primary + SMTP 폴백).

T7a: build_message — EmailMessage 객체 생성 (multipart + HTML + 첨부)
T7b (다음 task): send — 실제 발송 + safe_mode short-circuit

NOTE: 외부 호출은 모듈 참조로 호출 (safe_mode patch 격리)::

    from core.messaging import email
    email.send(...)
"""

from __future__ import annotations

import os
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

GMAIL_ATTACHMENT_LIMIT = 100 * 1024 * 1024  # 100MB

# 시연용 자주 쓰는 MIME 타입 (extension → maintype, subtype)
_MIME_BY_EXT: dict[str, tuple[str, str]] = {
    ".pdf": ("application", "pdf"),
    ".docx": (
        "application",
        "vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    ".xlsx": (
        "application",
        "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    ".png": ("image", "png"),
    ".jpg": ("image", "jpeg"),
    ".jpeg": ("image", "jpeg"),
    ".txt": ("text", "plain"),
    ".csv": ("text", "csv"),
}


def _guess_mime(path: Path) -> tuple[str, str]:
    return _MIME_BY_EXT.get(path.suffix.lower(), ("application", "octet-stream"))


def build_message(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[Path] | None = None,
    sender: str | None = None,
) -> EmailMessage:
    """EmailMessage 객체 빌드 (multipart + HTML + 첨부).

    Args:
        to: 수신자 (복수 시 ", " 콤마 구분).
        subject: 제목.
        body_text: 본문 (text/plain).
        body_html: HTML 본문 (있으면 multipart/alternative).
        attachments: 첨부 파일 경로 리스트.
        sender: 발신자. 미명시 시 ``GMAIL_SENDER`` 환경변수 폴백.

    Raises:
        ValueError: sender 미설정 + ``GMAIL_SENDER`` 미설정.
        ValueError: 첨부 파일 100MB 초과 (Gmail 한계).
        FileNotFoundError: 첨부 파일이 존재하지 않을 때.

    Returns:
        구성된 :class:`EmailMessage`. T7b ``send`` 함수의 입력으로 사용된다.
    """
    sender_addr = sender or os.environ.get("GMAIL_SENDER", "")
    if not sender_addr:
        raise ValueError("sender not provided and GMAIL_SENDER env not set")

    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = sender_addr
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body_text)

    if body_html is not None:
        msg.add_alternative(body_html, subtype="html")

    for path in attachments or []:
        if not path.exists():
            raise FileNotFoundError(f"attachment missing: {path}")
        size = path.stat().st_size
        if size > GMAIL_ATTACHMENT_LIMIT:
            raise ValueError(
                f"attachment {path.name} size {size} exceeds Gmail limit {GMAIL_ATTACHMENT_LIMIT}"
            )
        maintype, subtype = _guess_mime(path)
        msg.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )
    return msg
