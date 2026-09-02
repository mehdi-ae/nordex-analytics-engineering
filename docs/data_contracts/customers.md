# Data contract — customers

**Système source :** master_data
**Grain :** une ligne = un client, identifié par `customer_id`.

## Schéma (types cibles en silver)

| colonne | type | nullable | signification |
|---|---|---|---|
| customer_id | STRING | non | identifiant unique du client |
| region | STRING | **oui** | région du client (8 valeurs) — voir issue |
| signup_date | DATE | **oui** | date d'inscription du client — voir issue |

> En bronze (`raw`), tout est STRING. Cast en silver via `safe_cast`.
> `signup_date` : format **ISO propre** vérifié au diagnostic (0 valeur non-castable),
> donc `safe_cast(signup_date as date)` suffit — pas de `parse_date` multi-format.

## Règles & attentes

1. **Clé primaire** : `customer_id` unique et non-nulle. *(un client = un identifiant)*
   → vérifié : 40 000 lignes / 40 000 distincts / 0 null. **Test dbt.**
2. **Domaine `region`** : quand renseignée, doit appartenir aux 8 régions connues.
   → **Test dbt** `accepted_values` (surveille l'apparition d'une valeur hors-liste).
3. `region` et `signup_date` **peuvent être nulles** (voir issues) — la nullité est
   tolérée mais **flaguée**, jamais supprimée.

## Issues connues (de la source) — constatées au diagnostic, NON corrigées en silver

Deux populations **disjointes** (600 + 600 = 1 200 lignes distinctes, pas les mêmes
clients) → deux problèmes indépendants, traités séparément.

### `region` manquante — 600 clients
- **Nature :** donnée manquante. Un client sans région peut être légitime à la source,
  MAIS a une **conséquence opérationnelle** : la région détermine le DC de fulfillment
  (sans elle, pas d'affectation propre au site → fallback DC1 dans le générateur).
- **Décision :** ligne **conservée** et **flaguée** `is_region_missing`. Ce n'est pas
  "irrécupérable" : la région pourra potentiellement être **enrichie en aval** depuis
  `orders.ship_to_region` (couche intermediate, là où vivent les jointures). Le flag
  signale "à enrichir si possible, sinon fallback".
- **Statut :** à surveiller, résolution possible en intermediate.

### `signup_date` manquante — 600 clients
- **Nature :** donnée manquante, plus douteuse. Un client existe forcément parce qu'il
  s'est inscrit → une date d'inscription absente ressemble davantage à un **défaut de
  saisie** qu'à un cas normal.
- **Décision :** ligne **conservée** et **flaguée** `is_signup_missing`. Gravité
  **indéterminée à ce stade** : dépend de l'usage aval de la date (cohortes, ancienneté,
  LTV). À **investiguer** avant de trancher. On documente l'incertitude plutôt que de la
  masquer.
- **Statut :** à investiguer.

### Autre
- Tout en STRING dans `raw` → cast requis en silver (`safe_cast`).

## Stratégie de traitement en silver

- `safe_cast` chaque colonne au type cible (`signup_date` → DATE, cast simple).
- `TRIM` sur les colonnes texte (sécurité, ne masque rien).
- **Aucune ligne supprimée.**
- Flags de complétude (nommés par la **nature** du problème = "missing", pas "invalid") :

| flag | condition (true = à signaler) | nature |
|---|---|---|
| `is_region_missing` | region IS NULL | donnée manquante, impact fulfillment, enrichissable aval |
| `is_signup_missing` | signup_date IS NULL | donnée manquante, à investiguer |

- Règles d'unicité `customer_id` et domaine `region` → **tests dbt**, pas flags.

## Fraîcheur

Master data : évolution lente (nouveaux clients au fil des inscriptions).

## Note de vocabulaire

Les flags disent "missing" (absent), pas "invalid" (invalide) : une région absente
n'est pas une région fausse. Le nom du flag doit refléter la **nature** exacte du
problème — précision qui rend le contrat lisible et la décision défendable.
