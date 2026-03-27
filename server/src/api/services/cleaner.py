import re

_SKIP_PATTERNS = [
    re.compile(r"verzeichnis\b", re.IGNORECASE),
    re.compile(r"\bErklärung\b"),
    re.compile(r"\bSperrvermerk\b"),
    re.compile(r"\bAbstract\b", re.IGNORECASE),
    re.compile(r"\bAbstrakt\b", re.IGNORECASE),
    re.compile(r"^A\.\d+"),
    re.compile(r"\bAnhang\b"),
    re.compile(r"\bDanksagung\b"),
    re.compile(r"\bVorwort\b"),
    re.compile(r"\bGlossar\b"),
]


def is_skippable_section(title: str) -> bool:
    return any(p.search(title) for p in _SKIP_PATTERNS)

_TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9\-/.]*")


def extract_document_terms(raw_markdown: str) -> set[str]:
    """Build a document-specific whitelist from structural cues in raw markdown.

    Only extracts terms from places where the author *explicitly* marked
    something as technical: code spans, code blocks, and hyphenated
    compounds.  Headings and bold/italic are intentionally excluded because
    they contain too many regular-language words (especially German nouns).
    """
    terms: set[str] = set()

    for m in re.finditer(r"`([^`\n]+)`", raw_markdown):
        for tok in _TOKEN_RE.findall(m.group(1)):
            if len(tok) >= 2:
                terms.add(tok)

    for m in re.finditer(r"```[\s\S]*?```", raw_markdown):
        for tok in _TOKEN_RE.findall(m.group(0)):
            if len(tok) >= 2:
                terms.add(tok)

    for m in re.finditer(
        r"(?<!\w)([A-ZÄÖÜa-zäöü]\w+-[A-ZÄÖÜa-zäöü]\w+(?:-\w+)*)", raw_markdown
    ):
        terms.add(m.group(1))

    terms.discard("")
    return terms


def clean_markdown(markdown_text: str) -> str:
    # 1. OCR-Meldungen
    text = re.sub(
        r"=== Document parser messages ===.*?(?=\n#)",
        "",
        markdown_text,
        flags=re.DOTALL,
    )
    # 2. Bild-Platzhalter & Bildunterschriften
    text = re.sub(r"\*\*==>.*?<==\*\*\n?", "", text)
    text = re.sub(r"(Abbildung|Tabelle)\s+[\d\.A-Z]+[:\-–].*?\n", "", text)
    # 3. Markdown-Tabellen
    text = re.sub(r"(\|.*\|\n)+", "", text)
    # 4. ToC-Punkt-Muster
    text = re.sub(r"[\.\s]{5,}", " ", text)
    # 5. Seitenzahlen (arabisch & römisch)
    text = re.sub(r"^\s*[ivxlcIVXLC\d]{1,6}\s*$", "", text, flags=re.MULTILINE)
    # 6. Paginierungs-Artefakte
    text = re.sub(r"Fortsetzung auf der nächste[rn]? Seite\n?", "", text)
    # 7. OCR-Silbentrennungen ("ein-\ngesetzt" → "eingesetzt")
    text = re.sub(
        r"(\w+)-\s*\n\s*(\w)", lambda m: m.group(1) + m.group(2).lower(), text
    )
    # 8. OCR Multi-Space-Artefakte ("Skalierbarkeit   beim" → "Skalierbarkeit beim")
    text = re.sub(r"([a-zäöüßA-ZÄÖÜ\.\,\)\]\d])\s{2,}([a-zäöüß])", r"\1 \2", text)
    # 9. OCR fehlende Punkte vor typischen Satzanfängen reparieren
    text = re.sub(r"([a-zäöüß])\s+(Zur\s)", r"\1. \2", text)
    text = re.sub(r"([a-zäöüß])\s+(Die\s+Abbildung)", r"\1. \2", text)
    text = re.sub(r"([a-zäöüß])\s+(Der\s+[A-ZÄÖÜ][a-z])", r"\1. \2", text)
    text = re.sub(r"([a-zäöüß])\s+(In\s+Abbildung)", r"\1. \2", text)
    # 10. Code-Blöcke entfernen
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`\n]+`", "", text)
    # 11. Property-Listen entfernen (_camelCaseProp_ – Beschreibung)
    text = re.sub(
        r"^\s*[-–]\s+_[a-zA-Z][a-zA-Z0-9_]+_\s*[–-].*$", "", text, flags=re.MULTILINE
    )
    # 12. _italic_ stripping (muss vor *bold* kommen)
    text = re.sub(r"_(.*?)_", r"\1", text)
    # 13. Leerzeichen vor Doppelpunkt in Listen ("Admin :" → "Admin:")
    #     Nur nach Buchstaben, nicht nach Zahlen (1:n bleibt erhalten)
    text = re.sub(r"([A-Za-zäöüÄÖÜ\)])\s+:", r"\1:", text)
    # 14. Bold/Italic (*) entfernen
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    # 15. Strikethrough-OCR-Artefakte
    text = re.sub(r"~~.*?~~", "", text)
    # 16. Mehrfache Leerzeilen
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(cleaned_text: str) -> list[dict]:
    section_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    positions = [
        (m.start(), m.group(1), m.group(2).strip())
        for m in section_pattern.finditer(cleaned_text)
    ]
    chunks = []
    for i, (pos, level, title) in enumerate(positions):
        if is_skippable_section(title):
            continue
        start = pos + len(cleaned_text[pos:].split("\n")[0]) + 1
        end = positions[i + 1][0] if i + 1 < len(positions) else len(cleaned_text)
        body = cleaned_text[start:end].strip()
        if len(body) > 50:
            chunks.append(
                {
                    "section": title,
                    "heading_level": len(level),
                    "text": body,
                }
            )
    return chunks
