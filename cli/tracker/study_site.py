#!/usr/bin/env python3
"""Genera `sitio_estudio/`: sitio estático (PWA) para estudiar desde el móvil.

Toma SOLO las notas de estudio (notas/PLAN_ESTUDIO_POSTULACIONES.md y
notas/PLAN_CERTIFICACIONES.md), elimina datos de postulaciones (sueldos,
reclutadores, enlaces de reuniones) y verifica que no se filtren antes de
escribir los archivos. No toca el dashboard privado ni el CSV.

Uso:
    python3 .agents/skills/postulaciones-tracker/cli/study_site.py
    python3 .agents/skills/postulaciones-tracker/cli/study_site.py --out /ruta/salida
"""
import argparse
import datetime
import hashlib
import html
import os
import re
import shutil
import sys

def find_root_dir():
    env_root = os.environ.get("DEV_JOB_HUB_ROOT")
    if env_root and os.path.isdir(env_root):
        return os.path.abspath(env_root)
    current = os.path.abspath(os.path.dirname(__file__))
    for _ in range(5):
        if any(os.path.exists(os.path.join(current, marker)) for marker in ["SEGUIMIENTO_POSTULACIONES.csv", "SEGUIMIENTO.template.csv", "package.json", ".git"]):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = find_root_dir()
NOTAS = os.path.join(ROOT, "notas")
ASSETS = os.path.join(HERE, "study_site_assets")
DEFAULT_OUT = os.path.join(ROOT, "sitio_estudio")

DEFAULT_DOCS = [
    {"id": "plan", "file": "PLAN_ESTUDIO.md", "tab": "Plan de Estudio"},
    {"id": "agenda", "file": "ROADMAP_ACTIVIDADES_OCTUBRE.md", "tab": "Roadmap Diario"},
    {"id": "cert", "file": "PLAN_CERTIFICACIONES.md", "tab": "Certificaciones"},
]

# Líneas que describen el avance de una postulación y no material de estudio.
DROP_LINE = re.compile(
    r"Participantes|Postulación enviada|Filtro RH|netos|vales de|tracker\.py|lisandroflores",
    re.I,
)
# Patrones que, si aparecen en el resultado final, detienen la construcción.
LEAK_PATTERNS = {
    "correo": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "enlace de reunión": re.compile(r"teams\.microsoft|meet\.google|zoom\.us", re.I),
    "teléfono": re.compile(r"(?<!\d)\d{10}(?!\d)"),
    "sueldo": re.compile(r"\$\s?\d{2,3},\d{3}|\$\s?\d{2,3}\s?k\b", re.I),
    "persona de contacto": re.compile(r"Natalia|Monarrez|Franco-Ibo|Karen Mondragon|Luz Garc", re.I),
    "ruta interna": re.compile(r"/home/|SEGUIMIENTO_POSTULACIONES|information\.json"),
}

EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]|[\u2600-\u27bf\ufe0f]")
LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
CHECK_RE = re.compile(r"^\[([ xX])\]\s+(.*)$")
HEAD_RE = re.compile(r"^(#{1,4})\s+(.*)$")
SEP_CELL_RE = re.compile(r"^:?-{2,}:?$")

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

ICON_EXT = (
    '<svg class="ext" viewBox="0 0 24 24" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
)
ICON_TICK = '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>'
ICON_CHEV = '<svg class="i chev" viewBox="0 0 24 24" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg>'


def esc(text, quote=False):
    return html.escape(text, quote=quote)


