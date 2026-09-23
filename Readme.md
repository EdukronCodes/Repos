# LangGraph File-to-Report Multi-Agent System

This project implements the supplied architecture as a local-first reporting
system. It ingests common file types, understands and analyzes their content,
reviews the result, and publishes structured reports.

## Agents and Shared State

- `Supervisor`: understands the user goal, creates the workflow plan, and
	initializes shared memory.
- `File Ingestion Agent`: parses Excel/XLSX, CSV, PDF, DOCX, PPTX, text, images,
	media, and ZIP inputs.
- `Content Understanding Agent`: extracts text, keywords, document kinds, and
	retrieves relevant context from the in-memory vector store.
- `Analysis Agent`: calculates table statistics, distributions, missing values,
	duplicates, keywords, and optional web context.
- `Report Generation Agent`: creates the report model and optional charts.
- `Quality Review Agent`: validates completeness before delivery.
- `Shared Memory / State`: LangGraph state passes the plan, documents, tables,
	findings, and review results between agents.

Tool integrations are represented by `FileParsers`, `OCR`, `SpeechToText`,
`DataAnalysis`, `Visualization`, `WebSearch`, and `VectorStore`. OCR,
transcription, matplotlib, and web search are optional integrations; the
pipeline still produces a report when they are unavailable.

## Outputs

The delivery agent supports PDF, DOCX, XLSX, CSV, PPTX, HTML, Markdown, JSON,
and can be extended with custom publishers in `_write_outputs`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI

```bash
python excel_report.py input.xlsx \
	--output report.pdf \
	--format pdf \
	--title "Quarterly Review" \
	--goal "Compare revenue and order performance by region"
```

Change `--format` to `docx`, `xlsx`, `csv`, `pptx`, `html`, `md`, or `json`.
No API key is required: the default analysis is local and reproducible.

## HTTP API

Install dependencies and start the access layer:

```bash
uvicorn app:app --reload
```

Use `POST /reports` with a multipart `file`, optional `goal`, `title`, and
`format` fields. Use `POST /chat` with JSON such as
`{"input_path":"input.xlsx","goal":"Summarize sales"}`.

## Workflow

```text
Input files -> Supervisor -> Ingestion -> Understanding -> Analysis -> Report
Generation -> Quality Review -> Generated reports
```
