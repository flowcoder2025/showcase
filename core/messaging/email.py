"""이메일 메시지 빌드 + 발송 (Gmail API primary + SMTP 폴백).

T7a: build_message — EmailMessage 객체 생성 (multipart + HTML + 첨부)
T7a.5: build_html_body 헬퍼 (XSS 방어), sender/to 형식 검증, 0바이트 첨부 warning
T7b (다음 task): send — 실제 발송 + safe_mode short-circuit

NOTE: 외부 호출은 모듈 참조로 호출 (safe_mode patch 격리)::

    from core.messaging import email
    email.send(...)
"""

from __future__ import annotations

import os
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, parseaddr
from pathlib import Path
from typing import Any

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


def _is_valid_addr_spec(email_addr: str) -> bool:
    """RFC 5322 addr-spec 최소 검증 (local@domain.tld)."""
    if not email_addr or "@" not in email_addr:
        return False
    local, _, domain = email_addr.rpartition("@")
    if not local or not domain or "." not in domain:
        return False
    return True


def _validate_email_address(addr: str, *, label: str) -> str:
    """email 주소 형식 검증. 정상 시 원형(원본) 반환.

    ``"Name <addr@host>"`` 형식도 허용 — display name + addr.
    """
    _, email_addr = parseaddr(addr)
    if not _is_valid_addr_spec(email_addr):
        raise ValueError(f"{label} not a valid email address: {addr!r}")
    return addr  # 원형 보존 (display name 포함 가능)


def _validate_to_field(to: str) -> str:
    """to 필드 — 단일 또는 ``", "`` 구분 다중. 각 주소 검증."""
    addrs = getaddresses([to])
    if not addrs:
        raise ValueError(f"to field has no valid addresses: {to!r}")
    for _, email_addr in addrs:
        if not _is_valid_addr_spec(email_addr):
            raise ValueError(f"to field contains invalid address: {email_addr!r} in {to!r}")
    return to


def build_html_body(template_str: str, context: dict[str, Any]) -> str:
    """HTML 메일 본문 빌드 — autoescape 적용 (XSS 방어).

    내부적으로 :func:`core.docgen.template.render_html_string` 사용 (autoescape=True).
    case03에서 ``build_message(body_html=...)`` 에 안전하게 전달 가능.

    Example:
        >>> html = build_html_body(
        ...     "<p>안녕하세요 {{ vendor }}님,</p><p>{{ message }}</p>",
        ...     {"vendor": "<script>alert(1)</script>", "message": "..."},
        ... )
        >>> # vendor의 <script>는 &lt;script&gt;로 escape됨
    """
    from core.docgen import template

    return template.render_html_string(template_str, context)


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
        to: 수신자 (복수 시 ``", "`` 콤마 구분). 각 주소 형식 검증.
        subject: 제목.
        body_text: 본문 (text/plain).
        body_html: HTML 본문. **사용자 데이터 포함 시 사전 escape 필수.**
            안전한 빌드는 :func:`build_html_body` 사용 (autoescape 적용).
        attachments: 첨부 파일 경로 리스트.
        sender: 발신자. 미명시 시 ``GMAIL_SENDER`` 환경변수 폴백.
            ``"Name <addr@host>"`` 형식도 허용. addr-spec 형식 검증.

    Raises:
        ValueError: sender 미설정 + ``GMAIL_SENDER`` 미설정.
        ValueError: sender / to 형식 부적합 (parseaddr 검증 실패).
        ValueError: 첨부 파일 100MB 초과 (Gmail 한계).
        FileNotFoundError: 첨부 파일이 존재하지 않을 때.

    Returns:
        구성된 :class:`EmailMessage`. T7b ``send`` 함수의 입력으로 사용된다.

    Note:
        0바이트 첨부는 Gmail이 거부할 수 있어 ``demo_logger.warning`` 으로 경고하지만
        시연 비차단 정책으로 raise 하지 않는다 (case04 discord 429 패턴 동일).
    """
    sender_addr = sender or os.environ.get("GMAIL_SENDER", "")
    if not sender_addr:
        raise ValueError("sender not provided and GMAIL_SENDER env not set")
    sender_addr = _validate_email_address(sender_addr, label="sender")
    to_field = _validate_to_field(to)

    msg = EmailMessage()
    msg["To"] = to_field
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
        if size == 0:
            from core.common import demo_logger as _dl

            _dl.demo_logger("messaging.email").warning(
                f"attachment {path.name} is 0 bytes — Gmail may reject"
            )
        maintype, subtype = _guess_mime(path)
        msg.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )
    return msg
