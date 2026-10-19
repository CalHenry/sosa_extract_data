"""
Convert .xls (actually HTML-in-disguise) call-data exports into a single deduplicated parquet file.

Pipeline:
1. Read each .xls file with pandas.read_html() (they're HTML files with a
   .xls extension, not real Excel files). The 3rd table (index 2) on the
   page is the actual data table: rows 0-9 are title/summary info, row 10
   is the header, data starts at row 11 - pandas' `header=[0]` handles
   that once we've selected the right table.
2. Convert each resulting pandas DataFrame to polars and write it as its
   own .parquet file.
3. A couple of files reliably fail to parse via read_html (unknown
   XPathEvalError). Workaround: open those in Excel and re-save as .csv;
   this script picks up any .csv files sitting in CSV_DIR and parses them
   with polars directly (semicolon-separated, header on line 11).
4. Once every source file has a matching .parquet, scan them all, drop
   any duplicate rows, and sink the result to one combined parquet file.

Re-running the script is safe: steps 1 and 2 skip any file whose stem
already has a matching .parquet in OUTPUT_DIR.

This script is a marimo notebook (that does the exact same thing) converted to a python script by an LLM.
The text above is a rewrite of the comments in the notebook.
"""

from pathlib import Path

import pandas as pd
import polars as pl

# --- Paths -------------------------------------------------------------
SOURCE_DIR = Path("data/stats_module/extracted/")
OUTPUT_DIR = Path("data/stats_module/raw/extraction_parquet/")
RAW_DIR = Path("data/stats_module/raw/")
MERGED_FILENAME = "ecoutants_2010_2026.parquet"


def convert_xls_files(source_dir: Path, output_dir: Path) -> list[str]:
    """Convert HTML-disguised-as-.xls files to parquet via pandas.read_html().

    Returns the list of filenames that failed to convert.
    """
    existing_files = {f.stem for f in output_dir.glob("*.parquet")}
    failed_files: list[str] = []

    for file in source_dir.glob("*.xls"):
        if file.stem in existing_files:
            continue

        try:
            pdf = pd.read_html(file, header=[0])[2]
            pl.from_pandas(pdf).write_parquet(output_dir / f"{file.stem}.parquet")
            print(f"OK: {file.name}")
        except Exception as e:
            print(f"FAILED: {file.name} -> {e}")
            failed_files.append(file.name)

    if failed_files:
        print(f"FAIL: {failed_files}")

    return failed_files


def convert_csv_files(source_dir: Path, output_dir: Path) -> None:
    """Convert manually re-saved .csv files (the ones read_html couldn't
    parse) to parquet using polars directly."""
    existing_files = {f.stem for f in output_dir.glob("*.parquet")}

    for csv_file in source_dir.glob("*.csv"):
        if csv_file.stem in existing_files:
            continue

        try:
            data = pl.read_csv(
                csv_file,
                separator=";",
                skip_lines=10,
            )
            data.write_parquet(output_dir / f"{csv_file.stem}.parquet")
            print(f"OK: {csv_file.name}")
        except Exception as e:
            print(f"FAILED: {csv_file.name} -> {e}")


def merge_parquets(output_dir: Path, raw_dir: Path, merged_filename: str) -> None:
    """Scan all per-file parquets, drop duplicate rows, and sink the
    combined result to a single parquet file."""
    df = pl.scan_parquet(
        output_dir / "*parquet",
        cast_options=pl.ScanCastOptions(integer_cast="allow-float"),
    ).collect()

    df.unique(maintain_order=True).lazy().sink_parquet(raw_dir / merged_filename)
    print(f"Merged {df.height} rows -> {raw_dir / merged_filename}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    convert_xls_files(SOURCE_DIR, OUTPUT_DIR)
    convert_csv_files(SOURCE_DIR, OUTPUT_DIR)
    merge_parquets(OUTPUT_DIR, RAW_DIR, MERGED_FILENAME)


if __name__ == "__main__":
    main()
