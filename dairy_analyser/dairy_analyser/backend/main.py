from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
import io
import json
from typing import Optional, List
import os

app = FastAPI(title="Dairy Sales Analyser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
store = {"df": None}

def parse_upload(content: bytes, filename: str) -> pd.DataFrame:
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))
    df.columns = [c.strip() for c in df.columns]
    # Normalize column names
    rename = {}
    for c in df.columns:
        cl = c.lower()
        if "date" in cl: rename[c] = "Date"
        elif "product" in cl: rename[c] = "Product"
        elif "quantity" in cl or "qty" in cl: rename[c] = "Quantity"
        elif "festival" in cl: rename[c] = "Festival"
    df.rename(columns=rename, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=False, errors="coerce")
    df.dropna(subset=["Date"], inplace=True)
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["MonthName"] = df["Date"].dt.strftime("%B")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    if "Festival" not in df.columns:
        df["Festival"] = ""
    df["Festival"] = df["Festival"].fillna("").astype(str).str.strip()
    df["IsFestival"] = df["Festival"].ne("")
    return df


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        df = parse_upload(content, file.filename)
    except Exception as e:
        raise HTTPException(400, f"Parse error: {e}")
    store["df"] = df
    years = sorted(df["Year"].unique().tolist())
    months = [
        {"num": int(m), "name": pd.Timestamp(2000, int(m), 1).strftime("%B")}
        for m in sorted(df["Month"].unique())
    ]
    products = sorted(df["Product"].unique().tolist())
    festivals = sorted([f for f in df["Festival"].unique() if f])
    return {
        "rows": len(df),
        "years": years,
        "months": months,
        "products": products,
        "festivals": festivals,
    }


def get_df():
    if store["df"] is None:
        raise HTTPException(400, "No data uploaded yet")
    return store["df"]


# ── Chart 1: Product trend over years (line chart) ──────────────────────────
@app.get("/chart/trend")
def chart_trend(products: str):
    df = get_df()
    selected = [p.strip() for p in products.split("||") if p.strip()]
    sub = df[df["Product"].isin(selected)]
    result = {}
    for prod in selected:
        grp = sub[sub["Product"] == prod].groupby("Year")["Quantity"].sum().reset_index()
        result[prod] = {"years": grp["Year"].tolist(), "quantities": grp["Quantity"].tolist()}
    return result

# ── Chart 2: Monthly comparison (ignores month filter) ──────────────────────
@app.get("/chart/monthly")
def chart_monthly(
    products: str,
    year: Optional[int] = None,
    festival: Optional[str] = None,
):
    df = get_df()
    selected = [p.strip() for p in products.split("||") if p.strip()]
    sub = df[df["Product"].isin(selected)]
    # Only apply year and festival filters — NOT month
    if year:
        sub = sub[sub["Year"] == year]
    if festival:
        sub = sub[sub["Festival"] == festival]
    result = {}
    month_order = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"]
    for prod in selected:
        grp = sub[sub["Product"] == prod].groupby("MonthName")["Quantity"].sum().reindex(month_order).fillna(0)
        result[prod] = {"months": month_order, "quantities": grp.tolist()}
    return result


# ── Chart 3: Top 5 products in selected month ────────────────────────────────
@app.get("/chart/top5")
def chart_top5(month: int, year: Optional[int] = None):
    df = get_df()
    sub = df[df["Month"] == month]
    if year:
        sub = sub[sub["Year"] == year]
    grp = sub.groupby("Product")["Quantity"].sum().nlargest(5).reset_index()
    return {"products": grp["Product"].tolist(), "quantities": grp["Quantity"].tolist()}


# ── Chart 4: Festival vs non-festival sales for product ──────────────────────
@app.get("/chart/festival")
def chart_festival(product: str, year: Optional[int] = None, month: Optional[int] = None):
    df = get_df()
    sub = df[df["Product"] == product]
    if year:
        sub = sub[sub["Year"] == year]
    if month:
        sub = sub[sub["Month"] == month]

    non_fest_avg = sub[~sub["IsFestival"]]["Quantity"].mean()
    non_fest_avg = round(float(non_fest_avg), 2) if not pd.isna(non_fest_avg) else 0

    by_fest = sub[sub["IsFestival"]].groupby("Festival")["Quantity"].mean().reset_index()
    by_fest["Quantity"] = by_fest["Quantity"].round(2)

    return {
        "non_festival_avg": non_fest_avg,
        "by_festival": {
            "names": by_fest["Festival"].tolist(),
            "quantities": by_fest["Quantity"].tolist(),
        },
    }


# ── Chart 5: Forecast / Category classification ──────────────────────────────
@app.get("/chart/forecast")
def chart_forecast():
    df = get_df()

    results = []
    for product, grp in df.groupby("Product"):
        monthly = grp.groupby(["Year","Month"])["Quantity"].sum().reset_index()
        total = monthly["Quantity"].sum()
        if total == 0:
            results.append({"product": product, "category": "Rare", "avg": 0, "total": 0})
            continue

        # Monthly CV (coefficient of variation) — measures seasonality
        monthly_avg = monthly.groupby("Month")["Quantity"].mean()
        mean_val = monthly_avg.mean()
        std_val = monthly_avg.std()
        if pd.isna(mean_val) or mean_val == 0 or pd.isna(std_val):
            cv = 0.0
        else:
            cv = float(std_val / mean_val)

        # Festival ratio
        fest_qty = grp[grp["IsFestival"]]["Quantity"].sum()
        fest_ratio = fest_qty / total if total > 0 else 0

        # Yearly presence
        years_present = grp["Year"].nunique()
        total_years = df["Year"].nunique()
        presence = years_present / total_years

        avg_monthly = total / max(len(monthly), 1)

        if presence < 0.4 or avg_monthly < 50:
            category = "Rare"
        elif fest_ratio > 0.3:
            category = "Festive Demand"
        elif cv > 0.4:
            category = "Seasonal"
        else:
            category = "Stable"

        results.append({
            "product": product,
            "category": category,
            "avg_monthly": round(float(avg_monthly) if not pd.isna(avg_monthly) else 0, 1),
            "total": round(float(total) if not pd.isna(total) else 0, 1),
            "fest_ratio": round(float(fest_ratio) if not pd.isna(fest_ratio) else 0, 3),
            "cv": round(float(cv) if not pd.isna(cv) else 0, 3),
            })
    # Sort: Stable → Seasonal → Festive Demand → Rare
    order = {"Stable": 0, "Seasonal": 1, "Festive Demand": 2, "Rare": 3}
    results.sort(key=lambda x: (order.get(x["category"], 9), -x["total"]))
    return results


# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",  port=8000, reload=True)
