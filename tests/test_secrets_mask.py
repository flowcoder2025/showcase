from core.common import secrets_mask


def test_masks_discord_webhook_url():
    url = "https://discord.com/api/webhooks/123456/abcdef-token-here"
    assert secrets_mask.mask(url) == "https://discord.com/api/webhooks/***"


def test_masks_openrouter_key():
    assert secrets_mask.mask("sk-or-v1-abc123def456") == "sk-or-***"


def test_masks_anthropic_key():
    assert secrets_mask.mask("sk-ant-api03-xyz789") == "sk-ant-***"


def test_passthrough_for_non_secret_text():
    assert secrets_mask.mask("hello world") == "hello world"


def test_mask_text_replaces_inline_secrets():
    text = "calling https://discord.com/api/webhooks/x/y now"
    out = secrets_mask.mask_text(text)
    assert "y" not in out
    assert "https://discord.com/api/webhooks/***" in out
