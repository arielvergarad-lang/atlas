---
title: "El data warehouse hoy"
description: "El warehouse moderno separó dos cosas que antes venían pegadas: dónde viven los datos y qué máquina los procesa."
sidebar:
  order: 4
lesson:
  id: datos-warehouse
  guide: datos
  order: 4
quiz:
  - q: "¿Qué permite separar el cómputo del almacenamiento?"
    options:
      - "Que cada consulta use un solo nodo"
      - "Escalar o apagar el cómputo por su cuenta y pagar solo cuando consultas"
      - "Guardar los datos sin comprimir"
      - "Evitar el SQL"
    answer: 1
    why: "Los datos viven en almacenamiento barato; el cómputo se enciende según la carga."
  - q: "¿Qué agregan los formatos de tabla (Iceberg, Delta, Hudi) sobre archivos Parquet?"
    options:
      - "La compresión columnar"
      - "Índices B-tree"
      - "Un motor de consultas propio"
      - "Transacciones, evolución de esquema y time travel sobre los archivos"
    answer: 3
    why: "Parquet ya es columnar y comprimido; el formato de tabla agrega la capa de metadatos transaccional."
  - q: "¿Cuándo suele bastar DuckDB local en vez de un warehouse?"
    options:
      - "Cuando cientos de usuarios consultan a la vez"
      - "Solo con menos de mil filas"
      - "Nunca en producción"
      - "Cuando los datos caben en una máquina y los consulta una persona o un proceso"
    answer: 3
    why: "DuckDB procesa decenas de GB en un portátil; lo que no resuelve es la concurrencia multiusuario gestionada."
---

El warehouse moderno separó dos cosas que antes venían pegadas: dónde viven los datos y qué máquina los procesa. Eso cambió el modelo de costos, hizo viable el "carga todo y ya veremos", y abrió la puerta al lakehouse. También hizo que, para muchos casos, DuckDB en tu portátil sea suficiente.

#### Cómo está construido

### Separación de cómputo y almacenamiento

Los datos se guardan una sola vez en almacenamiento de objetos barato (S3, GCS). El **cómputo** es un clúster efímero que se enciende para una consulta y se apaga después. Consecuencias: puedes tener varios clústeres de distinto tamaño sobre los mismos datos sin copiarlos, escalar en segundos, y no pagar cómputo cuando nadie consulta.

``` text
  consulta A          consulta B          consulta C
  (warehouse XS)      (warehouse XL)      (warehouse M)
       |                   |                   |
       +---------+---------+---------+---------+
                 v                   v
       +-------------------------------------------+
       |     ALMACEN DE OBJETOS  (S3 / GCS)         |
       |     Parquet particionado + metadatos       |
       +-------------------------------------------+

  computo: se apaga si no corre, escala por consulta, aislado por equipo
  almacen: barato, siempre disponible, una sola copia de la verdad
```

### Micro-particiones y pruning

El motor divide cada tabla en miles de bloques y guarda estadísticas de cada uno (min, max, nº de nulos por columna). Cuando consultas `WHERE fecha = '2026-09-01'`, lee los metadatos, descarta los bloques cuyo rango no incluye esa fecha (**partition pruning**) y solo escanea los que quedan. Consultar bien —filtrar por la columna de partición, no por una función sobre ella— es la diferencia entre escanear 2 GB o 2 TB.

### Formatos columnares en disco · Parquet

**Parquet** (y ORC) es un formato de archivo columnar, comprimido, con esquema y estadísticas embebidas. Es el formato franco del ecosistema: lo leen Spark, DuckDB, Polars, BigQuery, Snowflake, pandas. Guardar tus datos crudos en Parquet particionado en S3 ya te da el 80% de un warehouse sin montar nada.

### Formatos de tabla · Iceberg, Delta, Hudi

Un montón de archivos Parquet no es una tabla: no hay transacciones, ni renombrar columnas, ni "cómo estaba ayer". Un **table format** añade una capa de metadatos encima que da `ACID`, evolución de esquema, *time travel* (consultar un snapshot pasado) y borrados eficientes. **Apache Iceberg** es el que está ganando como estándar abierto; **Delta Lake** viene de Databricks.

