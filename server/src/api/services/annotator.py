from __future__ import annotations

import re
import fitz


def _find_heading_page(doc: fitz.Document, title: str) -> int | None:
    """Try several strategies to locate a section heading in the PDF."""
    for page_num in range(len(doc)):
        if doc[page_num].search_for(title):
            return page_num

    short = re.sub(r"\s*\(.*?\)\s*$", "", title).strip()
    if short != title:
        for page_num in range(len(doc)):
            if doc[page_num].search_for(short):
                return page_num

    words = title.split()
    if len(words) >= 3:
        fragment = " ".join(words[:3])
        for page_num in range(len(doc)):
            if doc[page_num].search_for(fragment):
                return page_num

    return None


def _build_section_page_ranges(
    doc: fitz.Document, chunk_results: list[dict]
) -> dict[str, tuple[int, int]]:
    """Map each section title to (start_page, end_page_exclusive)."""
    headings: list[tuple[str, int]] = []
    seen: set[str] = set()

    for result in chunk_results:
        title = result["section"]
        if title in seen:
            continue
        seen.add(title)
        page = _find_heading_page(doc, title)
        headings.append((title, page if page is not None else 0))

    headings.sort(key=lambda h: h[1])

    ranges: dict[str, tuple[int, int]] = {}
    for i, (title, start) in enumerate(headings):
        if i + 1 < len(headings):
            end = headings[i + 1][1] + 1
        else:
            end = len(doc)
        ranges[title] = (start, end)

    return ranges


_CONTEXT_WORD_WINDOW = 3


def _extract_context_phrase(text: str, offset: int, length: int) -> str | None:
    """Pull a multi-word phrase around the error for disambiguation."""
    before = text[max(0, offset - 80) : offset]
    after = text[offset + length : offset + length + 80]

    words_before = re.findall(r"\S+", before)[-_CONTEXT_WORD_WINDOW:]
    words_after = re.findall(r"\S+", after)[:_CONTEXT_WORD_WINDOW]
    error_word = text[offset : offset + length]

    phrase = " ".join(words_before + [error_word] + words_after)
    if len(phrase) > len(error_word) + 4:
        return phrase
    return None


