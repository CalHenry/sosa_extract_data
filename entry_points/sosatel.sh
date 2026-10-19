#!/bin/sh
set -e

uv run src/sos_extract_data/sosatel/1_extract_sosatel.py
echo "1_extract_sosatel.py DONE ✅"

uv run src/sos_extract_data/sosatel/2_aggregate_extracted_data.py
echo "2_aggregate_extracted_data.py DONE ✅"
