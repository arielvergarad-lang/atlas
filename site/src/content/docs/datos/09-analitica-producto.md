---
title: "Analítica de producto"
description: "Los datos de producto responden a '¿la gente usa esto, vuelve, y avanza hacia el valor?'."
sidebar:
  order: 9
lesson:
  id: datos-analitica-producto
  guide: datos
  order: 9
quiz:
  - q: "El ratio DAU/MAU mide…"
    options:
      - "La tasa de conversión del funnel"
      - "El ingreso por usuario"
      - "Qué tan seguido vuelve el usuario medio: la \"pegajosidad\""
      - "Cuántos usuarios nuevos llegan por día"
    answer: 2
    why: "0,5 significa que el usuario medio usa el producto la mitad de los días del mes."
  - q: "¿Cuál de estas es típicamente una vanity metric?"
    options:
      - "Registros totales acumulados desde el lanzamiento"
      - "Retención a la semana 4 por cohorte"
      - "Conversión del paso 2 al 3 del checkout"
      - "Usuarios activos semanales"
    answer: 0
    why: "Un acumulado solo puede subir: no te dice si el producto mejora."
  - q: "¿Para qué sirve una guardrail metric en un A/B test?"
    options:
      - "Para asegurar que la mejora no rompe algo importante, como la latencia o las cancelaciones"
      - "Para elegir el ganador"
      - "Para aumentar el tamaño de muestra"
      - "Para evitar calcular significancia"
    answer: 0
    why: "Ganar en conversión y perder en reembolsos no es ganar."
---

Los datos de producto responden a "¿la gente usa esto, vuelve, y avanza hacia el valor?". Las técnicas son pocas —cohortes, funnels, retención, una métrica norte— pero se prestan a engaños de interpretación que llevan a conclusiones seguras y equivocadas.

### DAU / WAU / MAU y stickiness

Usuarios activos diarios, semanales, mensuales. El ratio **DAU/MAU** mide "pegajosidad": si es 0,5, el usuario medio usa el producto la mitad de los días del mes —propio de herramientas diarias—; 0,1 es normal en productos de uso ocasional. El número solo importa comparado consigo mismo en el tiempo y contra una definición estable de "activo".

### Retención y cohortes

Agrupa usuarios por el periodo en que se registraron (**cohorte**) y mide qué fracción sigue activa 1, 2, 4, 8 semanas después. **N-day retention**: activo exactamente el día N. **Rolling / unbounded**: activo el día N o después. La **curva de retención** típica cae fuerte y luego se aplana: si la asíntota es mayor que cero, tienes un producto; si tiende a cero, tienes una fuga.

``` text
Retencion por cohorte de registro (% activos)

cohorte    sem0   sem1   sem2   sem4   sem8
2026-06   100%    42%    31%    24%    22%   <- se aplana en ~22%: hay producto
2026-07   100%    45%    33%    26%    23%
2026-08   100%    51%    39%    30%     -    <- mejoro tras el cambio de onboarding

curva:  100 |*
         50 | *
            |  *___
          0 |      *________________  -> asintota > 0 = usuarios que se quedan
```

### Funnel · embudo de conversión

Una secuencia de pasos hacia un objetivo (visita → registro → conecta datos → crea algo → invita al equipo). Se mide cuántos usuarios llegan a cada paso y dónde está la mayor caída. Decisiones importantes: la ventana de tiempo permitida entre pasos, y si el orden es estricto o no.

``` text
visita_landing    ####################   12 400   100%
crea_cuenta       #########               5 580    45%   v cae 55% aqui
conecta_datos     ########                4 960    40%
crea_dashboard    ###                     1 860    15%   v cae 25% aqui
invita_equipo     #                         620     5%

activacion = crea_dashboard en los primeros 7 dias
el escalon grande (cuenta -> datos) es donde conviene invertir
```

### North-star metric

Una métrica que captura el valor entregado al usuario y que el equipo entero mueve: "mensajes enviados entre amigos", "noches reservadas", "documentos compartidos". Buena si predice ingresos a futuro y refleja valor real; peligrosa si se puede subir sin dar valor (entonces se optimiza el número, no el producto).

### Vanity metrics

Números que suben, se ven bien en una lámina y no informan ninguna decisión: total acumulado de registros, page views, descargas, "usuarios totales". Suben siempre por definición. La contrapartida útil es casi siempre una *tasa* o una métrica de cohorte: registros que activan, no registros; ingreso recurrente, no ingreso acumulado.

### Significancia estadística en un A/B

Que la variante B tenga una tasa de conversión más alta que A en la muestra no basta: hay que saber si la diferencia es real o ruido. El **valor p** estima la probabilidad de ver esa diferencia (o una mayor) si en realidad no hubiera ninguna; un umbral común es 0,05. El **error tipo I** es declarar ganador a algo que no lo es (falso positivo); el **error tipo II** es no detectar una mejora real por poca muestra (falso negativo). El **tamaño de muestra** necesario se calcula antes del experimento, a partir del efecto mínimo que importa detectar —no se decide sobre la marcha mirando el dashboard cada día.

### Guardrail metrics · lo que no debe empeorar

Un experimento se diseña para mover una métrica objetivo (conversión), pero se monitorean también **métricas de guardarraíl** que no deberían empeorar aunque la principal mejore: tiempo de carga, tasa de error, cancelaciones. Ganar conversión a costa de duplicar quejas de soporte no es una victoria; sin guardarraíles definidos de antemano, ese costo se descubre semanas después, si se descubre.

