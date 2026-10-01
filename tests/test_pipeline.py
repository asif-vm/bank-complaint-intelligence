from pathlib import Path

import duckdb
from src.pipeline import build_mart, generate_demo


def test_pipeline(tmp_path: Path):
    csv_path = generate_demo(tmp_path / "demo.csv", rows=1000)
    db_path = tmp_path / "mart.duckdb"
    quality = build_mart(csv_path, db_path)
    assert quality["rows"] == 1000
    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM monthly_kpis").fetchone()[0] > 0

