# Data contract — order_lines

**Système source :** Order Management (front e-commerce)
**Grain :** une ligne = un article commandé (une ligne de détail) dans une commande.
**Clé primaire = composite** : `(order_id, line_no)` — le numéro de ligne distingue
les articles d'une même commande (deux lignes du même SKU sont possibles sur des
line_no différents). `sku` ne fait PAS partie de la clé (redondant : déterminé par
`(order_id, line_no)`).

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| order_id | STRING | non | commande parente (FK vers orders) — voir intermediate |
| line_no | INTEGER | non | numéro de la ligne dans la commande |
| sku | STRING | non | article commandé (FK vers products) — voir intermediate |
| quantity_ordered | NUMERIC | non | quantité commandée |
| unit_price_eur | NUMERIC | non | prix unitaire — voir issue (négatifs) |
| line_total_eur | NUMERIC | non | total de la ligne |

> Bronze = tout STRING. En silver : `safe_cast` (`line_no` → INTEGER,
> `quantity_ordered`/`unit_price_eur`/`line_total_eur` → NUMERIC). Identifiants STRING.

## Règles & attentes

1. **Clé primaire composite** : `(order_id, line_no)` unique.
   → constaté : 111 doublons (voir issue) → **dédupliqués en staging**, puis
   **Test dbt** `dbt_utils.unique_combination_of_columns` sur `[order_id, line_no]`.
2. **Complétude** : toutes les colonnes non-nulles (vérifié : 0 sku null).
   → **Tests dbt** `not_null`.
3. **Prix positif** : `unit_price_eur` > 0. → **violé** (voir issue) → flag.
4. **Quantité positive** : `quantity_ordered` > 0.

## Issues connues (de la source)

### Doublons de ligne — 111 lignes (traité en staging)
- **Constat :** 436 807 lignes ; 111 lignes en trop au grain `(order_id, line_no)`.
- **Vérification :** doublons **parfaits** — même `(order_id, line_no)` ET toutes les
  autres colonnes identiques. Confirmé en inspectant une commande (ex : `ORD-018121`,
  8 lignes = 4 lignes uniques dupliquées, chaque paire portant le MÊME `line_no`).
  Origine : double-envoi du système de commande (cohérent avec les 40 doublons de `orders`).
- **Décision : déduplication EN STAGING** (mono-table, au plus tôt) via
  `ROW_NUMBER() OVER (PARTITION BY toutes les colonnes) = 1` + `QUALIFY`. Ne retire que
  les doublons **parfaits** ; un éventuel conflit (même clé, valeurs différentes)
  survivrait et serait bloqué par le test d'unicité composite. Aucune perte d'info.

### Prix non positifs — 15 lignes (flag)
- **Constat :** `min(unit_price_eur) = -9.99` ; **15 lignes** avec `unit_price_eur <= 0`.
- **Nature :** probable erreur (bad promo feed). Douteux mais gravité indéterminée.
- **Subtilité :** `min(line_total_eur) = 3.11` (positif) alors que le prix unitaire est
  négatif → `unit_price × quantity != line_total` sur ces lignes. Le prix a été corrompu
  APRÈS le calcul du total : incohérence interne entre deux colonnes.
- **Décision :** ligne **conservée** et **flaguée** `is_price_non_positive` (unit_price <= 0).
  Pas de test bloquant (on ne veut pas arrêter le pipeline pour 15 lignes ; le métier tranche).
  Optionnel : flag `is_price_total_mismatch` si l'on veut aussi signaler l'incohérence
  prix×qté ≠ total.
- **Piste de remédiation (documentée, NON appliquée) :** `unit_price` est en principe
  déductible — `unit_price = line_total_eur / quantity_ordered`. On ne l'applique PAS à
  ce stade : cela présuppose que `line_total` et `quantity` font foi et que seul
  `unit_price` est faux — hypothèse non vérifiée. Corriger en aveugle remplacerait une
  erreur **visible** par une erreur **invisible** et effacerait le signal d'un problème
  source (bad promo feed). La correction, si elle a lieu, est une décision métier
  (quelle colonne fait foi ?), pas une opération de staging.

### SKU orphelins (reporté en intermediate)
- **Constat :** `null_sku = 0`, MAIS il existe ~60 order_lines dont le `sku` **n'existe
  pas dans products** (SKU présents mais invalides, ex : `SKU-DELETED-x`). Non détectable
  en staging (nécessite `products`).
- **Décision :** intégrité référentielle → **intermediate** via `relationships` vers products.

### Autre
- Tout en STRING dans `raw` → cast en silver.

## Reporté à la couche intermediate (inter-tables)
Via le test dbt `relationships` :
- `order_id` → `orders`
- `sku` → `products` (attrape les SKU orphelins)

## Stratégie de traitement en silver (staging)

- `safe_cast` : `line_no` (INTEGER), `quantity_ordered`/`unit_price_eur`/`line_total_eur`
  (NUMERIC). `TRIM` sur `order_id`, `sku`.
- **Déduplication** des 111 doublons parfaits (`ROW_NUMBER`/`QUALIFY` sur toutes colonnes).
- Flag `is_price_non_positive` (`unit_price_eur <= 0`).
- **Aucune autre suppression.**
- Tests : `not_null` sur les colonnes-clés + `unique_combination_of_columns`
  `[order_id, line_no]`.

## Fraîcheur

Order Management : lignes générées avec les commandes (haute fréquence).

## Concept illustré sur cette table

- **Clé minimale** : `(order_id, line_no)` est unique ET minimal ; `sku` est superflu
  (déterminé par la clé) → exclu. Test : « si je retire cette colonne, la clé reste-t-elle
  unique ? » Si oui, la colonne ne fait pas partie de la clé.
- **Vérifier le grain avant de dédupliquer** : dédupliquer sur `(order_id, sku)` aurait
  supprimé des lignes légitimes (même SKU, line_no différents). Le `line_no` révèle le vrai grain.
