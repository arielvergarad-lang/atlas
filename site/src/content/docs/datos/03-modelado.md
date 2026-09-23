---
title: "Modelado dimensional"
description: "El almacenamiento es barato, pero el modelo sigue importando: define qué preguntas son fáciles de responder, qué números cuadran entre reportes, y si un analista nuevo entiende las tablas sin preguntarle a nadie."
sidebar:
  order: 3
lesson:
  id: datos-modelado
  guide: datos
  order: 3
quiz:
  - q: "¿Qué es lo primero que se decide al diseñar una tabla de hechos?"
    options:
      - "El grano: qué representa exactamente una fila"
      - "Los índices"
      - "La herramienta de BI"
      - "El nombre de las columnas"
    answer: 0
    why: "Todo lo demás (dimensiones, medidas) se deriva del grano."
  - q: "El saldo de una cuenta bancaria es una medida…"
    options:
      - "No aditiva en ninguna dimensión"
      - "Degenerada"
      - "Semi-aditiva: se suma entre cuentas, no a lo largo del tiempo"
      - "Aditiva en todas las dimensiones"
    answer: 2
    why: "Sumar el saldo de enero y el de febrero no da nada con sentido."
  - q: "¿Qué hace un SCD tipo 2 cuando cambia un atributo de la dimensión?"
    options:
      - "Agrega una columna \"valor anterior\""
      - "Borra la fila vieja"
      - "Agrega una fila nueva con vigencia desde/hasta y conserva la historia"
      - "Sobrescribe el valor anterior"
    answer: 2
    why: "Así los hechos antiguos siguen apuntando a la versión vigente en su momento."
---

El almacenamiento es barato, pero el modelo sigue importando: define qué preguntas son fáciles de responder, qué números cuadran entre reportes, y si un analista nuevo entiende las tablas sin preguntarle a nadie. El modelo dimensional de Kimball —hechos y dimensiones— sigue siendo el lenguaje común.

### Hechos  ·  dimensiones

Una **tabla de hechos** registra eventos medibles del negocio: una venta, un envío, una llamada de soporte. Contiene *medidas* numéricas (cantidad, monto, duración) y *claves foráneas* a las dimensiones. Una **dimensión** es el contexto por el que quieres cortar y filtrar: cliente, producto, tiempo, tienda, campaña. Regla mental: los hechos responden "¿cuánto?", las dimensiones responden "¿por qué, quién, cuándo, dónde?".

### El grano · lo primero que se decide

El **grano** es qué representa exactamente una fila de la tabla de hechos: "una línea de una factura", "un pedido", "el saldo de una cuenta al cierre del día". Se define antes que las columnas. Un grano mal elegido o inconsistente (algunas filas por pedido, otras por línea) hace que las sumas dupliquen o falten, y el error es silencioso.

:::tip[Por qué importa]
Casi todos los "el dashboard no cuadra" se rastrean a un `JOIN` que multiplicó filas porque alguien no tenía claro el grano de las dos tablas.
:::

### Tipos de tabla de hechos

**Transaccional**: una fila por evento, el más común. **Snapshot periódico**: una fila por entidad y periodo (inventario al cierre de cada día), para medir estados, no eventos. **Snapshot acumulado**: una fila por proceso que avanza por hitos (un pedido: creado → pagado → enviado → entregado), con una fecha por hito, para medir tiempos de ciclo.

### Aditiva · semi-aditiva · no aditiva

Una medida es **aditiva** si sumarla tiene sentido en todas las dimensiones (el monto de ventas). **Semi-aditiva** si suma en unas pero no en el tiempo (un saldo de cuenta: sumar los saldos de todos los clientes sí, sumar el saldo de ayer y hoy no). **No aditiva** si nunca se suma (un porcentaje, un ratio): hay que recalcularlo desde los componentes, no promediar promedios.

### Estrella  vs  copo de nieve

En el **esquema estrella**, cada dimensión es una sola tabla plana, aunque repita datos (el país está en `dim_cliente` aunque haya un catálogo de países). En el **copo de nieve**, las dimensiones se normalizan en sub-tablas (`dim_cliente` → `dim_ciudad` → `dim_pais`). La estrella es el default: menos joins, más rápida, más legible. El copo solo si una dimensión es gigante y cambia mucho.

