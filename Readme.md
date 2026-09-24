# LangGraph File-to-Report Multi-Agent System

This project implements the supplied architecture as a local-first reporting
system. It ingests common file types, understands and analyzes their content,
reviews the result, and publishes structured reports.

## Agents and Shared State

	initializes shared memory.
	media, and ZIP inputs.
	retrieves relevant context from the in-memory vector store.
	duplicates, keywords, and optional web context.
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

# File Intelligence

Streamlit UI and LangGraph multi-agent system for analyzing uploaded files and generating structured reports.

## Run the UI

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Upload a supported document, spreadsheet, media, image, archive, or text file. The report runs automatically and can be downloaded as PDF, DOCX, XLSX, CSV, PPTX, HTML, Markdown, or JSON.

The UI includes an **Execution flow** tab with the visual agent graph. See [PROJECT_REPORT.md](PROJECT_REPORT.md) for the end-to-end architecture, state contract, execution trace, output matrix, and validation plan. Generate test fixtures with `python samples/generate_samples.py`; the inventory is documented in [samples/README.md](samples/README.md).

## Agents

- `Supervisor`: creates the goal and workflow plan.
- `File Ingestion Agent`: loads every workbook sheet into shared state.
- `Content Understanding Agent`: indexes content and extracts keywords.
- `Analysis Agent`: calculates numeric summaries, missing cells, and duplicates.
- `Report Generation Agent`: builds the report model.
- `Quality Review Agent`: checks report completeness.
- `Delivery Agent`: publishes the selected download format.

The implementation is split into `report_system/state.py`, `parsing.py`, `agents.py`, `publishing.py`, and `graph.py`. LangGraph passes the typed shared state between each agent.

## CLI

```bash
python excel_report.py input.xlsx --format xlsx --output report.xlsx --goal "Summarize revenue by region"
```
