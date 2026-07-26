# Informations libres Sage — Synchronisation & exploitation dans les rapports

> **Nature du document** : rapport d'analyse (aucune implémentation).
> **Date** : 2026-07-19
> **Périmètre** : informations libres Sage sur documents (vente / achat / interne), articles, tiers (clients / fournisseurs), et leur usage dans les rapports OptiBoard.

---

## 1. Résumé exécutif (TL;DR)

- Sage laisse **chaque client définir ses propres champs « informations libres »** (champs additionnels paramétrables) sur ses articles, tiers et documents. Le schéma est donc **variable d'une instance à l'autre** : impossible de coder en dur des colonnes fixes.
- OptiBoard **synchronise déjà** ces informations libres via l'agent ETL C#, sous forme **EAV** (Entité-Attribut-Valeur), dans deux tables du DWH :
  - `Info_Libres` → le **catalogue** des champs (quel champ existe, sur quelle table Sage) ;
  - `Info_Libres_Valeurs` → les **valeurs** (une ligne par entité × champ).
- **Mais rien ne les exploite aujourd'hui** : aucune datasource, aucun rapport, aucun dashboard ne lit ces deux tables. Elles sont alimentées puis « dormantes ».
- **Verrou technique principal pour les rapports** : la jointure valeur ↔ entité repose sur `cbMarq` (marqueur de ligne Sage). Cette clé est présente dans le DWH pour les **articles** et les **entêtes de ventes**, mais **absente pour les clients / fournisseurs** et **incertaine pour les lignes de documents**. Tant que la clé n'est pas exposée, les infos libres des tiers restent inexploitables en rapport.
- Ce document décrit le mécanisme réel, le modèle de données, la manière d'exploiter l'EAV en rapport (avec exemples SQL), les écarts, et une trajectoire de mise en valeur **par phases** — sans rien coder.

---

## 2. Le besoin métier

Dans Sage, au-delà des champs standard (code article, prix, intitulé tiers…), l'utilisateur peut **paramétrer des champs supplémentaires** propres à son organisation, appelés **informations libres**. Exemples réels observés dans le code : un champ `CHAUFFEUR` ou `CA` sur la fiche tiers (`F_COMPTET`).

Ces champs peuvent porter sur :

| Entité Sage | Table Sage | Exemples d'informations libres |
|---|---|---|
| Article | `F_ARTICLE` | Norme, certification, coefficient logistique, code douanier interne… |
| Client / Fournisseur | `F_COMPTET` | Chauffeur attitré, zone de tournée, segment commercial, référence contrat… |
| Entête de document (vente / achat / interne) | `F_DOCENTETE` | N° de dossier, canal, transporteur, motif… |
| Ligne de document | `F_DOCLIGNE` | Lot, n° série interne, mention spécifique ligne… |

Le besoin exprimé : **comment ces champs sont-ils synchronisés, et comment les rendre utilisables dans les rapports** (listes, tableaux de bord, pivots), sachant que **chaque client a un jeu de champs différent**.

---

## 3. Qu'est-ce qu'une information libre côté Sage

### 3.1 Deux objets distincts

1. **La définition** (le catalogue) : Sage stocke la liste des champs libres dans la table système **`cbSysLibre`**, avec notamment :
   - `CB_File` : la table parente concernée (`F_ARTICLE`, `F_COMPTET`, `F_DOCENTETE`, `F_DOCLIGNE`…) ;
   - `CB_Name` : le nom du champ libre (qui devient **une colonne physique** ajoutée à la table parente).
2. **La valeur** : chaque champ libre est matérialisé comme **une colonne** directement sur la table parente. Ex. : si `CHAUFFEUR` est défini sur `F_COMPTET`, alors `F_COMPTET` possède une colonne `[CHAUFFEUR]`.

### 3.2 Pourquoi c'est structurellement délicat

- Le **nombre et le nom des colonnes varient par instance client** → un modèle relationnel « colonne fixe » ne tient pas.
- Les colonnes libres sont **typées librement** (texte, numérique, date, booléen) selon le paramétrage Sage.
- La clé de rattachement d'une valeur à sa ligne parente est le **marqueur interne `cbMarq`** de la table parente (identité de ligne Sage).

