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


def questions_requiring_review(answers: tuple[str | None, ...]) -> tuple[int, ...]:
    return tuple(
        question
        for question, answer in enumerate(answers, start=1)
        if answer is not None and len(answer) > 1
    )


def describe_multiple_selection(selected: str, correct: str) -> str:
    incorrect = tuple(option for option in selected if option != correct)
    if correct not in selected:
        return (
            f"Multiple selection, all incorrect (selected options {', '.join(incorrect)}); "
            f"correct option {correct}."
        )
    label = "option" if len(incorrect) == 1 else "options"
    return (
        f"Multiple selection, correct option {correct} together with "
        f"incorrect {label} {', '.join(incorrect)}."
    )
