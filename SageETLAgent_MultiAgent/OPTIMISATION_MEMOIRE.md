# SageETLAgent — Optimisation mémoire / CPU

Symptôme initial : le process `SageETLAgent` consommait **~4,6 Go de RAM** et jusqu'à
**72 % CPU** pendant un cycle de synchronisation continue (tables volumineuses :
`Ecritures_Analytiques` ~234 072 lignes, `Clients` ~9 293, `Articles` ~2 357).

Ce document décrit le **Volet A** (réglages de configuration, faible risque) déjà appliqué.
Le **Volet B** (corrections structurelles) est décrit en fin de document — non encore appliqué.

---

## Volet A — Réglages de configuration (appliqué)

Tous ces réglages sont **surchargeables sans recompiler** via `appsettings.json`
(section `SageEtl`). Les valeurs par défaut du code ont été abaissées : même sans modifier
`appsettings.json`, un simple redéploiement applique déjà les valeurs recommandées.

| Réglage | Ancien | **Nouveau défaut** | Rôle |
|---|---|---|---|
| `MaxParallelTables` | 3 | **1** | Nombre de tables synchronisées simultanément par agent |
| `TurboBatchSize` | 50000 | **15000** | Taille de lot `SqlBulkCopy` côté DWH |
| `MergeBatchSize` | 5000 | 5000 | Taille de lot `MERGE` (inchangé, désormais configurable) |
| `DeleteDetectionDisabledTables` | — | `[]` | Tables exclues de la détection des suppressions |

### 1. `MaxParallelTables` : 3 → 1 — **le gain principal**

Le service traitait jusqu'à **3 tables en parallèle** (un `SemaphoreSlim(3)`). Or, chaque
table est **entièrement matérialisée en mémoire** (`List<Dictionary<string, object?>>`)
avant écriture. Trois tables volumineuses chargées en même temps = **×3 sur le pic RAM**.

`Ecritures_Analytiques` (~234 k lignes × ~20 colonnes, valeurs boxées + surcharge
`Dictionary`) pèse à elle seule ~1–1,5 Go en mémoire managée. En parallèle ×3 → l'ordre de
grandeur des 4,6 Go observés.

Passer à **1** sérialise les tables : le pic mémoire correspond désormais à **une seule
table à la fois**. C'est le levier le plus impactant du Volet A.

> Compromis : un cycle est un peu plus long (les grosses tables ne se recouvrent plus).
> Pour un agent de fond en continu, la latence d'un cycle importe moins que le pic RAM.
> Si le poste a de la marge (RAM + CPU), monter à `2`. Éviter `3` sur les postes contraints.

### 2. `TurboBatchSize` : 50000 → 15000

Taille de lot de `SqlBulkCopy` (nombre de lignes par aller-retour / transaction interne).
La baisser **réduit les verrous et la croissance du journal de transactions SQL Server par
lot**, ce qui limite la contention côté base.

> Honnêteté technique : dans le code **actuel**, `ConvertToDataTable` matérialise déjà tout
> le `DataTable` avant l'appel, donc baisser `TurboBatchSize` n'allège que marginalement la
> RAM **de l'agent** (le gros de la RAM est le `List<Dictionary>` + le `DataTable`). Le vrai
> gain RAM de ce réglage n'apparaît **qu'après le Volet B** (écriture par lots streamés), où
> chaque `DataTable` sera borné à `TurboBatchSize`. En attendant, le bénéfice immédiat est
> côté SQL Server (verrous/journal).

### 3. `DeleteDetectionDisabledTables` : opt-out par table

**Constat.** La détection des suppressions compare tous les IDs de la source Sage avec tous
les IDs du DWH pour supprimer les orphelins. Elle charge **deux listes complètes d'IDs en
mémoire** (côté source ~234 k pour `Ecritures_Analytiques`, plus l'ensemble côté DWH dans un
`HashSet`). C'est le **2ᵉ poste mémoire** après la matérialisation des tables.

**Limite du réglage serveur existant.** Le flag par table `delete_detection` (0/1) vient du
serveur. Mais la décision réelle est :
`table.DeleteDetection || (isIncremental && pks.Any())`
(`ContinuousSyncService.SyncTableAsync`). Autrement dit, pour une table **incrémentale avec
clé primaire**, la détection tourne **toujours**, même avec `delete_detection = 0`. Il
n'existait donc **aucun moyen** de la désactiver pour une grosse table incrémentale.

