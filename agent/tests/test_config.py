import os

import pytest

from agent.config import SERVER_REGISTRY


def test_server_registry_contains_all_servers():
    expected = {"DataAnalysisExpert", "MarketResearchExpert", "ReportWritingExpert"}
    assert expected == set(SERVER_REGISTRY.keys())


def test_each_server_uses_streamable_http_transport():
    for name, cfg in SERVER_REGISTRY.items():
        assert "url" in cfg, f"{name}: 'url' 키 없음"
        assert (
            cfg.get("transport") == "streamable_http"
        ), f"{name}: transport는 streamable_http여야 함"


def test_each_server_url_is_non_empty():
    for name, cfg in SERVER_REGISTRY.items():
        assert cfg["url"], f"{name}: URL이 비어 있음"


def test_server_urls_loaded_from_env(monkeypatch):
    monkeypatch.setenv("DATA_ANALYSIS_MCP_URL", "http://10.0.0.1:9000/mcp")
    monkeypatch.setenv("MARKET_RESEARCH_MCP_URL", "http://10.0.0.1:9001/mcp")
    monkeypatch.setenv("REPORT_WRITING_MCP_URL", "http://10.0.0.1:9002/mcp")

    import importlib

    import agent.config as config_module

    importlib.reload(config_module)

    assert (
        config_module.SERVER_REGISTRY["DataAnalysisExpert"]["url"]
        == "http://10.0.0.1:9000/mcp"
    )
    assert (
        config_module.SERVER_REGISTRY["MarketResearchExpert"]["url"]
        == "http://10.0.0.1:9001/mcp"
    )
    assert (
        config_module.SERVER_REGISTRY["ReportWritingExpert"]["url"]
        == "http://10.0.0.1:9002/mcp"
    )
