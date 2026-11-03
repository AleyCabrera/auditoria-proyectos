from pathlib import Path

from auditor.config import AuditConfig
from auditor.scanner import scan


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_finds_python(tmp_path):
    _write(tmp_path, "app.py", "print('hi')\n")
    cfg = AuditConfig(project_path=tmp_path, output_dir=tmp_path / "out")
    records = scan(cfg)
    assert any(r.relative == Path("app.py") for r in records)


def test_scan_skips_output_dir(tmp_path):
    _write(tmp_path, "app.py", "x = 1\n")
    out = tmp_path / "audit-output"
    out.mkdir()
    (out / "auditoria.md").write_text("# old", encoding="utf-8")
    cfg = AuditConfig(project_path=tmp_path, output_dir=out)
    records = scan(cfg)
    names = [r.relative.as_posix() for r in records]
    assert "audit-output/auditoria.md" not in names


def test_scan_skips_binary(tmp_path):
    (tmp_path / "image.bin").write_bytes(b"\x00\x01\x02" * 100)
    (tmp_path / "image.bin").rename(tmp_path / "image.txt")
    cfg = AuditConfig(project_path=tmp_path, output_dir=tmp_path / "out")
    records = scan(cfg)
    bin_rec = [r for r in records if r.relative.suffix == ".txt"]
    assert all(r.skipped_reason == "binary" for r in bin_rec)


def test_scan_marks_oversize(tmp_path):
    _write(tmp_path, "big.py", "x = 1\n" * 200_000)
    cfg = AuditConfig(project_path=tmp_path, output_dir=tmp_path / "out",
                      max_file_kb=1)
    records = scan(cfg)
    big = [r for r in records if r.relative.name == "big.py"]
    assert big and big[0].skipped_reason == "size"


def test_scan_skips_own_output(tmp_path):
    _write(tmp_path, "app.py", "x = 1\n")
    out = tmp_path / "audit-output"
    out.mkdir()
    cfg = AuditConfig(project_path=tmp_path, output_dir=out)
    # Primera pasada: no existe output
    scan(cfg)
    # Crear output y verificar que no se incluye
    (out / "auditoria.md").write_text("# generated", encoding="utf-8")
    records = scan(cfg)
    assert all("audit-output" not in r.relative.as_posix() for r in records)
    
def test_cli_output_goes_to_cwd(tmp_path, monkeypatch):
    """Regresión: el output NO debe escribirse dentro del target."""
    from auditor.cli import main as cli_main
    from pathlib import Path

    # Crear target
    target = tmp_path / "target-project"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")

    # Simular CWD distinto al target
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    rc = cli_main([str(target), "--quiet"])
    assert rc == 0

    # Output debe estar en CWD, NO en target
    assert (workdir / "audit-output" / "auditoria.md").exists()
    assert not (target / "audit-output").exists()