# ShadeSpark

ShadeSpark scans the included 50-question A4 MCQ answer sheet, marks student responses against a single-page answer key, displays grade statistics by CRN, and exports a color-coded Excel workbook.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Workflow

1. Download and print `MCQ_Answer_Sheet_50_Questions.pdf` at 100% / Actual size.
2. Complete one sheet as the answer key and scan it as a single-page PDF.
3. Scan student sheets. Each page must contain one complete sheet; a PDF may contain any number of students.
4. Upload the key and one or more student PDFs, then select **Scan and mark**.
5. Review the CRN-filtered dashboard and download the Excel workbook.

For reliable recognition, fill bubbles fully with a dark pencil or black pen. Keep all four corner squares visible, avoid shadows, and scan near 300 DPI. Pages with unreadable IDs are skipped and listed for review; blank or ambiguous answers receive zero and are highlighted yellow in Excel.
