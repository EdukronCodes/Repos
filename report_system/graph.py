from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .agents import analyze_content, generate_report, ingest_files, quality_review, supervisor, understand_content
from .publishing import publish_report
from .state import ReportState


def deliver_report(state: ReportState) -> dict[str, Any]:
    path = publish_report(state["report"], __import__("pathlib").Path(state["output_path"]), state.get("output_format", "json"))
    memory = dict(state.get("shared_memory", {}))
    memory["events"] = memory.get("events", []) + [f"delivery: published {path.suffix.lstrip('.')}"]
    return {"published_paths": [str(path)], "shared_memory": memory}


def build_graph() -> Any:
    graph = StateGraph(ReportState)
    nodes = [("supervisor", supervisor), ("file_ingestion", ingest_files), ("content_understanding", understand_content), ("analysis", analyze_content), ("report_generation", generate_report), ("quality_review", quality_review), ("delivery", deliver_report)]
    for name, node in nodes:
        graph.add_node(name, node)
    names = [name for name, _ in nodes]
    for before, after in zip([START, *names], [*names, END]):
        graph.add_edge(before, after)
    return graph.compile()
