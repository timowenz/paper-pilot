import re
import language_tool_python
from langdetect import detect, LangDetectException

_tools: dict[str, language_tool_python.LanguageTool] = {}

IGNORED_RULES = {
    "WHITESPACE_RULE",
    "PUNCTUATION_PARAGRAPH_END",
    "MORFOLOGIK_RULE_DE_DE",
    "GERMAN_SPELLER_RULE",
    "GERMAN_WORD_REPEAT_BEGINNING_RULE",
    "GERMAN_WORD_REPEAT_RULE",
    "WIEDERHOLUNG_VON_SATZTEILEN",
    "DE_VERB_VORSATZ_DAR",
    "DARZUSTELLEN",
    "DOPPELPUNKT_GROSS",
    "COMMA_PARENTHESIS_WHITESPACE",
}

IGNORED_MESSAGE_FRAGMENTS = [
    "hinter der Klammer",
]

_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s", re.MULTILINE)


def _get_tool(lang: str) -> language_tool_python.LanguageTool:
    if lang not in _tools:
        _tools[lang] = language_tool_python.LanguageTool(lang)
    return _tools[lang]


def _detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "de-DE" if lang == "de" else "en-US"
    except LangDetectException:
        return "de-DE"


def _is_whitelisted(
    text: str, offset: int, length: int, whitelist: set[str]
) -> bool:
    error_word = text[offset : offset + length].strip()
    return (
        error_word in whitelist
        or any(w in error_word for w in whitelist if len(w) >= 4)
        or bool(re.match(r"^[A-Z]{2,}$", error_word))
        or bool(re.match(r"^[A-Z][a-z]+[A-Z]", error_word))
        or bool(re.match(r"^[a-z]+[A-Z]", error_word))
        or bool(re.match(r"^\w+\.\w+", error_word))
        or bool(re.match(r"^\[?\d+\]?$", error_word))
        or bool(re.match(r"^\d+:\w+", error_word))
    )


def _is_in_list_item(text: str, offset: int) -> bool:
    line_start = text.rfind("\n", 0, offset) + 1
    return bool(_LIST_ITEM_RE.match(text[line_start:]))


def _is_false_positive(text: str, m, whitelist: set[str]) -> bool:
    if m.rule_id in IGNORED_RULES:
        return True
    if _is_whitelisted(text, m.offset, m.error_length, whitelist):
        return True
    if any(frag in m.message for frag in IGNORED_MESSAGE_FRAGMENTS):
        return True
    if m.rule_id == "DE_CASE" and _is_in_list_item(text, m.offset):
        return True
    return False


def check_chunk(chunk: dict, whitelist: set[str]) -> dict:
    lang = _detect_language(chunk["text"])
    tool = _get_tool(lang)
    matches = tool.check(chunk["text"])

    errors = [
        {
            "message": m.message,
            "context": m.context,
            "offset": m.offset,
            "length": m.error_length,
            "replacements": m.replacements[:3],
            "rule_id": m.rule_id,
            "word": chunk["text"][m.offset : m.offset + m.error_length],
        }
        for m in matches
        if not _is_false_positive(chunk["text"], m, whitelist)
    ]

    return {
        "section": chunk["section"],
        "heading_level": chunk["heading_level"],
        "language_detected": lang,
        "error_count": len(errors),
        "errors": errors,
    }


def check_all_chunks(chunks: list[dict], whitelist: set[str]) -> list[dict]:
    results = [check_chunk(c, whitelist) for c in chunks]
    return [r for r in results if r["error_count"] > 0]
