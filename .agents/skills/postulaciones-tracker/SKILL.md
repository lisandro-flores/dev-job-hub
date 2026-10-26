---
name: postulaciones-tracker
version: 1.0.0
description: >
  Usa este skill para revisar recordatorios de seguimiento vencidos o próximos en
  SEGUIMIENTO_POSTULACIONES.csv (equivalente a /outcome followup), analizar las
  tecnologías más demandadas en las vacantes registradas (equivalente a /upskill)
  o regenerar el dashboard HTML offline de postulaciones (equivalente a /html-report).
---

# Postulaciones Tracker Skill (`dev-job-hub`)

Herramienta local inspirada en `/outcome followup`, `/upskill` y `/html-report` de `ai-job-search`, conectada directamente a `SEGUIMIENTO_POSTULACIONES.csv` y `ofertas/*.md`.

## Comandos

### 1. Revisar seguimientos pendientes y próximos (`followup`)

```bash
python3 cli/tracker/tracker.py followup --days 7
```

Opciones:
- `--days <n>`: ventana de días hacia adelante (por defecto `7`).
- `--format text|json`: salida legible o JSON estructurado.

### 2. Mapa de calor de tecnologías demandadas (`skills`)

```bash
python3 cli/tracker/tracker.py skills
```

Analiza `SEGUIMIENTO_POSTULACIONES.csv` y todas las fichas en `ofertas/*.md` para mostrar qué tecnologías se repiten más en tu embudo actual.

### 3. Generar Dashboard HTML offline (`report`)

```bash
python3 cli/tracker/tracker.py report
```

Genera `postulaciones/dashboard_postulaciones.html` (autocontenido, sin dependencias externas, con buscador y checklists interactivos).

### 4. Generar Guía de Estudio Móvil / PWA sanitizada (`study_site.py`)

```bash
python3 cli/tracker/study_site.py
```

Genera `sitio_estudio/index.html` junto con `manifest.webmanifest`, `sw.js` e íconos PNG instalables, listo para subir a Cloudflare Pages, Netlify Drop, Vercel o GitHub Pages sin exponer datos privados de postulaciones.

### 5. Servidor local interactivo (`server.ts`)

```bash
node --no-warnings cli/tracker/server.ts
```

Sirve tanto el Centro de Mando (`http://localhost:4321/postulaciones/dashboard_postulaciones.html`) como la PWA de estudio (`http://localhost:4321/sitio_estudio/index.html`) y sincroniza en disco los checkboxes marcados (`POST /api/toggle-check`).

### 6. Desplegar a GitHub Pages (`scripts/deploy_ghpages.sh`)

```bash
# Publicar a rama gh-pages del repo actual
./scripts/deploy_ghpages.sh
```

Publica únicamente los archivos de `sitio_estudio/` sin historial previo ni datos privados.
