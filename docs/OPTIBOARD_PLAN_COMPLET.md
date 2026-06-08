# OptiBoard — Plan Complet : Tests & Implémentation
**Projet :** OptiBoard / OptiSAV  
**Auteur :** Kasoft  
**Date de création :** 23 mai 2026  
**Dernière mise à jour :** 23 mai 2026  

---

## SOMMAIRE

1. [Périmètre & Modules](#1-périmètre--modules)
2. [PHASE 1 — Tests Manuels (26–28 mai)](#2-phase-1--tests-manuels-26-28-mai)
   - [Jour 1 — Infrastructure, Auth, Ventes, Stocks](#jour-1--lundi-26-mai)
   - [Jour 2 — Recouvrement, Achats, Comptabilité](#jour-2--mardi-27-mai)
   - [Jour 3 — Builders, Fiches, Validation finale](#jour-3--mercredi-28-mai)
   - [Template rapport de test](#template-rapport-de-test)
3. [PHASE 2 — Améliorations Techniques (2–13 juin)](#3-phase-2--améliorations-techniques-2-13-juin)
4. [PHASE 3 — Améliorations UX (16–27 juin)](#4-phase-3--améliorations-ux-16-27-juin)
5. [PHASE 4 — Comptabilité Analytique (30 juin–5 juil)](#5-phase-4--comptabilité-analytique-30-juin--5-juil)
6. [PHASE 5 — Paie & Budget (7–11 juil)](#6-phase-5--paie--budget-7-11-juil)
7. [PHASE 6 — Tests finaux & Release (14–18 juil)](#7-phase-6--tests-finaux--release-14-18-juil)
8. [Rapports Manquants — Détail technique](#8-rapports-manquants--détail-technique)
9. [Calendrier Global](#9-calendrier-global)
10. [Checklist Release](#10-checklist-release)

---

## 1. Périmètre & Modules

| Module | Statut | Phase |
|--------|--------|-------|
| Authentification & Setup | ✅ Existant | Tests J1 |
| Ventes & CA | ✅ Existant | Tests J1 |
| Stocks | ✅ Existant | Tests J1 |
| Recouvrement (créances) | ✅ Existant | Tests J2 |
| Dettes Fournisseurs | ✅ Existant | Tests J2 |
| Comptabilité générale | ✅ Existant | Tests J2 |
| Trésorerie | ✅ Existant | Tests J2 |
| Fiche Client / Fournisseur | ✅ Existant | Tests J3 |
| Builders (Dashboard/Pivot/Grid) | ✅ Existant | Tests J3 |
| ETL & Synchronisation Sage | ✅ Existant | Tests J1 |
| **Comptabilité Analytique** | ❌ Manquant | Phase 4 |
| **Paie / Masse salariale** | ❌ Manquant | Phase 5 |
| **Budget vs Réalisé** | ❌ Manquant | Phase 5 |
| **Immobilisations** | ❌ Manquant | Backlog |

---

## 2. PHASE 1 — Tests Manuels (26–28 mai)

> **Durée :** 3 jours × 8h = 24h  
> **Objectif :** Valider les modules existants avant toute implémentation nouvelle  
> **Environnement :** `http://localhost:8084` + base `OptiBoard_SG`

---

### JOUR 1 — Lundi 26 mai
**Thème : Infrastructure + Auth + Ventes + Stocks**

#### Bloc 08h00–10h00 — Infrastructure & ETL

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 1.1 | 08h00 | Service Windows | `sc query OptiBoard-Backend` | Statut `RUNNING` |
| 1.2 | 08h10 | Accès HTTP | Ouvrir `http://localhost:8084` | Page login visible < 3s |
| 1.3 | 08h20 | AppDirectory NSSM | `reg query "HKLM\SYSTEM\CurrentControlSet\Services\OptiBoard-Backend\Parameters" /v AppDirectory` | Valeur = `C:\OptiBoard` sans guillemet final |
| 1.4 | 08h30 | Logs démarrage | Lire `C:\OptiBoard\logs\backend.log` (20 premières lignes) | Aucune ligne `ERROR` |
| 1.5 | 08h45 | Redémarrage service | `nssm restart OptiBoard-Backend` → attendre 30s → `sc query` | Retour à `RUNNING` |
| 1.6 | 09h00 | ETL démarrage | ETL Admin → "Démarrer agent" | Statut `running` → `success` |
| 1.7 | 09h15 | ETL données | `SELECT COUNT(*) FROM OptiBoard_SG.dbo.DashBoard_CA` | > 0 lignes |
| 1.8 | 09h30 | ETL hors ligne | Couper accès Sage → relancer agent | Message erreur clair, pas de crash |
| 1.9 | 09h45 | Logs ETL | Vérifier colonnes `last_run`, `last_status`, `rows_synced` dans `APP_ETL_Agents` | Renseignées après sync |

#### Bloc 09h00–10h30 — Authentification

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 2.1 | 09h00 | Login valide | `dwh_code=SG`, `admin_sg` / mot de passe correct | Token JWT, dashboard affiché |
| 2.2 | 09h10 | Login invalide | Mauvais mot de passe | HTTP 401 + message "Identifiants incorrects" |
| 2.3 | 09h20 | DWH inexistant | `dwh_code=INCONNU` | HTTP 401 ou 404 clair |
| 2.4 | 09h30 | Accès superadmin | Connexion compte superadmin → menu "Gestion DWH" | Visible uniquement pour superadmin |
| 2.5 | 09h40 | Accès refusé | Compte client → URL `/admin/dwh` | Redirection ou 403 |
| 2.6 | 09h50 | Token expiré | Attendre expiration ou modifier exp → action quelconque | Redirection automatique vers login |

#### Bloc 10h45–12h30 — Ventes & CA

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 3.1 | 10h45 | KPIs homepage | Ouvrir HomePage | Tuiles CA N / CA N-1 / Évolution % / Marge non nulles |
| 3.2 | 11h00 | Filtre annuel | Sélectionner "Année courante" | CA correspond à `SUM([Montant HT Net]) WHERE [Valorise CA]='oui'` |
| 3.3 | 11h15 | Filtre mensuel | Sélectionner "Dernier mois" | Données limitées au mois M-1 |
| 3.4 | 11h25 | Filtre global DWH | Changer DWH dans sélecteur global | Toutes les pages rechargées avec nouveau DWH |
| 3.5 | 11h35 | CA par gamme | Onglet "Par Gamme" | Somme toutes gammes = CA global ± 0.01 MAD |
| 3.6 | 11h45 | CA par commercial | Onglet "Par Commercial" | Tri décroissant, noms réels Sage |
| 3.7 | 11h55 | CA par zone | Onglet "Par Zone" | Ventilation par région |
| 3.8 | 12h00 | Top 10 clients | Section "Top Clients" | Classement CA desc, colonnes CA + % |
| 3.9 | 12h10 | Top 10 produits | Section "Top Produits" | Classement CA desc |
| 3.10 | 12h15 | Export Excel | Cliquer "Exporter" | Fichier `.xlsx` téléchargé, données identiques |
| 3.11 | 12h20 | Période vide | Sélectionner période sans ventes | Message "Aucune donnée", pas de crash |
| 3.12 | 12h25 | Drill-down client | Clic sur client → Fiche Client | Redirection `/fiche-client?code=XXX` |

#### Bloc 13h30–16h30 — Stocks + Régressions

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 4.1 | 13h30 | Stock par article | Ouvrir page Stocks | Liste complète, colonne `[Quantité]` visible |
| 4.2 | 13h45 | Stock dormant | Onglet "Stock Dormant" | Articles sans mouvement depuis N jours |
| 4.3 | 14h00 | Rotation stock | Onglet "Rotation" | Taux = CA / Stock moyen, cohérent |
| 4.4 | 14h15 | Mouvements article | Filtrer par article | Historique entrées/sorties complet |
| 4.5 | 14h30 | Stock négatif | Vérifier articles avec `Qté < 0` | Affichés en rouge |
| 4.6 | 14h45 | Alerte stock min | Article sous `[Quantité minimale]` | Indicateur rouge visible |
| 4.7 | 15h00 | Export stock | Cliquer "Exporter" | `.xlsx` avec Réf / Désignation / Qté / Valeur |
| 4.8 | 15h15 | **REG** — Filtre global | Changer DWH → revenir → vérifier données | Aucune donnée de l'ancien DWH |
| 4.9 | 15h30 | **REG** — 0 lignes GridView | Ouvrir GridView sur période sans données | Headers colonnes visibles, message "Aucune donnée" |
| 4.10 | 15h45 | **REG** — Valorise CA | Vérifier `[Valorise CA]='oui'` dans requête CA | Seuls docs facturés dans le CA |
| 4.11 | 16h00 | Liste ventes | Filtre par client → filtre par type document | Uniquement docs du client / type sélectionné |
| 4.12 | 16h20 | Analyse CA/Créances | Tableau CA vs Encours par commercial | DSO cohérent avec balance âgée |
| 4.13 | 16h30 | **FIN J1** | Compléter `bugs_j1.md` | Classifier : Bloquant / Majeur / Mineur |

---

### JOUR 2 — Mardi 27 mai
**Thème : Recouvrement + Achats + Comptabilité**

#### Bloc 08h00–12h00 — Recouvrement & Achats

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 5.1 | 08h00 | Balance âgée totaux | Ouvrir Recouvrement | Somme (0-30j + 31-60j + 61-90j + >90j) = Total encours ± 0.01 |
| 5.2 | 08h20 | Balance âgée commercial | Filtre commercial | Uniquement clients de ce commercial |
| 5.3 | 08h40 | DSO global | Vérifier valeur | = `(Encours / CA) × 30`, cohérent |
| 5.4 | 09h00 | Échéances à échoir | Onglet "À Échoir" | Dates futures uniquement, triées |
| 5.5 | 09h15 | Créances douteuses | Onglet "Douteuses" | Clients ancienneté > 90j |
| 5.6 | 09h30 | Règlements par période | Onglet "Règlements" | Somme = total encaissé période |
| 5.7 | 09h45 | Règlements par mode | Ventilation Chèque / Virement / Espèces | Total modes = total règlements |
| 5.8 | 10h00 | Factures non réglées | Onglet "Non Réglées" | Solde > 0 uniquement |
| 5.9 | 10h15 | KPIs recouvrement | Taux recouvrement % | = Réglé / Dû × 100 |
| 5.10 | 10h30 | Balance âgée fournisseurs | Ouvrir Dettes Fournisseurs | Même logique, sens inversé (dette = crédit) |
| 5.11 | 10h50 | Échéances fournisseurs | Onglet "Échéances" | Dates futures uniquement |
| 5.12 | 11h10 | DPO | Vérifier valeur | = `(Dettes / Achats) × 30` |
| 5.13 | 11h25 | Historique paiements | Filtrer sur 1 fournisseur | Tous règlements triés date desc |
| 5.14 | 11h40 | KPIs achats | Montant engagé / payé / reste | Engagé = Payé + Reste ± 0.01 |
| 5.15 | 11h55 | Cohérence fiche fournisseur | Solde fiche = balance tiers | Écart < 1 MAD sur 3 fournisseurs |

#### Bloc 13h30–16h30 — Comptabilité Générale

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 6.1 | 13h30 | **⚠️ CRITIQUE** Balance équilibrée | Onglet "Balance Générale" | TOTAL DÉBIT = TOTAL CRÉDIT (règle fondamentale) |
| 6.2 | 13h50 | Balance par classe | Onglet "Par Classe" | Classes 1,2,3,4,5,6,7 présentes |
| 6.3 | 14h10 | Journal — filtre journal | Filtrer `JO_Num = VT` | Écritures ventes uniquement |
| 6.4 | 14h25 | Journal — filtre dates | Sélectionner plage réduite | Aucune écriture hors période |
| 6.5 | 14h40 | Cohérence balance tiers clients | Balance tiers clients ↔ Recouvrement balance âgée | Écart < 1 MAD |
| 6.6 | 14h55 | **⚠️ CRITIQUE** Trésorerie | Onglet "Trésorerie" | Solde Final = Solde Initial + Encaissements − Décaissements |
| 6.7 | 15h10 | Détail charges évolution | Onglet "Charges" | Évolution % = `(N − N-1) / N-1 × 100` sur 3 lignes |
| 6.8 | 15h25 | Détail produits évolution | Onglet "Produits" | Idem charges |
| 6.9 | 15h40 | Lettrage | Onglet "Lettrage" | Solde Non Lettré = Total − Lettré sur 2 comptes |
| 6.10 | 15h55 | Analyses mensuelles | Onglet "Analyses" | 12 colonnes mois, totaux annuels corrects |
| 6.11 | 16h10 | KPIs résultat net | Résultat net KPI | = Produits − Charges, cohérent avec balance |
| 6.12 | 16h20 | Échéances clients/fournisseurs | Onglets séparés | Filtre `Type tiers` correct, pas de mélange |
| 6.13 | 16h30 | **FIN J2** | Compléter `bugs_j2.md` | Priorité spéciale si balance déséquilibrée |

---

### JOUR 3 — Mercredi 28 mai
**Thème : Builders + Fiches + Validation finale**

#### Bloc 08h00–10h00 — Fiches Client / Fournisseur

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 7.1 | 08h00 | Fiche client — 3 sections | Ouvrir fiche depuis liste | KPIs + Balance + Top produits visibles |
| 7.2 | 08h20 | Fiche client — cohérence | Solde fiche = balance âgée recouvrement | Écart < 1 MAD sur 3 clients |
| 7.3 | 08h40 | Drill-down depuis Ventes | Clic client dans Top 10 | Redirection `/fiche-client?code=XXX` avec données filtrées |
| 7.4 | 09h00 | Évolution CA client | Graphique évolution 12 mois | 12 points de données, libellés axe X visibles |
| 7.5 | 09h20 | Fiche fournisseur — solde | Ouvrir fiche fournisseur | Solde = `BALANCE_TIERS_FOURNISSEURS` filtré |
| 7.6 | 09h40 | Fiche fournisseur — historique | Onglet achats/paiements | Triés date desc, cohérent avec Dettes |

#### Bloc 10h15–12h30 — Dashboard & Builders

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 8.1 | 10h15 | Dashboard Builder — KPI | Créer widget KPI → choisir DataSource | Dropdown champs peuplé (pas vide) |
| 8.2 | 10h35 | Dashboard — chart_bar | Axe X = Période, Axe Y = CA | Libellés `Jan 26`, `Fév 26`… visibles sur axe X |
| 8.3 | 10h50 | Dashboard — chart_combo | 2 séries Y distinctes (CA + Marge) | Les deux courbes/barres affichées |
| 8.4 | 11h05 | DataSource template | Widget avec `dataSourceCode` sans `dataSourceId` | Dropdown Axe X/Y peuplé |
| 8.5 | 11h20 | Drilldown sur chart | Clic sur barre → filtre autres widgets | Les autres widgets se filtrent |
| 8.6 | 11h35 | Sauvegarde dashboard | Modifier titre + sauvegarder | Dashboard retrouvé après F5 |
| 8.7 | 11h50 | Pivot V2 — config | Glisser Gamme en lignes, Mois en colonnes, CA en valeurs | Tableau croisé correct |
| 8.8 | 12h05 | Pivot V2 — totaux | Vérifier ligne/colonne totaux | Totaux corrects |
| 8.9 | 12h15 | Master Catalog | Bouton "Synchroniser" → pull serveur central | Nouveaux dashboards importés |

#### Bloc 13h30–15h30 — GridView + Spreadsheet

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 9.1 | 13h30 | GridView — tri | Clic entête colonne | Tri asc puis desc |
| 9.2 | 13h45 | GridView — filtre texte | Filtre sur colonne "Tiers" | Résultats filtrés en temps réel |
| 9.3 | 14h00 | GridView — pagination | > 100 lignes → pagination | Navigation pages fonctionnelle |
| 9.4 | 14h15 | GridView — export PDF | Cliquer export PDF | Fichier `.pdf` fidèle à l'écran |
| 9.5 | 14h30 | GridView — export Excel | Cliquer export Excel | Fichier `.xlsx` conforme |
| 9.6 | 14h45 | Spreadsheet — formule | Saisir `=SUM(A1:A12)` | Résultat calculé correctement |
| 9.7 | 15h00 | Spreadsheet — sauvegarde | Modifier + sauvegarder | Retrouvé après rechargement |

#### Bloc 15h15–16h30 — Setup & Validation finale

| # | Heure | Test | Action | Critère PASS |
|---|-------|------|--------|--------------|
| 10.1 | 15h15 | Wizard setup (VM propre) | Lancer wizard 6 étapes complet | DWH créé, admin créé, Sage configurée |
| 10.2 | 15h30 | Vérification `APP_ClientDB` | `SELECT * FROM OptiBoard_SaaS.dbo.APP_ClientDB` | Ligne `(SG, OptiBoard_SG)` présente |
| 10.3 | 15h40 | Vérification `APP_DWH` colonnes | `SELECT COLUMN_NAME FROM sys.columns WHERE object_id=OBJECT_ID('APP_DWH')` | 10 colonnes SSH/OptiBoard présentes |
| 10.4 | 15h50 | **⚠️ CRITIQUE** Login post-setup | Login `admin_sg` sur installation fraîche | Accès dashboard sans erreur |
| 10.5 | 16h00 | **FIN J3** — Synthèse | Compiler `bugs_j1/j2/j3.md` en un seul rapport | Tableau classifié |
| 10.6 | 16h30 | **Décision Release** | PASS tous critiques → GO / sinon NO-GO | Voir checklist section 10 |

---

### Template Rapport de Test

```
╔══════════════════════════════════════════════════════╗
║         RAPPORT DE TEST OPTIBOARD                    ║
║         Date : 28/05/2026 | Version : x.x.x          ║
╚══════════════════════════════════════════════════════╝

RÉSUMÉ EXÉCUTIF
─────────────────────────────────────────
Total cas testés    : ___
PASS                : ___
FAIL Bloquant       : ___  ← Release impossible
FAIL Majeur         : ___  ← Release avec réserve
FAIL Mineur         : ___  ← Backlog

TESTS CRITIQUES (tous doivent être PASS pour GO)
─────────────────────────────────────────
☐ Balance Générale : DÉBIT = CRÉDIT
☐ Trésorerie : Solde Final = Initial ± Flux
☐ Login admin client après setup fresh
☐ ETL sync complète sans crash
☐ CA filtré sur [Valorise CA]='oui'
☐ Headers GridView visibles sur 0 lignes

BUGS TROUVÉS
─────────────────────────────────────────
ID  | Jour | Page                | Description              | Criticité | Assigné
----|------|---------------------|--------------------------|-----------|--------
001 | J1   |                     |                          |           |
002 | J2   |                     |                          |           |
003 | J3   |                     |                          |           |

DÉCISION RELEASE
─────────────────────────────────────────
☐ GO       — Tous critiques PASS, mineurs en backlog
☐ GO avec réserve — Majeurs documentés, workaround connu
☐ NO-GO    — Au moins 1 critique FAIL
```

---

## 3. PHASE 2 — Améliorations Techniques (2–13 juin)

> **Durée :** 2 semaines | **Prérequis :** Résultats tests Phase 1

### Semaine 1 — 2 au 7 juin

#### TÂCHE T-01 — Optimisation requêtes SQL
**Début : 02/06 | Fin : 04/06 | Durée : 8h | Priorité : HAUTE**

**02/06 matin (3h) — Ajout index manquants**

Créer `sql/migrations/011_add_performance_indexes.sql` :

```sql
-- Table DashBoard_CA (la plus requêtée)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_CA_DateBL')
CREATE INDEX IX_CA_DateBL
  ON [dbo].[DashBoard_CA] ([Date BL])
  INCLUDE ([Montant HT Net], [Code client], [Valorise CA]);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_CA_Client_DateBL')
CREATE INDEX IX_CA_Client_DateBL
  ON [dbo].[DashBoard_CA] ([Code client], [Date BL])
  INCLUDE ([Montant HT Net], [Coût]);

-- Table Echeances_Ventes (recouvrement)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Ech_DateEch')
CREATE INDEX IX_Ech_DateEch
  ON [dbo].[Echeances_Ventes] ([Date échéance])
  INCLUDE ([Montant], [Code tiers], [Soldé]);

-- Table Ecritures_Comptables (comptabilité)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_EC_DateCG')
CREATE INDEX IX_EC_DateCG
  ON [dbo].[Ecritures_Comptables] ([EC_Date], [CG_Num])
  INCLUDE ([EC_Montant], [EC_Sens]);
```

**02/06 après-midi (3h) — Optimiser `query_templates.py`**
- Remplacer `SELECT *` par colonnes explicites dans `CHIFFRE_AFFAIRES_GLOBAL`
- Ajouter `WITH (NOLOCK)` sur les lectures reporting
- Convertir les paramètres `?` en `:param` nommés

**03/06 (2h) — Vue matérialisée KPIs dashboard**

```sql
CREATE OR ALTER VIEW [dbo].[V_KPI_Dashboard]
WITH SCHEMABINDING AS
SELECT
  YEAR([Date BL]) AS Annee,
  MONTH([Date BL]) AS Mois,
  SUM([Montant HT Net]) AS CA_HT,
  SUM([Coût]) AS Cout,
  COUNT_BIG(*) AS Nb_Lignes
FROM [dbo].[DashBoard_CA]
WHERE [Valorise CA] = 'oui'
GROUP BY YEAR([Date BL]), MONTH([Date BL]);
GO
CREATE UNIQUE CLUSTERED INDEX IX_KPI_Dash ON [dbo].[V_KPI_Dashboard] (Annee, Mois);
```

**Cible :** Endpoints > 2s réduits à < 800ms

---

#### TÂCHE T-02 — Stratégie de cache in-memory
**Début : 04/06 | Fin : 05/06 | Durée : 4h**

Créer `reporting-commercial/backend/app/services/cache_service.py` :

```python
from datetime import datetime, timedelta
import hashlib, json

_cache: dict = {}

def cache_get(key: str):
    entry = _cache.get(key)
    if entry and datetime.now() < entry["expires"]:
        return entry["data"]
    return None

def cache_set(key: str, data, ttl_minutes: int = 15):
    _cache[key] = {
        "data": data,
        "expires": datetime.now() + timedelta(minutes=ttl_minutes)
    }

def cache_key(*args) -> str:
    return hashlib.md5(json.dumps(args, default=str).encode()).hexdigest()

def cache_invalidate_prefix(prefix: str):
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]
```

**TTL par type de données :**

| Endpoint | TTL | Raison |
|----------|-----|--------|
| KPIs homepage | 15 min | Données stables intraday |
| Balance générale | 30 min | Màj comptable peu fréquente |
| Balance âgée | 10 min | Sensible aux règlements |
| Stocks | 5 min | Mouvements fréquents |
| ETL status | 30 sec | Temps réel requis |

Invalider le cache après chaque ETL réussi (`etl_agents.py`) :
```python
from ..services.cache_service import cache_invalidate_prefix
cache_invalidate_prefix(dwh_code)
```

---

#### TÂCHE T-03 — ETL incrémental + tables Analytique
**Début : 05/06 | Fin : 07/06 | Durée : 7h | Priorité : HAUTE**

**Sync incrémentale (`SageExtractor.cs`) :**
```csharp
// Extraire uniquement les lignes modifiées depuis le dernier run
var lastRun = GetLastSuccessfulRun(agentId);
var query = $@"SELECT * FROM {tableName}
               WHERE cbModification > '{lastRun:yyyy-MM-dd HH:mm:ss}'";
// Puis MERGE (UPSERT) dans la table DWH cible
```

**Ajouter tables Analytique dans `03_insert_etl_config_data.sql` :**
```sql
INSERT INTO APP_ETL_Tables (dwh_code, table_source, table_dest, actif, priorite)
VALUES
  ('*', 'F_ANALCPTA',  'Axes_Analytiques',     1, 50),
  ('*', 'F_CENTREAN',  'Centres_Analytiques',  1, 51),
  ('*', 'F_ECRITUREA', 'Ecritures_Analytiques',1, 52),
  ('*', 'F_BUDGETA',   'Budgets_Analytiques',  1, 53);
```

**Dashboard monitoring ETL (`ETLAdmin.jsx`) :**
Ajouter par table : dernière sync | nb lignes | durée | statut (✅ OK / ⚠️ Retard / ❌ Erreur)

---

### Semaine 2 — 9 au 13 juin

#### TÂCHE T-04 — Supervision & health check
**Début : 09/06 | Fin : 10/06 | Durée : 5h**

Ajouter dans `run.py` :
```python
@app.get("/api/health")
async def health_check():
    checks = {}
    try:
        execute_central("SELECT 1")
        checks["db_centrale"] = "ok"
    except:
        checks["db_centrale"] = "error"
    last_etl = execute_central("SELECT MAX(last_run) FROM APP_ETL_Agents")[0][0]
    delay_h = (datetime.now() - last_etl).seconds // 3600
    checks["etl_delay_hours"] = delay_h
    checks["etl_status"] = "ok" if delay_h < 24 else "warning"
    status = "ok" if all(v in ["ok","warning"] for v in checks.values()) else "degraded"
    return {"status": status, **checks}
```

Alertes automatiques (`alerts.py`) :
- ETL sans sync > 24h → email admin
- Balance Débit ≠ Crédit → alerte critique
- Endpoint > 5s → log warning

---

#### TÂCHE T-05 — Documentation technique
**Début : 11/06 | Fin : 12/06 | Durée : 5h**

Mettre à jour `CLAUDE.md` avec :
- Schémas nouvelles tables (analytique, cache)
- Diagramme flux ETL incrémental
- Runbook : démarrage / arrêt / rebuild complet
- Top 10 erreurs courantes + fix

---

## 4. PHASE 3 — Améliorations UX (16–27 juin)

#### TÂCHE U-01 — Refonte visualisations
**Début : 16/06 | Fin : 17/06 | Durée : 6h**

Vérifier `resolvePeriodKey` + `formatPeriodLabel` (voir CLAUDE.md) sur **toutes** les pages :
- `PivotViewerV2.jsx`
- `Ventes.jsx`
- `Comptabilite.jsx`
- `Recouvrement.jsx`

Palette couleurs à harmoniser :
```js
const COLORS = {
  primary:  '#2563eb',
  success:  '#16a34a',
  danger:   '#dc2626',
  warning:  '#ea580c',
  neutral:  '#6b7280',
}
```

---

#### TÂCHE U-02 — Filtres persistants
**Début : 18/06 | Fin : 19/06 | Durée : 5h**

Dans `GlobalFilterContext.jsx` :
```js
useEffect(() => {
  localStorage.setItem('optiboard_filters', JSON.stringify({
    dwhCode, periode, commercial, zone
  }))
}, [dwhCode, periode, commercial, zone])

// Au chargement :
const saved = JSON.parse(localStorage.getItem('optiboard_filters') || '{}')
```

État vide amélioré (toutes les pages) :
```jsx
{data.length === 0 && (
  <div className="text-center py-16 text-gray-400">
    <BarChart2 className="mx-auto mb-3 opacity-30" size={48} />
    <p className="text-lg font-medium">Aucune donnée pour cette période</p>
    <p className="text-sm mt-1">Élargissez la plage de dates ou vérifiez l'ETL</p>
  </div>
)}
```

---

#### TÂCHE U-03 — Nouveaux KPIs homepage
**Début : 23/06 | Fin : 25/06 | Durée : 6h**

| KPI | Formule | Source SQL |
|-----|---------|-----------|
| Taux de marge brute | `(CA − Coût) / CA × 100` | `DashBoard_CA` |
| DPO fournisseurs | `(Dettes / Achats) × 30` | `Echeances_Fournisseurs` |
| Taux recouvrement mois | `Réglé M / Dû M × 100` | `Echeances_Ventes` |
| Stock couverture (jours) | `Stock / (CA / 30)` | `Stock` + `CA` |
| Résultat net estimé | `Produits − Charges` | `Balance_Generale` |

---

## 5. PHASE 4 — Comptabilité Analytique (30 juin–5 juil)

> **Prérequis :** Tables Sage `F_ECRITUREA`, `F_CENTREAN` synchronisées (TÂCHE T-03)

#### TÂCHE AN-01 — Tables DWH analytiques
**Début : 30/06 | Fin : 01/07 | Durée : 4h**

Ajouter dans `sql/002_create_dwh_tables.sql` :
```sql
-- Axes analytiques
CREATE TABLE [dbo].[Axes_Analytiques] (
    [cbIndice]    TINYINT PRIMARY KEY,
    [cbIntitule]  NVARCHAR(200),
    [cbActif]     BIT DEFAULT 1
);

-- Centres analytiques
CREATE TABLE [dbo].[Centres_Analytiques] (
    [CA_Num]      NVARCHAR(20) PRIMARY KEY,
    [CA_Intitule] NVARCHAR(200),
    [cbIndice]    TINYINT,
    [CA_Niv]      TINYINT
);

-- Écritures analytiques
CREATE TABLE [dbo].[Ecritures_Analytiques] (
    [EA_Num]      INT IDENTITY PRIMARY KEY,
    [EA_DateEcr]  DATE,
    [CA_Num]      NVARCHAR(20),
    [CG_Num]      NVARCHAR(20),
    [EA_Montant]  DECIMAL(18,2),
    [EA_Sens]     TINYINT,   -- 1=Débit, 2=Crédit
    [JO_Num]      NVARCHAR(10),
    [EC_Num]      INT,
    [EA_Libelle]  NVARCHAR(200)
);
CREATE INDEX IX_EA_DateCA ON [dbo].[Ecritures_Analytiques] ([EA_DateEcr], [CA_Num]);

-- Budgets analytiques
CREATE TABLE [dbo].[Budgets_Analytiques] (
    [id]          INT IDENTITY PRIMARY KEY,
    [exercice]    INT,
    [mois]        TINYINT,
    [CA_Num]      NVARCHAR(20),
    [CG_Num]      NVARCHAR(20),
    [montant]     DECIMAL(18,2)
);
```

**Requêtes à ajouter dans `query_templates.py` :**
```python
ANALYTIQUE_PAR_CENTRE = """
SELECT
    ce.[CA_Num]      AS Code_Centre,
    ce.[CA_Intitule] AS Centre,
    SUM(CASE WHEN ea.[EA_Sens]=1 THEN ea.[EA_Montant] ELSE 0 END) AS Debit,
    SUM(CASE WHEN ea.[EA_Sens]=2 THEN ea.[EA_Montant] ELSE 0 END) AS Credit,
    SUM(CASE WHEN ea.[EA_Sens]=1 THEN ea.[EA_Montant]
             ELSE -ea.[EA_Montant] END)                           AS Solde
FROM [dbo].[Ecritures_Analytiques] ea
JOIN [dbo].[Centres_Analytiques] ce ON ea.[CA_Num] = ce.[CA_Num]
WHERE ea.[EA_DateEcr] BETWEEN :date_debut AND :date_fin
GROUP BY ce.[CA_Num], ce.[CA_Intitule]
ORDER BY Solde DESC
"""

ANALYTIQUE_EVOLUTION_MENSUELLE = """
SELECT
    FORMAT(ea.[EA_DateEcr], 'yyyy-MM')  AS Periode,
    ce.[CA_Intitule]                    AS Centre,
    SUM(ea.[EA_Montant])                AS Montant
FROM [dbo].[Ecritures_Analytiques] ea
JOIN [dbo].[Centres_Analytiques] ce ON ea.[CA_Num] = ce.[CA_Num]
WHERE ea.[EA_DateEcr] BETWEEN :date_debut AND :date_fin
GROUP BY FORMAT(ea.[EA_DateEcr], 'yyyy-MM'), ce.[CA_Intitule]
ORDER BY Periode, Centre
"""

ANALYTIQUE_BUDGET_VS_REALISE = """
SELECT
    ce.[CA_Intitule]       AS Centre,
    COALESCE(b.montant, 0) AS Budget,
    COALESCE(SUM(ea.[EA_Montant]), 0) AS Realise,
    COALESCE(SUM(ea.[EA_Montant]), 0) - COALESCE(b.montant, 0) AS Ecart,
    CASE WHEN COALESCE(b.montant, 0) > 0
         THEN COALESCE(SUM(ea.[EA_Montant]), 0) / b.montant * 100
         ELSE NULL END AS Taux_Realisation
FROM [dbo].[Centres_Analytiques] ce
LEFT JOIN [dbo].[Ecritures_Analytiques] ea
       ON ea.[CA_Num] = ce.[CA_Num]
      AND ea.[EA_DateEcr] BETWEEN :date_debut AND :date_fin
LEFT JOIN (
    SELECT [CA_Num], SUM([montant]) AS montant
    FROM [dbo].[Budgets_Analytiques]
    WHERE [exercice] = :exercice
    GROUP BY [CA_Num]
) b ON b.[CA_Num] = ce.[CA_Num]
GROUP BY ce.[CA_Intitule], b.montant
ORDER BY Centre
"""
```

---

#### TÂCHE AN-02 — Page Comptabilité Analytique (Frontend)
**Début : 02/07 | Fin : 05/07 | Durée : 8h**

Nouveau fichier `frontend/src/pages/ComptabiliteAnalytique.jsx` avec 4 onglets :

| Onglet | Composant | DataSource |
|--------|-----------|-----------|
| Centres de coûts | Tableau Centre / Débit / Crédit / Solde | `DS_ANALYTIQUE_CENTRES` |
| Ventilation charges | BarChart empilé par centre | `DS_ANALYTIQUE_EVOLUTION` |
| Résultat par activité | Tableau Produits − Charges = Résultat | `DS_ANALYTIQUE_CENTRES` |
| Budget vs Réalisé | Tableau comparatif 4 colonnes | `DS_ANALYTIQUE_BUDGET` |

Route dans `App.jsx` :
```jsx
<Route path="/comptabilite-analytique" element={<ComptabiliteAnalytique />} />
```

---

## 6. PHASE 5 — Paie & Budget (7–11 juil)

#### TÂCHE P-01 — Rapport Masse Salariale
**Début : 07/07 | Fin : 08/07 | Durée : 5h**

Requête à ajouter dans `query_templates.py` :
```python
MASSE_SALARIALE_MENSUELLE = """
SELECT
    FORMAT(e.[EC_Date], 'yyyy-MM')   AS Periode,
    SUM(CASE WHEN LEFT(e.[CG_Num],3) IN ('641','642')
             THEN e.[EC_Montant] ELSE 0 END)  AS Salaires_Bruts,
    SUM(CASE WHEN LEFT(e.[CG_Num],3) = '645'
             THEN e.[EC_Montant] ELSE 0 END)  AS Charges_Patronales,
    SUM(CASE WHEN LEFT(e.[CG_Num],3) = '646'
             THEN e.[EC_Montant] ELSE 0 END)  AS Autres_Charges,
    SUM(e.[EC_Montant])              AS Total_Charges_Personnel
FROM [dbo].[Ecritures_Comptables] e
WHERE LEFT(e.[CG_Num], 2) = '64'
  AND e.[EC_Date] BETWEEN :date_debut AND :date_fin
GROUP BY FORMAT(e.[EC_Date], 'yyyy-MM')
ORDER BY Periode
"""

RATIO_MASSE_SALARIALE_CA = """
SELECT
    FORMAT(e.[EC_Date], 'yyyy-MM') AS Periode,
    SUM(e.[EC_Montant])            AS Masse_Salariale,
    ca.CA_HT,
    CASE WHEN ca.CA_HT > 0
         THEN SUM(e.[EC_Montant]) / ca.CA_HT * 100
         ELSE NULL END             AS Ratio_MS_CA
FROM [dbo].[Ecritures_Comptables] e
JOIN (
    SELECT FORMAT([Date BL],'yyyy-MM') AS Periode,
           SUM([Montant HT Net]) AS CA_HT
    FROM [dbo].[DashBoard_CA]
    WHERE [Valorise CA]='oui'
    GROUP BY FORMAT([Date BL],'yyyy-MM')
) ca ON ca.Periode = FORMAT(e.[EC_Date],'yyyy-MM')
WHERE LEFT(e.[CG_Num], 2) = '64'
  AND e.[EC_Date] BETWEEN :date_debut AND :date_fin
GROUP BY FORMAT(e.[EC_Date], 'yyyy-MM'), ca.CA_HT
ORDER BY Periode
"""
```

---

#### TÂCHE B-01 — Module Budget vs Réalisé
**Début : 09/07 | Fin : 11/07 | Durée : 8h**

Table `APP_Budgets` dans la base DWH client :
```sql
CREATE TABLE [dbo].[APP_Budgets] (
    [id]            INT IDENTITY PRIMARY KEY,
    [exercice]      INT NOT NULL,
    [mois]          TINYINT NOT NULL,       -- 1 à 12
    [axe]           NVARCHAR(50) NOT NULL,  -- 'CA', 'CHARGES', 'MARGE', 'PAIE'
    [code_poste]    NVARCHAR(50),
    [libelle_poste] NVARCHAR(200),
    [montant_budget] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [created_at]    DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Budget UNIQUE (exercice, mois, axe, code_poste)
);
```

Interface de saisie budget : grille `mois × poste` dans `Settings.jsx`

Rapport comparatif : croiser `APP_Budgets` avec `DETAIL_CHARGES` / `CHIFFRE_AFFAIRES_GLOBAL`

---

## 7. PHASE 6 — Tests finaux & Release (14–18 juil)

| Date | Action |
|------|--------|
| 14/07 | Tests de non-régression sur les modules modifiés |
| 15/07 | Tests des 4 nouveaux modules (Analytique, Paie, Budget, Supervision) |
| 16/07 | `build_protected.bat` + `npm run build` |
| 17/07 | `build_installer.bat` → `OptiBoard-Setup-x.x.x.exe` |
| 17/07 | Test install sur VM propre (wizard + login + ETL) |
| 18/07 | **Release** |

---

## 8. Rapports Manquants — Détail Technique

### 8.1 Comptabilité Analytique

| Rapport | Table Sage source | Priorité |
|---------|------------------|----------|
| Centres de coûts (Débit/Crédit/Solde) | `F_ECRITUREA` + `F_CENTREAN` | 🔴 Haute |
| Ventilation charges par centre | `F_ECRITUREA` | 🔴 Haute |
| Résultat par activité (P&L analytique) | `F_ECRITUREA` | 🔴 Haute |
| Budget analytique vs Réalisé | `F_BUDGETA` | 🟠 Moyenne |
| Évolution mensuelle par centre | `F_ECRITUREA` | 🟡 Basse |

### 8.2 Paie / Masse Salariale

| Rapport | Source | Priorité |
|---------|--------|----------|
| Masse salariale mensuelle | Journal paie (comptes 641x) | 🔴 Haute |
| Charges sociales (CNSS/AMO/CIMR/IR) | Comptes 645x | 🔴 Haute |
| Ratio masse salariale / CA | Paie + Ventes | 🟠 Moyenne |
| Effectif par département | `F_EMPLOYE` (si Sage Paie) | 🟠 Moyenne |

### 8.3 Budget vs Réalisé

| Rapport | Priorité |
|---------|----------|
| Suivi budgétaire global | 🔴 Haute |
| Budget CA par commercial | 🔴 Haute |
| Budget charges par poste | 🟠 Moyenne |
| Forecast fin d'année | 🟠 Moyenne |

### 8.4 Immobilisations (Backlog)

| Rapport | Table Sage | Priorité |
|---------|-----------|----------|
| État des immobilisations | `F_IMMOB` | 🟡 Basse |
| Dotations annuelles | `F_IMMOB` | 🟡 Basse |
| Plan d'amortissement | `F_IMMOB` | 🟡 Basse |

---

## 9. Calendrier Global

```
Mai 2026
─────────────────────────────────────────────
26–28 mai    ████████  PHASE 1 : Tests manuels (3 jours)

Juin 2026
─────────────────────────────────────────────
02–07 juin   ████████  PHASE 2a : Optimisation technique (requêtes, cache, ETL)
09–13 juin   █████     PHASE 2b : Supervision + Documentation

16–20 juin   █████     PHASE 3a : UX refonte + filtres persistants
23–27 juin   █████     PHASE 3b : Nouveaux KPIs homepage

Juillet 2026
─────────────────────────────────────────────
30 juin–5 juil  ██████  PHASE 4 : Comptabilité Analytique
07–11 juil      █████   PHASE 5 : Paie + Budget
14–18 juil      █████   PHASE 6 : Tests finaux + Release

DATES CLÉS
─────────────────────────────────────────────
28/05  Rapport de test Phase 1 + décision GO/NO-GO
07/06  Index SQL + cache + ETL incrémental opérationnels
13/06  Supervision + documentation technique
27/06  Nouveaux KPIs + UX améliorée
05/07  Module Comptabilité Analytique live
11/07  Module Paie + Module Budget
18/07  Release packagée OptiBoard-Setup-x.x.x.exe
```

---

## 10. Checklist Release

### Obligatoire (bloquant si KO)
- [ ] Balance Générale : DÉBIT = CRÉDIT sur données réelles
- [ ] Trésorerie : Solde Final correct sur 3 banques
- [ ] Login admin client après setup fresh sur VM propre
- [ ] ETL sync complète sans crash (Sage disponible + Sage hors ligne)
- [ ] `[Valorise CA]='oui'` filtré correctement dans tous les CA
- [ ] `build_protected.bat` terminé sans erreur (Cython)
- [ ] `npm run build` terminé sans erreur
- [ ] `dist_client/` et `dist/` à jour (vérifier dates de modification)
- [ ] Wizard 6 étapes complet sur VM propre : DWH créé + admin créé + Sage configurée
- [ ] `APP_ClientDB` renseignée : `(dwh_code, db_name)` présent
- [ ] `APP_DWH` : 10 colonnes SSH/OptiBoard présentes

### Conseillé (release avec réserve si KO)
- [ ] Taille finale installer ≈ 109 MB
- [ ] Temps de réponse endpoints principaux < 2s
- [ ] GridView : headers visibles sur 0 lignes
- [ ] Charts : libellés axe X visibles (`Jan 26`, `Fév 26`…)
- [ ] Export Excel fonctionnel (Ventes, Stocks, GridView)
- [ ] Master Catalog : sync depuis `central.kasoft.ma` OK
- [ ] Test `/api/health` retourne `{"status": "ok"}`

### Nouveaux modules (si inclus dans cette release)
- [ ] Tables `Ecritures_Analytiques` et `Centres_Analytiques` peuplées après ETL
- [ ] Page `/comptabilite-analytique` : 4 onglets fonctionnels
- [ ] Budget vs Réalisé : saisie budget + comparatif affiché
- [ ] Masse salariale mensuelle : données issues comptes 64x

---

*Document généré le 23/05/2026 — OptiBoard / Kasoft*
