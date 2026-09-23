---
title: "Transformación como código: dbt"
description: "La T de ELT es SQL, y ese SQL merece lo mismo que el código de la aplicación: control de versiones, revisión, pruebas, documentación, CI."
sidebar:
  order: 6
lesson:
  id: datos-dbt
  guide: datos
  order: 6
quiz:
  - q: "¿Para qué sirve `ref('stg_pedidos')` en un modelo dbt?"
    options:
      - "Crea un índice"
      - "Ejecuta un test"
      - "Declara la dependencia: dbt arma el DAG y resuelve el nombre real de la tabla"
      - "Copia la tabla a otra base"
    answer: 2
    why: "Con `ref()` el orden de ejecución y el lineage salen solos."
  - q: "¿Cuándo falla un test de datos en dbt?"
    options:
      - "Cuando el modelo es una vista"
      - "Cuando tarda más de un minuto"
      - "Cuando la consulta del test devuelve alguna fila"
      - "Cuando devuelve cero filas"
    answer: 2
    why: "Un test es un `SELECT` de las filas que rompen la regla: si no hay filas, pasa."
  - q: "¿Qué hace la materialización `incremental`?"
    options:
      - "Guarda el modelo en memoria"
      - "Procesa solo las filas nuevas o cambiadas y las agrega a una tabla existente"
      - "Crea una vista"
      - "Reconstruye la tabla entera cada vez"
    answer: 1
    why: "Ahorra cómputo en tablas grandes, a cambio de definir bien qué es \"nuevo\"."
---

La T de ELT es SQL, y ese SQL merece lo mismo que el código de la aplicación: control de versiones, revisión, pruebas, documentación, CI. **dbt** es la herramienta que impuso esa idea. No mueve datos ni corre nada por su cuenta: compila y ordena tus `SELECT` y los ejecuta dentro del warehouse.

### Un modelo es un SELECT

Cada archivo `.sql` en dbt es un modelo: un `SELECT` que define una tabla o vista. dbt se encarga del `CREATE TABLE AS` / `CREATE VIEW`, del orden de ejecución y de recrearlo. Tú solo escribes la lógica de transformación.

### ref() y source() · el DAG se construye solo

En vez de escribir el nombre físico de una tabla, escribes `{{ ref('stg_pedidos') }}` o `{{ source('stripe', 'charges') }}`. dbt reemplaza eso por el nombre real según el entorno (dev/prod) y, sobre todo, **deduce las dependencias**: si el modelo A referencia a B, B se construye antes. De ahí sale el grafo dirigido (DAG) completo, sin que nadie lo declare a mano.

### Las tres capas · staging → intermediate → marts

**Staging**: uno por tabla de origen, relación 1:1, solo renombra columnas a la convención, castea tipos y limpieza trivial. Sin joins. **Intermediate**: lógica reutilizable y joins que no quieres repetir; no se expone a nadie. **Marts**: lo que consumen BI y los analistas, organizado por área de negocio (finanzas, producto, marketing), en forma de hechos y dimensiones o tablas anchas.

``` text
 sources (raw)          staging               intermediate          marts

 raw.pedidos     -->  stg_pedidos     \
 raw.clientes    -->  stg_clientes     +--> int_pedidos_enriq --> fct_pedidos
 raw.pagos       -->  stg_pagos       /                       \-> dim_clientes
                      stg_clientes  ------------------------------/

 staging      : 1:1 con la fuente, renombra y castea, sin joins
 intermediate : joins y calculos compartidos, no se expone
 marts        : por area de negocio, es lo que consume el dashboard
```

### Materializaciones

Una directiva de configuración decide cómo se persiste cada modelo. Cambiarla es una línea, no reescribir el SQL.

| Materialización | Qué hace | Cuándo |
|----|----|----|
| `view` | Crea una vista, cero almacenamiento | Modelo ligero, siempre fresco |
| `table` | Reconstruye la tabla en cada corrida | Transformación cara que se consulta mucho |
| `incremental` | Inserta/mergea solo filas nuevas | Tablas de eventos grandes; recompute total caro |
| `ephemeral` | Se inyecta como CTE en el modelo hijo | Lógica intermedia que no vale materializar |

### Tests de datos

dbt corre aserciones sobre las tablas *después* de construirlas. Los cuatro genéricos que cubren casi todo: `unique`, `not_null`, `accepted_values` (el estado solo puede ser uno de una lista), `relationships` (toda `cliente_id` del hecho existe en la dimensión — integridad referencial que el warehouse no impone). Además puedes escribir **tests singulares**: un `SELECT` que no debería devolver ninguna fila.

``` sql
-- models/marts/fct_pedidos.sql
{{ config(materialized='table') }}

with pedidos as (
    select * from {{ ref('stg_pedidos') }}
),
clientes as (
    select * from {{ ref('stg_clientes') }}
)
select
    p.pedido_id,
    p.cliente_id,
    c.pais,
    p.fecha,
    p.monto
from pedidos p
left join clientes c on p.cliente_id = c.cliente_id
```

