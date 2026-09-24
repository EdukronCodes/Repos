# Sample Inputs

Generate the complete fixture pack from the repository root:

```bash
python samples/generate_samples.py
```

The script creates:

- `sample_workbook.xlsx`, `sample_sales.csv`: tabular inputs
- `sample_report.pdf`, `sample_report.docx`, `sample_presentation.pptx`: office/document inputs
- `sample_notes.txt`, `sample_notes.md`, `sample_events.log`, `sample_data.json`, `sample_data.xml`, `sample_data.yaml`, `sample_page.html`: text inputs
- `sample_image.png`: image/OCR input
- `sample_archive.zip`: compressed input containing text and CSV files
- `sample_audio.wav`, `sample_video.mp4`: media inputs when `ffmpeg` is installed

Upload any generated file in the Streamlit UI. The parser reports graceful fallback text when optional tools such as Tesseract or ffmpeg are not installed.
