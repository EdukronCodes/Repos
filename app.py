from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from report_system.graph import build_graph
from report_system.publishing import SUPPORTED_FORMATS, report_bytes


st.set_page_config(page_title="File Intelligence", page_icon="📊", layout="wide")
st.title("File Intelligence")
st.caption("Upload a file and let the LangGraph multi-agent pipeline turn it into a structured report.")

with st.sidebar:
    st.header("Report settings")
    title = st.text_input("Report title", placeholder="Quarterly performance review")
    goal = st.text_area("Analysis goal", value="Understand this file and summarize the important findings.", height=110)
    output_format = st.selectbox("Download format", SUPPORTED_FORMATS, index=2)

input_types = ["pdf", "doc", "docx", "xls", "xlsx", "xlsm", "ods", "csv", "ppt", "pptx", "txt", "md", "log", "json", "xml", "yaml", "yml", "html", "png", "jpg", "jpeg", "tif", "tiff", "webp", "mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "zip", "tar", "gz", "rar", "7z"]
uploaded = st.file_uploader("Drop a file here", type=input_types)

flow_tab, report_tab = st.tabs(["Execution flow", "Generated report"])

with flow_tab:
    st.subheader("How the code executes")
    st.graphviz_chart("""digraph { rankdir=LR; input [label="Upload\nStreamlit"]; supervisor [label="Supervisor\nplan + route"]; ingest [label="File Ingestion\nparse input"]; understand [label="Content Understanding\nextract context"]; analyze [label="Analysis\nfindings + metrics"]; generate [label="Report Generation\nstructured report"]; review [label="Quality Review\nvalidate"]; deliver [label="Delivery\nexport format"]; state [label="Shared State", shape=cylinder]; input -> supervisor -> ingest -> understand -> analyze -> generate -> review -> deliver; state -> ingest; state -> understand; state -> analyze; state -> generate; state -> review; }""")
    st.markdown("**Runtime path:** `app.py` saves the upload temporarily, `build_graph()` compiles LangGraph, each node returns a partial state update, and the delivery node writes the selected report format.")

with report_tab:
    if not uploaded:
        st.info("Upload a supported file to start the agents automatically.")
    else:
        st.success(f"Ready to analyze **{uploaded.name}**")
        result_key = (uploaded.name, title, goal, output_format)
        if st.session_state.get("result_key") != result_key:
            st.session_state.pop("result", None)
            st.session_state["result_key"] = result_key

        if "result" not in st.session_state:
            with st.status("Running report agents...", expanded=True) as status:
                try:
                    with tempfile.TemporaryDirectory() as directory:
                        source = Path(directory) / uploaded.name
                        source.write_bytes(uploaded.getvalue())
                        result = build_graph().invoke({"input_path": str(source), "output_path": str(Path(directory) / "report"), "output_format": output_format, "title": title, "user_goal": goal})
                        data, filename, mime = report_bytes(result["report"], output_format)
                    st.session_state["result"] = {"data": data, "filename": filename, "mime": mime, "report": result["report"], "review": result["quality_review"], "events": result.get("shared_memory", {}).get("events", [])}
                    status.update(label="Report generated", state="complete")
                except Exception as error:
                    status.update(label="Report generation failed", state="error")
                    st.exception(error)

        result = st.session_state.get("result")
        if result:
            report = result["report"]
            left, right = st.columns([2, 1])
            with left:
                st.subheader(report["title"])
                st.write(report["goal"])
                st.download_button("Download report", result["data"], result["filename"], result["mime"], type="primary")
            with right:
                st.metric("Sources analyzed", report["understanding"]["file_count"])
                st.metric("Rows analyzed", sum(sheet["rows"] for sheet in report["analysis"]["tables"]))
            st.divider()
            st.subheader("Agent execution trace")
            st.write(result["events"] or ["supervisor", "file_ingestion", "content_understanding", "analysis", "report_generation", "quality_review", "delivery"])
            st.subheader("Findings")
            for sheet in report["analysis"]["tables"]:
                with st.expander(sheet["name"], expanded=True):
                    st.write(f"{sheet['rows']:,} rows, {len(sheet['columns'])} columns, {sheet['missing_cells']:,} missing cells, {sheet['duplicate_rows']:,} duplicate rows")
                    if sheet["numeric"]:
                        st.dataframe(sheet["numeric"], use_container_width=True, hide_index=True)
