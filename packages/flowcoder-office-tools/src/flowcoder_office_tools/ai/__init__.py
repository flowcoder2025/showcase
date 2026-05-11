"""AI/LLM surface — OpenRouter chat plus prompt and task helpers.

Public sub-modules:
    - ``client``  : :func:`chat`, ``MODEL_PRIORITY``,
      :class:`RateLimitError`, :class:`ServerError`
    - ``prompts`` : :func:`email_draft_user`, :func:`meeting_summary`
    - ``tasks``   : :func:`draft_email`, :func:`summarize_meeting`,
      :class:`ActionItem`, :class:`MeetingSummary`
"""

from flowcoder_office_tools.ai import client, prompts, tasks

__all__ = ["client", "prompts", "tasks"]
