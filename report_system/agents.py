from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from .parsing import FileParser
from .state import ReportState


def _event(state: ReportState, message: str) -> dict[str, Any]:
    memory = dict(state.get("shared_memory", {}))
    memory["events"] = memory.get("events", []) + [message]
    return memory


def keyword_summary(text: str) -> list[tuple[str, int]]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
    stop = {"this", "that", "with", "from", "have", "were", "there", "their", "which", "sheet"}
    counts = pd.Series([word for word in words if word not in stop]).value_counts()
    return [(str(word), int(count)) for word, count in counts.head(10).items()]


def summarize_tables(tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    findings = []
    for name, records in tables.items():
        frame = pd.DataFrame(records)
        numeric = []
        for column in frame.select_dtypes(include="number").columns:
            series = frame[column].dropna()
            if not series.empty:
                numeric.append({"column": str(column), "mean": float(series.mean()), "minimum": float(series.min()), "maximum": float(series.max()), "total": float(series.sum())})
        categorical = []
        for column in frame.select_dtypes(exclude="number").columns:
            top = frame[column].dropna().astype(str).value_counts().head(5)
            categorical.append({"column": str(column), "top": [(str(key), int(value)) for key, value in top.items()]})
        findings.append({"name": name, "rows": len(frame), "columns": [str(column) for column in frame.columns], "numeric": numeric, "categorical": categorical, "missing_cells": int(frame.isna().sum().sum()), "duplicate_rows": int(frame.duplicated().sum())})
    return findings


def supervisor(state: ReportState) -> dict[str, Any]:
    path = Path(state["input_path"])
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    goal = state.get("user_goal") or "Understand this workbook and summarize the important findings."
    return {"plan": {"goal": goal, "stages": ["ingest", "understand", "analyze", "generate", "review", "deliver"]}, "shared_memory": {"source": str(path), "events": ["supervisor: plan created"]}}


def ingest_files(state: ReportState) -> dict[str, Any]:
    path = Path(state["input_path"])
    documents, tables = FileParser().parse(path)
    memory = dict(state.get("shared_memory", {}))
    memory["events"] = memory.get("events", []) + [f"ingestion: parsed {path.suffix or 'file'}"]
    return {"documents": documents, "tables": tables, "shared_memory": memory}


def understand_content(state: ReportState) -> dict[str, Any]:
    text = "\n".join(document["text"] for document in state["documents"])
    return {"understanding": {"file_count": len(state["documents"]), "content_chars": len(text), "keywords": keyword_summary(text), "kinds": [document["kind"] for document in state["documents"]]}, "shared_memory": _event(state, "understanding: extracted context and keywords")}


def analyze_content(state: ReportState) -> dict[str, Any]:
    text = "\n".join(document["text"] for document in state["documents"])
    return {"analysis": {"tables": summarize_tables(state.get("tables", {})), "keywords": keyword_summary(text), "text_preview": text[:2000]}, "shared_memory": _event(state, "analysis: calculated findings and metrics")}


def generate_report(state: ReportState) -> dict[str, Any]:
    title = state.get("title") or f"File report: {Path(state['input_path']).stem}"
    tables = state["analysis"]["tables"]
    total_rows = sum(table["rows"] for table in tables)
    return {"report": {"title": title, "goal": state["plan"]["goal"], "overview": [f"{len(state['documents'])} input file(s) processed", f"{total_rows:,} tabular row(s) analyzed", f"{state['understanding']['content_chars']:,} content character(s) indexed"], "understanding": state["understanding"], "analysis": state["analysis"]}, "shared_memory": _event(state, "generation: built structured report")}


def quality_review(state: ReportState) -> dict[str, Any]:
    report = state.get("report", {})
    issues = []
    if not report.get("title"):
        issues.append("Report title is missing.")
    if not state.get("documents"):
        issues.append("No input document was ingested.")
    if not report.get("analysis"):
        issues.append("Analysis is missing.")
    if issues:
        raise ValueError("Quality review failed: " + " ".join(issues))
    return {"quality_review": {"passed": True, "issues": []}, "shared_memory": _event(state, "quality: validation passed")}
