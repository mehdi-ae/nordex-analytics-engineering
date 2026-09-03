# Data contract — inventory_snapshots

**Système source :** WMS (Warehouse Management System)
**Grain :** une ligne = le niveau de stock d'un SKU, sur un site, à une date donnée.
**Clé primaire = composite** : `(snapshot_date, site_id, sku)`. Pas de clé technique
unique — l'identité est la combinaison des trois colonnes.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| snapshot_date | DATE | non | date de la capture de stock |
| site_id | STRING | non | DC concerné (FK vers sites) — voir intermediate |
| sku | STRING | non | produit concerné (FK vers products) — voir intermediate |
| quantity_on_hand | NUMERIC | non | quantité en stock ce jour-là |

> Bronze = tout STRING. En silver : `safe_cast` (`snapshot_date` → DATE, format ISO
> vérifié → cast direct ; `quantity_on_hand` → NUMERIC). Identifiants restent STRING.

## Règles & attentes

1. **Clé primaire composite** : `(snapshot_date, site_id, sku)` unique.
   → **Test dbt** `dbt_utils.unique_combination_of_columns` (au niveau modèle).
   Doit passer **après** déduplication (voir issue).
2. **Complétude** : les trois colonnes-clés non-nulles (vérifié : 0 null).
   → **Tests dbt** `not_null`.
3. **Quantité** : `quantity_on_hand` >= 0 (un stock peut légitimement être 0 = rupture ;
   une valeur négative serait une anomalie).

## Issues connues (de la source) — traitée en staging

### Doublons de grain — 20 lignes
- **Constat :** 180 020 lignes pour 180 000 combinaisons `(snapshot_date, site_id, sku)`
  distinctes → **20 doublons** sur la clé composite (violation de grain).
- **Vérification :** ces 20 doublons sont **parfaits** — même clé ET même
  `quantity_on_hand` (contrôlé : `count(distinct quantity_on_hand) = 1` par groupe).
  Ce sont des copies exactes, pas des conflits de valeur.
- **Décision : déduplication EN STAGING** (problème mono-table → au plus tôt, avant que
  les couches aval héritent des doublons). Via `ROW_NUMBER() OVER (PARTITION BY clé) = 1`
  + `QUALIFY`. Supprimer une copie exacte ne perd **aucune information** (l'autre porte la
  même donnée) → ne viole pas la règle « ne jamais perdre d'info ».
- **Note :** la déduplication n'est sûre QUE parce que les doublons sont parfaits. En cas
  de **conflit** (mêmes clés, quantités différentes), on ne déduplique pas au hasard :
  on flague et on remonte au métier. Ici, pas de conflit -> dédup sûre.

### Autre
- Tout en STRING dans `raw` → cast en silver. Dates en ISO (vérifié).

## Reporté à la couche intermediate (intégrité référentielle)
Via le test dbt `relationships` :
- `sku` doit exister dans `products`.
- `site_id` doit exister dans `sites`.

## Stratégie de traitement en silver (staging)

- `safe_cast` : `snapshot_date` (DATE), `quantity_on_hand` (NUMERIC). `TRIM` sur les id.
- **Déduplication** des 20 doublons parfaits via `ROW_NUMBER`/`QUALIFY`.
- **Aucune autre suppression** ; aucun flag interne.
- Tests staging : `not_null` sur les 3 colonnes-clés + unicité de la combinaison
  `(snapshot_date, site_id, sku)`.

## Fraîcheur

WMS : snapshot **journalier** (une capture par SKU/site/jour). Cadence quotidienne.

## Concept découvert sur cette table

- **Clé composite** : quand il n'y a pas de clé technique, le grain = la combinaison de
  colonnes qui identifie une ligne. Testée avec `unique_combination_of_columns`.
- **Doublon parfait vs conflit** : un doublon identique se déduplique sans risque ; un
  doublon avec valeurs divergentes est une incohérence à signaler, pas à trancher au hasard.
- **Test au niveau modèle** (vs niveau colonne) : un test portant sur plusieurs colonnes
  s'attache au modèle, pas à une colonne.
