"""T35 — `flowcoder_office_tools.protocols.serialize_result` sentinel leak coverage.

Covers all secrets_mask patterns + structural cases (R1-L3 dataclass, R1-L4 depth,
R3-M3 output_files paths, bytes/tuple/Decimal preservation).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from flowcoder_office_tools.protocols import ScenarioResult, serialize_result


def _empty_result(case_id: str = "x") -> ScenarioResult:
    return {
        "case_id": case_id,
        "summary_text": "ok",
        "output_files": [],
        "metrics": {},
        "failures": [],
        "extras": {},
    }


# ── Secret pattern coverage (each pattern from secrets_mask.py) ─────────


def test_serialize_masks_discord_webhook() -> None:
    sentinel = "https://discord.com/api/webhooks/123/REAL_TOKEN_PART"
    result = _empty_result("case04")
    result["summary_text"] = f"posted to {sentinel}"
    serialized = serialize_result(result)
    assert "REAL_TOKEN_PART" not in str(serialized)


def test_serialize_masks_openrouter_key() -> None:
    sentinel = "sk-or-v1-FAKE_OPENROUTER_KEY_FOR_TEST"
    result = _empty_result("case09")
    result["summary_text"] = f"key={sentinel}"
    serialized = serialize_result(result)
    assert "FAKE_OPENROUTER_KEY_FOR_TEST" not in str(serialized)


def test_serialize_masks_anthropic_key() -> None:
    sentinel = "sk-ant-api03-FAKE_ANTHROPIC_KEY_FOR_TEST"
    result = _empty_result()
    result["summary_text"] = f"using {sentinel}"
    serialized = serialize_result(result)
    assert "FAKE_ANTHROPIC_KEY_FOR_TEST" not in str(serialized)


def test_serialize_masks_openai_key() -> None:
    sentinel = "sk-proj-FAKE_OPENAI_KEY_FOR_TEST_12345"
    result = _empty_result()
    result["metrics"] = {"key": sentinel}
    serialized = serialize_result(result)
    assert "FAKE_OPENAI_KEY_FOR_TEST_12345" not in str(serialized)


def test_serialize_masks_github_pat() -> None:
    sentinel = "ghp_FAKE_GITHUB_PAT_FOR_TEST_1234567890"
    result = _empty_result()
    result["summary_text"] = f"token: {sentinel}"
    serialized = serialize_result(result)
    assert "FAKE_GITHUB_PAT_FOR_TEST_1234567890" not in str(serialized)


def test_serialize_masks_slack_token() -> None:
    sentinel = "xoxb-FAKE-SLACK-TOKEN-FOR-TEST"
    result = _empty_result()
    result["extras"] = {"slack": sentinel}
    serialized = serialize_result(result)
    assert "FAKE-SLACK-TOKEN-FOR-TEST" not in str(serialized)


def test_serialize_masks_aws_access_key() -> None:
    sentinel = "AKIAIOSFODNN7EXAMPLE"
    result = _empty_result()
    result["summary_text"] = f"aws={sentinel}"
    serialized = serialize_result(result)
    assert sentinel not in str(serialized)


def test_serialize_masks_jwt() -> None:
    sentinel = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.FAKE_JWT_SIG_HERE"
    result = _empty_result()
    result["summary_text"] = f"jwt={sentinel}"
    serialized = serialize_result(result)
    assert "FAKE_JWT_SIG_HERE" not in str(serialized)


def test_serialize_masks_generic_bearer() -> None:
    sentinel = "FAKE_BEARER_TOKEN_VALUE"
    result = _empty_result()
    result["summary_text"] = f"Bearer {sentinel}"
    serialized = serialize_result(result)
    assert sentinel not in str(serialized)


def test_serialize_masks_gmail_access_token() -> None:
    sentinel = "ya29.A0ARrdaM_FAKE_GMAIL_ACCESS_TOKEN"
    result = _empty_result("case03")
    result["summary_text"] = f"oauth={sentinel}"
    serialized = serialize_result(result)
    assert "FAKE_GMAIL_ACCESS_TOKEN" not in str(serialized)


def test_serialize_masks_gmail_refresh_token_in_json() -> None:
    sentinel = "1//FAKE_GMAIL_REFRESH_TOKEN_VALUE"
    result = _empty_result("case03")
    result["extras"] = {"token_json": f'{{"refresh_token": "{sentinel}"}}'}
    serialized = serialize_result(result)
    assert "FAKE_GMAIL_REFRESH_TOKEN_VALUE" not in str(serialized)


def test_serialize_masks_gmail_client_secret_in_json() -> None:
    sentinel = "GOCSPX-FAKE_CLIENT_SECRET"
    result = _empty_result("case03")
    result["extras"] = {"client": f'{{"client_secret": "{sentinel}"}}'}
    serialized = serialize_result(result)
    assert "FAKE_CLIENT_SECRET" not in str(serialized)


def test_serialize_masks_smtp_pass() -> None:
    sentinel = "FAKE_SMTP_PASSWORD_VALUE"
    result = _empty_result("case03")
    result["summary_text"] = f"env: SMTP_PASS={sentinel}"
    serialized = serialize_result(result)
    assert sentinel not in str(serialized)


# ── Structural placement coverage ──────────────────────────────────────


def test_serialize_masks_in_summary_text() -> None:
    sentinel = "sk-or-v1-IN_SUMMARY"
    result = _empty_result()
    result["summary_text"] = f"failure: {sentinel}"
    serialized = serialize_result(result)
    assert "IN_SUMMARY" not in str(serialized)


def test_serialize_masks_in_failures_list() -> None:
    sentinel = "ya29.IN_FAILURES_LIST"
    result = _empty_result("case03")
    result["failures"] = [{"vendor": "v1", "error": f"401 token={sentinel}"}]
    serialized = serialize_result(result)
    assert "IN_FAILURES_LIST" not in str(serialized)


def test_serialize_masks_in_metrics_nested_dict() -> None:
    sentinel = "sk-ant-IN_NESTED_METRIC"
    result = _empty_result()
    result["metrics"] = {"backend": {"config": {"key": sentinel}}}
    serialized = serialize_result(result)
    assert "IN_NESTED_METRIC" not in str(serialized)


def test_serialize_masks_in_extras_list_of_dicts() -> None:
    sentinel = "ghp_IN_LIST_OF_DICTS_1234567890ABCD"
    result = _empty_result()
    result["extras"] = {"history": [{"event": f"push token={sentinel}"}]}
    serialized = serialize_result(result)
    assert "IN_LIST_OF_DICTS" not in str(serialized)


def test_serialize_masks_output_files_path(tmp_path: Path) -> None:
    """R3-M3: output_files도 mask 적용."""
    sentinel = "sk-or-v1-FAKE_KEY_IN_FILENAME"
    sus_path = tmp_path / f"report-{sentinel}.xlsx"
    sus_path.write_bytes(b"")
    result = _empty_result("case01")
    result["output_files"] = [sus_path]
    serialized = serialize_result(result)
    assert "FAKE_KEY_IN_FILENAME" not in str(serialized)


def test_serialize_handles_dataclass_in_extras() -> None:
    """R1-L3: dataclass도 sanitize 거침."""

    @dataclass
    class MeetingSummary:
        title: str
        notes: str

    sentinel = "ya29.LEAK_VIA_DATACLASS"
    result = _empty_result("case10")
    result["extras"] = {"summaries": [MeetingSummary(title="회의", notes=f"action: {sentinel}")]}
    serialized = serialize_result(result)
    assert "LEAK_VIA_DATACLASS" not in str(serialized)


def test_serialize_handles_bytes_in_extras() -> None:
    """R1-L3: bytes는 길이만 노출, 내용 유출 없음."""
    payload = b"BINARY_SECRET_PAYLOAD_FAKE"
    result = _empty_result()
    result["extras"] = {"raw": payload}
    serialized = serialize_result(result)
    assert b"BINARY_SECRET_PAYLOAD_FAKE" not in str(serialized).encode()
    assert "BINARY_SECRET_PAYLOAD_FAKE" not in str(serialized)
    assert "<bytes:" in str(serialized)


def test_serialize_recursion_depth_safe() -> None:
    """R1-L4: 재귀 깊이 보호."""
    deep: dict[str, Any] = {}
    current = deep
    for _ in range(200):
        current["nested"] = {}
        current = current["nested"]
    current["leaf"] = "ok"
    result = _empty_result("x")
    result["metrics"] = deep
    serialized = serialize_result(result)
    assert serialized["case_id"] == "x"
    assert "<TRUNCATED:depth>" in str(serialized)


def test_serialize_preserves_int_float_bool_none() -> None:
    """비-string scalar는 변환 없이 유지."""
    result = _empty_result()
    result["metrics"] = {
        "count": 42,
        "ratio": 3.14,
        "ok": True,
        "missing": None,
    }
    serialized = serialize_result(result)
    assert serialized["metrics"]["count"] == 42
    assert serialized["metrics"]["ratio"] == 3.14
    assert serialized["metrics"]["ok"] is True
    assert serialized["metrics"]["missing"] is None


def test_serialize_handles_tuple() -> None:
    """tuple → list로 정규화."""
    sentinel = "sk-or-v1-IN_TUPLE_FAKE_KEY"
    result = _empty_result()
    result["extras"] = {"pair": (f"k={sentinel}", "value")}
    serialized = serialize_result(result)
    assert "IN_TUPLE_FAKE_KEY" not in str(serialized)
    assert isinstance(serialized["extras"]["pair"], list)


def test_serialize_handles_decimal() -> None:
    """Decimal은 변환 없이 통과."""
    result = _empty_result()
    result["metrics"] = {"amount": Decimal("123.45")}
    serialized = serialize_result(result)
    assert serialized["metrics"]["amount"] == Decimal("123.45")


def test_serialize_empty_strings_safe() -> None:
    """빈 문자열은 그대로 (마스킹 패턴 없음)."""
    result = _empty_result()
    result["summary_text"] = ""
    serialized = serialize_result(result)
    assert serialized["summary_text"] == ""


def test_serialize_handles_empty_dict() -> None:
    result = _empty_result()
    serialized = serialize_result(result)
    assert serialized["metrics"] == {}
    assert serialized["extras"] == {}


def test_serialize_handles_empty_list() -> None:
    result = _empty_result()
    serialized = serialize_result(result)
    assert serialized["output_files"] == []
    assert serialized["failures"] == []


def test_serialize_handles_mixed_types() -> None:
    """str + int + None + nested dict 혼합도 leak 없음."""
    sentinel = "sk-ant-MIXED_TYPES_LEAK"
    result = _empty_result()
    result["extras"] = {
        "string_key": f"val={sentinel}",
        "count": 7,
        "missing": None,
        "nested": {"inner_key": sentinel},
        "list": [sentinel, 42, None],
    }
    serialized = serialize_result(result)
    assert "MIXED_TYPES_LEAK" not in str(serialized)


def test_serialize_pathlib_path_in_output_files_returns_str() -> None:
    """output_files의 Path는 str로 직렬화."""
    p = Path("/tmp/no-secret-here.xlsx")
    result = _empty_result()
    result["output_files"] = [p]
    serialized = serialize_result(result)
    assert serialized["output_files"] == ["/tmp/no-secret-here.xlsx"]


def test_serialize_returns_dict_type() -> None:
    """반환 타입은 dict[str, Any]."""
    result = _empty_result()
    serialized = serialize_result(result)
    assert isinstance(serialized, dict)
    assert set(serialized.keys()) == {
        "case_id",
        "summary_text",
        "output_files",
        "metrics",
        "failures",
        "extras",
    }


def test_serialize_round_trip_no_secret_left() -> None:
    """모든 필드에 secret 심어도 leak 0건."""
    sentinel = "sk-or-v1-FULL_ROUND_TRIP_LEAK"
    result: ScenarioResult = {
        "case_id": "x",
        "summary_text": f"summary {sentinel}",
        "output_files": [Path(f"/tmp/{sentinel}.txt")],
        "metrics": {"key": sentinel, "nested": {"deeper": sentinel}},
        "failures": [{"err": sentinel}],
        "extras": {"raw": sentinel, "list": [sentinel]},
    }
    serialized = serialize_result(result)
    assert "FULL_ROUND_TRIP_LEAK" not in str(serialized)
