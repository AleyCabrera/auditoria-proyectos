"""Configuración tipada del auditor. Carga desde TOML o argumentos CLI."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path


@dataclass
class AuditConfig:
    project_path: Path = Path(".")
    output_dir: Path = Path("audit-output")
    preset: str = "general"
    use_gitignore: bool = True
    respect_auditignore: bool = True
    ignore_folders: set[str] = field(default_factory=lambda: {
        ".git", ".github", ".gitlab", ".idea", ".vscode",
        "__pycache__", "node_modules", "venv", ".venv", "env",
        "dist", "build", "target", "bin", "obj", "coverage",
        ".next", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        ".tox", ".cache", "audit-output",
    })
    ignore_patterns: set[str] = field(default_factory=lambda: {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "poetry.lock", "composer.lock", "Gemfile.lock",
        "*.min.js", "*.min.css", "*.map", "*.lock",
        "*.pyc", "*.pyo", "*.so", "*.dll", "*.dylib",
        "*.exe", "*.bin", "*.png", "*.jpg", "*.jpeg", "*.gif",
        "*.svg", "*.ico", "*.pdf", "*.zip", "*.tar", "*.gz",
    })
    allowed_extensions: set[str] = field(default_factory=lambda: {
        ".py", ".js", ".mjs", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
        ".java", ".kt", ".swift", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".pl", ".lua", ".r", ".dart",
        ".html", ".css", ".scss", ".sql", ".graphql", ".gql", ".proto",
        ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
        ".env", ".sh", ".ps1", ".dockerfile", ".tf",
        ".md", ".txt", ".properties",
    })
    key_files_priority: list[str] = field(default_factory=lambda: [
        "README.md", "README.rst", "pyproject.toml", "package.json",
        "requirements.txt", "composer.json", "pom.xml", "build.gradle",
        "go.mod", "Cargo.toml", "Gemfile", "Dockerfile", "docker-compose.yml",
        ".env.example",
    ])
    max_file_kb: int = 300
    max_total_mb: int = 8
    max_files_per_chunk: int = 150
    hash_files: bool = True
    scan_secrets: bool = True
    redact_secrets: bool = True
    include_git_metadata: bool = True
    follow_symlinks: bool = False
    run_external: list[str] = field(default_factory=list)

    @classmethod
    def from_toml(cls, path: Path) -> "AuditConfig":
        import tomllib
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        kwargs = {}
        for key, value in raw.items():
            if key not in known:
                continue
            if key in {"ignore_folders", "ignore_patterns", "allowed_extensions"}:
                kwargs[key] = set(value)
            elif key == "key_files_priority":
                kwargs[key] = list(value)
            elif key in {"project_path", "output_dir"}:
                kwargs[key] = Path(value)
            else:
                kwargs[key] = value
        return cls(**kwargs)


def default_config() -> AuditConfig:
    return AuditConfig()