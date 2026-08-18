import polars as pl
from polars import selectors as cs
from pathlib import Path

"""
The extraction from sosatel returns 1 csv file for each day of data.
This cript aggregates all the files into a single parquet file.

2 files are porduced:
    - hour level data
    - day level data
"""

# ---- Config ---- #
RAW_DIR = Path("data/sosatel/extracted")
OUTPUT_DIR = Path("data/sosatel/processed")


# ---- Process ---- #
# Hourly first (data is at the hour level from extraction)
df_hourly = (
    pl.scan_csv(RAW_DIR / "*.csv", include_file_paths="file_path") # the file name is used to extract the date of the data
    .with_columns(
        pl.col("file_path")
        .map_elements(lambda p: Path(p).stem, return_dtype=pl.String)
        .alias("date")
        .str.to_date()
        .sort()
    )
    .drop("file_path")
    .select(["date", pl.exclude("date")])
).sort("date")


# daily
df_daily = (
    df_hourly.drop("heure_locale")
    .group_by("date")
    .agg(
        pl.exclude("^pourcentage_.*$").sum(),
        pl.col("^pourcentage_.*$").mean(),
    )
    .with_columns(cs.by_dtype(pl.Float64).round(2))
)




# # ---- Sink to disk as parquet ---- #

min_date = df_hourly.select("date").min().collect().item()
max_date = df_hourly.select("date").max().collect().item()

df_hourly.sink_parquet(
    OUTPUT_DIR / "hourly" / f"sosatel_hourly_{min_date}-{max_date}.parquet"
)

df_daily.sink_parquet(
    OUTPUT_DIR / "daily" / f"sosatel_daily_{min_date}-{max_date}.parquet"
)
