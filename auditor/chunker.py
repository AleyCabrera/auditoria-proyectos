"""Divide el render final en N documentos ≤ max_total_mb."""

from __future__ import annotations

from pathlib import Path

from auditor.config import AuditConfig


def write_chunked(rendered: str, cfg: AuditConfig) -> list[Path]:
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = cfg.max_total_mb * 1024 * 1024

    if len(rendered.encode("utf-8")) <= max_bytes:
        out = output_dir / "auditoria.md"
        out.write_text(rendered, encoding="utf-8")
        return [out]

    # Split por encabezados de nivel 2 (`## `)
    sections = rendered.split("\n## ")
    sections = [sections[0]] + [f"## {s}" for s in sections[1:]]

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for section in sections:
        section_size = len(section.encode("utf-8"))
        if current and current_size + section_size > max_bytes:
            chunks.append("".join(current))
            current, current_size = [], 0
        current.append(section)
        current_size += section_size
    if current:
        chunks.append("".join(current))

    paths: list[Path] = []
    for i, chunk in enumerate(chunks, start=1):
        path = output_dir / f"auditoria_{i:02d}.md"
        path.write_text(chunk, encoding="utf-8")
        paths.append(path)
    return paths


def write_manifest_json(records, cfg: AuditConfig, git_meta: dict) -> Path:
    import json
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": cfg.project_path.name,
        "preset": cfg.preset,
        "git": git_meta,
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