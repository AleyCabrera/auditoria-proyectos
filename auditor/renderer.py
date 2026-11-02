"""Renderiza el documento Markdown: manifiesto + cuerpo."""

from __future__ import annotations

from datetime import datetime, timezone

from auditor.config import AuditConfig
from auditor.external import ExternalResult
from auditor.scanner import FileRecord
from auditor.secrets import SecretHit


def _tree(records: list[FileRecord], root_name: str) -> str:
    paths = sorted({r.relative.as_posix() for r in records})
    lines = [root_name + "/"]
    seen_dirs: set[str] = set()
    for path in paths:
        parts = path.split("/")
        for i in range(len(parts) - 1):
            prefix = "/".join(parts[: i + 1])
            if prefix not in seen_dirs:
                seen_dirs.add(prefix)
                lines.append("    " * (i + 1) + parts[i] + "/")
        lines.append("    " * len(parts) + parts[-1])
    return "\n".join(lines)


def _manifest(records: list[FileRecord], project_name: str,
              cfg: AuditConfig, git_meta: dict,
              external: list[ExternalResult]) -> str:
    lines: list[str] = [
        "# MANIFIESTO DE AUDITORÍA\n",
        f"**Proyecto:** `{project_name}`",
        f"**Generado:** {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "**Generador:** auditor v0.1",
        f"**Preset:** `{cfg.preset}`",
    ]
    if git_meta:
        lines.append(f"**Commit:** `{git_meta.get('commit', 'n/a')}`")
        lines.append(f"**Rama:** `{git_meta.get('branch', 'n/a')}`")
        lines.append(f"**Working tree limpio:** {git_meta.get('dirty', 'n/a')}")

    included = [r for r in records if r.skipped_reason is None]
    omitted = [r for r in records if r.skipped_reason is not None]
    lines.append(f"**Archivos incluidos:** {len(included)}")
    lines.append(f"**Archivos omitidos:** {len(omitted)}")
    lines.append("")

    # Tabla de archivos
    lines.append("## Archivos\n")
    lines.append("| Archivo | Lenguaje | KB | SHA-256 (12) | Secretos | Estado |")
    lines.append("|---|---|---|---|---|---|")
    for r in sorted(records, key=lambda x: x.relative.as_posix()):
        status = "✅" if r.skipped_reason is None else f"⛔ {r.skipped_reason}"
        sha = r.sha256[:12] if r.sha256 else "—"
        secrets = str(len(r.secret_hits)) if r.secret_hits else "—"
        lines.append(
            f"| `{r.relative.as_posix()}` | {r.language} | "
            f"{r.size_bytes / 1024:.1f} | `{sha}` | {secrets} | {status} |"
        )
    lines.append("")

    # Secretos
    all_secrets: list[tuple[FileRecord, SecretHit]] = [
        (r, h) for r in records for h in r.secret_hits
    ]
    if all_secrets:
        lines.append("## Secretos detectados (redactados)\n")
        lines.append("| Archivo:Línea | Regla | Extracto |")
        lines.append("|---|---|---|")
        for record, hit in all_secrets:
            lines.append(
                f"| `{record.relative.as_posix()}:{hit.line}` | "
                f"`{hit.rule}` | `{hit.redacted}` |"
            )
        lines.append("")

    # Scanners externos
    if external:
        lines.append("## Scanners externos\n")
        for result in external:
            if not result.available:
                lines.append(f"- **{result.name}:** no instalado (omitido)")
                continue
            lines.append(
                f"- **{result.name}:** {len(result.findings)} hallazgo(s), "
                f"exit={result.returncode}"
            )
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def _external_findings_block(external: list[ExternalResult]) -> str:
    blocks = []
    for result in external:
        if not result.available or not result.findings:
            continue
        blocks.append(f"### {result.name}\n")
        blocks.append("```json")
        blocks.append(__import__("json").dumps(
            result.findings, indent=2, ensure_ascii=False)[:50_000])
        blocks.append("```\n")
    if not blocks:
        return ""
    return "# HALLAZGOS DE SCANNERS EXTERNOS\n\n" + "\n".join(blocks) + "\n---\n\n"


def render(records: list[FileRecord], cfg: AuditConfig, *,
           prompt: str, git_meta: dict,
           external: list[ExternalResult],
           redact: bool = True) -> str:
    project_name = cfg.project_path.name or "proyecto"
    parts: list[str] = []
    parts.append(
        f"# DOCUMENTO DE AUDITORÍA — {project_name}\n\n"
        f"{prompt}\n\n---\n\n"
    )
    parts.append(_manifest(records, project_name, cfg, git_meta, external))
    parts.append("\n# ESTRUCTURA\n\n```text\n")
    parts.append(_tree(records, project_name))
    parts.append("\n```\n\n---\n\n")

    ext_block = _external_findings_block(external)
    if ext_block:
        parts.append(ext_block)

    parts.append("# CONTENIDO DE LOS ARCHIVOS\n\n")

    budget = cfg.max_total_mb * 1024 * 1024
    written = sum(len(p.encode("utf-8")) for p in parts)
    skipped: list[FileRecord] = []

    for record in records:
        if record.skipped_reason is not None:
            continue
        content = record.content
        if redact and record.secret_hits:
            from auditor.secrets import redact_text
            content = redact_text(content, record.secret_hits)
        fence = record.fence
        header = (
            f"## `{record.relative.as_posix()}`\n\n"
            f"**Lenguaje:** {record.language}  ·  "
            f"**SHA-256:** `{record.sha256[:12] if record.sha256 else '—'}`\n\n"
            f"```{fence}\n"
        )
        footer = "\n```\n\n---\n\n"
        block = header + content + footer
        if written + len(block.encode("utf-8")) > budget:
            record.skipped_reason = "budget"
            skipped.append(record)
            continue
        parts.append(block)
        written += len(block.encode("utf-8"))

    all_omitted = [r for r in records if r.skipped_reason is not None]
    if all_omitted:
        parts.append("# ARCHIVOS OMITIDOS\n\n")
        for r in all_omitted:
            parts.append(
                f"- `{r.relative.as_posix()}` — motivo: **{r.skipped_reason}**\n")
        parts.append("\n")

    return "".join(parts)