# Data contract — sites

**Système source :** master_data
**Grain :** une ligne = un site logistique (centre de distribution / DC), identifié par `site_id`.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| site_id | STRING | non | identifiant unique du DC (ex : DC1) |
| city | STRING | non | ville du DC |
| region | STRING | non | région administrative du DC |
| storage_capacity_units | NUMERIC | non | capacité de stockage, en unités |

> En bronze (`raw`), tout est STRING. Cast en silver via `safe_cast`
> (`storage_capacity_units` → NUMERIC). Les colonnes texte reçoivent un `TRIM`.

## Règles & attentes

1. **Clé primaire** : `site_id` unique et non-nulle. *(un DC = un identifiant)*
   → **Tests dbt** `unique` + `not_null`.
2. **Complétude** : `city`, `region`, `storage_capacity_units` non-nulles
   (données structurelles d'un entrepôt, doivent toujours exister).
   → **Test dbt** `not_null` sur `storage_capacity_units`.
3. **Capacité positive** : `storage_capacity_units` **≥ 1**.
   Justification : un entrepôt avec une capacité nulle ou négative n'a pas de sens
   opérationnel. Une violation est **inacceptable**, pas un cas métier à tolérer.
   → **Test dbt** `dbt_utils.accepted_range` (min_value: 1) — échec si violé,
   ce qui est le comportement voulu (test, pas flag).

## Issues connues (de la source)

**Aucune anomalie constatée au diagnostic.** Table de référence propre :
- 4 sites, `site_id` unique et non-null ;
- aucune valeur nulle sur les 4 colonnes ;
- capacités toutes positives et d'ordre de grandeur plausible.

Les règles ci-dessus sont donc des **filets permanents** : elles ne corrigent rien
aujourd'hui, mais détecteront une anomalie future (ex : un 5e site mal saisi).

## Stratégie de traitement en silver

- `safe_cast(storage_capacity_units as NUMERIC)`.
- `TRIM` sur `site_id`, `city`, `region` (sécurité, ne masque rien).
- **Aucun flag nécessaire** : toutes les règles de sites sont des **tests**
  (violation = inacceptable), pas des tolérances à signaler.
- **Aucune ligne supprimée.**

## Fraîcheur

Master data quasi statique : les DC changent très rarement (ouverture/fermeture
d'entrepôt = événement rare).
