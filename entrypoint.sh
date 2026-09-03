#!/usr/bin/env bash
set -euo pipefail

echo "=== [1/3] Extract + Load ==="
python extract_load/run_extract_load.py

echo "=== [2/3] dbt run (raw -> curated star schema) ==="
dbt run --profiles-dir .

echo "=== [3/3] dbt test (data quality checks on curated layer) ==="
dbt test --profiles-dir .

echo "=== Pipeline complete ==="