C'est cette variabilité qui impose une modélisation **EAV** (une ligne = une valeur d'un champ pour une entité), plutôt qu'un miroir colonne-à-colonne.

---

## 4. État actuel de la synchronisation dans OptiBoard

### 4.1 Vue d'ensemble du flux

```
Sage (F_ARTICLE / F_COMPTET / F_DOCENTETE / F_DOCLIGNE …)
        │  colonnes libres décrites dans cbSysLibre
        ▼
Agent ETL C# (SageETLAgent)
   ├─ Config « Informations libres »        → lit cbSysLibre               → DWH.Info_Libres          (catalogue)
   └─ Config « Valeurs informations libres » → extracteur __INFO_LIBRES_VALUES__ → DWH.Info_Libres_Valeurs (EAV)
        ▼
DWH OptiBoard_<CODE>  (2 tables)   ← ⚠ aujourd'hui non consommées par les rapports
```

### 4.2 Les deux configurations ETL

Définies dans `reporting-commercial/backend/sql/sql_jobs/03_insert_etl_config_data.sql` (et `insert_sync_query_data.sql`, `sync_tables.yaml`) :

| Config ETL | `source_query` | `target_table` | Clé primaire | Mode |
|---|---|---|---|---|
| Informations libres | `SELECT [CB_File],[CB_Name] FROM [cbSysLibre]` | `Info_Libres` | — | full |
| Valeurs informations libres | `__INFO_LIBRES_VALUES__` (marqueur spécial) | `Info_Libres_Valeurs` | `CB_File, entity_key, CB_Name` | full |

- **`__INFO_LIBRES_VALUES__`** n'est pas une vraie requête : c'est un **marqueur** qui aiguille l'agent vers un extracteur dédié (`ContinuousSyncService.cs`, test `table.CustomQuery == "__INFO_LIBRES_VALUES__"`).
- Mode **`full`** (truncate/insert à chaque cycle), priorité **high**, batch **50000** (yaml). Pas d'incrémental sur ces tables.

### 4.3 L'extracteur EAV (le cœur du mécanisme)

`SageETLAgent_MultiAgent/SageETLAgent/Services/SageExtractor.cs` → `ExtractInfoLibresValuesAsync()` (≈ ligne 1072). Algorithme :

1. **Découverte** : lit `cbSysLibre` → liste des couples `(CB_File, CB_Name)`.
2. **Regroupement** par table parente (`CB_File`).
3. **Contrôle de schéma** : pour chaque table, interroge `INFORMATION_SCHEMA.COLUMNS` et ne garde que les champs libres **réellement présents** comme colonnes (robustesse : un champ déclaré mais absent est ignoré).
4. **UNPIVOT dynamique** via `CROSS APPLY (VALUES …)` : transforme les N colonnes libres en lignes. Requête générée (simplifiée) :

```sql
SELECT
    N'F_COMPTET'                        AS [CB_File],
    CAST(cbMarq AS VARCHAR(50))         AS [entity_key],   -- ← clé de jointure
    il.field_name                       AS [CB_Name],
    il.field_value                      AS [CB_Value]
FROM [F_COMPTET]
CROSS APPLY (VALUES
    (N'CA',        CAST([CA]        AS NVARCHAR(500))),
    (N'CHAUFFEUR', CAST([CHAUFFEUR] AS NVARCHAR(500)))
) AS il(field_name, field_value)
WHERE il.field_value IS NOT NULL
  AND LTRIM(RTRIM(CAST(il.field_value AS NVARCHAR(500)))) <> '';
```

5. **Sortie** : lignes `{ CB_File, entity_key, CB_Name, CB_Value }`. Les valeurs vides/nulles sont **filtrées** (le DWH ne stocke que les champs renseignés).

Points de conception importants :
- **`entity_key = cbMarq`** de la table parente → c'est ce qui doit permettre de relier une valeur à sa ligne métier.
- Toutes les valeurs sont **coulées en `NVARCHAR(500)`** → le **typage d'origine est perdu** (un montant ou une date deviennent du texte).

