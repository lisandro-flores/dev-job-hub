#!/usr/bin/env bash
# Despliegue de la PWA de estudio y Centro de Mando a GitHub Pages.
#
# Uso:
#   ./scripts/deploy_ghpages.sh
#       -> Despliega a la rama 'gh-pages' del repositorio actual (origin).
#
#   ./scripts/deploy_ghpages.sh https://github.com/<usuario>/<repo>.git
#       -> Despliega a un repositorio remoto específico.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STUDY_DIR="$SCRIPT_DIR/sitio_estudio"
STUDY_PY="$SCRIPT_DIR/cli/tracker/study_site.py"
TRACKER_PY="$SCRIPT_DIR/cli/tracker/tracker.py"
DASHBOARD_HTML="$SCRIPT_DIR/postulaciones/dashboard_postulaciones.html"

TARGET_REMOTE="${1:-origin}"
TARGET_BRANCH="gh-pages"

echo "=== 1. Regenerando componentes (guia de estudio y panel cifrado) ==="
python3 "$STUDY_PY"
python3 "$TRACKER_PY" report

if [ ! -f "$STUDY_DIR/index.html" ] || [ ! -f "$DASHBOARD_HTML" ]; then
  echo "Error: no se generaron los archivos requeridos" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d /tmp/dev-job-hub-ghpages-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== 2. Preparando artefacto aislado ==="
cp -R "$STUDY_DIR"/* "$TMP_DIR/"
cp -R "$STUDY_DIR"/.[!.]* "$TMP_DIR/" 2>/dev/null || true

mv "$TMP_DIR/index.html" "$TMP_DIR/estudio.html"
cp "$DASHBOARD_HTML" "$TMP_DIR/index.html"

sed -i 's|\.\./sitio_estudio/index\.html|\./estudio\.html|g' "$TMP_DIR/index.html"

touch "$TMP_DIR/.nojekyll"

echo "=== 3. Publicando en la rama $TARGET_BRANCH de $TARGET_REMOTE ==="
cd "$TMP_DIR"
git init -b "$TARGET_BRANCH"
git config user.name "dev-job-hub-deployer"
git config user.email "deployer@devjobhub.local"
git add .
git commit -m "deploy: actualizar Centro de Mando y PWA de estudio [$(date +'%Y-%m-%d %H:%M')]"

git push --force "$TARGET_REMOTE" "$TARGET_BRANCH"

echo "=== Despliegue completado exitosamente ==="
