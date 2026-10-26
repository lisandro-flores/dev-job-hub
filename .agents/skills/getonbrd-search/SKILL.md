---
name: getonbrd-search
description: >
  Usa este skill para buscar vacantes de tecnología y startups en LATAM y México
  a través de la API pública oficial de Get on Board (getonbrd.com). Permite
  filtrar por palabras clave (TypeScript, React, Node.js, etc.), trabajo remoto,
  país (Mexico, Chile, Colombia, Remote) y seniority (junior, semi, senior),
  incluyendo rangos salariales en USD cuando son públicos.
---

# Get on Board Job Search Skill (`getonbrd-search`)

Busca vacantes tecnológicas en startups y empresas de tecnología de Latinoamérica y México usando la API pública de **Get on Board** (`https://www.getonbrd.com/api/v0/search/jobs`) sin necesidad de cuenta ni API Key.

## Comandos del CLI

Ejecuta desde la raíz del repositorio:

```bash
# Buscar vacantes por tecnología o rol (posicional o con -q/--query)
node --no-warnings cli/search/getonbrd/src/cli.ts search "typescript" --remote --format table

# Filtrar por país (ej. Mexico) o nivel (junior, semi, senior)
node --no-warnings cli/search/getonbrd/src/cli.ts search -q "react node" --country Mexico --format table
node --no-warnings cli/search/getonbrd/src/cli.ts search "full stack" --seniority junior --per-page 30 --limit 15

# Ver el detalle completo de una vacante por su ID (slug)
node --no-warnings cli/search/getonbrd/src/cli.ts detail "software-engineer-examedi-santiago" --query "react" --format plain
```

## Opciones de `search`

| Flag | Descripción |
|---|---|
| `<query>` o `-q, --query <text>` | Palabra clave de búsqueda (default: `typescript`). |
| `--remote` | Filtra vacantes con modalidad remota (`remote: true` o `remote_modality` remoto/híbrido). |
| `--country <nombre>` | Filtra por país (`Mexico`, `Chile`, `Colombia`, etc.) e incluye vacantes 100% remotas regionales. |
| `--seniority <nivel>` | Filtra por seniority (`sin experiencia`, `junior`, `semi`, `senior`). |
| `--per-page <n>` | Resultados por página de la API (default: `30`, máx: `100`). |
| `--page <n>` | Número de página (default: `1`). |
| `-n, --limit <n>` | Limitar número de resultados mostrados. |
| `--format <json\|table\|plain>` | Formato de salida (default: `json`). |

