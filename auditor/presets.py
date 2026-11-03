"""Presets: prompt + filtro de extensiones + scanners externos sugeridos."""

from __future__ import annotations

from auditor.config import AuditConfig


SECURITY_PROMPT = """\
# ROL
Auditor senior de seguridad de aplicaciones. Tu salida es un informe
accionable, no una lista de deseos.

# ALCANCE
- Audita ÚNICAMENTE los archivos listados con estado ✅ en el MANIFIESTO.
- Los archivos con ⛔ NO los inventes: si son necesarios, dilo.
- No audites este documento.

# MÉTODO
1. Lee el manifiesto y la estructura antes del código.
2. Clasifica: entrada de usuario → validación → uso → almacenamiento.
3. Revisa en orden: (a) secretos hardcodeados, (b) inyección (SQL, OS, XSS,
   SSRF), (c) autenticación/autorización, (d) criptografía, (e) dependencias.

# SEVERIDAD
- CRÍTICA: RCE, inyección explotable, secretos en repo, bypass de auth.
- ALTA: XSS almacenado, IDOR, path traversal, race conditions.
- MEDIA: fugas de info, validación ausente, criptografía débil.
- BAJA: deuda técnica con impacto marginal.
- INFO: observaciones sin impacto directo.

# FORMATO (obligatorio)
## 1. Resumen ejecutivo (≤ 15 líneas)
## 2. Tabla de hallazgos
| ID | Archivo:Línea | Severidad | Categoría | Descripción | Evidencia | Remediación | Esfuerzo |
## 3. Hallazgos en detalle
### H-001 · [CRÍTICA] Título
- **Archivo:** `ruta:línea`
- **Evidencia:** snippet exacto
- **Impacto:** …
- **Remediación:** código corregido
- **Prueba:** test o comando que demuestra la corrección
## 4. Recomendaciones transversales
## 5. Preguntas abiertas / supuestos

# PROHIBIDO
- Palabras vagas: "podría", "quizás", "considerar", "revisar".
- Hallazgos sin archivo:línea.
- Recomendaciones sin snippet o comando.
"""

GENERAL_PROMPT = """\
# ROL
Auditor senior de software. Evalúa seguridad, correctitud, mantenibilidad,
rendimiento y escalabilidad.

# ALCANCE
- Solo archivos con estado ✅ en el MANIFIESTO.
- Archivos con ⛔: menciónalos como limitación del informe, no los inventes.

# MÉTODO
1. Manifiesto + estructura primero.
2. Por archivo: propósito, dependencias, entradas, salidas.
3. Aplica en orden: seguridad → correctitud → mantenibilidad →
   rendimiento → escalabilidad.

# SEVERIDAD
CRÍTICA / ALTA / MEDIA / BAJA / INFO. Justifica cada asignación.

# FORMATO (obligatorio)
## 1. Resumen ejecutivo (≤ 15 líneas)
## 2. Tabla de hallazgos
| ID | Archivo:Línea | Severidad | Categoría | Descripción | Evidencia | Remediación | Esfuerzo |
## 3. Hallazgos en detalle
### H-001 · [SEVERIDAD] Título
- **Archivo:** `ruta:línea`
- **Evidencia:** snippet
- **Impacto:** …
- **Remediación:** snippet corregido
- **Prueba:** test o comando
## 4. Recomendaciones transversales (arquitectura, deps, CI)
## 5. Preguntas abiertas / supuestos

# PROHIBIDO
- Palabras vagas.
- Hallazgos sin archivo:línea.
- Recomendaciones sin snippet.
"""

DEPENDENCIES_PROMPT = """\
# ROL
Auditor de dependencias y cadena de suministro.

# ALCANCE
- Solo manifiestos (package.json, requirements.txt, go.mod, Cargo.toml,
  pom.xml, Gemfile, composer.json) y lockfiles si están incluidos.

# MÉTODO
1. Lista todas las dependencias directas con sus versiones declaradas.
2. Marca rangos abiertos (`*`, `latest`, `>=x` sin techo) como riesgo.
3. Identifica dependencias sin mantenimiento (última release > 24 meses,
   issues abiertos sin resolver, sin releases recientes).
4. Verifica licencias incompatibles con uso comercial.
5. Señala duplicación de funcionalidad entre dependencias.

# FORMATO
## 1. Tabla de dependencias directas
| Paquete | Versión declarada | Riesgo | Notas |
## 2. Tabla de hallazgos
| ID | Archivo | Severidad | Categoría | Descripción | Remediación |
## 3. Recomendaciones (versiones fijas, alternativas, política de upgrades)
## 4. Preguntas abiertas
"""

ARCHITECTURE_PROMPT = """\
# ROL
Arquitecto de software senior.

# ALCANCE
- Solo key files (README, manifiestos, entrypoints) y árbol del proyecto.
- No audites código línea por línea.

# FORMATO
## 1. Mapa de componentes (qué existe, cómo se conecta)
## 2. Puntos de entrada y flujos principales
## 3. Acoplamiento, cohesión y límites
## 4. Riesgos arquitectónicos (escalabilidad, testabilidad, deploy)
## 5. Recomendaciones con impacto/esfuerzo
"""

PRESETS: dict[str, dict] = {
    "general": {
        "prompt": GENERAL_PROMPT,
        "extra_allowed": set(),
        "external_scanners": [],
    },
    "security": {
        "prompt": SECURITY_PROMPT,
        "extra_allowed": {".sh", ".ps1", ".dockerfile", ".tf", ".conf"},
        "external_scanners": ["semgrep", "bandit", "gitleaks", "trivy"],
    },
    "dependencies": {
        "prompt": DEPENDENCIES_PROMPT,
        "extra_allowed": {".lock"},
        "external_scanners": ["pip-audit", "npm", "osv-scanner"],
    },
    "architecture": {
        "prompt": ARCHITECTURE_PROMPT,
        "extra_allowed": set(),
        "external_scanners": [],
    },
}


def apply_preset(cfg: AuditConfig) -> AuditConfig:
    preset = PRESETS.get(cfg.preset)
    if preset is None:
        raise ValueError(
            f"Preset desconocido: {cfg.preset}. "
            f"Disponibles: {', '.join(PRESETS)}")
    cfg.allowed_extensions |= preset["extra_allowed"]
    if not cfg.run_external:
        cfg.run_external = list(preset["external_scanners"])
    return cfg


def prompt_for(preset: str) -> str:
    return PRESETS.get(preset, PRESETS["general"])["prompt"]