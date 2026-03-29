# databricks-etl-baking

An end-to-end ETL pipeline built on Databricks that extracts baking recipe data from the Spoonacular API, applies medallion architecture transformations using PySpark, and loads aggregated results into Delta Lake materialized views via Databricks Lakeflow Pipelines.

---

## overview

This project demonstrates a production-style data engineering workflow applied to a food analytics use case — analyzing the complexity of baking recipes across 5 categories (cake, cookies, bread, pastry, muffins).

The pipeline answers: **what actually makes a baking recipe complex?**

---

## architecture

```
Spoonacular API
      ↓
  Bronze layer        raw API response, flattened to Delta table
      ↓
  Silver layer        cleaned + enriched with custom complexity scoring
      ↓
  Gold layer          aggregated summary by category & complexity label
      ↓
  Databricks SQL      queryable materialized views
```

Built using the **medallion architecture** pattern on Databricks Lakeflow Pipelines.

---

## pipeline design

### bronze
- hits the Spoonacular `/recipes/complexSearch` endpoint across 5 baking categories
- uses `fillIngredients=True` and `addRecipeInformation=True` to pull full ingredient lists and metadata
- flattens raw JSON response and writes to a Delta table

### silver
- parses ingredient and instruction JSON using custom PySpark UDFs
- calculates a **complexity score** per recipe:
  ```
  complexity_score = ingredient_count + step_count + (ready_in_minutes / 10)
  ```
- assigns complexity labels: Simple (≤15), Moderate (15–30), Complex (>30)

### gold
- aggregates by `category` and `complexity_label`
- outputs: recipe count, avg ingredients, avg steps, avg prep time, avg complexity score

---

## tech stack

| tool | purpose |
|------|---------|
| Databricks Community Edition | compute + orchestration |
| Databricks Lakeflow Pipelines | pipeline execution + monitoring |
| Apache Spark (PySpark) | distributed data transformation |
| Delta Lake | ACID-compliant storage layer |
| Spoonacular API | recipe data source |
| Databricks SQL | analytical querying layer |
| Tableau Desktop | visualization (connected via Databricks connector) |
| Python | UDFs, API calls, data wrangling |

---

## key findings

- **55% of recipes scored as Simple** — most baking is more approachable than perceived
- **Bread is the most complex category** with an average complexity score of 40.0, nearly double pastry (18.5)
- **Cookies beat cake** in complexity — averaging 35.0 vs 35.0 at the complex end, but cookies have more moderate-tier recipes
- A single bread recipe hit a complexity score of 50+ with 220 min prep time — a clear outlier

---

## data quality note

Spoonacular defaults `readyInMinutes` to 45 for recipes with missing prep time data, causing clustering in the scatter distribution. This is a known API limitation and is flagged as a data quality consideration. A production pipeline would implement a data quality expectation in Lakeflow to flag or exclude these records.

---

## repo structure

```
databricks-etl-baking/
├── notebooks/
│   ├── 01_bronze_ingestion.py       API extraction + raw Delta table
│   ├── 02_silver_transform.py       PySpark UDFs + complexity scoring
│   └── 03_gold_aggregation.py       category-level aggregation
├── pipeline/
│   └── baking_dlt_pipeline.py       Lakeflow pipeline definition
├── screenshots/
│   ├── pipeline_graph.png           Bronze → Silver → Gold visual
│   └── gold_table_output.png        final aggregated output
└── README.md
```

---

## how to run

1. sign up for [Databricks Community Edition](https://community.cloud.databricks.com)
2. get a free API key from [Spoonacular](https://spoonacular.com/food-api)
3. create a new notebook and paste the contents of `01_bronze_ingestion.py` — add your API key
4. run notebooks in order: 01 → 02 → 03
5. alternatively, use `baking_dlt_pipeline.py` with Databricks Lakeflow Pipelines for automated orchestration

---

## resume context

> Built an end-to-end ETL pipeline in Databricks Lakeflow using the Spoonacular API — extracted raw recipe data, applied medallion architecture (Bronze/Silver/Gold) with PySpark transformations including custom UDFs for complexity scoring, and loaded aggregated results into Delta Lake materialized views.

---

## author

Mishree Bagdai · [github.com/mishreee](https://github.com/mishreee) · MSBA candidate, Virginia Tech Pamplin College of Business
