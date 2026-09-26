from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from scanner import ScanError, ScanResult, scan_image


@dataclass(frozen=True)
class PageScan:
    source: str
    page: int
    image: bytes
    result: ScanResult | None
    error: str | None


def render_pdf_pages(data: bytes) -> list[bytes]:
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ScanError(f"The PDF could not be opened: {exc}") from exc

    pages: list[bytes] = []
    try:
        for page in document:
            scale = max(2.0, 1600 / page.rect.height)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            pages.append(pixmap.tobytes("png"))
    finally:
        document.close()
    return pages


def scan_pdf(data: bytes, source: str) -> list[PageScan]:
    scans: list[PageScan] = []
    for page_number, image in enumerate(render_pdf_pages(data), start=1):
        try:
            scans.append(PageScan(source, page_number, image, scan_image(image), None))
        except ScanError as exc:
            scans.append(PageScan(source, page_number, image, None, str(exc)))
    return scans
