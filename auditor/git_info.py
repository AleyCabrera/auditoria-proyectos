"""Metadatos de git (opcional). No falla si git no está disponible."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _run(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def git_metadata(root: Path) -> dict[str, str]:
    if not shutil.which("git"):
        return {}
    if not (root / ".git").exists():
        return {}
    meta: dict[str, str] = {}
    for key, args in {
        "commit": ["git", "rev-parse", "--short", "HEAD"],
        "branch": ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        "dirty": ["git", "status", "--porcelain"],
    }.items():
        out = _run(args, root)
        if out is not None:
            meta[key] = "yes" if key == "dirty" and out else (out or "no")
    return meta


def changed_since(root: Path, ref: str) -> set[Path] | None:
    """Devuelve rutas relativas cambiadas desde `ref`. None si git falla."""
    out = _run(["git", "diff", "--name-only", f"{ref}..."], root)
    if out is None:
        return None
    return {Path(p) for p in out.splitlines() if p.strip()}