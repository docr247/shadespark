from __future__ import annotations

from typing import Literal

AnswerOutcome = Literal["correct", "wrong", "inconclusive"]


def grade_answer(selected: str | None, correct: str) -> AnswerOutcome:
    if selected == correct:
        return "correct"
    if selected is not None and len(selected) > 1 and correct in selected:
        return "inconclusive"
    return "wrong"


def grade_answers(
    answers: tuple[str | None, ...], answer_key: tuple[str, ...]
) -> tuple[tuple[AnswerOutcome, ...], int, bool]:
    outcomes = tuple(
        grade_answer(selected, correct)
        for selected, correct in zip(answers, answer_key, strict=True)
    )
    score = outcomes.count("correct")
    return outcomes, score, "inconclusive" not in outcomes
