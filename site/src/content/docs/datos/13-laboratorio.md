---
title: "Laboratorio: tocar el concepto en el navegador"
description: "Todo corre en la pestaña, sin cuenta ni instalación."
sidebar:
  order: 13
---

Todo corre en la pestaña, sin cuenta ni instalación. Ideal para probar una consulta o un modelo de datos sin montar nada.

| Herramienta | Qué concepto de la guía vuelve tangible |
|----|----|
| [DuckDB WASM shell](https://shell.duckdb.org/) | lección 1 · lección 4 · lección 10 — un motor analítico columnar entero en el navegador: consulta CSV/JSON/Parquet remoto con SQL, mira los planes |
| [Sqlime](https://sqlime.org/) · [Datasette Lite](https://lite.datasette.io) | lección 2 — SQLite en WASM: practicar window functions, CTEs y GROUPING SETS sin backend |
| [SQLChef](https://jonathanwalker.github.io/SQLChef/) | lección 5 — consultar un archivo (CSV, JSON, Parquet) con SQL directo: ver un archivo como fuente de datos |
| [drawDB](https://www.drawdb.app) | lección 3 — dibujar un esquema estrella (hechos, dimensiones, claves) y exportar el DDL |
| [DB Fiddle](https://www.db-fiddle.com) · [SQL Fiddle](https://sqlfiddle.com) | lección 2 — probar la misma consulta en Postgres, MySQL y SQLite y ver dónde cambia el dialecto |
| [JSON Crack](https://jsoncrack.com/) | lección 5 — pegar un payload de una API de ingesta y verlo como árbol antes de modelarlo |
| [Malloy playground](https://docs.malloydata.dev/documentation/) | lección 3 · lección 6 — un lenguaje de modelado moderno: definir métricas y dimensiones una vez, reutilizarlas |

:::note[El siguiente paso]
Cuando lo del navegador te quede chico: una cuenta gratis de **BigQuery** (sandbox, sin tarjeta) o **Snowflake** (trial) y un proyecto de **dbt Core** local contra ella. Ahí se aprende de verdad el flujo staging → marts.
:::
