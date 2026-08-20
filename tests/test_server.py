"""Exercise the MCP server through its tool-call layer (in-process)."""

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from soif_mcp.server import mcp


async def _call(tool: str, args: dict):
    result = await mcp.call_tool(tool, args)
    assert not result.is_error, result.content
    sc = result.structured_content
    # list-returning tools are wrapped as {"result": [...]}
    if isinstance(sc, dict) and set(sc) == {"result"}:
        return sc["result"]
    return sc


async def test_lists_all_tools():
    tools = {t.name for t in await mcp.list_tools()}
    assert tools == {
        "estimate_water",
        "estimate_from_usage",
        "compare_models",
        "pick_low_water_model",
        "list_known_models",
    }


async def test_estimate_water():
    out = await _call(
        "estimate_water",
        {"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 500},
    )
    assert out["tier"] == "large"
    assert out["water_ml"]["total"]["low"] < out["water_ml"]["total"]["mid"]
    assert "water" in out["summary"]


async def test_estimate_water_prompt_only_records_assumptions():
    out = await _call("estimate_water", {"model": "claude-haiku-4-5", "prompt": "hi " * 50})
    assert out["assumptions"]


async def test_estimate_from_usage_anthropic_shape():
    out = await _call(
        "estimate_from_usage",
        {
            "usage": {
                "input_tokens": 800,
                "output_tokens": 400,
                "cache_read_input_tokens": 5000,
            },
            "model": "claude-sonnet-4-5",
        },
    )
    assert out["tokens"]["cached"] == 5000
    assert out["water_ml"]["total"]["mid"] > 0


async def test_compare_and_pick():
    ranked = await _call(
        "compare_models",
        {"models": ["gpt-4o", "gpt-4o-mini"], "output_tokens": 500},
    )
    assert [r["model"] for r in ranked] == ["gpt-4o-mini", "gpt-4o"]

    best = await _call(
        "pick_low_water_model",
        {"candidates": ["claude-opus-4", "claude-haiku-4-5"]},
    )
    assert best["model"] == "claude-haiku-4-5"
    assert best["saved_vs_worst_ml"] > 0


async def test_pick_with_impossible_floor_errors():
    with pytest.raises(ToolError, match="min_tier"):
        await mcp.call_tool(
            "pick_low_water_model",
            {"candidates": ["gpt-4o-mini"], "min_tier": "frontier"},
        )


async def test_list_known_models():
    models = await _call("list_known_models", {})
    assert any(m["match"] == "gpt-4o" for m in models)


async def test_methodology_resource():
    contents = await mcp.read_resource("soif://methodology")
    text = next(iter(contents)).content
    assert "arXiv:2304.03271" in text
    assert "tiers" in text.lower()


def test_console_entrypoint_importable():
    from soif_mcp.server import main

    assert callable(main)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