#### Dónde viven los datos y qué garantías dan

### Lake  vs  warehouse  vs  lakehouse

El **data lake** es almacenamiento barato con archivos crudos y esquema al leer: flexible, pero sin gobierno se vuelve un "pantano" que nadie confía. El **warehouse** da estructura, ACID y rendimiento, a cambio de meter los datos en su formato (y a veces lock-in y coste). El **lakehouse** intenta lo mejor de ambos: archivos abiertos (Parquet) en tu bucket + un table format (Iceberg/Delta) que aporta las garantías del warehouse, consultables por varios motores.

|  | Data warehouse | Data lake | Lakehouse |
|----|----|----|----|
| Formato | Propietario del motor | Archivos crudos (Parquet, JSON, CSV) | Parquet + capa de tabla (Iceberg/Delta) |
| Esquema | Al escribir | Al leer | Al escribir, sobre el lake |
| Transacciones / ACID | Sí | No | Sí (snapshots, time travel) |
| Gobierno y calidad | Fuerte | Débil | Fuerte |
| Coste | Cómputo + almacenamiento del motor | Solo objeto barato | Objeto barato + motor externo |
| Riesgo | Lock-in; caro a escala | Pantano sin catálogo | Stack más nuevo, más piezas |
| Ejemplos | Snowflake, Redshift, BigQuery | S3 + Glue Catalog | Databricks, Snowflake+Iceberg, DuckDB+Iceberg |

#### Coste y rendimiento

### Cómo se cobra · en términos relativos

Los modelos difieren y conviene entenderlos antes de elegir. **BigQuery** cobra sobre todo por *bytes escaneados* por cada consulta (más una opción de capacidad reservada): consultas mal filtradas o `SELECT *` sobre tablas anchas se pagan caro. **Snowflake** cobra por *segundos de warehouse activo* según el tamaño del clúster: importa apagarlo rápido y no sobredimensionarlo. **Redshift** tradicionalmente cobra por nodos provisionados (pagas aunque no consultes), con opciones serverless más recientes. **DuckDB** corre en tu máquina: el "coste" es la RAM y el CPU que ya tienes.

:::tip[Por qué importa]
La factura de un warehouse la infla casi siempre un puñado de consultas o dashboards que se refrescan cada minuto escaneando tablas enormes. Medir el coste por consulta y particionar bien es FinOps de datos.
:::

### Snowflake, BigQuery, Redshift y DuckDB, uno al lado del otro

Los cuatro resuelven "SQL analítico rápido sobre columnas", pero con arquitecturas y modelos de costo distintos. Compara por lo estructural, no por precio de lista (cambia todo el tiempo — ver la nota al pie de esta guía).

|  | Snowflake | BigQuery | Redshift | DuckDB |
|----|----|----|----|----|
| Cómputo vs almacenamiento | Separados; "warehouses" virtuales que se apagan solos | Separados; serverless, sin clúster que administrar | Acoplados en clúster clásico; RA3/Serverless los separa | No aplica: motor embebido en un solo proceso |
| Unidad que se cobra | Segundos de cómputo activo (créditos) | Bytes escaneados (on-demand) o slots reservados | Nodos-hora, o cómputo serverless por uso | Ninguna: es la CPU/RAM que ya tienes |
| Formato de tabla nativo | Propietario (micro-particiones); lee Iceberg externo | Propietario (Capacitor); lee Iceberg/Delta externo | Propietario; Redshift Spectrum lee S3/Iceberg | Lee Parquet/CSV/JSON/Iceberg directo, sin importar |
| Escala típica cómoda | GB a decenas de TB por warehouse | TB a PB, sin límite operativo visible | GB a bajos PB | Hasta el tamaño de RAM/disco de una máquina |
| Cuándo | Equipo de analítica que no quiere operar infraestructura | Ya vives en GCP, cargas muy variables o picos grandes | Ya vives en AWS, carga predecible que justifica nodos reservados | Proyecto pequeño, notebook, o motor embebido dentro de una app |

### Clonado sin copia y "time travel"

