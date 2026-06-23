# 🥛 Krishna Dairy — Sales Analyser

A full-stack data analysis tool for dairy product sales with festival tracking and trend forecasting.

## Quick Start

### 1. Install Python (3.9+) if not already installed

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Or simply run `start.sh` (Linux/Mac):
```bash
bash start.sh
```

### 4. Open browser
Go to: **http://127.0.0.1:8000**

---

## Features

| Chart | What it shows | Filters applied |
|-------|--------------|-----------------|
| **Chart 1** — Product Trend | Annual quantity per product (line graph) | Year, Festival, Product |
| **Chart 2** — Monthly Distribution | Month-wise sales pattern | Year, Festival, Product (month ignored) |
| **Chart 3** — Top 5 Products | Best-selling products in a month | Month, Year (overall — all days) |
| **Chart 4** — Festival vs Non-Festival | Sales split by festival days | Product, Year (month ignored) |
| **Chart 5** — Forecast Classification | Products classified as Stable / Seasonal / Festive / Rare | Full dataset only |

## Data Format

Your CSV/Excel file must have these columns:
- **Date** — any standard date format (e.g. 4/1/2019)
- **Product** — product name
- **Quantity** — numeric quantity sold
- **Festival** *(optional)* — festival name on that date, blank otherwise

---

## Project Structure
```
dairy_analyser/
├── backend/
│   └── main.py          # FastAPI backend
├── frontend/
│   └── index.html       # Interactive HTML frontend
├── requirements.txt
├── start.sh
└── README.md
```
