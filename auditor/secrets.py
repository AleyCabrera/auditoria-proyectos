"""Detección de secretos con regex. Redacción opcional."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SecretHit:
    line: int
    rule: str
    matched: str
    redacted: str


# Orden importa: los más específicos primero.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("aws_secret_key", re.compile(
        r"(?:aws_?secret(?:_?access_?key)?|secret_?access_?key)"
        r"\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        re.IGNORECASE)),
    ("private_key", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("gitlab_token", re.compile(r"glpat-[A-Za-z0-9_\-]{20,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("stripe_key", re.compile(r"sk_live_[A-Za-z0-9]{24,}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("generic_api_key", re.compile(
        r"(?:api[_-]?key|apikey|access[_-]?token)\s*[:=]\s*['\"]?"
        r"([A-Za-z0-9_\-]{20,})['\"]?", re.IGNORECASE)),
    ("generic_password", re.compile(
        r"(?:password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{6,})['\"]",
        re.IGNORECASE)),
    ("connection_string", re.compile(
        r"(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis)://"
        r"[^\s:@'\"]+:[^\s@'\"]+@")),
]

# Placeholders REALES (con límites de palabra).
# NO incluimos "example" suelto: AKIAIOSFODNN7EXAMPLE debe detectarse.
_PLACEHOLDER_REGEX = re.compile(
    r"""
    \byour[_\-]?\w+          # your_key, your-token, yourkey, your_password
    | \bchange[_\-]?me\b     # changeme, change-me
    | \bplaceholder\b
    | \btodo\b
    | \bfixme\b
    | \bx{4,}\b              # xxxx, xxxxxxxx
    | \*{4,}                 # ****, ********
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _is_placeholder(value: str) -> bool:
    """True si el valor es claramente un placeholder de documentación.

    IMPORTANTE: NO rechazamos fixtures canónicos como AKIAIOSFODNN7EXAMPLE
    (la llave de ejemplo de AWS). Un secreto de ejemplo copiado a código es
    un riesgo real: alguien pudo haberlo usado por error.
    """
    if not value:
        return True
    if len(value) < 6:
        return True
    return bool(_PLACEHOLDER_REGEX.search(value))


def _redact(value: str) -> str:
    """Mantiene primeros 4 y últimos 2 chars, enmascara el resto."""
    if len(value) <= 6:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 6) + value[-2:]


def scan_secrets(text: str) -> list[SecretHit]:
    hits: list[SecretHit] = []
    seen: set[tuple[int, str]] = set()
    for line_num, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in PATTERNS:
            for match in pattern.finditer(line):
                raw = match.group(0)
                candidate = match.group(1) if match.groups() else raw
                if _is_placeholder(candidate):
                    continue
                key = (line_num, rule)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(SecretHit(
                    line=line_num, rule=rule,
                    matched=raw, redacted=_redact(raw),
                ))
    return hits


def redact_text(text: str, hits: list[SecretHit]) -> str:
    """Reemplaza las coincidencias exactas de `hits` por su versión redactada."""
    lines = text.splitlines(keepends=True)
    by_line: dict[int, list[SecretHit]] = {}
    for hit in hits:
        by_line.setdefault(hit.line, []).append(hit)
    for line_num, line_hits in by_line.items():
        if 0 < line_num <= len(lines):
            original = lines[line_num - 1]
            for hit in line_hits:
                original = original.replace(hit.matched, hit.redacted, 1)
            lines[line_num - 1] = original
    return "".join(lines)