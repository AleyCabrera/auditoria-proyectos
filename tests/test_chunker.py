"""Tests del chunker: splitting, fences, round-trip y limpieza."""

from pathlib import Path

from auditor.chunker import write_chunked
from auditor.config import AuditConfig
from auditor.renderer import CHUNK_SEPARATOR


def test_write_chunked_single_file_when_small(tmp_path):
    """Si el render cabe en el budget, un solo auditoria.md (sin numerar)."""
    cfg = AuditConfig(output_dir=tmp_path, max_total_mb=1.0)
    rendered = "# Título\n\n## Archivo 1\n\ncontenido\n"
    paths = write_chunked(rendered, cfg)

    assert len(paths) == 1
    assert paths[0].name == "auditoria.md"
    assert paths[0].exists()


def test_write_chunked_splits_when_large(tmp_path):
    """Con CHUNK_SEPARATOR, un render grande se divide en varios chunks."""
    cfg = AuditConfig(output_dir=tmp_path, max_total_mb=0.001)  # 1 KB
    sections = [f"## Sección {i}\n\n{'x' * 500}" for i in range(10)]
    rendered = CHUNK_SEPARATOR.join(sections)
    paths = write_chunked(rendered, cfg)

    assert len(paths) > 1, "Debe dividir cuando el render excede el budget"
    assert all(p.name.startswith("auditoria_") for p in paths)
    for p in paths:
        assert p.stat().st_size < 2 * 1024, (
            f"{p.name} pesa {p.stat().st_size} bytes > budget 1 KB + margen"
        )


def test_write_chunked_no_split_inside_fences(tmp_path):
    """Regresión: ## dentro de ``` no deben crear chunks."""
    file_a = (
        "## `big.md`\n\n```markdown\n"
        + ("## section\n" * 50)
        + "```\n"
    )
    file_b = "## `small.py`\n\n```python\nx = 1\n```\n"
    rendered = file_a + CHUNK_SEPARATOR + file_b

    cfg = AuditConfig(output_dir=tmp_path, max_total_mb=0.05)  # 50 KB
    paths = write_chunked(rendered, cfg)

    assert len(paths) == 1
    content = paths[0].read_text(encoding="utf-8")
    assert content.count("## section") == 50
    assert "`big.md`" in content
    assert "`small.py`" in content


def test_write_chunked_preserves_separator_metadata(tmp_path):
    """Round-trip: concatenar chunks con el separador recupera el original."""
    cfg = AuditConfig(output_dir=tmp_path, max_total_mb=0.001)  # 1 KB
    sections = [f"## S{i}\n\n{'y' * 400}" for i in range(5)]
    original = CHUNK_SEPARATOR.join(sections)

    paths = write_chunked(original, cfg)
    combined = CHUNK_SEPARATOR.join(
        p.read_text(encoding="utf-8") for p in paths
    )

    assert combined == original


def test_write_chunked_accepts_float_budget(tmp_path):
    """Regresión: --max-total-mb 0.05 debe funcionar (no solo int)."""
    cfg = AuditConfig(output_dir=tmp_path, max_total_mb=0.05)
    rendered = "## a\n\n" + ("x" * 60_000)  # 60 KB > 50 KB budget
    paths = write_chunked(rendered, cfg)
    assert len(paths) >= 1


def test_write_chunked_cleans_stale_chunks(tmp_path):
    """Regresión: no deben quedar chunks huérfanos de runs anteriores."""
    # Setup: simular run previo con 4 chunks huérfanos
    (tmp_path / "auditoria_03.md").write_text("stale", encoding="utf-8")
    (tmp_path / "auditoria_04.md").write_text("stale", encoding="utf-8")
    (tmp_path / "auditoria.md").write_text("stale-single", encoding="utf-8")

    # Run nuevo: debe producir 2 chunks
    cfg = AuditConfig(output_dir=tmp_path, max_total_mb=0.001)
    rendered = CHUNK_SEPARATOR.join(
        [f"## S{i}\n\n{'x' * 400}" for i in range(4)]
    )
    paths = write_chunked(rendered, cfg)

    on_disk = sorted(p.name for p in tmp_path.glob("auditoria*.md"))
    assert on_disk == sorted(p.name for p in paths), (
        f"Disco {on_disk} ≠ retorno {sorted(p.name for p in paths)}"
    )
    assert "auditoria_03.md" not in on_disk, "Chunk huérfano no fue limpiado"
    assert "auditoria_04.md" not in on_disk, "Chunk huérfano no fue limpiado"
    assert "auditoria.md" not in on_disk, "Single huérfano no fue limpiado"