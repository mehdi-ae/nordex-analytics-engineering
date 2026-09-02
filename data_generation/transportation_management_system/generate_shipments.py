"""
TRANSPORTATION MANAGEMENT source system  —  depends on MASTER DATA + ORDERS + WMS.

Reads:  orders.csv, order_lines.csv, products.csv, fulfillments.csv
Writes: shipments.csv   (one shipment per order)

The TMS owns delivery status. Shipments whose delivery would fall after the
month cutoff are legitimately IN_TRANSIT with a NULL actual_delivery_date — a
correct null, NOT a bug. Contrast with the injected DELIVERED+null bug below.

Injected issues (see data/issues_transportation.md):
    - null-semantics bug: ~30 DELIVERED shipments with null actual_delivery_date
    - business rule: ~25 shipments with ship_date before the order date
    - whitespace/casing: ~20% of carrier_name values inconsistently formatted

Run standalone (after warehouse):  python generate_shipments.py
"""
from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

MONTH_START = date(2025, 6, 1)
DAYS = 30
CUTOFF = MONTH_START + timedelta(days=DAYS - 1)
CARRIERS = ["Chronopost", "Colissimo", "DPD", "GLS", "MondialRelay"]
ISSUES = []
def log(itype, table, rows, detect, note=""):
    ISSUES.append(dict(type=itype, table=table, rows=rows, detect=detect, note=note))


def main():
    print("[transport] reading orders + warehouse + master…")
    orders = pd.read_csv(DATA_DIR / "orders.csv",
        dtype={"order_id": str, "ship_to_region": str})
    order_lines = pd.read_csv(DATA_DIR / "order_lines.csv", dtype={"order_id": str, "sku": str})
    products = pd.read_csv(DATA_DIR / "products.csv", dtype={"sku": str})
    ful = pd.read_csv(DATA_DIR / "fulfillments.csv", dtype={"order_id": str, "sku": str, "site_id": str})

    o = orders.drop_duplicates("order_id").copy()

    # weight per order from deduped, catalogue-only lines
    lines = (order_lines.drop_duplicates(["order_id", "line_no"])
        .merge(products[["sku", "weight_grams"]], on="sku", how="inner"))
    lines["w"] = lines["weight_grams"] * lines["quantity_ordered"]
    weight = lines.groupby("order_id")["w"].sum()

    # origin site + fulfilment date from the WMS
    site = ful.groupby("order_id")["site_id"].first()
    fdate = ful.groupby("order_id")["fulfillment_date"].max()

    o = (o.merge(weight.rename("weight_grams"), on="order_id", how="left")
        .merge(site.rename("origin_site"), on="order_id", how="left")
        .merge(fdate.rename("f_date"), on="order_id", how="left"))
    # orders with only orphan lines have no weight/fulfilment — drop from shipping
    o = o.dropna(subset=["f_date"]).reset_index(drop=True)

    n = len(o)
    ship_lag = rng.integers(0, 2, size=n)
    ship_date = pd.to_datetime(o["f_date"]) + pd.to_timedelta(ship_lag, unit="D")
    carrier = rng.choice(CARRIERS, size=n, p=np.array([2, 3, 2, 1.5, 1.5]) / 10)
    base = np.select([np.isin(carrier, ["Chronopost"]), np.isin(carrier, ["MondialRelay"])],
        [1, 4], default=2)
    promised = base + rng.integers(0, 3, size=n)
    promised_delivery = ship_date + pd.to_timedelta(promised, unit="D")
    noise = rng.choice([-1, 0, 0, 0, 1, 2, 3], size=n)
    actual = np.clip(promised + noise, 1, None)
    actual_delivery = ship_date + pd.to_timedelta(actual, unit="D")
    freight = np.round(2.5 + o["weight_grams"].fillna(500) / 1000 * 0.8 + promised * 0.4, 2)

    ship = pd.DataFrame({
        "shipment_id": [f"SHP-{i:07d}" for i in range(1, n + 1)],
        "order_id": o["order_id"].values,
        "origin_site": o["origin_site"].values,
        "dest_region": o["ship_to_region"].values,
        "carrier_name": carrier,
        "ship_date": ship_date.dt.date.astype(str).values,
        "promised_delivery_date": promised_delivery.dt.date.astype(str).values,
        "actual_delivery_date": actual_delivery.dt.date.astype(str).values,
        "weight_grams": o["weight_grams"].values,
        "freight_cost_eur": freight.values,
        "status": "DELIVERED",
    })

    # LEGITIMATE null: delivery after cutoff -> still in transit
    in_transit = pd.to_datetime(ship["actual_delivery_date"]).dt.date > CUTOFF
    ship.loc[in_transit, "status"] = "IN_TRANSIT"
    ship.loc[in_transit, "actual_delivery_date"] = None
    log("legitimate null (NOT a bug)", "shipments", int(in_transit.sum()),
        "status='IN_TRANSIT' AND actual_delivery_date IS NULL",
        "Correct. Do not 'fix'. Contrast with the DELIVERED+null bug below.")

    # ---------- INJECTED ISSUES ----------
    delivered = ship.index[ship["status"] == "DELIVERED"]
    bad = rng.choice(delivered, size=30, replace=False)
    ship.loc[bad, "actual_delivery_date"] = None
    log("null-semantics bug", "shipments", 30,
        "status='DELIVERED' AND actual_delivery_date IS NULL",
        "This IS a bug. Same null, opposite meaning to the in-transit nulls.")

    s = rng.choice(ship.index, size=25, replace=False)
    ship.loc[s, "ship_date"] = "2025-05-20"
    log("business-rule violation", "shipments", 25,
        "shipment.ship_date < order.order_date (join on order_id)",
        "Shipped before it was ordered — physically impossible.")

    c = rng.choice(ship.index, size=int(n * 0.2), replace=False)
    def messy(name):
        return rng.choice([f"{name} ", f" {name}", name.upper(), name.lower()])
    ship.loc[c, "carrier_name"] = [messy(x) for x in ship.loc[c, "carrier_name"]]
    log("whitespace/casing inconsistency", "shipments", len(c),
        "SELECT DISTINCT carrier_name shows 'Chronopost', 'chronopost ', ' CHRONOPOST'…",
        "TRIM + UPPER before grouping.")

    ship.to_csv(DATA_DIR / "shipments.csv", index=False)

    lines_md = ["# Injected issues — transportation\n"]
    for it in ISSUES:
        lines_md.append(f"\n## {it['type']} — `{it['table']}` ({it['rows']} rows)\n"
                        f"- detect: {it['detect']}\n"
                        + (f"- note: {it['note']}\n" if it['note'] else ""))
    (DATA_DIR / "issues_transportation.md").write_text("".join(lines_md))
    print(f"[transport] done: {len(ship):,} shipments")


if __name__ == "__main__":
    main()