``` sql
# models/marts/_marts.yml  ->  documentacion + tests declarativos
models:
  - name: fct_pedidos
    description: "Una fila por pedido confirmado. Grano: pedido_id."
    columns:
      - name: pedido_id
        tests: [unique, not_null]
      - name: monto
        tests:
          - not_null
      - name: cliente_id
        tests:
          - relationships:
              to: ref('stg_clientes')
              field: cliente_id
```

``` sql
-- tests/assert_monto_no_negativo.sql  ->  test singular: falla si hay filas
select pedido_id, monto
from {{ ref('fct_pedidos') }}
where monto < 0
```

### Snapshots · SCD tipo 2 automática

Si una tabla de origen se sobrescribe (el CRM no guarda historia), un **snapshot** de dbt la fotografía en cada corrida y mantiene una tabla con `dbt_valid_from`/`dbt_valid_to`. Así reconstruyes "en qué plan estaba este cliente en junio" aunque la fuente solo tenga el estado actual.

### Macros y Jinja · no te repitas en SQL

dbt compila cada modelo con **Jinja** antes de mandarlo al warehouse: permite variables, condicionales y **macros** (funciones reutilizables que generan SQL). Un caso típico: una macro `cents_to_dollars(column)` que se llama igual en veinte modelos en vez de repetir la división. El paquete comunitario **dbt_utils** trae macros ya hechas para lo común (generar claves subrogadas con hash, pivotar, detectar huecos en series de fechas), y el ecosistema de **packages** de dbt Hub permite instalar y reusar el trabajo de otros equipos como una dependencia más.

``` sql
-- macro reutilizable en macros/cents_to_dollars.sql
{% macro cents_to_dollars(column_name) %}
    ({{ column_name }} / 100.0)
{% endmacro %}

-- uso en cualquier modelo
select pedido_id, {{ cents_to_dollars('monto_centavos') }} as monto_usd
from {{ ref('stg_pedidos') }}
```

### Contratos de modelo · dbt Core 1.5+

Un modelo con `contract: {enforced: true}` declara de antemano los nombres, tipos y algunas restricciones de sus columnas en el `.yml`; dbt valida al construirlo que el `SELECT` real produce exactamente ese esquema, y falla la corrida si no. Es la versión dbt de un contrato de datos (lección 8) aplicado a los propios modelos: protege a quien consume un mart de que alguien cambie un tipo o borre una columna sin darse cuenta. Se combina con **model versions** para publicar una v2 de un modelo sin romper a quien todavía depende de la v1.

### Documentación y lineage generados

De las descripciones en los `.yml` y del DAG de `ref()`, dbt genera un sitio navegable: cada columna con su definición, y el grafo completo de qué alimenta qué. Los **exposures** declaran qué dashboard o modelo de ML consume cada mart, así el lineage llega hasta el consumidor final.

### Por qué se volvió el estándar

Trajo al mundo de los datos prácticas que el software ya tenía: cada cambio es un pull request revisable, CI corre los tests antes de mergear, Jinja permite macros y no repetirse, y el lineage hace visible el impacto de tocar una columna. **dbt Core** es la CLI open source; **dbt Cloud** añade scheduler, IDE y control de accesos.

:::note[Dbt no es un orquestador]
`dbt run` construye tus modelos en orden, pero no sabe cuándo llegó la data cruda, no reintenta media hora después, no lanza la ingesta previa ni avisa a Slack si algo falla. Eso lo hace Airflow, Dagster o Prefect —la sección siguiente— invocando a dbt como un paso más.
:::

## Práctica

Sin instalar nada, imita las capas de dbt con vistas en el [DuckDB shell](https://shell.duckdb.org/):

```sql
CREATE TABLE raw_pedidos AS SELECT * FROM (VALUES
  ('1', 'ANA',  '2026-09-01', '12000'),
  ('2', 'beto', '2026-09-01', '8000'),
  ('2', 'beto', '2026-09-01', '8000'),
  ('3', NULL,   '2026-09-02', '5000')
) t(id, cliente, fecha, monto);
```

1. Crea `stg_pedidos` como vista: tipos correctos (`INT`, `DATE`), cliente en minúsculas, **una fila por id**.
2. Escribe dos tests "al estilo dbt" (consultas que devuelven las filas que fallan): `id` único y `cliente` no nulo.
3. Crea `fct_ventas_diarias` encima de `stg_pedidos`, **nunca** encima de `raw_`.

<details>
<summary>Ver soluciones</summary>

```sql
CREATE VIEW stg_pedidos AS
SELECT DISTINCT id::INT AS id, lower(cliente) AS cliente, fecha::DATE AS fecha, monto::INT AS monto
FROM raw_pedidos;

-- test unique: debe devolver 0 filas
SELECT id, count(*) FROM stg_pedidos GROUP BY id HAVING count(*) > 1;
-- test not_null: devuelve 1 fila, el pedido 3 -> el test FALLA, y así debe ser
SELECT * FROM stg_pedidos WHERE cliente IS NULL;

CREATE VIEW fct_ventas_diarias AS
SELECT fecha, sum(monto) AS ventas, count(*) AS pedidos FROM stg_pedidos GROUP BY fecha;
```

Siguiente paso real: `uv tool install dbt-core --with dbt-duckdb`, `dbt init` y estos mismos modelos como archivos `.sql` con `{{ ref() }}` y los tests en `schema.yml`.

</details>
