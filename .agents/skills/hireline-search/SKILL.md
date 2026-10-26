---
name: hireline-search
description: >
  Usa este skill para buscar vacantes de tecnología en México y remoto LATAM en
  Hireline.io (la bolsa de empleo TI #1 de México). Permite filtrar por palabras
  clave (React, TypeScript, Node.js, Angular, Full Stack), ubicación (remoto,
  puebla, ciudad-de-mexico, queretaro, jalisco, nuevo-leon o todo México) y
  consultar la descripción completa de cualquier vacante.
---

# Hireline Mexico Tech Job Search Skill (`hireline-search`)

Busca vacantes de desarrollo de software y TI en México a través de **Hireline.io** (`https://hireline.io/mx/empleos`) y extrae el detalle completo de cada oferta.

## Comandos del CLI

Ejecuta desde la raíz del repositorio:

```bash
# Buscar vacantes remotas en México por tecnología (tabla o JSON)
node --no-warnings cli/search/hireline/src/cli.ts search "react" --location remoto --format table

# Buscar vacantes en todo México o por estado (soporta posicional o -q/--query)
node --no-warnings cli/search/hireline/src/cli.ts search -q "typescript" -l puebla --limit 10 --format table

# Ver la descripción completa de una vacante usando su URL de Hireline
node --no-warnings cli/search/hireline/src/cli.ts detail "https://hireline.io/remoto/empleos/full-stack-engineer-react-nodejs-typescript-postgresql-saas/114880" --format plain
```

## Opciones de `search`

| Flag | Descripción |
|---|---|
| `<keyword>` o `-q, --query <text>` | Palabra clave de búsqueda (ej. `react`, `typescript`, `nestjs`). |
| `-l, --location <slug>` | Ubicación en Hireline: `remoto`, `puebla`, `ciudad-de-mexico`, `queretaro`, `jalisco`, `nuevo-leon`, `usa` o vacío (`""`, default: todo México). |
| `--date <1\|2\|3>` | Antigüedad máxima: `1` (hace 2 semanas), `2` (hace 1 mes), `3` (hace 2 meses). |
| `--page <n>` | Número de página (default: `1`). |
| `-n, --limit <n>` | Limitar número de resultados devueltos. |
| `--format <json\|table\|plain>` | Formato de salida (default: `json`). |