### 4.4 Les deux tables du DWH

**`Info_Libres`** — catalogue (DDL statique, `01_create_dwh_database.sql` ≈ ligne 70) :

```sql
CREATE TABLE Info_Libres (
    [id]         INT IDENTITY(1,1) PRIMARY KEY,
    [DB_Id]      INT NOT NULL,
    [DB]         VARCHAR(100) NOT NULL,
    [DB_Caption] NVARCHAR(200) NOT NULL,
    [CB_File]    NVARCHAR(200),   -- table Sage parente
    [CB_Name]    NVARCHAR(200),   -- nom du champ libre
    [SyncDate]   DATETIME DEFAULT GETDATE()
);
```
> ⚠️ **Piège de nommage** : `Info_Libres` ne contient **que les définitions** (quels champs existent), pas les valeurs. Les valeurs sont dans `Info_Libres_Valeurs`.

**`Info_Libres_Valeurs`** — valeurs EAV : **pas de DDL statique**. La table est **auto-créée par l'agent** (`DwhWriter.cs`, `EnsureTableExistsAsync` / `EnsureTableExistsFromColumnsAsync`) à partir des colonnes reçues, avec ajout de la colonne `societe` (multi-société). Colonnes effectives : `CB_File, entity_key, CB_Name, CB_Value` (+ `societe`, + colonnes de traçabilité DWH selon la convention du writer). PK logique = `CB_File + entity_key + CB_Name`.

### 4.5 Constat clé

Un `grep` sur `reporting-commercial/backend/app` (routes / services / datasources) ne renvoie **aucune** référence à `Info_Libres` ni `Info_Libres_Valeurs`. **Conclusion : les données sont synchronisées mais jamais lues.** La brique « synchronisation » est faite ; la brique « exploitation » n'existe pas encore.

---

## 5. Comment les utiliser dans les rapports

Le DWH fournit un modèle **EAV** ; les *builders* OptiBoard (Dashboard, GridView, Pivot) attendent des **datasources « larges »** (colonnes nommées). Il faut donc un **pont** entre les deux. Deux approches, non exclusives.

### 5.1 La jointure de base (valeur ↔ entité)

Le principe : relier `Info_Libres_Valeurs.entity_key` (= `cbMarq` de la table parente) à la **clé équivalente** dans la table métier du DWH.

**Correspondance `CB_File` → table DWH → colonne de jointure** (vérifiée dans `sync_tables.yaml`) :

| `CB_File` (Sage) | Table DWH | Colonne de jointure | Clé présente ? |
|---|---|---|---|
| `F_ARTICLE` | `Articles` | `[Code interne]` (= `F_ARTICLE.cbMarq`) | ✅ oui |
| `F_DOCENTETE` | `Entête_des_ventes` | `[N° interne]` (= `F_DOCENTETE.cbMarq`) | ✅ oui (ventes) |
| `F_DOCENTETE` | `Entête_des_achats` / `Entête_des_documents_internes` | `[N° interne]` | ⚠️ même schéma probable — **à confirmer** |
| `F_COMPTET` | `Clients` / `Fournisseurs` | — | ❌ **absente** (les requêtes exposent `CT_Num` = `[Code client]/[Code fournisseur]`, **pas** `cbMarq`) |
| `F_DOCLIGNE` | `Lignes_des_ventes` / `Lignes_des_achats` | `[N° interne]` = `DL_No` | ❌ **incertaine** (le DWH stocke `DL_No`, l'EAV stocke `cbMarq` — égalité non garantie) |

Exemple (article) — cas où la clé existe :

```sql
SELECT a.[Code Article], a.[Désignation Article], v.[CB_Name], v.[CB_Value]
FROM Articles a
JOIN Info_Libres_Valeurs v
  ON v.CB_File = 'F_ARTICLE'
 AND v.entity_key = CAST(a.[Code interne] AS VARCHAR(50))
 AND v.societe = a.[societe]         -- scoping multi-société
WHERE v.CB_Name = 'CODE_DOUANE';
```

### 5.2 Le pivot EAV → colonnes (pour alimenter un rapport « large »)

Pour qu'un dashboard/grid affiche les infos libres comme des colonnes, il faut **pivoter** l'EAV. Deux techniques :

**a) Agrégation conditionnelle** (souple, tolère les noms dynamiques via SQL généré) :

