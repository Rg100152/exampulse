"""Dependency-free PDF scorecard generator (pure standard library).

Produces a clean, printable A4 report so the project needs no extra pip package
for the "Download PDF Scorecard" feature.
"""

from __future__ import annotations

import textwrap
from typing import Any

PAGE_W, PAGE_H = 595.28, 841.89
NAVY = (0.059, 0.090, 0.157)
BLUE = (0.145, 0.388, 0.922)
GREEN = (0.063, 0.725, 0.506)
RED = (0.937, 0.267, 0.267)
PURPLE = (0.545, 0.361, 0.965)
SLATE = (0.32, 0.41, 0.55)
LIGHT = (0.945, 0.961, 0.98)
WHITE = (1.0, 1.0, 1.0)


def _escape(text: str) -> str:
    cleaned = str(text).encode("latin-1", "replace").decode("latin-1")
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class _Page:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def rect(self, x: float, top: float, w: float, h: float, color) -> None:
        r, g, b = color
        y = PAGE_H - top - h
        self.ops.append(f"{r:.4f} {g:.4f} {b:.4f} rg\n{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")

    def text(self, x: float, top: float, value: str, size: float = 11,
             color=NAVY, bold: bool = False) -> None:
        r, g, b = color
        self.ops.append(
            f"{r:.4f} {g:.4f} {b:.4f} rg\nBT /{'F2' if bold else 'F1'} {size:.1f} Tf "
            f"1 0 0 1 {x:.2f} {PAGE_H - top:.2f} Tm ({_escape(value)}) Tj ET"
        )

    def rule(self, x: float, top: float, w: float, color=LIGHT) -> None:
        self.rect(x, top, w, 0.7, color)

    def stream(self) -> bytes:
        return "\n".join(self.ops).encode("latin-1", "replace")


def _build_pdf(pages: list[_Page]) -> bytes:
    objects: list[str | None] = []
    catalog_id = len(objects) + 1
    objects.append(None)
    pages_id = len(objects) + 1
    objects.append(None)
    font_regular = len(objects) + 1
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold = len(objects) + 1
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    page_ids: list[int] = []
    for page in pages:
        data = page.stream()
        stream_id = len(objects) + 1
        objects.append(f"<< /Length {len(data)} >>\nstream\n{data.decode('latin-1')}\nendstream")
        page_id = len(objects) + 1
        objects.append(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
            f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
            f"/Contents {stream_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = (
        "<< /Type /Pages /Kids [" + " ".join(f"{pid} 0 R" for pid in page_ids)
        + f"] /Count {len(page_ids)} >>"
    )
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode("latin-1", "replace"))
    xref_at = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n".encode()
    )
    return bytes(out)


def _fmt_time(seconds: int) -> str:
    seconds = int(seconds or 0)
    return f"{seconds // 60:02d}m {seconds % 60:02d}s"


def generate_scorecard_pdf(report: dict[str, Any]) -> bytes:
    """Return a printable PDF scorecard for a graded attempt."""
    pages = [_Page()]
    page = pages[0]

    # Header
    page.rect(0, 0, PAGE_W, 96, NAVY)
    page.rect(0, 96, PAGE_W, 4, BLUE)
    page.text(40, 34, "ExamPulse 1000", 24, WHITE, bold=True)
    page.text(40, 60, "POST-EXAM PERFORMANCE SCORECARD", 10, (0.69, 0.78, 0.92), bold=True)
    page.text(455, 34, str(report["code"]), 12, WHITE, bold=True)
    page.text(455, 54, "by Raj Gautam", 9, (0.69, 0.78, 0.92))

    y = 126
    page.text(40, y, str(report["candidate"]), 18, NAVY, bold=True)
    page.text(40, y + 22, f"{report['subject_name']}  |  {report['mode_label']}", 10, SLATE)
    page.text(355, y, f"Submitted: {str(report['submitted_at'])[:16].replace('T', ' ')}", 9, SLATE)
    page.text(355, y + 16, f"Time taken: {_fmt_time(report['time_taken_seconds'])}", 9, SLATE)
    page.rule(40, y + 34, 515)

    # Score hero
    y = 190
    page.rect(40, y, 515, 92, LIGHT)
    page.rect(40, y, 6, 92, GREEN if report["passed"] else RED)
    page.text(60, y + 22, "SCORE", 9, SLATE, bold=True)
    page.text(60, y + 42, f"{report['marks_earned']:g} / {report['max_marks']:g}", 28, NAVY, bold=True)
    page.text(60, y + 72, f"{report['percentage']:g}% of maximum marks", 10, SLATE)
    page.text(245, y + 24, f"Accuracy      {report['accuracy']:g}%", 12, NAVY, bold=True)
    page.text(245, y + 48, f"Correct       {report['correct']}", 11, GREEN, bold=True)
    page.text(245, y + 68, f"Incorrect     {report['wrong']}", 11, RED, bold=True)
    page.text(410, y + 24, f"Unanswered    {report['unanswered']}", 10, SLATE)
    page.text(410, y + 44, f"Negative      -{report['negative_marks']:g}", 10, RED)
    page.text(410, y + 64, f"Verdict       {'PASS' if report['passed'] else 'NEEDS WORK'}", 10,
              GREEN if report["passed"] else RED, bold=True)

    # Topic analysis
    y = 306
    page.text(40, y, "TOPIC-WISE ACCURACY", 12, NAVY, bold=True)
    y += 18
    for topic in report["topics"]:
        if y > 620:
            pages.append(_Page())
            page = pages[-1]
            y = 60
        page.text(40, y, topic["topic"][:52], 9, NAVY)
        page.text(470, y, f"{topic['accuracy']:g}%  ({topic['correct']}/{topic['total']})", 9, SLATE)
        page.rect(40, y + 13, 440, 5, LIGHT)
        page.rect(40, y + 13, max(2, 440 * topic["accuracy"] / 100), 5,
                  GREEN if not topic["weak"] else RED)
        y += 28

    # Question-by-question summary
    if y > 640:
        pages.append(_Page())
        page = pages[-1]
        y = 60
    else:
        y += 10
    page.text(40, y, "QUESTION REVIEW", 12, NAVY, bold=True)
    y += 20
    colors = {"correct": GREEN, "wrong": RED, "unanswered": SLATE}
    for item in report["questions"]:
        if y > 782:
            pages.append(_Page())
            page = pages[-1]
            y = 52
        q = " ".join(item["question"].split())
        for line in textwrap.wrap(f"Q{item['position']:>3}. {q}", width=96)[:2]:
            page.text(40, y, line, 8.5, NAVY)
            y += 11
        answer = str(item["selected_option"] or "-")
        page.text(52, y, f"Your answer: {answer}   |   Correct: {item['correct_option']}",
                  8, colors[item["status"]], bold=True)
        y += 13
        detail = " ".join(item["explanation"].split())
        for line in textwrap.wrap(detail, width=110)[:2]:
            page.text(52, y, line, 7.5, SLATE)
            y += 10
        y += 5

    # Footers
    for number, p in enumerate(pages, start=1):
        p.text(40, 812, "ExamPulse 1000  |  Enterprise Mock Exam & Practice Test Platform", 8, SLATE)
        p.text(520, 812, f"Page {number}/{len(pages)}", 8, SLATE)
    return _build_pdf(pages)
