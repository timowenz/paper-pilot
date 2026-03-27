import logging
import re

import language_tool_python

from api.services.language_support import (
    document_language_iso,
    iso639_to_languagetool,
    lt_language_for_chunk,
)

logger = logging.getLogger(__name__)

_tools: dict[str, language_tool_python.LanguageTool] = {}

# Rules to ignore for all languages
IGNORED_RULES_COMMON = {
    "WHITESPACE_RULE",
    "PUNCTUATION_PARAGRAPH_END",
    "COMMA_PARENTHESIS_WHITESPACE",
}

# German-only noise rules (LanguageTool de-DE)
IGNORED_RULES_GERMAN = {
    "MORFOLOGIK_RULE_DE_DE",
    "GERMAN_SPELLER_RULE",
    "GERMAN_WORD_REPEAT_BEGINNING_RULE",
    "GERMAN_WORD_REPEAT_RULE",
    "WIEDERHOLUNG_VON_SATZTEILEN",
    "DE_VERB_VORSATZ_DAR",
    "DARZUSTELLEN",
    "DOPPELPUNKT_GROSS",
}

IGNORED_MESSAGE_FRAGMENTS = [
    "hinter der Klammer",
]

_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s", re.MULTILINE)


def _get_tool(lang: str) -> language_tool_python.LanguageTool:
    if lang not in _tools:
        try:
            _tools[lang] = language_tool_python.LanguageTool(lang)
        except Exception as exc:
            logger.warning(
                "LanguageTool init failed for %s (%s); using en-US",
                lang,
                exc,
            )
            if "en-US" not in _tools:
                _tools["en-US"] = language_tool_python.LanguageTool("en-US")
            _tools[lang] = _tools["en-US"]
    return _tools[lang]


def _ignored_rules_for_lt(lt_lang: str) -> set[str]:
    rules = set(IGNORED_RULES_COMMON)
    if lt_lang.startswith("de"):
        rules |= IGNORED_RULES_GERMAN
    return rules


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


def _is_false_positive(
    text: str, m, whitelist: set[str], ignored_rules: set[str], lt_lang: str
) -> bool:
    if m.rule_id in ignored_rules:
        return True
    if _is_whitelisted(text, m.offset, m.error_length, whitelist):
        return True
    if lt_lang.startswith("de") and any(
        frag in m.message for frag in IGNORED_MESSAGE_FRAGMENTS
    ):
        return True
    if lt_lang.startswith("de") and m.rule_id == "DE_CASE" and _is_in_list_item(
        text, m.offset
    ):
        return True
    return False


def check_chunk(
    chunk: dict, whitelist: set[str], document_fallback_lt: str
) -> dict:
    lang = lt_language_for_chunk(chunk["text"], document_fallback_lt)
    tool = _get_tool(lang)
    ignored_rules = _ignored_rules_for_lt(lang)
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
        if not _is_false_positive(chunk["text"], m, whitelist, ignored_rules, lang)
    ]

    return {
        "section": chunk["section"],
        "heading_level": chunk["heading_level"],
        "language_detected": lang,
        "error_count": len(errors),
        "errors": errors,
    }


def check_all_chunks(chunks: list[dict], whitelist: set[str]) -> list[dict]:
    doc_iso = document_language_iso(chunks)
    document_fallback_lt = iso639_to_languagetool(doc_iso)
    results = [check_chunk(c, whitelist, document_fallback_lt) for c in chunks]
    return [r for r in results if r["error_count"] > 0]