class Renderer:
    """Convierte el subconjunto de Markdown usado en las notas a HTML."""

    def __init__(self, doc_id, doc_file=""):
        self.doc_id = doc_id
        self.doc_file = doc_file
        self.ids = set()
        self.task_count = 0

    # ---------- Inline ----------
    def inline(self, text):
        stash = []

        def keep(fragment):
            stash.append(fragment)
            return "\x00%d\x00" % (len(stash) - 1)

        text = esc(text)
        text = re.sub(r"`([^`]+)`", lambda m: keep("<code>%s</code>" % m.group(1)), text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", text)

        def link(m):
            return keep(
                '<a class="res" href="%s" target="_blank" rel="noopener noreferrer">%s%s</a>'
                % (m.group(2), m.group(1), ICON_EXT)
            )

        text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", link, text)

        def bare(m):
            url = m.group(0)
            trail = ""
            while url and url[-1] in ".,;:)":
                trail = url[-1] + trail
                url = url[:-1]
            return keep(
                '<a class="res" href="%s" target="_blank" rel="noopener noreferrer">%s%s</a>' % (url, url, ICON_EXT)
            ) + trail

        text = re.sub(r"https?://[^\s<>\x00]+", bare, text)

        while "\x00" in text:
            text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
        return text

    # ---------- Bloques auxiliares ----------
    def quote(self, qlines):
        paras, buf = [], []
        for line in qlines:
            if line.strip() == "":
                if buf:
                    paras.append(buf)
                    buf = []
            else:
                buf.append(line.strip())
        if buf:
            paras.append(buf)
        cls = ""
        if paras:
            m = re.match(r"^\[!(\w+)\]\s*(.*)$", " ".join(paras[0]))
            if m:
                cls = ' class="callout"'
                paras[0] = [m.group(2)] if m.group(2) else []
                paras = [p for p in paras if p]
        body = "".join("<p>%s</p>" % self.inline(" ".join(p)) for p in paras)
        return "<blockquote%s>%s</blockquote>" % (cls, body)

    def table(self, rows):
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        header = cells[0]
        body = cells[1:]
        if body and all(SEP_CELL_RE.match(c) for c in body[0] if c):
            body = body[1:]
        out = ['<div class="tbl-scroll"><table><thead><tr>']
        out += ["<th>%s</th>" % self.inline(h) for h in header]
        out.append("</tr></thead><tbody>")
        for row in body:
            row = (row + [""] * len(header))[: len(header)]
            out.append("<tr>")
            for label, cell in zip(header, row):
                out.append('<td data-label="%s">%s</td>' % (esc(re.sub(r"[*`]", "", label), True), self.inline(cell)))
            out.append("</tr>")
        out.append("</tbody></table></div>")
        return "".join(out)

    def task_id(self, text):
        norm = re.sub(r"\s+", " ", text).strip().lower()
        base = "k" + hashlib.sha1(("%s|%s" % (self.doc_id, norm)).encode("utf-8")).hexdigest()[:9]
        tid, n = base, 1
        while tid in self.ids:
            n += 1
            tid = "%s%d" % (base, n)
        self.ids.add(tid)
        return tid

    # ---------- Listas ----------
    def list_block(self, lines):
        items = []
        for line in lines:
            if not line.strip():
                continue
            m = LIST_RE.match(line)
            if m:
                items.append({"indent": len(m.group(1).expandtabs(4)), "marker": m.group(2), "text": m.group(3), "extra": [], "kids": []})
            elif items:
                items[-1]["extra"].append(line.strip())
        root, stack = [], []
        for it in items:
            while stack and stack[-1]["indent"] >= it["indent"]:
                stack.pop()
            (stack[-1]["kids"] if stack else root).append(it)
            stack.append(it)
        return self.render_items(root)

    def extra_html(self, extra):
        out, qbuf, pbuf = [], [], []

        def flush():
            if qbuf:
                out.append(self.quote([re.sub(r"^>\s?", "", q) for q in qbuf]))
                qbuf.clear()
            if pbuf:
                out.append("<p>%s</p>" % self.inline(" ".join(pbuf)))
                pbuf.clear()

        for line in extra:
            if line.startswith(">"):
                if pbuf:
                    flush()
                qbuf.append(line)
            else:
                if qbuf:
                    flush()
                pbuf.append(line)
        flush()
        return "".join(out)

    def render_items(self, items):
        if not items:
            return ""
        ordered = items[0]["marker"] not in ("-", "*")
        tag = "ol" if ordered else "ul"
        has_task = any(CHECK_RE.match(i["text"]) for i in items)
        out = ["<%s%s>" % (tag, ' class="tasks"' if has_task else "")]
        for it in items:
            extra = self.extra_html(it["extra"])
            kids = self.render_items(it["kids"])
            m = CHECK_RE.match(it["text"])
            if m:
                default = m.group(1).lower() == "x"
                tid = self.task_id(m.group(2))
                sync_key = "%s::%s" % (self.doc_file, re.sub(r"\s+", " ", m.group(2)).strip()[:100])
                self.task_count += 1
                out.append(
                    '<li class="task" id="t-%s"><div class="task-card"><label class="task-row">'
                    '<input type="checkbox" class="task-check visually-hidden" data-id="%s" data-sync-key="%s" data-default="%d"%s>'
                    '<span class="box" aria-hidden="true">%s</span><span class="task-text">%s</span></label>%s%s</div></li>'
                    % (tid, tid, esc(sync_key, True), int(default), " checked" if default else "", ICON_TICK, self.inline(m.group(2)), extra, kids)
                )
            else:
                out.append("<li>%s%s%s</li>" % (self.inline(it["text"]), extra, kids))
        out.append("</%s>" % tag)
        return "".join(out)

    # ---------- Documento ----------
    def parse(self, lines):
        title = ""
        intro = []
        sections = []
        current = {"parts": intro, "title": None, "t0": 0}

        def close():
            if current["title"] is not None:
                sections.append({"title": current["title"], "html": "".join(current["parts"]), "tasks": self.task_count - current["t0"]})

        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            if stripped.startswith("```"):
                j = i + 1
                code = []
                while j < n and not lines[j].strip().startswith("```"):
                    code.append(lines[j])
                    j += 1
                current["parts"].append("<pre><code>%s</code></pre>" % esc("\n".join(code)))
                i = j + 1
                continue
            hm = HEAD_RE.match(line)
            if hm:
                level, text = len(hm.group(1)), hm.group(2).strip()
                if level == 1:
                    title = re.sub(r"[*`]", "", text)
                elif level == 2:
                    close()
                    current = {"parts": [], "title": re.sub(r"[*`]", "", text), "t0": self.task_count}
                else:
                    current["parts"].append("<h%d>%s</h%d>" % (level, self.inline(text), level))
                i += 1
                continue
            if re.match(r"^-{3,}$", stripped):
                i += 1
                continue
            if stripped.startswith("|"):
                rows = []
                while i < n and lines[i].strip().startswith("|"):
                    rows.append(lines[i])
                    i += 1
                current["parts"].append(self.table(rows))
                continue
            if stripped.startswith(">"):
                q = []
                while i < n and lines[i].strip().startswith(">"):
                    q.append(re.sub(r"^\s*>\s?", "", lines[i]))
                    i += 1
                current["parts"].append(self.quote(q))
                continue
            if LIST_RE.match(line):
                block = []
                while i < n:
                    cur = lines[i]
                    if cur.strip() == "":
                        k = i + 1
                        while k < n and lines[k].strip() == "":
                            k += 1
                        if k < n and (LIST_RE.match(lines[k]) or lines[k].startswith("  ")):
                            i = k
                            continue
                        break
                    if LIST_RE.match(cur) or cur.startswith("  "):
                        block.append(cur)
                        i += 1
                        continue
                    break
                current["parts"].append(self.list_block(block))
                continue
            para = []
            while i < n and lines[i].strip() and not (
                HEAD_RE.match(lines[i]) or lines[i].strip().startswith(("```", "|", ">")) or LIST_RE.match(lines[i])
            ):
                para.append(lines[i].strip())
                i += 1
            current["parts"].append("<p>%s</p>" % self.inline(" ".join(para)))
        close()
        return title, "".join(intro), sections


def sanitize(text):
    """Quita emojis, el bloque de metadatos tras el H1 y líneas de seguimiento."""
    text = EMOJI_RE.sub("", text).replace("\r\n", "\n")
    lines = text.split("\n")
    out, removed = [], []
    after_h1 = False
    dropping_meta = False
    for line in lines:
        if line.startswith("# ") and not after_h1:
            after_h1 = True
            out.append(line)
            continue
        if after_h1 and not dropping_meta and line.startswith(">") and not line.startswith("> [!"):
            dropping_meta = True
        if dropping_meta:
            if line.startswith(">"):
                removed.append(line)
                continue
            dropping_meta = False
            after_h1 = False
        elif after_h1 and line.strip():
            after_h1 = False
        if DROP_LINE.search(line):
            removed.append(line)
            continue
        out.append(line)
    return "\n".join(out), removed


def build_doc_html(doc, title, intro, sections, today):
    out = ['<article class="doc" id="doc-%s" data-doc="%s" hidden>' % (doc["id"], doc["id"])]
    out.append('<header class="doc-head"><h1>%s</h1><p class="doc-sub">Actualizado el %s</p>' % (esc(title), today))
    out.append('<div class="doc-progress"><div class="bar"><span class="fill"></span></div><span class="doc-pct">0%</span></div></header>')
    if intro.strip():
        out.append('<div class="doc-intro">%s</div>' % intro)
    for idx, sec in enumerate(sections, 1):
        open_attr = ' open data-open-default="1"' if (doc["id"] in ("plan", "ngicaja") and idx in (1, 2, 3)) else ""
        out.append(
            '<details class="sec" id="%s-s%d"%s><summary>%s<span class="sec-title">%s</span><span class="sec-count" hidden></span></summary>'
            '<div class="sec-body">%s</div></details>' % (doc["id"], idx, open_attr, ICON_CHEV, esc(sec["title"]), sec["html"])
        )
    out.append("</article>")
    return "".join(out)


INDEX_TEMPLATE = """<!doctype html>
<html lang="es" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Plan de estudio</title>
<meta name="description" content="Plan de estudio personal con recursos oficiales y lista de avance.">
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="theme-color" content="#0b1020" id="meta-theme">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Estudio">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="stylesheet" href="styles.css">
<script src="theme.js"></script>
</head>
<body data-filter="all">
<a class="skip" href="#main">Saltar al contenido</a>

<header class="topbar">
  <button class="icon-btn" id="btn-menu" type="button" aria-label="Abrir menú" aria-controls="drawer" aria-expanded="false">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
  </button>
  <div class="brand"><strong>Plan de estudio</strong><span id="top-doc"></span></div>
  <button class="icon-btn" id="btn-top-search" type="button" data-action="toggle-search" aria-label="Buscar en guía" aria-expanded="false">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
  </button>
  <a href="./index.html" class="top-dash-link">📊 Dashboard</a>
  <span class="global-chip" title="Avance total"><svg class="i" viewBox="0 0 24 24" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg><span id="global-pct">0%</span></span>
</header>

<nav class="tabs" aria-label="Documentos">__TABS__</nav>

<div class="search-bar" id="search-bar" hidden>
  <div class="search-inner">
    <svg class="i search-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="search" id="q-study" class="search-input" placeholder="Buscar concepto, SQL, NgiCaja, Redis, guion..." autocomplete="off" aria-label="Buscar en el plan de estudio">
    <span class="search-count" id="search-count" hidden>0</span>
    <button class="icon-btn search-clear" type="button" data-action="clear-search" aria-label="Cerrar búsqueda">
      <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
</div>

<div class="scrim" id="scrim" hidden></div>
<aside class="drawer" id="drawer" aria-label="Menú">
  <div class="drawer-head">
    <strong>Menú</strong>
    <button class="icon-btn" id="btn-close" type="button" aria-label="Cerrar menú">
      <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
  <h2>Secciones</h2>
  <ul class="toc" id="toc"></ul>
  <h2>Mostrar</h2>
  <div class="seg" role="group" aria-label="Filtro de tareas">
    <button class="btn" type="button" data-filter-btn="all" aria-pressed="true">Todos</button>
    <button class="btn" type="button" data-filter-btn="pending" aria-pressed="false">Pendientes</button>
    <button class="btn" type="button" data-filter-btn="done" aria-pressed="false">Hechos</button>
  </div>
  <h2>Práctica de entrevista</h2>
  <div class="tools">
    <button class="btn" type="button" data-action="toggle-recall" id="drawer-recall-btn" aria-pressed="false">👁️ Modo Memoria (Ocultar guiones)</button>
    <button class="btn" type="button" data-action="toggle-timer" id="drawer-timer-btn">⏱️ Cronómetro de Pitch + Pantalla activa</button>
  </div>
  <h2>Herramientas</h2>
  <div class="tools">
    <div class="row">
      <button class="btn" type="button" data-action="smaller" aria-label="Reducir texto">A&minus;</button>
      <button class="btn" type="button" data-action="bigger" aria-label="Aumentar texto">A+</button>
    </div>
    <button class="btn" type="button" data-action="theme" id="theme-label">Tema: Automático</button>
    <div class="row">
      <button class="btn" type="button" data-action="expand">Expandir todo</button>
      <button class="btn" type="button" data-action="collapse">Contraer todo</button>
    </div>
    <button class="btn" type="button" data-action="sync">Respaldar o restaurar progreso</button>
    <button class="btn" type="button" data-action="reset-doc">Reiniciar este documento</button>
    <a class="btn drawer-dash-link" href="./index.html">📊 Ir al Centro de Mando</a>
  </div>
</aside>

<main id="main" class="container">
__DOCS__
</main>

<div class="timer-bar" id="timer-bar" role="region" aria-label="Cronómetro de práctica" hidden>
  <div class="timer-main">
    <span class="timer-dot" id="timer-dot"></span>
    <strong class="timer-clock" id="timer-clock">00:00</strong>
    <span class="timer-hint" id="timer-hint">Meta: 60s–90s</span>
    <span class="wake-badge" id="wake-badge" hidden title="La pantalla no se apagará mientras practicas">🔆 Activa</span>
  </div>
  <div class="timer-actions">
    <button class="timer-btn" type="button" data-action="timer-play" id="timer-play-btn">Pausar</button>
    <button class="timer-btn" type="button" data-action="timer-reset">00:00</button>
    <button class="timer-btn" type="button" data-action="timer-close" aria-label="Cerrar cronómetro">✕</button>
  </div>
</div>

<button class="fab" type="button" data-action="next">
  <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
  <span>Siguiente pendiente</span>
</button>

<nav class="bottom-nav" aria-label="Navegación rápida móvil">
  <button class="bnav-btn" type="button" data-nav-doc="plan">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/></svg>
    <span>ALPRO</span>
  </button>
  <button class="bnav-btn" type="button" data-nav-doc="ngicaja">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 9l9-6 9 6v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    <span>NgiCaja/CV</span>
  </button>
  <button class="bnav-btn" type="button" data-action="toggle-recall" id="bnav-recall" aria-pressed="false">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
    <span>Memoria</span>
  </button>
  <button class="bnav-btn" type="button" data-action="toggle-timer" id="bnav-timer" aria-pressed="false">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="13" r="8"/><polyline points="12 9 12 13 15 15"/><line x1="9" y1="2" x2="15" y2="2"/></svg>
    <span id="bnav-timer-label">Reloj</span>
  </button>
  <button class="bnav-btn" type="button" data-action="toggle-search" id="bnav-search" aria-pressed="false">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <span>Buscar</span>
  </button>
</nav>

<div class="toast" id="toast" role="status" aria-live="polite" hidden></div>

<dialog id="dlg-sync" aria-labelledby="dlg-title">
  <h2 id="dlg-title">Respaldar o restaurar progreso</h2>
  <p>El avance se guarda solo en este dispositivo. Copia este código y pégalo en otro dispositivo para continuar ahí.</p>
  <textarea id="sync-text" spellcheck="false" aria-label="Código de progreso"></textarea>
  <div class="dlg-actions">
    <button class="btn primary" type="button" data-action="copy">Copiar</button>
    <button class="btn" type="button" data-action="import">Restaurar desde el texto</button>
    <button class="btn" type="button" data-action="close-dialog">Cerrar</button>
  </div>
</dialog>

<script src="app.js" defer></script>
</body>
</html>
"""

MANIFEST = """{
  "name": "Plan de estudio",
  "short_name": "Estudio",
  "description": "Plan de estudio con recursos oficiales y lista de avance.",
  "lang": "es",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#0b1020",
  "theme_color": "#0b1020",
  "icons": [
    {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    {"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
"""

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="112" fill="#0f172a"/>
<circle cx="256" cy="256" r="150" fill="none" stroke="#4cc3ff" stroke-width="16"/>
<polyline points="190,262 240,312 330,208" fill="none" stroke="#3ddc97" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

PAGES_WORKFLOW = """name: Publicar en GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - id: deployment
        uses: actions/deploy-pages@v4
"""

README = """# Plan de estudio (sitio estático PWA)

Sitio de lectura y avance para estudiar desde el móvil. Es HTML, CSS y JavaScript
sin dependencias; funciona sin conexión una vez visitado (PWA) y no usa servidores.

Este directorio se genera desde `notas/` con:

    python3 .agents/skills/postulaciones-tracker/cli/study_site.py

No edites estos archivos a mano: se sobrescriben en cada generación.

## Despliegue en GitHub Pages

### Opción 1: Comando automatizado (rama gh-pages)
Desde la raíz del repositorio ejecuta:

    ./desplegar_estudio_ghpages.sh

O hacia un repositorio público dedicado:

    ./desplegar_estudio_ghpages.sh https://github.com/lisandro-flores/plan-estudio.git

### Opción 2: GitHub Actions
Si este repositorio está en GitHub, el archivo `.github/workflows/deploy-estudio.yml`
publica automáticamente cada cambio en `sitio_estudio/` o notas cuando haces push a `main`.
Solo activa GitHub Pages en **Settings -> Pages -> Source: GitHub Actions**.
"""


def write(path, content, binary=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as fh:
        fh.write(content)


def make_icons(out_dir):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Aviso: Pillow no está instalado; se omiten los iconos PNG.", file=sys.stderr)
        return False

    def render(size, maskable):
        s = size * 4
        img = Image.new("RGBA", (s, s), (15, 23, 42, 255))
        d = ImageDraw.Draw(img)
        scale = 0.78 if maskable else 1.0
        cx = cy = s / 2
        r = s * 0.29 * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(76, 195, 255, 255), width=int(s * 0.032 * scale))
        pts = [(cx - r * 0.42, cy + r * 0.04), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.46, cy - r * 0.34)]
        d.line(pts, fill=(61, 220, 151, 255), width=int(s * 0.066 * scale), joint="curve")
        for x, y in (pts[0], pts[-1]):
            rr = s * 0.033 * scale
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(61, 220, 151, 255))
        img = img.resize((size, size), Image.LANCZOS)
        if not maskable and size != 180:
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255)
            img.putalpha(mask)
        return img

    icons = os.path.join(out_dir, "icons")
    os.makedirs(icons, exist_ok=True)
    render(192, False).save(os.path.join(icons, "icon-192.png"))
    render(512, False).save(os.path.join(icons, "icon-512.png"))
    render(512, True).save(os.path.join(icons, "maskable-512.png"))
    render(180, True).save(os.path.join(icons, "apple-touch-icon.png"))
    return True


