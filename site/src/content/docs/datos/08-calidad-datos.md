---
title: "Calidad de datos y confianza en los números"
description: "Un dashboard equivocado es peor que no tener dashboard: la gente toma decisiones con confianza sobre datos falsos, y nadie lo cuestiona porque 'sale de un sistema'."
sidebar:
  order: 8
lesson:
  id: datos-calidad-datos
  guide: datos
  order: 8
quiz:
  - q: "Un dashboard muestra datos de hace tres días sin avisar. ¿Qué dimensión de calidad falló?"
    options:
      - "Unicidad"
      - "Validez"
      - "Consistencia de tipos"
      - "Frescura"
    answer: 3
    why: "`dbt source freshness` existe justamente para detectarlo antes que el usuario."
  - q: "¿Qué gana la cuarentena de filas malas frente a hacer fallar todo el batch?"
    options:
      - "Hace el pipeline más rápido siempre"
      - "El pipeline sigue con las filas buenas y las malas quedan aparte para revisarlas"
      - "Borra las filas malas automáticamente"
      - "Evita tener que escribir tests"
    answer: 1
    why: "Una fila corrupta no bloquea el reporte de todo el negocio, pero tampoco se pierde en silencio."
  - q: "¿Qué es un contrato de datos?"
    options:
      - "Un contrato legal con el proveedor del warehouse"
      - "Un test de unicidad"
      - "Una licencia de uso de datos"
      - "Un acuerdo explícito sobre esquema y semántica entre quien produce y quien consume el dato"
    answer: 3
    why: "Hace que un cambio en la fuente rompa en el productor, no en el dashboard."
---

Un dashboard equivocado es peor que no tener dashboard: la gente toma decisiones con confianza sobre datos falsos, y nadie lo cuestiona porque "sale de un sistema". La calidad de datos es el trabajo de hacer que los números merezcan esa confianza, y de saber a quién avisar cuando dejan de merecerla.

### Las dimensiones de calidad

Lo que se monitorea, más allá de "¿está bien?": **frescura** (¿cuándo se actualizó por última vez?), **volumen** (¿llegaron aproximadamente las filas de siempre, o cero, o el triple?), **esquema** (¿cambió un tipo, desapareció una columna?), **distribución** (¿el rango, la media, el % de nulos siguen normales?), **unicidad** e **integridad referencial**.

### Tests en el pipeline

**dbt tests**: aserciones declarativas junto al modelo, la primera línea de defensa. **Great Expectations**: un framework más rico —"expectativas" versionadas sobre un dataset (esta columna entre 0 y 100, este % de nulos máximo), con documentación de resultados—, útil sobre datos que entran antes de dbt. **Soda** y otros ocupan un espacio parecido. La idea común: el pipeline *se detiene o alerta* si los datos no cumplen, en vez de publicar basura.

``` sql
# Great Expectations: expectativas versionadas sobre un dataset
validator.expect_column_values_to_not_be_null("pedido_id")
validator.expect_column_values_to_be_unique("pedido_id")
validator.expect_column_values_to_be_between("monto", min_value=0, max_value=100000)
validator.expect_column_values_to_be_in_set("estado", ["pagado", "pendiente", "anulado"])
validator.expect_table_row_count_to_be_between(min_value=1000)   # volumen
```

### Detección de anomalías

Los tests fijos ("monto entre 0 y 100000") no atrapan un descenso del 40% en las filas diarias si sigue "dentro de rango". La detección de anomalías compara la métrica de hoy con su historial (media móvil, banda de desviación, estacionalidad) y alerta cuando se sale del patrón. Es lo que hacen las plataformas de *data observability* tipo Monte Carlo, y se puede aproximar con un test que consulte los últimos 30 días.

### Cuarentena de filas malas · en vez de fallar todo el batch

Frente a un test que falla, la opción binaria "para todo el pipeline" es a veces peor que el problema: cien filas con un `email` mal formado no deberían bloquear las otras diez mil válidas. El patrón de **cuarentena**: las filas que no pasan validación se apartan a una tabla separada (con el motivo del rechazo) en vez de entrar al mart o de tumbar la corrida entera; alguien las revisa después. dbt lo soporta con la config `store_failures: true` en un test, que guarda las filas que fallaron en una tabla en vez de solo contarlas.

### dbt source freshness

Un test de frescura no verifica el *contenido* de una tabla, verifica que **llegó a tiempo**: compara la columna de fecha de actualización de una fuente contra el reloj y falla si pasó demasiado (`warn_after` / `error_after`). Es la primera alarma de un pipeline roto —antes de que ningún test de calidad sobre los datos en sí llegue a ejecutarse, porque el dato nuevo nunca llegó.

### Contratos de datos · data contracts

