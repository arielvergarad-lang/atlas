# HANDOFF — Atlas publicación

## Objetivo
Ariel: "Atlas no es solo para mí, es para todo aquel que quiera aprender; quiero hacerlo interactivo". "Atlas es una guía interactiva que se va construyendo, debe tener animaciones y todo". Referencias: forks `arielvergarad-lang/ai-engineering-from-scratch`, `bases-de-programacion-` (project-based-learning), `system-design-primer` (CC BY 4.0, citar).

## Dónde está
- Worktree `~/atlas-starlight`, rama `starlight` (NO tocar `~/atlas`: opencode trabaja ahí en `mapa.html`, sin commit).
- Commits locales, **sin push**: `82a2412` (sitio base + Datos + diagrama), `2f3cb21` (simulador hashing), + limpieza (link muerto, plantilla, handoff en git).
- Node 24.15 por nvm (Astro 7.3 pide ≥22.12). Python vía `uv`.

## Archivos
- `site/` Astro 7.3 + Starlight 0.42. es = raíz, en = `/en/`.
- `site/astro.config.mjs` locales, sidebar (Mi progreso, Datos y SQL, Diseño de sistemas), override MarkdownContent.
- `site/src/content.config.ts` schema extendido: `lesson{id,guide,order}` + `quiz[]`.
- `site/src/components/MarkdownContent.astro` + `Lesson.astro` quiz y checkpoints (leída / práctica / quiz).
- `site/src/components/ProgressTable.astro`, `src/scripts/progress.ts` progreso en localStorage `atlas:progress:v1`.
- `site/src/i18n.ts` textos UI es/en.
- `site/src/components/diagramas/` motor `ScrollDiagram.astro` + `Paso.astro` + `tipos.ts` + `escenarios/escalar.ts` (GSAP + ScrollTrigger).
- `site/src/components/simuladores/` `AnilloHash.astro` + `hashing.ts` + `hashing.test.ts`.
- `site/src/content/docs/datos/01..13` guía Datos migrada (11 lecciones con Práctica DuckDB + quiz, currículo, laboratorio).
- `site/src/content/docs/diseno-sistemas/01-de-uno-a-millones.mdx`, `02-consistent-hashing.mdx`.
- `site/src/content/docs/en/` index, progreso, `datos/01` (única lección traducida).
- `tools/migrate_guide.py` (HTML→md), `validate_content.py`, `check_links.py`.
- `.github/workflows/site.yml` validar + test + build en push/PR; links los lunes.

## Decisiones
- Camino B (contenido como datos) sobre A (capa JS) y C (framework pesado). Starlight sobre Zensical/build.js propio.
- GSAP solo en componentes de diagrama/simulador; resto del sitio sin JS pesado. `prefers-reduced-motion` respetado.
- Progreso solo local (sin cuentas). Id de lección común entre idiomas.
- Punto interno `j` en diagrama para evitar telaraña; móvil con lienzo desplazable + cámara.
- Todo SQL/Python de prácticas ejecutado en DuckDB real antes de publicar.

## Comandos
```bash
cd ~/atlas-starlight/site && export PATH=~/.nvm/versions/node/v24.15.0/bin:$PATH
npx astro dev                      # http://localhost:4321
npm test && npx astro build        # prueba hashing + build
cd .. && uv run tools/validate_content.py && uv run tools/check_links.py
uv run tools/migrate_guide.py guia/<x>-guia.html <slug>   # migrar otra guía
git log --oneline -3
```

## Siguiente paso (publicación)
Decidido 2026-09-23: el sitio nuevo REEMPLAZA la raíz de Pages (`https://arielvergarad-lang.github.io/atlas/`).
- Hecho: `site`+`base: '/atlas'` en `astro.config.mjs`; links internos relativos / con `BASE_URL`; `pages.yml` reescrito (validar + test + build `site/dist`, copia `guia/` y `mapa.html` viejos para no romper URLs, deploy con configure-pages@v6, upload-pages-artifact@v5, deploy-pages@v5). Verificado sirviendo `dist` bajo `/atlas/`: todas las rutas 200.
- Falta: OK de Ariel para `git push` y merge `starlight` → `main` (el push a main dispara el deploy).
- Pendiente derivado: los links a `index.html` desde `guia/*.html` y `mapa.html` ahora caen en la portada nueva.

## Pendiente / abierto
- Elegir siguiente pieza animada: (b) diagrama Parquet en Datos, (c) animar recorrido/mapa de progreso.
- Traducir al inglés: 10 lecciones de Datos + 2 de Diseño de sistemas (hoy caen al español).
- Migrar las otras 9 guías con `migrate_guide.py` + escribir práctica/quiz.
- Coordinar con opencode: el mapa debe pasar a generarse desde los datos de lecciones.
- Warning benigno de build: colección `i18n` inexistente.
