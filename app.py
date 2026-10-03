from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

DB = Path(__file__).parent / "data" / "complaints.duckdb"
app = FastAPI(title="Bank Complaint Intelligence")


def query(sql: str, parameters: list[str] | None = None) -> list[dict]:
    if not DB.exists():
        raise HTTPException(503, "Run python -m src.pipeline first")
    with duckdb.connect(str(DB), read_only=True) as con:
        cursor = con.execute(sql, parameters or [])
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD


@app.get("/api/products")
def products() -> list[str]:
    return [row["product"] for row in query("SELECT DISTINCT product FROM complaints ORDER BY 1")]


@app.get("/api/dashboard")
def dashboard_data(product: str | None = Query(default=None)) -> dict:
    where, params = ("WHERE product = ?", [product]) if product else ("", [])
    overview = query(f"""SELECT count(*) complaints, round(100*avg(timely_flag),2) timely,
        round(100*avg(disputed_flag),2) disputed, count(DISTINCT company) companies
        FROM complaints {where}""", params)[0]
    monthly = query(f"""SELECT strftime(date_trunc('month', date_received), '%Y-%m') AS month_key,
        count(*) complaints FROM complaints {where} GROUP BY 1 ORDER BY 1""", params)
    issues = query(f"""SELECT issue, count(*) complaints FROM complaints {where}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 8""", params)
    companies = query("SELECT * FROM company_scorecard ORDER BY complaints DESC LIMIT 10")
    return {"overview": overview, "monthly": monthly, "issues": issues, "companies": companies}


DASHBOARD = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Bank Complaint Intelligence</title><style>
:root{--navy:#13243a;--blue:#1976d2;--ink:#1f2937}*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:var(--ink);font:15px system-ui}header{background:linear-gradient(120deg,var(--navy),#245a8d);color:white;padding:34px max(5vw,24px)}h1{margin:0 0 8px;font-size:30px}.sub{opacity:.82}.wrap{max-width:1200px;margin:auto;padding:24px}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}select{padding:10px 14px;border:1px solid #ccd7e4;border-radius:8px;background:white}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.panel{background:white;border-radius:14px;padding:20px;box-shadow:0 4px 18px #19324d12}.value{font-size:28px;font-weight:750;color:var(--navy)}.label{font-size:13px;color:#667085}.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:18px;margin-top:18px}.bars{display:flex;align-items:end;height:210px;gap:5px;padding-top:18px}.bar{background:var(--blue);flex:1;min-width:4px;border-radius:4px 4px 0 0}.issue{display:grid;grid-template-columns:1fr 3fr 45px;gap:8px;align-items:center;margin:12px 0}.track{height:10px;background:#e8eef5;border-radius:8px}.fill{height:100%;background:#ee7d45;border-radius:8px}table{width:100%;border-collapse:collapse;margin-top:12px}th,td{text-align:left;padding:10px;border-bottom:1px solid #edf0f4}th{color:#667085;font-size:12px}@media(max-width:800px){.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}
</style></head><body><header><h1>Complaint Operations Intelligence</h1><div class="sub">Where customers struggle, how quickly companies respond, and where attention is needed.</div></header><main class="wrap"><div class="toolbar"><b>Operations overview</b><select id="product"><option value="">All products</option></select></div><section class="cards" id="cards"></section><section class="grid"><div class="panel"><b>Complaint volume by month</b><div class="bars" id="monthly"></div></div><div class="panel"><b>Top customer problems</b><div id="issues"></div></div></section><section class="panel" style="margin-top:18px"><b>Company response scorecard</b><table><thead><tr><th>Company</th><th>Complaints</th><th>Timely responses</th><th>Disputed</th></tr></thead><tbody id="companies"></tbody></table></section></main><script>
const fmt=n=>Number(n).toLocaleString();async function load(){let p=document.querySelector('#product').value;let d=await fetch('/api/dashboard'+(p?'?product='+encodeURIComponent(p):'')).then(r=>r.json()),o=d.overview;let cs=[['Complaints',fmt(o.complaints)],['Timely responses',o.timely+'%'],['Disputed',o.disputed+'%'],['Companies',fmt(o.companies)]];document.querySelector('#cards').innerHTML=cs.map(x=>`<div class="card"><div class="value">${x[1]}</div><div class="label">${x[0]}</div></div>`).join('');let max=Math.max(...d.monthly.map(x=>x.complaints));document.querySelector('#monthly').innerHTML=d.monthly.map(x=>`<div class="bar" title="${x.month_key}: ${x.complaints}" style="height:${Math.max(3,x.complaints/max*100)}%"></div>`).join('');max=Math.max(...d.issues.map(x=>x.complaints));document.querySelector('#issues').innerHTML=d.issues.map(x=>`<div class="issue"><span>${x.issue}</span><div class="track"><div class="fill" style="width:${x.complaints/max*100}%"></div></div><b>${x.complaints}</b></div>`).join('');document.querySelector('#companies').innerHTML=d.companies.map(x=>`<tr><td>${x.company}</td><td>${fmt(x.complaints)}</td><td>${x.timely_response_pct}%</td><td>${x.disputed_pct}%</td></tr>`).join('')}
fetch('/api/products').then(r=>r.json()).then(ps=>{document.querySelector('#product').innerHTML+=ps.map(p=>`<option>${p}</option>`).join('');load()});document.querySelector('#product').onchange=load;</script></body></html>'''
