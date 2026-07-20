from __future__ import annotations

import json
import textwrap
from io import BytesIO

try:
    from backend.app.models.schemas import ScanApiResponse
except ModuleNotFoundError:
    from app.models.schemas import ScanApiResponse


def build_markdown_report(scan: ScanApiResponse) -> str:
    lines = [
        f"# Scan Report: {scan.repo_name}",
        "",
        f"- Repository: {scan.repo}",
        f"- Status: {scan.status}",
        f"- Analysis mode: {scan.analysis_mode}",
        f"- Findings: {scan.summary.total}",
        f"- Critical: {scan.summary.critical}",
        f"- High: {scan.summary.high}",
        f"- Medium: {scan.summary.medium}",
        f"- Low: {scan.summary.low}",
        "",
        "## Repo Summary",
        "",
        scan.repo_analysis.overview_summary or "No repo summary available.",
        "",
        "## Top 3 Priorities",
        "",
    ]
    priorities = scan.repo_analysis.top_priorities or ["No urgent remediation priorities were generated."]
    lines.extend([f"- {priority}" for priority in priorities])
    lines.extend(["", "## Findings", ""])

    if not scan.vulnerabilities:
        lines.append("No major findings were surfaced for this repository.")
    else:
        for finding in scan.vulnerabilities:
            lines.extend(
                [
                    f"### {finding.title}",
                    "",
                    f"- Severity: {finding.severity}",
                    f"- Tech context: {finding.tech_context or 'Application Layer'}",
                    f"- Tool: {finding.tool}",
                    f"- File: {finding.file}:{finding.line}",
                    f"- CVSS: {finding.cvss_score}",
                    f"- Exploitability: {round(finding.exploitability_score * 100)}%",
                    f"- Review status: {finding.review_status}",
                    "",
                    f"**What happened**: {finding.what_happened}",
                    "",
                    f"**Why it matters**: {finding.why_it_matters}",
                    "",
                    f"**How to fix**: {finding.how_to_fix}",
                    "",
                ]
            )
    return "\n".join(lines)


