"""Filtros: .gitignore, .auditignore y detección de binarios."""

from __future__ import annotations

import fnmatch
from pathlib import Path


def load_pathspec(root: Path, filename: str):
    """Carga un PathSpec desde `filename` en `root`. None si no existe pathspec."""
    spec_path = root / filename
    if not spec_path.exists():
        return None
    try:
        import pathspec
    except ImportError:
        return None
    lines = spec_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def matches_ignored_name(name: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def is_binary_file(path: Path, sniff_bytes: int = 8192) -> bool:
    """Heurística: presencia de byte nulo en los primeros KB."""
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(sniff_bytes)
    except OSError:
        return True


def is_within(child: Path, parent: Path) -> bool:
    """True si `child` está dentro de `parent` (resuelve symlinks)."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False