from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

DB = Path(__file__).parent / "data" / "complaints.duckdb"
st.set_page_config(page_title="Bank Complaint Intelligence", layout="wide")
st.title("Bank Complaint Operations Intelligence")
if not DB.exists():
    st.error("Run `python -m src.pipeline` first.")
    st.stop()

with duckdb.connect(str(DB), read_only=True) as con:
    products = [r[0] for r in con.execute("SELECT DISTINCT product FROM complaints ORDER BY 1").fetchall()]
    selected = st.multiselect("Products", products, default=products)
    con.register("selected_products", __import__("pandas").DataFrame({"product": selected}))
    overview = con.execute("""
        SELECT count(*) complaints, round(100*avg(timely_flag),2) timely,
               round(100*avg(disputed_flag),2) disputed, count(DISTINCT company) companies
        FROM complaints WHERE product IN (SELECT product FROM selected_products)
    """).fetchone()
    monthly = con.execute("""
        SELECT date_trunc('month', date_received) AS month_key, count(*) AS complaints
        FROM complaints WHERE product IN (SELECT product FROM selected_products)
        GROUP BY 1 ORDER BY 1
    """).df()
    issues = con.execute("""
        SELECT issue, count(*) complaints FROM complaints
        WHERE product IN (SELECT product FROM selected_products)
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """).df()
    companies = con.execute("SELECT * FROM company_scorecard LIMIT 15").df()

for col, label, value in zip(st.columns(4), ["Complaints", "Timely response", "Disputed", "Companies"], [overview[0], f"{overview[1]}%", f"{overview[2]}%", overview[3]]):
    col.metric(label, value)
left, right = st.columns(2)
left.plotly_chart(px.line(monthly, x="month_key", y="complaints", title="Monthly complaint volume"), width="stretch")
right.plotly_chart(px.bar(issues, x="complaints", y="issue", orientation="h", title="Top root causes"), width="stretch")
st.subheader("Company operations scorecard")
st.dataframe(companies, width="stretch", hide_index=True)
