---
title: "El SQL que no se ve en un CRUD"
description: "Ya sabes SELECT , JOIN y GROUP BY ."
sidebar:
  order: 2
lesson:
  id: datos-sql-analitico
  guide: datos
  order: 2
quiz:
  - q: "¿Cuál es la diferencia clave entre `GROUP BY` y una window function?"
    options:
      - "La window function agrega sin colapsar las filas"
      - "`GROUP BY` es más rápido siempre"
      - "La window function no puede sumar"
      - "No hay diferencia, son sinónimos"
    answer: 0
    why: "Cada fila conserva su detalle y además recibe el valor agregado de su ventana."
  - q: "¿Para qué sirve `QUALIFY`?"
    options:
      - "Para ordenar el resultado final"
      - "Para reemplazar `WHERE` en cualquier consulta"
      - "Para filtrar por el resultado de una window function"
      - "Para filtrar antes de agrupar"
    answer: 2
    why: "Es a las window functions lo que `HAVING` es a `GROUP BY`."
  - q: "En `GROUP BY ROLLUP (mes, cliente)`, la fila con `mes` y `cliente` en `NULL` es…"
    options:
      - "El total general"
      - "Un error de datos"
      - "Los pedidos sin cliente"
      - "El subtotal por cliente"
    answer: 0
    why: "Ojo: si tus datos ya traen `NULL` reales, usa `GROUPING()` para distinguirlos."
---

Ya sabes `SELECT`, `JOIN` y `GROUP BY`. El SQL analítico añade una capa: subtotales en una pasada, cálculos que miran filas vecinas sin colapsarlas, y pivotes. Con esto se resuelven cohortes, retención y funnels sin exportar nada a Python.

### Agregación con subtotales

### GROUPING SETS · ROLLUP · CUBE

Un `GROUP BY` normal te da un nivel de detalle. **GROUPING SETS** pide varios a la vez en una sola consulta: por región y producto, solo por región, y el total global. `ROLLUP(a, b)` es el atajo para jerarquías (a+b, a, total); `CUBE(a, b)` genera todas las combinaciones. Evita hacer tres consultas y unirlas con `UNION ALL`.

``` sql
-- subtotales por region+producto, por region, y total, en una pasada
SELECT region, producto, SUM(monto) AS total
FROM ventas
GROUP BY GROUPING SETS ((region, producto), (region), ());

-- GROUPING() marca las filas de subtotal (1 = "agregado en esta columna")
```

### Window functions

### La idea: agregar sin colapsar

Una función de ventana calcula sobre un conjunto de filas *relacionadas con la fila actual* pero devuelve un valor por fila, sin agruparlas. La cláusula `OVER` define ese conjunto: `PARTITION BY` lo divide en grupos independientes, `ORDER BY` lo ordena dentro de cada grupo, y el **frame** (`ROWS BETWEEN ...`) acota qué filas entran en el cálculo acumulado.

### Las familias que se usan

**Ranking**: `ROW_NUMBER` (1,2,3 sin empates), `RANK` (1,1,3), `DENSE_RANK` (1,1,2), `NTILE(4)` (reparte en cuartiles). **Desplazamiento**: `LAG`/`LEAD` traen el valor de la fila anterior o siguiente (variación mes a mes, tiempo entre eventos). **Acumulados**: `SUM/AVG/COUNT` con `OVER (... ORDER BY ...)` dan running totals y medias móviles.

``` sql
-- ingreso acumulado por cliente y numero de pedido, media movil de 3
SELECT
  cliente_id,
  fecha,
  monto,
  SUM(monto) OVER (
    PARTITION BY cliente_id ORDER BY fecha
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )                                                    AS acumulado,
  AVG(monto) OVER (
    PARTITION BY cliente_id ORDER BY fecha
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  )                                                    AS media_movil_3,
  monto - LAG(monto) OVER (
    PARTITION BY cliente_id ORDER BY fecha
  )                                                    AS delta_vs_anterior,
  ROW_NUMBER() OVER (
    PARTITION BY cliente_id ORDER BY fecha
  )                                                    AS nro_pedido
FROM pedidos;
```

:::note[El frame por defecto muerde]
Si pones `ORDER BY` dentro de `OVER` pero no defines el frame, el default es `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. Con `RANGE`, todas las filas con el mismo valor de orden (misma fecha, por ejemplo) se suman juntas de golpe: tu "running total" salta en escalones y no cuadra. Para acumulados fila a fila usa siempre `ROWS BETWEEN ...` de forma explícita.
:::

### QUALIFY · filtrar por el resultado de una ventana

No puedes usar una window function en `WHERE` (se calcula después del filtrado). **QUALIFY** resuelve eso: filtra por el valor de la ventana sin subconsulta. Es una extensión de **Snowflake, BigQuery y DuckDB**; en PostgreSQL o MySQL hay que envolver en una CTE y filtrar fuera.

``` sql
-- el ultimo pedido de cada cliente (Snowflake / BigQuery / DuckDB)
SELECT cliente_id, fecha, monto
FROM pedidos
QUALIFY ROW_NUMBER() OVER (PARTITION BY cliente_id ORDER BY fecha DESC) = 1;

