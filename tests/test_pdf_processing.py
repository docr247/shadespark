from __future__ import annotations

import sys
from unittest.mock import Mock, patch

try:
    import pymupdf  # noqa: F401
except ModuleNotFoundError:
    sys.modules["pymupdf"] = Mock()

import pdf_processing


def test_scan_pdf_retains_rendered_page_image() -> None:
    image = b"\x89PNG\r\n\x1a\nrendered-page"
    result = Mock()
    with (
        patch.object(pdf_processing, "render_pdf_pages", return_value=[image]),
        patch.object(pdf_processing, "scan_image", return_value=result),
    ):
        scans = pdf_processing.scan_pdf(b"pdf", "test.pdf")

    assert len(scans) == 1
    assert scans[0].image == image
    assert scans[0].result is result
