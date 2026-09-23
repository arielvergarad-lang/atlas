---
title: "Dos mundos: transaccional y analítico"
description: "La base de datos que sostiene una aplicación y la que responde '¿cuánto vendimos por país el trimestre pasado?' están optimizadas para cosas opuestas."
sidebar:
  order: 1
lesson:
  id: datos-oltp-vs-olap
  guide: datos
  order: 1
quiz:
  - q: "Correr un reporte pesado directo sobre la base de producción de la app es riesgoso sobre todo porque…"
    options:
      - "SQL no sabe agregar millones de filas"
      - "Una base OLTP no puede leer más de una fila a la vez"
      - "Los reportes necesitan datos en JSON"
      - "Compite por CPU y locks con el tráfico de usuarios"
    answer: 3
    why: "Es aislamiento de fallos: un reporte pesado puede degradar el checkout."
  - q: "¿Por qué \"suma el monto de 40 millones de filas\" es más rápido en un column store?"
    options:
      - "Guarda las filas normalizadas"
      - "Hace menos `JOIN` por diseño"
      - "Lee solo esa columna, contigua y comprimida"
      - "Tiene más índices B-tree"
    answer: 2
    why: "El row store tiene que leer todas las columnas de cada fila aunque solo necesite una."
  - q: "En un motor columnar, ¿qué hace que los zone maps (min/max por bloque) realmente descarten bloques?"
    options:
      - "Usar UUID como clave primaria"
      - "El orden físico de las filas, por ejemplo por fecha"
      - "Tener un índice B-tree por columna"
      - "Normalizar a tercera forma normal"
    answer: 1
    why: "Sin orden, los rangos min/max de cada bloque se solapan y el pruning no ahorra nada."
---

La base de datos que sostiene una aplicación y la que responde "¿cuánto vendimos por país el trimestre pasado?" están optimizadas para cosas opuestas. Entender por qué es la puerta de entrada a todo lo demás: el modelado, el almacenamiento columnar y el warehouse existen porque una sola base no puede ser buena en ambas cargas.

### Carga transaccional · OLTP

Muchísimas operaciones pequeñas y concurrentes: crear un pedido, marcar un mensaje como leído, descontar stock. Cada una toca pocas filas, tiene que ser rápida (milisegundos) y correcta bajo concurrencia. El diseño se optimiza para **escrituras** y para leer filas concretas por clave. Es lo que cubre la guía de Backend: PostgreSQL o MySQL detrás de una API.

### Carga analítica · OLAP

Pocas consultas, pero cada una lee millones de filas para agregarlas: sumas, promedios, conteos, agrupaciones, ventanas temporales. Casi no hay `UPDATE`; los datos entran por lotes y se consultan muchas veces. El diseño se optimiza para **escanear columnas enteras** lo más rápido y barato posible.

:::tip[Por qué importa]
Si corres estas consultas contra la base de la app, compites por CPU y locks con el tráfico de usuarios: un reporte pesado puede degradar el checkout. La separación no es purismo, es aislamiento de fallos.
:::

### Normalizar  vs  desnormalizar

OLTP **normaliza**: cada hecho vive en un solo lugar, referenciado por claves, para que una corrección se haga una vez y no haya contradicciones. OLAP **desnormaliza** a propósito: repite el nombre del país y la categoría en cada fila de ventas para que la consulta no tenga que hacer diez `JOIN`. El almacenamiento es barato; el tiempo de escaneo y la claridad para quien consulta, no.

### Almacén por fila  vs  por columna

Un **row store** guarda todas las columnas de una fila juntas en disco: ideal para "tráeme el pedido 4821 completo". Un **column store** guarda cada columna por separado y contigua: para "suma el monto de 40 millones de filas" solo lee esa columna y salta el resto. Esa es la diferencia de fondo entre una base OLTP y un motor analítico.

``` text
FILA  (row store, OLTP)              COLUMNA  (column store, OLAP)

bloque 1: [ 1 | Ana  | CL | 120 ]    bloque A: [ 1  2  3  4 ... ]      id
bloque 2: [ 2 | Beto | AR |  90 ]    bloque B: [ Ana Beto Cee ... ]    nombre
bloque 3: [ 3 | Cee  | CL | 300 ]    bloque C: [ CL AR CL CL ... ]     pais
                                     bloque D: [ 120 90 300 ... ]      monto

"dame la fila 2 entera"   1 bloque              4 bloques (una por columna)
"suma monto de todo"      3 bloques (todo)      1 bloque, ya contiguo
"cuenta por pais"         3 bloques             1 bloque + se comprime:
                                                 CL,CL,CL  ->  CL x3  (RLE)
```

### Por qué columnar comprime y escanea rápido

Datos del mismo tipo y dominio juntos se comprimen muchísimo mejor: **run-length** (CL repetido 900 veces → "CL ×900"), **diccionario** (mapea "Chile" a un entero pequeño), **delta** (guarda diferencias entre valores ordenados). Menos bytes en disco = menos lectura = más rápido. Encima, el motor procesa en **bloques vectorizados** (miles de valores por instrucción) en vez de fila por fila.