``` text
                    +---------------+
                    |  dim_tiempo   |
                    | fecha_id (PK) |
                    | dia mes anio  |
                    +-------+-------+
                            |
 +--------------+   +-------+------------------+   +----------------+
 | dim_cliente  |   |      fct_ventas          |   |  dim_producto  |
 | cliente_id PK|---| cliente_id  (FK) --------|---| producto_id PK |
 | pais  plan   |   | producto_id (FK)         |   | categoria      |
 +--------------+   | fecha_id    (FK)         |   | marca          |
                    | tienda_id   (FK)         |   +----------------+
                    |------ grano: 1 fila -----|
                    |  por linea de factura    |
                    | cantidad   monto   desc  |  <- solo medidas numericas
                    +-------------+------------+
                                  |
                          +-------+-------+
                          |  dim_tienda   |
                          +---------------+
```

### Clave subrogada

Las dimensiones no usan la clave del sistema origen como clave primaria, sino una **clave subrogada** propia (un entero autoincremental o un hash). Aísla el warehouse de cambios en los ids de origen, permite tener una fila "desconocido" para hechos sin dimensión, y es imprescindible para las SCD de tipo 2.

### Slowly Changing Dimensions · SCD 1 / 2 / 3

Un cliente cambia de plan o de país. ¿Qué hace la dimensión? **Tipo 1**: sobrescribe. Simple, pero pierdes la historia: los pedidos viejos ahora "parecen" del plan nuevo. **Tipo 2**: inserta una fila nueva con nueva clave subrogada y marca `valido_desde`/`valido_hasta` y `es_actual`; los hechos apuntan a la versión vigente cuando ocurrieron. Es el estándar para análisis histórico correcto. **Tipo 3**: guarda una columna "valor anterior"; solo sirve para un cambio.

``` text
SCD Tipo 2 en dim_cliente

sk  cliente_id  pais  plan   valido_desde  valido_hasta  es_actual
--  ----------  ----  -----  ------------  ------------  ---------
 1     C-42      CL   free   2025-01-10    2026-03-01    false
 2     C-42      CL   pro    2026-03-01    9999-12-31    true

  un pedido del 2025-06 apunta a sk=1  -> se reporta como "free"
  un pedido del 2026-05 apunta a sk=2  -> se reporta como "pro"
```

### SCD tipo 1 y tipo 3, con el mismo caso

Mismo evento —el cliente C-42 cambia de plan free a pro el 2026-03-01— resuelto con las otras dos estrategias, para comparar contra el tipo 2 de arriba.

|  | Antes (2026-02) | Después (tipo 1) | Después (tipo 3) |
|----|----|----|----|
| Filas en `dim_cliente` | C-42 · plan=free | C-42 · plan=pro *(se sobrescribió)* | C-42 · plan_actual=pro · plan_anterior=free |
| Un pedido de enero, consultado hoy | — | se reporta como "pro" (incorrecto) | se reporta con plan_actual=pro; la fecha exacta del cambio no queda registrada |
| Cuándo usarlo | — | el valor viejo no tiene valor analítico (corregir un typo) | solo importa comparar "antes vs. ahora", no la fecha exacta del cambio |

:::tip[Por qué importa]
Tipo 1 es el default por accidente: es lo que hace un `UPDATE` normal si nadie decide lo contrario. Elegir el tipo de SCD por dimensión —y a veces por columna, mezclando tipo 1 y tipo 2 dentro de la misma dimensión— es una conversación de modelado, no un detalle técnico.
:::

### Dimensión degenerada · degenerate dimension

Un atributo como el **número de factura** o de **orden** vive en la tabla de hechos sin tabla de dimensión propia: no tiene otros atributos que describir (no hay "fecha de creación" del número de factura, solo el número). Se guarda directo como columna del hecho en vez de crear una `dim_factura` de una sola columna. Sirve para agrupar y para trazabilidad ("dame todas las líneas de la factura 88213") sin el costo de mantener una dimensión vacía.

### Tabla de puente · bridge

