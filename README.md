<div align="center">

# Auditoria de Proyectos

**Pipeline de auditoría estática: empaqueta tu proyecto en Markdown + hallazgos de scanners para que cualquier LLM produzca un informe accionable.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Version](https://img.shields.io/badge/version-0.1.0-orange)
![Tests](https://img.shields.io/badge/tests-19%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## Tabla de contenidos

- [Auditoria de Proyectos](#auditoria-de-proyectos)
  - [Tabla de contenidos](#tabla-de-contenidos)
  - [¿Por qué existe?](#por-qué-existe)
  - [Características](#características)
  - [Instalación](#instalación)
    - [Scanners externos (opcionales)](#scanners-externos-opcionales)
  - [Quick start](#quick-start)
  - [Cómo funciona](#cómo-funciona)
    - [Etapas](#etapas)
  - [Uso avanzado](#uso-avanzado)
    - [Presets](#presets)
    - [Modo diff (PR review)](#modo-diff-pr-review)
    - [Presupuesto y límites](#presupuesto-y-límites)
    - [Output custom](#output-custom)
    - [Deshabilitar features](#deshabilitar-features)
  - [Referencia CLI](#referencia-cli)
  - [Formato de salida](#formato-de-salida)
  - [Configuración](#configuración)
    - [`.auditignore`](#auditignore)
    - [`audit.toml`](#audittoml)
  - [Arquitectura](#arquitectura)
  - [Decisiones de diseño](#decisiones-de-diseño)
    - [¿Por qué `<!-- CHUNK_BREAK -->` y no `##`?](#por-qué----chunk_break----y-no-)
    - [¿Por qué el render no trunca al budget?](#por-qué-el-render-no-trunca-al-budget)
    - [¿Por qué SHA-256 por archivo?](#por-qué-sha-256-por-archivo)
    - [¿Por qué output al CWD y no al proyecto auditado?](#por-qué-output-al-cwd-y-no-al-proyecto-auditado)
    - [¿Por qué redactar secretos en vez de omitirlos?](#por-qué-redactar-secretos-en-vez-de-omitirlos)
    - [¿Por qué no hay split intra-archivo?](#por-qué-no-hay-split-intra-archivo)
    - [¿Por qué 4 presets y no uno solo?](#por-qué-4-presets-y-no-uno-solo)
  - [Limitaciones conocidas](#limitaciones-conocidas)
  - [Testing](#testing)
  - [Estado y roadmap](#estado-y-roadmap)
  - [Contribuir](#contribuir)
  - [Licencia](#licencia)
  - [Autor](#autor)

> Para comandos de uso diario, flujos por escenario y troubleshooting, ver [`COMMANDS.md`](COMMANDS.md).

---

## ¿Por qué existe?

Auditar un proyecto con un LLM debería ser simple: pegás el código, la IA encuentra problemas, los arreglás. En la práctica no funciona por 4 razones concretas:

| Problema | Por qué rompe el flujo |
|---|---|
| **Contexto limitado** | Un proyecto mediano tiene 200+ archivos. La ventana del LLM (128k–200k tokens) no alcanza para todos a la vez. |
| **Sin metadata** | Cuando pegás código suelto, la IA no sabe qué archivos incluyó, cuáles faltan, ni puede referenciar `archivo:línea` con precisión. |
| **Detección desde cero** | El LLM gasta todo su presupuesto en "encontrar" vulnerabilidades que `semgrep` ya detecta en 2 segundos. |
| **Fuga de secretos** | Si tu proyecto tiene una API key en un `.env` mal versionado, esa key termina en el historial del chat. |

`auditor` resuelve los 4:

1. **Chunking coherente** → divide el proyecto en `.md` ≤ presupuesto configurable, **sin romper bloques de código**.
2. **Manifiesto con SHA-256** → la IA sabe exactamente qué se incluyó, qué se omitió y por qué.
3. **Orquestación de scanners** → `semgrep`, `bandit`, `gitleaks`, `trivy` aportan hallazgos reales que el LLM solo clasifica.
4. **Detección + redacción de secretos** → regex sobre 12 patrones; se redacta antes de renderizar.

El resultado es un `.md` (o varios) que le pasás a cualquier IA, pidiéndole un informe estructurado con hallazgos accionables y referencias `archivo:línea`.

---

## Características

- **Recorrido respetuoso del repo**: honra `.gitignore` y un `.auditignore` propio; excluye `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/` y binarios.
- **Detección de secretos con redacción**: 12 patrones (AWS, GitHub, GitLab, Slack, Stripe, Google, JWT, claves privadas, strings de conexión, API keys/passwords genéricos). Se reportan **redactados** (`AKIA***...`).
- **SHA-256 de cada archivo**: el consumidor puede verificar integridad y detectar cambios entre runs.
- **Chunking por separador semántico**: usa `<!-- CHUNK_BREAK -->` en vez de headers `##`, así no rompe archivos `.md` auditados con headers internos.
- **Presets por dominio**: `general`, `security`, `dependencies`, `architecture`. Cada uno ajusta extensiones, prompt y scanners externos.
- **Modo diff**: `--since origin/main` audita solo los archivos cambiados. Ideal para PR reviews.
- **Orquestación de scanners**: ejecuta `semgrep`, `bandit`, `gitleaks`, `trivy`, `pip-audit`, `npm audit` y `osv-scanner` si están instalados; degrada con elegancia si no.
- **Metadatos de git**: commit, rama y estado del working tree en el manifiesto.
- **Sin efectos secundarios**: el proyecto auditado nunca se modifica. La salida va al CWD (configurable).
- **Testeado**: 19 tests cubriendo scanner, chunker, secretos, renderer y CLI.

---

## Instalación

**Requisitos:** Python 3.11+ y `git` (opcional, para metadatos y modo diff).

```bash
git clone https://github.com/AleyCabreraD/auditoria-proyectos.git
cd auditoria-proyectos

python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash)
# source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -e ".[dev]"

auditor --version     # → auditor 0.1.0
pytest -q             # → 19 passed
```

### Scanners externos (opcionales)

`auditor` funciona sin ellos, pero con ellos el informe mejora mucho.

```bash
# Python (los más importantes)
pip install semgrep bandit

# Binarios del sistema
scoop install gitleaks trivy        # Windows con scoop
brew install gitleaks trivy         # macOS / Linux
```

---

## Quick start

```bash
# 1. Dry run: ver qué se va a incluir
auditor "D:/RUTA/AL/PROYECTO" --list-files

# 2. Auditar
auditor "D:/RUTA/AL/PROYECTO" --preset security
```

**Salida:**

```text
./audit-output/auditoria.md      (o auditoria_01.md, _02.md, ... si se dividió)
./audit-output/MANIFEST.json     (metadatos + hashes + secretos)
```

**3. Pasale el resultado a una IA** (Claude, ChatGPT, Gemini...) adjuntando `auditoria*.md` junto con este prompt:

```text
Lee el archivo adjunto completo. Es el resultado de una auditoría de código.
Produce el informe siguiendo EXACTAMENTE la sección "FORMATO (obligatorio)"
del documento.

Requisitos:
- Cada hallazgo debe tener archivo:línea exactos
- Severidad justificada (CRÍTICA / ALTA / MEDIA / BAJA / INFO)
- Evidencia: snippet exacto del código
- Remediación: código corregido, no descripción
- Sin palabras vagas ("podría", "quizás", "considerar")
```

Si hay varios chunks, adjuntalos en orden y agregá: *"Los archivos están divididos por tamaño, no por tema. Léelos todos antes de responder."*

> ⚠️ **Verificá siempre los snippets** del informe contra el código real: los LLM pueden alucinar hallazgos.

---

## Cómo funciona

```text
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌────────────────┐
│   scan()      │──▶│   secrets     │──▶│   render()    │──▶│   chunk()      │
│               │   │               │   │               │   │                │
│ • os.walk     │   │ • 12 regex    │   │ • prompt      │   │ • split por    │
│ • .gitignore  │   │ • filtro de   │   │ • manifiesto  │   │   SEPARATOR    │
│ • .auditignore│   │   placeholders│   │ • estructura  │   │ • ≤ budget     │
│ • binary sniff│   │ • redacción   │   │ • code blocks │   │ • limpieza de  │
│ • SHA-256     │   │               │   │   + SHA-256   │   │   huérfanos    │
└───────────────┘   └───────────────┘   └───────────────┘   └───────┬────────┘
                                                                    │
                                                                    ▼
                                                        ┌────────────────────────┐
                                                        │  audit-output/         │
                                                        │  ├── auditoria_01.md   │
                                                        │  ├── auditoria_02.md   │
                                                        │  └── MANIFEST.json     │
                                                        └────────────────────────┘
```

### Etapas

| Etapa | Qué hace |
|---|---|
| `scan()` | Recorre el proyecto con `os.walk`. Aplica filtros: `.gitignore`, `.auditignore`, extensiones permitidas, binarios y tamaño máximo. Calcula SHA-256. Devuelve `FileRecord[]` con contenido y secretos ya escaneados. |
| `scan_secrets()` | Regex sobre cada archivo. Descarta placeholders conocidos (`your_*`, `changeme`, `****`). Reporta `SecretHit[line, rule, matched, redacted]`. El contenido original queda intacto en memoria; la redacción se aplica en el render. |
| `render()` | Escribe en orden: prompt de auditoría (del preset), manifiesto (archivos + SHA-256 + secretos + scanners externos), estructura en árbol y cada archivo envuelto en un code fence con su hash. Emite `<!-- CHUNK_BREAK -->` entre archivos. |
| `write_chunked()` | Si el render total ≤ `max_total_mb`, genera un solo `auditoria.md`. Si no, divide por `CHUNK_SEPARATOR` y emite `auditoria_01.md`, `_02.md`, etc. Limpia chunks huérfanos de runs anteriores. Si un archivo individual excede el budget, va solo y se emite un warning. |
| `write_manifest_json()` | Genera `MANIFEST.json` con proyecto, preset, metadatos de git, lista de chunks y todos los archivos con `path` / `language` / `size` / `sha256` / `skipped_reason` / `secret_hits`. |

---

## Uso avanzado

### Presets

| Preset | Extensiones extra | Scanners externos | Enfoque del prompt |
|---|---|---|---|
| `general` | — | — | Auditoría completa (seguridad + calidad + performance) |
| `security` | `.sh`, `.ps1`, `.dockerfile`, `.tf`, `.conf` | semgrep, bandit, gitleaks, trivy | Secretos, inyección, auth, cripto, dependencias |
| `dependencies` | `.lock` | pip-audit, npm, osv-scanner | Supply chain, versiones, licencias |
| `architecture` | — | — | Mapa de componentes, acoplamiento, deuda |

```bash
auditor . --preset security
auditor . --preset dependencies
auditor . --preset architecture
```

### Modo diff (PR review)

```bash
cd "D:/RUTA/AL/PROYECTO"
auditor . --since origin/main --preset security --quiet
```

Solo incluye archivos cambiados desde `origin/main`. Salida típica: 2–8 archivos en vez de 200.

### Presupuesto y límites

```bash
# Presupuesto total del documento (acepta decimales)
auditor . --max-total-mb 0.05        # 50 KB → muchos chunks chicos
auditor . --max-total-mb 8           # 8 MB (default)

# Límite por archivo individual
auditor . --max-file-kb 100          # omite archivos sueltos > 100 KB
```

### Output custom

```bash
auditor . --output-dir /tmp/audit-custom
```

### Deshabilitar features

```bash
auditor . --no-gitignore    # no leer .gitignore
auditor . --no-secrets      # no escanear secretos
auditor . --no-redact       # NO redactar secretos (¡cuidado! quedan en el .md)
auditor . --no-hash         # no calcular SHA-256 (más rápido)
```

---

## Referencia CLI

```bash
auditor [path] [opciones]
```

| Flag | Default | Descripción |
|---|---|---|
| `path` | `.` | Ruta del proyecto a auditar |
| `--preset {general,security,dependencies,architecture}` | `general` | Perfil de auditoría |
| `--output-dir DIR` | `./audit-output` (CWD) | Directorio de salida |
| `--since REF` | — | Solo archivos cambiados desde `REF` (requiere git) |
| `--list-files` | — | Dry run: listar archivos sin generar output |
| `--max-file-kb N` | `300` | Omitir archivos individuales > N KB |
| `--max-total-mb N` | `8` | Presupuesto total (acepta float: `0.05`) |
| `--external "semgrep,bandit"` | según preset | Scanners externos custom |
| `--no-gitignore` | — | Ignorar `.gitignore` del proyecto |
| `--no-secrets` | — | No escanear secretos |
| `--no-redact` | — | No redactar secretos (peligroso) |
| `--no-hash` | — | No calcular SHA-256 |
| `--config FILE` | — | Configuración TOML alternativa |
| `--quiet` | — | Ocultar logs de progreso |
| `--version`, `-h` | — | Versión / ayuda |

**Códigos de salida:** `0` éxito · `1` ruta inexistente · `2` ref git inválido.

---

## Formato de salida

Cada `auditoria_NN.md` tiene esta estructura:

````markdown
# DOCUMENTO DE AUDITORÍA — <proyecto>

# ROL
Auditor senior de seguridad...

# ALCANCE
- Audita ÚNICAMENTE los archivos con estado ✅ en el MANIFIESTO.
- Los archivos con ⛔ NO los inventes...

# MÉTODO
1. Lee el manifiesto y la estructura antes del código.
...

# FORMATO (obligatorio)
## 1. Resumen ejecutivo (≤ 15 líneas)
## 2. Tabla de hallazgos
| ID | Archivo:Línea | Severidad | Categoría | Descripción | Evidencia | Remediación | Esfuerzo |
...

---

# MANIFIESTO DE AUDITORÍA

**Proyecto:** `proyecto-de-vida-personal`
**Generado:** 2026-11-02T20:20:15+00:00
**Preset:** `security`
**Commit:** `35741f6`  **Rama:** `develop`
**Archivos incluidos:** 18  **Omitidos:** 2

| Archivo      | Lenguaje   | KB   | SHA-256 (12)   | Secretos | Estado |
| ------------ | ---------- | ---- | -------------- | -------- | ------ |
| `README.md`  | Markdown   | 0.1  | `1e9690fd1ce7` | —        | ✅     |
| `js/main.js` | JavaScript | 12.4 | `333119c15df6` | —        | ✅     |
...

## Secretos detectados (redactados)

| Archivo:Línea | Regla               | Extracto                             |
| ------------- | ------------------- | ------------------------------------ |
| `config.js:4` | `connection_string` | `post****************************3@` |

## Scanners externos

- **semgrep:** 3 hallazgo(s), exit=1
- **bandit:** 0 hallazgo(s), exit=0
- **gitleaks:** no instalado (omitido)

---

# ESTRUCTURA

    proyecto/
        README.md
        index.html
        css/
            styles.css
        js/
            main.js

# HALLAZGOS DE SCANNERS EXTERNOS

## semgrep
    [{ "check_id": "...", "path": "js/main.js", "start": { "line": 120 }, ... }]

# CONTENIDO DE LOS ARCHIVOS

## js/main.js
Lenguaje: JavaScript · SHA-256: 333119c15df6

    // ... código completo ...
````

`MANIFEST.json` es la contraparte parseable:

```json
{
  "project": "proyecto-de-vida-personal",
  "preset": "security",
  "git": { "commit": "35741f6", "branch": "develop", "dirty": "yes" },
  "chunks": ["auditoria_01.md"],
  "files": [
    {
      "path": "js/main.js",
      "language": "JavaScript",
      "size_bytes": 12700,
      "sha256": "333119c15df6...",
      "skipped_reason": null,
      "secret_hits": []
    }
  ]
}
```

---

## Configuración

### `.auditignore`

Crealo en la raíz del **proyecto auditado** (no del tool). Sintaxis idéntica a `.gitignore`:

```gitignore
# Outputs generados
output/
dist/
build/
coverage/
*.min.js
*.min.css

# Tests y fixtures (solo si NO querés auditarlos)
tests/
fixtures/
*.test.js
*.spec.ts

# Docs (si querés enfocarte en código)
docs/
*.md
!README.md

# Vendor y dependencias
vendor/
node_modules/
third_party/

# Assets visuales
assets/
img/
```

Verificá con `auditor . --list-files` que la lista se reduce.

### `audit.toml`

Configuración persistente, alternativa a los flags:

```toml
project_path = "."
output_dir = "./audit-output"
preset = "security"
use_gitignore = true
respect_auditignore = true
max_file_kb = 300
max_total_mb = 8
hash_files = true
scan_secrets = true
redact_secrets = true
```

```bash
auditor --config audit.toml
```

---

## Arquitectura

```text
auditoria-proyectos/                # repo (nombre histórico)
├── auditor/                        # paquete Python "auditor"
│   ├── __init__.py                 # __version__
│   ├── __main__.py                 # permite `python -m auditor`
│   ├── cli.py                      # argparse + orquestación
│   ├── config.py                   # AuditConfig (dataclass) + TOML
│   ├── filters.py                  # .gitignore / .auditignore / binarios
│   ├── languages.py                # extensión → fence válido
│   ├── scanner.py                  # os.walk + SHA-256 + FileRecord
│   ├── secrets.py                  # 12 regex + redacción
│   ├── git_info.py                 # commit / rama / dirty / changed_since
│   ├── presets.py                  # 4 presets + prompts
│   ├── external.py                 # semgrep / bandit / gitleaks / trivy / ...
│   ├── renderer.py                 # manifiesto + estructura + contenido
│   ├── chunker.py                  # split + limpieza + MANIFEST.json
│   └── prompts/
│       └── general.md
├── tests/                          # 19 tests (pytest)
│   ├── test_scanner.py
│   ├── test_secrets.py
│   ├── test_renderer.py
│   └── test_chunker.py
├── sample_project/                 # proyecto de ejemplo con bugs deliberados
├── audit-output/                   # salida por defecto (gitignored)
├── COMMANDS.md                     # comandos de uso diario
├── README.md
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

> **Nota sobre nombres:** el repo se llama `auditoria-proyectos` por razones históricas. El paquete Python y el comando CLI son `auditor` (más corto y fácil de tipear). `pyproject.toml` declara `auditor` como nombre del proyecto, así que `pip install -e .` expone `auditor` como entrypoint.

---

## Decisiones de diseño

### ¿Por qué `<!-- CHUNK_BREAK -->` y no `##`?

Los headers de nivel 2 (`##`) son ubicuos: cualquier `.md` auditado los contiene, y el propio renderer los emite para cada archivo. Si el chunker dividiera por `##`, un `.md` de 300 KB con 50 headers internos generaría 50 chunks falsos.

La solución es un separador único, `<!-- CHUNK_BREAK -->`, que solo emite el renderer. El chunker divide exclusivamente por él y los headers internos del contenido auditado quedan intactos.

### ¿Por qué el render no trunca al budget?

En versiones tempranas, `render()` omitía archivos al superar el budget. Resultado: el chunker recibía un render ya recortado y nunca se activaba; el presupuesto era código muerto.

Hoy `render()` produce el contenido completo y `write_chunked()` decide cómo repartirlo. El render produce, el chunker distribuye.

### ¿Por qué SHA-256 por archivo?

1. **Integridad:** el consumidor puede hashear el archivo en su repo y comparar.
2. **Diff entre runs:** si el hash de `main.js` cambió, se modificó aunque el tamaño sea igual.
3. **Referencia estable:** si dos reportes de IA citan "el mismo archivo", se puede verificar que es el mismo contenido.

### ¿Por qué output al CWD y no al proyecto auditado?

Auditar no debe modificar el target. Escribir ahí:

- Contamina el working tree (`git status` muestra `audit-output/` untracked).
- Falla si el target es read-only (network share, permisos).
- Rompe el principio "read-only target", fundamental para la confianza.
- Es impredecible: la ruta depende del input, no del usuario.

`--output-dir` permite override explícito.

### ¿Por qué redactar secretos en vez de omitirlos?

Omitir pierde información: el consumidor no sabe qué archivos tienen secretos ni de qué tipo. Redactar preserva el contexto (`aws_access_key` en `config.py:4`) sin exponer el valor. `MANIFEST.json` incluye la lista completa, redactada.

`--no-redact` existe para casos controlados (auditoría offline), pero el default es el seguro.

### ¿Por qué no hay split intra-archivo?

Un archivo individual mayor a `max_total_mb` se emite solo, con warning. Partirlo por líneas crearía código roto (funciones truncadas, imports faltantes). La solución correcta es `.auditignore` o `--max-file-kb`, no el split.

### ¿Por qué 4 presets y no uno solo?

Cada dominio tiene distintas extensiones relevantes (`dependencies` solo mira manifiestos), distinto prompt (seguridad prioriza inyección; arquitectura, acoplamiento) y distintos scanners (`security` corre semgrep; `dependencies` corre pip-audit). Un solo preset obligaría a comprometer; cuatro permiten foco.

---

## Limitaciones conocidas

Siendo honesto sobre el estado v0.1:

| Limitación | Impacto | Workaround |
|---|---|---|
| Archivos individuales > `max_total_mb` no se parten | El chunk puede exceder el budget, con warning | `--max-file-kb` o `.auditignore` |
| Secretos por regex, no por entropía | Falsos negativos con formatos custom | Agregar regex en `secrets.py` |
| Detección de binarios por byte nulo | Falsos positivos en archivos UTF-16 | Fallback de encoding (utf-8, utf-16, latin-1) |
| Sin integración CI nativa | Requiere wrapper custom | Ver [roadmap](#estado-y-roadmap) |
| Sin caching entre runs | Re-escanea todo cada vez | `--since` mitiga |
| Prompts de los presets solo en español | No localizado a otros idiomas | Fácil de traducir |
| Sin sanitización de `--external` | Los comandos corren con el shell del usuario | Usar solo scanners de confianza |

---

## Testing

```bash
pytest -q                          # 19 passed
pytest -v                          # verbose con nombres
pytest tests/test_chunker.py -v    # solo chunker
```

| Módulo | Tests | Qué verifica |
|---|---|---|
| `scanner.py` | 3 | Filtros, binarios, auto-exclusión del output |
| `secrets.py` | 4 | Detección (AWS, clave privada), placeholders, redacción |
| `renderer.py` | 2 | Manifiesto, estructura, no-drop por budget |
| `chunker.py` | 6 | Split, no-split en fences, round-trip, budget float, limpieza |
| CLI | 4 | Default al CWD, exclusión mutua de flags y demás casos de uso |

**Proyecto de ejemplo:** `sample_project/` tiene 4 archivos con bugs deliberados (SQL injection, XSS, path traversal, `eval`, secretos hardcodeados). Útil para verificar que la herramienta detecta lo que debe.

---

## Estado y roadmap

**Versión actual: 0.1.0**, funcional, testeada y lista para uso personal.

- [x] Scanner con `.gitignore` / `.auditignore`
- [x] Detección y redacción de secretos
- [x] Manifiesto con SHA-256
- [x] Chunking por separador semántico
- [x] Presets (`general`, `security`, `dependencies`, `architecture`)
- [x] Orquestación de scanners externos
- [x] Modo diff (`--since`)
- [x] Output al CWD (target read-only)
- [ ] GitHub Action para PRs
- [ ] Pre-commit hook
- [ ] `--timestamp` para historial de runs
- [ ] `--format json` completo (para integraciones)
- [ ] Caching entre runs (por SHA-256)
- [ ] Split intra-archivo opcional para `.md` gigantes
- [ ] Detección de secretos por entropía (Shannon)
- [ ] Reporte HTML además de Markdown

**Feedback:** si encontrás un caso de uso que no cubre, abrí un issue con el proyecto de ejemplo.

---

## Contribuir

Contribuciones bienvenidas. Guía rápida:

1. Fork del repo.
2. Branch descriptivo: `feature/<nombre>` o `fix/<nombre>`.
3. Tests para cualquier cambio funcional.
4. Sin dependencias nuevas sin justificación (el proyecto depende solo de `pathspec`).
5. Commits en formato [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`).
6. PR con descripción del problema, la solución y el impacto.

**Áreas donde la ayuda es más valiosa:**

- Nuevos patrones de secretos (con regex y test).
- Nuevos presets (`mobile`, `data`, `ml`).
- Integraciones CI (GitHub Actions, GitLab CI, pre-commit).
- Traducción de presets a inglés.

**Antes de abrir un PR:**

```bash
pytest -q                        # todos verdes
auditor . --preset security      # el self-audit no se rompe
```

---

## Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE). Podés usar, modificar y distribuir libremente, incluso comercialmente, siempre que conserves el aviso de copyright.

---

## Autor

**Aley Cabrera D.**

- GitHub: [@AleyCabreraD](https://github.com/AleyCabreraD)
- LinkedIn: Aley Cabrera D.
- Email: aley.cabrera@gmail.com

Construido como herramienta para auditar proyectos personales antes de un deploy o un PR. Si te sirve, contame en qué la usás.

<div align="center">

¿Encontraste un bug? [Abrí un issue](../../issues).
¿La usás en producción? Contame, me interesa.

</div>
