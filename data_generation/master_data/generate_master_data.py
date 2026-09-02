"""
MASTER DATA source system  —  depends on NOTHING.

Produces the reference "nouns" every other system points at:
    products.csv, sites.csv, carriers.csv, customers.csv

Injected issues (see data/issues_master_data.md):
    - unit drift: ~4% of product weights recorded in KG, not grams (silent)
    - missing values: ~3% of customers with null region or null signup_date

Run standalone:  python generate_master_data.py
"""
from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

# data/ lives one level up from this system folder (…/data_generation/data)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

N_PRODUCTS = 1500
N_CUSTOMERS = 40000
MONTH_START = date(2025, 6, 1)

ISSUES: list[dict] = []
def log(itype, table, rows, detect, note=""):
    ISSUES.append(dict(type=itype, table=table, rows=rows, detect=detect, note=note))

REGIONS = ["Ile-de-France", "Hauts-de-France", "Grand-Est", "Normandie",
    "Bretagne", "Nouvelle-Aquitaine", "Occitanie", "Auvergne-Rhone-Alpes"]
SITES = [
    ("DC1", "Orleans",  "Centre-Val-de-Loire"),
    ("DC2", "Lille",    "Hauts-de-France"),
    ("DC3", "Lyon",     "Auvergne-Rhone-Alpes"),
    ("DC4", "Bordeaux", "Nouvelle-Aquitaine"),
]
CARRIERS = ["Chronopost", "Colissimo", "DPD", "GLS", "MondialRelay"]
CATEGORIES = {   # category: (weight_grams range, unit_cost range)
    "Electronics": ((200, 4000), (30, 400)),  "Home":    ((500, 8000), (10, 150)),
    "Apparel":     ((150, 1200), (5, 60)),    "Beauty":  ((50, 600),   (3, 40)),
    "Sports":      ((300, 6000), (15, 200)),  "Toys":    ((100, 2500), (8, 80)),
    "Books":       ((200, 1500), (4, 25)),    "Grocery": ((250, 5000), (2, 30)),
}


def products():
    cats = rng.choice(list(CATEGORIES), size=N_PRODUCTS)
    weights, costs = [], []
    for c in cats:
        (wlo, whi), (clo, chi) = CATEGORIES[c]
        weights.append(float(rng.integers(wlo, whi)))
        costs.append(round(float(rng.uniform(clo, chi)), 2))
    costs = np.array(costs)
    price = np.round(costs * rng.uniform(1.3, 2.6, size=N_PRODUCTS), 2)
    df = pd.DataFrame({
        "sku": [f"SKU-{i:05d}" for i in range(1, N_PRODUCTS + 1)],
        "product_name": [f"{c} item {i}" for i, c in enumerate(cats, 1)],
        "category": cats, "weight_grams": weights,
        "unit_cost_eur": costs, "list_price_eur": price,
    })
    # ISSUE: unit drift — some weights in kg not grams
    u = rng.choice(df.index, size=int(N_PRODUCTS * 0.04), replace=False)
    df.loc[u, "weight_grams"] = (df.loc[u, "weight_grams"] / 1000).round(2)
    log("unit drift (silent)", "products", len(u),
        "weight_grams has a cluster of tiny values (<20); real weights are 50-8000. "
        "Detect via distribution/outlier check, not a hard rule.",
        "The kind you miss first time. Propagates into shipment weight & freight.")
    return df


def sites():
    return pd.DataFrame(
        [(s[0], s[1], s[2], int(rng.integers(50_000, 200_000))) for s in SITES],
        columns=["site_id", "city", "region", "storage_capacity_units"])


def carriers():
    return pd.DataFrame({
        "carrier_id": [f"C{i}" for i in range(1, len(CARRIERS) + 1)],
        "carrier_name": CARRIERS,
        "service_level": ["EXPRESS", "STANDARD", "STANDARD", "STANDARD", "ECONOMY"]})


def customers():
    w = np.array([5, 3, 2, 1.5, 1.5, 2.5, 2, 3], dtype=float)
    region = rng.choice(REGIONS, size=N_CUSTOMERS, p=w / w.sum())
    signup = [(MONTH_START - timedelta(days=int(rng.integers(30, 1200)))).isoformat()
    for _ in range(N_CUSTOMERS)]
    df = pd.DataFrame({
        "customer_id": [f"CUST-{i:06d}" for i in range(1, N_CUSTOMERS + 1)],
        "region": region, "signup_date": signup})
    # ISSUE: missing values in a nullable dimension field
    m = rng.choice(df.index, size=int(N_CUSTOMERS * 0.03), replace=False)
    df.loc[m[:len(m)//2], "region"] = None
    df.loc[m[len(m)//2:], "signup_date"] = None
    log("missing values (nullable dim)", "customers", len(m),
        "region IS NULL OR signup_date IS NULL",
        "Propagates: null region -> null ship_to_region -> site fallback.")
    return df


def write_issues():
    lines = [f"# Injected issues — master_data\n"]
    for it in ISSUES:
        lines.append(f"\n## {it['type']} — `{it['table']}` ({it['rows']} rows)\n"
            f"- detect: {it['detect']}\n"
            + (f"- note: {it['note']}\n" if it['note'] else ""))
    (DATA_DIR / "issues_master_data.md").write_text("".join(lines))


def main():
    print("[master_data] generating…")
    products().to_csv(DATA_DIR / "products.csv", index=False)
    sites().to_csv(DATA_DIR / "sites.csv", index=False)
    carriers().to_csv(DATA_DIR / "carriers.csv", index=False)
    customers().to_csv(DATA_DIR / "customers.csv", index=False)
    write_issues()
    print(f"[master_data] done -> {DATA_DIR}")


if __name__ == "__main__":
    main()