def locate_errors_in_pdf(
    pdf_bytes: bytes, chunk_results: list[dict], chunks: list[dict]
) -> list[dict]:
    """Enrich spellcheck errors with page number and rectangle coordinates."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    section_ranges = _build_section_page_ranges(doc, chunk_results)
    chunk_text_map = {c["section"]: c["text"] for c in chunks}

    used_locations: set[tuple[int, tuple[float, float, float, float]]] = set()
    located: list[dict] = []

    def _search_pages(
        word: str,
        page_range: range,
        phrase: str | None,
        chunk_text: str,
    ) -> tuple[int | None, fitz.Rect | None]:
        """Search *page_range* for *word*, return (page, rect) or (None, None)."""
        for page_num in page_range:
            page = doc[page_num]

            if phrase:
                ctx_rects = page.search_for(phrase)
                if ctx_rects:
                    for r in page.search_for(word):
                        if (
                            r.intersects(ctx_rects[0])
                            or abs(r.y0 - ctx_rects[0].y0) < 2
                        ):
                            key = (page_num, tuple(r))
                            if key not in used_locations:
                                return page_num, r

            for r in page.search_for(word):
                key = (page_num, tuple(r))
                if key not in used_locations:
                    return page_num, r

        return None, None

    for result in chunk_results:
        section = result["section"]
        start_page, end_page = section_ranges.get(section, (0, len(doc)))
        chunk_text = chunk_text_map.get(section, "")

        for error in result["errors"]:
            word = error["word"]
            entry = {
                **error,
                "section": section,
                "page": None,
                "rect": None,
            }

            phrase = _extract_context_phrase(
                chunk_text,
                error["offset"],
                error["length"],
            )

            best_page, best_rect = _search_pages(
                word,
                range(start_page, end_page),
                phrase,
                chunk_text,
            )

            if best_rect is None:
                best_page, best_rect = _search_pages(
                    word,
                    range(len(doc)),
                    phrase,
                    chunk_text,
                )

            if best_rect is not None and best_page is not None:
                entry["page"] = best_page
                entry["rect"] = best_rect
                used_locations.add((best_page, tuple(best_rect)))

            located.append(entry)

    doc.close()
    return located


_BLUE = (0.18, 0.4, 0.9)
_SEVERITY_LABELS = {"error": "FEHLER", "warning": "WARNUNG", "info": "HINWEIS"}

_PAGE_W = 595.28  # A4
_PAGE_H = 841.89
_MARGIN_TOP = 60
_MARGIN_BOTTOM = 60
_MARGIN_LEFT = 60
_MARGIN_RIGHT = 60
_FONT = "helv"
_FONT_BOLD = "hebo"


def _sanitize(text: str) -> str:
    """Replace characters unsupported by the built-in Helvetica font."""
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u201e", '"')
        .replace("\u2026", "...")
    )


class _PageWriter:
    """Helper that manages page breaks and cursor position."""

    def __init__(self, doc: fitz.Document) -> None:
        self._doc = doc
        self._page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        self._y = _MARGIN_TOP

    def _ensure_space(self, needed: float) -> None:
        if self._y + needed > _PAGE_H - _MARGIN_BOTTOM:
            self._page = self._doc.new_page(width=_PAGE_W, height=_PAGE_H)
            self._y = _MARGIN_TOP

    def skip(self, pts: float = 8) -> None:
        self._y += pts

    def line(self) -> None:
        """Draw a thin horizontal rule."""
        self._ensure_space(10)
        self._page.draw_line(
            fitz.Point(_MARGIN_LEFT, self._y + 4),
            fitz.Point(_PAGE_W - _MARGIN_RIGHT, self._y + 4),
            color=(0.7, 0.7, 0.7),
            width=0.5,
        )
        self._y += 10

    def text(
        self,
        txt: str,
        fontsize: float = 10,
        bold: bool = False,
        indent: float = 0,
        color: tuple[float, float, float] = (0, 0, 0),
    ) -> None:
        if not txt:
            return
        fontname = _FONT_BOLD if bold else _FONT
        safe = _sanitize(txt)
        left = _MARGIN_LEFT + indent
        right = _PAGE_W - _MARGIN_RIGHT
        tb = fitz.Rect(left, self._y, right, _PAGE_H - _MARGIN_BOTTOM)
        rc = self._page.insert_textbox(
            tb,
            safe,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            align=fitz.TEXT_ALIGN_LEFT,
        )
        used = tb.height - rc if rc >= 0 else fontsize * 1.5
        self._y += used + 2
        if self._y > _PAGE_H - _MARGIN_BOTTOM - fontsize:
            self._page = self._doc.new_page(width=_PAGE_W, height=_PAGE_H)
            self._y = _MARGIN_TOP


def _write_summary_pages(
    doc: fitz.Document,
    located_errors: list[dict],
    coherence_findings: list[dict],
    evaluation: dict,
) -> None:
    """Append a concise evaluation summary at the end of the document.

    Instead of listing every note again, this gives a high-level overview:
    statistics and LLM strengths/weaknesses.
    """
    w = _PageWriter(doc)

    grammar_count = len(located_errors)
    coherence_count = len(coherence_findings)

    errors = sum(1 for f in coherence_findings if f.get("severity") == "error")
    warnings = sum(1 for f in coherence_findings if f.get("severity") == "warning")
    infos = coherence_count - errors - warnings

    w.text("Paper Pilot  -  Analysis Report", fontsize=20, bold=True)
    w.skip(6)
    w.line()
    w.skip(8)

    w.text("Statistics", fontsize=14, bold=True)
    w.skip(4)
    w.text(f"Grammar & spelling issues:   {grammar_count}", fontsize=11)
    w.text(
        f"Coherence findings:          {coherence_count}"
        + (f"  ({errors} error, {warnings} warning, {infos} info)" if coherence_count else ""),
        fontsize=11,
    )
    w.skip(4)
    w.text(
        "All issues are annotated as sticky notes in the PDF at their "
        "respective positions. Refer to the annotations for details.",
        fontsize=9.5,
        color=(0.35, 0.35, 0.35),
    )
    w.skip(6)
    w.line()
    w.skip(8)

    strengths = evaluation.get("strengths", [])
    weaknesses = evaluation.get("weaknesses", [])

    if strengths:
        w.text("Strengths", fontsize=14, bold=True, color=(0.1, 0.55, 0.2))
        w.skip(4)
        for s in strengths:
            w.text(f"+  {s}", fontsize=10.5, indent=10)
            w.skip(2)
        w.skip(6)

    if weaknesses:
        w.text("Areas for Improvement", fontsize=14, bold=True, color=(0.8, 0.1, 0.1))
        w.skip(4)
        for wk in weaknesses:
            w.text(f"-  {wk}", fontsize=10.5, indent=10)
            w.skip(2)
        w.skip(6)

    if not strengths and not weaknesses:
        if grammar_count == 0 and coherence_count == 0:
            w.text(
                "No issues found. The document has correct grammar and a "
                "coherent structure.",
                fontsize=11,
            )
        else:
            w.text(
                "See the sticky-note annotations throughout the document "
                "for detailed feedback on each issue.",
                fontsize=11,
            )


def annotate_pdf(
    pdf_bytes: bytes,
    located_errors: list[dict],
    coherence_findings: list[dict] | None = None,
    evaluation: dict | None = None,
) -> bytes:
    """Annotate the PDF with grammar errors and coherence findings.

    Grammar errors: yellow highlight + yellow "Note" sticky note.
    Coherence findings: blue "Comment" sticky note at the quote position.
    A high-level evaluation summary is appended at the end.

    Returns the annotated PDF as bytes (nothing is written to disk).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for err in located_errors:
        if err["page"] is None or err["rect"] is None:
            continue

        page = doc[err["page"]]
        rect = err["rect"]

        highlight = page.add_highlight_annot(rect)
        highlight.update()

        parts = [err["message"]]
        if err.get("word"):
            parts.insert(0, f"Wort: «{err['word']}»")
        if err.get("replacements"):
            parts.append(f"Vorschläge: {', '.join(err['replacements'])}")
        note_text = "\n".join(parts)

        note_point = fitz.Point(rect.x1 + 2, rect.y0)
        note = page.add_text_annot(note_point, note_text)
        note.set_info(
            title=f"[{err.get('rule_id', '')}] {err.get('section', '')}",
        )
        note.update()

    section_ranges = _build_section_page_ranges(doc, [{"section": f["section"]} for f in (coherence_findings or [])])

    for finding in coherence_findings or []:
        section = finding["section"]
        severity = finding.get("severity", "info")
        label = _SEVERITY_LABELS.get(severity, "HINWEIS")
        quote = finding.get("quote", "")
        start_page, end_page = section_ranges.get(section, (0, len(doc)))

        point = None

        if quote:
            for pn in range(start_page, end_page):
                rects = doc[pn].search_for(quote)
                if rects:
                    point = fitz.Point(rects[0].x1 + 2, rects[0].y0)
                    page_num = pn
                    break

            if point is None:
                words = quote.split()
                if len(words) > 4:
                    fragment = " ".join(words[:5])
                    for pn in range(start_page, end_page):
                        rects = doc[pn].search_for(fragment)
                        if rects:
                            point = fitz.Point(rects[0].x1 + 2, rects[0].y0)
                            page_num = pn
                            break

        if point is None:
            page_num = _find_heading_page(doc, section)
            if page_num is None:
                page_num = start_page
            rects = doc[page_num].search_for(section)
            point = fitz.Point(rects[0].x1 + 2, rects[0].y0) if rects else fitz.Point(72, 72)

        parts = [f"[{label}] {finding['issue']}"]
        if finding.get("suggestion"):
            parts.append(f"Suggestion: {finding['suggestion']}")
        note_text = "\n".join(parts)

        page = doc[page_num]
        note = page.add_text_annot(point, note_text, icon="Comment")
        note.set_colors(stroke=_BLUE)
        note.set_info(title=f"Coherence - {section}")
        note.update()

    _write_summary_pages(doc, located_errors, coherence_findings or [], evaluation or {})

    result = doc.tobytes()
    doc.close()
    return result
