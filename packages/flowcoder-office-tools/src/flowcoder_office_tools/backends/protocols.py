"""Re-export Protocol surface from ``flowcoder_office_tools.protocols``.

T43 이주 완료 — protocols 모듈은 패키지 최상위에 있고, 이 모듈은 backends
서브패키지에서 동일 surface 를 재노출 하는 shim 이다. consumer 는
``from flowcoder_office_tools.backends.protocols import OCRBackend`` 또는
``from flowcoder_office_tools.protocols import OCRBackend`` 어느 쪽이든 사용 가능.
"""

from flowcoder_office_tools.protocols import AIBackend, Backends, MessagingBackend, OCRBackend

__all__ = ["AIBackend", "Backends", "MessagingBackend", "OCRBackend"]
