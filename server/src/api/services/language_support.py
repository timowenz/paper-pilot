"""Map langdetect output to LanguageTool locales and document language hints for the LLM."""

from __future__ import annotations

import logging

from langdetect import LangDetectException, detect, detect_langs

logger = logging.getLogger(__name__)

# langdetect ISO 639-1 → LanguageTool language codes (see https://languagetool.org/languages/)
_ISO_TO_LT: dict[str, str] = {
    "ar": "ar",
    "bg": "bg-BG",
    "bn": "bn-BD",
    "ca": "ca-ES",
    "cs": "cs-CZ",
    "da": "da-DK",
    "de": "de-DE",
    "el": "el-GR",
    "en": "en-US",
    "eo": "eo",
    "es": "es",
    "et": "et-EE",
    "fa": "fa",
    "fr": "fr",
    "ga": "ga-IE",
    "gl": "gl-ES",
    "gu": "gu-IN",
    "he": "he",
    "hi": "hi",
    "hr": "hr-HR",
    "id": "id",
    "is": "is-IS",
    "it": "it",
    "ja": "ja",
    "km": "km",
    "kn": "kn-IN",
    "lt": "lt-LT",
    "lv": "lv-LV",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "mt": "mt-MT",
    "nb": "no",
    "nl": "nl",
    "nn": "no",
    "no": "no",
    "pa": "pa-IN",
    "pl": "pl",
    "pt": "pt-PT",
    "ro": "ro-RO",
    "ru": "ru-RU",
    "sk": "sk-SK",
    "sl": "sl-SI",
    "sr": "sr-BA",
    "sv": "sv",
    "ta": "ta-IN",
    "te": "te-IN",
    "tl": "tl-PH",
    "tr": "tr",
    "uk": "uk-UA",
    "ur": "ur",
    "vi": "vi",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
}

# ISO 639-1 → English name for LLM instructions
_ISO_TO_ENGLISH_NAME: dict[str, str] = {
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "eo": "Esperanto",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fr": "French",
    "ga": "Irish",
    "gl": "Galician",
    "gu": "Gujarati",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "km": "Khmer",
    "kn": "Kannada",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "mt": "Maltese",
    "nb": "Norwegian",
    "nl": "Dutch",
    "nn": "Norwegian",
    "no": "Norwegian",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "sv": "Swedish",
    "ta": "Tamil",
    "te": "Telugu",
    "tl": "Tagalog",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese (Traditional)",
}

_MIN_CHARS_FOR_CHUNK_DETECT = 120
_MAX_SAMPLE = 15000


def iso639_to_languagetool(iso: str) -> str:
    """Normalize langdetect code (may be zh-cn style) and map to LanguageTool."""
    key = iso.lower().replace("_", "-")
    if key in _ISO_TO_LT:
        return _ISO_TO_LT[key]
    if key.startswith("zh"):
        return "zh-CN" if "tw" not in key and "hk" not in key else "zh-TW"
    return "en-US"


def detect_iso639(text: str) -> str:
    """Return ISO 639-1 language code or 'en' on failure."""
    t = text.strip()
    if len(t) < 20:
        return "en"
    try:
        return detect(t)
    except LangDetectException:
        return "en"


def document_language_iso(chunks: list[dict]) -> str:
    """Dominant language from concatenated chunk text (for fallbacks + LLM hint)."""
    parts = [c.get("text", "") for c in chunks[:40]]
    blob = "\n\n".join(parts)[:_MAX_SAMPLE]
    if len(blob.strip()) < 40:
        return "en"
    try:
        ranked = detect_langs(blob)
        if ranked:
            return ranked[0].lang
    except LangDetectException:
        pass
    return detect_iso639(blob)


def document_language_for_llm(chunks: list[dict]) -> tuple[str, str]:
    """(iso_code, english_name) for coherence system/user prompts."""
    iso = document_language_iso(chunks)
    name = _ISO_TO_ENGLISH_NAME.get(iso.lower(), iso.upper())
    return iso, name


def lt_language_for_chunk(text: str, document_fallback_lt: str) -> str:
    """LanguageTool locale: per-chunk detect if enough text, else document default."""
    t = text.strip()
    if len(t) < _MIN_CHARS_FOR_CHUNK_DETECT:
        return document_fallback_lt
    iso = detect_iso639(t)
    return iso639_to_languagetool(iso)
