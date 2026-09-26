from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from export_results import build_results_workbook
from grading import grade_answers, questions_requiring_review
from pdf_processing import render_pdf_pages, scan_pdf
from scanner import ScanError, scan_image

APP_DIR = Path(__file__).parent
TEMPLATE_PATH = APP_DIR / "MCQ_Answer_Sheet_50_Questions.pdf"

st.set_page_config(page_title="ShadeSpark", page_icon="✓", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f5f4ef; color: #17201d; }
    [data-testid="stHeader"] { background: transparent; }
    h1, h2, h3 { font-family: Georgia, serif; letter-spacing: 0; }
    .block-container { max-width: 1280px; padding-top: 2.2rem; }
    div[data-testid="stMetric"] { border-top: 3px solid #247158; padding-top: .8rem; }
    @media (max-width: 480px) {
        h1 { font-size: 2.5rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("ShadeSpark")
st.caption("Optical Marking Made Easy")

with st.sidebar:
    st.header("Answer sheet")
    if TEMPLATE_PATH.exists():
        st.download_button(
            "Download blank PDF",
            data=TEMPLATE_PATH.read_bytes(),
            file_name=TEMPLATE_PATH.name,
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.caption("Blank answer-sheet download is unavailable.")
    st.markdown("Print at **Actual size / 100%** and scan the complete A4 page with all four corner squares visible.")

st.subheader("1. Answer key")
is_answer_key = st.checkbox("This upload is the answer key", value=True)
answer_key_file = st.file_uploader(
    "Upload one completed answer-key PDF",
    type=["pdf"],
    accept_multiple_files=False,
    disabled=not is_answer_key,
    key="answer-key",
)

st.subheader("2. Student scripts")
student_files = st.file_uploader(
    "Upload one or more PDFs. Each page must contain one student's answer sheet.",
    type=["pdf"],
    accept_multiple_files=True,
    key="student-scripts",
)


def process_uploads() -> tuple[tuple[str, ...], list[dict[str, Any]], list[str]]:
    if answer_key_file is None:
        raise ScanError("Upload the single-page answer key first.")
    if not student_files:
        raise ScanError("Upload at least one student PDF.")

    key_pages = render_pdf_pages(answer_key_file.getvalue())
    if len(key_pages) != 1:
        raise ScanError("The answer key must be a single-page PDF.")
    key_scan = scan_image(key_pages[0])
    invalid = [index + 1 for index, answer in enumerate(key_scan.answers) if answer is None or len(answer) != 1]
    if invalid:
        raise ScanError("The answer key must have exactly one answer per question. Review: " + ", ".join(map(str, invalid)))
    answer_key = tuple(answer for answer in key_scan.answers if answer is not None)

    records: list[dict[str, Any]] = []
    notices: list[str] = []
    for uploaded_file in student_files:
        for page_scan in scan_pdf(uploaded_file.getvalue(), uploaded_file.name):
            if page_scan.error is not None or page_scan.result is None:
                notices.append(f"{page_scan.source}, page {page_scan.page}: {page_scan.error}")
                continue
            result = page_scan.result
            if result.student_id is None:
                notices.append(f"{page_scan.source}, page {page_scan.page}: student ID requires review; page skipped.")
                continue
            outcomes, score, grading_complete = grade_answers(result.answers, answer_key)
            records.append(
                {
                    "student_id": result.student_id,
                    "crn": result.crn,
                    "answers": result.answers,
                    "outcomes": outcomes,
                    "score": score,
                    "percentage": score * 2.0,
                    "grading_status": "Complete" if grading_complete else "Partial",
                    "source": page_scan.source,
                    "page": page_scan.page,
                    "script_image": page_scan.image,
                    "warnings": " ".join(result.warnings),
                }
            )

    if not records:
        raise ScanError("No student pages with a readable shaded ID were found.")
    return answer_key, records, notices


if st.button("Scan and mark", type="primary", use_container_width=True):
    try:
        with st.spinner("Aligning pages, reading marks, and calculating grades..."):
            key, results, scan_notices = process_uploads()
        st.session_state["answer_key"] = key
        st.session_state["results"] = results
        st.session_state["scan_notices"] = scan_notices
    except ScanError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Processing failed: {exc}")

if "results" in st.session_state:
    records = st.session_state["results"]
    answer_key = st.session_state["answer_key"]
    notices = st.session_state.get("scan_notices", [])

    st.divider()
    st.subheader("Results dashboard")
    crn_values = sorted({record["crn"] for record in records if record["crn"]})
    selected_crn = st.selectbox("Select CRN", ["All CRNs", *crn_values])
    filtered = records if selected_crn == "All CRNs" else [record for record in records if record["crn"] == selected_crn]

    scores = np.array([record["score"] for record in filtered])
    metric_columns = st.columns(4)
    metric_columns[0].metric("Students", len(filtered))
    metric_columns[1].metric("Average", f"{scores.mean():.1f} / 50")
    metric_columns[2].metric("Median", f"{np.median(scores):.1f} / 50")
    metric_columns[3].metric("Highest", f"{scores.max()} / 50")

    summary_tab, detail_tab = st.tabs(["Summary", "Detailed responses"])
    with summary_tab:
        st.markdown("#### Grade distribution")
        counts, _ = np.histogram(scores, bins=[0, 10, 20, 30, 40, 46, 51])
        labels = ["0–9", "10–19", "20–29", "30–39", "40–45", "46–50"]
        st.bar_chart(pd.DataFrame({"Score band": labels, "Students": counts}).set_index("Score band"))

        st.markdown("#### Student grades")
        st.caption("Select a student row to view the scanned answer script.")
        display = pd.DataFrame(
            {
                "Student ID": [record["student_id"] for record in filtered],
                "CRN": [record["crn"] or "Needs review" for record in filtered],
                "Score": [record["score"] for record in filtered],
                "Percent": [f'{record["percentage"]:.1f}%' for record in filtered],
                "Grading": [record["grading_status"] for record in filtered],
                "Source": [f'{record["source"]} p.{record["page"]}' for record in filtered],
            }
        )
        summary_styles = pd.DataFrame("", index=display.index, columns=display.columns)
        for row_index, record in enumerate(filtered):
            if record["grading_status"] == "Partial":
                summary_styles.loc[row_index, :] = "background-color: #e2f0d9"
        grade_selection = st.dataframe(
            display.style.apply(lambda _: summary_styles, axis=None),
            hide_index=True,
            width="stretch",
            height=min(700, 38 + 35 * len(display)),
            key=f"student-grades-{selected_crn}",
            on_select="rerun",
            selection_mode="single-row",
        )
        selected_rows = grade_selection.selection.rows
        if selected_rows:
            selected_record = filtered[selected_rows[0]]
            st.markdown(f'#### Scanned script: {selected_record["student_id"]}')
            st.caption(
                f'CRN {selected_record["crn"] or "Needs review"} · '
                f'{selected_record["source"]}, page {selected_record["page"]}'
            )
            review_questions = questions_requiring_review(selected_record["outcomes"])
            if selected_record["grading_status"] == "Partial":
                question_list = ", ".join(f"Q{question}" for question in review_questions)
                st.warning(f"Grading: Partial · Questions requiring review: {question_list}")
            else:
                st.success("Grading: Complete")
            script_image = selected_record.get("script_image")
            if script_image is None:
                st.warning("This result was created before script viewing was enabled. Select Scan and mark again.")
            else:
                st.image(script_image, width="stretch")

    with detail_tab:
        st.markdown("#### Question-level responses")
        detail_rows = []
        outcome_by_cell: dict[tuple[int, str], str] = {}
        for row_index, record in enumerate(filtered):
            row: dict[str, Any] = {
                "Student ID": record["student_id"],
                "CRN": record["crn"] or "Needs review",
            }
            for question, (answer, outcome) in enumerate(
                zip(record["answers"], record["outcomes"], strict=True), start=1
            ):
                column = f"Q{question}"
                row[column] = "/".join(answer) if answer else "-"
                outcome_by_cell[(row_index, column)] = "blank" if answer is None else outcome
            row.update(
                {
                    "Score": record["score"],
                    "Percent": f'{record["percentage"]:.1f}%',
                    "Grading": record["grading_status"],
                }
            )
            detail_rows.append(row)

        detailed = pd.DataFrame(detail_rows)
        detail_styles = pd.DataFrame("", index=detailed.index, columns=detailed.columns)
        outcome_colors = {
            "correct": "background-color: #c6efce",
            "inconclusive": "background-color: #bdd7ee",
            "wrong": "background-color: #ffc7ce",
            "blank": "background-color: #ffeb9c",
        }
        for (row_index, column), outcome in outcome_by_cell.items():
            detail_styles.loc[row_index, column] = outcome_colors[outcome]
        for row_index, record in enumerate(filtered):
            if record["grading_status"] == "Partial":
                detail_styles.loc[row_index, "Grading"] = "background-color: #bdd7ee"

        st.dataframe(
            detailed.style.apply(lambda _: detail_styles, axis=None),
            hide_index=True,
            use_container_width=True,
            height=min(700, 38 + 35 * len(detailed)),
        )

    workbook = build_results_workbook(answer_key, records)
    st.download_button(
        "Download marked Excel workbook",
        workbook,
        file_name="shadespark_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    if notices:
        with st.expander(f"Pages requiring attention ({len(notices)})"):
            for notice in notices:
                st.warning(notice)

st.markdown(
    '<p style="border-top: 1px solid #c9c7bd; margin-top: 3rem; padding-top: 1rem; text-align: center; color: #59615e; font-size: 0.85rem;">Developed by Dr Ravi Suppiah ETS@HCT</p>',
    unsafe_allow_html=True,
)
