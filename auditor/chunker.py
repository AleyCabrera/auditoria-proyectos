def write_chunked(rendered: str, output_dir: Path, cfg) -> list[Path]:
    """Si el render excede max_total_mb, divide por encabezados `## `."""
    max_bytes = cfg.max_total_mb * 1024 * 1024
    output_dir.mkdir(parents=True, exist_ok=True)
    if len(rendered.encode()) <= max_bytes:
        out = output_dir / "auditoria.md"
        out.write_text(rendered, encoding="utf-8")
        return [out]

    sections = rendered.split("\n## ")
    # Reconstruir con el encabezado `## ` original
    sections = [sections[0]] + [f"## {s}" for s in sections[1:]]

    parts, current, current_size = [], [], 0
    for sec in sections:
        sec_size = len(sec.encode())
        if current and current_size + sec_size > max_bytes:
            parts.append("".join(current))
            current, current_size = [], 0
        current.append(sec)
        current_size += sec_size
    if current:
        parts.append("".join(current))

    paths = []
    for i, part in enumerate(parts, start=1):
        p = output_dir / f"auditoria_{i:02d}.md"
        p.write_text(part, encoding="utf-8")
        paths.append(p)
    return paths