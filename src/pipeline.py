from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import requests

CFPB_API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
REQUIRED = {
    "complaint_id", "date_received", "product", "issue", "company",
    "state", "submitted_via", "timely_response", "company_response",
}


def generate_demo(path: Path, rows: int = 15000, seed: int = 42) -> Path:
    rng = np.random.default_rng(seed)
    products = ["Credit card", "Checking account", "Mortgage", "Consumer loan", "Debt collection"]
    issues = ["Incorrect information", "Unexpected fees", "Account access", "Payment processing", "Communication"]
    companies = ["North Bank", "Metro Credit", "Horizon Finance", "Union Lending", "Capital Trust"]
    states = ["CA", "TX", "FL", "NY", "IL", "GA", "NJ", "NC"]
    submitted = ["Web", "Phone", "Referral", "Postal mail"]
    dates = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, rows), unit="D")
    product = rng.choice(products, rows, p=[.27, .22, .18, .13, .20])
    risk = np.where(product == "Debt collection", .16, .08)
    timely = rng.random(rows) > risk
    disputed = rng.random(rows) < np.where(timely, .10, .33)
    df = pd.DataFrame({
        "complaint_id": np.arange(1, rows + 1),
        "date_received": dates,
        "product": product,
        "issue": rng.choice(issues, rows),
        "company": rng.choice(companies, rows),
        "state": rng.choice(states, rows),
        "submitted_via": rng.choice(submitted, rows, p=[.66, .16, .11, .07]),
        "timely_response": np.where(timely, "Yes", "No"),
        "company_response": np.where(timely, "Closed with explanation", "In progress"),
        "consumer_disputed": np.where(disputed, "Yes", "No"),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def download_cfpb(destination: Path, rows: int = 10000) -> Path:
    """Download a review-friendly sample from the official CFPB API."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(CFPB_API, params={"field": "all", "size": min(rows, 10000)}, timeout=120)
    response.raise_for_status()
    records = [hit["_source"] for hit in response.json()["hits"]["hits"]]
    pd.DataFrame(records).to_csv(destination, index=False)
    return destination


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [c.strip().lower().replace(" ", "_").replace("?", "") for c in out.columns]
    aliases = {
        "date_received": "date_received", "complaint_id": "complaint_id",
        "submitted_via": "submitted_via", "timely_response": "timely_response",
        "timely": "timely_response",
        "company_response_to_consumer": "company_response",
        "consumer_disputed": "consumer_disputed",
    }
    out = out.rename(columns=aliases)
    if "consumer_disputed" not in out:
        out["consumer_disputed"] = "Not available"
    return out


def validate(df: pd.DataFrame) -> dict[str, float | int]:
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    duplicate_ids = int(df["complaint_id"].duplicated().sum())
    null_critical = int(df[["complaint_id", "date_received", "product", "company"]].isna().sum().sum())
    if duplicate_ids or null_critical:
        raise ValueError(f"Quality failure: duplicates={duplicate_ids}, critical_nulls={null_critical}")
    return {"rows": len(df), "duplicate_ids": duplicate_ids, "critical_nulls": null_critical}


def build_mart(csv_path: Path, db_path: Path) -> dict[str, float | int]:
    df = normalize_columns(pd.read_csv(csv_path, low_memory=False))
    quality = validate(df)
    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")
    df["timely_flag"] = df["timely_response"].astype(str).str.lower().eq("yes").astype(int)
    df["disputed_flag"] = df["consumer_disputed"].astype(str).str.lower().eq("yes").astype(int)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.register("complaints_df", df)
        con.execute("CREATE OR REPLACE TABLE complaints AS SELECT * FROM complaints_df")
        con.execute("""
            CREATE OR REPLACE TABLE monthly_kpis AS
            SELECT date_trunc('month', date_received) AS month, product,
                   count(*) AS complaints,
                   round(100 * avg(timely_flag), 2) AS timely_response_pct,
                   round(100 * avg(disputed_flag), 2) AS disputed_pct
            FROM complaints GROUP BY 1, 2
        """)
        con.execute("""
            CREATE OR REPLACE TABLE company_scorecard AS
            SELECT company, count(*) AS complaints,
                   round(100 * avg(timely_flag), 2) AS timely_response_pct,
                   round(100 * avg(disputed_flag), 2) AS disputed_pct
            FROM complaints GROUP BY 1 ORDER BY complaints DESC
        """)
    quality["timely_response_pct"] = round(100 * float(df["timely_flag"].mean()), 2)
    return quality


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="download the large official CFPB extract")
    parser.add_argument("--rows", type=int, default=15000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data" / ("cfpb_complaints.csv" if args.real else "demo_complaints.csv")
    if not csv_path.exists():
        download_cfpb(csv_path, args.rows) if args.real else generate_demo(csv_path, args.rows)
    print(build_mart(csv_path, root / "data" / "complaints.duckdb"))


if __name__ == "__main__":
    main()