```sql
SELECT
    a.[Code Article],
    a.[Désignation Article],
    MAX(CASE WHEN v.CB_Name = 'CODE_DOUANE' THEN v.CB_Value END) AS [Code douane],
    MAX(CASE WHEN v.CB_Name = 'NORME'       THEN v.CB_Value END) AS [Norme]
FROM Articles a
LEFT JOIN Info_Libres_Valeurs v
  ON v.CB_File = 'F_ARTICLE'
 AND v.entity_key = CAST(a.[Code interne] AS VARCHAR(50))
 AND v.societe = a.[societe]
GROUP BY a.[Code Article], a.[Désignation Article];
```

**b) `PIVOT` T-SQL** — équivalent, mais liste de colonnes figée (moins adapté au schéma variable sans SQL dynamique).

> **Typage** : `CB_Value` étant du texte, tout calcul nécessite un `TRY_CONVERT` (ex. `TRY_CONVERT(decimal(18,4), v.CB_Value)` pour un montant, `TRY_CONVERT(date, v.CB_Value)` pour une date).

### 5.3 Découverte dynamique des champs (indispensable en multi-client)

Comme les champs varient par client, un rapport générique doit **découvrir** les colonnes disponibles avant de construire le pivot :

```sql
-- Quels champs libres existent pour les articles de cette instance ?
SELECT DISTINCT CB_Name
FROM Info_Libres_Valeurs
WHERE CB_File = 'F_ARTICLE'
ORDER BY CB_Name;
```

C'est ce jeu de noms qui pilote la génération du `CASE WHEN … MAX(…)` (ou du `PIVOT`) — d'où la nécessité d'un **SQL généré** côté datasource plutôt que d'une requête statique.

---

## 6. Écarts et limites identifiés

| # | Écart | Impact | Sévérité |
|---|---|---|---|
| E1 | **Clé de jointure absente sur `Clients`/`Fournisseurs`** (pas de `cbMarq` exposé) | Les infos libres **tiers** (ex. `CHAUFFEUR`) sont synchronisées mais **non rattachables** à une fiche → inexploitables en rapport | 🔴 Élevée |
| E2 | **Clé incertaine sur les lignes de documents** (`DL_No` ≠ `cbMarq` a priori) | Infos libres au niveau ligne potentiellement non jointes | 🟠 Moyenne |
| E3 | **Aucune datasource / rapport ne lit ces tables** | Fonctionnalité invisible pour l'utilisateur final ; les champs n'apparaissent nulle part dans les sélecteurs du builder | 🔴 Élevée |
| E4 | **EAV non consommable directement par les builders** (qui attendent des colonnes) | Nécessite des vues pivotées ou une datasource générée | 🟠 Moyenne |
| E5 | **Typage perdu** (`NVARCHAR(500)`) | Tri/filtre/calcul numériques ou dates faussés sans `TRY_CONVERT` | 🟠 Moyenne |
| E6 | **Schéma variable par client** | Impossible de figer les colonnes ; impose une découverte dynamique | 🟡 Inhérente |
| E7 | **Synchronisation `full` uniquement** | Volumétrie recalculée à chaque cycle (acceptable tant que le volume reste modéré) | 🟢 Faible |
| E8 | **`Entête_des_achats` / `documents_internes` non vérifiés** pour l'alias `cbMarq` | Risque symétrique à E1/E2 sur achats & internes | 🟡 À confirmer |

---

## 7. Recommandations (par phases — sans implémentation)

> Objectif : passer de « données dormantes » à « champs exploitables en rapport », en levant d'abord le verrou de la clé de jointure.