**Nouvelle option (côté client, sans changement serveur).** Lister les tables à exclure dans
`appsettings.json`. À réserver aux tables **volumineuses qui ne suppriment jamais de lignes
côté Sage** (typiquement les écritures comptables, en append-only) :

```jsonc
"SageEtl": {
  // ...
  "DeleteDetectionDisabledTables": [ "Ecritures_Analytiques" ]
}
```

La correspondance se fait sur le **nom source** ou la **table cible** (insensible à la casse).
Liste vide / absente ⇒ **comportement historique strictement inchangé**.

> Attention : ne désactiver que pour des tables où une suppression côté Sage ne doit **pas**
> être répercutée (ou est impossible). Pour une table où des lignes peuvent disparaître,
> laisser la détection active — le Volet B la rendra peu coûteuse (côté SQL).

### Exemple `appsettings.json` complet

```jsonc
"SageEtl": {
  "ServerUrl": "http://optiboard.kasoft.ma",
  "DwhCode": "ALEA_FOOD",
  "AgentFilter": "",

  "MaxParallelTables": 1,
  "TurboBatchSize": 15000,
  "MergeBatchSize": 5000
  // , "DeleteDetectionDisabledTables": [ "Ecritures_Analytiques" ]
}
```

### Où c'est câblé

- Défauts : `ContinuousSyncService` (`MaxParallelTables`, `WriterTurboBatchSize`,
  `WriterMergeBatchSize`), `DwhWriter.TurboBatchSize`.
- Lecture config : `ServiceConfig` (section `SageEtl`) → `ContinuousSyncService.ApplyPerformanceConfig(config)`.
- Appliqué aux 3 points de démarrage d'un agent : `SageEtlWorker` (service Windows) et les
  deux instanciations de `MultiAgentForm` (interface).

### Impact attendu (Volet A seul)

- Pic RAM divisé ~×3 grâce à `MaxParallelTables=1` (de ~4,6 Go vers ~1,5 Go, ordre de grandeur).
- `-DeleteDetectionDisabledTables` sur `Ecritures_Analytiques` : évite le chargement de
  ~234 k IDs source + ensemble DWH à chaque cycle.
- CPU plus lissé (moins de contention SQL, moins de GC de gros objets simultanés).
- **Données synchronisées identiques** (aucun changement fonctionnel).

---

## Volet B — Corrections structurelles (appliqué)

Objectif : réduire le **pic mémoire** sans changer les données synchronisées. Chaque point
préserve strictement la logique métier (mêmes lignes écrites/supprimées).

### 1. Extraction streamée par lots — **le vrai correctif mémoire**

`SageExtractor.ExtractTableStreamedAsync(query, batchSize, onBatchAsync, ...)` lit le
`DataReader` et invoque un callback tous les `BatchSize` lignes **sans jamais accumuler toute
la table** (`List<Dictionary>`). Chaque lot est écrit dans le DWH puis libéré → **pic mémoire
= 1 lot** (`table.BatchSize`, défaut 5000) au lieu de toute la table (234 k lignes).

Côté écriture : `DwhWriter.PrepareSocieteReplaceAsync` (schéma + colonnes + `DELETE` société
**une seule fois**, au 1ᵉʳ lot) puis `InsertSocieteBatchAsync` par lot. Résultat final
identique à `WriteTableDataForSocieteAsync` (DELETE société + INSERT), mais en flux.

**Préservation de la stratégie (point critique).** La stratégie (`merge` vs `truncate_insert`)
dépend aujourd'hui de `data.Count` (`> 100000`, `< 10000`). On ne connaît pas ce total en
streaming. Le streaming n'est donc activé (`streamingEligible`, `ContinuousSyncService`) que
lorsque la stratégie est **forcément `truncate_insert` quel que soit le nombre de lignes** :

```
streamingEligible = extraction complète (ni info-libres, ni moteur incrémental)
                    ET (forceFullReload OU non-incrémental OU sans PK)
```

