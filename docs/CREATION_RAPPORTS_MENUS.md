# OptiBoard — Création d'un rapport, d'un menu et fonctionnalités

> Descriptif fonctionnel à l'usage des administrateurs et concepteurs de rapports.
> Couvre la **création de rapports**, la **création de menus** et les **fonctionnalités** associées.
> _Hors périmètre : la synchronisation depuis le serveur maître (catalogue master / publication / récupération base maître)._

---

## 1. Concepts de base

OptiBoard repose sur trois briques qui s'articulent :

```
   Source de données  ──►  Rapport  ──►  Menu
   (la requête SQL)        (la mise        (le point d'accès
                            en forme)        dans l'application)
```

| Brique | Rôle | Où la créer |
|---|---|---|
| **Source de données** | Définit *quelles données* sont remontées (requête SQL + paramètres) | `Admin ▸ Sources de données` |
| **Rapport** | Met en forme les données (graphiques, tableaux, croisés) | Les *Builders* (Dashboard, GridView, Pivot, Tableur) |
| **Menu** | Rend le rapport accessible dans la navigation | `Gestion des Menus` |

> Un rapport **n'apparaît pas** automatiquement dans l'application : il faut lui créer une entrée de menu (étape 3).

---

## 2. Les sources de données (prérequis du rapport)

Une **source de données unifiée** alimente tous les rapports. Deux origines possibles :

- **Modèle (template)** — source partagée, définie dans `Admin ▸ Sources de données` (page `DataSourceTemplates`). Identifiée par un **code** (ex. `DS_VENTES_MENSUELLES`).
- **Source locale** — requête SQL créée à la volée depuis un builder (bouton **« + Créer Source »**), propre au DWH du client.

### Anatomie d'une source

| Champ | Description |
|---|---|
| **Code** | Identifiant unique (ex. `DS_STK_EVOLUTION_MENSUELLE`) |
| **Nom** | Libellé lisible |
| **Catégorie** | `ventes`, `stocks`, `recouvrement`, `finance`, `rh`, `dashboard`, `custom` |
| **Requête (query_template)** | SQL avec paramètres `@dateDebut`, `@societe`, etc. |
| **Paramètres** | Liste JSON : `[{ name, type, label, default, required }]` |

### Paramètres dynamiques

Une source peut exposer des paramètres (période, société…). Dans les builders, des **présélections de période** sont proposées : `Année en cours`, `Mois en cours`, `Trimestre`, `Année précédente`, avec boutons **Réinitialiser** et **Appliquer**.

> **Champs vides dans les sélecteurs ?** Si la source n'existe pas dans `APP_DataSources_Templates`, l'appel `/fields` renvoie une liste vide et tous les menus déroulants restent vides. Il faut alors insérer la source manquante (voir `CLAUDE.md ▸ Dashboard Builder ▸ FieldSelect`).

---

## 3. Création d'un rapport

OptiBoard propose **4 types de rapports**, chacun avec son builder et son visualiseur.

| Type | Builder | À quoi ça sert |
|---|---|---|
| **Tableau de bord** (Dashboard) | `Builder ▸ Dashboards` | Indicateurs (KPI), graphiques et widgets interactifs |
| **Grille** (GridView) | `Builder ▸ GridView` | Tableau de données : tri, filtre, regroupement, totaux, export |
| **Tableau croisé** (Pivot) | `Builder ▸ Pivot` | Croisement Lignes × Colonnes avec agrégations |
| **Tableur** (Spreadsheet) | `Builder ▸ Tableur` | Classeur multi-feuilles type Excel |

Stockage SQL (base client `OptiBoard_<CODE>`) :
`APP_Dashboards` · `APP_GridViews` · `APP_Pivots_V2` · `spreadsheet_sheets`.

---

### 3.1 Tableau de bord (Dashboard)

Tableau composé de **widgets** disposés sur une grille, avec filtres globaux et rafraîchissement automatique.

**Étapes :**

1. **Créer** — `Builder ▸ Dashboards` → **« + Nouveau »** → saisir le **Nom**, choisir l'**Application** (Gestion Commerciale, Comptabilité, Paie, Trésorerie) → **Créer**.
2. **Ajouter des widgets** — **« + Ajouter Widget »**, puis choisir parmi les 16 types groupés :
   - **Indicateurs** : KPI, KPI Comparé, Jauge, Progression, Sparkline
   - **Graphiques** : Barres, Barres empilées, Lignes, Combo, Camembert, Aire, Entonnoir, Treemap
   - **Données** : Tableau
   - **Divers** : Texte, Image
