from __future__ import annotations

from demo_interactive import explain, prompt, section, show, wait
from repo_paths import REPO_ROOT

from app.agent.context import BomAgentContext
from app.agent.runner import BomAutonomousAgent, ToolCall
from pipeline.demo.seed import seed_complex_bom


def seed(duckdb: str) -> BomAgentContext:
    ctx = BomAgentContext.create(repo_root=REPO_ROOT, duckdb_path=duckdb)
    seed_complex_bom(ctx.graph, ctx.component_master)
    return ctx


def main() -> None:
    section(
        "Autonomous BOM agent demo",
        intro=(
            "Loads skills/bom-ontology and bom-graph-explorer on a 12-component BOM,\n"
            "then runs BomAutonomousAgent to pick and execute tools (works without an LLM)."
        ),
    )
    wait()

    ctx = seed("data/bom.duckdb")
    agent = BomAutonomousAgent(ctx)

    try:
        prompt_preview = ctx.system_prompt()[:500] + "\n..."
        show(
            "System prompt (from Agent Skills, truncated)",
            prompt_preview,
            commentary=(
                "SKILL.md bodies become behavioral instructions for the agent.\n"
                "bom-ontology holds schema constraints; "
                "bom-graph-explorer holds exploration workflows."
            ),
        )
        wait()

        goal = prompt(
            "Agent goal (e.g. Analyze supplier impact for SUP-002)",
            "Analyze supplier impact for SUP-002",
        )
        result = agent.run(goal, mode="tools")
        show("Autonomous run result", result, commentary=_explain_agent_run(result))
        wait()

        run_path = prompt("Run supply_path demo? (y/n)", "y").lower()
        if run_path in ("y", "yes", ""):
            from_id = prompt("from_component_id", "COMP-103")
            to_id = prompt("to_product_id", "PROD-901")
            explain("Next: explicit tool_calls bypass the planner.")
            wait()
            path_result = agent.run(
                "shortest path",
                mode="tools",
                tool_calls=[
                    ToolCall(
                        "bom_supply_path",
                        {"from_component_id": from_id, "to_product_id": to_id},
                    )
                ],
            )
            show(
                "Explicit tool call result", path_result, commentary=_explain_agent_run(path_result)
            )

        section(
            "Demo complete",
            intro="Reseed: uv run python scripts/seed_complex_bom.py --reset",
        )
    finally:
        ctx.close()


def _explain_agent_run(result: object) -> str:
    goal = getattr(result, "goal", "")
    mode = getattr(result, "mode", "")
    tool_calls = getattr(result, "tool_calls", []) or []
    run_results = getattr(result, "results", []) or []
    notes = getattr(result, "llm_notes", None)

    lines = [
        f"Goal: {goal}",
        f"Mode: {mode} (tools = heuristic planner, no API key required)",
    ]
    if tool_calls:
        lines.append("Selected tools:")
        for tc in tool_calls:
            lines.append(f"  - {tc.name}({tc.arguments})")
    if run_results:
        op = (run_results[0] or {}).get("operation", "")
        summary = (run_results[0] or {}).get("summary", "")
        data = (run_results[0] or {}).get("data") or []
        lines.append(f"Tool result operation={op}: {summary}")
        if op == "supplier_impact":
            lines.append(f"  Impact rows: {len(data)}")
        elif op == "supply_path" and data:
            nodes = (data[0] or {}).get("nodes") or []
            lines.append(f"  Path nodes: {len(nodes)}")
    if notes:
        lines.append(f"Planner note: {notes}")
    lines.append(
        "Agent Skills under skills/ are injected into the system prompt;\n"
        "  the same tool names run deterministic graph exploration."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
