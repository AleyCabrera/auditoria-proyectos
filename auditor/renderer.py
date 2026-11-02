from datetime import datetime

def render_manifest(records, project, cfg, git_meta: dict) -> str:
    included = [r for r in records if r.skipped_reason is None]
    omitted = [r for r in records if r.skipped_reason]
    lines = [
        "# MANIFIESTO DE AUDITORÍA\n",
        f"**Proyecto:** `{project.name}`",
        f"**Generado:** {datetime.now().isoformat()}",
        f"**Generador:** auditor v0.1",
        f"**Preset:** {cfg.preset}",
    ]
    if git_meta:
        lines += [
            f"**Commit:** `{git_meta.get('commit', 'n/a')}`",
            f"**Rama:** `{git_meta.get('branch', 'n/a')}`",
            f"**Dirty:** {git_meta.get('dirty', 'n/a')}",
        ]
    lines += [
        f"**Archivos incluidos:** {len(included)}",
        f"**Archivos omitidos:** {len(omitted)}",
        "",
        "| Archivo | Lenguaje | KB | SHA-256 (12) | Estado |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda x: x.relative.as_posix()):
        status = "✅" if r.skipped_reason is None else f"⛔ {r.skipped_reason}"
        sha = r.sha256[:12] if r.sha256 else "—"
        lines.append(
            f"| `{r.relative.as_posix()}` | {r.language} | "
            f"{r.size_bytes/1024:.1f} | `{sha}` | {status} |"
        )
    return "\n".join(lines) + "\n\n---\n\n"


def render_body(records, project, cfg, prompt_text: str) -> str:
    """Escribe cabecera, manifiesto, árbol y contenido respetando presupuesto real."""
    max_bytes = cfg.max_total_mb * 1024 * 1024
    parts = []

    header = (
        f"# DOCUMENTO DE AUDITORÍA — {project.name}\n\n"
        f"{prompt_text}\n\n---\n\n"
    )
    parts.append(header)

    # Árbol (ligero, siempre incluido)
    parts.append("## ESTRUCTURA\n\n```text\n" + build_tree(records) + "\n```\n\n---\n\n")

    written = sum(len(p.encode()) for p in parts)
    skipped = []
    for r in records:
        if r.skipped_reason:
            skipped.append(r); continue
        content = read_text(r.path)
        overhead = len(f"## {r.relative}\n\n**Lenguaje:** {r.language}\n\n```{r.fence}\n\n```\n\n---\n\n".encode())
        projected = written + overhead + len(content.encode())
        if projected > max_bytes:
            r.skipped_reason = "budget"; skipped.append(r); continue
        block = (
            f"## {r.relative}\n\n"
            f"**Lenguaje:** {r.language}  ·  "
            f"**SHA-256:** `{r.sha256[:12] if r.sha256 else '—'}`\n\n"
            f"```{r.fence}\n{content}\n```\n\n---\n\n"
        )
        parts.append(block); written += len(block.encode())

    if skipped:
        parts.append("## ARCHIVOS OMITIDOS\n\n")
        for r in skipped:
            parts.append(f"- `{r.relative}` — motivo: **{r.skipped_reason}**\n")
        parts.append("\n")

    return "".join(parts)