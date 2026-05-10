"""Re-export Protocol surface from `cases._protocols`.

T43 이주 시 protocols.py가 packages/.../protocols.py가 되고, 이 re-export는
shim으로 보존된다. consumer는 `from core.backends.protocols import OCRBackend`
또는 `from cases._protocols import OCRBackend` 어느 쪽이든 사용 가능.
"""

from cases._protocols import AIBackend, Backends, MessagingBackend, OCRBackend

__all__ = ["AIBackend", "Backends", "MessagingBackend", "OCRBackend"]
