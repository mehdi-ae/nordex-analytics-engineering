"""
ORCHESTRATOR — runs the five source-system generators in dependency order.

This is hand-rolled orchestration: run a task, check it succeeded, only then run
the next. It's the exact mental model Airflow formalises later (a DAG of tasks
with dependencies). Each script is a black box to this file — it just runs them
in order and stops if one fails.

    master_data  ->  orders  ->  warehouse  ->  transport  ->  finance

Run the whole pipeline reproducibly with one command:  python python_generate.py
(You can still run any single script on its own, as long as its inputs exist.)
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

# (label, path) in strict dependency order
PIPELINE = [
    ("master_data",   ROOT / "master_data" / "generate_master_data.py"),
    ("orders",        ROOT / "order_management_system" / "generate_orders.py"),
    ("warehouse",     ROOT / "warehouse_management_system" / "generate_warehouse.py"),
    ("transport",     ROOT / "transportation_management_system" / "generate_shipments.py"),
    ("finance",       ROOT / "finance_system" / "generate_finance.py"),
]


def run_stage(label, path):
    print(f"\n{'='*60}\n▶ STAGE: {label}\n{'='*60}")
    result = subprocess.run([sys.executable, str(path)])
    if result.returncode != 0:
        print(f"\n✗ Stage '{label}' FAILED (exit {result.returncode}). Stopping pipeline.")
        sys.exit(result.returncode)


def merge_answer_key():
    parts = ["# Injected Data Issues — Answer Key\n",
        "Consolidated from every source system. Keep this out of the public repo\n",
        "(add `data/INJECTED_ISSUES.md` to .gitignore) if you want to re-test yourself.\n"]
    for name in ["master_data", "order_management", "warehouse", "transportation", "finance"]:
        f = DATA_DIR / f"issues_{name}.md"
        if f.exists():
            parts.append("\n\n---\n\n" + f.read_text())
    (DATA_DIR / "INJECTED_ISSUES.md").write_text("".join(parts))


def coherence_check():
    print(f"\n{'='*60}\n▶ COHERENCE SELF-CHECK\n{'='*60}")
    orders = pd.read_csv(DATA_DIR / "orders.csv", dtype={"order_id": str}).drop_duplicates("order_id")
    lines = pd.read_csv(DATA_DIR / "order_lines.csv", dtype={"order_id": str, "sku": str})
    prods = pd.read_csv(DATA_DIR / "products.csv", dtype={"sku": str})
    ship = pd.read_csv(DATA_DIR / "shipments.csv", dtype={"order_id": str})
    inv = pd.read_csv(DATA_DIR / "inventory_snapshots.csv", dtype={"site_id": str, "sku": str})
    fin = pd.read_csv(DATA_DIR / "finance_ledger.csv")

    orphan = (~lines.drop_duplicates(["order_id", "line_no"])["sku"].isin(prods["sku"])).sum()
    j = ship.merge(orders[["order_id", "order_date"]], on="order_id", how="left")
    bad_ship = (pd.to_datetime(j["ship_date"]) < pd.to_datetime(j["order_date"])).sum()
    d = ship.dropna(subset=["actual_delivery_date"])
    bad_deliv = (pd.to_datetime(d["actual_delivery_date"]) < pd.to_datetime(d["ship_date"])).sum()
    neg_inv = (inv["quantity_on_hand"] < 0).sum()
    bug_null = ((ship["status"] == "DELIVERED") & ship["actual_delivery_date"].isna()).sum()

    # finance join only works after normalising the key
    fin2 = fin.copy()
    fin2["order_id_fixed"] = "ORD-" + fin2["order_ref"].astype(int).map("{:06d}".format)
    matched = fin2.merge(orders[["order_id"]], left_on="order_id_fixed",
        right_on="order_id", how="inner")

    print(f"orphan order_lines (injected 60):            {orphan}")
    print(f"ship_date < order_date (injected 25):        {int(bad_ship)}")
    print(f"actual_delivery < ship_date (must be 0):     {int(bad_deliv)}")
    print(f"negative inventory (must be 0):              {int(neg_inv)}")
    print(f"DELIVERED + null delivery bug (injected 30): {int(bug_null)}")
    print(f"finance rows matched after key-normalise:    {len(matched):,} / {len(fin):,}")


def main():
    print("Running data-generation pipeline in dependency order…")
    for label, path in PIPELINE:
        run_stage(label, path)
    merge_answer_key()
    coherence_check()
    print(f"\n✓ Pipeline complete. Tables + answer key in {DATA_DIR}")


if __name__ == "__main__":
    main()