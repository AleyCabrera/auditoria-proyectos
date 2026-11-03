from pathlib import Path

from auditor.config import AuditConfig
from auditor.renderer import render
from auditor.scanner import scan


def test_render_contains_manifest_and_files(tmp_path):
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    cfg = AuditConfig(project_path=tmp_path, output_dir=tmp_path / "out")
    records = scan(cfg)
    out = render(records, cfg, prompt="# PROMPT", git_meta={}, external=[])
    assert "# DOCUMENTO DE AUDITORÍA" in out
    assert "# MANIFIESTO DE AUDITORÍA" in out
    assert "app.py" in out
    assert "# ESTRUCTURA" in out


def test_render_does_not_drop_files(tmp_path):
    """El renderer NO debe omitir archivos por budget (eso lo hace el chunker)."""
    (tmp_path / "a.py").write_text("x = 1\n" * 500_000, encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")
    cfg = AuditConfig(project_path=tmp_path, output_dir=tmp_path / "out",
                      max_total_mb=0.001, max_file_kb=10_000)
    records = scan(cfg)
    out = render(records, cfg, prompt="# PROMPT", git_meta={}, external=[])
    # Ambos archivos deben aparecer aunque excedan el budget total
    assert "`a.py`" in out
    assert "`b.py`" in out
    # Ninguno debe tener skipped_reason="budget"
    assert all(r.skipped_reason != "budget" for r in records)