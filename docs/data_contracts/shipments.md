# Data contract — shipments

**Système source :** TMS (Transportation Management System)
**Grain :** une ligne = une expédition d'une commande, identifiée par `shipment_id`.

> Table la plus riche du projet : normalisation, flag conditionnel, deux propagations
> amont, et plusieurs règles inter-tables reportées en intermediate.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| shipment_id | STRING | non | identifiant unique de l'expédition |
| order_id | STRING | non | commande expédiée (FK vers orders) — voir intermediate |
| origin_site | STRING | non | DC d'origine (FK vers sites) — voir intermediate |
| dest_region | STRING | **oui** | région de destination — voir issue (propagation) |
| carrier_name | STRING | non | transporteur (FK vers carriers) — normalisé, voir issue |
| ship_date | DATE | non | date d'expédition |
| promised_delivery_date | DATE | non | date de livraison promise |
| actual_delivery_date | DATE | **oui** | date de livraison réelle — voir issue (null selon statut) |
| weight_grams | NUMERIC | non | poids de l'expédition — voir issue (propagation) |
| freight_cost_eur | NUMERIC | non | coût de transport |
| status | STRING | non | statut : DELIVERED / IN_TRANSIT |

> Bronze = tout STRING. En silver : `safe_cast` (3 dates → DATE, 2 montants → NUMERIC ;
> formats OK vérifiés). Identifiants restent STRING.

## Règles & attentes

1. **Clé primaire** : `shipment_id` unique et non-nulle (vérifié : 174 875 / 174 875).
   → **Tests dbt** `unique` + `not_null`.
2. **Statut** : `status` ∈ `['DELIVERED', 'IN_TRANSIT']`. → **Test dbt** `accepted_values`.
3. **Cohérence interne des dates** : `actual_delivery_date >= ship_date` quand présente
   (vérifié : 0 violation). Règle intra-table.
4. **Complétude** : `order_id`, `origin_site`, `carrier_name`, `ship_date`,
   `promised_delivery_date`, `weight_grams`, `freight_cost_eur`, `status` non-nuls.

## Issues connues (de la source)

### `carrier_name` — casse/espaces incohérents (corrigé en staging)
- **Constat :** plusieurs variantes du même transporteur (majuscules/minuscules/espaces).
- **Décision : normalisé en staging** via `UPPER(TRIM(carrier_name))`. Correction sûre :
  problème de casse **constaté** (contrairement à `products.category` où rien n'était à
  corriger). Un nom de transporteur a une forme canonique.

### `actual_delivery_date` — null selon le statut (flag conditionnel)
- **Constat :** 32 435 lignes avec `actual_delivery_date` null (vrais nulls, format OK).
  DEUX populations de sens **opposés** :
  - `IN_TRANSIT` + null → **LÉGITIME** (colis pas encore livré). Ne pas flaguer.
  - `DELIVERED` + null → **BUG** (30 lignes) : livré sans date de livraison.
- **Décision :** flag conditionnel `is_delivered_without_date`
  (`status = 'DELIVERED' AND actual_delivery_date IS NULL`) → 30 lignes. Les nulls
  IN_TRANSIT ne sont PAS flagués. **Même null, deux significations selon le statut.**
- **Criticité dépendante de l'usage (raisonnement clé) :** en **staging**, on **signale**
  via flag, sans bloquer — le staging ne connaît pas l'usage aval. La **contrainte forte**
  (test bloquant ou exclusion explicite) vivra dans les **marts** qui utilisent
  `actual_delivery_date` pour mesurer la performance de livraison (OTD, transit time). Un
  mart de simple suivi de commande, lui, ignore ce flag. On n'impose pas l'exigence du
  mart le plus strict à tous les usages via un test en staging.

### `dest_region` manquante — 2584 lignes (propagation)
- **Constat :** 2584 expéditions sans région de destination.
- **Nature :** **propagation de bout en bout.** Racine = ~600 clients sans `region` →
  2585 `orders.ship_to_region` nulls → 2584 `shipments.dest_region` nulls (l'écart de 1 =
  une commande sans région n'ayant pas d'expédition). Cohérence confirmée sur toute la chaîne.
- **Décision :** ligne **conservée** et **flaguée** `is_dest_region_missing`.
  Enrichissement éventuel en intermediate.

### `weight_grams` — poids aberrants (propagation)
- **Constat :** `min(weight_grams) = 0.06`.
- **Nature :** **propagation du unit drift de `products`** — les ~60 SKU dont le poids est
  saisi en kg (au lieu de grammes) contaminent le poids des expéditions qui les contiennent.
- **Décision :** **non corrigé ici** (problème à la source, dans products). Documenté comme
  conséquence connue. La correction se fait à la racine (products) ou en intermediate.
  Impact aval : fausse le coût de transport de ces expéditions.

### Autre
- Tout en STRING dans `raw` → cast en silver. Formats de dates OK (vérifié).

## Reporté à la couche intermediate (inter-tables)

- **Cohérence commande/expédition** : `ship_date >= order_date` (nécessite `orders` —
  ~25 violations injectées : expédié avant commandé). Test/flag en intermediate.
- **Intégrité référentielle** via `relationships` :
  - `order_id` → `orders`
  - `origin_site` → `sites`
  - `carrier_name` (normalisé) → `carriers`

## Stratégie de traitement en silver (staging)

- `safe_cast` des 3 dates (DATE) et 2 montants (NUMERIC) ; `TRIM` sur les id.
- **Normalisation** `carrier_name` = `UPPER(TRIM(...))`.
- Flags : `is_delivered_without_date` (conditionnel au statut), `is_dest_region_missing`.
- **Aucune ligne supprimée.**
- Tests : `shipment_id` (unique + not_null), `accepted_values` sur status, `not_null` sur
  les colonnes non-nullables, cohérence interne des dates si souhaité.

## Fraîcheur

TMS : expéditions générées au fil des livraisons (haute fréquence). Le statut évolue
dans le temps (IN_TRANSIT → DELIVERED) — nature d'une donnée qui se met à jour.

## Concepts synthétisés sur cette table

- **Flag conditionnel** : la même valeur (null) a deux sens selon une autre colonne
  (statut) → le flag combine les deux, ne se déclenche que sur le cas-bug.
- **Criticité dépendante de l'usage** : le staging signale (flag) ; la contrainte forte
  descend vers les marts, là où l'usage de la donnée est connu.
- **Propagation de bout en bout** : deux problèmes (région, poids) tracés depuis leur
  racine à travers 3-4 tables → preuve de la cohérence du pipeline.
- **Normalisation justifiée par constat** : on normalise (carrier) parce qu'on a constaté
  le problème ; on ne normalise pas préventivement (category) sans problème constaté.
