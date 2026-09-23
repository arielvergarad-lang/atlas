---
title: "Two worlds: transactional and analytical"
description: "The database behind an application and the one that answers 'how much did we sell per country last quarter?' are optimized for opposite things."
sidebar:
  order: 1
lesson:
  id: datos-oltp-vs-olap
  guide: datos
  order: 1
quiz:
  - q: "Running a heavy report directly against the app's production database is risky mainly because…"
    options:
      - "SQL can't aggregate millions of rows"
      - "An OLTP database can only read one row at a time"
      - "Reports need data in JSON"
      - "It competes for CPU and locks with user traffic"
    answer: 3
    why: "It's fault isolation: one heavy report can degrade checkout."
  - q: "Why is \"sum the amount over 40 million rows\" faster in a column store?"
    options:
      - "It has more B-tree indexes"
      - "It stores rows normalized"
      - "It does fewer `JOIN`s by design"
      - "It reads only that column, contiguous and compressed"
    answer: 3
    why: "A row store has to read every column of each row even when it needs just one."
  - q: "In a columnar engine, what makes zone maps (min/max per block) actually skip blocks?"
    options:
      - "Having a B-tree index per column"
      - "Normalizing to third normal form"
      - "Using UUIDs as the primary key"
      - "The physical order of the rows, for example by date"
    answer: 3
    why: "Without ordering, each block's min/max ranges overlap and pruning saves nothing."
---

The database behind an application and the one that answers "how much did we sell per country last quarter?" are optimized for opposite things. Understanding why is the entry point to everything else: modeling, columnar storage and the warehouse exist because a single database can't be good at both workloads.

### Transactional workload · OLTP

Lots of small, concurrent operations: create an order, mark a message as read, decrement stock. Each one touches few rows, has to be fast (milliseconds) and correct under concurrency. The design optimizes for **writes** and for reading specific rows by key. This is what the Backend guide covers: PostgreSQL or MySQL behind an API.

### Analytical workload · OLAP

Few queries, but each one reads millions of rows to aggregate them: sums, averages, counts, groupings, time windows. There's almost no `UPDATE`; data arrives in batches and is queried many times. The design optimizes for **scanning entire columns** as fast and cheaply as possible.

:::tip[Why it matters]
If you run these queries against the app's database, you compete for CPU and locks with user traffic: a heavy report can degrade checkout. The separation isn't purism, it's fault isolation.
:::

### Normalize vs denormalize

OLTP **normalizes**: every fact lives in one place, referenced by keys, so a correction happens once and nothing contradicts itself. OLAP **denormalizes** on purpose: it repeats the country name and category on every sales row so the query doesn't need ten `JOIN`s. Storage is cheap; scan time and clarity for whoever queries are not.

### Row store vs column store

A **row store** keeps all of a row's columns together on disk: ideal for "give me order 4821 in full". A **column store** keeps each column separately and contiguously: for "sum the amount over 40 million rows" it reads only that column and skips the rest. That's the underlying difference between an OLTP database and an analytical engine.

```text
ROW  (row store, OLTP)               COLUMN  (column store, OLAP)

block 1: [ 1 | Ana  | CL | 120 ]     block A: [ 1  2  3  4 ... ]       id
block 2: [ 2 | Beto | AR |  90 ]     block B: [ Ana Beto Cee ... ]     name
block 3: [ 3 | Cee  | CL | 300 ]     block C: [ CL AR CL CL ... ]      country
                                     block D: [ 120 90 300 ... ]       amount

"give me row 2 in full"   1 block               4 blocks (one per column)
"sum all amounts"         3 blocks (all)        1 block, already contiguous
"count per country"       3 blocks              1 block + it compresses:
                                                 CL,CL,CL  ->  CL x3  (RLE)
```

### Why columnar compresses and scans fast

Data of the same type and domain stored together compresses far better: **run-length** (CL repeated 900 times → "CL ×900"), **dictionary** (maps "Chile" to a small integer), **delta** (stores differences between sorted values). Fewer bytes on disk = less reading = faster. On top of that, the engine processes **vectorized blocks** (thousands of values per instruction) instead of row by row.

### MPP · massively parallel processing

Warehouses split a query across tens or hundreds of nodes that scan different chunks of the table at the same time and combine the results. That's why an aggregation over a billion rows finishes in seconds: it's not one faster machine, it's many working in parallel over partitioned data.

### Indexes in an analytical engine · zone maps, not B-trees

A B-tree index helps find one row among millions; in OLAP you almost always scan millions of rows anyway, so maintaining it costs more than it saves. Columnar engines use **zone maps** instead (min/max per block, to discard whole blocks) and sometimes per-column **bloom filters** to skip blocks where an exact value can't be. The structure that matters most isn't the index, it's the **physical order** of the rows (by date, for example): unsorted, each block's min/max ranges overlap and pruning saves nothing.

### Trap: porting the OLTP schema as is

Pointing a BI tool straight at a replica of the transactional database, without modeling, looks like a shortcut. The result: technical column names (`fk_cli_id`), business logic scattered across the app code instead of the tables, and a simple question ("revenue per country") requires ten `JOIN`s that every analyst writes differently —and each one adds up differently. The dimensional modeling in lesson 3 isn't bureaucracy, it's the translation from "how the data is stored" to "how the business thinks".

| Dimension | OLTP (transactional) | OLAP (analytical) |
|----|----|----|
| Access pattern | Many small operations, few rows each | Few queries, scanning millions of rows |
| Writes | Constant and concurrent | Batch loads; almost no `UPDATE` |
| Data model | Normalized (3NF) | Denormalized (star, wide table) |
| Storage | By row | By column, compressed |
| Indexes | Many, selective (B+ tree) | Few; pruning by partition and statistics |
| Success metric | p99 latency in ms, transactions/sec | Bytes scanned, cost and time per query |
| Examples | PostgreSQL, MySQL, SQL Server | Snowflake, BigQuery, Redshift, DuckDB, ClickHouse |

:::note[Before building a warehouse]
Many teams start analyzing on a **read replica** of the production database, or on a nightly dump loaded into **DuckDB**. It isolates the workload from real traffic and costs almost nothing. Only when queries get slow, data comes from several sources, or several people need it at once is a real warehouse justified.
:::

:::note[HTAP doesn't save you from modeling]
Some engines promise to serve both workloads ("HTAP" databases, or columnar extensions on top of PostgreSQL). They help with physical isolation, but the app's normalized table is still awkward to analyze: the names are technical, the business logic isn't there, and a simple question requires knowing ten tables. The work of modeling for analysis doesn't go away.
:::

## Practice

Open the [DuckDB shell](https://shell.duckdb.org/): it's DuckDB, a columnar analytical engine, running entirely in your tab.

**1. Measure the difference.** Create 5 million rows and compare an analytical query with a point lookup:

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

**2. See which columns it reads.** Run `EXPLAIN ANALYZE SELECT sum(monto) FROM ventas;` and look in the plan for which columns the scan projects.

**3. Classify.** OLTP or OLAP? (a) mark an order as paid, (b) monthly revenue per country over the last year, (c) decrement stock on purchase, (d) conversion rate per campaign.

<details>
<summary>See answers</summary>

- In the plan, the scan of `ventas` projects only `monto`: the other columns aren't touched. That's columnar storage at work.
- The aggregation over 5 million rows finishes in milliseconds because the engine processes vectorized blocks of a single column.
- (a) OLTP, (b) OLAP, (c) OLTP, (d) OLAP. Hint: if it touches few rows by key and writes, it's OLTP; if it scans many to summarize, it's OLAP.

</details>
