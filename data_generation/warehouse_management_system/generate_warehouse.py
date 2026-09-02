"""
WAREHOUSE MANAGEMENT source system  —  depends on MASTER DATA + ORDERS.

Reads:  orders.csv, order_lines.csv, products.csv
Writes: fulfillments.csv, inventory_snapshots.csv, inbound_receipts.csv

Coherence defence: the raw order files carry injected duplicates and orphan
SKUs. The WMS keys on order_id and only fulfils catalogue SKUs, so those issues
stay CONTAINED in the order files (for your bronze layer to catch) instead of
corrupting inventory. Inventory is a real running balance:
    on_hand(day) = opening + cumulative_inbound - cumulative_outbound  (never < 0)

Injected issues (see data/issues_warehouse.md):
    - business rule: ~25 fulfilments with quantity_fulfilled > quantity_ordered
    - grain violation: ~20 exact-duplicate inventory snapshot rows

Run standalone (after orders):  python generate_warehouse.py
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
CAL = [(MONTH_START + timedelta(days=i)).isoformat() for i in range(DAYS)]
SITE_IDS = ["DC1", "DC2", "DC3", "DC4"]
REGION_TO_SITE = {
    "Ile-de-France": "DC1", "Normandie": "DC1", "Bretagne": "DC1",
    "Hauts-de-France": "DC2", "Grand-Est": "DC2",
    "Auvergne-Rhone-Alpes": "DC3", "Occitanie": "DC3",
    "Nouvelle-Aquitaine": "DC4",
}
ISSUES = []
def log(itype, table, rows, detect, note=""):
    ISSUES.append(dict(type=itype, table=table, rows=rows, detect=detect, note=note))


def main():
    print("[warehouse] reading orders + master data…")
    orders = pd.read_csv(DATA_DIR / "orders.csv",
    dtype={"order_id": str, "ship_to_region": str})
    order_lines = pd.read_csv(DATA_DIR / "order_lines.csv", dtype={"order_id": str, "sku": str})
    products = pd.read_csv(DATA_DIR / "products.csv", dtype={"sku": str})

    # --- work from the coherent subset (contain injected mess) ---
    o = orders.drop_duplicates("order_id").copy()
    lines = (order_lines.drop_duplicates(["order_id", "line_no"])
            .merge(products[["sku"]], on="sku", how="inner"))   # drop orphan SKUs

    # --- assign a fulfilment site per order (home DC + ~10% alternate) ---
    home = o["ship_to_region"].map(REGION_TO_SITE).fillna("DC1")
    alt = rng.random(len(o)) < 0.10
    alt_site = rng.choice(SITE_IDS, size=len(o))
    o["site_id"] = np.where(alt, alt_site, home.to_numpy())
    site_map = dict(zip(o["order_id"], o["site_id"]))
    odate = dict(zip(o["order_id"], o["order_date"]))

    # --- fulfilments (line grain) ---
    ful = lines[["order_id", "sku", "quantity_ordered"]].copy()
    ful["site_id"] = ful["order_id"].map(site_map)
    ful["quantity_fulfilled"] = ful["quantity_ordered"]
    lag = rng.integers(0, 3, size=len(ful))
    f_dt = pd.to_datetime(ful["order_id"].map(odate).values) + pd.to_timedelta(lag, unit="D")
    ful["fulfillment_ts"] = f_dt
    ful["fulfillment_date"] = f_dt.date.astype(str)
    ful.insert(0, "fulfillment_id", [f"FUL-{i:07d}" for i in range(1, len(ful) + 1)])
    ful = ful.drop(columns=["quantity_ordered"])

    # ISSUE: over-fulfilment
    f = rng.choice(ful.index, size=25, replace=False)
    ful.loc[f, "quantity_fulfilled"] = ful.loc[f, "quantity_fulfilled"] + 50
    log("business-rule violation", "fulfillments", 25,
        "quantity_fulfilled > quantity_ordered (join order_lines on order_id+sku)",
        "Can't ship more units than ordered.")

    # --- inventory: running balance per (site, sku) from real outbound ---
    out = (ful.groupby(["site_id", "sku", "fulfillment_date"])["quantity_fulfilled"]
        .sum().reset_index())
    out_map = {(r.site_id, r.sku, r.fulfillment_date): r.quantity_fulfilled
        for r in out.itertuples()}
    monthly = out.groupby(["site_id", "sku"])["quantity_fulfilled"].sum().to_dict()

    inv_rows, inb_rows = [], []
    skus = products["sku"].to_numpy()
    for site in SITE_IDS:
        for sku in skus:
            m = monthly.get((site, sku), 0)
            balance = int(m * 2 + rng.integers(20, 120))          # opening buffer
            weekly_in = int(m / 4) + int(rng.integers(10, 60))
            for i, d in enumerate(CAL):
                if i % 7 == 0 and i > 0:
                    balance += weekly_in
                    inb_rows.append((f"RCP-{len(inb_rows)+1:07d}", sku, site, weekly_in, d))
                balance -= out_map.get((site, sku, d), 0)
                inv_rows.append((d, site, sku, balance))

    inventory = pd.DataFrame(inv_rows,
        columns=["snapshot_date", "site_id", "sku", "quantity_on_hand"])
    inbound = pd.DataFrame(inb_rows,
        columns=["receipt_id", "sku", "site_id", "quantity_received", "receipt_date"])

    # ISSUE: duplicate inventory snapshot rows (grain violation)
    dup = inventory.sample(20, random_state=SEED)
    inventory = pd.concat([inventory, dup], ignore_index=True)
    log("grain violation (duplicate PK)", "inventory_snapshots", 20,
        "(snapshot_date, site_id, sku) appears twice",
        "SUM(quantity_on_hand) double-counts unless deduped.")

    ful.to_csv(DATA_DIR / "fulfillments.csv", index=False)
    inventory.to_csv(DATA_DIR / "inventory_snapshots.csv", index=False)
    inbound.to_csv(DATA_DIR / "inbound_receipts.csv", index=False)

    lines_md = ["# Injected issues — warehouse\n"]
    for it in ISSUES:
        lines_md.append(f"\n## {it['type']} — `{it['table']}` ({it['rows']} rows)\n"
                        f"- detect: {it['detect']}\n"
                        + (f"- note: {it['note']}\n" if it['note'] else ""))
    (DATA_DIR / "issues_warehouse.md").write_text("".join(lines_md))
    print(f"[warehouse] done: {len(ful):,} fulfilments, {len(inventory):,} snapshots")


if __name__ == "__main__":
    main()