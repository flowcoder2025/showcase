"""이메일 메시지 빌드 + 발송 (Gmail API primary + SMTP 폴백).

T7a: build_message — EmailMessage 객체 생성 (multipart + HTML + 첨부)
T7a.5: build_html_body 헬퍼 (XSS 방어), sender/to 형식 검증, 0바이트 첨부 warning
T7b: send — 실제 발송 + safe_mode short-circuit + Gmail API/SMTP 폴백

NOTE: 외부 호출은 모듈 참조로 호출 (safe_mode patch 격리)::

    from flowcoder_office_tools.messaging import email
    email.send(...)

INTERCEPT_TARGETS["gmail"] = (flowcoder_office_tools.messaging.email, send) — 단일 patch point.
``_send_gmail_api`` / ``_send_smtp`` 는 internal helper로, ``send`` 만 patch
되어도 모든 외부 호출이 격리된다.
"""

from __future__ import annotations

import base64
import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, parseaddr
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from flowcoder_office_tools.common import safe_mode

GMAIL_ATTACHMENT_LIMIT = 100 * 1024 * 1024  # 100MB
GMAIL_SCOPES: list[str] = ["https://www.googleapis.com/auth/gmail.send"]

TransportLiteral = Literal["auto", "gmail_api", "smtp", "safe-fallback"]


class SendResult(TypedDict):
    """Result of :func:`send`.

    - transport: 실제 사용된 transport (auto는 결과에서 절대 등장하지 않음 —
      auto는 입력 옵션일 뿐 resolution 후 실제 값으로 대체된다)
    - sent: 메시지가 외부로 실제 송신됐는지 (safe-fallback이면 항상 False)
    - to: msg["To"] 그대로 propagate
    - message_id: Gmail API 응답의 id (SMTP는 mail server가 생성하므로 None)
    - note: safe / fallback 사유 등 부가 설명
    """

    transport: TransportLiteral
    sent: bool
    to: str
    message_id: str | None
    note: str | None


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
    from flowcoder_office_tools.docgen import template

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
            from flowcoder_office_tools.common import demo_logger as _dl

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


# --- send (T7b) ------------------------------------------------------------


def _gmail_oauth_available() -> bool:
    """``GMAIL_OAUTH_CREDENTIALS`` 환경변수가 가리키는 파일이 존재하는지."""
    creds_path = os.environ.get("GMAIL_OAUTH_CREDENTIALS", "")
    return bool(creds_path) and Path(creds_path).exists()


def _smtp_configured() -> bool:
    """``SMTP_HOST`` + ``SMTP_USER`` + ``SMTP_PASS`` 모두 설정됐는지."""
    return all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))


def send(msg: EmailMessage, *, transport: TransportLiteral = "auto") -> SendResult:
    """이메일 발송. Gmail API 우선, SMTP 폴백, 둘 다 없으면 force_safe + dummy.

    Safe-mode short-circuit: ``DEMO_SAFE=1`` 이면 외부 호출 없이 즉시 dummy
    반환 (``core.ai.client.chat`` 패턴 동일).

    Args:
        msg: :func:`build_message` 로 빌드된 :class:`EmailMessage`.
        transport: ``"auto"`` (자동 선택), ``"gmail_api"``, ``"smtp"``,
            ``"safe-fallback"`` (강제 더미).

    Returns:
        :class:`SendResult` — transport / sent / to / message_id / note.

    Raises:
        ValueError: ``transport`` 가 알 수 없는 값일 때.
        RuntimeError: ``transport`` 명시했는데 그 transport 환경변수 미설정.
    """
    to_addr = str(msg["To"] or "")

    if safe_mode.is_safe():
        return SendResult(
            transport="safe-fallback",
            sent=False,
            to=to_addr,
            message_id=None,
            note="DEMO_SAFE=1 short-circuit",
        )

    chosen: TransportLiteral
    if transport == "auto":
        if _gmail_oauth_available():
            chosen = "gmail_api"
        elif _smtp_configured():
            chosen = "smtp"
        else:
            safe_mode.force_safe("no email transport configured")
            return SendResult(
                transport="safe-fallback",
                sent=False,
                to=to_addr,
                message_id=None,
                note="no Gmail OAuth and no SMTP — auto-safe",
            )
    else:
        chosen = transport

    if chosen == "safe-fallback":
        return SendResult(
            transport="safe-fallback",
            sent=False,
            to=to_addr,
            message_id=None,
            note="explicit safe-fallback",
        )
    if chosen == "gmail_api":
        if not _gmail_oauth_available():
            raise RuntimeError(
                "transport=gmail_api but GMAIL_OAUTH_CREDENTIALS not set or file missing"
            )
        return _send_gmail_api(msg, to_addr)
    if chosen == "smtp":
        if not _smtp_configured():
            raise RuntimeError("transport=smtp but SMTP_HOST/SMTP_USER/SMTP_PASS not all set")
        return _send_smtp(msg, to_addr)

    raise ValueError(f"unknown transport: {chosen!r}")


def _send_gmail_api(msg: EmailMessage, to_addr: str) -> SendResult:
    """Gmail API 발송 — token cache → refresh → 신규 OAuth flow.

    Internal helper. 외부에서 직접 호출하지 말 것 — :func:`send` 가 단일 patch
    point이므로 이 helper는 safe_mode.intercept 로 patch 되지 않는다.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds_path = os.environ["GMAIL_OAUTH_CREDENTIALS"]
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "./secrets/gmail_token.json")
    token_path_obj = Path(token_path)

    creds: Any = None
    if token_path_obj.exists():
        # from_authorized_user_file is not annotated upstream — cast keeps mypy --strict happy.
        creds = cast(Any, Credentials.from_authorized_user_file)(str(token_path_obj), GMAIL_SCOPES)
    if not creds or not getattr(creds, "valid", False):
        if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path_obj.parent.mkdir(parents=True, exist_ok=True)
        token_path_obj.write_text(creds.to_json(), encoding="utf-8")

    service = build("gmail", "v1", credentials=creds)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    response = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    message_id_raw = response.get("id") if isinstance(response, dict) else None
    message_id: str | None = str(message_id_raw) if message_id_raw is not None else None
    return SendResult(
        transport="gmail_api",
        sent=True,
        to=to_addr,
        message_id=message_id,
        note=None,
    )


def _send_smtp(msg: EmailMessage, to_addr: str) -> SendResult:
    """SMTP TLS 발송 — STARTTLS + login + send_message.

    Internal helper. 외부에서 직접 호출하지 말 것 — :func:`send` 가 단일 patch
    point이므로 이 helper는 safe_mode.intercept 로 patch 되지 않는다.
    """
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return SendResult(
        transport="smtp",
        sent=True,
        to=to_addr,
        message_id=None,  # SMTP는 mail server가 message-id를 생성
        note=None,
    )
