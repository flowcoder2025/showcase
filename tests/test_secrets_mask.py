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


# Bearer (gap 3 — was untested)
def test_masks_bearer_token():
    assert secrets_mask.mask("Bearer abcdef12345678") == "Bearer ***"


def test_bearer_does_not_match_short_tokens():
    # {8,} bound — 7 chars must NOT match
    assert (
        secrets_mask.mask("Bearer short12") == "Bearer short12"
        or secrets_mask.mask("Bearer short1") == "Bearer short1"
    )
    # 7-char case (definitely below bound)
    assert secrets_mask.mask("Bearer abc1234") == "Bearer abc1234"


def test_bearer_does_not_eat_trailing_word_after_period():
    # Gap 2 — period must not be in token charset
    out = secrets_mask.mask("Bearer abcdefgh.then more")
    assert "then" in out
    assert "more" in out


def test_bearer_inline_with_trailing_text():
    out = secrets_mask.mask_text("Authorization: Bearer xyz12345abc trailing")
    assert "trailing" in out
    assert "Bearer ***" in out


# OpenAI keys (gap 1)
def test_masks_openai_key_classic():
    assert secrets_mask.mask("sk-abcdef1234567890ABCDEF") == "sk-***"


def test_masks_openai_key_proj():
    assert secrets_mask.mask("sk-proj-abcdef1234567890ABCDEF") == "sk-***"


def test_masks_openai_key_svcacct():
    assert secrets_mask.mask("sk-svcacct-abcdef1234567890ABCD") == "sk-***"


# GitHub tokens (gap 1)
def test_masks_github_pat():
    assert secrets_mask.mask("ghp_abcdef1234567890ABCDEFghij") == "ghp_***"


def test_masks_github_fine_grained_pat():
    assert secrets_mask.mask("github_pat_abcdef1234567890ABCDEFghij") == "github_pat_***"


# Slack (gap 1)
def test_masks_slack_bot_token():
    assert secrets_mask.mask("xoxb-1234567890-abcdef") == "xoxb-***"


def test_masks_slack_user_token():
    assert secrets_mask.mask("xoxp-1234567890-abcdef") == "xoxp-***"


# AWS (gap 1)
def test_masks_aws_access_key():
    assert secrets_mask.mask("AKIAIOSFODNN7EXAMPLE") == "AKIA***"


def test_masks_aws_session_key():
    assert secrets_mask.mask("ASIAIOSFODNN7EXAMPLE") == "ASIA***"


# JWT (gap 1)
def test_masks_jwt():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcXYZ123"
    assert secrets_mask.mask(jwt) == "eyJ***"


# Inline mask_text with multiple secrets
def test_mask_text_handles_multiple_distinct_secrets():
    text = "key=sk-abcdef1234567890ABCDEF token=ghp_abcdef1234567890ABCDEFghij plain"
    out = secrets_mask.mask_text(text)
    assert "sk-***" in out
    assert "ghp_***" in out
    assert "plain" in out


# Gap 1: GitHub regex must mask even with leading word char
def test_github_token_masked_after_underscore():
    out = secrets_mask.mask("foo_ghp_abcdef1234567890ABCDEFghij")
    assert "abcdef" not in out
    assert "ghp_***" in out


def test_github_token_not_masked_when_glued_to_alpha_prefix():
    # Deliberate boundary: a token directly concatenated to alphanumerics
    # without any separator (e.g. `prefixghp_…`) is treated as a variable
    # name lookalike, NOT a leak. This is the conservative trade-off; real
    # log lines always have a separator (=, /, space, comma, etc.).
    text = "prefixghp_abcdef1234567890ABCDEFghij"
    assert secrets_mask.mask(text) == text


def test_github_token_inline_with_equals():
    out = secrets_mask.mask_text("token=foo_ghp_abcdef1234567890ABCDEFghij&next=value")
    assert "abcdef" not in out
    assert "next=value" in out


# Gap 2: JWT must NOT match short dotted base64-like strings
def test_jwt_does_not_match_short_dotted_string():
    # Each segment under 10 chars — should NOT mask
    text = "eyJabc.def123.xyz789"
    assert secrets_mask.mask(text) == text


def test_jwt_matches_realistic_jwt():
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    assert secrets_mask.mask(jwt) == "eyJ***"


# Gap 3: AWS key followed by alphanumeric must still mask
def test_aws_key_with_trailing_alpha():
    out = secrets_mask.mask("AKIAIOSFODNN7EXAMPLEx more text")
    # Key body must be masked
    assert "IOSFODNN7EXAMPLE" not in out
    assert "AKIA***" in out


def test_aws_key_with_trailing_digit_not_masked():
    # AWS access keys are exactly 20 chars (AKIA + 16). A trailing digit
    # makes the surrounding string NOT a valid AWS key, so the conservative
    # lookahead (?![A-Z0-9]) correctly refuses to match. This avoids
    # masking unrelated 17+ char [A-Z0-9] tokens that happen to start with AKIA.
    text = "AKIAIOSFODNN7EXAMPLE1 more"
    assert secrets_mask.mask(text) == text


def test_aws_negative_below_charset():
    # AKIA followed by lowercase or fewer than 16 [A-Z0-9] must NOT match
    text = "AKIAioshortmix"
    assert secrets_mask.mask(text) == text


# Negative regression: original behavior preserved
def test_aws_key_with_period_separator():
    # Period is non-AWS-charset, so lookahead allows masking
    out = secrets_mask.mask("AKIAIOSFODNN7EXAMPLE.suffix")
    assert "AKIA***" in out
    assert "suffix" in out
