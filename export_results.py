from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CORRECT_FILL = PatternFill("solid", fgColor="C6EFCE")
WRONG_FILL = PatternFill("solid", fgColor="FFC7CE")
BLANK_FILL = PatternFill("solid", fgColor="FFEB9C")
INCONCLUSIVE_FILL = PatternFill("solid", fgColor="BDD7EE")
HEADER_FILL = PatternFill("solid", fgColor="D9EAF7")


def build_results_workbook(answer_key: tuple[str, ...], records: list[dict[str, Any]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "MCQ Results"

    sheet.cell(1, 1, "ANSWER KEY")
    for question, answer in enumerate(answer_key, start=1):
        cell = sheet.cell(1, question + 1, answer)
        cell.fill = CORRECT_FILL
        cell.comment = Comment(f"Question {question}", "ShadeSpark")
    sheet.cell(1, 52, "MAX SCORE")
    sheet.cell(1, 53, "PERCENT")
    sheet.cell(1, 54, "CRN")
    sheet.cell(1, 55, "GRADING STATUS")
    sheet.cell(1, 56, "SOURCE")

    for row_number, record in enumerate(records, start=2):
        sheet.cell(row_number, 1, record["student_id"])
        for question, (selected, outcome) in enumerate(
            zip(record["answers"], record["outcomes"], strict=True), start=1
        ):
            cell = sheet.cell(row_number, question + 1, "/".join(selected) if selected else "-")
            if selected is not None and len(selected) > 1:
                cell.fill = INCONCLUSIVE_FILL
            elif outcome == "correct":
                cell.fill = CORRECT_FILL
            elif outcome == "inconclusive":
                cell.fill = INCONCLUSIVE_FILL
            else:
                cell.fill = BLANK_FILL if selected is None else WRONG_FILL
        sheet.cell(row_number, 52, record["score"])
        sheet.cell(row_number, 53, record["percentage"] / 100)
        sheet.cell(row_number, 53).number_format = "0.0%"
        sheet.cell(row_number, 54, record["crn"] or "")
        status_cell = sheet.cell(row_number, 55, record["grading_status"])
        if record["grading_status"] == "Partial":
            status_cell.fill = INCONCLUSIVE_FILL
        sheet.cell(row_number, 56, f'{record["source"]} / page {record["page"]}')

    for cell in sheet[1]:
        cell.font = Font(bold=True)
        if cell.fill.fill_type is None:
            cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

    sheet.freeze_panes = "B2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(56)}{max(len(records) + 1, 2)}"
    sheet.column_dimensions["A"].width = 16
    for column in range(2, 52):
        sheet.column_dimensions[get_column_letter(column)].width = 4
    sheet.column_dimensions[get_column_letter(52)].width = 12
    sheet.column_dimensions[get_column_letter(53)].width = 12
    sheet.column_dimensions[get_column_letter(54)].width = 10
    sheet.column_dimensions[get_column_letter(55)].width = 18
    sheet.column_dimensions[get_column_letter(56)].width = 34

    legend = workbook.create_sheet("Legend")
    legend.append(["Color", "Meaning"])
    legend.append(["Green", "Correct answer"])
    legend.append(["Red", "Wrong answer"])
    legend.append(["Yellow", "Blank answer"])
    legend.append(["Blue", "Review issue: multiple options shaded"])
    legend["A2"].fill = CORRECT_FILL
    legend["A3"].fill = WRONG_FILL
    legend["A4"].fill = BLANK_FILL
    legend["A5"].fill = INCONCLUSIVE_FILL
    legend.column_dimensions["A"].width = 16
    legend.column_dimensions["B"].width = 34

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
