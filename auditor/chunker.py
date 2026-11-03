"""Divide el render final en N documentos ≤ max_total_mb."""

from __future__ import annotations

import logging
from pathlib import Path

from auditor.config import AuditConfig
from auditor.renderer import CHUNK_SEPARATOR

log = logging.getLogger("auditor")


def write_chunked(rendered: str, cfg: AuditConfig) -> list[Path]:
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = cfg.max_total_mb * 1024 * 1024

    # === Fix A: limpiar salidas previas (chunks huérfanos) ===
    for old in output_dir.glob("auditoria_*.md"):
        old.unlink()
    old_single = output_dir / "auditoria.md"
    if old_single.exists():
        old_single.unlink()

    # Caso feliz: cabe en un solo archivo
    if len(rendered.encode("utf-8")) <= max_bytes:
        out = output_dir / "auditoria.md"
        out.write_text(rendered, encoding="utf-8")
        return [out]

    # Split SOLO en separadores explícitos (nunca dentro de code fences)
    sections = [s for s in rendered.split(CHUNK_SEPARATOR) if s.strip()]
    if not sections:
        out = output_dir / "auditoria.md"
        out.write_text(rendered, encoding="utf-8")
        return [out]

    # === Fix B: contabilidad correcta del separador ===
    sep_len = len(CHUNK_SEPARATOR.encode("utf-8"))
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for section in sections:
        section_size = len(section.encode("utf-8"))
        # El separador cuenta solo si ya hay contenido previo
        extra = sep_len if current else 0
        if current and current_size + extra + section_size > max_bytes:
            chunks.append(CHUNK_SEPARATOR.join(current))
            current, current_size = [], 0
            extra = 0
        current.append(section)
        current_size += extra + section_size
    if current:
        chunks.append(CHUNK_SEPARATOR.join(current))

    # Si aún así quedó uno solo (ej: un archivo individual > budget)
    if len(chunks) == 1:
        out = output_dir / "auditoria.md"
        out.write_text(chunks[0], encoding="utf-8")
        return [out]

    # Warning para chunks que exceden el budget (archivo individual > budget)
    for i, chunk in enumerate(chunks, start=1):
        size = len(chunk.encode("utf-8"))
        if size > max_bytes * 1.1:
            log.warning(
                "Chunk %02d (%.1f KB) excede el budget (%.1f KB). "
                "Archivo individual > --max-total-mb. "
                "Considerá --max-file-kb menor o --max-total-mb mayor.",
                i, size / 1024, max_bytes / 1024,
            )

    paths: list[Path] = []
    for i, chunk in enumerate(chunks, start=1):
        out = output_dir / f"auditoria_{i:02d}.md"
        out.write_text(chunk, encoding="utf-8")
        paths.append(out)
    return paths


def write_manifest_json(records, cfg: AuditConfig, git_meta: dict,
                        chunks: list[Path] | None = None) -> Path:
    """Escribe MANIFEST.json con metadatos de archivos y chunks."""
    import json
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": cfg.project_path.name,
        "preset": cfg.preset,
        "git": git_meta,
        "chunks": [p.name for p in (chunks or [])],
        "files": [
            {
                "path": r.relative.as_posix(),
                "language": r.language,
                "size_bytes": r.size_bytes,
                "sha256": r.sha256,
                "skipped_reason": r.skipped_reason,
                "secret_hits": [
                    {"line": h.line, "rule": h.rule, "redacted": h.redacted}
                    for h in r.secret_hits
                ],
            }
            for r in records
        ],
    }
    path = output_dir / "MANIFEST.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path