#!/bin/sh
set -e

uv run src/sos_extract_data/stats_module/1_extract_statsmodule.py
echo "1_extract_statsmodule.py DONE ✅"

uv run src/sos_extract_data/stats_module/2_convert_fake_xls_to_parquet.py
echo "2_convert_fake_xls_to_parquet.py DONE ✅"

uv run src/sos_extract_data/stats_module/3_prep_stats_module_data.py
echo "3_prep_stats_module_data.py DONE ✅"
