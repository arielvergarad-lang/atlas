---
title: "Cuando SQL no alcanza: pandas, Polars, DuckDB"
description: "SQL es el mejor lenguaje para transformar datos tabulares en conjunto, y debería ser el default."
sidebar:
  order: 10
lesson:
  id: datos-pandas-python
  guide: datos
  order: 10
quiz:
  - q: "¿Por qué conviene vectorizar en vez de iterar fila por fila en pandas o Polars?"
    options:
      - "Porque evita tener que instalar NumPy"
      - "La operación corre en código nativo sobre columnas enteras, no en el intérprete de Python fila a fila"
      - "Porque los bucles `for` no funcionan con DataFrames"
      - "Porque usa menos disco"
    answer: 1
    why: "La diferencia suele ser de 10 a 100 veces o más."
  - q: "¿Qué aporta Apache Arrow al ecosistema?"
    options:
      - "Un reemplazo de SQL"
      - "Un formato columnar en memoria común, que permite pasar datos entre herramientas sin copiarlos"
      - "Un lenguaje de consultas nuevo"
      - "Un warehouse en la nube"
    answer: 1
    why: "Por eso DuckDB puede consultar un DataFrame de Polars casi gratis."
  - q: "¿Cuándo tiene sentido pasar de SQL a Python?"
    options:
      - "Cuando necesitas lógica que SQL expresa mal: llamar APIs, modelos estadísticos o ML, texto complejo"
      - "Siempre que la tabla tenga más de mil filas"
      - "Nunca, SQL lo hace todo"
      - "Cuando quieres que sea más rápido por defecto"
    answer: 0
    why: "Para filtrar, unir y agregar, SQL suele ser más simple y más rápido."
---

SQL es el mejor lenguaje para transformar datos tabulares en conjunto, y debería ser el default. Pero hay trabajo —exploración iterativa, limpieza irregular, estadística, preparar datos para modelos— donde Python encaja mejor. La clave es saber qué va en el warehouse y qué va en un script, y no confundir un notebook con un pipeline.

### Cuándo mover el trabajo a Python

Se queda en el warehouse: transformación repetible, sobre tablas grandes, que alimenta dashboards o modelos —eso es dbt. Se va a Python: análisis exploratorio de una vez, parsing de formatos raros, limpieza con reglas que cambian cada dos filas, estadística y ML, integración con APIs, y cualquier cosa que necesite librerías que no existen en SQL. Regla: *si lo vas a correr todas las noches, es SQL; si es para responder una pregunta hoy, es Python*.

### pandas · el estándar histórico

**DataFrame** en memoria, evaluación inmediata, un solo núcleo. Enorme ecosistema y todo tutorial lo usa. Límites: consume varias veces el tamaño del archivo en RAM, se pone lento con millones de filas, la API tiene muchas formas de hacer lo mismo, y el índice y el `SettingWithCopyWarning` confunden. Bien para datasets de hasta unos pocos millones de filas.

### Polars · el reemplazo moderno

DataFrame escrito en Rust, sobre Apache Arrow. **Multinúcleo** por defecto, API más consistente, y un modo **lazy**: encadenas operaciones sin ejecutar y un optimizador de consultas reordena filtros y proyecciones antes de correr. Procesa datasets más grandes que la RAM en streaming. Para trabajo de datos nuevo, es la opción razonable.

``` python
# lazy: no ejecuta hasta collect(); el optimizador empuja el filtro
# y solo lee las columnas usadas
import polars as pl

q = (
    pl.scan_parquet("eventos/*.parquet")
      .filter(pl.col("precio") > 0)
      .group_by("categoria")
      .agg(pl.col("precio").mean().alias("precio_medio"))
      .sort("precio_medio", descending=True)
)
df = q.collect()
```

### DuckDB como pegamento

DuckDB consulta con SQL directamente sobre DataFrames de pandas/Polars, sobre Parquet y sobre CSV, y suele ganar a pandas en agregaciones y joins. El patrón práctico: exploras en un notebook, y cuando necesitas un `GROUP BY` o un join serio, lo escribes en SQL con DuckDB sobre el DataFrame que ya tienes. SQL y Python en el mismo flujo, sin mover datos.

``` python
# SQL sobre un DataFrame de Python, sin cargarlo a ninguna base
import duckdb
resumen = duckdb.sql("""
    SELECT categoria, COUNT(*) AS n, SUM(monto) AS total
    FROM df                         -- 'df' es un DataFrame en memoria
    WHERE fecha >= DATE '2026-01-01'
    GROUP BY categoria ORDER BY total DESC
""").df()
```

