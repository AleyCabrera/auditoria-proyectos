import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileRecord:
    path: Path            # absoluta
    relative: Path        # relativa a la raíz
    size_bytes: int
    language: str
    fence: str
    sha256: str
    is_binary: bool
    secret_hits: list[dict] = None
    skipped_reason: str | None = None   # "size" | "budget" | "binary" | None

def _is_binary(path: Path, sniff: int = 8192) -> bool:
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(sniff)
        return b"\x00" in chunk
    except OSError:
        return True

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _should_skip_dir(name: str, cfg, spec, rel_dir: Path) -> bool:
    if name in cfg.ignore_folders:
        return True
    if spec and spec.match_file(rel_dir.as_posix() + "/"):
        return True
    return False

def _should_skip_file(name: str, path: Path, cfg, spec) -> bool:
    import fnmatch
    if any(fnmatch.fnmatch(name, pat) for pat in cfg.ignore_patterns):
        return True
    if path.suffix.lower() not in cfg.allowed_extensions:
        return True
    if spec and spec.match_file(path.as_posix()):
        return True
    return False

def _load_gitignore(root: Path, cfg):
    """Devuelve el patrón de .gitignore, si existe y pathspec está instalado."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return None
    try:
        from importlib import import_module

        pathspec = import_module("pathspec")
        with gitignore.open("r", encoding="utf-8", errors="replace") as fh:
            return pathspec.PathSpec.from_lines("gitwildmatch", fh)
    except (OSError, ImportError):
        return None

def scan(root: Path, cfg) -> list[FileRecord]:
    """Recorre el proyecto y devuelve FileRecord con metadatos resueltos.

    Excluye el output_dir propio para evitar auto-inclusión.
    """
    # Excluir el directorio de salida explícitamente
    output_dir = cfg.output_dir.resolve()
    spec = _load_gitignore(root, cfg) if cfg.use_gitignore else None

    records: list[FileRecord] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        # Poda in-place (evita descender)
        dirs[:] = sorted(
            d for d in dirs
            if not _should_skip_dir(d, cfg, spec,
                                    (current_path / d).relative_to(root))
            and (current_path / d).resolve() != output_dir
        )
        for name in sorted(files):
            path = current_path / name
            rel = path.relative_to(root)
            if _should_skip_file(name, rel, cfg, spec):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            language, fence = LANGUAGE_MAP.get(path.suffix.lower(), ("Texto", "text"))
            binary = _is_binary(path)
            records.append(FileRecord(
                path=path, relative=rel, size_bytes=size,
                language=language, fence=fence,
                sha256=_sha256(path) if cfg.hash_files else "",
                is_binary=binary,
                skipped_reason="binary" if binary else None,
            ))
    return records