Snowflake, BigQuery y los table formats tipo Iceberg permiten crear un **clon** de una tabla o esquema completo que no copia bytes: solo apunta a los mismos micro-bloques hasta que algo se modifica (copy-on-write). Sirve para clonar producción a un entorno de pruebas en segundos, sin duplicar terabytes. El mismo mecanismo de versionado por snapshots habilita **time travel**: consultar la tabla "como estaba hace 3 días" o recuperarla tras un `DELETE` equivocado, dentro de una ventana de retención configurable.

### Particionado y clustering

Elegir por qué columna se agrupan físicamente los datos (normalmente fecha, a veces tenant o región) determina cuánto se puede podar. Particionar por algo que casi nunca aparece en el `WHERE` no ayuda; particionar por algo con demasiados valores distintos (partición por usuario) genera millones de archivos diminutos y empeora todo. La fecha del evento es el default sensato.

### Cuándo DuckDB local basta

**DuckDB** es un motor analítico columnar embebido (como "SQLite para OLAP"): sin servidor, una dependencia, consulta Parquet/CSV/JSON directo, incluso desde S3. Si tus datos caben en decenas de GB —y la mayoría de los datasets de una PyME o de un proyecto freelance caben— procesarlos en DuckDB o en un notebook es más rápido de montar, gratis y suficiente. El warehouse gestionado se justifica por escala, concurrencia de muchos usuarios, o necesidad de que los datos estén siempre disponibles sin tu máquina.

``` sql
-- consulta directa sobre archivos, sin cargar ni crear tablas
SELECT categoria, COUNT(*) AS n, ROUND(AVG(precio), 2) AS precio_medio
FROM read_parquet('s3://bucket/eventos/anio=2026/mes=*/*.parquet')
WHERE precio > 0
GROUP BY categoria
ORDER BY n DESC
LIMIT 20;

-- unir un CSV local con un Parquet remoto en la misma query
SELECT *
FROM 'clientes.csv' c
JOIN read_parquet('s3://bucket/pedidos/*.parquet') p USING (cliente_id);
```

:::note["Big data" es más raro de lo que parece]
La mayoría de las organizaciones nunca tienen una tabla que no quepa en la RAM de una máquina grande. Montar Spark, un clúster y un warehouse caro "por si acaso" añade meses de complejidad para datos que DuckDB o Polars procesan en segundos. Mide el tamaño real de tus tablas activas antes de elegir la arquitectura.
:::

## Práctica

En el [DuckDB shell](https://shell.duckdb.org/) (si el shell web no te deja escribir archivos, usa la [CLI de DuckDB](https://duckdb.org/docs/installation/) local):

```sql
CREATE TABLE ventas AS
SELECT range AS id, DATE '2026-01-01' + (range // 20000)::INT AS fecha, (random()*1000)::INT AS monto
FROM range(2000000);

COPY (SELECT * FROM ventas ORDER BY fecha) TO 'ventas.parquet' (FORMAT parquet, ROW_GROUP_SIZE 100000);
```

1. Mira las estadísticas por bloque: `SELECT row_group_id, path_in_schema, stats_min, stats_max FROM parquet_metadata('ventas.parquet') WHERE path_in_schema = 'fecha';`
2. Cuenta cuántos row groups **podrían** contener el 15 de febrero (los demás se descartan sin leerlos):

```sql
SELECT count(*) FILTER (WHERE stats_min <= '2026-02-15' AND stats_max >= '2026-02-15') AS grupos_a_leer,
       count(*) AS grupos_total
FROM parquet_metadata('ventas.parquet') WHERE path_in_schema = 'fecha';
```

3. Repite el `COPY` cambiando `ORDER BY fecha` por `ORDER BY random()` y vuelve a contar.

<details>
<summary>Ver qué deberías observar</summary>

- `parquet_metadata` muestra el min/max de `fecha` por row group: son los **zone maps** de la lección, guardados dentro del archivo.
- Ordenado: solo **2 de 20** row groups pueden contener esa fecha (el día cae en el borde entre dos); los otros 18 se saltan sin leerlos.
- Desordenado: **20 de 20**. Cada row group contiene casi todo el rango de fechas, así que no se puede descartar ninguno y hay que leer los 2 millones de filas. Esto es lo que significa que "el orden físico importa más que el índice".

</details>