### Vectorizar en vez de iterar

Un `for` fila por fila, o `.apply()` con una función Python, procesan una fila a la vez en el intérprete de Python: son órdenes de magnitud más lentos que una operación vectorizada (`df['a'] + df['b']`, `df.groupby().sum()`), que delega el bucle al código en C/Rust de abajo. La señal de alarma es un `.apply(lambda row: ...)` que recorre millones de filas: casi siempre existe una operación vectorizada equivalente, y si no la hay, es momento de pensarlo en SQL o en Polars.

### Apache Arrow · el formato que todos comparten en memoria

Arrow define cómo representar datos columnares *en memoria* (no en disco, ahí está Parquet) de forma estándar. Polars, DuckDB, pandas 2.x (con el backend Arrow opcional) y muchos conectores lo usan, lo que permite pasar un DataFrame de una librería a otra **sin copiar ni serializar** —"zero-copy". Es la razón práctica de que `duckdb.sql("... FROM df")` del ejemplo anterior sea instantáneo en vez de exportar e importar.

### Notebooks: para qué sí y para qué no

El notebook es imbatible para explorar: ves cada paso, graficas, iteras. Sus problemas aparecen cuando se quiere que sea producción: **estado oculto** (una variable de una celda borrada sigue viva), **orden de ejecución** no lineal, difícil de versionar (es JSON con salidas), difícil de testear, y sin manejo de errores. Un notebook que "funciona" puede no volver a funcionar desde cero.

:::tip[Por qué importa]
Muchos incidentes de datos son un notebook crítico que corría en la máquina de una persona, con celdas ejecutadas en un orden que solo ella conocía, y que dejó de funcionar cuando se fue.
:::

### De notebook a pipeline

Cuando un análisis exploratorio se vuelve recurrente: extrae la lógica a funciones en un módulo `.py` con tests, muévela a dbt si es transformación SQL, y déjala corriendo bajo el orquestador. Herramientas como `papermill` o `nbconvert` permiten parametrizar y ejecutar un notebook de forma controlada como paso intermedio, pero el destino sano es código normal.

:::note[No pongas un notebook en cron]
"Lo dejo agendado y listo" con un `.ipynb` es deuda garantizada: sin logs útiles, sin alertas, sin reintentos, sin control de versiones real, y cuando falla a las 4 a.m. no hay traza de qué celda ni por qué. Si algo tiene que correr solo, merece ser un script o un modelo dbt bajo un orquestador.
:::

## Práctica

Corre esto en tu máquina con [uv](https://docs.astral.sh/uv/), sin crear un entorno a mano:

```bash
uv run --with polars --with duckdb --with pyarrow python
```

```python
import time, random
import polars as pl
import duckdb

n = 2_000_000
df = pl.DataFrame({"pais": random.choices(["CL", "AR", "PE"], k=n),
                   "monto": [random.randint(1, 1000) for _ in range(n)]})

# 1. versión con bucle
t = time.perf_counter()
totales = {}
for pais, monto in df.iter_rows():
    totales[pais] = totales.get(pais, 0) + monto * 1.19
print("bucle", time.perf_counter() - t)

# 2. escribe la versión vectorizada con Polars y mide
# 3. escribe la misma consulta en SQL con duckdb.sql("... FROM df ...") y mide
```

<details>
<summary>Ver soluciones</summary>

```python
t = time.perf_counter()
out = df.group_by("pais").agg((pl.col("monto") * 1.19).sum())
print("polars", time.perf_counter() - t)

duckdb.sql("SELECT 1").fetchall()  # calentamiento: la primera llamada inicializa DuckDB
t = time.perf_counter()
out = duckdb.sql("SELECT pais, sum(monto * 1.19) FROM df GROUP BY pais").pl()
print("duckdb", time.perf_counter() - t)
```

Qué deberías ver (en un portátil, con 2 millones de filas): el bucle tarda alrededor de medio segundo y Polars unas **10 veces menos**. DuckDB lee el DataFrame de Polars por su nombre de variable, sin que exportes nada, porque los dos hablan Arrow; pero en esta prueba chica puede salir **igual o más lento que el bucle**, porque paga la conversión del DataFrame en cada consulta. Su ventaja aparece cuando los datos son más grandes que la memoria o cuando lee Parquet directo del disco. La lección real del ejercicio: **mide antes de afirmar**, en caliente y más de una vez.

</details>
