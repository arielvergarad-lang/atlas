---
title: "Orquestación de pipelines"
description: "Un pipeline de datos es una cadena de pasos con dependencias, horarios, fallos parciales y necesidad de reprocesar el pasado."
sidebar:
  order: 7
lesson:
  id: datos-orquestacion-datos
  guide: datos
  order: 7
quiz:
  - q: "¿Por qué no basta `cron` para orquestar pipelines de datos?"
    options:
      - "No funciona en Linux"
      - "No conoce dependencias, reintentos, historial de corridas ni backfill"
      - "No puede correr scripts de Python"
      - "Solo corre una vez al día"
    answer: 1
    why: "Cron dispara a una hora; no sabe si lo anterior terminó bien."
  - q: "La corrida diaria con fecha lógica 2026-09-21 representa…"
    options:
      - "La hora exacta en que arrancó"
      - "La fecha del último deploy"
      - "El día en que se creó el DAG"
      - "El periodo de datos que procesa, sin importar cuándo se ejecute"
    answer: 3
    why: "Por eso un reintento o un backfill del día 21 procesa siempre los mismos datos."
  - q: "¿Cuál es el riesgo típico de lanzar un backfill de 2 años de golpe?"
    options:
      - "Ninguno si el código es correcto"
      - "Saturar la base de origen con cientos de corridas en paralelo"
      - "Que se borre el DAG"
      - "Que el warehouse no acepte fechas viejas"
    answer: 1
    why: "Se limita la concurrencia del backfill y se corre en horario valle."
---

Un pipeline de datos es una cadena de pasos con dependencias, horarios, fallos parciales y necesidad de reprocesar el pasado. Un `cron` con scripts no aguanta eso. Los orquestadores —Airflow, Dagster, Prefect— existen para hacer visible y recuperable esa cadena. Enlaza con la sección de observabilidad de la guía de DevOps.

### Por qué no basta cron

`cron` ejecuta un comando a una hora. No sabe que el paso B depende de que A terminara *bien*, no reintenta con backoff, no te muestra qué corrió y cuánto tardó, no permite relanzar solo la parte que falló, y no tiene concepto de "procesar la fecha lógica 2026-09-01" independiente de cuándo lo corres. Un orquestador da todo eso.

### DAG, scheduling y fecha lógica

El pipeline se declara como un **DAG**: nodos (tareas) y aristas (dependencias). El scheduler lo dispara por horario o por evento. Cada ejecución tiene una **fecha lógica** (el periodo que representa), distinta de la hora real de ejecución: así un reintento o un backfill procesa el periodo correcto, no "hoy".

### Reintentos, backoff y sensores

**Reintentos**: cada tarea define cuántas veces reintentar y con qué espera creciente (*backoff*) ante fallos transitorios. **Sensores**: tareas que esperan a que algo exista antes de seguir —un archivo en S3, una partición en una tabla, otro DAG terminado—. Evitan la fragilidad de "corre a las 3 y reza para que la data ya esté".

``` text
03:00  extract_stripe --> load_raw --+--> dbt_run --> dbt_test --> publish_dash
       (retry x3,        (idempotente|   (rebuild   |  fallo?         (solo si
        backoff 5m)       MERGE por  |    marts)    |   |              dbt_test OK)
           |              clave)     |              |   +--> alerta #data-alerts
           +-- falla 3x --> alerta   |              |        y NO publica
                            y para   |         sensor: espera a que
                                     |         load_raw termine OK
                                     |
   backfill: re-ejecuta el DAG para fecha logica 2026-09-01 .. 09-08;
   cada corrida escribe SOLO su particion  ->  sin duplicados
```

### Backfill

Relanzar el DAG para un rango de fechas pasadas: llegó data histórica, cambió una transformación, o el pipeline estuvo caído dos días. Funciona bien solo si cada tarea es idempotente y parametrizada por la fecha lógica. Un buen orquestador lo hace con un comando y controla cuántas corridas lanza en paralelo para no saturar el warehouse.

### dbt dentro del orquestador

