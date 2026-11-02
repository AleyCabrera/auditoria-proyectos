"""Orquestación de scanners externos opcionales."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExternalResult:
    name: str
    available: bool
    returncode: int | None = None
    output: str = ""
    findings: list[dict] = field(default_factory=list)


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except FileNotFoundError:
        return -1, "scanner not installed"
    except subprocess.TimeoutExpired:
        return -2, "timeout"


def _run_semgrep(root: Path) -> ExternalResult:
    if not shutil.which("semgrep"):
        return ExternalResult("semgrep", available=False)
    rc, out = _run(
        ["semgrep", "--config=auto", "--json", "--quiet", "."], root)
    findings = []
    if rc == 0:
        try:
            data = json.loads(out)
            findings = data.get("results", [])
        except json.JSONDecodeError:
            pass
    return ExternalResult("semgrep", available=True, returncode=rc,
                          output=out, findings=findings)


def _run_bandit(root: Path) -> ExternalResult:
    if not shutil.which("bandit"):
        return ExternalResult("bandit", available=False)
    rc, out = _run(["bandit", "-r", "-f", "json", "-q", "."], root)
    findings = []
    try:
        data = json.loads(out)
        findings = data.get("results", [])
    except json.JSONDecodeError:
        pass
    return ExternalResult("bandit", available=True, returncode=rc,
                          output=out, findings=findings)


def _run_gitleaks(root: Path) -> ExternalResult:
    if not shutil.which("gitleaks"):
        return ExternalResult("gitleaks", available=False)
    rc, out = _run(
        ["gitleaks", "detect", "--no-git", "--source", ".",
         "--report-format", "json", "--report-path", "/dev/stdout"],
        root,
    )
    findings = []
    try:
        findings = json.loads(out) if out.strip().startswith("[") else []
    except json.JSONDecodeError:
        pass
    return ExternalResult("gitleaks", available=True, returncode=rc,
                          output=out, findings=findings)


def _run_trivy(root: Path) -> ExternalResult:
    if not shutil.which("trivy"):
        return ExternalResult("trivy", available=False)
    rc, out = _run(
        ["trivy", "fs", "--quiet", "--format", "json", "."], root)
    findings = []
    try:
        data = json.loads(out)
        for result in data.get("Results", []):
            for vuln in result.get("Vulnerabilities", []) or []:
                findings.append(vuln)
    except json.JSONDecodeError:
        pass
    return ExternalResult("trivy", available=True, returncode=rc,
                          output=out, findings=findings)


def _run_pip_audit(root: Path) -> ExternalResult:
    if not shutil.which("pip-audit"):
        return ExternalResult("pip-audit", available=False)
    rc, out = _run(["pip-audit", "--format=json"], root)
    findings = []
    try:
        findings = json.loads(out)
    except json.JSONDecodeError:
        pass
    return ExternalResult("pip-audit", available=True, returncode=rc,
                          output=out, findings=findings)


def _run_npm_audit(root: Path) -> ExternalResult:
    if not shutil.which("npm"):
        return ExternalResult("npm", available=False)
    if not (root / "package-lock.json").exists():
        return ExternalResult("npm", available=False,
                              output="package-lock.json no encontrado")
    rc, out = _run(["npm", "audit", "--json"], root)
    findings = []
    try:
        findings = json.loads(out).get("vulnerabilities", [])
    except json.JSONDecodeError:
        pass
    return ExternalResult("npm", available=True, returncode=rc,
                          output=out, findings=findings)


def _run_osv_scanner(root: Path) -> ExternalResult:
    if not shutil.which("osv-scanner"):
        return ExternalResult("osv-scanner", available=False)
    rc, out = _run(
        ["osv-scanner", "--format", "json", "-r", "."], root)
    findings = []
    try:
        data = json.loads(out)
        findings = data.get("results", [])
    except json.JSONDecodeError:
        pass
    return ExternalResult("osv-scanner", available=True, returncode=rc,
                          output=out, findings=findings)


SCANNERS = {
    "semgrep": _run_semgrep,
    "bandit": _run_bandit,
    "gitleaks": _run_gitleaks,
    "trivy": _run_trivy,
    "pip-audit": _run_pip_audit,
    "npm": _run_npm_audit,
    "osv-scanner": _run_osv_scanner,
}


def run_external_scanners(root: Path,
                          requested: list[str]) -> list[ExternalResult]:
    results: list[ExternalResult] = []
    for name in requested:
        runner = SCANNERS.get(name)
        if runner is None:
            results.append(ExternalResult(name, available=False,
                                          output="desconocido"))
            continue
        results.append(runner(root))
    return results