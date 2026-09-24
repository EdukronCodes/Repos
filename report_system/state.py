from __future__ import annotations

from typing import Any, TypedDict


class ReportState(TypedDict, total=False):
    user_goal: str
    input_path: str
    output_path: str
    output_format: str
    title: str
    plan: dict[str, Any]
    shared_memory: dict[str, Any]
    documents: list[dict[str, Any]]
    tables: dict[str, list[dict[str, Any]]]
    understanding: dict[str, Any]
    analysis: dict[str, Any]
    report: dict[str, Any]
    quality_review: dict[str, Any]
    published_paths: list[str]