### MPP · procesamiento masivamente paralelo

Los warehouses reparten una consulta entre decenas o cientos de nodos que escanean trozos distintos de la tabla a la vez y combinan resultados. Por eso una agregación sobre mil millones de filas termina en segundos: no es una máquina más rápida, son muchas trabajando en paralelo sobre datos particionados.

### Índices en un motor analítico · zone maps, no B-tree

Un índice B-tree ayuda a encontrar una fila entre millones; en OLAP casi siempre se escanean millones de filas de todos modos, así que mantenerlo cuesta más de lo que ahorra. Los motores columnares usan en su lugar **zone maps** (min/max por bloque, para descartar bloques enteros) y a veces **bloom filters** por columna para saltarse bloques donde un valor exacto no puede estar. La estructura que más importa no es el índice, es el **orden físico** de las filas (por fecha, por ejemplo): sin ordenar, los rangos min/max de cada bloque se solapan y el pruning no ahorra nada.

### Trampa: portar el esquema OLTP tal cual

Apuntar una herramienta de BI directo a una réplica de la base transaccional, sin modelar, parece un atajo. El resultado: nombres de columna técnicos (`fk_cli_id`), la lógica de negocio repartida en el código de la app y no en las tablas, y una pregunta simple ("ingreso por país") exige diez `JOIN` que cada analista escribe distinto —y cada uno cuadra distinto. El modelado dimensional de la lección 3 no es burocracia, es la traducción de "cómo se guardan los datos" a "cómo se piensa el negocio".

| Dimensión | OLTP (transaccional) | OLAP (analítico) |
|----|----|----|
| Patrón de acceso | Muchas operaciones chicas, pocas filas cada una | Pocas consultas, escanean millones de filas |
| Escrituras | Constantes y concurrentes | Carga por lotes; casi sin `UPDATE` |
| Modelo de datos | Normalizado (3NF) | Desnormalizado (estrella, tabla ancha) |
| Almacenamiento | Por fila | Por columna, comprimido |
| Índices | Muchos, selectivos (árbol B+) | Pocos; se poda por partición y estadísticas |
| Métrica de éxito | Latencia p99 en ms, transacciones/seg | Bytes escaneados, coste y tiempo por consulta |
| Ejemplos | PostgreSQL, MySQL, SQL Server | Snowflake, BigQuery, Redshift, DuckDB, ClickHouse |

:::note[Antes de montar un warehouse]
Muchos equipos empiezan analizando sobre una **réplica de lectura** de la base de producción o sobre un dump nocturno cargado en **DuckDB**. Aísla la carga del tráfico real y cuesta casi nada. Solo cuando las consultas tardan, los datos vienen de varias fuentes, o varias personas los necesitan a la vez, se justifica un warehouse de verdad.
:::

:::note[HTAP no te salva del modelado]
Hay motores que prometen servir ambas cargas (bases "HTAP", o extensiones columnares sobre PostgreSQL). Ayudan con el aislamiento físico, pero la tabla normalizada de la app sigue siendo incómoda de analizar: los nombres son técnicos, la lógica de negocio no está, y una pregunta simple exige conocer diez tablas. El trabajo de modelar para análisis no desaparece.
:::

## Práctica

Abre el [DuckDB shell](https://shell.duckdb.org/): es DuckDB, un motor analítico columnar, corriendo entero en tu pestaña.

**1. Mide la diferencia.** Crea 5 millones de filas y compara una consulta analítica con una de búsqueda puntual:

```sql
.timer on
CREATE TABLE ventas AS
SELECT range AS id,
       ['CL','AR','PE','MX'][1 + range % 4] AS pais,
       (random() * 1000)::INT AS monto
FROM range(5000000);

SELECT pais, sum(monto) FROM ventas GROUP BY pais;   -- OLAP
SELECT * FROM ventas WHERE id = 4821;                -- OLTP
```

**2. Mira qué columnas lee.** Corre `EXPLAIN ANALYZE SELECT sum(monto) FROM ventas;` y busca en el plan qué columnas proyecta el escaneo.

**3. Clasifica.** ¿OLTP u OLAP? (a) marcar un pedido como pagado, (b) ingreso mensual por país del último año, (c) descontar stock al comprar, (d) tasa de conversión por campaña.

<details>
<summary>Ver respuestas</summary>

- En el plan, el escaneo de `ventas` solo proyecta `monto`: las otras columnas ni se tocan. Eso es el almacenamiento columnar en acción.
- La agregación sobre 5 millones de filas termina en milisegundos porque el motor procesa bloques vectorizados de una sola columna.
- (a) OLTP, (b) OLAP, (c) OLTP, (d) OLAP. Pista: si toca pocas filas por clave y escribe, es OLTP; si escanea muchas para resumir, es OLAP.

</details>