Lo normal no es que Airflow o Dagster reimplementen la lógica de transformación, sino que disparen `dbt build` como un paso del DAG y observen su resultado. **Cosmos** (Astronomer) convierte cada modelo dbt en una tarea individual de Airflow, así el DAG visible muestra staging → intermediate → marts en vez de una caja negra "correr dbt"; Dagster hace algo equivalente con su integración nativa de dbt, donde cada modelo se ve como un activo más del grafo.

### Trampa: un backfill masivo tumba la fuente

Relanzar 90 días de un DAG a la vez dispara 90 llamadas concurrentes contra una API con límite de tasa, o 90 consultas pesadas contra la base de producción a la misma hora. Un orquestador serio permite limitar el **paralelismo del backfill** (procesar de a 5 fechas lógicas a la vez) y respetar el límite de tasa de la fuente. El backfill que "funciona en dev" y tumba producción es uno de los incidentes más comunes y más evitables de orquestación.

### Orientado a tareas  vs  a activos

Airflow piensa en **tareas**: "¿qué se ejecuta y en qué orden?". Dagster introdujo pensar en **activos de datos** (*software-defined assets*): declaras "existe la tabla `fct_mrr` y depende de estas otras", y el orquestador deriva el grafo, sabe qué está desactualizado y puede rematerializar solo eso. Encaja de forma natural con el modelo de dbt.

### SLAs y observabilidad de datos

Un **SLA de datos** es un compromiso: "la tabla de ventas de ayer está lista y validada antes de las 8:00". El orquestador debe alertar si no se cumple, registrar duración de cada corrida para ver degradación, y exponer un panel de "qué corrió, cuándo, y si pasó los tests". Sin esto, te enteras de que el pipeline lleva tres días roto porque alguien de negocio pregunta por un número.

|  | Airflow | Dagster | Prefect |
|----|----|----|----|
| Modelo mental | DAG de tareas (imperativo) | Activos de datos (declarativo) | Flujos Python, dinámicos |
| Pregunta que responde | "¿Qué tareas y en qué orden?" | "¿Qué tablas existen y de qué dependen?" | "Mi función Python, con reintentos y visibilidad" |
| Backfill | Por fecha lógica | Por partición de activo | Por parámetros del flujo |
| Fuerte en | Ecosistema enorme, estándar de facto | Lineage nativo, dev local, tipos | Ergonomía Python, flujos dinámicos |
| Flojo en | Dev local, testing, pasar datos entre tareas | Comunidad más pequeña | Menos "batería incluida" para datos |

:::note[Que el orquestador orqueste, no procese]
La tentación es meter la transformación pesada en tareas Python del DAG. Mejor que el orquestador solo dispare y vigile: la ingesta la hace la herramienta de extract-load, la transformación la hace dbt *dentro del warehouse*. El orquestador aporta orden, reintentos, backfill y alertas —no músculo de cómputo.
:::

## Práctica

Ejercicio de diseño, en papel o en un editor.

Un pipeline diario hace: (1) extraer pedidos de Postgres, (2) extraer pagos de la API de Stripe, (3) cargar ambos al warehouse, (4) correr `dbt build`, (5) refrescar el dashboard.

1. Dibuja el **DAG**: ¿qué pasos pueden correr en paralelo?
2. Define **reintentos** para cada paso: ¿cuáles reintentas y con qué backoff? ¿Cuál no conviene reintentar a ciegas?
3. Hay que reprocesar todo agosto por un bug. Escribe el plan de **backfill**: ¿cuántas corridas, con qué concurrencia y cómo sabes que no duplicas datos?

<details>
<summary>Ver una solución razonable</summary>

1. (1) y (2) en paralelo → (3) espera a ambos → (4) → (5).
2. Extracciones: 3 reintentos con backoff exponencial (errores de red y 429 son transitorios). `dbt build`: 1 reintento como máximo; si falla un test, reintentar no arregla datos malos: hay que alertar. El refresco del dashboard es barato de reintentar.
3. 31 corridas, una por fecha lógica, con concurrencia de 2 o 3 para no saturar Postgres ni el rate limit de Stripe. No duplicas porque cada corrida **sobrescribe su partición** (o hace upsert por clave): es idempotente, ver la lección de ingesta.

</details>
