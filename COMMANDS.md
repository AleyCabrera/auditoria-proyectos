# Auditor — Comandos de uso diario

**Proyecto:** auditor v0.1  
**Ubicación del tool:** `D:/Project/Python/auditoria-proyectos/`  
**Output por defecto:** `./audit-output/` (en el CWD, NO en el proyecto auditado)

---

## 0. Setup — cada vez que abrís una terminal nueva

```bash
cd /d/Project/Python/auditoria-proyectos
source .venv/Scripts/activate

# Verificación rápida (10 segundos)
auditor --version          # → auditor 0.1.0
pytest -q                  # → 19 passed
```

Si `auditor --version` falla: no estás en el venv. Repetí `source .venv/Scripts/activate`.

---

## 1. Los 5 comandos que vas a usar el 90% del tiempo

### 1.1 Ver qué va a incluir (dry run)

```bash
auditor "D:/RUTA/AL/PROYECTO" --list-files
```

**Cuándo:** siempre antes de auditar. Confirma que la lista sea la esperada.

### 1.2 Auditar todo el proyecto (seguridad)

```bash
auditor "D:/RUTA/AL/PROYECTO" --preset security
```

**Cuándo:** deploy, PR importante, revisión antes de compartir código.

### 1.3 Auditar todo el proyecto (visión general)

```bash
auditor "D:/RUTA/AL/PROYECTO" --preset general
```

**Cuándo:** primera auditoría, onboarding, visión holística.

### 1.4 Auditar solo los archivos que cambiaste

```bash
cd "D:/RUTA/AL/PROYECTO"
auditor . --since origin/main --preset security
```

**Cuándo:** antes de cada PR. 10x más rápido y relevante.

### 1.5 Auditar con budget custom (proyectos grandes)

```bash
auditor "D:/RUTA/AL/PROYECTO" --preset security --max-total-mb 8
```

**Cuándo:** >200 archivos o >5 MB de código. Genera 2-4 chunks en vez de 1 gigante.

---

## 2. Proyectos reales que auditás

| Proyecto                         | Comando                                                                   |
| -------------------------------- | ------------------------------------------------------------------------- |
| proyecto-de-vida-personal        | `auditor "D:/Project/Web/proyecto-de-vida-personal" --preset security`    |
| auditoria_basica_proyectos       | `auditor "D:/Project/Python/auditoria_basica_proyectos" --preset general` |
| auditoria-proyectos (self-audit) | `cd /d/Project/Python/auditoria-proyectos && auditor . --preset security` |
| Cualquier repo git               | `cd /ruta && auditor . --since origin/main --preset security`             |

---

## 3. Flujo completo end-to-end (5 pasos)

### Paso 1 — Dry run

```bash
auditor "D:/RUTA/AL/PROYECTO" --list-files
```

Revisá que la lista tenga:

- ✅ Los archivos que querés auditar
- ❌ NO `node_modules/`, `.venv/`, `dist/`, `build/`, `output/`

Si hay ruido → creá `.auditignore` (sección 4).

### Paso 2 — Auditar

```bash
auditor "D:/RUTA/AL/PROYECTO" --preset security --quiet
```

`--quiet` oculta logs de progreso. Quitalo si querés ver qué está pasando.

### Paso 3 — Verificar el output

```bash
ls -lh audit-output/

# ¿Qué archivos auditó?
python -c "
import json
d = json.load(open('audit-output/MANIFEST.json'))
print(f\"Proyecto: {d['project']}\")
print(f\"Chunks: {d['chunks']}\")
print(f\"Archivos: {len(d['files'])}\")
print('Secretos:', sum(len(f['secret_hits']) for f in d['files']))
"
```

### Paso 4 — Pasar a la IA

**Si es 1 chunk** (`audit-output/auditoria.md`):

1. Abrí Claude/ChatGPT/Gemini
2. Adjuntá `audit-output/auditoria.md`
3. Pegá el prompt:

```text
Lee el archivo adjunto completo. Es el resultado de una auditoría de código.

Produce el informe siguiendo EXACTAMENTE la sección "FORMATO (obligatorio)"
del documento.

Requisitos:
- Cada hallazgo debe tener archivo:línea exactos
- Severidad justificada (CRÍTICA/ALTA/MEDIA/BAJA/INFO)
- Evidencia: snippet exacto del código
- Remediación: código corregido, no descripción
- Sin palabras vagas ("podría", "quizás", "considerar")
```

**Si son varios chunks** (`audit-output/auditoria_01.md`, `_02.md`, ...):

Adjuntalos todos en orden y agregá al prompt:

> "Los archivos están divididos por tamaño, no por tema. Léelos todos antes de responder."

### Paso 5 — Actuar sobre el informe

1. Tomá los hallazgos **CRÍTICA** y **ALTA**
2. Por cada uno: issue → PR → fix → re-auditar con `--since`
3. Repetir hasta que no queden CRÍTICAS

