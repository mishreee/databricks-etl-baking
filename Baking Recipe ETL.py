# Databricks notebook source
# MAGIC %pip install requests
# MAGIC
# MAGIC API_KEY = "YOUR_API_KEY"  

# COMMAND ----------

spark.sql("DROP TABLE IF EXISTS baking_gold")
spark.sql("DROP TABLE IF EXISTS baking_silver")

# COMMAND ----------

import requests
import json

def fetch_baking_recipes(query, number=20):
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": API_KEY,
        "query": query,
        "number": number,
        "addRecipeInformation": True,
        "fillIngredients": True,        # this is the fix
        "instructionsRequired": True
    }
    response = requests.get(url, params=params)
    return response.json().get("results", [])

categories = ["cake", "cookies", "bread", "pastry", "muffins"]
all_recipes = []

for category in categories:
    recipes = fetch_baking_recipes(category, number=20)
    for r in recipes:
        r["search_category"] = category
    all_recipes.extend(recipes)

print(f"Total recipes fetched: {len(all_recipes)}")

# debug: check one recipe's ingredients
if all_recipes:
    print("Sample ingredients:", all_recipes[0].get("extendedIngredients", "EMPTY"))

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import lit
import pandas as pd

# Flatten raw recipes to key fields
bronze_records = []
for r in all_recipes:
    bronze_records.append({
        "id": r.get("id"),
        "title": r.get("title"),
        "category": r.get("search_category"),
        "ready_in_minutes": r.get("readyInMinutes"),
        "servings": r.get("servings"),
        "ingredients_raw": json.dumps(r.get("extendedIngredients", [])),
        "instructions_raw": json.dumps(r.get("analyzedInstructions", [])),
        "nutrition_raw": json.dumps(r.get("nutrition", {})),
        "image": r.get("image", "")
    })

bronze_df = spark.createDataFrame(pd.DataFrame(bronze_records))
bronze_df.write.format("delta").mode("overwrite").saveAsTable("baking_bronze")
print(f"Bronze table saved: {bronze_df.count()} rows")

# COMMAND ----------

from pyspark.sql.functions import col, udf, size
from pyspark.sql.types import IntegerType, StringType
import json

def count_ingredients(raw):
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return len(data)
        return 0
    except:
        return 0

def count_steps(raw):
    try:
        instructions = json.loads(raw)
        if instructions:
            return len(instructions[0].get("steps", []))
        return 0
    except:
        return 0

def complexity_label(score):
    if score is None:
        return "Unknown"
    elif score <= 15:
        return "Simple"
    elif score <= 30:
        return "Moderate"
    else:
        return "Complex"

count_ingredients_udf = udf(count_ingredients, IntegerType())
count_steps_udf = udf(count_steps, IntegerType())
complexity_label_udf = udf(complexity_label, StringType())

# Load bronze and apply transformations
bronze = spark.table("baking_bronze")

silver = bronze \
    .withColumn("ingredient_count", count_ingredients_udf(col("ingredients_raw"))) \
    .withColumn("step_count", count_steps_udf(col("instructions_raw"))) \
    .withColumn("complexity_score",
        col("ingredient_count") + col("step_count") + (col("ready_in_minutes") / 10).cast(IntegerType())) \
    .withColumn("complexity_label", complexity_label_udf(col("complexity_score"))) \
    .select("id", "title", "category", "ready_in_minutes", "servings",
            "ingredient_count", "step_count", "complexity_score", "complexity_label")

silver.write.format("delta").mode("overwrite").saveAsTable("baking_silver")
print(f"Silver table saved: {silver.count()} rows")
silver.show(5)

# COMMAND ----------

from pyspark.sql.functions import avg, count, round

silver = spark.table("baking_silver")

gold = silver.groupBy("category", "complexity_label") \
    .agg(
        count("id").alias("recipe_count"),
        round(avg("ingredient_count"), 1).alias("avg_ingredients"),
        round(avg("step_count"), 1).alias("avg_steps"),
        round(avg("ready_in_minutes"), 1).alias("avg_time_mins"),
        round(avg("complexity_score"), 1).alias("avg_complexity_score")
    ) \
    .orderBy("category", "complexity_label")

gold.write.format("delta").mode("overwrite").saveAsTable("baking_gold")
print("Gold table saved!")
gold.show()

# COMMAND ----------

# check what the raw ingredients_raw field actually looks like
from pyspark.sql.functions import col

spark.table("baking_bronze").select("title", "ingredients_raw").limit(3).show(truncate=False)