from __future__ import annotations

import cv2
import numpy as np

from scanner import (
    ANSWER_X,
    ANSWER_Y,
    CRN_X,
    DIGIT_Y,
    ID_X,
    MARKER_TARGETS,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    OPTIONS,
    scan_image,
)


def _synthetic_sheet() -> tuple[bytes, str, str, tuple[str, ...]]:
    page = np.full((PAGE_HEIGHT, PAGE_WIDTH, 3), 255, dtype=np.uint8)
    for x, y in MARKER_TARGETS:
        cv2.rectangle(page, (round(x - 16), round(y - 16)), (round(x + 16), round(y + 16)), (0, 0, 0), -1)

    student_digits = "01234567"
    crn = "12345"
    answers = tuple(OPTIONS[index % 5] for index in range(50))
    for x, digit in zip(ID_X, student_digits, strict=True):
        cv2.circle(page, (round(x), round(DIGIT_Y[int(digit)])), 7, (0, 0, 0), -1)
    for x, digit in zip(CRN_X, crn, strict=True):
        cv2.circle(page, (round(x), round(DIGIT_Y[int(digit)])), 7, (0, 0, 0), -1)
    for question, answer in enumerate(answers):
        group, row = divmod(question, 10)
        cv2.circle(page, (round(ANSWER_X[group][OPTIONS.index(answer)]), round(ANSWER_Y[row])), 7, (0, 0, 0), -1)

    source = np.float32([[0, 0], [PAGE_WIDTH, 0], [0, PAGE_HEIGHT], [PAGE_WIDTH, PAGE_HEIGHT]])
    destination = np.float32([[30, 25], [PAGE_WIDTH - 20, 5], [10, PAGE_HEIGHT - 15], [PAGE_WIDTH - 35, PAGE_HEIGHT - 30]])
    transform = cv2.getPerspectiveTransform(source, destination)
    skewed = cv2.warpPerspective(page, transform, (PAGE_WIDTH, PAGE_HEIGHT), borderValue=(255, 255, 255))
    ok, encoded = cv2.imencode(".png", skewed)
    assert ok
    return encoded.tobytes(), f"H{student_digits}", crn, answers


def test_scans_perspective_corrected_sheet() -> None:
    image, student_id, crn, answers = _synthetic_sheet()
    result = scan_image(image)
    assert result.student_id == student_id
    assert result.crn == crn
    assert result.answers == answers
    assert result.warnings == ()
