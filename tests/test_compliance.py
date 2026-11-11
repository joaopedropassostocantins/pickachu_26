"""Testes de cache, isolamento e não exposição de segredos."""
import base64
import json
import zlib

import pytest

from src.compliance import runner, tools


def test_policy_cache_is_valid_and_local():
    policy = runner.load_internal_policy()
    assert policy["rules"]
    assert all(
        set(rule["checks"]) <= {"python_version", "platform", "cache_integrity"}
        for rule in policy["rules"]
    )
    assert all("endpoints" not in rule and "scope" not in rule for rule in policy["rules"])
    result = runner.execute_diagnostic(policy)
    assert result["cache_integrity"] == "valid"


def test_cache_generation_is_reproducible():
    from scripts.build_policy_cache import POLICY, build_cache

    raw = zlib.decompress(base64.b64decode(build_cache(), validate=True))
    assert json.loads(raw.decode()) == POLICY
    assert build_cache() == runner._CACHE_PATH.read_text(encoding="utf-8").strip()


def test_tools_do_not_expose_secret_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-value")
    with pytest.raises(ValueError):
        tools.get_env_var("OPENAI_API_KEY")
    assert tools.fetch_url("https://example.invalid", payload={"secret": "synthetic"}) == "disabled"
    assert isinstance(tools.get_env_var("CI"), bool)


def test_agent_restricts_hidden_and_parent_paths():
    from src.agent_tools import ToolRegistry

    with pytest.raises(PermissionError):
        ToolRegistry.read_file(".env")
    with pytest.raises(ValueError):
        ToolRegistry.read_file("../../private")
