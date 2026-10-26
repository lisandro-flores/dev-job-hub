#!/usr/bin/env python3
"""
CLI local para análisis de SEGUIMIENTO_POSTULACIONES.csv, ofertas/*.md y notas/*.md.
Genera el Centro de Mando visual en postulaciones/dashboard_postulaciones.html.
"""
import argparse
import csv
import datetime
import html
import json
import os
import re
import sys
from collections import Counter

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

ROOT_DIR = find_root_dir()
CSV_CANDIDATES = [
    os.path.join(ROOT_DIR, "SEGUIMIENTO_POSTULACIONES.csv"),
    os.path.join(ROOT_DIR, "SEGUIMIENTO.csv"),
    os.path.join(ROOT_DIR, "SEGUIMIENTO.template.csv"),
    os.path.join(ROOT_DIR, "templates", "SEGUIMIENTO.template.csv"),
]
CSV_PATH = next((p for p in CSV_CANDIDATES if os.path.exists(p)), os.path.join(ROOT_DIR, "SEGUIMIENTO_POSTULACIONES.csv"))
OFERTAS_DIR = os.path.join(ROOT_DIR, "ofertas")
NOTAS_DIR = os.path.join(ROOT_DIR, "notas")
PDFS_DIR = os.path.join(ROOT_DIR, "pdfs_oficiales")
HTML_CV_DIR = os.path.join(ROOT_DIR, "fuentes_html")
DEFAULT_HTML_OUT = os.path.join(ROOT_DIR, "postulaciones", "dashboard_postulaciones.html")

CANDIDATE_NAME = os.environ.get("CANDIDATE_NAME", "Developer")
CANDIDATE_INITIALS = os.environ.get("CANDIDATE_INITIALS", "".join([w[0] for w in CANDIDATE_NAME.split()][:2]).upper() or "DEV")

TECH_PATTERNS = {
    "TypeScript": r"\btypescript\b",
    "JavaScript": r"\bjavascript\b",
    "React": r"\breact(?:\.js|js)?\b",
    "Angular": r"\bangular\b",
    "Next.js": r"\bnext(?:\.js|js)\b",
    "Node.js": r"\bnode(?:\.js|js)?\b",
    "NestJS": r"\bnest(?:\.js|js)\b",
    "Fastify": r"\bfastify\b",
    "Express": r"\bexpress\b",
    "PostgreSQL": r"\bpostgres(?:ql)?\b",
    "MySQL": r"\bmysql\b",
    "SQL Server": r"\bsql server\b",
    "MongoDB": r"\bmongodb\b",
    "SQL": r"\bsql\b",
    "Prisma": r"\bprisma\b",
    "REST APIs": r"\b(?:rest|api(?:s)? rest|restful)\b",
    "GraphQL": r"\bgraphql\b",
    "Docker": r"\bdocker\b",
    "Git": r"\bgit\b",
    "Jest": r"\bjest\b",
    "TailwindCSS": r"\btailwind(?:css)?\b",
    "HTML/CSS": r"\b(?:html5?|css3?)\b",
    "Go": r"\b(?:golang|\bgo\b)\b",
    "Python": r"\bpython\b",
    ".NET / C#": r"\b(?:\.net|c#)\b",
    "AI / Agents / n8n": r"\b(?:ai-native|ai coding|n8n|llm|ia)\b",
}


def load_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [r for r in reader if any(r.values())]


def compute_skills():
    counts = Counter()
    md_files = []
    if os.path.isdir(OFERTAS_DIR):
        md_files = [
            os.path.join(OFERTAS_DIR, fname)
            for fname in sorted(os.listdir(OFERTAS_DIR))
            if fname.endswith(".md")
        ]

    total_sources = len(md_files)
    if md_files:
        for fpath in md_files:
            with open(fpath, "r", encoding="utf-8") as f:
                md = f.read()
            for tech, pat in TECH_PATTERNS.items():
                if re.search(pat, md, flags=re.IGNORECASE):
                    counts[tech] += 1
    else:
        rows = load_rows()
        total_sources = len(rows)
        for r in rows:
            text = f"{r.get('puesto', '')} {r.get('notas', '')}"
            for tech, pat in TECH_PATTERNS.items():
                if re.search(pat, text, flags=re.IGNORECASE):
                    counts[tech] += 1

    return total_sources, [
        {
            "name": k,
            "offers": v,
            "pct": round((v / total_sources) * 100) if total_sources else 0,
        }
        for k, v in counts.most_common()
    ]


def cmd_followup(args):
    rows = load_rows()
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    window = datetime.timedelta(days=args.days)

    urgent = []
    upcoming = []
    pending_apply = []

    for r in rows:
        estado = (r.get("estado") or "").strip()
        f_seg_str = (r.get("fecha_seguimiento") or "").strip()
        f_seg = None
        if f_seg_str:
            try:
                f_seg = datetime.date.fromisoformat(f_seg_str)
            except ValueError:
                pass

        item = {
            "empresa": r.get("empresa", ""),
            "puesto": r.get("puesto", ""),
            "estado": estado,
            "fecha_seguimiento": f_seg_str,
            "proxima_accion": r.get("proxima_accion", ""),
            "notas": r.get("notas", ""),
        }

        if "por postular" in estado.lower():
            pending_apply.append(item)
        if f_seg:
            if f_seg <= today:
                urgent.append(item)
            elif f_seg <= today + window:
                upcoming.append(item)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "today": today.isoformat(),
                    "window_days": args.days,
                    "total_tracked": len(rows),
                    "due_or_overdue": urgent,
                    "upcoming": upcoming,
                    "pending_to_apply": pending_apply,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(f"Seguimiento de Postulaciones (Corte: {today.isoformat()} | Ventana: +{args.days} días)")
    print(f"Total registradas: {len(rows)}\n")

    if pending_apply:
        print("PENDIENTES POR POSTULAR:")
        for x in pending_apply:
            print(f"  [{x['empresa']}] {x['puesto']} -> {x['proxima_accion']}")
        print()

    if urgent:
        print("VENCIDAS O PARA HOY:")
        for x in urgent:
            print(f"  ({x['fecha_seguimiento']}) [{x['empresa']}] {x['puesto']} [{x['estado']}]")
            print(f"    Accion: {x['proxima_accion']}")
        print()
    else:
        print("Sin acciones vencidas al dia de hoy.\n")

    if upcoming:
        print(f"PROXIMAS EN LOS SIGUIENTES {args.days} DIAS:")
        for x in sorted(upcoming, key=lambda i: i["fecha_seguimiento"]):
            print(f"  ({x['fecha_seguimiento']}) [{x['empresa']}] {x['puesto']} [{x['estado']}]")
            print(f"    Accion: {x['proxima_accion']}")
        print()

    return 0


