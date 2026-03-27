from __future__ import annotations

import json
import os
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "openai/gpt-oss-20b:free"

_SYSTEM_PROMPT = """\
Du bist ein erfahrener akademischer Lektor. Du erhältst die Abschnitte einer \
wissenschaftlichen Arbeit (Bachelor-/Masterarbeit) und prüfst ausschließlich:

1. **Roter Faden**: Gibt es eine nachvollziehbare, logische Abfolge der Abschnitte? \
Baut jeder Abschnitt sinnvoll auf dem vorherigen auf?
2. **Logische Brüche**: Gibt es Stellen, an denen der Gedankengang abrupt wechselt, \
Argumente fehlen oder Schlussfolgerungen nicht aus dem Vorherigen folgen?
3. **Akademischer Schreibstil**: Wird durchgängig ein sachlicher, präziser, \
wissenschaftlicher Ton verwendet? Gibt es umgangssprachliche oder zu informelle Passagen?

WICHTIG: Antworte IMMER in derselben Sprache, in der die Arbeit verfasst ist. \
Ist die Arbeit auf Deutsch, antworte auf Deutsch. Ist sie auf Englisch, antworte auf Englisch.

Antworte ausschließlich mit einem JSON-Array. Jedes Element beschreibt genau ein Problem:

```json
[
  {
    "section": "<exakter Titel des betroffenen Abschnitts>",
    "issue": "<Beschreibung des Problems, 1-2 Sätze, in der Sprache der Arbeit>",
    "suggestion": "<konkreter Verbesserungsvorschlag, 1-2 Sätze, in der Sprache der Arbeit>",
    "severity": "info | warning | error"
  }
]
```

Wenn du keine Probleme findest, antworte mit einem leeren Array `[]`.
Antworte NUR mit dem JSON-Array, ohne Erklärung davor oder danach.\
"""


def _build_user_prompt(chunks: list[dict]) -> str:
    parts: list[str] = []
    for c in chunks:
        level = c["heading_level"]
        prefix = "#" * level
        parts.append(f"{prefix} {c['section']}\n\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def _parse_findings(raw: str) -> list[dict]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        findings = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON response, attempting extraction")
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                findings = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                logger.error("Could not parse LLM coherence response")
                return []
        else:
            return []

    if not isinstance(findings, list):
        return []

    valid: list[dict] = []
    for f in findings:
        if isinstance(f, dict) and "section" in f and "issue" in f:
            valid.append(
                {
                    "section": str(f["section"]),
                    "issue": str(f["issue"]),
                    "suggestion": str(f.get("suggestion", "")),
                    "severity": str(f.get("severity", "info")),
                }
            )
    return valid


def check_coherence(chunks: list[dict]) -> list[dict]:
    """Send all chunks to the LLM and return coherence findings."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping coherence check")
        return []

    model = os.environ.get("COHERENCE_MODEL", _DEFAULT_MODEL)

    client = OpenAI(base_url=_OPENROUTER_BASE, api_key=api_key)

    user_prompt = _build_user_prompt(chunks)

    logger.info("Sending %d chunks to %s for coherence check", len(chunks), model)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content or "[]"
    findings = _parse_findings(raw)
    logger.info("Coherence check returned %d findings", len(findings))
    return findings
