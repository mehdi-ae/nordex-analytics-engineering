# NORDEX — data generation (file-based, orchestrated)

Generates coherent raw data for five source systems of a fictional French D2C
e-commerce company that runs its own warehouses. Each system is its own script
that reads upstream CSVs and writes its own, mirroring how a real warehouse
landing zone behaves. A thin orchestrator runs them in dependency order.

## Dependency order (this is the pipeline)

```
master_data  ->  orders  ->  warehouse  ->  transport  ->  finance
```

- **master_data/** → products, sites, carriers, customers (depends on nothing)
- **order_management_system/** → orders, order_lines (needs master data)
- **warehouse_management_system/** → fulfillments, inventory, inbound (needs orders)
- **transportation_management_system/** → shipments (needs warehouse)
- **finance_system/** → finance_ledger (needs shipments)

## Run it

One command, whole pipeline, reproducible (single seed per script):

```bash
python python_generate.py
```

Or run any single stage on its own, as long as its inputs already exist:

```bash
python order_management_system/generate_orders.py
```

Output lands in `./data/` (created automatically): 11 CSVs + `INJECTED_ISSUES.md`
(the merged answer key). The orchestrator prints a coherence self-check at the end.

## Two rules that keep quality intact

1. **Orchestrated order.** `python_generate.py` runs the stages in dependency
   order and stops if one fails. Coherence is not left to you remembering the order.
2. **Typed join keys on read.** Every script that reads an upstream CSV pins the
   dtype of the *join keys* only (`order_id`, `sku`, `customer_id`, `site_id`), so
   CSV's typelessness can't silently break the links between stages. Everything
   else lands however it lands — cleaning it is the project (bronze/staging), not
   the generator's job.

## Coherence vs. injected issues

- **Coherence is guaranteed:** entities connect, the business story holds, no
  impossible records — verified by the self-check every run.
- **Injected issues are deliberate:** documented in `data/INJECTED_ISSUES.md`.
  Interpretive nuances you discover while building belong in your data contracts,
  not here.

**Add `data/` to `.gitignore`** — commit the generators, not the ~90 MB of output.
Keep `data/INJECTED_ISSUES.md` out of the public repo if you want to re-test yourself.
