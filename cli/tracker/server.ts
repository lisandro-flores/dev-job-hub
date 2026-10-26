#!/usr/bin/env node
/**
 * Servidor local en TypeScript + Node.js para el Centro de Mando de Búsqueda de Empleo.
 * Ejecución: node --no-warnings .agents/skills/postulaciones-tracker/cli/server.ts
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
function findRootDir(): string {
  if (process.env.DEV_JOB_HUB_ROOT) return path.resolve(process.env.DEV_JOB_HUB_ROOT);
  let current = __dirname;
  for (let i = 0; i < 5; i++) {
    if (
      fs.existsSync(path.join(current, "SEGUIMIENTO_POSTULACIONES.csv")) ||
      fs.existsSync(path.join(current, "SEGUIMIENTO.template.csv")) ||
      fs.existsSync(path.join(current, "package.json")) ||
      fs.existsSync(path.join(current, ".git"))
    ) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return path.resolve(__dirname, "../..");
}

const ROOT_DIR = findRootDir();
const TRACKER_PY = path.join(__dirname, "tracker.py");
const STUDY_SITE_PY = path.join(__dirname, "study_site.py");
const DASHBOARD_HTML = path.join(ROOT_DIR, "postulaciones", "dashboard_postulaciones.html");
const PORT = Number(process.env.PORT || 4321);

const MIME_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".pdf": "application/pdf",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".md": "text/markdown; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
};

function regenerateDashboard(): void {
  execFileSync("python3", [TRACKER_PY, "report"], { cwd: ROOT_DIR, stdio: "ignore" });
  if (fs.existsSync(STUDY_SITE_PY)) {
    execFileSync("python3", [STUDY_SITE_PY], { cwd: ROOT_DIR, stdio: "ignore" });
  }
}

const server = http.createServer((req, res) => {
  try {
    const rawUrl = (req.url || "/").split("?")[0];
    const decodedPath = decodeURIComponent(rawUrl);

    if (req.method === "POST" && decodedPath === "/api/toggle-check") {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        try {
          const payload = JSON.parse(body || "{}");
          const safeFile = path.basename(String(payload.filename || ""));
          const lineIdx = Number(payload.lineIdx);
          const checked = Boolean(payload.checked);

          const candidateDirs = [path.join(ROOT_DIR, "notas"), path.join(ROOT_DIR, "ofertas")];
          let targetMd = "";
          for (const dir of candidateDirs) {
            const full = path.join(dir, safeFile);
            if (fs.existsSync(full)) {
              targetMd = full;
              break;
            }
          }

          if (targetMd && Number.isInteger(lineIdx) && lineIdx >= 0) {
            const lines = fs.readFileSync(targetMd, "utf-8").replace(/\r\n/g, "\n").split("\n");
            if (lineIdx < lines.length) {
              lines[lineIdx] = lines[lineIdx].replace(
                /^(\s*[-*]\s+\[)[ xX](\]\s+)/,
                `$1${checked ? "x" : " "}$2`
              );
              fs.writeFileSync(targetMd, lines.join("\n"), "utf-8");
              regenerateDashboard();
            }
          }
          res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
          res.end(JSON.stringify({ ok: true }));
        } catch (e) {
          res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" });
          res.end(JSON.stringify({ ok: false }));
        }
      });
      return;
    }

    if (decodedPath === "/" || decodedPath === "/postulaciones/dashboard_postulaciones.html") {
      regenerateDashboard();
      const htmlContent = fs.readFileSync(DASHBOARD_HTML, "utf-8");
      res.writeHead(200, { "Content-Type": MIME_TYPES[".html"] });
      res.end(htmlContent);
      return;
    }

    const cleanRel = decodedPath.replace(/^\/+/, "");
    let targetPath = path.resolve(ROOT_DIR, cleanRel);
    if (fs.existsSync(targetPath) && fs.statSync(targetPath).isDirectory()) {
      targetPath = path.join(targetPath, "index.html");
    }

    if (!targetPath.startsWith(ROOT_DIR) || !fs.existsSync(targetPath) || fs.statSync(targetPath).isDirectory()) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Recurso no encontrado");
      return;
    }

    const ext = path.extname(targetPath).toLowerCase();
    const mime = MIME_TYPES[ext] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": mime });
    fs.createReadStream(targetPath).pipe(res);
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(`Error interno: ${err instanceof Error ? err.message : String(err)}`);
  }
});

regenerateDashboard();
server.listen(PORT, "0.0.0.0", () => {
  console.log(`[OK] Centro de Mando activo en: http://localhost:${PORT}/postulaciones/dashboard_postulaciones.html`);
  console.log(`[OK] Guía Móvil / PWA activa en: http://localhost:${PORT}/sitio_estudio/index.html`);
  console.log(`[OK] Archivo estático: ${DASHBOARD_HTML}`);
});
