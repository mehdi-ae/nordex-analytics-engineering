# Data contract — inbound_receipts

**Système source :** WMS (Warehouse Management System)
**Grain :** une ligne = une réception de stock (un SKU reçu sur un site à une date),
identifiée par `receipt_id`. C'est le flux **entrant** de stock (réapprovisionnement
depuis les fournisseurs).

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| receipt_id | STRING | non | identifiant unique de la réception |
| sku | STRING | non | produit reçu (FK vers products) — voir intermediate |
| site_id | STRING | non | DC de réception (FK vers sites) — voir intermediate |
| quantity_received | NUMERIC | non | quantité reçue |
| receipt_date | DATE | non | date de réception |

> Bronze = tout STRING. En silver : `safe_cast` (`quantity_received` → NUMERIC,
> `receipt_date` → DATE, format **ISO** vérifié → cast direct). Identifiants restent STRING.

## Règles & attentes

1. **Clé primaire** : `receipt_id` unique et non-nulle.
   → vérifié : 24 000 lignes / 24 000 distincts / 0 null. **Tests dbt** `unique` + `not_null`.
2. **Complétude** : `sku`, `site_id`, `quantity_received`, `receipt_date` non-nulles
   (vérifié : 0 null partout). → **Tests dbt** `not_null`.
3. **Quantité positive** : `quantity_received` > 0 (vérifié : min = 26).
   → **Test dbt** `dbt_utils.accepted_range` (min_value: 1) — filet permanent.
4. **Format date** : `receipt_date` en ISO (vérifié : 0 valeur non-castable).

## Issues connues (de la source)

**Aucune anomalie interne constatée.** Table propre en elle-même : clé unique, zéro
null, quantités positives, dates ISO. Les règles ci-dessus sont des **filets permanents**.

## Reporté à la couche intermediate (intégrité référentielle)

À vérifier en intermediate avec le test dbt `relationships` (validation contre la
source de vérité = la dimension, plutôt qu'une liste figée) :
- `sku` doit exister dans `products` (`stg_products`).
- `site_id` doit exister dans `sites` (`stg_sites`).

> Rappel : `relationships` est inter-tables → intermediate, pas staging. Une seule
> source de vérité (la dimension), mise à jour à un seul endroit.

## Stratégie de traitement en silver (staging)

- `safe_cast` : `quantity_received` (NUMERIC), `receipt_date` (DATE).
- `TRIM` sur les identifiants (restent STRING).
- **Aucun flag** : aucune règle interne à risque ; les FK sont inter-tables → intermediate.
- **Aucune ligne supprimée.**
- Tests staging : `receipt_id` (unique + not_null) ; `not_null` sur les colonnes clés ;
  `accepted_range` (min 1) sur `quantity_received`.

## Fraîcheur

WMS : réceptions générées au fil des réapprovisionnements (dans le générateur,
réappro périodique — cadence régulière).