3. **Configurer chaque widget** (panneau de droite) :
   - **Général** : titre, description, **source de données**
   - **Données** : **Axe X** (catégorie/période), **Axe Y** (numérique), **fonction d'agrégation** (SUM, AVG, COUNT, MIN, MAX, FIRST, LAST), série, tri, regroupement temporel (jour/semaine/mois/trimestre/année)
   - **Mise en forme** : format des nombres, **seuils de couleur conditionnels** (ex. > 100K = vert)
   - **Documentation** : objectif, champs, formule, avantage métier
4. **Aperçu / Éditer** — basculer en lecture seule pour vérifier, revenir en édition.
5. **Sauvegarder**.

**Points clés** : intervalle d'auto-rafraîchissement, filtres globaux (`dateDebut`, `dateFin`, `societe`, `commercial`, `gamme`), visibilité Public/Privé, affectation à une Application.

> **Libellés d'axe X** : pour les périodes, OptiBoard détecte un champ `YYYY-MM` (ex. `Mois`) et formate en `« Jan 25 »`. Voir `CLAUDE.md ▸ Affichage libellés axe X`.

---

### 3.2 Grille (GridView)

Tableau de données riche (AG Grid) : colonnes configurables, tri, filtres, regroupement multi-niveaux, totaux, pagination, export Excel et **préférences sauvegardées par utilisateur**.

**Étapes :**

