# Data contract — orders

**Système source :** Order Management (front e-commerce)
**Grain :** une ligne = une commande client, identifiée par `order_id`.

> Le système de commande ne connaît que « commande passée » — le statut de livraison
> est géré par le TMS. D'où `status = PLACED` pour toutes les lignes.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| order_id | STRING | non | identifiant unique de la commande (`ORD-######`) |
| customer_id | STRING | non | client (FK vers customers) — voir intermediate |
| order_ts | TIMESTAMP | non | horodatage de la commande |
| order_date | DATE | non | date de la commande |
| ship_to_region | STRING | **oui** | région de livraison — voir issue (nulls propagés) |
| status | STRING | non | statut de la commande (unique : PLACED) |

> Bronze = tout STRING. En silver : `safe_cast` (`order_ts` → TIMESTAMP,
> `order_date` → DATE ; formats OK vérifiés). Identifiants restent STRING.

## Règles & attentes

1. **Clé primaire** : `order_id` unique et non-nulle.
   → constaté : 40 doublons (voir issue) → **dédupliqués en staging**, puis
   **Tests dbt** `unique` + `not_null` (doivent passer après dédup).
2. **Complétude** : `customer_id`, `order_ts`, `order_date`, `status` non-nuls (0 null).
3. **Statut** : `status` ∈ `['PLACED']`. → **Test dbt** `accepted_values`.
   Justification : protège l'hypothèse « ce système n'émet que des commandes passées ».
   Si la source évolue (annulations, expéditions trackées…), le test alerte.

## Issues connues (de la source)

### Doublons de commande — 40 lignes (traité en staging)
- **Constat :** 174 918 lignes pour 174 878 `order_id` distincts → **40 doublons**.
- **Vérification :** doublons **parfaits** (toutes colonnes identiques). Copies exactes,
  pas de conflit — origine : double-envoi du système de commande.
- **Décision : déduplication EN STAGING** (mono-table, au plus tôt) via
  `ROW_NUMBER() OVER (PARTITION BY order_id) = 1` + `QUALIFY`. Aucune perte d'info.

### `ship_to_region` manquante — 2585 lignes (propagée)
- **Constat :** 2585 commandes sans région de livraison.
- **Nature :** **propagation d'un problème amont.** Ces commandes proviennent des ~600
  clients sans `region` (issue documentée dans le contrat `customers`). La nullité de
  `customers.region` se propage à `orders.ship_to_region`. La cohérence est confirmée :
  la propagation *a du sens* (chaque client sans région a passé plusieurs commandes).
- **Conséquence aval :** sans région, l'affectation au DC de fulfillment est indéterminée.
- **Décision :** ligne **conservée** et **flaguée** `is_region_missing`. Enrichissement
  éventuel à évaluer en **intermediate**. Statut : à surveiller.

### Autre
- Tout en STRING dans `raw` → cast en silver. Dates au bon format (vérifié).

## Reporté à la couche intermediate (intégrité référentielle)
Via le test dbt `relationships` :
- `customer_id` doit exister dans `customers` (`stg_customers`).

## Stratégie de traitement en silver (staging)

- `safe_cast` : `order_ts` (TIMESTAMP), `order_date` (DATE). `TRIM` sur les id / textes.
- **Déduplication** des 40 doublons parfaits (`ROW_NUMBER`/`QUALIFY`).
- Flag `is_region_missing` (`ship_to_region IS NULL`).
- **Aucune autre suppression.**
- Tests staging : `order_id` (unique + not_null), `not_null` sur customer_id/dates/status,
  `accepted_values: ['PLACED']` sur status.

## Fraîcheur

Order Management : commandes générées en continu (haute fréquence).

## Concept illustré sur cette table

- **Propagation d'un null** : un manque dans une dimension (customers.region) réapparaît
  dans les faits qui la référencent (orders.ship_to_region). Tracer ces propagations =
  comprendre comment un problème de qualité voyage dans le pipeline.
- **Un test protège une hypothèse** : `status = PLACED` toujours ? On le fige avec un
  test `accepted_values` qui alerte si la source change de comportement.
