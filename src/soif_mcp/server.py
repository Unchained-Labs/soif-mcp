"""MCP server for soif — water-footprint estimation for LLM prompts.

Exposes soif (https://github.com/Unchained-Labs/soif) over the Model
Context Protocol so any MCP client (Claude Code, Claude Desktop, Cursor,
agent frameworks) can ask "how much water did/would this call use?" and
route models by water cost.

Run with stdio transport (the default for local clients):

    soif-mcp
"""

from __future__ import annotations

from typing import Any

import soif
from mcp.server import MCPServer
from soif import factors, optimize, registry

mcp = MCPServer(
    "soif",
    instructions=(
        "Water-footprint estimation for LLM usage. All water figures are in "
        "millilitres as {low, mid, high} scenario ranges — quote the mid value "
        "with its range, never the mid alone as a precise fact. Prefer "
        "estimate_from_usage with real token usage when a response is at hand; "
        "use estimate_water for what-if questions; use compare_models / "
        "pick_low_water_model to choose a model by water cost."
    ),
)


@mcp.tool()
def estimate_water(
    model: str,
    input_tokens: int = 0,
    output_tokens: int | None = None,
    reasoning_tokens: int = 0,
    cached_tokens: int = 0,
    prompt: str | None = None,
    reasoning_effort: str | None = None,
    provider: str | None = None,
    region: str | None = None,
    include_embodied: bool = True,
) -> dict[str, Any]:
    """Estimate the freshwater consumed (mL) by one LLM call.

    Provide real token counts when known; otherwise pass `prompt` text
    (tokens are approximated and output defaults to a typical 500 tokens).
    `reasoning_effort` ("none"|"low"|"medium"|"high") models thinking tokens
    when actual usage is unknown. `provider` ("aws"|"azure"|"gcp"|"average")
    and `region` ("world"|"us"|"eu"|"france"|"nordics"|"asia"|"renewable")
    override the hosting profile. Set include_embodied=false for
    operational water only. Returns water/energy breakdowns as
    {low, mid, high} ranges plus a human summary and the assumptions made.
    """
    est = soif.estimate(
        model,
        prompt=prompt,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        cached_tokens=cached_tokens,
        reasoning_effort=reasoning_effort,
        provider=provider,
        region=region,
        include_embodied=include_embodied,
    )
    return {"summary": est.humanize(), **est.to_dict()}


@mcp.tool()
def estimate_from_usage(
    usage: dict[str, Any],
    model: str,
    region: str | None = None,
    include_embodied: bool = True,
) -> dict[str, Any]:
    """Estimate water (mL) from a real API usage object — the accurate path.

    `usage` accepts OpenAI Chat Completions shape (prompt_tokens /
    completion_tokens, with completion_tokens_details.reasoning_tokens and
    prompt_tokens_details.cached_tokens), OpenAI Responses shape, or
    Anthropic Messages shape (input_tokens / output_tokens,
    cache_read_input_tokens, cache_creation_input_tokens). Reasoning and
    cached tokens are handled without double counting.
    """
    est = soif.from_usage(
        usage, model=model, region=region, include_embodied=include_embodied
    )
    return {"summary": est.humanize(), **est.to_dict()}


@mcp.tool()
def compare_models(
    models: list[str],
    input_tokens: int = 1000,
    output_tokens: int = 500,
    min_tier: str | None = None,
) -> list[dict[str, Any]]:
    """Rank candidate models by mid-scenario water use for a workload.

    Returns models sorted least- to most-thirsty, each with its tier and
    water range in mL. `min_tier` ("nano"|"small"|"medium"|"large"|
    "frontier") filters out models below a capability floor.
    """
    ranked = optimize.rank(
        models, input_tokens=input_tokens, output_tokens=output_tokens, min_tier=min_tier
    )
    return [
        {
            "model": r.model,
            "tier": r.tier,
            "water_ml": r.estimate.total_ml.to_dict(),
            "summary": r.estimate.humanize(),
        }
        for r in ranked
    ]


@mcp.tool()
def pick_low_water_model(
    candidates: list[str],
    min_tier: str | None = None,
    input_tokens: int = 1000,
    output_tokens: int = 500,
) -> dict[str, Any]:
    """Pick the least-thirsty candidate model that meets a capability floor.

    Use in agent graphs to route each step: set `min_tier` to the minimum
    capability the step needs, and the tool returns the lowest-water model
    among the candidates plus what it saves vs. the thirstiest candidate.
    """
    ranked = optimize.rank(
        candidates, input_tokens=input_tokens, output_tokens=output_tokens, min_tier=min_tier
    )
    if not ranked:
        raise ValueError(
            f"no candidate meets min_tier={min_tier!r}; candidates were {candidates}"
        )
    best, worst = ranked[0], ranked[-1]
    return {
        "model": best.model,
        "tier": best.tier,
        "water_ml": best.estimate.total_ml.to_dict(),
        "saved_vs_worst_ml": max(0.0, worst.ml - best.ml),
        "summary": best.estimate.humanize(),
    }


@mcp.tool()
def list_known_models() -> list[dict[str, str]]:
    """List models soif recognises, with their size tier and default hosting.

    Unknown models still work everywhere (they fall back to the "large"
    tier with an explicit assumption), but known models get calibrated
    tier/provider/region defaults.
    """
    return [
        {"match": s.match, "tier": s.tier, "provider": s.provider, "region": s.region}
        for s in registry.known_models()
    ]


@mcp.resource("soif://methodology")
def methodology() -> str:
    """How soif estimates water, in brief, with factor tables."""
    tiers = "\n".join(
        f"- {name}: {t.low}/{t.mid}/{t.high} Wh per 1k output tokens"
        for name, t in factors.TIER_WH_PER_1K_OUTPUT_TOKENS.items()
    )
    return (
        "soif estimates freshwater CONSUMED per LLM call (Ren et al., "
        "arXiv:2304.03271):\n"
        "  E_it = tokens x Wh-per-token(tier); E_facility = E_it x PUE\n"
        "  W = E_it x WUE (on-site cooling) + E_facility x EWIF (power "
        "generation), optionally x lifecycle (embodied)\n\n"
        f"Model tiers (low/mid/high scenarios):\n{tiers}\n\n"
        "Every factor is a (low, mid, high) scenario triple propagated end "
        "to end; results are estimate ranges, not measurements. Factors "
        f"version: {factors.FACTORS_VERSION}. Full methodology: "
        "https://unchained-labs.github.io/soif/methodology/"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
