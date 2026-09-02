"""
ERP / FINANCE source system  —  depends on ORDERS + WMS + TMS.

Reads:  orders.csv, order_lines.csv, products.csv, shipments.csv
Writes: finance_ledger.csv   (one row per order)

This system is the "authoritative but weird" one. On PURPOSE it uses different
conventions from every other system, so joining finance to the rest of the
platform requires reconciliation — the single most realistic multi-source task.

Injected issues (see data/issues_finance.md):
    - systemic key mismatch: order_ref is the BARE number ('123'),
    while everyone else uses 'ORD-000123'. Naive join returns nothing.
    - systemic date drift: revenue_date is 'DD/MM/YYYY' text, not ISO.

Run standalone (after shipments):  python generate_finance.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ISSUES = []
def log(itype, table, rows, detect, note=""):
    ISSUES.append(dict(type=itype, table=table, rows=rows, detect=detect, note=note))


def main():
    print("[finance] reading orders + lines + shipments…")
    orders = pd.read_csv(DATA_DIR / "orders.csv", dtype={"order_id": str})
    order_lines = pd.read_csv(DATA_DIR / "order_lines.csv", dtype={"order_id": str, "sku": str})
    products = pd.read_csv(DATA_DIR / "products.csv", dtype={"sku": str})
    ship = pd.read_csv(DATA_DIR / "shipments.csv", dtype={"order_id": str})

    o = orders.drop_duplicates("order_id").copy()
    lines = order_lines.drop_duplicates(["order_id", "line_no"]).merge(
        products[["sku", "unit_cost_eur"]], on="sku", how="left")

    rev = lines.groupby("order_id")["line_total_eur"].sum().round(2)
    lines["c"] = lines["unit_cost_eur"] * lines["quantity_ordered"]
    cogs = lines.groupby("order_id")["c"].sum().round(2)
    freight = ship.drop_duplicates("order_id").set_index("order_id")["freight_cost_eur"]

    fin = o[["order_id", "order_date"]].copy()
    fin["recognized_revenue_eur"] = fin["order_id"].map(rev)
    fin["cogs_eur"] = fin["order_id"].map(cogs)
    fin["freight_cost_eur"] = fin["order_id"].map(freight)

    # SYSTEMIC ISSUE 1: bare-number key (strip the 'ORD-' prefix, drop leading zeros)
    fin["order_ref"] = fin["order_id"].str.split("-").str[1].astype(int).astype(str)
    # SYSTEMIC ISSUE 2: DD/MM/YYYY text dates
    fin["revenue_date"] = pd.to_datetime(fin["order_date"]).dt.strftime("%d/%m/%Y")

    fin = fin[["order_ref", "revenue_date", "recognized_revenue_eur",
        "cogs_eur", "freight_cost_eur"]]
    log("systemic key-format mismatch", "finance_ledger", len(fin),
        "finance_ledger.order_ref='123'; orders.order_id='ORD-000123'. "
        "Normalise before any join (strip prefix / cast).",
        "Affects EVERY join from finance to the platform.")
    log("systemic date-format drift", "finance_ledger", len(fin),
        "revenue_date is 'DD/MM/YYYY' text; everyone else uses ISO 'YYYY-MM-DD'.")

    fin.to_csv(DATA_DIR / "finance_ledger.csv", index=False)

    lines_md = ["# Injected issues — finance\n"]
    for it in ISSUES:
        lines_md.append(f"\n## {it['type']} — `{it['table']}` ({it['rows']} rows)\n"
                        f"- detect: {it['detect']}\n"
                        + (f"- note: {it['note']}\n" if it['note'] else ""))
    (DATA_DIR / "issues_finance.md").write_text("".join(lines_md))
    print(f"[finance] done: {len(fin):,} ledger rows")


if __name__ == "__main__":
    main()