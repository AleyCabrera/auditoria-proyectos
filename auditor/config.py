from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AuditConfig:
    project_path: Path
    output_dir: Path = Path("audit-output")
    preset: str = "general"
    use_gitignore: bool = True
    respect_auditignore: bool = True
    ignore_folders: set[str] = field(default_factory=lambda: {
        ".git", ".github", ".idea", ".vscode", "__pycache__", "node_modules",
        "venv", ".venv", "env", "dist", "build", "target", "bin", "obj",
        "coverage", ".next", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        "audit-output",
    })
    ignore_patterns: set[str] = field(default_factory=lambda: {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
        "composer.lock", "*.min.js", "*.min.css", "*.map", "*.lock",
    })
    allowed_extensions: set[str] = field(default_factory=lambda: {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs", ".cpp", ".c",
        ".h", ".hpp", ".go", ".rs", ".php", ".html", ".css", ".scss",
        ".sql", ".json", ".xml", ".yaml", ".yml", ".md", ".txt", ".env",
        ".properties", ".toml", ".sh", ".ps1", ".dockerfile",
    })
    key_files_priority: list[str] = field(default_factory=lambda: [
        "README.md", "pyproject.toml", "package.json", "requirements.txt",
        "composer.json", "pom.xml", "go.mod", "Cargo.toml", "Dockerfile",
        ".env.example",
    ])
    max_file_kb: int = 300
    max_total_mb: int = 8          # más realista para ventanas de 128k-200k tokens
    max_files_per_chunk: int = 150
    chunk_by: str = "size"         # "size" | "files" | "none"
    hash_files: bool = True
    scan_secrets: bool = True
    redact_secrets: bool = True
    include_git_metadata: bool = True
    run_external: list[str] = field(default_factory=list)  # ["semgrep","bandit","gitleaks"]

    @classmethod
    def from_toml(cls, path: Path) -> "AuditConfig":
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(**{k: Path(v) if isinstance(v, str) and "/" in k else v
                      for k, v in data.items()})
        