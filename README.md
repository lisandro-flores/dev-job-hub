# 🎯 dev-job-hub

> **Local-first developer job search, tracking pipeline and interview prep toolkit.**  
> *Gestiona tu búsqueda de empleo tech como código: 100% privado, sin bases de datos externas, sin suscripciones y con cero dependencias externas.*

[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20(native%20only)-brightgreen)](package.json)
[![Node.js](https://img.shields.io/badge/node.js-%3E%3D22.6-blue)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Local-First](https://img.shields.io/badge/data-100%25%20local%20%26%20git--native-success)](#-privacidad-y-filosofía-local-first)

---

## ⚡ ¿Por qué `dev-job-hub`?

La mayoría de herramientas para buscar empleo en tecnología caen en dos extremos: o son hojas de cálculo manuales y desordenadas, o son plataformas SaaS de pago que venden tus datos y te atan a sus interfaces.

`dev-job-hub` unifica todo el ciclo de búsqueda en una herramienta para desarrolladores:

1. **Buscador Multi-Fuente CLI:** Motores de búsqueda integrados para **Get on Board** (LATAM y Remoto), **Hireline** (TI en México), **LinkedIn** (búsqueda pública global) y **Freehire** (agregador global de más de 50 ATS).
2. **Sin dependencias JavaScript:** Los CLIs usan APIs nativas de Node.js. El cifrado del dashboard requiere opcionalmente `cryptography` y los iconos PNG de la PWA requieren opcionalmente Pillow.
3. **Pipeline en Texto Plano (Git-Native):** Tu embudo vive en un archivo `CSV` estructurado y fichas en `Markdown`. Si sabes usar Git, sabes usar `dev-job-hub`.
4. **Mapa de Calor de Habilidades (`skills`):** Analiza automáticamente las ofertas guardadas y te muestra qué tecnologías, frameworks y librerías son las más demandadas en tu mercado objetivo.
5. **Centro de Mando Offline & PWA Móvil:** Genera un dashboard HTML interactivo con búsqueda, métricas de conversión, modo entrevista y una aplicación web progresiva (PWA) para repasar notas técnicas desde el teléfono sin conexión.
6. **Listo para Agentes de IA:** Incluye skills (`SKILL.md`) listos para usar con asistentes como **Antigravity**, **Cursor**, **Claude Code** o **Cline**.

> Requisitos: Node.js 22.6+ y Python 3.8+. La búsqueda requiere conexión; el tracker y la PWA generada funcionan localmente.

---

## 🚀 Inicio Rápido (3 Pasos)

### 1. Clonar el repositorio y preparar tu archivo de seguimiento

```bash
git clone https://github.com/tu-usuario/dev-job-hub.git
cd dev-job-hub

# Copia la plantilla base de seguimiento
cp templates/SEGUIMIENTO.template.csv SEGUIMIENTO_POSTULACIONES.csv
```

### 2. Buscar vacantes desde la terminal

```bash
# Buscar vacantes remotas de React en Get on Board (LATAM)
npm run search:getonbrd -- "react" --remote --format table

# Buscar vacantes de TypeScript en Hireline (México)
npm run search:hireline -- "typescript" --location remoto --format table

# Buscar vacantes en LinkedIn por ubicación
npm run search:linkedin -- -q "frontend developer" -l "Remote" --format table

# Buscar en 50+ ATS con Freehire
npm run search:freehire -- -q "full stack" --seniority junior --format table
```

### 3. Iniciar el Centro de Mando interactivo

```bash
npm start
```
Abre tu navegador en `http://localhost:4321/postulaciones/dashboard_postulaciones.html` para ver tu embudo, métricas y checklists sincronizados en tiempo real.

---

## 🛠️ Herramientas y Comandos

### 🔍 1. Motores de Búsqueda de Empleo

| Comando | Portal / Fuente | Alcance | Flags útiles |
|---|---|---|---|
| `npm run search:getonbrd -- <query>` | **Get on Board** | Startups & Tech LATAM / Remoto | `--remote`, `--country Mexico`, `--seniority junior` |
| `npm run search:hireline -- <query>` | **Hireline** | Tech & TI en México | `-l remoto`, `-l puebla`, `-l ciudad-de-mexico` |
| `npm run search:linkedin -- -l <loc>` | **LinkedIn** | Global / Cualquier país | `-q "react"`, `-l "Remote"`, `--jobage 7` |
| `npm run search:freehire -- -q <query>` | **Freehire** | 50+ ATS internacionales | `--region latam,us`, `--remote remote`, `--seniority senior` |

> *Para ver la descripción completa de una vacante, utiliza el subcomando `detail`:*
> ```bash
> node --no-warnings cli/search/getonbrd/src/cli.ts detail "<slug-o-id>"
> ```

---

### 📊 2. Tracker y Análisis de Postulaciones

#### Alertas de Seguimiento (`followup`)
Revisa postulaciones que requieren acción hoy o en los próximos 7 días:
```bash
npm run tracker:followup
# O personalizar la ventana de días:
python3 cli/tracker/tracker.py followup --days 14
```

#### Validar datos (`validate`)
Comprueba que el CSV tenga todas las columnas esperadas y fechas ISO válidas:
```bash
npm run tracker:validate
```

#### Mapa de Calor de Tecnologías (`skills`)
Escanea todas las fichas guardadas en `ofertas/*.md` y genera el reporte de demanda:
```bash
npm run tracker:skills
```

#### Generar Dashboard HTML Offline (`report`)
Genera un dashboard autocontenido en `postulaciones/dashboard_postulaciones.html` (soporta protección por contraseña opcional con cifrado AES-256-GCM):
```bash
npm run tracker:report
# Con protección por contraseña:
python3 cli/tracker/tracker.py report --password "mi-clave-secreta"
```

El cifrado requiere opcionalmente `cryptography`:
`python3 -m pip install cryptography`. Copia `dashboard_banners.example.json` como
`dashboard_banners.json` para agregar banners personales al dashboard; ese archivo está
ignorado por Git. No hay datos personales específicos embebidos en el código por defecto.

#### Generar Guía Móvil / PWA de Estudio (`study`)
Compila tus notas técnicas de `notas/*.md` en una PWA estática instalable en `sitio_estudio/`:
```bash
npm run tracker:study
```

---

## 📱 Modo Móvil & Despliegue en GitHub Pages

Puedes publicar la guía de estudio directamente a GitHub Pages con un solo comando:

```bash
npm run deploy:ghpages
```

Por seguridad, el script publica solo la PWA de estudio por defecto. El dashboard personal
solo se incluye si se solicita explícitamente y se proporciona una contraseña:

```bash
DASHBOARD_PASSWORD='mi-clave-secreta' npm run deploy:ghpages -- --include-dashboard
```

El script prepara un artefacto aislado con `.nojekyll` y lo sube a la rama `gh-pages`;
nunca publica un dashboard sin cifrar.

---

## 🤖 Integración con Agentes de IA

Si utilizas asistentes como **Antigravity**, **Cursor**, **Claude Code** o **Cline**, este repositorio incluye sus especificaciones estándar en `.agents/skills/`:

* `.agents/skills/getonbrd-search/`: Permite que la IA busque vacantes en Get on Board.
* `.agents/skills/hireline-search/`: Permite que la IA busque vacantes en Hireline.
* `.agents/skills/linkedin-search/`: Permite que la IA busque vacantes en LinkedIn.
* `.agents/skills/freehire-search/`: Permite que la IA busque vacantes en Freehire.
* `.agents/skills/postulaciones-tracker/`: Permite que la IA revise seguimientos, actualice el estado y consulte skills.

Ejemplo de prompt para tu agente:
> *"Busca 3 vacantes de React y TypeScript remotas en Get on Board, guarda los detalles en ofertas/ y añade una fila de seguimiento en SEGUIMIENTO_POSTULACIONES.csv."*

---

## 🔒 Privacidad y Filosofía Local-First

* **Tus datos te pertenecen:** El archivo `.gitignore` viene configurado para **nunca subir a Git tus postulaciones reales**, salarios negociados, contactos de reclutadores ni notas personales.
* **Sin telemetría ni trackers:** Cero llamadas ocultas a analíticas.
* **Independiente de la nube:** Todo corre en tu máquina y funciona al 100% sin conexión a internet una vez descargado.

---

## 📁 Estructura del Repositorio

```text
dev-job-hub/
├── README.md                      # Documentación y guía de uso
├── package.json                   # Scripts unificados de ejecución
├── LICENSE                        # Licencia MIT
├── .gitignore                     # Protección de privacidad de datos personales
│
├── templates/                     # Plantillas limpias para comenzar
│   ├── SEGUIMIENTO.template.csv   # Plantilla estructurada de postulaciones
│   ├── ofertas/ejemplo_vacante.md # Estructura recomendada para guardar una vacante
│   └── notas/PLAN_ESTUDIO.template.md
│
├── cli/                           # Herramientas de terminal (Zero Dependencies)
│   ├── search/                    # Motores de búsqueda
│   │   ├── getonbrd/
│   │   ├── hireline/
│   │   ├── linkedin/
│   │   └── freehire/
│   └── tracker/                   # Análisis, generación visual y servidor
│       ├── tracker.py
│       ├── study_site.py
│       └── server.ts
│
├── .agents/skills/                # Skills listos para agentes de IA
└── scripts/
    └── deploy_ghpages.sh          # Script de despliegue automatizado a GitHub Pages
```

## 🗺️ Roadmap

Consulta [`ROADMAP.md`](./ROADMAP.md) para ver el estado actual, las mejoras
priorizadas y los criterios de terminado del proyecto.

---

## 📄 Licencia

Distribuido bajo la Licencia **MIT**. Consulta [`LICENSE`](LICENSE) para más detalles.