Un acuerdo explícito entre quien **produce** los datos (el equipo de la app que emite eventos) y quien los **consume** (analítica): qué campos, con qué tipos y semántica, con qué garantías de frescura y qué pasa si va a cambiar. Sin contrato, un desarrollador renombra un campo en un sprint normal y rompe silenciosamente tres dashboards y un modelo de ML aguas abajo.

:::tip[Por qué importa]
La fuente de la mayoría de incidentes de datos es un cambio upstream que nadie comunicó porque nadie sabía que alguien dependía de eso.
:::

### Data lineage · de dónde viene cada columna

El grafo que rastrea una columna del dashboard hasta la tabla, el modelo, el campo de staging y la fuente original, con las transformaciones en cada salto. Sirve para dos cosas: **impacto** ("si toco este campo en Stripe, ¿qué se rompe?") y **depuración** ("este número está mal, ¿en qué paso se torció?"). dbt lo genera del DAG; herramientas de catálogo lo extienden hasta las columnas.

``` text
  fct_mrr.mrr_usd
    ^
    |  sum(monto_centavos) / 100        agrupado por mes
  int_revenue.monto_centavos
    ^
    |  coalesce(monto_reembolsado, monto_cobrado)
  stg_stripe_charges.monto_cobrado
    ^
    |  cast(raw.amount as integer)      renombra y castea
  raw.stripe_charges.amount            (columna JSON cruda)
    ^
    |  Fivetran sync cada 6 h
  Stripe API  /v1/charges.amount

  cambiar el tipo de "amount" en Stripe  ->  el cast en stg falla en silencio
  ->  monto_cobrado queda NULL  ->  mrr_usd cae sin motivo aparente
  el lineage te dice A QUIEN avisar ANTES de tocar nada
```

### El coste de un dashboard mal

Un bug en una API tira un error y alguien lo ve. Un bug en un pipeline produce un número plausible pero falso: se presenta en la reunión, se decide sobre él, y el error se descubre —si se descubre— meses después, cuando ya guió presupuesto y prioridades. Por eso la inversión en tests, contratos y lineage se paga sola: el fallo silencioso es el caro.

:::note[La métrica que nadie valida]
En casi toda organización hay un número que todos citan ("tenemos 12.000 usuarios activos") cuya definición exacta nadie recuerda y cuyo cálculo nadie ha revisado en un año. Suele estar mal: cuenta bots, o incluye cuentas de prueba, o el filtro de fecha está desfasado. Encuentra esa métrica, define su lógica en dbt con un test, y documéntala.
:::

## Práctica

En el [DuckDB shell](https://shell.duckdb.org/):

```sql
CREATE TABLE pagos AS SELECT * FROM (VALUES
  (1, 'CLP', 15000, TIMESTAMP '2026-09-20 10:00'),
  (2, 'USD',    20, TIMESTAMP '2026-09-20 11:00'),
  (3, 'clp',  5000, TIMESTAMP '2026-09-20 12:00'),
  (5, 'CLP', -3000, TIMESTAMP '2026-09-20 13:00'),
  (4, 'EUR',  NULL, TIMESTAMP '2026-09-21 09:00')
) t(id, moneda, monto, creado);
```

1. Escribe tests que devuelvan las filas que fallan: `monto` no nulo, `monto` positivo, `moneda` dentro de `('CLP','USD')` (valores aceptados).
2. Mueve las filas malas a `pagos_cuarentena` y deja las buenas en `pagos_ok`.
3. Escribe un chequeo de **frescura**: alerta si el pago más reciente tiene más de 24 horas.

<details>
<summary>Ver soluciones</summary>

```sql
SELECT * FROM pagos WHERE monto IS NULL OR monto <= 0 OR moneda NOT IN ('CLP','USD');

CREATE TABLE pagos_cuarentena AS
SELECT *, 'regla de calidad' AS motivo FROM pagos
WHERE monto IS NULL OR monto <= 0 OR moneda NOT IN ('CLP','USD');

CREATE TABLE pagos_ok AS
SELECT * FROM pagos
WHERE monto > 0 AND moneda IN ('CLP','USD');

SELECT max(creado) AS ultimo, now() - max(creado) > INTERVAL 24 HOUR AS atrasado FROM pagos;
```

Fíjate que `'clp'` en minúscula cae en cuarentena: ¿es un dato malo o falta normalizar en staging? Esa pregunta es la mitad del trabajo de calidad. Otro detalle: `pagos_ok` usa condiciones positivas porque con un `monto` nulo, `monto > 0` da `NULL` y la fila queda fuera sola; al revés, `NOT (monto <= 0)` también daría `NULL`, así que el test de nulos siempre va explícito.

</details>
