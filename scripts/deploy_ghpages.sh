#!/usr/bin/env bash
# Despliegue de la PWA de estudio y, opcionalmente, del Centro de Mando cifrado.
#
# Uso:
#   ./scripts/deploy_ghpages.sh [remote]
#       -> Publica solo la PWA de estudio (seguro por defecto).
#
#   DASHBOARD_PASSWORD='...' ./scripts/deploy_ghpages.sh --include-dashboard [remote]
#       -> Publica también el dashboard, siempre cifrado.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STUDY_DIR="$SCRIPT_DIR/sitio_estudio"
STUDY_PY="$SCRIPT_DIR/cli/tracker/study_site.py"
TRACKER_PY="$SCRIPT_DIR/cli/tracker/tracker.py"
DASHBOARD_HTML="$SCRIPT_DIR/postulaciones/dashboard_postulaciones.html"

TARGET_REMOTE="${1:-origin}"
TARGET_BRANCH="gh-pages"
INCLUDE_DASHBOARD="false"

if [ "${1:-}" = "--include-dashboard" ]; then
  INCLUDE_DASHBOARD="true"
  TARGET_REMOTE="${2:-origin}"
fi

if [ "$INCLUDE_DASHBOARD" = "true" ] && [ -z "${DASHBOARD_PASSWORD:-}" ]; then
  echo "Error: --include-dashboard requiere DASHBOARD_PASSWORD; no se publicará un dashboard sin cifrar." >&2
  exit 1
fi

echo "=== 1. Regenerando la guia de estudio ==="
python3 "$STUDY_PY"
if [ ! -f "$STUDY_DIR/index.html" ]; then
  echo "Error: no se genero la guia de estudio" >&2
  exit 1
fi

if [ "$INCLUDE_DASHBOARD" = "true" ]; then
  echo "=== 2. Generando dashboard cifrado ==="
  python3 "$TRACKER_PY" report --password "$DASHBOARD_PASSWORD"
  if [ ! -f "$DASHBOARD_HTML" ]; then
    echo "Error: no se genero el dashboard" >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d /tmp/dev-job-hub-ghpages-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== 3. Preparando artefacto aislado ==="
cp -R "$STUDY_DIR"/* "$TMP_DIR/"
cp -R "$STUDY_DIR"/.[!.]* "$TMP_DIR/" 2>/dev/null || true

if [ "$INCLUDE_DASHBOARD" = "true" ]; then
  mv "$TMP_DIR/index.html" "$TMP_DIR/estudio.html"
  cp "$DASHBOARD_HTML" "$TMP_DIR/index.html"
  sed -i 's|\.\./postulaciones/dashboard_postulaciones\.html|\./index\.html|g' "$TMP_DIR/estudio.html"
  sed -i 's|\.\./sitio_estudio/index\.html|\./estudio\.html|g' "$TMP_DIR/index.html"
else
  sed -i '/class="top-dash-link"/d' "$TMP_DIR/index.html"
fi

touch "$TMP_DIR/.nojekyll"

echo "=== 4. Publicando en la rama $TARGET_BRANCH de $TARGET_REMOTE ==="
cd "$TMP_DIR"
git init -b "$TARGET_BRANCH"
git config user.name "dev-job-hub-deployer"
git config user.email "deployer@devjobhub.local"
git add .
git commit -m "deploy: actualizar Centro de Mando y PWA de estudio [$(date +'%Y-%m-%d %H:%M')]"

git push --force "$TARGET_REMOTE" "$TARGET_BRANCH"

echo "=== Despliegue completado exitosamente ==="
