from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

PAGE_WIDTH = 1131
PAGE_HEIGHT = 1600
MARKER_TARGETS = np.float32(
    [[63, 65], [1066, 65], [63, 1537], [1066, 1537]]
)

ANSWER_X = (
    (154, 181.5, 208, 235.5, 262),
    (343.5, 370, 397.5, 424, 451.5),
    (532, 559, 586, 613, 640),
    (721, 748, 774.5, 802, 828.5),
    (910, 936, 964, 990, 1018),
)
ANSWER_Y = (1024.5, 1064.5, 1104, 1144, 1184, 1224, 1264, 1304, 1344, 1384)
ID_X = (203, 257, 311, 365, 418.5, 472.5, 526.5, 580)
CRN_X = (737, 791, 845, 899, 952.5)
DIGIT_Y = (496, 526, 556, 586.5, 617, 647.5, 678, 708, 738, 768)
OPTIONS = "ABCDE"


class ScanError(ValueError):
    pass


@dataclass(frozen=True)
class Mark:
    value: str | None
    confidence: float
    status: str


@dataclass(frozen=True)
class ScanResult:
    student_id: str | None
    crn: str | None
    answers: tuple[str | None, ...]
    statuses: tuple[str, ...]
    warnings: tuple[str, ...]


def decode_image(data: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ScanError("The page could not be decoded as an image.")
    return image


def _find_registration_markers(gray: np.ndarray) -> np.ndarray:
    height, width = gray.shape
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, float]] = []
    min_area = height * width * 0.00025
    max_area = height * width * 0.003

    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        aspect = box_width / box_height
        fill = area / max(box_width * box_height, 1)
        if min_area <= area <= max_area and 0.72 <= aspect <= 1.28 and fill >= 0.72:
            candidates.append((x + box_width / 2, y + box_height / 2))

    if len(candidates) < 4:
        raise ScanError("Four registration squares were not found. Scan the entire page.")

    corners = np.float32([[0, 0], [width, 0], [0, height], [width, height]])
    points = np.float32(candidates)
    selected = []
    for corner in corners:
        distances = np.linalg.norm(points - corner, axis=1)
        selected.append(points[int(np.argmin(distances))])

    if len({tuple(point) for point in selected}) != 4:
        raise ScanError("The registration squares could not be identified reliably.")
    return np.float32(selected)


def align_page(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    markers = _find_registration_markers(gray)
    transform = cv2.getPerspectiveTransform(markers, MARKER_TARGETS)
    return cv2.warpPerspective(gray, transform, (PAGE_WIDTH, PAGE_HEIGHT), borderValue=255)


def _darkness(gray: np.ndarray, x: float, y: float, radius: int = 7) -> float:
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.circle(mask, (round(x), round(y)), radius, 255, -1)
    pixels = gray[mask == 255]
    return float(np.mean(255 - pixels) / 255)


def _read_mark(scores: list[float], labels: str, minimum: float = 0.28) -> Mark:
    order = np.argsort(scores)[::-1]
    best_index = int(order[0])
    best = scores[best_index]
    second = scores[int(order[1])]
    confidence = best - second
    if best < minimum:
        return Mark(None, confidence, "blank")
    if confidence < 0.12:
        return Mark(None, confidence, "ambiguous")
    return Mark(labels[best_index], confidence, "ok")


def _read_digits(gray: np.ndarray, x_positions: tuple[float, ...]) -> str | None:
    digits: list[str] = []
    for x in x_positions:
        scores = [_darkness(gray, x, y, radius=7) for y in DIGIT_Y]
        mark = _read_mark(scores, "0123456789", minimum=0.32)
        if mark.value is None:
            return None
        digits.append(mark.value)
    return "".join(digits)


def scan_aligned_page(gray: np.ndarray) -> ScanResult:
    id_digits = _read_digits(gray, ID_X)
    crn = _read_digits(gray, CRN_X)
    answers: list[str | None] = []
    statuses: list[str] = []

    for group in range(5):
        for row in range(10):
            scores = [_darkness(gray, x, ANSWER_Y[row]) for x in ANSWER_X[group]]
            mark = _read_mark(scores, OPTIONS)
            answers.append(mark.value)
            statuses.append(mark.status)

    warnings: list[str] = []
    if id_digits is None:
        warnings.append("Student ID is incomplete or ambiguous.")
    if crn is None:
        warnings.append("CRN is incomplete or ambiguous.")
    problem_answers = [index + 1 for index, status in enumerate(statuses) if status != "ok"]
    if problem_answers:
        warnings.append("Review blank or ambiguous questions: " + ", ".join(map(str, problem_answers)))

    return ScanResult(
        student_id=f"H{id_digits}" if id_digits is not None else None,
        crn=crn,
        answers=tuple(answers),
        statuses=tuple(statuses),
        warnings=tuple(warnings),
    )


def scan_image(data: bytes) -> ScanResult:
    return scan_aligned_page(align_page(decode_image(data)))


def scan_image_file(path: str | Path) -> ScanResult:
    return scan_image(Path(path).read_bytes())