Cuando la relación entre hecho y dimensión es muchos-a-muchos (una transacción de banco con varias categorías, un paciente con varios diagnósticos), se mete una tabla intermedia con un factor de reparto. Resuelve el problema pero es fácil que duplique sumas: se documenta bien y se usa con cuidado.

### Kimball · Inmon · "one big table"

**Kimball** (bottom-up): construyes data marts dimensionales por proceso de negocio y se integran por dimensiones compartidas ("conformadas"). **Inmon** (top-down): primero un warehouse corporativo normalizado, y los marts salen de ahí. **OBT** (one big table): una tabla ancha totalmente desnormalizada por área, porque el storage es barato y algunas herramientas BI no hacen bien los joins. En la práctica moderna con dbt se mezcla: staging normalizado → marts dimensionales o tablas anchas según el consumidor.

|  | Estrella | Copo de nieve | One Big Table |
|----|----|----|----|
| Dimensiones | Una tabla plana por dimensión | Normalizadas en sub-tablas | Aplanadas dentro del hecho |
| Joins en la consulta | Pocos (hecho ↔ dim) | Muchos | Ninguno |
| Redundancia | Algo | Mínima | Mucha (aceptada) |
| Legibilidad para BI | Alta | Media | Alta si no explota en columnas |
| Cuándo | El default para BI | Dimensión enorme y muy cambiante | Herramienta sin buenos joins; feature store |

:::note[Dimensiones conformadas]
El valor real del modelo dimensional aparece cuando `dim_cliente` y `dim_tiempo` son *las mismas* para ventas, soporte y marketing. Ahí "clientes activos" significa lo mismo en los tres reportes y se pueden cruzar. Sin dimensiones conformadas tienes silos con definiciones que no cuadran, que es justo el problema que un warehouse debía resolver.
:::

## Práctica

**1. Diseña en papel.** Una pizzería quiere responder "¿cuánto vendimos por categoría, sucursal y mes?". Define el **grano** de la tabla de hechos, sus **medidas** y sus **dimensiones**.

**2. Constrúyelo** en el [DuckDB shell](https://shell.duckdb.org/):

```sql
CREATE TABLE dim_producto (producto_key INT, nombre TEXT, categoria TEXT);
CREATE TABLE dim_sucursal (sucursal_key INT, ciudad TEXT);
CREATE TABLE fct_ventas (fecha DATE, producto_key INT, sucursal_key INT, cantidad INT, monto INT);

INSERT INTO dim_producto VALUES (1,'Margarita','clásica'), (2,'Pepperoni','clásica'), (3,'Trufa','premium');
INSERT INTO dim_sucursal VALUES (1,'Santiago'), (2,'Concepción');
INSERT INTO fct_ventas VALUES
 ('2026-08-01',1,1,3,27000), ('2026-08-01',3,2,1,15000),
 ('2026-09-02',2,1,2,20000), ('2026-09-03',3,1,2,30000);
```

Escribe la consulta de ingreso por categoría, ciudad y mes.

**3. Piensa el cambio.** La "Pepperoni" pasa a categoría "premium" en septiembre. Con SCD tipo 2, ¿qué filas tendría `dim_producto` y a cuál apuntaría la venta de agosto?

<details>
<summary>Ver soluciones</summary>

1. Grano: una fila por producto vendido, por sucursal y por día (o por línea de ticket si quieres más detalle). Medidas: cantidad y monto. Dimensiones: fecha, producto, sucursal.

2. Consulta:

```sql
SELECT date_trunc('month', f.fecha) AS mes, p.categoria, s.ciudad, sum(f.monto) AS ingreso
FROM fct_ventas f
JOIN dim_producto p USING (producto_key)
JOIN dim_sucursal s USING (sucursal_key)
GROUP BY ALL ORDER BY mes, categoria, ciudad;
```

3. Dos filas para Pepperoni, cada una con su propia clave subrogada: `(2, 'clásica', vigente_desde 2025-…, vigente_hasta 2026-08-31)` y `(4, 'premium', vigente_desde 2026-09-01, vigente_hasta NULL)`. Las ventas de agosto apuntan a la clave 2 y siguen contando como "clásica".

</details>