def clean_output(out_dir):
    """Vacía el directorio de salida conservando un repositorio .git existente."""
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
        return
    for name in os.listdir(out_dir):
        if name == ".git":
            continue
        path = os.path.join(out_dir, name)
        shutil.rmtree(path) if os.path.isdir(path) and not os.path.islink(path) else os.remove(path)


def main():
    parser = argparse.ArgumentParser(description="Genera el sitio de estudio (PWA estática).")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Directorio de salida (default: sitio_estudio/)")
    args = parser.parse_args()
    out_dir = os.path.abspath(args.out)

    now = datetime.datetime.now()
    today = "%d %s %d" % (now.day, MESES[now.month - 1], now.year)

    docs_to_render = []
    if os.path.isdir(NOTAS):
        seen_files = set()
        for doc in DEFAULT_DOCS:
            if os.path.isfile(os.path.join(NOTAS, doc["file"])):
                docs_to_render.append(doc)
                seen_files.add(doc["file"])
        for fname in sorted(os.listdir(NOTAS)):
            if fname.endswith(".md") and fname not in seen_files:
                doc_id = re.sub(r"[^a-zA-Z0-9_-]", "", os.path.splitext(fname)[0].lower()) or "doc"
                tab_title = os.path.splitext(fname)[0].replace("_", " ").title()
                docs_to_render.append({"id": doc_id, "file": fname, "tab": tab_title})
                seen_files.add(fname)

    if not docs_to_render:
        print("No se encontraron notas en notas/. Agrega archivos Markdown en notas/ para generar el sitio.", file=sys.stderr)
        return 1

    rendered, tab_html, doc_html, removed_total = [], [], [], 0
    for doc in docs_to_render:
        path = os.path.join(NOTAS, doc["file"])
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text, removed = sanitize(fh.read())
        removed_total += len(removed)
        renderer = Renderer(doc["id"], doc["file"])
        title, intro, sections = renderer.parse(text.split("\n"))
        html_doc = build_doc_html(doc, title or doc["tab"], intro, sections, today)
        rendered.append((doc, html_doc, renderer.task_count, len(sections)))
        doc_html.append(html_doc)
        tab_html.append('<a class="tab" href="#%s" data-doc="%s">%s<span class="n">0/0</span></a>' % (doc["id"], doc["id"], esc(doc["tab"])))

    index = INDEX_TEMPLATE.replace("__TABS__", "".join(tab_html)).replace("__DOCS__", "\n".join(doc_html))

    # Verificación de privacidad: se revisa el texto visible y los atributos.
    leaks = []
    for label, pattern in LEAK_PATTERNS.items():
        for m in pattern.finditer(index):
            leaks.append((label, m.group(0)))
    if leaks:
        print("Construcción detenida: posible dato privado en el sitio:", file=sys.stderr)
        for label, value in leaks:
            print("  - %s: %r" % (label, value), file=sys.stderr)
        print("Ajusta DROP_LINE en study_site.py o la nota de origen.", file=sys.stderr)
        return 2

    clean_output(out_dir)
    write(os.path.join(out_dir, "index.html"), index)
    for name in ("styles.css", "app.js", "theme.js"):
        shutil.copyfile(os.path.join(ASSETS, name), os.path.join(out_dir, name))

    digest = hashlib.sha1()
    for name in ("index.html", "styles.css", "app.js", "theme.js"):
        with open(os.path.join(out_dir, name), "rb") as fh:
            digest.update(fh.read())
    with open(os.path.join(ASSETS, "sw.js"), encoding="utf-8") as fh:
        write(os.path.join(out_dir, "sw.js"), fh.read().replace("__BUILD__", digest.hexdigest()[:12]))

    write(os.path.join(out_dir, "manifest.webmanifest"), MANIFEST)
    write(os.path.join(out_dir, "icons", "icon.svg"), ICON_SVG)
    write(os.path.join(out_dir, "robots.txt"), "User-agent: *\nDisallow: /\n")
    write(os.path.join(out_dir, ".nojekyll"), "")
    write(os.path.join(out_dir, "README.md"), README)
    write(os.path.join(out_dir, ".github", "workflows", "pages.yml"), PAGES_WORKFLOW)
    icons_ok = make_icons(out_dir)

    print("Sitio generado en: %s" % out_dir)
    for doc, _, tasks, secs in rendered:
        print("  - %s: %d secciones, %d tareas" % (doc["file"], secs, tasks))
    print("  - Líneas de seguimiento omitidas del sitio público: %d" % removed_total)
    print("  - Iconos PNG: %s" % ("generados" if icons_ok else "omitidos"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
