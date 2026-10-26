# Roadmap de `dev-job-hub`

Plan de evolución para mantener el proyecto útil como herramienta personal y
presentable como portafolio. El proyecto ya es funcional; las siguientes fases
priorizan mantenibilidad, confiabilidad y seguridad antes que añadir más
funcionalidades.

## Estado actual

**Estado:** usable para búsqueda y seguimiento personal  
**Calificación actual:** 8.9/10  
**Runtime:** Node.js 22.6+ y Python 3.8+  
**Validación disponible:**

```bash
npm test
npm run test:cli
npm run tracker:validate
```

## Fase 1 — Completada: seguridad y base de calidad

- [x] Evitar publicar el dashboard privado sin contraseña.
- [x] Publicar solo la PWA de estudio por defecto.
- [x] Eliminar datos personales hardcodeados del código.
- [x] Permitir banners personalizados mediante `dashboard_banners.json`.
- [x] Restringir el servidor local a `127.0.0.1`.
- [x] Bloquear acceso HTTP a CSV, Markdown, secretos y código fuente.
- [x] Validar requests de actualización de checklists.
- [x] Documentar Node.js, Python y la dependencia opcional `cryptography`.
- [x] Añadir pruebas Python.
- [x] Añadir fixtures y pruebas de parsers TypeScript.
- [x] Añadir validación del esquema y fechas del CSV.
- [x] Añadir CI con GitHub Actions.

## Fase 2 — Prioridad alta: mantenibilidad

### 2.1 Cliente HTTP compartido

Crear un helper común para Get on Board, Hireline, LinkedIn y Freehire.

Debe centralizar:

- timeout;
- reintentos ante `429` y `5xx`;
- backoff con jitter;
- User-Agent;
- errores estructurados;
- validación de respuestas;
- cancelación de requests.

**Criterio de terminado:** todos los buscadores comparten la misma política de
red y conservan sus formatos de salida actuales.

### 2.2 Modularización del tracker

Dividir [`cli/tracker/tracker.py`](./cli/tracker/tracker.py) sin cambiar la
salida pública:

```text
cli/tracker/
├── tracker.py
├── config.py
├── csv_store.py
├── followup.py
├── skills.py
├── report_data.py
├── report_template.py
├── encryption.py
└── markdown.py
```

Orden recomendado:

1. extraer cifrado;
2. extraer carga y validación CSV;
3. extraer análisis de habilidades;
4. extraer clasificación de estados;
5. extraer generación del payload;
6. dejar `tracker.py` como punto de entrada CLI.

**Criterio de terminado:** los tests actuales pasan sin cambios en el formato
del dashboard.

### 2.3 Validación de banners

Validar `dashboard_banners.json` antes de insertarlo en el HTML:

- estructura JSON;
- campos obligatorios;
- tipos de datos;
- archivos referenciados existentes;
- iconos permitidos;
- rechazo de contenido HTML no esperado.

**Criterio de terminado:** un archivo inválido produce un error accionable y no
genera un dashboard parcialmente válido.

## Fase 3 — Prioridad media: modelo de datos y operación

### 3.1 Versionado del CSV

Introducir una versión de esquema para permitir cambios compatibles.

Opciones a evaluar:

- columna `schema_version`;
- archivo `.schema-version`;
- migrador explícito `tracker.py migrate`.

**Criterio de terminado:** una instalación existente puede actualizarse sin
perder registros.

### 3.2 Estados normalizados

Definir estados internos estables:

```text
por_postular
postulado
filtro_rh
entrevista
oferta
rechazado
cerrado
retirado
```

El dashboard puede mostrar etiquetas en español, pero el almacenamiento debe
usar valores normalizados.

**Criterio de terminado:** la clasificación no depende de coincidencias
parciales impredecibles.

### 3.3 Despliegue con `--dry-run`

Agregar:

```bash
./scripts/deploy_ghpages.sh --dry-run
```

Debe:

- generar el artefacto;
- listar archivos incluidos;
- comprobar que no haya CSV, secretos ni rutas privadas;
- indicar si el dashboard está cifrado;
- no ejecutar `git push`.

### 3.4 Evitar regeneraciones innecesarias

El servidor debe regenerar reportes solo cuando cambien las entradas relevantes,
o mediante una acción explícita. También debe evitar ejecuciones concurrentes de
los scripts Python.

## Fase 4 — Prioridad media: resiliencia de integraciones

- [ ] Añadir fixtures de detalle para cada portal.
- [ ] Detectar respuestas HTML exitosas con cero resultados inesperados.
- [ ] Mostrar advertencias cuando cambie la estructura de un portal.
- [ ] Añadir límites y validación uniforme para `page`, `limit` y filtros.
- [ ] Registrar fuente, fecha de consulta y error sin guardar datos sensibles.
- [ ] Documentar las limitaciones y términos de uso de cada portal.

**Criterio de terminado:** un cambio de HTML no produce silenciosamente un
resultado vacío sin explicación.

## Fase 5 — Prioridad baja: portafolio

- [ ] Añadir sección de arquitectura al README.
- [ ] Añadir capturas del dashboard y de la PWA.
- [ ] Añadir `CHANGELOG.md`.
- [ ] Crear releases versionadas.
- [ ] Añadir badges de CI y cobertura.
- [ ] Documentar decisiones técnicas importantes.
- [ ] Mantener datos de demostración completamente ficticios.
- [ ] Publicar solo la PWA pública como demo.

## Definición de terminado del proyecto

El proyecto puede considerarse cercano a 10/10 cuando:

- todos los buscadores usan una política HTTP común;
- el tracker está dividido en módulos testeables;
- el CSV tiene esquema versionado y migraciones;
- los estados del pipeline están normalizados;
- el despliegue tiene modo seguro y `--dry-run`;
- los parsers tienen fixtures de búsqueda y detalle;
- la CI cubre validación, tests y generación de artefactos;
- la documentación permite a otra persona instalarlo y usarlo sin contexto
  adicional;
- no existen datos personales reales en el repositorio ni en la demo pública.

## Uso recomendado mientras avanza el roadmap

El proyecto ya puede utilizarse. Antes de trabajar con datos reales:

```bash
cp templates/SEGUIMIENTO.template.csv SEGUIMIENTO_POSTULACIONES.csv
npm run tracker:validate
npm test
npm start
```

Para publicar únicamente la guía de estudio:

```bash
npm run deploy:ghpages
```

No publicar el dashboard en GitHub Pages salvo que sea necesario y se use una
contraseña fuerte:

```bash
DASHBOARD_PASSWORD='tu-clave' npm run deploy:ghpages -- --include-dashboard
```