#### Instrumentación y herramientas

### Event tracking · el esquema de eventos

La analítica de producto vale lo que vale su instrumentación. El modelo estándar (Segment y similares): `identify` asocia un usuario con sus rasgos, `track` registra una acción con nombre y propiedades, `page`/`screen` registra navegación, `group` asocia el usuario a una organización. Necesita una **taxonomía**: nombres consistentes (`objeto_accion`, p. ej. `dashboard_creado`), propiedades tipadas, y un documento vivo de qué evento significa qué.

:::tip[Por qué importa]
Instrumentar mal es deuda cara: no puedes analizar retroactivamente un evento que no registraste, y renombrar eventos en producción parte las series históricas.
:::

### Herramientas

**PostHog**: analítica de producto (funnels, cohortes, session replay, flags), self-host o cloud, todo en uno. **Amplitude** y **Mixpanel**: especializadas en analítica de producto, potentes en exploración. **Metabase**: BI ligero, preguntas y dashboards sobre SQL, fácil de dar a gente de negocio. **Superset**: BI open source más flexible y técnico. Un stack común: eventos → warehouse → dbt → Metabase/Superset para negocio, PostHog para producto.

### Errores de interpretación

**Paradoja de Simpson**: una tendencia que se ve en cada subgrupo se invierte al agregarlos (un cambio mejora la conversión en móvil y en escritorio, pero "empeora" el total porque cambió la mezcla de tráfico). **Sesgo de supervivencia**: analizas solo a los que se quedaron. **Regresión a la media**: mediste un pico, hiciste un cambio, "bajó" —habría bajado igual. **Promedios que mienten**: el tiempo de carga medio es 1,2 s pero el p95 es 9 s; usa percentiles. **p-hacking**: mirar un experimento hasta que "sale significativo".

:::note[Instrumenta antes de lanzar]
La pregunta "¿funcionó la feature?" solo se puede responder si los eventos que la miden ya estaban emitiéndose el día del lanzamiento. Definir el evento y las propiedades es parte del diseño de la feature, no un extra para después. Lo mismo aplica a un experimento A/B: la métrica y el tamaño de muestra se fijan antes, no se eligen mirando el resultado.
:::

## Práctica

En el [DuckDB shell](https://shell.duckdb.org/), genera eventos sintéticos de 2.000 usuarios durante 60 días:

```sql
CREATE TABLE eventos AS
SELECT u AS usuario,
       DATE '2026-07-01' + ((u % 30) + d)::INT AS fecha,
       CASE WHEN hash(u, d) % 10 < 6 OR hash(u) % 10 >= 5 THEN 'visita'   -- la mitad solo mira
            WHEN hash(u, d) % 10 < 9 OR hash(u) % 10 >= 2 THEN 'carrito'
            ELSE 'compra' END AS evento
FROM range(2000) r1(u), range(30) r2(d)
WHERE hash(u * 31 + d) % 100 < 40 - d;   -- la actividad cae con los días: hay churn
```

1. Calcula **DAU** por día y el **DAU/MAU** de agosto.
2. Arma la **retención por cohorte semanal**: de los usuarios cuya primera actividad fue la semana X, qué porcentaje sigue activo 1, 2 y 3 semanas después.
3. Calcula el **funnel** visita → carrito → compra (usuarios únicos en cada paso).

<details>
<summary>Ver soluciones</summary>

```sql
-- 1
SELECT fecha, count(DISTINCT usuario) AS dau FROM eventos GROUP BY fecha ORDER BY fecha;

SELECT avg(dau) / (SELECT count(DISTINCT usuario) FROM eventos
                   WHERE fecha BETWEEN '2026-08-01' AND '2026-08-31') AS stickiness
FROM (SELECT fecha, count(DISTINCT usuario) AS dau FROM eventos
      WHERE fecha BETWEEN '2026-08-01' AND '2026-08-31' GROUP BY fecha);

-- 2
WITH primera AS (
  SELECT usuario, date_trunc('week', min(fecha)) AS cohorte FROM eventos GROUP BY usuario
), actividad AS (
  SELECT DISTINCT e.usuario, p.cohorte,
         date_diff('week', p.cohorte, date_trunc('week', e.fecha)) AS semana
  FROM eventos e JOIN primera p USING (usuario)
)
SELECT cohorte,
       count(DISTINCT usuario) FILTER (WHERE semana = 0) AS usuarios,
       round(100.0 * count(DISTINCT usuario) FILTER (WHERE semana = 1) / count(DISTINCT usuario) FILTER (WHERE semana = 0)) AS s1,
       round(100.0 * count(DISTINCT usuario) FILTER (WHERE semana = 2) / count(DISTINCT usuario) FILTER (WHERE semana = 0)) AS s2,
       round(100.0 * count(DISTINCT usuario) FILTER (WHERE semana = 3) / count(DISTINCT usuario) FILTER (WHERE semana = 0)) AS s3
FROM actividad GROUP BY cohorte ORDER BY cohorte;

-- 3
SELECT evento, count(DISTINCT usuario) AS usuarios FROM eventos GROUP BY evento ORDER BY usuarios DESC;
```

Un funnel estricto exige además el **orden** (carrito después de visita): inténtalo con `min(fecha) FILTER (WHERE evento = …)` por usuario.

</details>
