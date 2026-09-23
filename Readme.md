 # Excel to PDF Multi-Agent System

This project turns an Excel workbook into a concise PDF report with a LangGraph
workflow. The graph contains four agents:

1. `Supervisor`: validates the request and establishes the shared execution
	plan.
2. `WorkbookInspector`: loads every worksheet and profiles its shape, columns,
	missing values, and sample rows.
3. `DataAnalyst`: finds numeric summaries, categorical distributions, and
	simple quality signals.
4. `ReportWriter`: converts those findings into a structured report.
5. `QualityReview`: checks completeness and worksheet consistency before
	publication.
6. `PdfPublisher`: renders the approved report as a readable PDF.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python excel_report.py input.xlsx --output report.pdf --title "Quarterly Review" \
	--goal "Compare revenue and order performance by region"
```

The input can contain multiple worksheets. The output path is created or
overwritten. No API key is required: the agents use local, reproducible
analysis. `langgraph` is used for orchestration so an LLM-backed writer can be
added later without changing the workflow contract.

## Workflow

```text
Excel workbook -> supervisor -> inspect -> analyze -> write -> quality review -> PDF
```