-- equivalente portatil
WITH r AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY cliente_id ORDER BY fecha DESC) AS rn
  FROM pedidos
)
SELECT cliente_id, fecha, monto FROM r WHERE rn = 1;
```

### El frame en detalle · ROWS vs RANGE vs GROUPS

`ROWS BETWEEN n PRECEDING AND CURRENT ROW` cuenta filas físicas: siempre exactamente n+1 filas, sin importar si hay empates. `RANGE` cuenta por *valor* de la columna de orden: todas las filas con el mismo valor entran juntas, aunque sean miles. `GROUPS` (menos soportado) cuenta por grupos de valores distintos, no por filas. Para una media móvil de "los últimos 3 pedidos" quieres `ROWS`; para "todo lo vendido en la misma fecha" el comportamiento de `RANGE` es el que quieres, pero rara vez es el que crees que pediste.

### CTEs, recursión y pivote

### Trampa: la CTE que el motor no materializa

Antes de PostgreSQL 12, un `WITH` era una barrera de optimización: el motor la ejecutaba aparte y luego usaba el resultado. Desde PostgreSQL 12, si la CTE se referencia una sola vez y no es recursiva, el planificador la **inlinea** dentro de la consulta principal (como si fuera una subconsulta), lo que en general mejora el plan pero cambia el comportamiento de código antiguo que dependía del "corte" para forzar un orden de evaluación. Para forzar el comportamiento clásico se marca `WITH x AS MATERIALIZED (...)`; para forzar el inlineo, `NOT MATERIALIZED`. Snowflake, BigQuery y DuckDB también inlinean CTEs simples por defecto.

### CTE y CTE recursiva

Un `WITH nombre AS (...)` nombra un paso intermedio y hace la consulta legible de arriba abajo, como una tubería. La versión **recursiva** (`WITH RECURSIVE`) se refiere a sí misma: sirve para jerarquías (organigrama, categorías anidadas, árbol de comentarios) y para generar series (todas las fechas de un rango, para no perder los días sin ventas).

``` sql
-- serie de fechas: una fila por dia aunque no haya datos
WITH RECURSIVE dias AS (
  SELECT DATE '2026-01-01' AS d
  UNION ALL
  SELECT d + 1 FROM dias WHERE d < DATE '2026-01-31'
)
SELECT dias.d, COUNT(v.id) AS ventas
FROM dias LEFT JOIN ventas v ON v.fecha = dias.d
GROUP BY dias.d ORDER BY dias.d;
```

### PIVOT / UNPIVOT

**PIVOT** gira filas a columnas (una columna por mes, una fila por producto); **UNPIVOT** hace lo contrario, pasa una tabla ancha a formato largo (que es el que quieren casi todas las herramientas de gráficos). La sintaxis `PIVOT` existe en DuckDB, Snowflake y SQL Server; el patrón portátil es `SUM(CASE WHEN ...)`.

``` sql
-- portatil: funciona en cualquier motor
SELECT
  producto,
  SUM(CASE WHEN mes = 'ene' THEN monto END) AS ene,
  SUM(CASE WHEN mes = 'feb' THEN monto END) AS feb,
  SUM(CASE WHEN mes = 'mar' THEN monto END) AS mar
FROM ventas
GROUP BY producto;

-- DuckDB / Snowflake
SELECT * FROM ventas PIVOT (SUM(monto) FOR mes IN ('ene','feb','mar'));
```

### Los tres patrones de analítica de producto

**Cohorte + retención**: agrupa usuarios por mes de alta (`DATE_TRUNC`), calcula para cada mes posterior cuántos siguieron activos, divide. **Funnel**: por usuario, marca el paso máximo alcanzado con `MAX(CASE WHEN evento = ...)` y cuenta. **Sesiones**: ordena eventos por usuario y tiempo, usa `LAG` para ver el hueco, y una `SUM() OVER` de "empezó sesión nueva" te da el id de sesión. Los tres son window functions + un `GROUP BY`.

:::note[Legibilidad primero]
El SQL analítico se vuelve ilegible rápido. Nombra cada CTE por lo que representa (`pedidos_por_cliente`, no `t1`), un paso por CTE, y comenta el grano de cada tabla intermedia ("una fila por usuario y día"). Esto es exactamente lo que dbt formaliza en la lección 6.
:::

## Práctica

En el [DuckDB shell](https://shell.duckdb.org/), crea esta tabla pequeña:

```sql
CREATE TABLE pedidos (cliente TEXT, fecha DATE, monto INT);
INSERT INTO pedidos VALUES
 ('ana','2026-01-03',120), ('ana','2026-01-10',80), ('ana','2026-02-02',200),
 ('beto','2026-01-05',50), ('beto','2026-02-11',70), ('cee','2026-02-20',300);
```

1. Para cada pedido, muestra el **acumulado** que lleva ese cliente hasta esa fecha.
2. Devuelve **solo el último pedido** de cada cliente, sin subconsultas.
3. Suma por mes y cliente, con **subtotal por mes y total general**, en una sola consulta.

<details>
<summary>Ver soluciones</summary>

```sql
-- 1. window function: agrega sin colapsar
SELECT cliente, fecha, monto,
       sum(monto) OVER (PARTITION BY cliente ORDER BY fecha) AS acumulado
FROM pedidos ORDER BY cliente, fecha;

-- 2. QUALIFY filtra por el resultado de la ventana
SELECT * FROM pedidos
QUALIFY row_number() OVER (PARTITION BY cliente ORDER BY fecha DESC) = 1;

-- 3. ROLLUP genera los subtotales
SELECT date_trunc('month', fecha) AS mes, cliente, sum(monto) AS total
FROM pedidos
GROUP BY ROLLUP (mes, cliente)
ORDER BY mes NULLS LAST, cliente NULLS LAST;
```

</details>
