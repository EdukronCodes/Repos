"""LangGraph file-to-report multi-agent system.

The workflow is local-first and accepts tabular, document, media, image, and
archive files. Optional OCR, speech, web, and vector integrations degrade
gracefully when their providers are not installed or configured.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any, TypedDict
from xml.sax.saxutils import escape

import pandas as pd
from langgraph.graph import END, START, StateGraph
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return None if pd.isna(value) else value
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _display(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}" if not value.is_integer() else f"{value:,.0f}"
    return str(value)[:100]


class FileParsers:
    """File parsers used by the File Ingestion Agent."""

    TEXT_EXTENSIONS = {".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml", ".html", ".htm"}

    def parse(self, path: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        suffix = path.suffix.lower()
        if suffix in {".xlsx", ".xls", ".xlsm", ".ods"}:
            workbook = pd.read_excel(path, sheet_name=None)
            return ([{"name": name, "kind": "table", "text": frame.to_csv(index=False)} for name, frame in workbook.items()], {name: self._records(frame) for name, frame in workbook.items()})
        if suffix == ".csv":
            frame = pd.read_csv(path)
            return ([{"name": path.name, "kind": "table", "text": frame.to_csv(index=False)}], {path.stem: self._records(frame)})
        if suffix == ".pdf":
            return ([{"name": path.name, "kind": "pdf", "text": self._pdf(path)}], {})
        if suffix == ".docx":
            return ([{"name": path.name, "kind": "document", "text": self._docx(path)}], {})
        if suffix in {".pptx", ".ppt"}:
            return ([{"name": path.name, "kind": "presentation", "text": self._pptx(path)}], {})
        if suffix in self.TEXT_EXTENSIONS:
            return ([{"name": path.name, "kind": "text", "text": path.read_text(encoding="utf-8", errors="replace")}], {})
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}:
            return ([{"name": path.name, "kind": "image", "text": OCR().extract(path)}], {})
        if suffix in {".mp3", ".wav", ".m4a", ".mp4", ".mov", ".avi", ".mkv"}:
            return ([{"name": path.name, "kind": "media", "text": SpeechToText().transcribe(path)}], {})
        if suffix in {".zip", ".rar", ".7z", ".tar", ".gz"}:
            return ([{"name": path.name, "kind": "archive", "text": self._archive(path)}], {})
        return ([{"name": path.name, "kind": "binary", "text": f"File type: {mimetypes.guess_type(path.name)[0] or 'unknown'}"}], {})

    @staticmethod
    def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
        return [{str(key): _json_safe(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]

    @staticmethod
    def _pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except ImportError:
            return "PDF text extraction unavailable; install pypdf."

    @staticmethod
    def _docx(path: Path) -> str:
        try:
            from docx import Document
            return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
        except ImportError:
            return "DOCX text extraction unavailable; install python-docx."

    @staticmethod
    def _pptx(path: Path) -> str:
        try:
            from pptx import Presentation
            return "\n".join(shape.text for slide in Presentation(str(path)).slides for shape in slide.shapes if hasattr(shape, "text"))
        except ImportError:
            return "PPTX text extraction unavailable; install python-pptx."

    @staticmethod
    def _archive(path: Path) -> str:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                return "Archive members:\n" + "\n".join(archive.namelist())
        return "Archive inspection is available for ZIP files; received " + path.suffix


class OCR:
    """OCR tool integration for image inputs."""

    def extract(self, path: Path) -> str:
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(path))
        except ImportError:
            return "OCR unavailable; install pillow and pytesseract."


class SpeechToText:
    """Speech-to-text integration point for audio and video inputs."""

    def transcribe(self, path: Path) -> str:
        try:
            result = subprocess.run(["ffprobe", "-v", "error", "-show_format", str(path)], capture_output=True, text=True, check=False)
            return f"Media metadata for {path.name}:\n{result.stdout or result.stderr}"
        except FileNotFoundError:
            return "Speech-to-text unavailable; install ffmpeg and configure a transcription provider."


class DataAnalysis:
    """Data analysis and insight generation tools."""

    def summarize_tables(self, tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
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

    @staticmethod
    def keyword_summary(text: str) -> list[tuple[str, int]]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
        stop = {"this", "that", "with", "from", "have", "were", "there", "their", "which"}
        counts = pd.Series([word for word in words if word not in stop]).value_counts()
        return [(str(word), int(count)) for word, count in counts.head(10).items()]


class Visualization:
    """Optional chart tool used by the report generation agent."""

    def create(self, analysis: dict[str, Any], directory: Path) -> list[str]:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return []
        paths = []
        for sheet in analysis.get("tables", []):
            if not sheet["numeric"]:
                continue
            figure, axis = plt.subplots(figsize=(7, 3.5))
            axis.bar([item["column"] for item in sheet["numeric"]], [item["total"] for item in sheet["numeric"]], color="#168AAD")
            axis.set_title(f"Totals: {sheet['name']}")
            axis.tick_params(axis="x", rotation=35)
            figure.tight_layout()
            output = directory / f"{Path(sheet['name']).stem}_summary.png"
            figure.savefig(output, dpi=150)
            plt.close(figure)
            paths.append(str(output))
        return paths


class WebSearch:
    """Network-free web search adapter; replace with a provider when enabled."""

    def search(self, query: str) -> list[dict[str, str]]:
        return [{"query": query, "status": "disabled", "message": "Configure a search provider to enable web search."}]


class VectorStore:
    """In-memory retrieval tool for shared report context."""

    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, name: str, text: str) -> None:
        self.items.append({"name": name, "text": text})

    def search(self, query: str, limit: int = 3) -> list[dict[str, str]]:
        terms = set(query.lower().split())
        return sorted(self.items, key=lambda item: len(terms & set(item["text"].lower().split())), reverse=True)[:limit]


def supervisor(state: ReportState) -> dict[str, Any]:
    path = Path(state["input_path"])
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return {"plan": {"goal": state.get("user_goal") or "Understand the input and generate an actionable report.", "stages": ["ingest", "understand", "analyze", "generate", "review", "deliver"]}, "shared_memory": {"source": str(path), "events": ["supervisor: plan created"]}}


def ingest_files(state: ReportState) -> dict[str, Any]:
    path = Path(state["input_path"])
    documents, tables = FileParsers().parse(path)
    memory = dict(state.get("shared_memory", {}))
    memory["events"] = memory.get("events", []) + [f"ingestion: parsed {path.suffix or 'file'}"]
    return {"documents": documents, "tables": tables, "shared_memory": memory}


def understand_content(state: ReportState) -> dict[str, Any]:
    store = VectorStore()
    for document in state["documents"]:
        store.add(document["name"], document["text"])
    text = "\n".join(document["text"] for document in state["documents"])
    return {"understanding": {"file_count": len(state["documents"]), "content_chars": len(text), "keywords": DataAnalysis.keyword_summary(text), "retrieval": store.search(state["plan"]["goal"]), "kinds": [document["kind"] for document in state["documents"]]}}


def analyze_content(state: ReportState) -> dict[str, Any]:
    text = "\n".join(document["text"] for document in state["documents"])
    return {"analysis": {"tables": DataAnalysis().summarize_tables(state.get("tables", {})), "keywords": DataAnalysis.keyword_summary(text), "text_preview": text[:2000], "web_context": WebSearch().search(state["plan"]["goal"])}}


def generate_report(state: ReportState) -> dict[str, Any]:
    title = state.get("title") or f"File report: {Path(state['input_path']).stem}"
    tables = state["analysis"]["tables"]
    total_rows = sum(table["rows"] for table in tables)
    report = {"title": title, "goal": state["plan"]["goal"], "overview": [f"{len(state['documents'])} input file(s) processed", f"{total_rows:,} tabular row(s) analyzed", f"{state['understanding']['content_chars']:,} content character(s) indexed"], "understanding": state["understanding"], "analysis": state["analysis"]}
    report["charts"] = Visualization().create(state["analysis"], Path(state["output_path"]).parent)
    return {"report": report}


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
    return {"quality_review": {"passed": True, "issues": []}}


def _table(rows: list[list[str]], widths: list[float] | None = None) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#19324D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CF")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF3F6")]), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    return table


def _publish_pdf(report: dict[str, Any], output: Path) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#19324D"))
    story = [Paragraph(escape(report["title"]), title_style), Spacer(1, 0.15 * inch), Paragraph(escape(report["goal"]), styles["BodyText"]), Spacer(1, 0.15 * inch), Paragraph(escape(" | ".join(report["overview"])), styles["BodyText"])]
    for index, sheet in enumerate(report["analysis"]["tables"]):
        story.extend([PageBreak() if index else Spacer(1, 0.2 * inch), Paragraph(f"Table: {escape(sheet['name'])}", styles["Heading2"])])
        story.append(Paragraph(f"Rows: {sheet['rows']:,} | Missing cells: {sheet['missing_cells']:,} | Duplicate rows: {sheet['duplicate_rows']:,}", styles["BodyText"]))
        if sheet["numeric"]:
            rows = [["Column", "Mean", "Minimum", "Maximum", "Total"]] + [[item["column"], _display(item["mean"]), _display(item["minimum"]), _display(item["maximum"]), _display(item["total"])] for item in sheet["numeric"]]
            story.extend([Spacer(1, 0.1 * inch), Paragraph("Numeric summary", styles["Heading3"]), _table(rows, [1.6 * inch] + [1.05 * inch] * 4)])
        if sheet["categorical"]:
            rows = [["Column", "Top values"]] + [[item["column"], ", ".join(f"{value} ({count})" for value, count in item["top"])] for item in sheet["categorical"]]
            story.extend([Spacer(1, 0.15 * inch), Paragraph("Categorical summary", styles["Heading3"]), _table(rows, [1.6 * inch, 4.9 * inch])])
    SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.55 * inch, bottomMargin=0.55 * inch).build(story)


def _write_outputs(state: ReportState) -> list[str]:
    report = state["report"]
    output = Path(state["output_path"])
    format_name = state.get("output_format", "pdf").lower()
    output = output.with_suffix("." + format_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "pdf":
        _publish_pdf(report, output)
    elif format_name in {"json", "md", "html"}:
        if format_name == "json":
            payload = json.dumps(report, indent=2, default=str)
        elif format_name == "md":
            payload = f"# {report['title']}\n\n{report['goal']}\n\n" + "\n".join(f"- {item}" for item in report["overview"]) + "\n\n## Findings\n\n" + "\n".join(f"### {sheet['name']}\n\nRows: {sheet['rows']}" for sheet in report["analysis"]["tables"])
        else:
            payload = f"<html><body><h1>{escape(report['title'])}</h1><p>{escape(report['goal'])}</p><ul>" + "".join(f"<li>{escape(item)}</li>" for item in report["overview"]) + "</ul><pre>" + escape(json.dumps(report["analysis"], indent=2, default=str)) + "</pre></body></html>"
        output.write_text(payload, encoding="utf-8")
    elif format_name == "csv":
        rows = []
        for sheet in report["analysis"]["tables"]:
            rows.extend({"table": sheet["name"], "column": item["column"], "mean": item["mean"], "minimum": item["minimum"], "maximum": item["maximum"], "total": item["total"]} for item in sheet["numeric"])
        pd.DataFrame(rows).to_csv(output, index=False)
    elif format_name == "xlsx":
        with pd.ExcelWriter(output) as writer:
            pd.DataFrame(report["overview"], columns=["overview"]).to_excel(writer, sheet_name="Overview", index=False)
            for sheet in report["analysis"]["tables"]:
                pd.DataFrame(sheet["numeric"]).to_excel(writer, sheet_name=str(sheet["name"])[:31] or "Data", index=False)
    elif format_name == "docx":
        from docx import Document
        document = Document()
        document.add_heading(report["title"], 0)
        document.add_paragraph(report["goal"])
        document.add_paragraph(" | ".join(report["overview"]))
        for sheet in report["analysis"]["tables"]:
            document.add_heading(sheet["name"], level=1)
            document.add_paragraph(f"Rows: {sheet['rows']}")
            for item in sheet["numeric"]:
                document.add_paragraph(f"{item['column']}: mean {item['mean']:.2f}, total {item['total']:.2f}")
        document.save(output)
    elif format_name == "pptx":
        from pptx import Presentation
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = report["title"]
        slide.placeholders[1].text = report["goal"] + "\n" + "\n".join(report["overview"])
        presentation.save(output)
    else:
        raise ValueError(f"Unsupported output format: {format_name}")
    return [str(output)]


def deliver_report(state: ReportState) -> dict[str, Any]:
    return {"published_paths": _write_outputs(state)}


def build_graph() -> Any:
    graph = StateGraph(ReportState)
    nodes = [("supervisor", supervisor), ("file_ingestion", ingest_files), ("content_understanding", understand_content), ("analysis", analyze_content), ("report_generation", generate_report), ("quality_review", quality_review), ("delivery", deliver_report)]
    for name, node in nodes:
        graph.add_node(name, node)
    for before, after in zip([START] + [name for name, _ in nodes], [name for name, _ in nodes] + [END]):
        graph.add_edge(before, after)
    return graph.compile()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reports from many file types with LangGraph agents.")
    parser.add_argument("input", type=Path, help="Excel, PDF, DOCX, PPTX, CSV, text, image, media, or archive")
    parser.add_argument("--output", type=Path, default=Path("report.pdf"), help="Output filename")
    parser.add_argument("--format", choices=["pdf", "docx", "xlsx", "csv", "pptx", "html", "md", "json"], default="pdf")
    parser.add_argument("--title", default="", help="Report title")
    parser.add_argument("--goal", default="", help="User goal for the supervisor")
    args = parser.parse_args()
    result = build_graph().invoke({"input_path": str(args.input), "output_path": str(args.output), "output_format": args.format, "title": args.title, "user_goal": args.goal})
    print(f"Created: {', '.join(result['published_paths'])}")


if __name__ == "__main__":
    main()