---

## 4. `.auditignore` — excluir archivos del análisis

Crear en la raíz del **proyecto auditado** (no del tool):

```bash
cd "D:/RUTA/AL/PROYECTO"
cat > .auditignore <<'EOF'
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

# Docs (solo si querés enfocarte en código)
docs/
*.md
!README.md

# Vendor / dependencias
vendor/
node_modules/
third_party/

# Assets visuales
assets/
img/
*.png
*.jpg
*.svg
EOF
```

Sintaxis idéntica a `.gitignore`:

- `carpeta/` → excluye la carpeta
- `*.ext` → excluye por extensión
- `!patrón` → excepción (incluye aunque otro patrón lo excluya)

**Verificar:** `auditor . --list-files` debe mostrar menos archivos.

---

## 5. Presets — cuál usar cuándo

| Preset         | Qué audita                                                            | Cuándo usarlo                                    |
| -------------- | --------------------------------------------------------------------- | ------------------------------------------------ |
| `security`     | Seguridad: secretos, inyección, auth, crypto, deps                    | **Default diario.** Antes de deploy, PR sensible |
| `general`      | Todo: seguridad + correctitud + mantenibilidad + perf + escalabilidad | Primera auditoría, visión holística              |
| `dependencies` | Solo manifiestos (`requirements.txt`, `package.json`, `go.mod`, etc.) | Actualizar deps, auditoría de supply chain       |
| `architecture` | Solo entrypoints + árbol (sin código línea por línea)                 | Onboarding, evaluar deuda arquitectónica         |

**Regla:** empezá con `security`, después `general`. Los otros dos son para casos específicos.

---

## 6. Verificación del output (siempre después de auditar)

```bash
# Tamaño de chunks
ls -lh audit-output/

# Metadata completa
python -c "
import json
d = json.load(open('audit-output/MANIFEST.json'))
print(f\"Proyecto: {d['project']}\")
print(f\"Preset: {d['preset']}\")
print(f\"Commit: {d.get('git', {}).get('commit', 'n/a')}\")
print(f\"Rama: {d.get('git', {}).get('branch', 'n/a')}\")
print(f\"Chunks: {d['chunks']}\")
print(f\"Archivos: {len(d['files'])}\")
print()
print('=== Archivos omitidos ===')
for f in d['files']:
    if f['skipped_reason']:
        print(f\"  {f['path']} → {f['skipped_reason']}\")
print()
print('=== Secretos detectados ===')
hits = [(f['path'], h) for f in d['files'] for h in f['secret_hits']]
if not hits:
    print('  Ninguno ✓')
for path, h in hits:
    print(f\"  {path}:{h['line']} → {h['rule']} ({h['redacted']})\")
"
```

**Qué verificar:**

| Check                      | Esperado                                        |
| -------------------------- | ----------------------------------------------- |
| Chunks                     | Coincide con `ls audit-output/auditoria*.md`    |
| Archivos omitidos          | Solo los que vos excluiste + binarios + >300 KB |
| Secretos                   | Vacío, o redactados (`AKIA***...`)              |
| `audit-output/` en `files` | NO debe aparecer. Bug si aparece → reportar     |

---

## 7. Troubleshooting

| Síntoma                              | Causa                                       | Fix                                              |
| ------------------------------------ | ------------------------------------------- | ------------------------------------------------ |
| `auditor: command not found`         | No estás en el venv                         | `source .venv/Scripts/activate`                  |
| `Incluidos: 0`                       | Ruta mal escrita, o `.auditignore` agresivo | `--list-files` para debug                        |
| `Chunk 01 (500 KB) excede el budget` | Archivo individual > `max-total-mb`         | `--max-file-kb 100` o `.auditignore`             |
| `semgrep: no instalado`              | No instalado (opcional)                     | `pip install semgrep`                            |
| `gitleaks/trivy: no instalado`       | Son binarios, no pip                        | Ignorar (opcionales) o instalar con scoop/winget |
| Output va al proyecto auditado       | Bug (ya arreglado)                          | Verificar `pwd` y `--output-dir`                 |
| La IA no sigue el formato            | Prompt no aplicado                          | Repetir prompt en mensaje nuevo                  |
| Hallazgos inventados por la IA       | Modelo alucinó                              | Reforzar: "solo lo que está en el manifiesto"    |
| Chunk huérfano de run anterior       | Bug (arreglado con Fix A)                   | Borrar `audit-output/*` y re-correr              |

---

## 8. Referencia rápida de flags

