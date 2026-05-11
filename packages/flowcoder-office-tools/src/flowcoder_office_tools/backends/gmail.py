"""Gmail backend (delegates to `core.messaging.email`).

token init 인자는 cache_identity fingerprint + audit log contract 검증에 사용된다.
실제 OAuth credentials는 `core.messaging.email`이 환경변수/token 파일로 관리한다.
"""

from __future__ import annotations

import hashlib
from email.message import EmailMessage
from typing import Any, cast

from flowcoder_office_tools.common.demo_logger import demo_logger
from flowcoder_office_tools.messaging import email


class GmailBackend:
    def __init__(self, token: str) -> None:
        self._token = token

    def cache_identity(self) -> str:
        """R1-H5: token sha256 후 16자만 노출."""
        return hashlib.sha256(f"gmail|{self._token}".encode()).hexdigest()[:16]

    def send_email(self, message: Any) -> None:
        demo_logger("backends.gmail").info("Gmail send: dispatching")
        email.send(cast(EmailMessage, message))
