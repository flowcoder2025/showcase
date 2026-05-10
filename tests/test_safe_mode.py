import json
import os

import pytest

from core.common import safe_mode


@pytest.fixture
def register_target():
    """Register intercept targets and unregister even if test fails."""
    added: list[str] = []

    def _add(name: str, mod: str, fn: str) -> None:
        safe_mode.INTERCEPT_TARGETS[name] = (mod, fn)
        added.append(name)

    yield _add

    for name in added:
        safe_mode.INTERCEPT_TARGETS.pop(name, None)


def test_is_safe_reads_env(monkeypatch):
    monkeypatch.setenv("DEMO_SAFE", "1")
    assert safe_mode.is_safe() is True
    monkeypatch.setenv("DEMO_SAFE", "0")
    assert safe_mode.is_safe() is False


def test_force_safe_makes_safe_and_logs(monkeypatch, capsys):
    """T37 (R1-H3): force_safe는 더 이상 os.environ을 변경하지 않는다.
    is_safe()는 ContextVar 기반으로 True를 반환, env는 그대로 보존.
    """
    monkeypatch.setenv("DEMO_SAFE", "0")
    safe_mode.force_safe("test reason")
    assert safe_mode.is_safe() is True
    assert os.getenv("DEMO_SAFE") == "0"  # env 보존 (R1-H3)
    assert "test reason" in capsys.readouterr().out


def test_cache_path_uses_sha1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = safe_mode.cache_path("case_x", "input_key")
    assert "case_x" in str(p)
    assert p.suffix == ".json"


def test_intercept_patches_only_listed_apis(tmp_path, monkeypatch, register_target):
    """unittest.mock.patch 기반 격리. 컨텍스트 종료 시 복원."""
    monkeypatch.setenv("DEMO_SAFE", "1")

    # 가짜 모듈 등록
    import sys
    import types

    fake = types.ModuleType("core.fake_api")

    def real_call(x):
        return f"REAL:{x}"

    fake.call = real_call
    sys.modules["core.fake_api"] = fake

    # 인터셉트 대상 추가
    register_target("fake", "core.fake_api", "call")

    cache_dir = tmp_path / "cases" / "case_x" / "output" / "_cached"
    cache_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    with safe_mode.intercept("case_x", apis=["fake"]):
        from core import fake_api

        result = fake_api.call("hi")
        assert isinstance(result, dict)
        assert result.get("_safe") is True
        assert result.get("qualname") == "core.fake_api.call"

    # 컨텍스트 종료 후 복원
    from core import fake_api

    assert fake_api.call("hi") == "REAL:hi"


def test_intercept_returns_cached_when_present(tmp_path, monkeypatch, register_target):
    monkeypatch.setenv("DEMO_SAFE", "1")
    monkeypatch.chdir(tmp_path)

    # 가짜 모듈 등록
    import sys
    import types

    fake = types.ModuleType("core.fake_api2")
    fake.call = lambda x: "REAL"
    sys.modules["core.fake_api2"] = fake
    register_target("fake2", "core.fake_api2", "call")

    # 캐시 파일 미리 작성
    case_id = "case_y"
    key = safe_mode._key("core.fake_api2.call", ("hi",), {})
    cpath = safe_mode.cache_path(case_id, key)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(json.dumps({"result": "CACHED"}))

    with safe_mode.intercept(case_id, apis=["fake2"]):
        from core import fake_api2

        assert fake_api2.call("hi") == "CACHED"
