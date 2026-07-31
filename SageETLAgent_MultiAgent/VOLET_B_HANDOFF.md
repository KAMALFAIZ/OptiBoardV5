# SageETLAgent — Volet B (optimisation mémoire streaming) — Hand-off dev

> Objet : finir et livrer le **Volet B** (réécriture streaming de l'écriture DWH) qui n'a pas
> pu être construit tel quel. Document autonome — voir aussi `OPTIMISATION_MEMOIRE.md`.
> Rédigé le 2026-07-14 après analyse + 3 tentatives de build.

---

## 1. Problème & objectif

Le process `SageETLAgent` consomme **~4 Go de RAM** pendant un cycle de sync (indépendamment
de SQL Server ~16 Go, qui est du cache normal). Cause racine (cf. `OPTIMISATION_MEMOIRE.md`) :

- Chaque table est **entièrement matérialisée en mémoire** (`List<Dictionary<string,object?>>`)
  **puis recopiée dans un `DataTable`** avant `SqlBulkCopy`. Tables volumineuses :
  `Lignes_des_ventes` ~552 k, `Ecritures_Analytiques` ~234 k → ~1–1,5 Go chacune.
- La détection des suppressions charge en plus **deux listes complètes d'IDs** (source + DWH).

**Volet A (config, déjà appliqué)** : `MaxParallelTables=1`, `TurboBatchSize=15000`,
`MergeBatchSize=5000`, et `DeleteDetectionDisabledTables=["Ecritures_Analytiques"]`. Gain
partiel seulement — la matérialisation table entière reste le poste principal.

**Volet B (à finir = ce doc)** : supprimer la matérialisation `DataTable` en **streamant**
la `List<Dictionary>` directement vers `SqlBulkCopy` via un `IDataReader` maison
(`DictionaryListDataReader`), borné à `TurboBatchSize` par lot ; et déplacer la détection des
orphelins **côté SQL** (table temp + anti-jointure) au lieu de HashSets en RAM. Cible : pic
RAM ≈ un seul lot, pas une table entière.

---

## 2. Où est le code Volet B

- **Git stash** : `stash@{0}: On main: WIP avant pull deploiement 2026-07-11`
  (repo `B:\Kasoft-Platform\OptiBoardV5`, branche `main`). C'est la source de vérité.
- **Backup du working tree conflictuel** (résultat du `stash pop` à 3 voies, avec marqueurs) :
  `SageETLAgent_MultiAgent/_stash_wip_backup/` — `ContinuousSyncService.cs`, `DwhWriter.cs`,
  `DeleteDetectionService.cs`, `DictionaryListDataReader.cs`.
- **Helper neuf mis de côté** : `SageETLAgent/Services/DictionaryListDataReader.cs.stashed`
  (le renommer en `.cs` pour l'inclure au build).

Fichiers touchés par le stash : `ContinuousSyncService.cs`, `DwhWriter.cs`,
`DeleteDetectionService.cs` (ignorer `.claude/settings.local.json`, `.license_cache`).

Voir les diffs exacts :
```bash
cd B:/Kasoft-Platform/OptiBoardV5
git stash show -p stash@{0}                                   # patch complet du Volet B
git show stash@{0}:SageETLAgent_MultiAgent/SageETLAgent/Services/DwhWriter.cs   # DwhWriter streaming complet
git diff HEAD stash@{0} -- SageETLAgent_MultiAgent/SageETLAgent/Services/DwhWriter.cs
```

---

## 3. Pourquoi ça ne compile pas tel quel (le vrai blocage)

Le stash est basé sur un commit **antérieur au pull de déploiement**. `HEAD` (`4338cf4`) a
**divergé** depuis : il a gagné des features d'écriture DWH que le stash n'a jamais eues.
Donc ni « prendre le stash en bloc » ni « accepter le côté stash à chaque conflit » ne compile.

### Ce que HEAD a en plus (à conserver — le stash les supprime)
| Membre | Fichier | Rôle |
|---|---|---|
| `DwhWriter.EnsureTableExistsFromColumnsAsync(...)` | DwhWriter.cs | création table cible par colonnes |
| `DwhWriter.PrepareSocieteReplaceAsync(...)` | DwhWriter.cs | chemin « société replace » |
| `DwhWriter.InsertSocieteBatchAsync(...)` | DwhWriter.cs | insert batch société |
| `ContinuousSyncService.ApplyPerformanceConfig(...)` | ContinuousSyncService.cs | lit les knobs perf depuis `appsettings.json` (MaxParallelTables / TurboBatchSize / MergeBatchSize / **DeleteDetectionDisabledTables**) |

Appelés par `SageEtlWorker.cs:53`, `MultiAgentForm.cs:1117,1898` (pour `ApplyPerformanceConfig`)
et par `ContinuousSyncService.cs:713,852,856,868` (pour les 3 méthodes DwhWriter). Si absents →
`CS1061`.

### Ce que le stash introduit (Volet B — à porter dans HEAD)
| Membre | Rôle |
|---|---|
| `DictionaryListDataReader` (nouveau fichier) | `IDataReader` sur `List<Dictionary>` → `SqlBulkCopy` sans copie `DataTable` |
| `DwhWriter.DeleteOrphansViaTempTableAsync(...)` | suppression orphelins via table temp + SQL (au lieu de HashSet RAM) |
| `DwhWriter.BuildCreateTempTableSqlFromSchema(...)` | DDL table temp depuis le schéma cible |
| signatures `MergeBatchInternalAsync(conn, table, **batch**, pks, targetSchema, ct)` | modèle « sous-liste `batch` » au lieu de `(rows, offset, count)` |

Le stash supprime en contrepartie `ConvertToDataTable(...)`, `StreamOrphanIdsAsync(...)`,
`EnsureTargetColumnsExistAsync(...)` et le modèle `(offset,count)`.

### Historique des tentatives (pour ne pas les refaire)
1. **Accept-theirs sur les fichiers conflictuels** → `DwhWriter` entrelacé : les zones
   non-conflit (HEAD) appellent `ConvertToDataTable`/`count`/`rows` alors que les hunks résolus
   utilisent `batch` → `CS0103` (les frontières de conflit coupent des méthodes en deux).
2. **Pur-stash des 3 fichiers** → compile entre eux, mais `ApplyPerformanceConfig` manque → `CS1061`.
3. **ContinuousSyncService HEAD + DwhWriter pur-stash** → HEAD appelle
   `EnsureTableExistsFromColumnsAsync` / `PrepareSocieteReplaceAsync` / `InsertSocieteBatchAsync`
   absents du DwhWriter stash → `CS1061`.

---

## 4. Stratégie recommandée : rebaser Volet B SUR HEAD (ne pas prendre le stash en bloc)

HEAD a avancé ; le stash est en retard. **Repartir de HEAD** et **ré-appliquer les idées
streaming du stash** dans le `DwhWriter` de HEAD, plutôt que l'inverse.

Concrètement, dans `DwhWriter.cs` **de HEAD** :

1. **Ajouter** `Services/DictionaryListDataReader.cs` (le prendre depuis `_stash_wip_backup/`).
2. Dans le chemin `SqlBulkCopy` : **remplacer** `ConvertToDataTable(list, offset, count)` +
   bulk-copy-depuis-DataTable par un `using var reader = new DictionaryListDataReader(batch, CleanColumnName)`
   et `bulkCopy.WriteToServerAsync(reader, ct)`. Itérer par **sous-lot `batch` borné à
   `TurboBatchSize`** (le `List` complet reste en RAM, mais plus de copie `DataTable`).
3. Dans le MERGE incrémental : aligner sur la signature `batch` (voir le stash) — la table temp
   est remplie via le même `DictionaryListDataReader`.
4. **Détection suppressions** : remplacer le HashSet de tous les IDs par
   `DeleteOrphansViaTempTableAsync` (bulk-load des IDs source dans une table temp, `DELETE ...
   WHERE NOT EXISTS`), en gardant la sémantique clé composite (`CompositeKeySeparator = `).
5. **Conserver intacts** `EnsureTableExistsFromColumnsAsync`, `PrepareSocieteReplaceAsync`,
   `InsertSocieteBatchAsync`, `ApplyPerformanceConfig` (HEAD) — les adapter uniquement là où
   ils touchent le chemin d'écriture (ex : la voie « société replace » doit aussi streamer).
6. Vérifier que **`TurboBatchSize` borne réellement le `DataTable`/reader** par lot (c'est là
   le gain RAM promis dans `OPTIMISATION_MEMOIRE.md`).

> Astuce : `git show stash@{0}:.../DwhWriter.cs` donne l'implémentation streaming complète de
> référence ; portez-en la logique méthode par méthode dans le DwhWriter de HEAD.

---

## 5. Build / publish / déploiement

- **SDK** : pas de SDK système sur le serveur. Un SDK 8 local est installé à `C:\dotnet8-sdk`
  (sinon : `dotnet-install.ps1 -Channel 8.0 -InstallDir C:\dotnet8-sdk -NoPath`).
  `$env:DOTNET_ROOT="C:\dotnet8-sdk"; $env:PATH="C:\dotnet8-sdk;$env:PATH"`.
- **NuGet** : aucune source configurée → passer `--source "https://api.nuget.org/v3/index.json"`.
- **Compile-check** : `dotnet build SageETLAgent\SageETLAgent.csproj -c Release --source https://api.nuget.org/v3/index.json`
- **Publish self-contained** :
  `dotnet publish SageETLAgent\SageETLAgent.csproj -c Release -r win-x64 --self-contained true -o binpublish_new --source https://api.nuget.org/v3/index.json`
- **Re-zip pour le téléchargement** : zipper `binpublish_new/` (préfixe `SageETLAgent/`) vers
  `SageETLAgent_MultiAgent/SageETLAgent/SageETLAgent.zip`. Le bouton « Agent Sage » de
  l'UI ETL sert ce zip (`GET /api/admin/etl/agents/download/sage-agent`) et le régénère si
  l'exe est plus récent que le zip. Pas de redémarrage backend nécessaire.

---

## 6. Validation (CRITIQUE — écriture DWH)

Volet B change l'écriture **et** la suppression de lignes DWH. Ne pas livrer sans valider.

1. **Ne pas tester d'abord sur le DWH de prod.** Utiliser une base DWH de test/snapshot, ou
   faire tourner en parallèle et comparer.
2. Pour chaque table, comparer **nombre de lignes + checksum** entre l'agent actuel (HEAD) et
   l'agent Volet B : mêmes lignes insérées / mises à jour / supprimées.
3. Cas à couvrir explicitement :
   - MERGE incrémental (mises à jour) ; `truncate_insert` (remplacement complet) ;
   - **suppression orphelins** : supprimer une ligne côté Sage → vérifier qu'elle disparaît du DWH ;
   - **clés primaires composites** (séparateur ``) ;
   - chemin **société-replace** (`PrepareSocieteReplaceAsync` / `InsertSocieteBatchAsync`).
4. Mesurer le **pic RAM** de `SageETLAgent` : doit chuter vers ~un lot (`TurboBatchSize`),
   plus une table entière. Objectif indicatif : bien sous ~1,5 Go sur `Lignes_des_ventes`.

---

## 7. Rollback

Le build HEAD actuel (fonctionnel) est publié dans `binpublish_new` et un backup existe :
`SageETLAgent/binpublish_old_<timestamp>`. En cas de souci Volet B, republier depuis HEAD
(`git checkout -- Services/*.cs`) ou restaurer le dossier `binpublish_old_*`, puis re-zipper.
Le stash reste intact (`git stash list`).
