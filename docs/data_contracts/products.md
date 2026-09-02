# Data contract — products

**Système source :** master_data
**Grain :** une ligne = un produit, identifié par `sku`.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| sku | STRING | non | identifiant unique du produit |
| product_name | STRING | non | libellé du produit |
| category | STRING | non | catégorie (8 valeurs distinctes) |
| weight_grams | NUMERIC | non | poids en grammes |
| unit_cost_eur | NUMERIC | non | coût unitaire d'achat |
| list_price_eur | NUMERIC | non | prix de vente catalogue |

> En bronze (`raw`), toutes les colonnes sont en STRING. Le cast au type cible se fait
> en silver, via `safe_cast` (une valeur incastable devient NULL = signal à flaguer).

## Règles & attentes

Ce qui **doit** être vrai. Chaque règle est justifiée, et deviendra un test dbt ou un flag.

1. **Clé primaire** : `sku` unique et non-nulle. *(un produit = une référence)*
2. **Cohérence libellé** : un `sku` ne peut avoir qu'un seul `product_name`
   (pas de SKU associé à plusieurs libellés).
3. **Positivité** : `weight_grams`, `unit_cost_eur`, `list_price_eur` sont tous **> 0**.
4. **Bornes de poids** : `weight_grams` ∈ **[20 g, 20 000 g]**.
   - Borne basse 20 g : en dessous, les articles trop petits risquent d'endommager les
     convoyeurs / équipements d'entrepôt.
   - Borne haute 20 kg : au-delà, dépasse la limite de port manuel autorisée pour les
     opérateurs (sécurité).
5. **Marge positive** : `list_price_eur ≥ unit_cost_eur`
   (on ne vend jamais à perte au niveau catalogue).

## Issues connues (de la source) — constatées au diagnostic, NON corrigées en silver

- **weight_grams — unit drift suspecté.** ~60 SKU présentent un poids anormalement bas
  (valeurs de type 0.06), sous le seuil de 20 g. Hypothèse : poids saisis en
  **kilogrammes** au lieu de grammes.
  - **Décision :** non corrigé automatiquement en silver. La ligne est **conservée** et
    **flaguée** non-conforme (`is_weight_out_of_bounds`). La correction est renvoyée au
    métier : soit vraie erreur d'unité à corriger, soit nouvelle référence légère légitime.
  - **Impact aval :** le poids alimente le calcul du coût de transport (freight) dans
    `shipments` → un poids en kg lu comme des grammes fausse le freight de ces produits.
- **Tout en STRING** dans `raw` : cast requis en silver (via `safe_cast`).

## Stratégie de traitement en silver (rappel de méthode)

- `safe_cast` chaque colonne au type cible ; NULL après cast = valeur non castable → flag.
- **Aucune ligne supprimée** : tout est conservé.
- Chaque règle violée → colonne booléenne de flag (`true` = non-conforme).
- Correction des non-conformités = décision métier, hors périmètre du silver.

## Fraîcheur

Master data : évolution lente (ajout occasionnel de SKU). Pas de mise à jour à haute fréquence.

## Flags produits en silver (dérivés des règles ci-dessus)

| flag | condition (true = problème) |
|---|---|
| `is_weight_out_of_bounds` | poids < 20 OU poids > 20000 |
| `is_price_below_cost` | list_price_eur < unit_cost_eur |
| `has_non_positive_value` | weight/cost/price ≤ 0 |
| `is_weight_uncastable` | safe_cast(weight_grams) IS NULL alors que la valeur brute ne l'est pas |

*(les règles d'unicité `sku` et `sku → product_name` seront des tests dbt, pas des flags)*
