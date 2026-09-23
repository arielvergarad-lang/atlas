---
title: "Ingesta: ETL, ELT y CDC"
description: "Antes de transformar hay que traer los datos: de la base de la app, de Stripe, de un CRM, de archivos."
sidebar:
  order: 5
lesson:
  id: datos-etl-elt
  guide: datos
  order: 5
quiz:
  - q: "¿Qué distingue a ELT de ETL?"
    options:
      - "ELT carga el dato crudo y lo transforma dentro del warehouse"
      - "ELT no transforma nunca"
      - "ETL solo existe en streaming"
      - "ELT exige un servidor aparte para transformar"
    answer: 0
    why: "El cómputo barato y elástico del warehouse hizo práctico transformar después de cargar."
  - q: "Un pipeline es idempotente cuando…"
    options:
      - "Corre en menos de un minuto"
      - "Usa solo `INSERT`"
      - "Correrlo dos veces con la misma entrada deja el mismo resultado"
      - "Nunca falla"
    answer: 2
    why: "Es lo que permite reintentar y hacer backfill sin duplicar datos."
  - q: "¿De dónde lee los cambios el CDC basado en log?"
    options:
      - "De un CSV exportado a mano"
      - "Del log de transacciones de la base origen (WAL, binlog)"
      - "De un `SELECT *` cada hora"
      - "De los logs HTTP de la app"
    answer: 1
    why: "Captura inserts, updates y deletes sin cargar la base origen con consultas."
---

Antes de transformar hay que traer los datos: de la base de la app, de Stripe, de un CRM, de archivos. El orden en que se hacen las tres letras —extraer, transformar, cargar— cambió, y con él todo el stack. La clave operativa es que la ingesta sea repetible sin duplicar ni perder nada.

### ETL  vs  ELT

**ETL** clásico: extraes, *transformas en un servidor intermedio* (limpias, unes, agregas) y cargas el resultado ya cocinado. **ELT** moderno: extraes, *cargas los datos crudos tal cual* en el warehouse ("raw"), y transformas ahí con SQL. Ganó ELT porque el cómputo del warehouse se volvió barato y elástico, y porque guardar el crudo te deja reprocesar sin volver a molestar a la fuente.

``` text
  EXTRACT              LOAD                     TRANSFORM
  (Fivetran /      ->  (tal cual, sin       ->  (dbt: SQL dentro
   Airbyte / dlt)       transformar, "raw")      del warehouse)

  Postgres app   -->  raw.app_pedidos     \
  Stripe API     -->  raw.stripe_charges   +-->  staging --> intermediate --> marts
  HubSpot        -->  raw.hubspot_contacts /       stg_*        int_revenue      fct_mrr
  CSV en S3      -->  raw.uploads_csv              (renombra)   (une, calcula)   (para BI)

  cambiar una regla de negocio:
    ETL  -> reprocesar desde la fuente (si aun la tienes igual)
    ELT  -> re-ejecutar el SQL sobre "raw", que ya esta cargado y versionado
```

#### Cómo entran los datos

### Batch  vs  streaming

**Batch**: cargas cada hora, cada noche. Simple, barato, suficiente para reportes y dashboards que nadie mira a las 3 a.m. **Streaming**: los eventos llegan continuamente (Kafka, Kinesis) y se procesan en segundos. Necesario para detección de fraude, alertas operativas, personalización en vivo. La mayoría de la analítica de negocio no necesita streaming; añade una complejidad operativa grande.

### CDC · change data capture

Replicar una base entera cada hora es caro y pesa sobre la fuente. **CDC** captura solo lo que cambió. **Basado en log** (leyendo el WAL de PostgreSQL, el binlog de MySQL con Debezium): captura inserciones, updates y *borrados*, con bajo impacto, casi en tiempo real. **Basado en consulta** (pregunta "¿qué filas tienen `updated_at` mayor que la última vez?"): fácil de montar, pero no ve los borrados y necesita esa columna fiable en cada tabla.

### Idempotencia y reprocesos

Una carga es **idempotente** si ejecutarla dos veces deja el mismo resultado que ejecutarla una. Se logra con `MERGE` / upsert por clave, o borrando la partición del día antes de reinsertarla. Sin idempotencia, un reintento tras un fallo a medias te deja filas duplicadas, y nadie se entera hasta que un número sale al doble en un reporte.

:::tip[Por qué importa]
Los pipelines fallan a media ejecución todo el tiempo (timeout de red, deploy, cuota de API). Si cada tarea es idempotente, la recuperación es "vuelve a correr"; si no, es una investigación forense.
:::

#### Que se pueda re-ejecutar sin romper nada

### Full refresh · incremental · backfill