def build_json_report(scan: ScanApiResponse) -> str:
    return json.dumps(scan.model_dump(mode="json"), indent=2)


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 48
RIGHT_MARGIN = 48
TOP_MARGIN = 56
BOTTOM_MARGIN = 52
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_lines(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    return textwrap.wrap(text, width=max(width, 24), break_long_words=False, break_on_hyphens=False) or [text]


def _paragraph_lines(label: str, text: str, width: int) -> list[str]:
    wrapped = _text_lines(text, width)
    first, *rest = wrapped
    lines = [f"{label}: {first}".strip()]
    lines.extend(rest)
    return lines


def _severity_tone(severity: str) -> tuple[float, float, float]:
    tones = {
        "Critical": (0.78, 0.15, 0.24),
        "High": (0.93, 0.43, 0.18),
        "Medium": (0.93, 0.67, 0.12),
        "Low": (0.11, 0.68, 0.48),
    }
    return tones.get(severity, (0.36, 0.32, 0.74))


def _append_text(commands: list[str], x: float, y: float, text: str, font: str = "F1", size: int = 11) -> None:
    commands.append(f"BT /{font} {size} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({_escape_pdf_text(text)}) Tj ET")


def _append_rule(commands: list[str], x: float, y: float, width: float, color: tuple[float, float, float]) -> None:
    commands.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG 1 w {x:.2f} {y:.2f} m {x + width:.2f} {y:.2f} l S")


def _append_fill(commands: list[str], x: float, y: float, width: float, height: float, color: tuple[float, float, float]) -> None:
    commands.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f")


def build_pdf_report(scan: ScanApiResponse) -> bytes:
    pages: list[list[str]] = [[]]
    y = PAGE_HEIGHT - TOP_MARGIN

    def current_page() -> list[str]:
        return pages[-1]

    def new_page() -> None:
        nonlocal y
        pages.append([])
        y = PAGE_HEIGHT - TOP_MARGIN

    def ensure_space(height: float) -> None:
        nonlocal y
        if y - height < BOTTOM_MARGIN:
            new_page()

    def draw_title(text: str) -> None:
        nonlocal y
        ensure_space(34)
        _append_text(current_page(), LEFT_MARGIN, y, text, font="F2", size=24)
        y -= 32

    def draw_subtitle(text: str) -> None:
        nonlocal y
        ensure_space(18)
        _append_text(current_page(), LEFT_MARGIN, y, text, font="F1", size=11)
        y -= 18

    def draw_section(title: str) -> None:
        nonlocal y
        ensure_space(26)
        _append_text(current_page(), LEFT_MARGIN, y, title, font="F2", size=14)
        _append_rule(current_page(), LEFT_MARGIN, y - 8, CONTENT_WIDTH, (0.91, 0.44, 0.62))
        y -= 24

    def draw_paragraph(label: str, text: str, width: int = 88) -> None:
        nonlocal y
        lines = _paragraph_lines(label, text, width)
        block_height = len(lines) * 14 + 8
        ensure_space(block_height)
        for line in lines:
            _append_text(current_page(), LEFT_MARGIN, y, line, font="F1", size=11)
            y -= 14
        y -= 8

    def draw_bullets(items: list[str], width: int = 84) -> None:
        nonlocal y
        if not items:
            return
        for item in items:
            wrapped = _text_lines(item, width)
            ensure_space(len(wrapped) * 14 + 4)
            first, *rest = wrapped
            _append_text(current_page(), LEFT_MARGIN, y, f"• {first}", font="F1", size=11)
            y -= 14
            for line in rest:
                _append_text(current_page(), LEFT_MARGIN + 12, y, line, font="F1", size=11)
                y -= 14
            y -= 4

    def draw_summary_card(lines: list[str]) -> None:
        nonlocal y
        height = len(lines) * 15 + 22
        ensure_space(height)
        _append_fill(current_page(), LEFT_MARGIN, y - height + 8, CONTENT_WIDTH, height, (0.97, 0.97, 0.99))
        local_y = y - 12
        for line in lines:
            _append_text(current_page(), LEFT_MARGIN + 14, local_y, line, font="F1", size=11)
            local_y -= 15
        y -= height + 8

    def draw_finding_card(index: int, total: int, finding) -> None:
        nonlocal y
        tone = _severity_tone(str(finding.severity))
        lines = [
            (f"Finding {index} of {total}", "F2", 13),
            (f"{finding.severity} | {finding.title}", "F2", 16),
            (f"{finding.tech_context or 'Application Layer'} | {finding.tool} | {finding.file}:{finding.line}", "F1", 11),
            (f"CVSS {finding.cvss_score} | Exploitability {round((finding.exploitability_score or 0) * 100)}% | Review {finding.review_status}", "F1", 11),
            *[(line, "F1", 11) for line in _paragraph_lines("What happened", finding.what_happened, 82)],
            *[(line, "F1", 11) for line in _paragraph_lines("Why it matters", finding.why_it_matters, 82)],
            *[(line, "F1", 11) for line in _paragraph_lines("How to fix", finding.how_to_fix, 82)],
        ]
        if finding.example_fix:
            lines.extend((line, "F1", 10) for line in _paragraph_lines("Example fix", finding.example_fix, 82))
        card_height = 28 + sum(16 if size >= 13 else 14 for _, _, size in lines) + 14
        ensure_space(card_height)
        _append_fill(current_page(), LEFT_MARGIN, y - card_height + 8, CONTENT_WIDTH, card_height, (0.99, 0.99, 1.0))
        _append_fill(current_page(), LEFT_MARGIN, y - 6, CONTENT_WIDTH, 4, tone)
        local_y = y - 24
        for text, font, size in lines:
            _append_text(current_page(), LEFT_MARGIN + 14, local_y, text, font=font, size=size)
            local_y -= 16 if size >= 13 else 14
        y -= card_height + 12

    draw_title(f"Scan Report: {scan.repo_name}")
    draw_subtitle(f"Repository: {scan.repo}")
    draw_subtitle(f"Status: {scan.status.title()} | Analysis mode: {scan.analysis_mode} | Generated for sharing")
    draw_subtitle(f"Scanned at: {scan.scanned_at.strftime('%Y-%m-%d %H:%M UTC')}")
    y -= 8

    draw_summary_card(
        [
            f"Summary: {scan.summary.total} findings | Critical {scan.summary.critical} | High {scan.summary.high} | Medium {scan.summary.medium} | Low {scan.summary.low}",
            f"Risk assessment: {scan.risk_assessment}",
            f"Repo overview: {scan.repo_analysis.overview_summary or 'No repo summary available.'}",
        ]
    )

    draw_section("Top priorities")
    draw_bullets(scan.repo_analysis.top_priorities or ["No urgent remediation priorities were generated."])
    y -= 4

    draw_section("Findings")
    if not scan.vulnerabilities:
        draw_paragraph("Status", "No major findings were surfaced for this repository.")
    else:
        for index, finding in enumerate(scan.vulnerabilities, start=1):
            draw_finding_card(index, len(scan.vulnerabilities), finding)

    contents = ["\n".join(page).encode("latin-1", errors="replace") for page in pages]
    page_count = len(contents)
    font_object_ids = {"F1": 3 + (page_count * 2), "F2": 4 + (page_count * 2)}

    objects: list[bytes] = [b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"]
    page_object_ids = [3 + index for index in range(page_count)]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects.append(f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {page_count} >> endobj\n".encode("latin-1"))

    content_object_start = 3 + page_count
    for index, content in enumerate(contents):
        page_object_id = page_object_ids[index]
        content_object_id = content_object_start + index
        objects.append(
            (
                f"{page_object_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Contents {content_object_id} 0 R /Resources << /Font << /F1 {font_object_ids['F1']} 0 R /F2 {font_object_ids['F2']} 0 R >> >> >> endobj\n"
            ).encode("latin-1")
        )
    for index, content in enumerate(contents):
        content_object_id = content_object_start + index
        objects.append(
            f"{content_object_id} 0 obj << /Length {len(content)} >> stream\n".encode("latin-1")
            + content
            + b"\nendstream endobj\n"
        )

    objects.append(f"{font_object_ids['F1']} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n".encode("latin-1"))
    objects.append(f"{font_object_ids['F2']} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n".encode("latin-1"))

    stream = BytesIO()
    stream.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(stream.tell())
        stream.write(obj)
    xref_start = stream.tell()
    stream.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    stream.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        stream.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    stream.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("latin-1"))
    return stream.getvalue()
