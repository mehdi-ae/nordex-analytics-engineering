"""
ORDER MANAGEMENT source system  —  depends on MASTER DATA.

Reads:  products.csv, customers.csv   (join keys typed explicitly on read)
Writes: orders.csv, order_lines.csv

The order system only knows an order was PLACED. Delivery status is the TMS's
job, so orders.status = 'PLACED' (clean separation of concerns).

Injected issues (see data/issues_order_management.md):
    - referential gap: ~60 order_lines pointing at SKUs not in the catalogue
    - duplicate records: ~40 whole orders (and their lines) double-sent
    - business rule: ~15 order_lines with non-positive unit_price

Run standalone (after master_data):  python generate_orders.py
"""
from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

ORDERS_PER_DAY = 6000
MONTH_START = date(2025, 6, 1)
DAYS = 30
CAL = [MONTH_START + timedelta(days=i) for i in range(DAYS)]

ISSUES = []
def log(itype, table, rows, detect, note=""):
    ISSUES.append(dict(type=itype, table=table, rows=rows, detect=detect, note=note))


def main():
    print("[orders] reading master data…")
    # explicit dtypes ONLY on the join keys, to stop CSV type-guessing from
    # silently breaking the coherence link to master data.
    products = pd.read_csv(DATA_DIR / "products.csv", dtype={"sku": str})
    customers = pd.read_csv(DATA_DIR / "customers.csv",
                            dtype={"customer_id": str, "region": str})

    # ---- daily order counts with weekday seasonality ----
    counts = [int(ORDERS_PER_DAY * (0.75 if d.weekday() >= 5 else 1.05)
                  * rng.uniform(0.9, 1.1)) for d in CAL]
    total = sum(counts)

    order_id = np.array([f"ORD-{n:06d}" for n in range(1, total + 1)])
    order_day = np.repeat([d.isoformat() for d in CAL], counts)
    secs = rng.integers(8 * 3600, 23 * 3600, size=total)
    order_ts = pd.to_datetime(order_day) + pd.to_timedelta(secs, unit="s")

    cust = customers["customer_id"].to_numpy()
    creg = customers["region"].to_numpy()
    ci = rng.integers(0, len(cust), size=total)

    orders = pd.DataFrame({
        "order_id": order_id,
        "customer_id": cust[ci],
        "order_ts": order_ts,
        "order_date": order_day,
        "ship_to_region": creg[ci],      # null region propagates as null here (on purpose)
        "status": "PLACED",
    })

    # ---- order lines: 1-4 per order ----
    n_lines = rng.integers(1, 5, size=total)
    line_oid = np.repeat(order_id, n_lines)
    tl = len(line_oid)
    line_no = np.concatenate([np.arange(1, n + 1) for n in n_lines])

    sku = products["sku"].to_numpy()
    price = products["list_price_eur"].to_numpy()
    si = rng.integers(0, len(sku), size=tl)
    qty = rng.integers(1, 5, size=tl)
    disc = rng.choice([1.0, 1.0, 1.0, 0.9, 0.85], size=tl)
    unit_price = np.round(price[si] * disc, 2)

    order_lines = pd.DataFrame({
        "order_id": line_oid, "line_no": line_no, "sku": sku[si],
        "quantity_ordered": qty, "unit_price_eur": unit_price,
        "line_total_eur": np.round(qty * unit_price, 2),
    })

    # ---------- INJECTED ISSUES ----------
    # 1. referential gap: orphan SKUs
    n = 60
    idx = rng.choice(order_lines.index, size=n, replace=False)
    order_lines.loc[idx, "sku"] = [f"SKU-DELETED-{i}" for i in range(n)]
    log("referential gap (orphan FK)", "order_lines", n,
        "LEFT JOIN order_lines to products ON sku WHERE products.sku IS NULL",
        "SKU removed from catalogue but still referenced.")

    # 2. non-positive prices (line_total keeps its earlier positive value, so
    #    unit_price*qty != line_total for these — a second, subtler symptom).
    p = rng.choice(order_lines.index, size=15, replace=False)
    order_lines.loc[p, "unit_price_eur"] = rng.choice([0.0, -1.0, -9.99], size=15)
    log("business-rule violation", "order_lines", 15,
        "unit_price_eur <= 0  (and unit_price*quantity != line_total for these)",
        "Bad promo feed. Note line_total was computed before the corruption.")

    # 3. duplicate records: double-send whole orders + their lines
    dup = orders.sample(40, random_state=SEED)
    orders = pd.concat([orders, dup], ignore_index=True)
    dup_lines = order_lines[order_lines["order_id"].isin(dup["order_id"])]
    order_lines = pd.concat([order_lines, dup_lines], ignore_index=True)
    log("duplicate records (source retry)", "orders / order_lines", 40,
        "order_id appears >1 time (GROUP BY order_id HAVING COUNT(*)>1)",
        "Downstream systems key on order_id, so this stays contained here — "
        "but YOUR bronze layer must dedupe it.")

    orders.to_csv(DATA_DIR / "orders.csv", index=False)
    order_lines.to_csv(DATA_DIR / "order_lines.csv", index=False)

    lines = ["# Injected issues — order_management\n"]
    for it in ISSUES:
        lines.append(f"\n## {it['type']} — `{it['table']}` ({it['rows']} rows)\n"
            f"- detect: {it['detect']}\n"
            + (f"- note: {it['note']}\n" if it['note'] else ""))
    (DATA_DIR / "issues_order_management.md").write_text("".join(lines))
    print(f"[orders] done: {len(orders):,} orders, {len(order_lines):,} lines")


if __name__ == "__main__":
    main()