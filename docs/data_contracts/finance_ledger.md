# Data contract — finance_ledger

**Système source :** ERP / finance
**Grain :** une ligne = les écritures financières d'une commande, identifiée par `order_ref`.

> ERP = le système « autoritaire mais atypique ». Il utilise volontairement des
> conventions différentes du reste de la plateforme → plusieurs problèmes systémiques.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| order_ref | STRING | non | réf. commande, **format numérique brut** (ex : `11288`) — voir issue |
| revenue_date | DATE | non | date de reconnaissance du revenu — voir issue (format) |
| recognized_revenue_eur | NUMERIC | non | revenu reconnu |
| cogs_eur | NUMERIC | non | coût des marchandises vendues |
| freight_cost_eur | NUMERIC | **oui** | coût de transport — voir issue (nulls) |

> Bronze = tout STRING. En silver : `safe_cast` des montants ; `revenue_date` via
> **`parse_date`** (pas `safe_cast`, voir issue format).

## Règles & attentes

1. **Clé primaire** : `order_ref` unique et non-nulle.
   → vérifié : 174 878 lignes / 174 878 distincts. **Tests dbt** `unique` + `not_null`.
2. **Revenu positif** : `recognized_revenue_eur` > 0 (une commande facturée génère un revenu).
3. **COGS positif** : `cogs_eur` > 0 (des marchandises vendues ont un coût). → **violé**, voir issue.
4. **Freight ≥ 0** quand présent.

## Issues connues (de la source) — constatées au diagnostic, NON corrigées en silver

### `revenue_date` — format non-ISO (systémique)
- **Constat :** dates au format **`DD/MM/YYYY`** (ex : `03/06/2025`), pas ISO. Toutes les
  valeurs résistent à un `safe_cast(... as date)`.
- **Décision :** **résolu en staging** (problème interne à la colonne, ne dépend d'aucune
  autre table) via `parse_date('%d/%m/%Y', revenue_date)`. C'est le problème qui faisait
  crasher le load initial ; on le corrige proprement dans la couche prévue pour ça.

### `order_ref` — format brut, réconciliation reportée (systémique, inter-tables)
- **Constat :** `order_ref` est un **numéro brut** (`11288`), sans le préfixe utilisé
  ailleurs sur la plateforme (`ORD-######`).
- **Décision :** **NON transformé en staging.** On ne présuppose pas le format de la clé de
  `orders` (table non encore diagnostiquée) — on ne travaille qu'avec l'info disponible.
  Réconcilier `order_ref` avec la clé de commande est une **logique inter-tables** →
  reportée à la couche **intermediate**, quand `stg_orders` existera. Le staging se
  contente de nettoyer `order_ref` (TRIM), et documente le format.

### `freight_cost_eur` — 3 valeurs nulles (inter-tables)
- **Constat :** 3 lignes (`order_ref` 11288, 22442, 24678) ont un freight null, alors que
  revenu et COGS sont présents.
- **Hypothèse :** commandes facturées **sans expédition correspondante** dans `shipments`
  (le freight provient de la TMS). Ne peut être tranché sans regarder `shipments`.
- **Décision :** ligne **conservée** et **flaguée** `is_freight_missing`. Investigation en
  **intermediate** (jointure finance ↔ shipments). Statut : à investiguer.

### `cogs_eur` — valeurs à 0 (règle métier)
- **Constat :** `min(cogs_eur) = 0` → des commandes avec un COGS nul.
- **Nature :** douteux — un COGS de 0 signifierait des marchandises sans coût. Possible
  coût manquant saisi en 0, ou cas légitime (promo/échantillon ?).
- **Décision :** ligne **conservée** et **flaguée** `is_cogs_non_positive`. Gravité
  indéterminée → à investiguer avant correction (décision métier). On documente
  l'incertitude au lieu de la masquer.

### Autre
- Tout en STRING dans `raw` → cast requis en silver.

## Stratégie de traitement en silver

- `revenue_date` → `parse_date('%d/%m/%Y', ...)`.
- `recognized_revenue_eur`, `cogs_eur`, `freight_cost_eur` → `safe_cast(... as NUMERIC)`.
- `order_ref` → `TRIM`, **pas de reconstruction de clé** (report intermediate).
- **Aucune ligne supprimée.**

| flag | condition (true = à signaler) | nature |
|---|---|---|
| `is_freight_missing` | freight_cost_eur IS NULL | manquant, à investiguer vs shipments |
| `is_cogs_non_positive` | cogs_eur ≤ 0 | règle métier violée, gravité à investiguer |

- Clé `order_ref` (unicité, non-null) → **tests dbt**.

## Reporté à la couche intermediate
- Réconciliation `order_ref` (brut) ↔ clé de `orders` (`ORD-######`).
- Investigation des 3 freight nuls contre `shipments`.

## Fraîcheur

ERP : mises à jour au fil des commandes facturées ; peut accuser un léger décalage
(nature « autoritaire mais en retard » d'un ERP).