**Full refresh**: recarga toda la tabla desde cero. Simple y siempre correcto, inviable cuando la tabla es enorme. **Incremental**: procesa solo lo nuevo desde una marca de agua (`high-water mark`: el `max(event_time)` ya cargado). **Backfill**: volver a procesar un rango del pasado porque cambió la lógica o llegó data tarde. Un pipeline serio soporta los tres modos y, en el incremental, tolera que lleguen eventos con fecha vieja (*late-arriving data*).

### Herramientas de extract-load

**Fivetran**: conectores gestionados, "funciona y no lo tocas", cobra según filas activas movidas al mes; caro a volumen. **Airbyte**: open source / gestionado, muchos conectores, más control y más mantenimiento. **Singer / Meltano**: estándar abierto de "taps" y "targets". **dlt**: librería Python para escribir tu propia ingesta con esquema y estado. El punto de todas: *no transforman*, solo mueven crudo a "raw". La transformación es dbt.

### Reverse ETL · el dato vuelve a las herramientas de negocio

ELT lleva datos de las herramientas operativas al warehouse para analizarlos. **Reverse ETL** hace el camino inverso: toma una métrica ya calculada en el warehouse (el *lifetime value* de un cliente, un score de riesgo de abandono) y la sincroniza de vuelta a Salesforce, HubSpot o Intercom, para que un vendedor o un email automatizado la use sin pedirle un reporte a analítica. Herramientas como **Census** y **Hightouch** ocupan ese espacio; el patrón convierte al warehouse en la fuente de verdad también para las herramientas operativas, no solo para dashboards.

### Schema drift · cuando la fuente cambia sin avisar

Una API agrega un campo nuevo, renombra uno o cambia un tipo (de entero a string) sin previo aviso, y la ingesta lo recibe igual. Sin manejo explícito: un campo nuevo se pierde silenciosamente si el esquema de destino es rígido, o un cambio de tipo rompe la carga a mitad de un batch. Las herramientas de extract-load serias detectan el *drift* y ofrecen una política: agregar la columna automáticamente, alertar y pausar, o mandar el cambio a una tabla de "esquema pendiente de revisión" en vez de fallar todo el pipeline.

|  | ETL | ELT |
|----|----|----|
| Orden | extract → transform → load | extract → load → transform |
| Dónde transforma | Servidor / herramienta intermedia (Spark) | Dentro del warehouse (SQL / dbt) |
| Datos crudos | Se pierden si no los guardas aparte | Siempre en "raw", reprocesables |
| Cambiar una regla | Reprocesar desde la fuente | Re-ejecutar SQL sobre "raw" |
| PII sensible | Se puede filtrar antes de cargar | Entra cruda; hay que gobernar accesos |
| Cuándo | Destino con cómputo caro o limitado | Warehouse moderno (el default hoy) |
| Herramientas | Informatica, Talend, Spark | Fivetran / Airbyte + dbt |

:::note[El backfill que duplicó todo]
Reprocesar marzo con un pipeline que hace `INSERT` en vez de `MERGE` o "borrar-y-reinsertar la partición" suma marzo dos veces. Como los totales anuales siguen "razonables", puede pasar semanas sin que nadie lo note. Toda tarea de carga debe poder re-ejecutarse para una fecha lógica y escribir *solo* esa partición.
:::

## Práctica

En el [DuckDB shell](https://shell.duckdb.org/), simula un lote de ingesta que trae un **duplicado** (el cliente 1 se actualizó dos veces):

```sql
CREATE TABLE destino (id INT PRIMARY KEY, email TEXT, actualizado TIMESTAMP);
CREATE TABLE lote AS SELECT * FROM (VALUES
  (1, 'a@x.cl',  TIMESTAMP '2026-09-01 10:00'),
  (2, 'b@x.cl',  TIMESTAMP '2026-09-01 11:00'),
  (1, 'a2@x.cl', TIMESTAMP '2026-09-02 09:00')
) t(id, email, actualizado);
```

1. Escribe una carga que deje en `destino` **una fila por id, con la versión más reciente**.
2. Córrela **dos veces**. `SELECT count(*) FROM destino` tiene que seguir dando 2. Si da más o falla, no es idempotente.

<details>
<summary>Ver solución</summary>

```sql
INSERT INTO destino
SELECT * FROM (
  SELECT * FROM lote
  QUALIFY row_number() OVER (PARTITION BY id ORDER BY actualizado DESC) = 1
)
ON CONFLICT (id) DO UPDATE SET email = excluded.email, actualizado = excluded.actualizado;
```

Dos ideas: **deduplicar dentro del lote** (un upsert no puede tocar la misma fila dos veces en una sentencia) y **upsert por clave** en vez de `INSERT` a ciegas. Un `INSERT` simple duplicaría en la segunda corrida o fallaría por la clave primaria.

</details>