```bash
auditor [path] [opciones]

# Posicional
path                          Ruta del proyecto (default: .)

# Salida
--output-dir DIR              Output custom (default: ./audit-output en CWD)
--quiet                       Sin logs de progreso

# Contenido
--preset {general,security,dependencies,architecture}
--since REF                   Solo archivos cambiados desde REF (ej: origin/main)
--list-files                  Dry run: solo listar archivos
--max-file-kb N               Omitir archivos individuales > N KB (default: 300)
--max-total-mb N              Budget total del documento (default: 8, acepta float: 0.05)
--external LISTA              Scanners custom: "semgrep,bandit" (default según preset)

# Filtros
--no-gitignore                Ignorar .gitignore del proyecto
--no-secrets                  No escanear secretos
--no-redact                   No redactar secretos (¡cuidado!)
--no-hash                     No calcular SHA-256

# Config
--config FILE                 TOML custom
--version                     Versión del tool
-h, --help                    Ayuda completa
```

---

## 9. Alias útiles (agregar a `~/.bashrc`)

```bash
# Activar venv + ir al proyecto
alias aud='cd /d/Project/Python/auditoria-proyectos && source .venv/Scripts/activate'

# Auditar CWD con security
alias aud-sec='auditor . --preset security'

# Auditar solo cambios
alias aud-diff='auditor . --since origin/main --preset security'

# Ver último manifest (función: evita problemas de comillas anidadas)
aud-last() {
  python -c "import json; d=json.load(open('audit-output/MANIFEST.json')); print(d['project'], '-', len(d['files']), 'archivos,', d['chunks'], 'chunks')"
}
```

Después:

```bash
aud                      # activar
aud-sec                  # auditar CWD
aud-diff                 # auditar diff
aud-last                 # ver último manifest
```

Para agregar solo el alias principal de una vez:

```bash
echo 'alias aud="cd /d/Project/Python/auditoria-proyectos && source .venv/Scripts/activate"' >> ~/.bashrc
source ~/.bashrc
```

---

## 10. Flujos por escenario

### Escenario A — "Antes de un PR"

```bash
cd "D:/RUTA/AL/PROYECTO"
auditor . --since origin/main --preset security --quiet
ls -lh audit-output/
# Pasar audit-output/auditoria*.md a la IA
```

### Escenario B — "Deploy a producción"

```bash
cd "D:/RUTA/AL/PROYECTO"
auditor . --preset security --max-total-mb 8
# Revisar sección HALLAZGOS DE SCANNERS EXTERNOS
# Si hay CRÍTICAS → NO deployar
```

### Escenario C — "Auditoría mensual completa"

```bash
cd "D:/RUTA/AL/PROYECTO"
auditor . --preset general --max-total-mb 8
# Pasar a Claude/ChatGPT con el prompt de §3 Paso 4
# Guardar el informe resultante en docs/audits/YYYY-MM.md
```

### Escenario D — "Onboarding a un proyecto desconocido"

```bash
# 1. Ver estructura sin código
auditor "D:/RUTA/NUEVO" --preset architecture
# 2. Después seguridad
auditor "D:/RUTA/NUEVO" --preset security
# 3. Después general
auditor "D:/RUTA/NUEVO" --preset general --max-total-mb 8
```

### Escenario E — "Auditar N proyectos en batch"

```bash
cd /d/Project/Python/auditoria-proyectos
for proj in \
    "D:/Project/Web/proyecto-de-vida-personal" \
    "D:/Project/Python/auditoria_basica_proyectos" \
    "D:/Project/Python/auditoria-proyectos"
do
    name=$(basename "$proj")
    auditor "$proj" --preset security --output-dir "audit-output/$name" --quiet
    echo "✓ $name"
done
```

---

## 11. Qué NO hacer

| ❌                                                               | Por qué                                    |
| --------------------------------------------------------------- | ------------------------------------------ |
| Auditar `node_modules/` o `.venv/`                              | 95% ruido. Ya excluidos por default        |
| Pegar 10 chunks de 500 KB a una IA sin avisar                   | Excede ventana de contexto                 |
| Confiar en el informe sin verificar snippets                    | La IA puede alucinar                       |
| Ignorar scanners externos                                       | Con semgrep+bandit el informe es 10x mejor |
| Ignorar gitleaks/trivy si tu proyecto tiene Docker/deps grandes | CVEs en supply chain son críticas          |
| Usar `--no-redact` en producción                                | Los secretos quedan en el `.md`            |

---

## 12. Cheatsheet de 1 minuto

```bash
# Setup
cd /d/Project/Python/auditoria-proyectos && source .venv/Scripts/activate

# Dry run
auditor "D:/RUTA/AL/PROYECTO" --list-files

# Auditar
auditor "D:/RUTA/AL/PROYECTO" --preset security

# Solo cambios
cd "D:/RUTA/AL/PROYECTO" && auditor . --since origin/main --preset security

# Verificar
ls -lh audit-output/

# Pasar a IA
# → Adjuntar audit-output/auditoria*.md + prompt
```

---

*Última actualización: 2026-11-02*  
*Versión del tool: 0.1.0*  
*Tests: 19 passing*