Dans ces cas, l'ancien code choisissait **toujours** `truncate_insert` (DELETE société +
INSERT) indépendamment du count → le streaming reproduit exactement cette opération. Tous les
autres cas (incrémental établi, **1ᵉʳ chargement** d'une table incrémentale, info-libres)
restent sur le chemin **matérialisé** (`ExtractAndWriteMaterializedAsync`, logique historique
inchangée), pour ne jamais risquer un `DELETE société + INSERT partiel` (perte de données).

> Robustesse (durcissements suite à revue) :
> - **Retry à l'ouverture** de la requête (avant tout écriture) comme le chemin non streamé ;
>   une fois un lot émis, plus de retry (ré-émettre un lot déjà écrit ferait une double-écriture).
>   Une erreur transitoire *après* le 1ᵉʳ lot fait échouer la table pour ce cycle → retentée au
>   suivant (`lastSync` non avancé sur échec ⇒ DELETE + ré-INSERT complet auto-réparateur).
> - **Inférence de type robuste** dans `ConvertToDataTable` : le type d'une colonne est déduit de
>   la 1ᵉʳ valeur **non nulle** de la plage (et non de la 1ᵉʳ ligne), pour éviter qu'une valeur
>   nulle en tête de lot ne type la colonne en `string` et fasse échouer une valeur typée plus bas.
>   (Corrige aussi un défaut latent du chemin matérialisé.)

### 2. MERGE sans double copie

`DwhWriter.UpsertTableDataAsync` itère désormais par **plage d'index** `(offset, count)` sur la
liste dédupliquée (`MergeBatchAsync`/`MergeBatchInternalAsync` + surcharge
`ConvertToDataTable(data, offset, count)`), au lieu de recréer une sous-liste
`deduped.Skip(i).Take(batchSize).ToList()` à chaque tour (qui était aussi en O(i²) à cause du
`Skip`). Mêmes lots, mêmes lignes.

### 3. Détection des suppressions — sans charger l'ensemble complet du DWH

`DwhWriter.DeleteOrphansAsync` ne matérialise plus l'**ensemble complet des IDs du DWH** dans un
`HashSet`. Le nouveau `StreamOrphanIdsAsync` parcourt la cible en streaming et ne retient que
les **orphelins** (clés absentes de l'ensemble source), avec une comparaison **strictement
identique** à l'ancienne (mêmes clés sérialisées via `SerializeValue`, même join `"|"`, même
`HashSet` ordinal). On passe de deux listes complètes à une seule (source) + streaming cible.

**Choix assumé : streaming plutôt que `NOT EXISTS` pur SQL.** Le brief suggérait un
`DELETE ... NOT EXISTS` côté base. Écarté volontairement car :
- Sage (source) et le DWH (cible) peuvent être sur **deux instances SQL distinctes** → pas de
  jointure inter-bases sans transférer les IDs.
- La comparaison actuelle repose sur des **clés sérialisées C#** (dates tronquées à la seconde,
  GUID en minuscules, comparaison **ordinale**). Reproduire ce format *à l'octet près* en SQL
  (collation, format datetime, culture des décimaux) est fragile et risquerait de **supprimer
  les mauvaises lignes** dans un DWH financier. Le streaming atteint l'objectif mémoire
  (ne plus charger deux listes complètes) **sans aucun changement de sémantique**.

### 4. `SELECT *` → colonnes explicites — **non applicable en l'état**

`SELECT *` n'est utilisé que pour les tables **sans** `CustomQuery` (la majorité des tables
Sage passent déjà par une requête personnalisée qui liste ses colonnes). Or `TableConfig` ne
contient **aucune liste de colonnes** configurable : la seule source serait le schéma de la
table = **toutes** les colonnes (aucune réduction), ou un nouveau champ côté serveur (hors
périmètre de l'agent). Remplacer `SELECT *` ajouterait un aller-retour sans réduire les
colonnes → **laissé tel quel**. À rouvrir si une liste de colonnes utiles devient configurable
côté serveur.

### Impact attendu (Volet A + B)

- Pic RAM d'un cycle dominé par **un seul lot** (`BatchSize`) pour les tables full-reload
  streamées, au lieu de la table entière — de plusieurs Go à quelques dizaines de Mo par table.
- Combiné à `MaxParallelTables=1` (Volet A), le pic global s'effondre.
- Données synchronisées et supprimées **identiques** (aucun changement fonctionnel).
