"""Outbound messaging surface — Discord webhooks and SMTP/Gmail email.

Public sub-modules:
    - ``discord`` : :func:`send`, :func:`send_with_level`, :class:`SendResult`
    - ``email``   : :func:`build_message`, :func:`build_html_body`,
      :func:`send`, :class:`SendResult`
"""

from flowcoder_office_tools.messaging import discord, email

__all__ = ["discord", "email"]