**Phase 0 — Cadrage & vérification (préalable)**
- Confirmer, sur une instance réelle, le contenu de `cbSysLibre` (sur quelles tables les clients définissent réellement des infos libres : tiers ? documents ? articles ?).
- Vérifier l'égalité `cbMarq` vs clé DWH pour `F_DOCLIGNE` (E2) et l'alias `cbMarq` pour `Entête_des_achats`/`documents_internes` (E8).
- Vérifier les colonnes réelles de `Info_Libres_Valeurs` telles qu'auto-créées (présence de `DB_Id`/`societe`).

**Phase 1 — Exposer la clé de jointure manquante (lève E1/E2)**
- Ajouter `cbMarq` (aliasé, ex. `[Clé Sage]`) dans les requêtes source `Clients`, `Fournisseurs` (et lignes de documents si nécessaire), afin de disposer côté DWH de la même clé que `entity_key`.
- Impact : modification de requêtes ETL + colonne DWH additionnelle ; **re-sync full** de ces tables.

**Phase 2 — Vues d'exploitation (lève E4/E5)**
- Créer des **vues pivotées** par entité (ex. `v_Articles_InfoLibres`, `v_Clients_InfoLibres`, `v_Ventes_InfoLibres`) qui : (a) découvrent les `CB_Name`, (b) pivotent l'EAV, (c) gèrent le `societe`/`DB_Id`, (d) exposent des colonnes prêtes à l'emploi (avec `TRY_CONVERT` optionnel).
- Alternative : une **datasource à SQL généré** qui produit le pivot dynamiquement à partir de `Info_Libres`.

**Phase 3 — Rendre visible dans le builder (lève E3)**
- Enregistrer une (ou plusieurs) **datasource template** (`APP_DataSources_Templates`) pointant sur les vues de Phase 2, pour que les champs libres apparaissent dans les sélecteurs (Axe X/Y, filtres, colonnes) des Dashboard/Grid/Pivot builders.

**Phase 4 — Confort & robustesse (optionnel)**
- Déclarer un **type par champ** (métadonnée) pour automatiser le casting et le formatage.
- Envisager un mode incrémental si la volumétrie EAV devient importante (E7).

---

## 8. Annexes

### 8.1 Fichiers de référence

| Rôle | Fichier |
|---|---|
| Extracteur EAV (C#) | `SageETLAgent_MultiAgent/SageETLAgent/Services/SageExtractor.cs` → `ExtractInfoLibresValuesAsync()` |
| Aiguillage marqueur `__INFO_LIBRES_VALUES__` | `SageETLAgent_MultiAgent/SageETLAgent/Services/ContinuousSyncService.cs` |
| Auto-création table valeurs | `SageETLAgent_MultiAgent/SageETLAgent/Services/DwhWriter.cs` (`EnsureTableExists*`) |
| DDL `Info_Libres` (catalogue) | `reporting-commercial/backend/sql/sql_jobs/01_create_dwh_database.sql` |
| Config ETL des 2 tables | `reporting-commercial/backend/sql/sql_jobs/03_insert_etl_config_data.sql`, `insert_sync_query_data.sql` |
| Requêtes source (alias `cbMarq`) | `reporting-commercial/backend/etl/config/sync_tables.yaml` |

### 8.2 Requêtes de diagnostic (lecture seule, à exécuter sur un DWH client)

```sql
-- 1) Catalogue : quels champs libres, sur quelles tables ?
SELECT CB_File, CB_Name, COUNT(*) OVER (PARTITION BY CB_File) AS nb_champs_table
FROM Info_Libres ORDER BY CB_File, CB_Name;

-- 2) Volumétrie des valeurs par entité
SELECT CB_File, CB_Name, COUNT(*) AS nb_valeurs
FROM Info_Libres_Valeurs
GROUP BY CB_File, CB_Name ORDER BY CB_File, nb_valeurs DESC;

-- 3) Taux de rattachement articles (test de la clé de jointure)
SELECT COUNT(DISTINCT v.entity_key) AS cles_eav,
       COUNT(DISTINCT a.[Code interne]) AS cles_appariees
FROM Info_Libres_Valeurs v
LEFT JOIN Articles a
  ON v.CB_File = 'F_ARTICLE'
 AND CAST(a.[Code interne] AS VARCHAR(50)) = v.entity_key
WHERE v.CB_File = 'F_ARTICLE';
```

### 8.3 Glossaire

| Terme | Sens |
|---|---|
| Information libre | Champ additionnel paramétrable par le client dans Sage |
| `cbSysLibre` | Table système Sage listant les définitions de champs libres |
| `CB_File` | Table Sage parente d'un champ libre (`F_ARTICLE`, `F_COMPTET`…) |
| `CB_Name` | Nom du champ libre |
| `cbMarq` | Marqueur d'identité de ligne Sage — sert de clé de rattachement (`entity_key`) |
| EAV | Entité-Attribut-Valeur : modèle « une ligne par champ » adapté aux schémas variables |

---

## 10. Approche #2 — Colonnes larges (au lieu de l'EAV)

L'EAV (`Info_Libres_Valeurs`) explose en volume (UNPIVOT = 1 ligne/champ ;
ALEAFOOD = 1,66 M lignes, dont F_DOCLIGNE 1,54 M). Approche #2 = **tables larges**
(1 ligne/entité, 1 colonne/champ), l'EAV étant **conservé en parallèle**.

