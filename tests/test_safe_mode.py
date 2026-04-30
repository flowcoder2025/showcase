import json
import os

from core.common import safe_mode


def test_is_safe_reads_env(monkeypatch):
    monkeypatch.setenv("DEMO_SAFE", "1")
    assert safe_mode.is_safe() is True
    monkeypatch.setenv("DEMO_SAFE", "0")
    assert safe_mode.is_safe() is False


def test_force_safe_sets_env_and_logs(monkeypatch, capsys):
    monkeypatch.setenv("DEMO_SAFE", "0")
    safe_mode.force_safe("test reason")
    assert os.getenv("DEMO_SAFE") == "1"
    assert "test reason" in capsys.readouterr().out


def test_cache_path_uses_sha1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = safe_mode.cache_path("case_x", "input_key")
    assert "case_x" in str(p)
    assert p.suffix == ".json"


def test_intercept_patches_only_listed_apis(tmp_path, monkeypatch):
    """unittest.mock.patch 기반 격리. 컨텍스트 종료 시 복원."""
    monkeypatch.setenv("DEMO_SAFE", "1")

    # 가짜 모듈 등록
    import sys
    import types
    fake = types.ModuleType("core.fake_api")
    def real_call(x): return f"REAL:{x}"
    fake.call = real_call
    sys.modules["core.fake_api"] = fake

    # 인터셉트 대상 추가
    safe_mode.INTERCEPT_TARGETS["fake"] = ("core.fake_api", "call")

    cache_dir = tmp_path / "cases" / "case_x" / "output" / "_cached"
    cache_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    with safe_mode.intercept("case_x", apis=["fake"]):
        from core import fake_api
        assert fake_api.call("hi") != "REAL:hi"  # patched

    # 컨텍스트 종료 후 복원
    from core import fake_api
    assert fake_api.call("hi") == "REAL:hi"
    del safe_mode.INTERCEPT_TARGETS["fake"]


def test_intercept_returns_cached_when_present(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_SAFE", "1")
    monkeypatch.chdir(tmp_path)

    # 가짜 모듈 등록
    import sys
    import types
    fake = types.ModuleType("core.fake_api2")
    fake.call = lambda x: "REAL"
    sys.modules["core.fake_api2"] = fake
    safe_mode.INTERCEPT_TARGETS["fake2"] = ("core.fake_api2", "call")

    # 캐시 파일 미리 작성
    case_id = "case_y"
    key = safe_mode._key("core.fake_api2.call", ("hi",), {})
    cpath = safe_mode.cache_path(case_id, key)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(json.dumps({"result": "CACHED"}))

    with safe_mode.intercept(case_id, apis=["fake2"]):
        from core import fake_api2
        assert fake_api2.call("hi") == "CACHED"

    del safe_mode.INTERCEPT_TARGETS["fake2"]
