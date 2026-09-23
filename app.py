"""HTTP access layer for the LangGraph file-to-report system."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from excel_report import build_graph

app = FastAPI(title="LangGraph File-to-Report API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reports")
async def create_report(
    file: UploadFile = File(...),
    goal: str = Form("Understand this file and summarize the important findings."),
    title: str = Form(""),
    format: str = Form("pdf"),
) -> dict[str, object]:
    suffix = Path(file.filename or "input.bin").suffix
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / f"input{suffix}"
        output = Path(directory) / f"report.{format}"
        with source.open("wb") as target:
            shutil.copyfileobj(file.file, target)
        result = build_graph().invoke({"input_path": str(source), "output_path": str(output), "output_format": format, "title": title, "user_goal": goal})
        return {"files": result["published_paths"], "quality_review": result["quality_review"], "plan": result["plan"]}


@app.post("/chat")
def chat(request: dict[str, str]) -> dict[str, object]:
    """Chat-style JSON access for files already available on the server."""
    input_path = request["input_path"]
    output_format = request.get("format", "json")
    output_path = request.get("output_path", f"report.{output_format}")
    result = build_graph().invoke({"input_path": input_path, "output_path": output_path, "output_format": output_format, "title": request.get("title", ""), "user_goal": request.get("goal", "")})
    return {"files": result["published_paths"], "quality_review": result["quality_review"], "plan": result["plan"]}