**Extracteur agent** — nouveau sentinel `__INFO_LIBRES_WIDE__:<CB_File>`
(`SageExtractor.ExtractInfoLibresWideAsync`) : `SELECT cbMarq AS entity_key + colonnes
libres` (types Sage conservés, PAS d'UNPIVOT). Dispatch dans `ContinuousSyncService`
(hors streaming/diagnostic). **Nécessite l'agent rebuild.**

**Tables larges** (`APP_ETL_Tables_Config` master + published, script
`publish_info_libres_wide.py`) : `IL_Articles` (F_ARTICLE), `IL_Tiers` (F_COMPTET),
`IL_Entetes_Documents` (F_DOCENTETE), `IL_Lignes_Documents` (F_DOCLIGNE),
`IL_Ecritures`, `IL_Comptes_Generaux`, `IL_Comptes_Analytiques`. Auto-créées par l'agent.

**Clés de jointure** (validées sur données) :
| Entité | Jointure base ↔ IL_* |
|---|---|
| Articles | `[Code interne]` = `entity_key` (direct) |
| Entête_des_ventes | `[N° interne]` = `entity_key` (direct, cbMarq confirmé) |
| Clients / Fournisseurs | via `Info_Libres_Cle_Tiers` (CT_Num↔cbMarq) |
| Lignes_des_ventes | via `Info_Libres_Cle_Lignes` (**DL_No↔cbMarq**, additif — car `[N° interne]`=DL_No ≠ cbMarq) |

> `Info_Libres_Cle_Lignes` est du **SQL normal** → tout agent la synchronise (pas besoin
> du rebuild). Elle évite de modifier les extractions financières des lignes.

**DataSources colonnes** (`create_info_libres_wide_ds.py`, catégorie « Informations
libres (colonnes) ») : `DS_IL_ARTICLES`, `DS_IL_VENTES`, `DS_IL_CLIENTS`,
`DS_IL_FOURNISSEURS`, `DS_IL_LIGNES_VENTES` — joignent base ↔ IL_* avec `il.*`
(les champs libres apparaissent comme de **vraies colonnes**, dynamiques par client).

**Déploiement approche #2** :
1. Déployer l'**agent rebuild** (extracteur wide) sur la machine du client.
2. `python scripts/publish_info_libres_wide.py OptiBoard_<CODE>` (publier vers ce client —
   **seulement après** l'agent à jour ; un agent ancien planterait sur le sentinel).
3. `python scripts/create_info_libres_wide_ds.py` (datasources, une fois).
4. Attendre un cycle agent → tables `IL_*` matérialisées → colonnes exploitables.

**Gotcha** : ne PAS publier les tables `IL_*` (sentinel) vers un client dont l'agent
n'est pas à jour → erreur par table à chaque cycle. La publication cliente est **opt-in**
(base en argument du script), master-only par défaut.

## 9. Implémentation réalisée (2026-07-19)

> Tout ce qui suit est **purement additif** : aucune requête d'extraction financière
> existante n'a été modifiée, aucune donnée synchronisée n'a été altérée. Réversible.

### 9.1 Découverte à l'exécution (état réel constaté)

En inspectant l'environnement live (SQL `kasoft`, 14 DWH) :
- La config ETL **est centrale** (`OptiBoard_SaaS.dbo.ETL_Tables_Config`, partagée par tous les tenants).
- **Aucune ligne infos libres n'y était présente** (ni `Info_Libres`, ni `Info_Libres_Valeurs`).
  → C'est la vraie cause pour laquelle l'EAV n'était matérialisé nulle part : la table
  `Info_Libres_Valeurs` n'existe dans **aucun** des 14 DWH. Seul le catalogue `Info_Libres`
  existe dans quelques bases (ex. `OptiBoard_ALEAFOOD` : **55 champs libres** définis).
- Colonnes réelles des tables auto-créées par l'agent = colonnes source **+ `DB_Id` + `societe`**
  (pas de `SyncDate`) — vérifié sur `Info_Libres`.

### 9.2 Ce qui a été livré

**1. Activation de la synchronisation (config ETL centrale)** — `scripts/seed_info_libres_etl_config.py`
Insère (idempotent) 3 lignes dans `ETL_Tables_Config`, **exécuté en live** :

| name | target_table | source | sync |
|---|---|---|---|
| Informations libres | `Info_Libres` | `SELECT [CB_File],[CB_Name] FROM [cbSysLibre]` | full |
| Valeurs informations libres | `Info_Libres_Valeurs` | `__INFO_LIBRES_VALUES__` (extracteur EAV existant) | full |
| Correspondance clé tiers | `Info_Libres_Cle_Tiers` | `SELECT CT_Num…, CAST(cbMarq…) FROM F_COMPTET` (**additif**) | full |

→ statut live : les 3 lignes sont `enabled=1, is_active=1`. L'agent matérialisera ces
tables **à son prochain cycle** (aucune action utilisateur requise).

**2. DataSources d'exploitation (templates centraux)** — `scripts/create_info_libres_ds.py`
Enregistre (idempotent) 6 datasources, **exécuté en live**, catégorie **« Informations libres »** :

| Code | Contenu | Disponible |
|---|---|---|
| `DS_INFO_LIBRES_CATALOGUE` | Champs libres définis (table, entité, nom) | ✅ immédiat (validé : 55 champs sur ALEAFOOD) |
| `DS_INFO_LIBRES_BRUT` | Toutes les valeurs EAV, toutes entités | dès le 1er sync EAV |
| `DS_INFO_LIBRES_ARTICLES` | Articles × champs libres (jointure `[Code interne]`) | dès le 1er sync EAV |
| `DS_INFO_LIBRES_VENTES` | Entêtes ventes × champs libres (jointure `[N° interne]`) | dès le 1er sync EAV |
| `DS_INFO_LIBRES_CLIENTS` | Clients × champs libres (via clé tiers) | dès sync EAV + clé tiers |
| `DS_INFO_LIBRES_FOURNISSEURS` | Fournisseurs × champs libres (via clé tiers) | dès sync EAV + clé tiers |

Format **long** (une ligne par champ) → directement consommable par le **Pivot builder**
(entité en lignes, `Champ` en colonnes, `Valeur` en valeurs), le **GridView** et les listes.
Toutes les colonnes de base ont été **validées** contre un DWH réel.

**3. Seeds pour les nouvelles installations** (cohérence installeur) :
- `backend/sql/insert_sync_query_data.sql` (+ copie `installer/payload/…`) : ajout des lignes EAV + clé tiers.
- `backend/sql/sql_jobs/03_insert_etl_config_data.sql` (+ payload) : ajout de la ligne clé tiers (2c).
- `backend/etl/config/sync_tables.yaml` : ajout de l'entrée « Correspondance clé tiers ».

### 9.3 Migration des instances existantes

La config ETL et les datasources étant **centrales**, les **deux scripts idempotents**
constituent la migration (à lancer une fois par base centrale `OptiBoard_SaaS`) :
```bash
python scripts/seed_info_libres_etl_config.py    # active la synchro
python scripts/create_info_libres_ds.py          # publie les datasources
```
La table `Info_Libres_Cle_Tiers` est **auto-créée par l'agent** au 1er sync (comme
`Info_Libres_Valeurs`) — aucune DDL manuelle requise.

### 9.6 Pipeline ETL réel (correction importante) + déclenchement live

Les agents multi-agents **ne lisent PAS** `ETL_Tables_Config` / `sync_tables.yaml` (cibles
de propagation « C# legacy »). Le pipeline **opératif** est :
```
APP_ETL_Tables_Config (central, master, source_query chiffrée $enc1$)
        --publish-->  APP_ETL_Tables_Published (base CLIENTE)  --lu par-->  agent
```
→ 3e script livré : `scripts/publish_info_libres_tables.py` — ajoute `Info_Libres_Valeurs`
+ `Info_Libres_Cle_Tiers` au master `APP_ETL_Tables_Config` **et** les publie dans
`APP_ETL_Tables_Published` des bases clientes ciblées (défaut : clients dont l'agent est vivant).
Le sentinel `__INFO_LIBRES_VALUES__` est reconnu par l'agent (`ContinuousSyncService.cs:534`).
Le mécanisme de commandes `sync_now` est **hors service** (FK vers `APP_ETL_Agents_OLD`) →
pas de trigger manuel ; les agents synchronisent sur leur intervalle (~5 min).

**Résultat live vérifié (2026-07-19, base `OptiBoard_ALEAFOOD`)** après publication :
- `Info_Libres_Valeurs` matérialisée = **1 664 792 valeurs** (F_DOCLIGNE 1,54 M / 16 champs,
  F_DOCENTETE 120 k, F_COMPTET 2 637, F_ARTICLE 790, F_ECRITUREC, F_COMPTEG, F_COMPTEA).
- `Info_Libres_Cle_Tiers` = **10 536 correspondances**.
- Datasources testés en réel : `DS_INFO_LIBRES_ARTICLES` (« Géré en Tonnage = Oui »),
  `DS_INFO_LIBRES_CLIENTS` via clé tiers (« Catégorie = Café », « ZONE = SETTAT »).

### 9.4 Reste à faire

- **Autres clients** : publier vers leur `APP_ETL_Tables_Published` quand leur agent tourne
  (`python scripts/publish_info_libres_tables.py OptiBoard_XXX`). `OptiBoard_cltAMM` publié,
  matérialisation au prochain cycle de son agent.
- **Achats & lignes de documents** : `Entête_des_achats` et les `Lignes_*` n'exposent pas
  `cbMarq` → non couverts. Le datasource `DS_INFO_LIBRES_BRUT` les montre tout de même en EAV.
  Un rattachement propre nécessiterait d'ajouter la clé dans ces extractions (à évaluer).
- **Typage** : les valeurs restent en texte ; caster (`TRY_CONVERT`) dans les rapports au besoin.

### 9.5 Fichiers créés / modifiés

| Fichier | Action |
|---|---|
| `reporting-commercial/backend/scripts/seed_info_libres_etl_config.py` | créé (activation synchro) |
| `reporting-commercial/backend/scripts/create_info_libres_ds.py` | créé (6 datasources) |
| `reporting-commercial/backend/sql/insert_sync_query_data.sql` | + EAV + clé tiers |
| `reporting-commercial/backend/sql/sql_jobs/03_insert_etl_config_data.sql` | + clé tiers |
| `reporting-commercial/backend/etl/config/sync_tables.yaml` | + clé tiers |
| `installer/payload/backend/sql/insert_sync_query_data.sql` | + EAV + clé tiers |
| `installer/payload/backend/sql/sql_jobs/03_insert_etl_config_data.sql` | + clé tiers |