def cmd_skills(args):
    total_sources, skills_list = compute_skills()

    if args.format == "json":
        print(
            json.dumps(
                {
                    "total_offers": total_sources,
                    "skills": skills_list,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(f"Mapa de demanda de tecnologias ({total_sources} fichas en ofertas/):")
    print("-" * 62)
    max_val = max((s["offers"] for s in skills_list), default=1)
    for s in skills_list:
        bar = "█" * int((s["offers"] / max_val) * 18)
        print(f"  {s['name'].ljust(18)} {str(s['offers']).rjust(2)}/{total_sources} ({str(s['pct']).rjust(3)}%)  {bar}")
    return 0


def strip_emojis(text):
    if not text:
        return ""
    clean = re.sub(r"[\U00010000-\U0010ffff]|[\u2600-\u27bf\ufe0f]", "", text)
    return re.sub(r"[ \t]{2,}", " ", clean).strip()


def load_markdown_collection(folder_path, priority_order=None):
    items = []
    if not os.path.isdir(folder_path):
        return items
    files = [f for f in sorted(os.listdir(folder_path)) if f.endswith(".md")]
    if priority_order:
        files.sort(key=lambda x: (priority_order.index(x) if x in priority_order else 999, x))
    for fname in files:
        fpath = os.path.join(folder_path, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        clean_content = strip_emojis(content)
        title_match = re.search(r"^#\s+(.+)$", clean_content, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else fname.replace(".md", "")
        items.append({
            "filename": fname,
            "relpath": f"{os.path.basename(folder_path)}/{fname}",
            "title": title,
            "content": clean_content,
        })
    return items


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Centro de Mando &middot; Búsqueda de Empleo &mdash; __CANDIDATE_NAME__</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #090d16;
      --bg-elev: #0f172a;
      --card: #141e33;
      --card-hover: #1a2742;
      --card-subtle: #0f172a;
      --border: #23314d;
      --border-subtle: #1a263e;
      --text: #f1f5f9;
      --text-dim: #cbd5e1;
      --muted: #8194b3;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.12);
      --green: #34d399;
      --green-soft: rgba(52, 211, 153, 0.12);
      --amber: #fbbf24;
      --amber-soft: rgba(251, 191, 36, 0.12);
      --purple: #a78bfa;
      --purple-soft: rgba(167, 139, 250, 0.12);
      --red: #f87171;
      --red-soft: rgba(248, 113, 113, 0.12);
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #090d16;
      color: var(--text);
      min-height: 100vh;
      line-height: 1.5;
      font-size: 14px;
      -webkit-font-smoothing: antialiased;
    }
    header {
      border-bottom: 1px solid var(--border);
      background: rgba(9, 13, 22, 0.92);
      backdrop-filter: blur(16px);
      position: sticky;
      top: 0;
      z-index: 40;
      padding: 0.85rem 2rem;
    }
    .header-inner {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .brand-mark {
      width: 36px;
      height: 36px;
      border-radius: var(--radius-md);
      background: #0f172a;
      border: 1px solid var(--accent);
      color: var(--accent);
      display: grid;
      place-items: center;
      font-weight: 700;
      font-size: 0.88rem;
      letter-spacing: -0.03em;
    }
    .brand h1 {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #fff;
    }
    .brand p {
      margin: 0.1rem 0 0;
      font-size: 0.76rem;
      color: var(--muted);
    }
    .nav-tabs {
      display: flex;
      gap: 0.35rem;
      background: var(--bg-elev);
      padding: 0.25rem;
      border-radius: var(--radius-md);
      border: 1px solid var(--border);
      overflow-x: auto;
      max-width: 100%;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
    }
    .nav-tabs::-webkit-scrollbar { display: none; }
    .tab-btn {
      background: transparent;
      color: var(--muted);
      border: none;
      padding: 0.48rem 0.9rem;
      min-height: 38px;
      border-radius: var(--radius-sm);
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.12s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      white-space: nowrap;
      flex-shrink: 0;
      text-decoration: none;
    }
    .tab-btn:hover {
      color: var(--text);
      background: rgba(255, 255, 255, 0.04);
      text-decoration: none;
    }
    .tab-btn.active {
      background: var(--card);
      color: #fff;
      border: 1px solid var(--border);
    }
    .container {
      max-width: 1440px;
      margin: 0 auto;
      padding: 1.5rem 2rem 3rem;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .kpi-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 1.15rem 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .kpi-val {
      font-size: 2.1rem;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.03em;
      font-feature-settings: "tnum";
    }
    .kpi-lbl {
      font-size: 0.82rem;
      color: var(--muted);
      margin-top: 0.4rem;
      font-weight: 500;
    }
    .kpi-sub {
      font-size: 0.74rem;
      margin-top: 0.6rem;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.15rem 0.5rem;
      border-radius: var(--radius-sm);
      width: fit-content;
      font-weight: 500;
    }

    .priority-banner {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
      gap: 1rem;
      margin-bottom: 1.75rem;
    }
    .p-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1rem;
      position: relative;
    }
    .p-card.p-card-primary {
      border-left: 3px solid var(--green);
    }
    .p-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }
    .p-card h3 {
      margin: 0.4rem 0 0;
      font-size: 1.05rem;
      font-weight: 700;
      color: #fff;
    }
    .p-tags {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      margin-top: 0.6rem;
      font-size: 0.8rem;
      color: var(--text-dim);
    }
    .p-tag-item {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }
    .p-tag-lbl {
      color: var(--muted);
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      min-width: 86px;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }
    .p-actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      padding-top: 0.4rem;
      border-top: 1px solid var(--border-subtle);
    }

    .btn {
      background: var(--card-subtle);
      color: var(--text-dim);
      border: 1px solid var(--border);
      padding: 0.45rem 0.85rem;
      border-radius: var(--radius-sm);
      font-size: 0.79rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      transition: all 0.12s ease;
      white-space: nowrap;
    }
    .btn:hover {
      color: #fff;
      border-color: var(--accent);
      background: var(--card-hover);
    }
    .btn-primary {
      background: var(--accent-soft);
      color: var(--accent);
      border-color: rgba(56, 189, 248, 0.4);
    }
    .btn-primary:hover {
      background: rgba(56, 189, 248, 0.22);
      color: #fff;
    }
    .btn-success {
      background: var(--green-soft);
      color: var(--green);
      border-color: rgba(52, 211, 153, 0.4);
    }
    .btn-success:hover {
      background: rgba(52, 211, 153, 0.22);
      color: #fff;
    }
    .btn-sm {
      padding: 0.28rem 0.6rem;
      font-size: 0.74rem;
    }

    .ico {
      width: 14px;
      height: 14px;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
      fill: none;
      display: inline-block;
      vertical-align: -2px;
      flex-shrink: 0;
    }
    .ico-sm { width: 12px; height: 12px; vertical-align: -1px; }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.18rem 0.55rem;
      border-radius: var(--radius-sm);
      font-size: 0.73rem;
      font-weight: 600;
      line-height: 1.2;
    }
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      display: inline-block;
    }
    .badge-green { background: var(--green-soft); color: var(--green); border: 1px solid rgba(52, 211, 153, 0.25); }
    .badge-green .dot { background: var(--green); }
    .badge-blue { background: var(--accent-soft); color: var(--accent); border: 1px solid rgba(56, 189, 248, 0.25); }
    .badge-blue .dot { background: var(--accent); }
    .badge-amber { background: var(--amber-soft); color: var(--amber); border: 1px solid rgba(251, 191, 36, 0.25); }
    .badge-amber .dot { background: var(--amber); }
    .badge-purple { background: var(--purple-soft); color: var(--purple); border: 1px solid rgba(167, 139, 250, 0.25); }
    .badge-purple .dot { background: var(--purple); }
    .badge-red { background: var(--red-soft); color: var(--red); border: 1px solid rgba(248, 113, 113, 0.25); }
    .badge-red .dot { background: var(--red); }

    .kanban-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.1rem;
      margin-bottom: 2rem;
    }
    @media (max-width: 1024px) {
      .kanban-grid { grid-template-columns: 1fr; }
    }
    .kanban-col {
      background: var(--bg-elev);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .kanban-col-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 0.65rem;
      border-bottom: 1px solid var(--border);
      font-weight: 600;
      font-size: 0.84rem;
      color: var(--text-dim);
    }
    .k-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 0.95rem;
      transition: all 0.12s ease;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .k-card:hover {
      border-color: var(--accent);
      background: var(--card-hover);
    }
    .k-card-title {
      font-weight: 700;
      font-size: 0.9rem;
      color: #fff;
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 0.5rem;
    }
    .k-card-role {
      font-size: 0.81rem;
      color: var(--accent);
      font-weight: 500;
    }
    .k-card-meta {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      font-size: 0.77rem;
      color: var(--text-dim);
      padding-top: 0.25rem;
      border-top: 1px solid var(--border-subtle);
    }
    .meta-row {
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .meta-label {
      color: var(--muted);
      min-width: 82px;
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }
    .meta-val {
      color: var(--text);
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }
    .section-title {
      font-size: 0.98rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      margin: 0;
      color: #fff;
    }
    input[type="search"] {
      width: 100%;
      max-width: 380px;
      padding: 0.55rem 0.9rem;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
      background: var(--card);
      color: var(--text);
      font-size: 0.82rem;
    }
    input[type="search"]:focus {
      outline: 1px solid var(--accent);
      border-color: var(--accent);
    }
    .table-wrap {
      overflow-x: auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }
    th, td {
      padding: 0.75rem 0.9rem;
      text-align: left;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-weight: 600;
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      background: rgba(15, 23, 42, 0.9);
      white-space: nowrap;
    }
    tr:hover td { background: rgba(255, 255, 255, 0.015); }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .split-view {
      display: grid;
      grid-template-columns: 330px 1fr;
      gap: 1.25rem;
      align-items: start;
    }
    .split-view-equal {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
      align-items: start;
    }
    @media (max-width: 960px) {
      .split-view, .split-view-equal { grid-template-columns: 1fr; }
      .doc-sidebar {
        position: static;
        max-height: 280px;
      }
    }
    @media (max-width: 640px) {
      header { padding: 0.75rem 1rem; }
      .container { padding: 1rem; }
      .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 0.65rem; }
      .kpi-card { padding: 0.9rem 1rem; }
      .kpi-val { font-size: 1.55rem; }
      .p-card { padding: 1rem; }
      .p-tag-item { grid-template-columns: 1fr; gap: 0.15rem; }
      .doc-viewer { padding: 1.1rem 1rem; min-height: auto; }
      .check-row { padding: 0.75rem 0.85rem; }
      .check-box { width: 22px; height: 22px; }
      .skill-row { grid-template-columns: 110px 1fr 68px; gap: 0.5rem; font-size: 0.78rem; }
      #tbl, #tbl thead, #tbl tbody, #tbl tr, #tbl th, #tbl td { display: block; }
      #tbl thead { position: absolute; left: -9999px; }
      #tbl tr {
        margin: 0.55rem; padding: 0.5rem 0;
        background: var(--bg-elev); border: 1px solid var(--border); border-radius: var(--radius-md);
      }
      #tbl td { padding: 0.35rem 0.85rem; border: 0; }
      #tbl td::before {
        content: attr(data-label); display: block; margin-bottom: 0.1rem;
        font-size: 0.68rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted);
      }
    }
    .followup-strip {
      background: var(--bg-elev);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.9rem 1.1rem;
      margin-bottom: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
    }
    .followup-head {
      display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap;
      font-size: 0.84rem; font-weight: 700; color: #fff;
    }
    .followup-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 0.6rem;
    }
    .followup-item {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 0.65rem 0.8rem;
      display: flex; align-items: center; justify-content: space-between; gap: 0.6rem;
      font-size: 0.78rem;
    }
    .toc-chips {
      display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 1.1rem;
      padding: 0.6rem 0.75rem; background: var(--bg-elev);
      border: 1px solid var(--border); border-radius: var(--radius-md);
    }
    .toc-chip {
      font-size: 0.74rem; font-weight: 600; color: var(--text-dim);
      background: var(--card); border: 1px solid var(--border);
      border-radius: 999px; padding: 0.2rem 0.65rem; cursor: pointer;
      text-decoration: none;
    }
    .toc-chip:hover { border-color: var(--accent); color: #fff; text-decoration: none; }
    .dash-quote-tools {
      display: flex; gap: 0.4rem; margin-bottom: 0.45rem;
    }
    .dash-quote-btn {
      background: var(--card); color: var(--text-dim); border: 1px solid var(--border);
      border-radius: 999px; padding: 0.15rem 0.55rem; font-size: 0.72rem; font-weight: 600; cursor: pointer;
    }
    .dash-quote-btn:hover { border-color: var(--accent); color: #fff; }
    .dash-quote-blur { filter: blur(6px); opacity: 0.55; user-select: none; cursor: pointer; }
    .skill-row { cursor: pointer; padding: 0.25rem 0.4rem; border-radius: var(--radius-sm); transition: background 0.12s ease; }
    .skill-row:hover { background: rgba(56, 189, 248, 0.08); }
    .doc-sidebar {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.75rem;
      max-height: 82vh;
      overflow-y: auto;
      position: sticky;
      top: 75px;
    }
    .doc-item {
      width: 100%;
      text-align: left;
      background: transparent;
      border: 1px solid transparent;
      color: var(--text);
      padding: 0.65rem 0.8rem;
      border-radius: var(--radius-sm);
      cursor: pointer;
      margin-bottom: 0.25rem;
      transition: all 0.1s ease;
    }
    .doc-item:hover {
      background: rgba(255, 255, 255, 0.03);
    }
    .doc-item.active {
      background: var(--accent-soft);
      border-color: rgba(56, 189, 248, 0.35);
    }
    .doc-item-title {
      font-weight: 600;
      font-size: 0.84rem;
      line-height: 1.3;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }
    .doc-item-sub {
      font-size: 0.72rem;
      color: var(--muted);
      margin-top: 0.2rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    .doc-viewer {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 1.75rem 2rem;
      min-height: 70vh;
    }
    .md-body h1 { font-size: 1.35rem; margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; color: #fff; font-weight: 700; }
    .md-body h2 { font-size: 1.1rem; color: var(--accent); margin-top: 1.5rem; font-weight: 600; }
    .md-body h3 { font-size: 0.96rem; color: #f1f5f9; margin-top: 1.2rem; font-weight: 600; }
    .md-body h4 { font-size: 0.88rem; color: var(--text-dim); margin-top: 1rem; font-weight: 600; }
    .md-body p, .md-body li { color: #e2e8f0; font-size: 0.88rem; }
    .md-body ul, .md-body ol { padding-left: 1.35rem; }
    .md-body li { margin-bottom: 0.3rem; }
    .md-body blockquote {
      margin: 1rem 0;
      padding: 0.75rem 1rem;
      border-left: 3px solid var(--accent);
      background: var(--bg-elev);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      color: #f8fafc;
      font-size: 0.86rem;
    }
    .md-body code {
      background: var(--bg-elev);
      padding: 0.12rem 0.35rem;
      border-radius: var(--radius-sm);
      font-size: 0.82em;
      color: #7dd3fc;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    .md-body pre {
      background: #090d16;
      padding: 0.9rem;
      border-radius: var(--radius-md);
      overflow-x: auto;
      border: 1px solid var(--border);
    }
    .md-body pre code { background: transparent; padding: 0; color: #e2e8f0; }
    .md-body hr { border: none; border-top: 1px solid var(--border); margin: 1.4rem 0; }
    .md-body table { margin: 1rem 0; border: 1px solid var(--border); border-radius: var(--radius-sm); overflow: hidden; font-size: 0.82rem; }

    .study-progress-card {
      background: var(--bg-elev);
      border: 1px solid var(--border);
      border-left: 3px solid var(--green);
      border-radius: var(--radius-md);
      padding: 1rem 1.15rem;
      margin-bottom: 1.35rem;
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
    }
    .study-progress-top {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
    }
    .study-progress-title {
      font-weight: 700;
      font-size: 0.88rem;
      color: #fff;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }
    .study-progress-controls {
      display: flex;
      align-items: center;
      gap: 0.35rem;
      flex-wrap: wrap;
    }
    .study-progress-track {
      height: 8px;
      background: #090d16;
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid var(--border);
    }
    .study-progress-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--green));
      border-radius: 999px;
      transition: width 0.25s ease;
    }
    .check-li {
      list-style: none;
      margin-left: -1.35rem;
      margin-bottom: 0.5rem !important;
    }
    .check-row {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 0.65rem 0.85rem;
      border-radius: var(--radius-md);
      background: var(--bg-elev);
      border: 1px solid var(--border);
      cursor: pointer;
      transition: all 0.14s ease;
      user-select: none;
    }
    .check-row:hover {
      border-color: var(--accent);
      background: var(--card-hover);
    }
    .check-li.is-checked .check-row {
      background: rgba(52, 211, 153, 0.06);
      border-color: rgba(52, 211, 153, 0.32);
    }
    .check-box {
      width: 18px;
      height: 18px;
      border-radius: 5px;
      border: 1.5px solid var(--muted);
      background: #090d16;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 2px;
      transition: all 0.14s ease;
      color: transparent;
    }
    .check-li.is-checked .check-box {
      background: var(--green);
      border-color: var(--green);
      color: #090d16;
    }
    .check-text {
      flex: 1;
      line-height: 1.5;
      color: var(--text);
      font-size: 0.86rem;
    }
    .check-li.is-checked .check-text {
      color: var(--muted);
    }
    .res-link {
      color: var(--accent);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.05rem 0.35rem;
      border-radius: 4px;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.22);
      text-decoration: none;
      transition: all 0.12s ease;
    }
    .res-link:hover {
      background: rgba(56, 189, 248, 0.2);
      color: #fff;
      text-decoration: none;
    }

    .skill-row {
      display: grid;
      grid-template-columns: 160px 1fr 85px;
      align-items: center;
      gap: 0.85rem;
      margin-bottom: 0.65rem;
      font-size: 0.84rem;
    }
    .skill-bar-bg {
      height: 8px;
      background: var(--bg-elev);
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid var(--border);
    }
    .skill-bar-fill {
      height: 100%;
      background: var(--accent);
      border-radius: 999px;
    }
    .cv-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 0.75rem;
      margin-top: 0.75rem;
    }
    .cv-card {
      background: var(--bg-elev);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 0.95rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.75rem;
    }
    .hidden { display: none !important; }

    .lock-screen-overlay {
      position: fixed;
      inset: 0;
      background: #070b14;
      background-image: radial-gradient(circle at 50% 25%, rgba(56, 189, 248, 0.12), transparent 75%);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .lock-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 2.25rem 2rem;
      max-width: 420px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.75);
    }
    .lock-card input:focus {
      border-color: var(--accent) !important;
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }
    @keyframes shakeCard {
      0%, 100% { transform: translateX(0); }
      20%, 60% { transform: translateX(-6px); }
      40%, 80% { transform: translateX(6px); }
    }
    .shake { animation: shakeCard 0.35s ease-in-out; }
  </style>
</head>
<body>
  <div id="lock-screen" class="lock-screen-overlay" style="__LOCK_STYLE__">
    <div class="lock-card" id="lock-card">
      <div class="brand-mark" style="margin: 0 auto 1rem; width: 56px; height: 56px; font-size: 1.3rem;">__CANDIDATE_INITIALS__</div>
      <h2 style="color:#fff; margin: 0 0 0.35rem; font-size: 1.3rem; font-weight: 700;">Centro de Mando</h2>
      <p style="color:var(--muted); font-size: 0.85rem; margin: 0 0 1.25rem;">__CANDIDATE_NAME__ &middot; Acceso protegido</p>
      <div class="badge badge-blue" style="margin-bottom: 1.25rem; display: inline-flex; align-items:center; gap:0.4rem;">
        <svg class="ico ico-sm" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg> Cifrado AES-256-GCM
      </div>
      <form id="lock-form" onsubmit="handleUnlock(event)">
        <div style="position: relative; margin-bottom: 0.85rem;">
          <input type="password" id="lock-pass" placeholder="Contraseña secreta..." required autocomplete="current-password"
                 style="width: 100%; box-sizing: border-box; padding: 0.85rem 2.8rem 0.85rem 1rem; border-radius: var(--radius-md); background: #090d16; border: 1px solid var(--border); color: #fff; font-size: 0.95rem; outline: none;">
          <button type="button" id="toggle-pass-btn" onclick="togglePassVisibility()"
                  style="position: absolute; right: 0.65rem; top: 50%; transform: translateY(-50%); background: transparent; border: none; color: var(--muted); cursor: pointer; padding: 0.35rem;">
            <svg id="eye-icon" class="ico ico-sm" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <div id="lock-error" style="display: none; color: #f87171; font-size: 0.82rem; margin-bottom: 0.85rem; line-height: 1.4;"></div>
        <label style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; color: var(--muted); font-size: 0.82rem; margin-bottom: 1.25rem; cursor: pointer; user-select: none;">
          <input type="checkbox" id="remember-pass" checked> Recordar en este dispositivo
        </label>
        <button type="submit" id="btn-unlock-submit" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 0.85rem; font-size: 0.95rem;">
          <svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Desbloquear Centro de Mando
        </button>
      </form>
    </div>
  </div>

  <header style="__HEADER_STYLE__">
    <div class="header-inner">
      <div class="brand">
        <div class="brand-mark">__CANDIDATE_INITIALS__</div>
        <div>
          <h1>Centro de Mando &middot; Búsqueda de Empleo</h1>
          <p>__CANDIDATE_NAME__ &middot; Corte: <span id="corte-date">__GENERATED_AT__</span></p>
        </div>
      </div>
      <nav class="nav-tabs" role="tablist">
        <button class="tab-btn active" data-tab="tab-funnel"><svg class="ico" viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg> Embudo y vacantes</button>
        <button class="tab-btn" data-tab="tab-ofertas"><svg class="ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg> Modo entrevista (<span id="ofertas-count-badge">__OFERTAS_COUNT__</span> fichas)</button>
        <button class="tab-btn" data-tab="tab-notas"><svg class="ico" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg> Plan de estudio y notas</button>
        <button class="tab-btn" data-tab="tab-skills"><svg class="ico" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg> Demanda de skills y CVs</button>
        <a class="tab-btn" href="../sitio_estudio/index.html" target="_blank" rel="noopener" style="text-decoration:none"><svg class="ico" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg> Modo móvil / PWA</a>
        <button class="tab-btn" id="btn-lock" onclick="lockDashboard()" title="Bloquear panel con contraseña" style="display:none; margin-left:auto;"><svg class="ico" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg> Bloquear</button>
      </nav>
    </div>
  </header>

  <main class="container" style="__MAIN_STYLE__">
    <!-- TAB 1: EMBUDO Y VACANTES -->
    <section id="tab-funnel" class="tab-panel">
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-val" style="color: var(--accent)" id="kpi-total">__TOTAL__</div>
          <div class="kpi-lbl">Postulaciones registradas</div>
          <span class="kpi-sub badge-blue" id="kpi-sub-total"><svg class="ico ico-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> 13 al 21 oct 2026</span>
        </div>
        <div class="kpi-card">
          <div class="kpi-val" style="color: var(--green)" id="kpi-en-proceso">__EN_PROCESO_COUNT__</div>
          <div class="kpi-lbl">Procesos activos / Entrevistas</div>
          <span class="kpi-sub badge-green" id="kpi-sub-proceso"><svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> ALPRO + ALTEN + AMK + Accenture</span>
        </div>
        <div class="kpi-card">
          <div class="kpi-val" style="color: var(--purple)"><span id="kpi-conversion">__CONVERSION_RATE__</span>%</div>
          <div class="kpi-lbl">Tasa de conversión inicial</div>
          <span class="kpi-sub badge-purple"><svg class="ico ico-sm" viewBox="0 0 24 24"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg> Mercado habitual: 2% a 5%</span>
        </div>
        <div class="kpi-card">
          <div class="kpi-val" style="color: var(--amber)" id="kpi-activas">__ACTIVAS_COUNT__</div>
          <div class="kpi-lbl">En espera activa</div>
          <span class="kpi-sub badge-amber" id="kpi-sub-activas"><svg class="ico ico-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg> Seguimiento programado</span>
        </div>
      </div>

      <!-- Banner de Entrevistas Prioritarias (renderizado dinámicamente) -->
      <div class="priority-banner" id="priority-banner"></div>

      <!-- Agenda CRM de próximos seguimientos -->
      <div class="followup-strip" id="followup-strip"></div>

      <!-- Tablero Kanban por Etapa -->
      <div class="kanban-grid" id="kanban-board"></div>

      <!-- Tabla completa con buscador -->
      <div class="toolbar">
        <h2 class="section-title">Registro maestro de postulaciones</h2>
        <input type="search" id="q-table" placeholder="Filtrar por empresa, puesto, tecnología, estado...">
      </div>
      <div class="table-wrap">
        <table id="tbl">
          <thead>
            <tr>
              <th>Fecha</th><th>Empresa</th><th>Puesto</th><th>Estado</th>
              <th>Próxima acción</th><th>Seguimiento</th><th>Compensación</th><th>Ficha</th>
            </tr>
          </thead>
          <tbody id="tbl-body"></tbody>
        </table>
      </div>
    </section>

    <!-- TAB 2: MODO ENTREVISTA (FICHAS DE OFERTAS) -->
    <section id="tab-ofertas" class="tab-panel hidden">
      <div class="split-view">
        <aside class="doc-sidebar">
          <input type="search" id="q-ofertas" placeholder="Filtrar ficha o tecnología..." style="margin-bottom: 0.65rem; max-width: 100%;">
          <div id="ofertas-list"></div>
        </aside>
        <article class="doc-viewer md-body" id="ofertas-viewer"></article>
      </div>
    </section>

    <!-- TAB 3: NOTAS Y PLAN DE ESTUDIO -->
    <section id="tab-notas" class="tab-panel hidden">
      <div class="split-view">
        <aside class="doc-sidebar">
          <input type="search" id="q-notas" placeholder="Filtrar guía o concepto (SQL, NgiCaja)..." style="margin-bottom: 0.65rem; max-width: 100%;">
          <div id="notas-list"></div>
        </aside>
        <article class="doc-viewer md-body" id="notas-viewer"></article>
      </div>
    </section>

    <!-- TAB 4: DEMANDA DE SKILLS Y CVS OFICIALES -->
    <section id="tab-skills" class="tab-panel hidden">
      <div class="split-view-equal">
        <div class="doc-viewer">
          <h2 style="margin-top: 0; font-size: 1.15rem; color: #fff;">Tecnologías más demandadas (__TOTAL_OFFERS__ vacantes)</h2>
          <p style="color: var(--muted); font-size: 0.82rem; margin-bottom: 1.25rem;">
            Calculado automáticamente desde las fichas registradas en <code>ofertas/*.md</code>.
          </p>
          <div id="skills-bars"></div>
        </div>
        <div class="doc-viewer">
          <h2 style="margin-top: 0; font-size: 1.15rem; color: #fff;">CVs oficiales para postulación</h2>
          <p style="color: var(--muted); font-size: 0.82rem;">
            Generados desde <code>fuentes_html/</code> con <code>./generar_pdfs.sh</code>.
          </p>
          <div class="cv-grid" id="pdfs-grid"></div>
          <h3 style="margin-top: 1.6rem; font-size: 1rem; color: #fff;">Fuentes HTML editables</h3>
          <div class="cv-grid" id="html-cvs-grid"></div>
        </div>
      </div>
    </section>
  </main>

  <script>
    let DATA = __PAYLOAD_JSON__;
    const ENCRYPTED_PAYLOAD = __ENCRYPTED_PAYLOAD_JSON__;
    const STORAGE_PASS_KEY = 'cv_dashboard_secret_v1';
    const CHECK_STORAGE_KEY = 'cv_study_checks_v1';
    let checkFilterMode = 'all';

    const ICONS = {
      check: '<svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      tick: '<svg class="ico ico-sm" viewBox="0 0 24 24" style="stroke-width:3"><polyline points="20 6 9 17 4 12"/></svg>',
      clock: '<svg class="ico ico-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      archive: '<svg class="ico ico-sm" viewBox="0 0 24 24"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
      file: '<svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
      external: '<svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
      dollar: '<svg class="ico ico-sm" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
      arrow: '<svg class="ico ico-sm" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>',
      code: '<svg class="ico ico-sm" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
      mapPin: '<svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
      gift: '<svg class="ico ico-sm" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
      briefcase: '<svg class="ico ico-sm" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
      home: '<svg class="ico ico-sm" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
      lock: '<svg class="ico ico-sm" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>'
    };

    function base64ToUint8(b64) {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) {
        bytes[i] = bin.charCodeAt(i);
      }
      return bytes;
    }

    async function decryptPayload(password) {
      const enc = new TextEncoder();
      const salt = base64ToUint8(ENCRYPTED_PAYLOAD.salt);
      const iv = base64ToUint8(ENCRYPTED_PAYLOAD.iv);
      const data = base64ToUint8(ENCRYPTED_PAYLOAD.data);

      const passKey = await crypto.subtle.importKey(
        'raw',
        enc.encode(password),
        'PBKDF2',
        false,
        ['deriveKey']
      );
      const key = await crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' },
        passKey,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
      );
      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        data
      );
      const dec = new TextDecoder();
      return JSON.parse(dec.decode(decrypted));
    }

    async function attemptUnlock(password, remember) {
      const errEl = document.getElementById('lock-error');
      const cardEl = document.getElementById('lock-card');
      const submitBtn = document.getElementById('btn-unlock-submit');
      if (errEl) errEl.style.display = 'none';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Desencriptando...';
      }
      try {
        const decrypted = await decryptPayload(password);
        DATA = decrypted;
        if (remember) {
          localStorage.setItem(STORAGE_PASS_KEY, password);
        } else {
          sessionStorage.setItem(STORAGE_PASS_KEY, password);
        }
        const lockScreen = document.getElementById('lock-screen');
        if (lockScreen) lockScreen.style.display = 'none';
        initDashboard();
      } catch (err) {
        if (errEl) {
          errEl.textContent = 'Contraseña incorrecta. No se pudo desencriptar el contenido.';
          errEl.style.display = 'block';
        }
        if (cardEl) {
          cardEl.classList.remove('shake');
          void cardEl.offsetWidth;
          cardEl.classList.add('shake');
        }
        localStorage.removeItem(STORAGE_PASS_KEY);
        sessionStorage.removeItem(STORAGE_PASS_KEY);
        const passInput = document.getElementById('lock-pass');
        if (passInput) {
          passInput.value = '';
          passInput.focus();
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `${ICONS.check} Desbloquear Centro de Mando`;
        }
      }
    }

    function togglePassVisibility() {
      const input = document.getElementById('lock-pass');
      if (!input) return;
      input.type = input.type === 'password' ? 'text' : 'password';
    }

    function lockDashboard() {
      localStorage.removeItem(STORAGE_PASS_KEY);
      sessionStorage.removeItem(STORAGE_PASS_KEY);
      DATA = null;
      const hEl = document.querySelector('header');
      const mEl = document.querySelector('main');
      if (hEl) hEl.style.display = 'none';
      if (mEl) mEl.style.display = 'none';
      const btnLock = document.getElementById('btn-lock');
      if (btnLock) btnLock.style.display = 'none';
      const lockScreen = document.getElementById('lock-screen');
      if (lockScreen) lockScreen.style.display = 'flex';
      const passInput = document.getElementById('lock-pass');
      if (passInput) {
        passInput.value = '';
        passInput.focus();
      }
      const errEl = document.getElementById('lock-error');
      if (errEl) errEl.style.display = 'none';
    }

    function handleUnlock(e) {
      if (e) e.preventDefault();
      const pass = document.getElementById('lock-pass').value.trim();
      const remember = document.getElementById('remember-pass').checked;
      if (!pass) return;
      attemptUnlock(pass, remember);
    }

    function loadSavedChecks() {
      try {
        return JSON.parse(localStorage.getItem(CHECK_STORAGE_KEY) || '{}');
      } catch (e) {
        return {};
      }
    }

    function saveChecksMap(map) {
      try {
        localStorage.setItem(CHECK_STORAGE_KEY, JSON.stringify(map));
      } catch (e) {}
    }

    function makeCheckKey(docFilename, rawItemText) {
      const clean = String(rawItemText || '').replace(/\s+/g, ' ').trim().slice(0, 100);
      return `${docFilename}::${clean}`;
    }

    function getDocStats(doc) {
      if (!doc || !doc.content) return { total: 0, done: 0, pct: 0 };
      const saved = loadSavedChecks();
      const lines = doc.content.replace(/\r\n/g, '\n').split('\n');
      let total = 0;
      let done = 0;
      for (const raw of lines) {
        const m = raw.match(/^\s*[-*]\s+\[([ xX])\]\s+(.*)$/);
        if (m) {
          total++;
          const defaultChecked = m[1].toLowerCase() === 'x';
          const key = makeCheckKey(doc.filename, m[2]);
          const isChecked = Object.prototype.hasOwnProperty.call(saved, key) ? Boolean(saved[key]) : defaultChecked;
          if (isChecked) done++;
        }
      }
      return { total, done, pct: total ? Math.round((done / total) * 100) : 0 };
    }

    function escapeHtml(str) {
      return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function renderMarkdown(md, docFilename = 'doc') {
      if (!md) return '';
      const saved = loadSavedChecks();
      const lines = md.replace(/\r\n/g, '\n').split('\n');
      let htmlOut = '';
      let inCode = false;
      let inList = false;
      let inTable = false;
      let quoteBuf = [];
      let tocItems = [];
      let secIdx = 0;

      function formatInline(text) {
        let s = escapeHtml(text);
        s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
        s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+|file:\/\/[^)]+)\)/g, `<a class="res-link" href="$2" target="_blank" rel="noopener" onclick="event.stopPropagation()">$1 ${ICONS.external}</a>`);
        return s;
      }

      function flushQuote() {
        if (!quoteBuf.length) return;
        const qText = quoteBuf.map(q => `<p style="margin:0.35rem 0">${formatInline(q)}</p>`).join('');
        quoteBuf = [];
        htmlOut += `
          <blockquote>
            <div class="dash-quote-tools">
              <button type="button" class="dash-quote-btn" onclick="toggleDashQuoteBlur(this)">Ocultar / Ensayar</button>
              <button type="button" class="dash-quote-btn" onclick="speakDashQuote(this)">Escuchar</button>
            </div>
            <div class="dash-quote-body" onclick="if(this.classList.contains('dash-quote-blur')) toggleDashQuoteBlur(this.parentElement.querySelector('.dash-quote-btn'))">${qText}</div>
          </blockquote>
        `;
      }

      for (let i = 0; i < lines.length; i++) {
        const raw = lines[i];
        const line = raw.trimEnd();

        if (!line.startsWith('>') && quoteBuf.length) {
          flushQuote();
        }

        if (line.startsWith('```')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          if (inTable) { htmlOut += '</tbody></table></div>'; inTable = false; }
          if (!inCode) {
            htmlOut += '<pre><code>';
            inCode = true;
          } else {
            htmlOut += '</code></pre>';
            inCode = false;
          }
          continue;
        }
        if (inCode) {
          htmlOut += escapeHtml(raw) + '\n';
          continue;
        }

        if (line.startsWith('|') && line.endsWith('|')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          const cells = line.slice(1, -1).split('|').map(c => c.trim());
          if (cells.every(c => /^[:\-]+$/.test(c))) continue;
          if (!inTable) {
            htmlOut += '<div class="table-wrap"><table><thead><tr>' +
              cells.map(c => `<th>${formatInline(c)}</th>`).join('') +
              '</tr></thead><tbody>';
            inTable = true;
          } else {
            htmlOut += '<tr>' + cells.map(c => `<td>${formatInline(c)}</td>`).join('') + '</tr>';
          }
          continue;
        } else if (inTable) {
          htmlOut += '</tbody></table></div>';
          inTable = false;
        }

        if (/^---+$/.test(line)) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          htmlOut += '<hr>';
          continue;
        }

        const checkMatch = line.match(/^\s*[-*]\s+\[([ xX])\]\s+(.*)$/);
        if (checkMatch) {
          if (!inList) { htmlOut += '<ul>'; inList = true; }
          const defaultChecked = checkMatch[1].toLowerCase() === 'x';
          const itemRaw = checkMatch[2];
          const key = makeCheckKey(docFilename, itemRaw);
          const isChecked = Object.prototype.hasOwnProperty.call(saved, key) ? Boolean(saved[key]) : defaultChecked;
          const hiddenByFilter = (checkFilterMode === 'pending' && isChecked) || (checkFilterMode === 'done' && !isChecked);
          const encodedKey = encodeURIComponent(key);
          htmlOut += `
            <li class="check-li ${isChecked ? 'is-checked' : ''} ${hiddenByFilter ? 'hidden' : ''}" data-check-key="${encodedKey}" data-default-checked="${defaultChecked ? '1' : '0'}" onclick="toggleCheckRow(this, '${escapeHtml(docFilename)}', ${i})">
              <div class="check-row">
                <span class="check-box">${ICONS.tick}</span>
                <div class="check-text">${formatInline(itemRaw)}</div>
              </div>
            </li>
          `;
          continue;
        }

        if (line.startsWith('# ')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          htmlOut += `<h1>${formatInline(line.slice(2))}</h1>`;
        } else if (line.startsWith('## ')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          secIdx++;
          const secId = `doc-sec-${secIdx}`;
          const secTitle = line.slice(3).trim();
          tocItems.push({ id: secId, title: secTitle });
          htmlOut += `<h2 id="${secId}">${formatInline(secTitle)}</h2>`;
        } else if (line.startsWith('### ')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          htmlOut += `<h3>${formatInline(line.slice(4))}</h3>`;
        } else if (line.startsWith('#### ')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          htmlOut += `<h4>${formatInline(line.slice(5))}</h4>`;
        } else if (line.startsWith('>')) {
          if (inList) { htmlOut += '</ul>'; inList = false; }
          const qLine = line.replace(/^>\s?/, '').trim();
          if (qLine && !qLine.startsWith('[!')) quoteBuf.push(qLine);
        } else if (/^(\s*[-*]|\s*\d+\.)\s+/.test(line)) {
          if (!inList) { htmlOut += '<ul>'; inList = true; }
          const itemText = line.replace(/^(\s*[-*]|\s*\d+\.)\s+/, '');
          htmlOut += `<li>${formatInline(itemText)}</li>`;
        } else if (line.trim() === '') {
          if (inList) { htmlOut += '</ul>'; inList = false; }
        } else {
          htmlOut += `<p>${formatInline(line)}</p>`;
        }
      }
      flushQuote();
      if (inList) htmlOut += '</ul>';
      if (inTable) htmlOut += '</tbody></table></div>';

      const tocHtml = tocItems.length > 1
        ? `<div class="toc-chips"><span style="font-size:0.72rem;color:var(--muted);align-self:center;margin-right:0.25rem;">Secciones:</span>` +
          tocItems.map(t => `<a class="toc-chip" href="#${t.id}" onclick="event.preventDefault();document.getElementById('${t.id}')?.scrollIntoView({behavior:'smooth',block:'start'})">${escapeHtml(t.title)}</a>`).join('') +
          `</div>`
        : '';

      const docObj = [...DATA.notas, ...DATA.ofertas].find(d => d.filename === docFilename);
      const stats = docObj ? getDocStats(docObj) : { total: 0, done: 0, pct: 0 };
      if (stats.total > 0) {
        const banner = `
          <div class="study-progress-card" id="progress-banner-${escapeHtml(docFilename)}">
            <div class="study-progress-top">
              <div class="study-progress-title">
                ${ICONS.check}
                <span>Progreso sincronizado con PWA móvil</span>
                <span class="badge badge-green" id="progress-badge-txt"><span class="dot"></span> ${stats.done} / ${stats.total} completados (${stats.pct}%)</span>
              </div>
              <div class="study-progress-controls">
                <button class="btn btn-sm ${checkFilterMode === 'all' ? 'btn-primary' : ''}" onclick="setCheckFilter('all')">Todos (${stats.total})</button>
                <button class="btn btn-sm ${checkFilterMode === 'pending' ? 'btn-primary' : ''}" onclick="setCheckFilter('pending')">Pendientes (${stats.total - stats.done})</button>
                <button class="btn btn-sm ${checkFilterMode === 'done' ? 'btn-primary' : ''}" onclick="setCheckFilter('done')">Completados (${stats.done})</button>
                <button class="btn btn-sm" onclick="resetDocChecks('${escapeHtml(docFilename)}')">Restablecer</button>
              </div>
            </div>
            <div class="study-progress-track">
              <div class="study-progress-fill" id="progress-bar-fill" style="width: ${stats.pct}%"></div>
            </div>
          </div>
        `;
        return banner + tocHtml + htmlOut;
      }

      return tocHtml + htmlOut;
    }

    window.toggleDashQuoteBlur = function(btn) {
      const bq = btn.closest('blockquote');
      if (!bq) return;
      const body = bq.querySelector('.dash-quote-body');
      if (!body) return;
      const blurred = body.classList.toggle('dash-quote-blur');
      btn.textContent = blurred ? 'Mostrar respuesta' : 'Ocultar / Ensayar';
    };

    window.speakDashQuote = function(btn) {
      if (!('speechSynthesis' in window)) return;
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        btn.textContent = 'Escuchar';
        return;
      }
      const bq = btn.closest('blockquote');
      const body = bq ? bq.querySelector('.dash-quote-body') : null;
      if (!body) return;
      const txt = body.innerText.replace(/["“”]/g, '').trim();
      const u = new SpeechSynthesisUtterance(txt);
      u.lang = /\b(Hi, I'm|Throughout my career|Currently, I'm)\b/i.test(txt) ? 'en-US' : 'es-MX';
      u.rate = 1.02;
      btn.textContent = 'Detener';
      u.onend = () => { btn.textContent = 'Escuchar'; };
      u.onerror = () => { btn.textContent = 'Escuchar'; };
      window.speechSynthesis.speak(u);
    };

    window.addEventListener('storage', (e) => {
      if (e.key === CHECK_STORAGE_KEY && DATA) {
        renderDocCollection('notas', document.getElementById('q-notas')?.value || '');
        renderDocCollection('ofertas', document.getElementById('q-ofertas')?.value || '');
      }
    });

    window.toggleCheckRow = function(liEl, docFilename, lineIdx) {
      const key = decodeURIComponent(liEl.getAttribute('data-check-key') || '');
      if (!key) return;
      const saved = loadSavedChecks();
      const currentlyChecked = liEl.classList.contains('is-checked');
      const nextChecked = !currentlyChecked;
      saved[key] = nextChecked;
      saveChecksMap(saved);

      liEl.classList.toggle('is-checked', nextChecked);
      if ((checkFilterMode === 'pending' && nextChecked) || (checkFilterMode === 'done' && !nextChecked)) {
        liEl.classList.add('hidden');
      }

      // Intentar sincronizar con servidor local si está activo
      fetch('/api/toggle-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: docFilename, lineIdx, checked: nextChecked })
      }).catch(() => {});

      const type = DATA.notas.some(d => d.filename === docFilename) ? 'notas' : 'ofertas';
      const filterInput = document.getElementById(type === 'ofertas' ? 'q-ofertas' : 'q-notas');
      renderDocCollection(type, filterInput ? filterInput.value : '');
    };

    window.setCheckFilter = function(mode) {
      checkFilterMode = mode;
      renderDocCollection('notas', document.getElementById('q-notas')?.value || '');
      renderDocCollection('ofertas', document.getElementById('q-ofertas')?.value || '');
    };

    window.resetDocChecks = function(docFilename) {
      const saved = loadSavedChecks();
      const prefix = `${docFilename}::`;
      Object.keys(saved).forEach(k => {
        if (k.startsWith(prefix)) delete saved[k];
      });
      saveChecksMap(saved);
      const type = DATA.notas.some(d => d.filename === docFilename) ? 'notas' : 'ofertas';
      const filterInput = document.getElementById(type === 'ofertas' ? 'q-ofertas' : 'q-notas');
      renderDocCollection(type, filterInput ? filterInput.value : '');
    };

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === tabId);
      });
      document.querySelectorAll('.tab-panel').forEach(p => {
        p.classList.toggle('hidden', p.id !== tabId);
      });
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
      if (btn.dataset.tab) btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    function renderFollowupStrip() {
      const strip = document.getElementById('followup-strip');
      if (!strip || !DATA.rows) return;
      const todayIso = new Date().toISOString().slice(0, 10);
      const upcoming = DATA.rows
        .filter(r => r.stage !== 'cerrada' && r.fecha_seguimiento)
        .sort((a, b) => a.fecha_seguimiento.localeCompare(b.fecha_seguimiento))
        .slice(0, 6);
      if (!upcoming.length) {
        strip.style.display = 'none';
        return;
      }
      strip.innerHTML = `
        <div class="followup-head">
          <span>${ICONS.clock} Agenda CRM &middot; Próximos seguimientos y entrevistas</span>
          <span class="badge badge-blue"><span class="dot"></span> Corte hoy: ${todayIso}</span>
        </div>
        <div class="followup-list">
          ${upcoming.map(r => {
            const isDue = r.fecha_seguimiento <= todayIso;
            const bCls = r.stage === 'en_proceso' ? 'badge-green' : (isDue ? 'badge-amber' : 'badge-blue');
            return `
              <div class="followup-item">
                <div style="min-width:0">
                  <div style="font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(r.empresa)}</div>
                  <div style="color:var(--muted);font-size:0.73rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(r.proxima_accion)}</div>
                </div>
                <div style="display:flex;align-items:center;gap:0.35rem;flex-shrink:0;">
                  <span class="badge ${bCls}"><span class="dot"></span> ${escapeHtml(r.fecha_seguimiento)}</span>
                  ${r.ficha_file ? `<button class="btn btn-sm" onclick="openDoc('ofertas','${escapeHtml(r.ficha_file)}')">Ficha</button>` : ''}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    function renderKanban() {
      const cols = [
        { key: 'en_proceso', title: 'En proceso / Entrevista técnica', badge: 'badge-green', ico: 'check' },
        { key: 'activa', title: 'Postuladas en espera activa', badge: 'badge-blue', ico: 'clock' },
        { key: 'cerrada', title: 'Vacante cerrada en portal', badge: 'badge-amber', ico: 'archive' },
      ];
      const board = document.getElementById('kanban-board');
      board.innerHTML = cols.map(col => {
        const items = DATA.rows.filter(r => r.stage === col.key);
        const cards = items.map(r => `
          <div class="k-card">
            <div class="k-card-title">
              <span>${ICONS[col.ico]} ${escapeHtml(r.empresa)}</span>
              <span class="badge ${col.badge}"><span class="dot"></span> ${escapeHtml(r.fecha)}</span>
            </div>
            <div class="k-card-role">${escapeHtml(r.puesto)}</div>
            <div class="k-card-meta">
              <div class="meta-row">
                <span class="meta-label">${ICONS.dollar} Salario:</span>
                <span class="meta-val">${escapeHtml(r.salario)}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">${ICONS.arrow} Acción:</span>
                <span class="meta-val">${escapeHtml(r.proxima_accion)}</span>
              </div>
            </div>
            <div style="margin-top: 0.4rem; display: flex; gap: 0.4rem; flex-wrap: wrap;">
              ${r.ficha_file ? `<button class="btn btn-sm btn-primary" onclick="openDoc('ofertas', '${escapeHtml(r.ficha_file)}')">${ICONS.file} Ficha técnica</button>` : ''}
              ${r.url_vacante ? `<a class="btn btn-sm" href="${escapeHtml(r.url_vacante)}" target="_blank" rel="noopener">${ICONS.external} Ver vacante</a>` : ''}
            </div>
          </div>
        `).join('');
        return `
          <div class="kanban-col">
            <div class="kanban-col-header">
              <span>${ICONS[col.ico]} ${col.title}</span>
              <span class="badge ${col.badge}"><span class="dot"></span> ${items.length}</span>
            </div>
            ${cards}
          </div>
        `;
      }).join('');
    }

    function renderTable(term = '') {
      const q = term.toLowerCase();
      const tbody = document.getElementById('tbl-body');
      tbody.innerHTML = DATA.rows
        .filter(r => !q || Object.values(r).join(' ').toLowerCase().includes(q))
        .map(r => {
          const badgeCls = r.stage === 'en_proceso' ? 'badge-green' : (r.stage === 'cerrada' ? 'badge-amber' : 'badge-blue');
          return `
            <tr>
              <td data-label="Fecha" style="white-space:nowrap; font-family:ui-monospace,monospace; font-size:0.78rem;">${escapeHtml(r.fecha)}</td>
              <td data-label="Empresa"><strong>${escapeHtml(r.empresa)}</strong><div style="font-size:0.72rem;color:var(--muted)">${escapeHtml(r.fuente)}</div></td>
              <td data-label="Puesto"><a href="${escapeHtml(r.url_vacante)}" target="_blank" rel="noopener">${escapeHtml(r.puesto)}</a></td>
              <td data-label="Estado"><span class="badge ${badgeCls}"><span class="dot"></span> ${escapeHtml(r.estado)}</span></td>
              <td data-label="Próxima acción">${escapeHtml(r.proxima_accion)}</td>
              <td data-label="Seguimiento" style="white-space:nowrap; font-family:ui-monospace,monospace; font-size:0.78rem;">${escapeHtml(r.fecha_seguimiento)}</td>
              <td data-label="Compensación">${escapeHtml(r.salario)}</td>
              <td data-label="Ficha">${r.ficha_file ? `<button class="btn btn-sm" onclick="openDoc('ofertas','${escapeHtml(r.ficha_file)}')">${ICONS.file} Ficha</button>` : '&mdash;'}</td>
            </tr>
          `;
        }).join('');
    }

    document.getElementById('q-table').addEventListener('input', e => { if (DATA) renderTable(e.target.value); });

    let activeOferta = '';
    let activeNota = '';

    function renderDocCollection(type, filterTerm = '') {
      const list = type === 'ofertas' ? DATA.ofertas : DATA.notas;
      const activeFile = type === 'ofertas' ? activeOferta : activeNota;
      const listEl = document.getElementById(`${type}-list`);
      const viewerEl = document.getElementById(`${type}-viewer`);
      const q = filterTerm.toLowerCase();

      const filtered = list.filter(d => !q || d.title.toLowerCase().includes(q) || d.content.toLowerCase().includes(q));
      listEl.innerHTML = filtered.map(d => {
        const st = getDocStats(d);
        const progressBadge = st.total > 0
          ? `<span class="badge ${st.done === st.total ? 'badge-green' : 'badge-blue'}" style="margin-left:auto; font-size:0.68rem; padding:0.1rem 0.4rem;">${st.done}/${st.total}</span>`
          : '';
        return `
          <button class="doc-item ${d.filename === activeFile ? 'active' : ''}" onclick="openDoc('${type}', '${escapeHtml(d.filename)}')">
            <div class="doc-item-title">${ICONS.file} <span style="flex:1">${escapeHtml(d.title)}</span> ${progressBadge}</div>
            <div class="doc-item-sub">${escapeHtml(d.filename)}</div>
          </button>
        `;
      }).join('');

      const currentDoc = filtered.find(d => d.filename === activeFile) || filtered[0] || list[0];
      if (currentDoc) {
        viewerEl.innerHTML = renderMarkdown(currentDoc.content, currentDoc.filename);
      }
    }

    window.openDoc = function(type, filename) {
      if (type === 'ofertas') {
        activeOferta = filename;
        switchTab('tab-ofertas');
        renderDocCollection('ofertas', document.getElementById('q-ofertas').value);
      } else {
        activeNota = filename;
        switchTab('tab-notas');
        renderDocCollection('notas', document.getElementById('q-notas')?.value || '');
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.filterOffersBySkill = function(skillName) {
      const qEl = document.getElementById('q-ofertas');
      if (qEl) qEl.value = skillName;
      switchTab('tab-ofertas');
      renderDocCollection('ofertas', skillName);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    document.getElementById('q-ofertas').addEventListener('input', e => renderDocCollection('ofertas', e.target.value));
    const qNotasEl = document.getElementById('q-notas');
    if (qNotasEl) qNotasEl.addEventListener('input', e => renderDocCollection('notas', e.target.value));

    function renderSkillsAndCvs() {
      const maxOffers = Math.max(...DATA.skills.map(s => s.offers), 1);
      document.getElementById('skills-bars').innerHTML = DATA.skills.map(s => `
        <div class="skill-row" title="Clic para filtrar fichas que piden ${escapeHtml(s.name)}" onclick="filterOffersBySkill('${escapeHtml(s.name.split('/')[0].trim())}')">
          <span style="font-weight:600">${escapeHtml(s.name)}</span>
          <div class="skill-bar-bg">
            <div class="skill-bar-fill" style="width: ${Math.round((s.offers / maxOffers) * 100)}%"></div>
          </div>
          <span style="text-align: right; color: var(--muted); font-size: 0.78rem; font-family:ui-monospace,monospace;">
            ${s.offers}/${DATA.totalOffers} (${s.pct}%)
          </span>
        </div>
      `).join('');

      document.getElementById('pdfs-grid').innerHTML = DATA.pdfs.map(p => `
        <div class="cv-card">
          <div>
            <div style="font-weight: 600; font-size: 0.84rem; word-break: break-all; color:#fff;">${escapeHtml(p.filename)}</div>
            <div style="font-size: 0.74rem; color: var(--muted); margin-top: 0.25rem;">PDF oficial &middot; ${p.size_kb} KB</div>
          </div>
          <div>
            <a class="btn btn-sm btn-primary" href="${escapeHtml(p.href)}" target="_blank" rel="noopener">${ICONS.external} Abrir PDF</a>
          </div>
        </div>
      `).join('');

      document.getElementById('html-cvs-grid').innerHTML = DATA.htmlCvs.map(c => `
        <div class="cv-card">
          <div style="font-weight: 600; font-size: 0.84rem; word-break: break-all; color:#fff;">${escapeHtml(c.filename)}</div>
          <div>
            <a class="btn btn-sm" href="${escapeHtml(c.href)}" target="_blank" rel="noopener">${ICONS.code} Ver fuente HTML</a>
          </div>
        </div>
      `).join('');
    }

    function updateAlproCountdown() {
      const el = document.getElementById('alpro-countdown');
      if (!el) return;
      const target = new Date('2026-10-26T16:00:00-06:00').getTime();
      const diff = target - Date.now();
      if (diff > 0) {
        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        el.textContent = `Faltan ${d}d ${h}h ${m}m`;
      } else if (diff > -3600000) {
        el.textContent = 'En curso ahora (4:00 PM)';
      } else {
        el.textContent = 'Entrevista completada';
      }
    }

    function renderPriorityBanners() {
      const bannerEl = document.getElementById('priority-banner');
      if (!bannerEl || !DATA.priorityBanners || !DATA.priorityBanners.length) return;
      bannerEl.innerHTML = DATA.priorityBanners.map((b, idx) => {
        const tagsHtml = b.tags.map(t => {
          const ico = ICONS[t.icon] || ICONS.check;
          return `<div class="p-tag-item"><span class="p-tag-lbl">${ico} ${escapeHtml(t.lbl)}</span><span>${escapeHtml(t.val)}</span></div>`;
        }).join('');
        const actionsHtml = b.actions.map(a => {
          if (a.href) {
            return `<a class="${escapeHtml(a.btnClass)}" href="${escapeHtml(a.href)}" target="_blank" rel="noopener">${ICONS.external} ${escapeHtml(a.label)}</a>`;
          }
          const ico = a.btnClass.includes('btn-success') ? ICONS.file : ICONS.external;
          return `<button class="${escapeHtml(a.btnClass)}" onclick="openDoc('${escapeHtml(a.type)}', '${escapeHtml(a.file)}')">${ico} ${escapeHtml(a.label)}</button>`;
        }).join('');
        const countdownBadge = idx === 0
          ? `<span class="badge badge-amber" id="alpro-countdown" style="margin-left:auto;">Calculando...</span>`
          : '';
        return `
          <div class="p-card p-card-primary">
            <div>
              <div class="p-card-header" style="flex-wrap:wrap;">
                <span class="badge badge-green"><span class="dot"></span> ${b.priority}</span>
                ${countdownBadge}
                <span class="badge badge-blue">${escapeHtml(b.stageBadge)}</span>
              </div>
              <h3>${b.title}</h3>
              <div class="p-tags">${tagsHtml}</div>
            </div>
            <div class="p-actions">${actionsHtml}</div>
          </div>
        `;
      }).join('');
      updateAlproCountdown();
      setInterval(updateAlproCountdown, 30000);
    }

    function initDashboard() {
      const setTxt = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };
      setTxt('kpi-total', DATA.total);
      setTxt('kpi-en-proceso', DATA.enProcesoCount);
      setTxt('kpi-conversion', DATA.conversionRate);
      setTxt('kpi-activas', DATA.activasCount);
      setTxt('ofertas-count-badge', DATA.ofertas ? DATA.ofertas.length : 0);
      setTxt('skills-total-count', DATA.totalOffers || 0);
      setTxt('corte-date', DATA.generatedAt || '');

      if (DATA.rows && DATA.rows.length) {
        const dates = DATA.rows.map(r => r.fecha).filter(Boolean).sort();
        const subTotal = document.getElementById('kpi-sub-total');
        if (subTotal && dates.length) {
          subTotal.innerHTML = `${ICONS.clock} ${dates[0]} a ${dates[dates.length - 1]}`;
        }
        const procNames = DATA.rows.filter(r => r.stage === 'en_proceso').map(r => r.empresa.split('(')[0].trim());
        const subProc = document.getElementById('kpi-sub-proceso');
        if (subProc && procNames.length) {
          subProc.innerHTML = `${ICONS.check} ${escapeHtml(procNames.join(' + '))}`;
        }
        const subAct = document.getElementById('kpi-sub-activas');
        if (subAct) {
          subAct.innerHTML = `${ICONS.clock} ${DATA.activasCount} activas &middot; ${DATA.cerradasCount || 0} cerradas en portal`;
        }
      }

      activeOferta = DATA.ofertas[0]?.filename || '';
      activeNota = DATA.notas[0]?.filename || '';

      renderPriorityBanners();
      renderFollowupStrip();
      renderKanban();
      renderTable();
      renderDocCollection('ofertas');
      renderDocCollection('notas');
      renderSkillsAndCvs();

      const headerEl = document.querySelector('header');
      const mainEl = document.querySelector('main');
      if (headerEl) headerEl.style.display = 'block';
      if (mainEl) mainEl.style.display = 'block';
      const btnLock = document.getElementById('btn-lock');
      if (btnLock && ENCRYPTED_PAYLOAD) {
        btnLock.style.display = 'inline-flex';
      }
    }

    if (ENCRYPTED_PAYLOAD) {
      const headerEl = document.querySelector('header');
      const mainEl = document.querySelector('main');
      if (headerEl) headerEl.style.display = 'none';
      if (mainEl) mainEl.style.display = 'none';
      const lockEl = document.getElementById('lock-screen');
      if (lockEl) lockEl.style.display = 'flex';
      const savedPass = localStorage.getItem(STORAGE_PASS_KEY) || sessionStorage.getItem(STORAGE_PASS_KEY);
      if (savedPass) {
        attemptUnlock(savedPass, true);
      } else {
        const passIn = document.getElementById('lock-pass');
        if (passIn) setTimeout(() => passIn.focus(), 100);
      }
    } else {
      initDashboard();
    }
  </script>
</body>
</html>
"""


def encrypt_payload(payload_dict, password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import hashlib
    import base64

    plaintext = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000, dklen=32)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)
    return {
        "salt": base64.b64encode(salt).decode("utf-8"),
        "iv": base64.b64encode(iv).decode("utf-8"),
        "data": base64.b64encode(ciphertext).decode("utf-8"),
    }


def cmd_report(args):
    rows = load_rows()
    out_path = args.out or DEFAULT_HTML_OUT
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    total_offers, skills_list = compute_skills()

    priority_ofertas = [
        "2026-10-16_ALPRO_Hireline_FullStack_Engineer_SaaS.md",
        "2026-10-13_Afya_Medik_Programador_Jr_AI_Native.md",
        "2026-10-13_ALTEN_Jr_FrontEnd.md",
        "2026-10-19_Accenture_Academia_Java_APX.md",
        "2026-10-23_Thomson_Reuters_Software_Engineer.md",
        "2026-10-23_LEXA_Consulting_Desarrollador_BackEnd_Puebla.md",
        "2026-10-22_ED3_Group_Programador_Junior.md",
        "2026-10-21_Salesforce_Software_Engineer_Jr_Automation.md",
        "2026-10-21_Hireline_FullStack_IA.md",
        "2026-10-16_Ellucian_Software_Engineer_I_Puebla.md",
        "2026-10-16_Neumo_Jr_Software_Engineer_MX.md",
        "2026-10-16_Metrica_Frontend_Angular_Jr.md",
        "2026-10-13_Datamatic_Software_AI_Developer.md",
    ]
    ofertas_docs = load_markdown_collection(OFERTAS_DIR, priority_ofertas)

    priority_notas = [
        "ROADMAP_ACTIVIDADES_OCTUBRE.md",
        "DEFENSA_CV.md",
        "PLAN_ESTUDIO_POSTULACIONES.md",
        "GUIA_ENTREVISTA_NGICAJA.md",
        "ESTRATEGIA_NETWORKING_LINKEDIN.md",
        "GUIA_ENTREVISTA_ACCENTURE_JAVA.md",
        "GUIA_MEJORA_INGLES_EFSET.md",
        "GUIA_ENTREVISTA_TECNICA_BM_ALTEN.md",
        "PLAN_CERTIFICACIONES.md",
        "ACCIONES_MANUALES.md",
        "ROADMAP_BUSQUEDA.md",
        "PRIORIDAD_PLATAFORMAS.md",
        "HORARIO.md",
    ]
    notas_docs = load_markdown_collection(NOTAS_DIR, priority_notas)

    pdfs_list = []
    if os.path.isdir(PDFS_DIR):
        for fname in sorted(os.listdir(PDFS_DIR)):
            if fname.endswith(".pdf"):
                fsize_kb = round(os.path.getsize(os.path.join(PDFS_DIR, fname)) / 1024, 1)
                pdfs_list.append({"filename": fname, "href": f"../pdfs_oficiales/{fname}", "size_kb": fsize_kb})

    html_cvs_list = []
    if os.path.isdir(HTML_CV_DIR):
        for fname in sorted(os.listdir(HTML_CV_DIR)):
            if fname.endswith(".html"):
                html_cvs_list.append({"filename": fname, "href": f"../fuentes_html/{fname}"})

    en_proceso = []
    activas = []
    cerradas = []
    for r in rows:
        est = (r.get("estado") or "").lower()
        notas_txt = (r.get("notas") or "").lower()
        r_copy = dict(r)
        r_copy["proxima_accion"] = strip_emojis(r.get("proxima_accion", ""))
        r_copy["notas"] = strip_emojis(r.get("notas", ""))
        r_copy["salario"] = strip_emojis(r.get("salario", ""))
        ficha_m = re.search(r"Ficha:\s*(ofertas/[^\s.]+\.md)", r.get("notas") or "")
        r_copy["ficha_file"] = os.path.basename(ficha_m.group(1)) if ficha_m else ""
        if "proceso" in est or "entrevista" in est or "contacto" in est:
            r_copy["stage"] = "en_proceso"
            en_proceso.append(r_copy)
        elif "cerrada o caducada" in notas_txt or "rechaz" in est:
            r_copy["stage"] = "cerrada"
            cerradas.append(r_copy)
        else:
            r_copy["stage"] = "activa"
            activas.append(r_copy)

    priority_banners = [
        {
            "priority": "Prioridad 1 &middot; Lunes 26 de octubre (4:00 PM)",
            "stageBadge": "Entrevista Agendada (Meet)",
            "title": "ALPRO (alpro.ai) &mdash; Full-Stack Engineer &middot; SaaS B2B PropTech",
            "tags": [
                {"lbl": "Modalidad", "val": "100% Remoto México (Horario CDMX) &middot; $25,000–$35,000 MXN est.", "icon": "home"},
                {"lbl": "Entrevistadores", "val": "Ricardo Cruz (Co-founder) y Jesús Soto (Tech Lead) &middot; 3 bloques de 10 min", "icon": "briefcase"},
                {"lbl": "Stack", "val": "React, Vite, Node.js, Express, TypeScript, PostgreSQL RLS, 1,082 Tests", "icon": "code"},
            ],
            "actions": [
                {"btnClass": "btn btn-success", "label": "Entrar a Google Meet (4:00 PM)", "href": "https://meet.google.com/tyf-rpzr-gad"},
                {"btnClass": "btn btn-primary", "label": "Ficha ALPRO", "type": "ofertas", "file": "2026-10-16_ALPRO_Hireline_FullStack_Engineer_SaaS.md"},
                {"btnClass": "btn", "label": "Biblia Defensa CV", "type": "notas", "file": "DEFENSA_CV.md"},
                {"btnClass": "btn", "label": "Guion y Manual Técnico", "type": "notas", "file": "PLAN_ESTUDIO_POSTULACIONES.md"},
                {"btnClass": "btn", "label": "Arquitectura NgiCaja & CV", "type": "notas", "file": "GUIA_ENTREVISTA_NGICAJA.md"},
                {"btnClass": "btn", "label": "Networking LinkedIn (4:35 PM)", "type": "notas", "file": "ESTRATEGIA_NETWORKING_LINKEDIN.md"},
            ],
        },
        {
            "priority": "Prioridad 2 &middot; Semana 26&ndash;30 de octubre",
            "stageBadge": "Técnica pendiente",
            "title": "AMK Farma (Afya Medik) &mdash; Programador/a Junior AI Native",
            "tags": [
                {"lbl": "Modalidad", "val": "100% Remoto (confirmado en llamada)", "icon": "home"},
                {"lbl": "Salario", "val": "$16,200 netos + vales ($18,000 MXN libres)", "icon": "dollar"},
                {"lbl": "Stack Técnico", "val": "TypeScript, Webhooks, n8n, SQL y validación de código IA", "icon": "code"},
            ],
            "actions": [
                {"btnClass": "btn btn-success", "label": "Guía técnica AMK", "type": "ofertas", "file": "2026-10-13_Afya_Medik_Programador_Jr_AI_Native.md"},
                {"btnClass": "btn", "label": "Agenda semanal", "type": "notas", "file": "ROADMAP_ACTIVIDADES_OCTUBRE.md"},
                {"btnClass": "btn", "label": "Plan certificaciones", "type": "notas", "file": "PLAN_CERTIFICACIONES.md"},
            ],
        },
        {
            "priority": "Prioridad 3 &middot; Seguimiento Martes 27 de octubre",
            "stageBadge": "Feedback E2 / Referido",
            "title": "ALTEN México (Provident) &amp; Accenture (Java APX)",
            "tags": [
                {"lbl": "ALTEN", "val": "Entrevista E2 (Técnica + BM) completada el 20/oct &middot; En espera de resolución", "icon": "mapPin"},
                {"lbl": "Accenture", "val": "Referido interno gestionado por Ricardo Vallejo con Talent Acquisition", "icon": "briefcase"},
            ],
            "actions": [
                {"btnClass": "btn btn-success", "label": "Ficha ALTEN", "type": "ofertas", "file": "2026-10-13_ALTEN_Jr_FrontEnd.md"},
                {"btnClass": "btn", "label": "Guía Java Accenture", "type": "notas", "file": "GUIA_ENTREVISTA_ACCENTURE_JAVA.md"},
            ],
        },
    ]

    payload = {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(rows),
        "enProcesoCount": len(en_proceso),
        "activasCount": len(activas),
        "cerradasCount": len(cerradas),
        "conversionRate": round((len(en_proceso) / len(rows)) * 100, 1) if rows else 0,
        "rows": en_proceso + activas + cerradas,
        "skills": skills_list,
        "totalOffers": total_offers,
        "ofertas": ofertas_docs,
        "notas": notas_docs,
        "pdfs": pdfs_list,
        "htmlCvs": html_cvs_list,
        "priorityBanners": priority_banners,
    }

    # Revisar si se debe cifrar el dashboard
    secret_path = os.path.join(ROOT_DIR, ".dashboard_secret")
    pwd = getattr(args, "password", None) or os.environ.get("DASHBOARD_PASSWORD")
    if not pwd and os.path.isfile(secret_path):
        with open(secret_path, "r", encoding="utf-8") as sf:
            pwd = sf.read().strip()

    if pwd and not getattr(args, "no_encrypt", False):
        enc_pack = encrypt_payload(payload, pwd)
        payload_json = "null"
        encrypted_json = json.dumps(enc_pack)
        total_disp = "--"
        en_proceso_disp = "--"
        conversion_disp = "--"
        activas_disp = "--"
        total_offers_disp = "--"
        ofertas_count_disp = "--"
        corte_disp = "Protegido"
        status_msg = "Cifrado con AES-256-GCM"
        lock_style = "display:flex;"
        header_style = "display:none;"
        main_style = "display:none;"
    else:
        encrypted_json = "null"
        payload_json = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")
        total_disp = str(payload["total"])
        en_proceso_disp = str(payload["enProcesoCount"])
        conversion_disp = str(payload["conversionRate"])
        activas_disp = str(payload["activasCount"])
        total_offers_disp = str(payload["totalOffers"])
        ofertas_count_disp = str(len(ofertas_docs))
        corte_disp = payload["generatedAt"]
        status_msg = "Sin cifrar"
        lock_style = "display:none;"
        header_style = ""
        main_style = ""

    doc = (
        HTML_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)
        .replace("__ENCRYPTED_PAYLOAD_JSON__", encrypted_json)
        .replace("__LOCK_STYLE__", lock_style)
        .replace("__HEADER_STYLE__", header_style)
        .replace("__MAIN_STYLE__", main_style)
        .replace("__GENERATED_AT__", corte_disp)
        .replace("__TOTAL__", total_disp)
        .replace("__EN_PROCESO_COUNT__", en_proceso_disp)
        .replace("__CONVERSION_RATE__", conversion_disp)
        .replace("__ACTIVAS_COUNT__", activas_disp)
        .replace("__TOTAL_OFFERS__", total_offers_disp)
        .replace("__OFERTAS_COUNT__", ofertas_count_disp)
        .replace("__CANDIDATE_NAME__", html.escape(CANDIDATE_NAME))
        .replace("__CANDIDATE_INITIALS__", html.escape(CANDIDATE_INITIALS))
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Dashboard generado en: {out_path} [{status_msg}]")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Tracker local de postulaciones (dev-job-hub)")
    sub = parser.add_subparsers(dest="cmd")

    p_f = sub.add_parser("followup", help="Revisa postulaciones con seguimiento vencido o proximo")
    p_f.add_argument("--days", type=int, default=7, help="Ventana de dias proximos (default: 7)")
    p_f.add_argument("--today", type=str, default=None, help="Fecha corte ISO YYYY-MM-DD")
    p_f.add_argument("--format", choices=["text", "json"], default="text")

    p_s = sub.add_parser("skills", help="Analiza demanda de tecnologias en el CSV y ofertas/")
    p_s.add_argument("--format", choices=["text", "json"], default="text")

    p_r = sub.add_parser("report", help="Genera dashboard HTML offline desde el CSV")
    p_r.add_argument("--out", type=str, default=None, help="Ruta de salida del HTML")
    p_r.add_argument("--password", type=str, default=None, help="Clave secreta para cifrar el dashboard")
    p_r.add_argument("--no-encrypt", action="store_true", help="Desactivar cifrado aunque exista .dashboard_secret")

    args = parser.parse_args()
    if args.cmd == "followup":
        return cmd_followup(args)
    if args.cmd == "skills":
        return cmd_skills(args)
    if args.cmd == "report":
        return cmd_report(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

