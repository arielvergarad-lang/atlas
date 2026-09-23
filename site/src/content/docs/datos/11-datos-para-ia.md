---
title: "Datos para IA aplicada"
description: "Casi todo lo que hace útil a una feature de IA es trabajo de datos: preparar el corpus que alimenta un RAG, construir los conjuntos con los que se evalúa un modelo, y sacar de los logs de producción los ejemplos para afinar prompts o hacer fine-tune."
sidebar:
  order: 11
lesson:
  id: datos-datos-para-ia
  guide: datos
  order: 11
quiz:
  - q: "Recall@5 = 0,6 significa que…"
    options:
      - "El 60% de las respuestas del LLM son correctas"
      - "El 60% de los 5 resultados son relevantes"
      - "La búsqueda tarda 0,6 segundos"
      - "De los fragmentos relevantes, el 60% aparece entre los 5 primeros resultados"
    answer: 3
    why: "Lo tercero es precision@5: otra métrica distinta."
  - q: "¿Por qué combinar BM25 con vectores (búsqueda híbrida)?"
    options:
      - "Porque BM25 genera embeddings mejores"
      - "BM25 acierta en términos exactos (códigos, nombres) y los vectores en el significado"
      - "Porque los vectores no funcionan solos"
      - "Para gastar menos en embeddings"
    answer: 1
    why: "Un número de factura o un SKU casi nunca se recupera bien solo con similitud semántica."
  - q: "¿Por qué deduplicar el corpus antes de crear embeddings?"
    options:
      - "Los duplicados ocupan los primeros resultados con la misma información y sesgan la recuperación"
      - "Porque los embeddings no aceptan texto repetido"
      - "Porque así el modelo alucina menos siempre"
      - "No hace falta si usas pgvector"
    answer: 0
    why: "También pagas dos veces por embeber el mismo texto."
---

Casi todo lo que hace útil a una feature de IA es trabajo de datos: preparar el corpus que alimenta un RAG, construir los conjuntos con los que se evalúa un modelo, y sacar de los logs de producción los ejemplos para afinar prompts o hacer fine-tune. El warehouse y las técnicas de esta guía son la base de ese puente hacia la guía de IA aplicada.

### Preparar un corpus para RAG

La recuperación es tan buena como el corpus. El trabajo: **extraer** el texto desde su fuente (docs, tickets, wiki, tablas del warehouse), **limpiar** el ruido (cabeceras, pies, navegación, HTML), **normalizar** (codificación, saltos de línea, tablas a texto), **enriquecer** con metadatos para filtrar después (fuente, fecha, autor, permisos, tipo de documento). Es exactamente limpieza y modelado de datos, aplicada a texto.

### Deduplicación

Los corpus reales tienen duplicados: la misma FAQ en tres sitios, versiones casi idénticas de un contrato. **Exacta**: hash del contenido normalizado. **Casi-duplicados**: *MinHash* / LSH sobre shingles, o similitud de embeddings sobre un umbral. Sin deduplicar, el modelo recupera cinco fragmentos que dicen lo mismo y desperdicia la ventana de contexto; en datasets de entrenamiento, sesga hacia lo repetido.

### Chunking · trocear el texto

Los documentos se parten en fragmentos que se indexan y recuperan. Dimensiones a decidir: **estrategia** (por tamaño fijo, por estructura —secciones, párrafos—, o semántica), **tamaño** (típico 300–800 tokens; muy grande diluye la relevancia, muy chico pierde contexto), **solape** entre fragmentos (10–20%, para no cortar una idea a la mitad). Cada fragmento guarda su `doc_id`, posición y un hash, para poder rastrearlo y regenerarlo.

### El pipeline de embeddings

Convertir cada fragmento en un vector con un modelo de embedding, en lote, y guardarlo indexado. Puntos operativos: procesar por batches (coste y límites de API), y sobre todo **versionar el modelo**: si cambias de modelo o de dimensión, los vectores viejos y nuevos no son comparables y hay que recomputar todo el índice.

``` text
 warehouse              chunking             embedding           indice
 marts.documentos  --> split por seccion --> modelo emb. v3  --> pgvector
 (texto + metadata)    300-800 tokens        batch 1000/req      HNSW
                       solape 15%            vector[1536]        + filtro por
                       guarda doc_id,                            metadata (tenant,
                       posicion, hash                            fecha, tipo)

 cambiar el modelo de embedding  ->  recomputar TODO el indice
 por eso cada fila lleva  embedding_model = 'v3'
```

#### Datasets a partir de los logs de producción

### Datasets de evaluación desde logs de producción

Para saber si un cambio de prompt o de modelo mejora algo, necesitas un conjunto fijo de casos con respuesta esperada (*golden set*). La materia prima son los logs reales: se muestrean (cubriendo casos frecuentes y raros), se anotan con la respuesta correcta o con una rúbrica, y se congelan. Cuidado con la **fuga**: si el caso de evaluación también entró al contexto o al fine-tune, la métrica miente.

