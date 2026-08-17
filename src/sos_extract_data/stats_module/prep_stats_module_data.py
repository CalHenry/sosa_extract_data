import polars as pl
import polars.selectors as cs
from pathlib import Path
import unicodedata

"""
This script prepares and cleans the extracted data of stats_module.

Expected input: output 'convert_fake_xls_to_parquet.py' (parquet file)

The script does 4 things:
    - fix the time values
    - fix the date values
    - apply the correct schema
    - anonymize 'Ecoutant' names

The script outputs a single parquet file.

All the polars code uses the lazy API.
Only the last line to sink into the final parquet file actually takes time to run and load the data in memory
"""

# ------ Config ------ #
RAW_PATH = Path("data/stats_module/raw")
PROCESSED_PATH = Path("data/stats_module/processed")

# Anonymization
ANOM = True

# ------ Import & standardize columns names ------ #
df_raw = pl.scan_parquet(RAW_PATH / "ecoutants_2010_2026.parquet")

df = df_raw.rename(
    {
        col: unicodedata.normalize("NFKD", col)  # remove accents
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .replace(" ", "_")
        for col in df_raw.collect_schema().names()
    }
)

# ------ Data manipulations & cleaning ------ #

# Anonymization of Ecoutant
"""
⚠️ Current implementation is not 100% stable accross versions of the data (ex ecoutant_2010_2016.parquet and ecoutant_2017_2026.parquet).
To get the same id for the same ecoutant, we have to ensure that the data is ordered the same.
This is true until a new ecoutant appears in the data, then the order might change.
➡ This is an issue to fix if we have to do:
    - process more than 1 file with this script (ex ecoutant_part1 and ecoutant_part2)
    - process new ecoutant data to aggregate with the previous file
Solution: Improve the script to use 'uuid' python module to create true unique IDs
(makes the code more expensive bc it requires to collect the list of unique ecoutant, and it breaks the full lazyness of this current script)
➡ To keep this version of the code: HAVE TO aggregate all the ecoutant data BEFORE running this script.

'.with_row_index()' is great bc it's fast, lazy and simple, this gives great performances, but limited if the data work spread to several files.
"""
mapping = (
    df.select("ecoutant")
    .unique()
    .with_row_index("id_var")
    .with_columns(ecoutant_anom="sosae_" + pl.col("id_var").cast(pl.String))
).drop("id_var")


# Hours columns
"""
2 type of errors:
- values above 23 and below 30 -> report the number of hours as mornign hours (25 -> 01, 29 -> 05)
- values above 30 -> replace by the last value of 'heure_fin_appel', as it is the last know correct time for the given plage

About intermediate variable names:
'__h' is the hour variable (contains only the extracted hour from the hh:mm:ss time)
'__hfixed' is '__h' but fixed
"""

df_clean_times = (
    df
    # extract the hours from 'heure' cols
    .with_columns(
        cs.starts_with("heure_")
        .str.slice(0, 2)
        .cast(pl.Int8, strict=False)
        .name.suffix("__h")
    )
    # fix the 24-29 overnight rollover encoding
    .with_columns(
        pl.when(cs.ends_with("__h").is_between(24, 29))
        .then(cs.ends_with("__h") - 24)
        .otherwise(cs.ends_with("__h"))
        .name.suffix("fixed")  # -> __hfixed
    )
    # rebuild each original string column with the fixed hour
    .with_columns(
        [
            pl.when(pl.col(f"{c}__hfixed") != pl.col(f"{c}__h"))
            .then(
                pl.col(f"{c}__hfixed").cast(pl.String).str.zfill(2)
                + pl.col(c).str.slice(2)
            )
            .otherwise(pl.col(c))
            .alias(c)
            for c in df.collect_schema().names()
            if c.startswith("heure_")
        ]
    )
    # to Time dtype (invalid times -> null)
    .with_columns(cs.starts_with("heure_").str.to_time(strict=False))
    # fallback for heure_fin_plage
    .with_columns(
        heure_fin_plage=pl.col("heure_fin_plage").fill_null(
            pl.col("heure_fin_appel")
        )
    )
    .drop(cs.contains("__h"))
)

# Date columns
"""
date_appel cannot be < date_debut_plage
date_debut_plage cannot be > date_fin plage
date_fin_plage cannot be < date_debut_plage

*date vars should be in date format*

⚠️ Null propagation:
If any of the 3 date vars are null, the when() condition goes directly to otherwise() and will input the value of 'date_debut_plage' that itself could be null.

"""

fix_dates: pl.Expr = (
    pl.when(
        (pl.col("date_appel") >= pl.col("date_debut_plage"))
        & (pl.col("date_appel") <= pl.col("date_fin_plage"))
        & (pl.col("date_debut_plage") <= pl.col("date_fin_plage"))
    )
    .then(pl.col("date_appel"))
    .otherwise(pl.col("date_debut_plage"))
    .alias("date_appel")
)

# Create a Datetime var
create_appel_datetime: pl.Expr = (
    pl.col("date_appel").cast(pl.Datetime)
    + pl.col("heure_debut_appel").cast(pl.Duration())
).alias("datetime_appel")


# Use the above expressions, apply the correct schema
df_clean_date_times = (
    df_clean_times
    # convert dates to date format
    .with_columns(cs.starts_with("date_").str.to_date(strict=False))
    # found years like 1010 (should be 2010)
    .with_columns(
        pl.when(cs.starts_with("date_").dt.year() < 2000)
        .then(cs.starts_with("date_").dt.offset_by("1000y"))
        .otherwise(cs.starts_with("date_"))
    )
    .with_columns(fix_dates)
    # apply expected dtypes
    .with_columns(
        # time vars already Time dtype
        pl.col("nom_poste").cast(pl.Categorical()),
        pl.col("duree_appel")
        .str.strptime(pl.Time, "%H:%M:%S")
        .cast(pl.Duration()),
    )
    .with_columns(create_appel_datetime)
)

# ------ Sink to parquet ------ #
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

if ANOM:
    df_clean = (
        df_clean_date_times.join(mapping, on="ecoutant", how="left")
        .drop("ecoutant")
        .rename({"ecoutant_anom": "ecoutant"})
    )
    df_clean.sink_parquet(PROCESSED_PATH / "ecoutants_2010_2026_anom.parquet")
else:
    df_clean.sink_parquet(PROCESSED_PATH / "ecoutants_2010_2026.parquet")
