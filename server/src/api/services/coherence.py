from __future__ import annotations

import json
import os
import logging
import re

import json_repair
from openai import OpenAI

from api.services.language_support import document_language_for_llm

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "openai/gpt-oss-20b:free"
_DEFAULT_MAX_TOKENS = 16384

_SYSTEM_PROMPT = """\
You are an experienced academic editor. You receive sections of a scholarly document \
(thesis, paper, report). Evaluate only:

1. **Structure / narrative flow**: Is there a clear, logical progression? Does each \
section build sensibly on the previous one?
2. **Logical gaps**: Abrupt shifts, missing arguments, or conclusions that do not \
follow from what came before?
3. **Academic tone**: Appropriate precision and formality? Any overly colloquial passages?

The document may be written in **any human language**. The user message states the \
detected primary language — you MUST write **all** human-readable JSON string values \
in **that same language**: every "issue", "suggestion", "strengths", "weaknesses", \
and "overall" entry. Do **not** default to English unless the document is English.

Reply with **only** a JSON object in exactly this shape (keys in English as shown):

```json
{
  "findings": [
    {
      "section": "<exact affected section title from the document>",
      "quote": "<verbatim 5-15 consecutive words from the document at the problem>",
      "issue": "<1-2 sentences, in the document language>",
      "suggestion": "<1-2 sentences, in the document language>",
      "severity": "info | warning | error"
    }
  ],
  "evaluation": {
    "strengths": ["<in the document language>", "..."],
    "weaknesses": ["<in the document language>", "..."],
    "overall": "<2-4 sentences in the document language>"
  }
}
```

The "quote" field MUST be copied **verbatim** from the document so the location can \
be found in the PDF.

If you find no issues, set "findings" to [].

CRITICAL for valid JSON: Inside string values, do not use the ASCII double-quote \
character U+0022 except at the start and end of each JSON string. For inner quotation \
in running text use typographic quotes (e.g. « » or “ ”) or rephrase without quotes.

Reply with the JSON object only — no markdown outside it, no preamble or postscript.\
"""


def _build_user_prompt(chunks: list[dict], doc_iso: str, doc_name: str) -> str:
    header = (
        f'DOCUMENT_PRIMARY_LANGUAGE: ISO 639-1 "{doc_iso}" ({doc_name}).\n'
        f"Write all narrative fields (issue, suggestion, strengths, weaknesses, overall) "
        f"in {doc_name}. The section titles and quote substrings must match the document.\n\n"
    )
    parts: list[str] = []
    for c in chunks:
        level = c["heading_level"]
        prefix = "#" * level
        parts.append(f"{prefix} {c['section']}\n\n{c['text']}")
    return header + "\n\n---\n\n".join(parts)


_EMPTY_EVALUATION: dict = {
    "strengths": [],
    "weaknesses": [],
    "overall": "",
}


_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _strip_fences(text: str) -> str:
    """Remove all markdown code fences wrapping the response."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _lenient_loads(text: str) -> dict | list:
    """json.loads with tolerance for trailing commas."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = _TRAILING_COMMA.sub(r"\1", text)
        return json.loads(cleaned)


def _repair_loads(text: str) -> dict | list | None:
    """LLMs often emit unescaped \" inside strings or truncate mid-JSON; json_repair fixes that."""
    try:
        out = json_repair.loads(text)
    except Exception as exc:
        logger.debug("json_repair.loads failed: %s", exc)
        return None
    if out is None:
        return None
    if not isinstance(out, (dict, list)):
        return None
    return out


def _extract_json(raw: str) -> dict | list | None:
    """Strip markdown fences and parse the first JSON structure found."""
    text = _strip_fences(raw)

    try:
        return _lenient_loads(text)
    except json.JSONDecodeError as exc:
        logger.debug("Strict JSON parse failed: %s", exc)
    repaired = _repair_loads(text)
    if repaired is not None:
        return repaired

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            inner = text[start : end + 1]
            try:
                return _lenient_loads(inner)
            except json.JSONDecodeError:
                pass
            repaired = _repair_loads(inner)
            if repaired is not None:
                return repaired

    logger.error("Could not parse LLM coherence response:\n%s", raw[:2000])
    return None


def _validate_findings(items: list) -> list[dict]:
    valid: list[dict] = []
    for f in items:
        if isinstance(f, dict) and "section" in f and "issue" in f:
            valid.append(
                {
                    "section": str(f["section"]),
                    "quote": str(f.get("quote", "")),
                    "issue": str(f["issue"]),
                    "suggestion": str(f.get("suggestion", "")),
                    "severity": str(f.get("severity", "info")),
                }
            )
    return valid


def _parse_response(raw: str) -> tuple[list[dict], dict]:
    """Parse the LLM response into (findings, evaluation)."""
    parsed = _extract_json(raw)
    if parsed is None:
        return [], dict(_EMPTY_EVALUATION)

    if isinstance(parsed, list):
        return _validate_findings(parsed), dict(_EMPTY_EVALUATION)

    if isinstance(parsed, dict):
        findings_raw = parsed.get("findings", [])
        findings = (
            _validate_findings(findings_raw) if isinstance(findings_raw, list) else []
        )

        evaluation = dict(_EMPTY_EVALUATION)
        eval_raw = parsed.get("evaluation", {})
        if isinstance(eval_raw, dict):
            if isinstance(eval_raw.get("strengths"), list):
                evaluation["strengths"] = [str(s) for s in eval_raw["strengths"]]
            if isinstance(eval_raw.get("weaknesses"), list):
                evaluation["weaknesses"] = [str(s) for s in eval_raw["weaknesses"]]
            if eval_raw.get("overall"):
                evaluation["overall"] = str(eval_raw["overall"])

        return findings, evaluation

    return [], dict(_EMPTY_EVALUATION)


def check_coherence(chunks: list[dict]) -> tuple[list[dict], dict]:
    """Send all chunks to the LLM and return (findings, evaluation)."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping coherence check")
        return [], dict(_EMPTY_EVALUATION)

    model = os.environ.get("COHERENCE_MODEL", _DEFAULT_MODEL)
    try:
        max_tokens = int(os.environ.get("COHERENCE_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)))
    except ValueError:
        max_tokens = _DEFAULT_MAX_TOKENS

    client = OpenAI(base_url=_OPENROUTER_BASE, api_key=api_key)

    doc_iso, doc_name = document_language_for_llm(chunks)
    user_prompt = _build_user_prompt(chunks, doc_iso, doc_name)
    logger.info(
        "Sending %d chunks to %s for coherence check (document language: %s / %s)",
        len(chunks),
        model,
        doc_iso,
        doc_name,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
    except Exception:
        logger.exception("OpenRouter API call failed")
        return [], dict(_EMPTY_EVALUATION)

    if not response.choices:
        logger.warning("LLM returned no choices")
        return [], dict(_EMPTY_EVALUATION)

    choice = response.choices[0]
    raw = choice.message.content or ""
    finish = getattr(choice, "finish_reason", None)
    if finish == "length":
        logger.warning(
            "LLM hit max_tokens limit (increase COHERENCE_MAX_TOKENS); response may be truncated"
        )
    logger.info(
        "LLM raw response (%d chars, finish=%s): %.500s",
        len(raw),
        finish,
        raw,
    )

    if not raw.strip():
        logger.warning("LLM returned empty content")
        return [], dict(_EMPTY_EVALUATION)

    findings, evaluation = _parse_response(raw)
    logger.info("Coherence check returned %d findings", len(findings))
    return findings, evaluation
