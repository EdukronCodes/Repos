"""Command-line compatibility entry point for the report system."""

from __future__ import annotations

import argparse
from pathlib import Path

from report_system.graph import build_graph

__all__ = ["build_graph"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a report from an Excel workbook with LangGraph agents.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("report.json"))
    parser.add_argument("--format", choices=["xlsx", "csv", "html", "md", "json"], default="json")
    parser.add_argument("--title", default="")
    parser.add_argument("--goal", default="")
    args = parser.parse_args()
    result = build_graph().invoke({"input_path": str(args.input), "output_path": str(args.output), "output_format": args.format, "title": args.title, "user_goal": args.goal})
    print(f"Created: {', '.join(result['published_paths'])}")


if __name__ == "__main__":
    main()