### Datasets de fine-tune

Se arman con el mismo material —logs curados—, en el formato de mensajes que pide el proveedor. Lo que importa: **calidad sobre cantidad** (cientos de ejemplos buenos superan a miles ruidosos), **balance** (que no sean todos el mismo tipo de petición), y consistencia de estilo en las respuestas objetivo. Es curación de datos, lenta y poco glamorosa, y es el 80% del resultado.

### Medir si la recuperación funciona · recall@k, MRR, nDCG

Antes de medir si el LLM responde bien, hay que medir si el paso de *retrieval* trae los fragmentos correctos. **Recall@k**: de los fragmentos relevantes que existen, qué fracción aparece entre los primeros k resultados. **MRR** (mean reciprocal rank): promedia 1/posición del primer resultado relevante —castiga que lo correcto aparezca en el puesto 8 en vez del 1. **nDCG** pondera además cuán relevante es cada resultado, no solo si es relevante o no. Se calculan contra un conjunto de preguntas con la respuesta "correcta" ya etiquetada, igual que el golden set de más arriba.

### Búsqueda híbrida · BM25 + vectores

La búsqueda semántica por embeddings falla en casos donde el usuario espera coincidencia exacta: códigos de producto, siglas, nombres propios poco frecuentes en el corpus de entrenamiento del modelo de embedding. **BM25** (la familia de algoritmos detrás de la búsqueda léxica clásica, basada en frecuencia de términos) los resuelve bien. La **búsqueda híbrida** combina ambos rankings (suma ponderada o *reciprocal rank fusion*) y suele superar a cualquiera de los dos solos. pgvector se combina con el índice de texto completo nativo de PostgreSQL para esto, sin sistemas adicionales.

#### Almacenar y buscar los vectores

### pgvector · warehouse y búsqueda semántica en una BD

**pgvector** es una extensión de PostgreSQL que añade un tipo `vector` y búsqueda por vecino más cercano con índices **HNSW** o **IVFFlat**. Ventaja: los embeddings viven junto a los datos relacionales, filtras por metadatos con SQL normal y no operas otro sistema. Basta para millones de vectores; un vector store dedicado (con más algoritmos de índice, sharding y filtrado híbrido) se justifica a escalas mayores o con requisitos de latencia estrictos.

### Feature store · mención

Para modelos de ML "clásicos" (no LLM), un feature store centraliza el cálculo de variables y resuelve dos problemas: que la feature en entrenamiento y en producción se calcule igual (*training-serving skew*), y que al entrenar solo se usen datos disponibles *en ese momento* (*point-in-time correctness*, no filtrar futuro). Para la mayoría de proyectos pequeños es sobredimensionado; conviene conocer el concepto.

:::note[El vector no es la fuente de verdad]
El índice de embeddings es un artefacto derivado y desechable: siempre regenerable desde el corpus. Guarda en el warehouse el texto de cada fragmento, su origen y su hash, y trata el índice vectorial como una caché reconstruible. Así puedes cambiar de modelo, de tamaño de chunk o de vector store sin haber perdido nada.
:::

## Práctica

**1. Mide recall a mano.** Para la pregunta "¿cómo cancelo mi suscripción?", los fragmentos relevantes del corpus son `A`, `D` y `F`. Tu buscador devuelve, en orden: `D, B, C, A, E, G, F`. Calcula **recall@3**, **recall@5** y el **reciprocal rank**.

**2. Trocea un texto.** Con `uv run python`, escribe una función `chunks(texto, tamaño=500, solape=100)` que corte por caracteres con solape, y pruébala con un texto de 1.800 caracteres: ¿cuántos trozos salen y por qué importa el solape?

**3. Diseña el set de evaluación.** Toma 20 preguntas reales de usuarios (de logs o de un FAQ) y anota para cada una qué fragmentos deberían recuperarse. Ese archivo es la base para medir cualquier cambio de chunking o de modelo de embeddings.

<details>
<summary>Ver soluciones</summary>

1. Entre los 3 primeros solo está `D`: recall@3 = 1/3 ≈ 0,33. Entre los 5 primeros están `D` y `A`: recall@5 = 2/3 ≈ 0,67. El primer relevante está en la posición 1, así que el reciprocal rank = 1.

2. Solución:

```python
def chunks(texto, tamaño=500, solape=100):
    paso = tamaño - solape
    return [texto[i:i + tamaño] for i in range(0, max(len(texto) - solape, 1), paso)]

print(len(chunks("x" * 1800)))  # 5 trozos: empiezan en 0, 400, 800, 1200 y 1600
```

El solape evita que una idea quede cortada justo en el borde entre dos trozos. En producción se corta por párrafos o encabezados, no por caracteres fijos.

3. No tiene una única respuesta: lo que importa es que exista y que se vuelva a correr en cada cambio.

</details>
