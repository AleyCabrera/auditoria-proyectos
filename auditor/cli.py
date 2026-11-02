"""CLI principal."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from auditor import __version__
from auditor.chunker import write_chunked, write_manifest_json
from auditor.config import AuditConfig
from auditor.external import run_external_scanners
from auditor.git_info import changed_since, git_metadata
from auditor.presets import apply_preset, prompt_for
from auditor.renderer import render
from auditor.scanner import scan

log = logging.getLogger("auditor")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="auditor",
        description="Empaqueta tu proyecto en Markdown + hallazgos "
                    "para que una IA lo audite.",
    )
    p.add_argument("path", nargs="?", default=".",
                   help="Ruta del proyecto a auditar (default: .)")
    p.add_argument("--output-dir", default=None,
                   help="Directorio de salida (default: ./audit-output)")
    p.add_argument("--preset", default="general",
                   choices=["general", "security", "dependencies", "architecture"])
    p.add_argument("--config", default=None, help="Ruta a un TOML de config")
    p.add_argument("--since", default=None,
                   help="Solo archivos cambiados desde este ref git (ej: origin/main)")
    p.add_argument("--max-file-kb", type=int, default=None)
    p.add_argument("--max-total-mb", type=int, default=None)
    p.add_argument("--no-gitignore", action="store_true")
    p.add_argument("--no-secrets", action="store_true")
    p.add_argument("--no-redact", action="store_true")
    p.add_argument("--no-hash", action="store_true")
    p.add_argument("--external", default=None,
                   help="Scanners externos separados por coma "
                        "(ej: semgrep,bandit). Default según preset.")
    p.add_argument("--list-files", action="store_true",
                   help="Solo listar archivos que se incluirían.")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--version", action="version", version=f"auditor {__version__}")
    return p


def _merge_config(args: argparse.Namespace) -> AuditConfig:
    if args.config:
        cfg = AuditConfig.from_toml(Path(args.config))
    else:
        cfg = AuditConfig()
    cfg.project_path = Path(args.path).resolve()
    if args.output_dir:
        cfg.output_dir = Path(args.output_dir).resolve()
    else:
        cfg.output_dir = (cfg.project_path / "audit-output").resolve()
    cfg.preset = args.preset
    if args.max_file_kb is not None:
        cfg.max_file_kb = args.max_file_kb
    if args.max_total_mb is not None:
        cfg.max_total_mb = args.max_total_mb
    if args.no_gitignore:
        cfg.use_gitignore = False
    if args.no_secrets:
        cfg.scan_secrets = False
    if args.no_redact:
        cfg.redact_secrets = False
    if args.no_hash:
        cfg.hash_files = False
    if args.external is not None:
        cfg.run_external = [s.strip() for s in args.external.split(",") if s.strip()]
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(message)s",
    )

    cfg = _merge_config(args)
    if not cfg.project_path.exists():
        log.error("La ruta no existe: %s", cfg.project_path)
        return 1
    if not cfg.project_path.is_dir():
        log.error("La ruta no es un directorio: %s", cfg.project_path)
        return 1

    cfg = apply_preset(cfg)

    # Modo --since
    only_paths = None
    if args.since:
        changed = changed_since(cfg.project_path, args.since)
        if changed is None:
            log.error("git no disponible o ref inválido: %s", args.since)
            return 2
        only_paths = changed
        log.info("Modo diff: %d archivo(s) cambiados desde %s",
                 len(changed), args.since)

    log.info("Escaneando %s ...", cfg.project_path)
    records = scan(cfg, only_paths=only_paths)
    if not records:
        log.warning("No se encontraron archivos para auditar.")
        return 0

    included = [r for r in records if r.skipped_reason is None]
    omitted = [r for r in records if r.skipped_reason is not None]
    log.info("Incluidos: %d  ·  Omitidos: %d", len(included), len(omitted))

    if args.list_files:
        for r in included:
            print(r.relative.as_posix())
        return 0

    # Git metadata
    git_meta = {}
    if cfg.include_git_metadata:
        git_meta = git_metadata(cfg.project_path)

    # External scanners
    external = []
    if cfg.run_external:
        log.info("Ejecutando scanners externos: %s", ", ".join(cfg.run_external))
        external = run_external_scanners(cfg.project_path, cfg.run_external)
        for result in external:
            if result.available:
                log.info("  · %s: %d hallazgo(s)", result.name, len(result.findings))

    # Render
    prompt = prompt_for(cfg.preset)
    rendered = render(
        records, cfg, prompt=prompt, git_meta=git_meta,
        external=external, redact=cfg.redact_secrets,
    )

    # Chunking + manifest JSON
    paths = write_chunked(rendered, cfg)
    manifest_path = write_manifest_json(records, cfg, git_meta)

    log.info("")
    log.info("Documentos generados:")
    for p in paths:
        log.info("  · %s", p)
    log.info("Manifiesto JSON: %s", manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())