"""Protocol implementation surface — concrete OCR/AI/Messaging backends + DI.

Public sub-modules:
    - ``cached``     : :class:`CachedOCRBackend`, :class:`CachedAIBackend`,
      :class:`CachedMessagingBackend`
    - ``discord``    : :class:`DiscordWebhookBackend`
    - ``factory``    : :func:`default_backends`, :func:`safe_backends`
    - ``gmail``      : :class:`GmailBackend`
    - ``mlx``        : :class:`MLXOCRBackend`
    - ``openrouter`` : :class:`OpenRouterAIBackend`
    - ``protocols``  : re-export of top-level :class:`OCRBackend`,
      :class:`AIBackend`, :class:`MessagingBackend`, :class:`Backends`
    - ``safe``       : :class:`SafeOCRBackend`, :class:`SafeAIBackend`,
      :class:`SafeMessagingBackend`
"""

from flowcoder_office_tools.backends import (
    cached,
    discord,
    factory,
    gmail,
    mlx,
    openrouter,
    protocols,
    safe,
)

__all__ = [
    "cached",
    "discord",
    "factory",
    "gmail",
    "mlx",
    "openrouter",
    "protocols",
    "safe",
]