1. **Créer** — `Builder ▸ GridView` → **« + Nouvelle grille »** → **Nom** (+ Application) → **Créer**.
2. **Choisir la source** — *« Source de données (Templates + Sources locales) »*. Possibilité de **« + Créer Source »**. Si la source a des paramètres, le panneau **Paramètres** s'affiche.
3. **Configurer les colonnes** — tableau : `Inclure | Champ source | Label affiché | Type | Format | Alignement | Visible | Épinglé`.
   - **« Régénérer les colonnes »** resynchronise depuis la requête (garde l'existant, ajoute les nouveaux champs, retire les supprimés).
4. **Options de grille** — taille de page (10 → 500), **afficher les totaux** + colonnes à totaliser, tri par défaut, et les bascules de fonctionnalités : recherche, filtres colonne, regroupement, sélecteur de colonnes, export, pagination, tri.
5. **Aperçu** (modale de paramètres si requis) puis **Sauvegarder**.

**Préférences utilisateur** : à la consultation, chaque utilisateur peut afficher/masquer, redimensionner, réordonner, trier, grouper — ses préférences sont mémorisées (`user-prefs`).

---

### 3.3 Tableau croisé (Pivot)

Croisement **Lignes × Colonnes** avec mesures agrégées, comparaisons N/N-1, mise en forme conditionnelle, calculs avancés et **drill-down** (détail au clic).

**Étapes :**

1. **Créer** — `Builder ▸ Pivot` → **« + Nouveau »**.
2. **Onglet Général** :
   - **Nom** + Description
   - **Source principale** (agrégation) et **Source drilldown** (détail des lignes, optionnelle, avec correspondance des champs)
   - **Application**, **Mode comparaison** (Désactivé / Année N vs N-1 / Mois M vs M-1 / Trimestre Q vs Q-1), Public/Privé
3. **Onglet Config** — glisser-déposer les champs dans les zones :
   - **Lignes** (regroupement hiérarchique ; pour les dates : `mois_annee`, `annee`, `trimestre`, `jour`…)
   - **Colonnes** (1 champ max)
   - **Filtres**
   - **Mesures (Valeurs)** : par mesure → agrégation (SUM, AVG, COUNT, MIN, MAX, MÉDIANE, VAR, STDEV), libellé, format, décimales
   - **Options** : totaux généraux, sous-totaux, % ligne / colonne / général, ligne de résumé, position des totaux, **calculs avancés** (cumul, écart N/N-1, % variation, rang, expression `[Champ A] / [Champ B]`)
4. **Onglet Format** — règles de couleur conditionnelles (ex. ≥ 100000 → vert).
5. **Onglet Aperçu** — **« Exécuter l'aperçu »** (nécessite ≥ 1 mesure + 1 ligne) ; drill-down disponible au clic si une source de détail est configurée.
6. **Onglet Documentation** puis **Sauvegarder**.

---

### 3.4 Tableur (Spreadsheet)

Classeur multi-feuilles type Excel (Fortune Sheet), alimenté par une source de données **ou** par un fichier Excel importé.

**Étapes :**

1. **Créer** — `Builder ▸ Tableur` → **« + Nouveau classeur »**.
2. **Onglet Général** — Nom, Description, Application, Public/Privé.
3. **Onglet Feuilles** — gérer les onglets (**« + Ajouter »**, renommer, supprimer). Par feuille, au choix :
   - **Importer Excel** (`.xlsx`/`.xls`) — parsing automatique, ou
   - **Source de données** + correspondance des colonnes (`Inclure | Champ source | Label affiché`).
4. **Aperçu** (modale de paramètres si requis).
5. **Créer / Sauvegarder**, puis **Export** vers Excel.

---

## 4. Création d'un menu

Le menu rend les rapports accessibles. Page **« Gestion des Menus »** (`MenuManagement`), deux onglets : **Structure** et **Droits d'accès**.

### 4.1 Structure du menu

Arborescence **hiérarchique** (parent/enfant). Chaque entrée a un **type** :

| Type | Cible | Stocke |
|---|---|---|
| **Dossier** (`folder`) | — | conteneur uniquement |
| **Dashboard** (`dashboard`) | un tableau de bord | `target_id` |
| **GridView** (`gridview`) | une grille | `target_id` |
| **Pivot** (`pivot-v2`) | un tableau croisé | `target_id` |
| **Fiche Client** (`fiche-client`) | écran dédié | — |
| **Fiche Fournisseur** (`fiche-fournisseur`) | écran dédié | — |
| **Page / Lien** (`page`) | URL personnalisée | `url` |

### 4.2 Créer une entrée de menu

Onglet **Structure** → **« + Nouveau Menu »**. La modale **« Nouveau menu »** propose :

| Champ | Description |
|---|---|
| **Nom** * | Libellé affiché (ex. `Analyse Ventes`) |
| **Code** * | Identifiant unique, minuscules sans espaces (ex. `analyse-ventes`) |
| **Parent** | `-- Racine --` ou un dossier existant |
| **Type** | Dossier, Dashboard, GridView, Pivot, Page… |
| **Cible** | (si Dashboard/GridView/Pivot) sélection du rapport à ouvrir |
| **URL** | (si Page) lien personnalisé (ex. `/ventes`) |
| **Icône** | sélecteur avec recherche, classé par catégorie (Lucide) |
| **Ordre** | position d'affichage (tri croissant) |
| **Menu actif** | masque/affiche l'entrée |

Champs obligatoires : **Nom** et **Code**. Validation → **« Créer »**.
À la création, l'entrée apparaît immédiatement (surbrillance verte), le parent se déploie automatiquement.

### 4.3 Rattacher un rapport à un menu

1. Type = `Dashboard` / `GridView` / `Pivot`.
2. Le sélecteur **Cible** se charge avec les rapports disponibles du type choisi.
3. Le `target_id` mémorise le rapport. Routage à l'ouverture :
   - Dashboard → `/view/{id}`
   - GridView → `/grid/{id}`
   - Pivot → `/pivot-v2/{id}`
   - Page → l'URL saisie

### 4.4 Modifier / Supprimer

- **Modifier** : survol → icône crayon → même modale (titre « Modifier le menu »).
- **Supprimer** : survol → icône corbeille → confirmation. Un menu **avec sous-menus** ne peut être supprimé (« Impossible de supprimer : ce menu a des sous-menus »).
- Les **menus standard** (`is_custom = 0`) sont verrouillés (« Menu standard — modification impossible »).

---

## 5. Droits d'accès (qui voit quoi)

Deux systèmes coexistent ; OptiBoard choisit automatiquement.

### 5.1 Accès simple (par utilisateur)

Onglet **Droits d'accès** :
1. Sélectionner un **utilisateur**.
2. Cocher dans l'arborescence les menus autorisés.
3. **Enregistrer**.

Permissions : `can_view`, `can_export`. Table `APP_UserMenus`.
Les administrateurs voient **tous** les menus (« Cet utilisateur est administrateur. Il a accès à tous les menus »).

### 5.2 Accès par rôles (avancé)

Si l'utilisateur a des **rôles** affectés, le filtrage se fait par rôle :

- **Rôles** (`APP_Roles`) : nom, couleur de badge, `is_admin`.
- **Affectation** (`APP_User_Roles`) : utilisateur ↔ rôle.
- **Droits sur rapports** (`APP_Role_Reports`) : rôle ↔ rapport, avec `can_view`, `can_export`, `can_schedule`.

**Logique de résolution (côté backend) :**

```
1. Rôle admin / superadmin / admin_client      → tous les menus
2. Sinon, utilisateur avec rôles               → filtrage via APP_Role_Reports
3. Sinon (aucun rôle)                           → repli sur APP_UserMenus
```

Les dossiers (conteneurs) restent visibles, mais les **dossiers vides** sont élagués de la réponse.

---

## 6. Fonctionnalités transverses

| Fonctionnalité | Disponible sur | Détail |
|---|---|---|
| **Filtres globaux** | Dashboard | Période, société, commercial, gamme appliqués à tous les widgets |
| **Filtres / tri colonne** | GridView, Pivot | Barres de filtre flottantes, tri multi-colonnes |
| **Regroupement** | GridView (multi-niveaux), Pivot (Lignes) | Glisser une colonne dans la zone de regroupement |
| **Totaux & sous-totaux** | GridView, Pivot | Totaux généraux + sous-totaux, position configurable |
| **Comparaison N / N-1** | Pivot | Année / Mois / Trimestre |
| **Mise en forme conditionnelle** | Dashboard (seuils), Pivot (règles) | Couleurs selon valeur |
| **Calculs avancés** | Pivot | Cumul, écart, % variation, rang, expression `[A]/[B]` |
| **Drill-down / détail** | Pivot | Clic sur une cellule → détail (source dédiée) |
| **Préférences utilisateur** | GridView | Disposition des colonnes mémorisée par utilisateur |
| **Export Excel (XLSX)** | GridView, Pivot, Tableur | Bouton **Export** |
| **Import Excel** | Tableur | Charger un `.xlsx`/`.xls` dans une feuille |
| **Public / Privé** | Tous | Visibilité du rapport |
| **Affectation à une Application** | Tous | Gestion Commerciale, Comptabilité, Paie, Trésorerie |
| **Documentation intégrée** | Dashboard, Pivot | Objectif / champs / formule / avantage |
| **Planification d'envoi** | Rapports (via rôles `can_schedule`) | Voir `Report Scheduler` |

---

## 7. Référence — API & tables

### Sources de données
- `GET  /api/datasources/unified/{code}/fields` — liste des champs
- `POST /api/datasources/unified/{code}/preview` — aperçu des données

### Rapports

| Type | Lister | Détail | Créer | MAJ | Supprimer | Données / Aperçu |
|---|---|---|---|---|---|---|
| Dashboard | `GET /builder/dashboards` | `…/{id}` | `POST` | `PUT …/{id}` | `DELETE …/{id}` | via datasource preview |
| GridView | `GET /gridview/grids` | `…/{id}` | `POST` | `PUT …/{id}` | `DELETE …/{id}` | `POST …/{id}/data`, `…/export` |
| Pivot | `GET /v2/pivots` | `…/{id}` | `POST` | `PUT …/{id}` | `DELETE …/{id}` | `…/preview`, `…/drilldown`, `…/export` |
| Tableur | `GET /spreadsheet/sheets` | `…/{id}` | `POST` | `PUT …/{id}` | `DELETE …/{id}` | `…/data`, `…/export`, `import-excel` |

### Menus (`/api/menus`)
- `GET /` (arbre) · `GET /flat` · `GET /user/{userId}` (selon droits)
- `POST /` · `PUT /{id}` · `DELETE /{id}`
- `GET /targets/{type}` — rapports disponibles pour un type (`gridview` / `pivot-v2` / `dashboard`)
- Droits : `GET /access/{userId}` · `POST /access` · `POST /access/bulk` · `DELETE /access/{userId}/{menuId}`

### Tables SQL (base client `OptiBoard_<CODE>`)
- `APP_Dashboards`, `APP_GridViews`, `APP_Pivots_V2`, `spreadsheet_sheets`
- `APP_Menus`, `APP_UserMenus`, `APP_Roles`, `APP_User_Roles`, `APP_Role_Reports`
- `APP_DataSources` (sources locales) · `APP_DataSources_Templates` (modèles)

---

## 8. Récapitulatif — du SQL à l'écran utilisateur

```
1. Source de données   → définir la requête (Admin ▸ Sources de données)
2. Rapport             → mettre en forme (Builder Dashboard / GridView / Pivot / Tableur)
3. Menu                → créer l'entrée + rattacher le rapport (target_id)
4. Droits d'accès      → autoriser utilisateurs/rôles (onglet Droits d'accès)
5. ✅ L'utilisateur voit le rapport dans son menu
```

---

_Document de référence interne OptiBoard — création de rapports & menus. Hors synchronisation maître._
