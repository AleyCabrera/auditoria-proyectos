"""Recorre el proyecto y devuelve FileRecord con metadatos resueltos."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from auditor.config import AuditConfig
from auditor.filters import (
    is_binary_file, is_within, load_pathspec, matches_ignored_name,
)
from auditor.languages import DEFAULT_LANGUAGE, LANGUAGE_MAP
from auditor.secrets import SecretHit, scan_secrets


@dataclass
class FileRecord:
    path: Path
    relative: Path
    size_bytes: int
    language: str
    fence: str
    sha256: str
    is_binary: bool = False
    secret_hits: list[SecretHit] = field(default_factory=list)
    skipped_reason: str | None = None
    content: str = ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
        except OSError as exc:
            return f"[No fue posible leer: {exc}]"
    return "[No fue posible leer: encoding no reconocido]"


def _prune_dirs(current: Path, names: list[str], cfg: AuditConfig,
                gitignore_spec, auditignore_spec) -> list[str]:
    kept = []
    for name in names:
        candidate = current / name
        if name in cfg.ignore_folders:
            continue
        if not cfg.follow_symlinks and candidate.is_symlink():
            continue
        if not is_within(candidate, cfg.project_path):
            continue
        if candidate.resolve() == cfg.output_dir.resolve():
            continue
        rel = candidate.relative_to(cfg.project_path).as_posix() + "/"
        if gitignore_spec and gitignore_spec.match_file(rel):
            continue
        if auditignore_spec and auditignore_spec.match_file(rel):
            continue
        kept.append(name)
    return kept


def _should_skip_file(name: str, path: Path, cfg: AuditConfig,
                      gitignore_spec, auditignore_spec) -> bool:
    if matches_ignored_name(name, cfg.ignore_patterns):
        return True
    suffix = path.suffix.lower()
    if suffix not in cfg.allowed_extensions:
        # Dockerfile sin extensión: detectar por nombre
        if name != "Dockerfile":
            return True
    if not cfg.follow_symlinks and path.is_symlink():
        return True
    rel = path.relative_to(cfg.project_path).as_posix()
    if gitignore_spec and gitignore_spec.match_file(rel):
        return True
    if auditignore_spec and auditignore_spec.match_file(rel):
        return True
    return False


def scan(cfg: AuditConfig, only_paths: set[Path] | None = None) -> list[FileRecord]:
    """Devuelve FileRecord con contenido y secretos ya escaneados.

    Si `only_paths` se pasa, solo esos archivos (rutas relativas al proyecto)
    se incluyen. Se usa en modo --since.
    """
    root = cfg.project_path.resolve()
    gitignore_spec = load_pathspec(root, ".gitignore") if cfg.use_gitignore else None
    auditignore_spec = (load_pathspec(root, ".auditignore")
                        if cfg.respect_auditignore else None)

    records: list[FileRecord] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(_prune_dirs(
            current_path, dirs, cfg, gitignore_spec, auditignore_spec))
        for name in sorted(files):
            path = current_path / name
            rel = path.relative_to(root)
            if only_paths is not None and rel not in only_paths:
                continue
            if _should_skip_file(name, path, cfg, gitignore_spec, auditignore_spec):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            language, fence = LANGUAGE_MAP.get(path.suffix.lower(), DEFAULT_LANGUAGE)
            binary = is_binary_file(path)
            record = FileRecord(
                path=path, relative=rel, size_bytes=size,
                language=language, fence=fence,
                sha256=_sha256(path) if cfg.hash_files else "",
                is_binary=binary,
            )
            if binary:
                record.skipped_reason = "binary"
            elif size / 1024 > cfg.max_file_kb:
                record.skipped_reason = "size"
            else:
                record.content = _read_text(path)
                if cfg.scan_secrets and record.content:
                    record.secret_hits = scan_secrets(record.content)
            records.append(record)

    # Archivos clave primero
    def sort_key(r: FileRecord):
        try:
            return (0, cfg.key_files_priority.index(r.relative.name))
        except ValueError:
            return (1, r.relative.as_posix())
    records.sort(key=sort_key)
    return records