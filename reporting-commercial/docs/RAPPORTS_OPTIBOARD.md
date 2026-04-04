# OptiBoard - Catalogue Complet des Rapports

> **Projet** : OptiBoard - Reporting Commercial & Financier
> **Groupe** : ALBOUGHAZE
> **Version** : 2.0
> **Date** : 14/02/2026
> **Total** : 182 rapports | 45 GridView | 40 Pivot | 97 Dashboard

---

## Table des Matieres

- [1. Cycle Ventes](#1-cycle-ventes)
  - [1.1 Documents Ventes](#11-documents-ventes)
  - [1.2 Analyses Ventes](#12-analyses-ventes)
  - [1.3 Ventes - Rapports Avances](#13-ventes---rapports-avances)
- [2. Cycle Achats](#2-cycle-achats)
  - [2.1 Documents Achats](#21-documents-achats)
  - [2.2 Analyses Achats](#22-analyses-achats)
  - [2.3 Achats - Rapports Avances](#23-achats---rapports-avances)
- [3. Cycle Stocks](#3-cycle-stocks)
  - [3.1 Mouvements et Situation](#31-mouvements-et-situation)
  - [3.2 Analyses Stocks](#32-analyses-stocks)
  - [3.3 Stocks - Rapports Avances](#33-stocks---rapports-avances)
- [4. Cycle Comptabilite](#4-cycle-comptabilite)
  - [4.1 Ecritures et Journaux](#41-ecritures-et-journaux)
  - [4.2 Etats Financiers](#42-etats-financiers)
  - [4.3 Analytique](#43-analytique)
  - [4.4 Comptabilite - Rapports Avances](#44-comptabilite---rapports-avances)
- [5. Cycle Recouvrement et Tresorerie](#5-cycle-recouvrement-et-tresorerie)
  - [5.1 Encours et Echeances Clients](#51-encours-et-echeances-clients)
  - [5.2 Reglements](#52-reglements)
  - [5.3 Tableaux de Bord Tresorerie](#53-tableaux-de-bord-tresorerie)
  - [5.4 Recouvrement - Rapports Avances](#54-recouvrement---rapports-avances)
- [6. Cycle Commercial / CRM](#6-cycle-commercial--crm)
  - [6.1 CRM de Base](#61-crm-de-base)
  - [6.2 CRM - Rapports Avances](#62-crm---rapports-avances)
- [7. Cycle Production / Industriel](#7-cycle-production--industriel)
- [8. Cycle RH et Paie](#8-cycle-rh-et-paie)
- [9. Tableaux de Bord Direction](#9-tableaux-de-bord-direction)
  - [9.1 Direction de Base](#91-direction-de-base)
  - [9.2 Direction - Rapports Avances](#92-direction---rapports-avances)
- [Synthese Globale](#synthese-globale)

---

## Legende des Types

| Type | Icone | Usage |
|------|-------|-------|
| **GridView** | `GRID` | Listes detaillees, consultation ligne par ligne, export Excel, filtrage/tri |
| **Pivot** | `PIVOT` | Analyses croisees multi-dimensions, drill-down, regroupements dynamiques |
| **Dashboard** | `DASH` | Indicateurs visuels, graphiques, KPIs, prise de decision rapide |

---

## 1. Cycle Ventes

### 1.1 Documents Ventes

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 1 | Factures de Ventes | `GRID` | Liste detaillee de toutes les factures avec montants HT/TTC, client, date, statut |
| 2 | Bons de Livraison | `GRID` | Suivi des BL avec statut de livraison, client, depot |
| 3 | Bons de Commande | `GRID` | Commandes clients en cours et historique |
| 4 | Devis | `GRID` | Liste des devis emis avec taux de conversion |
| 5 | Avoirs | `GRID` | Retours et avoirs clients avec motifs |
| 6 | Bons de Retour | `GRID` | Marchandises retournees par les clients |
| 7 | Preparations de Livraison | `GRID` | Documents en cours de preparation |

### 1.2 Analyses Ventes

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 8 | CA par Client | `PIVOT` | Chiffre d'affaires croise par client x periode x article |
| 9 | CA par Article | `PIVOT` | Analyse des ventes par produit avec quantites et marges |
| 10 | CA par Commercial | `PIVOT` | Performance commerciale par vendeur x periode |
| 11 | CA par Region / Ville | `PIVOT` | Repartition geographique du chiffre d'affaires |
| 12 | CA par Famille Article | `PIVOT` | Ventes agregees par categorie de produit |
| 13 | Evolution CA Mensuelle | `DASH` | Courbe d'evolution du CA avec comparatif N-1 |
| 14 | Top 20 Clients | `DASH` | Classement clients par CA avec graphe Pareto (80/20) |
| 15 | Top 20 Articles | `DASH` | Produits les plus vendus en valeur et quantite |
| 16 | Analyse Marges | `PIVOT` | Marge brute par client x article x commercial |
| 17 | Commandes en Cours | `GRID` | Commandes non encore livrees avec delais |
| 18 | Comparatif N / N-1 | `DASH` | Tableaux de bord comparatif annee en cours vs precedente |
| 19 | CA par Mode de Reglement | `PIVOT` | Repartition du CA par type de paiement |
| 20 | Statistiques Remises | `PIVOT` | Analyse des remises accordees par client/article |

### 1.3 Ventes - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 21 | Analyse RFM Clients | `DASH` | Segmentation Recence x Frequence x Montant pour ciblage marketing |
| 22 | Saisonnalite des Ventes | `DASH` | Detection des pics/creux par article et famille sur 3 ans |
| 23 | Panier Moyen par Client | `PIVOT` | Valeur moyenne par transaction x client x periode |
| 24 | Cross-Selling / Articles Associes | `DASH` | Articles frequemment achetes ensemble (associations) |
| 25 | Clients a Risque de Churn | `DASH` | Clients dont la frequence/valeur d'achat diminue avec alerte |
| 26 | Analyse des Prix de Vente | `PIVOT` | Evolution des prix unitaires par article x client x periode |
| 27 | Taux de Service Client | `DASH` | % commandes livrees a temps, completes, sans retour |
| 28 | Analyse des Retours | `DASH` | Taux de retour par article/client/motif avec tendance |
| 29 | CA Previsionnel (Forecast) | `DASH` | Projection du CA basee sur historique et commandes en cours |
| 30 | Rentabilite par Client | `PIVOT` | CA - cout des marchandises - remises - cout de recouvrement par client |
| 31 | Analyse Geographique Avancee | `DASH` | Cartographie des ventes par zone avec densite et potentiel |
| 32 | Fidelite Clients | `DASH` | Anciennete, regularite, evolution CA par tranche de fidelite |
| 33 | Analyse des Remises et Conditions | `PIVOT` | Impact des remises sur la marge par client x commercial x article |
| 34 | Performance des Devis | `DASH` | Delai moyen de conversion, taux d'acceptation, montant moyen |
| 35 | Ventes par Tranche Horaire / Jour | `PIVOT` | Repartition des ventes par heure de la journee et jour de la semaine |

**Sous-total Ventes : 35 rapports** (8 GRID | 12 PIVOT | 15 DASH)

---

## 2. Cycle Achats

### 2.1 Documents Achats

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 36 | Factures Fournisseurs | `GRID` | Liste des factures d'achat avec fournisseur, montants |
| 37 | Bons de Reception | `GRID` | Receptions de marchandises avec controle quantites |
| 38 | Bons de Commande Fournisseurs | `GRID` | Commandes passees aux fournisseurs |
| 39 | Demandes d'Achat | `GRID` | Demandes internes en attente de validation |
| 40 | Avoirs Fournisseurs | `GRID` | Retours et avoirs recus des fournisseurs |
| 41 | Bons de Retour Fournisseurs | `GRID` | Marchandises retournees aux fournisseurs |

### 2.2 Analyses Achats

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 42 | Achats par Fournisseur | `PIVOT` | Volume d'achats croise par fournisseur x periode |
| 43 | Achats par Article | `PIVOT` | Analyse des achats par produit x fournisseur |
| 44 | Achats par Famille Article | `PIVOT` | Achats agreges par categorie |
| 45 | Evolution Achats Mensuelle | `DASH` | Courbe des achats avec tendance |
| 46 | Top 20 Fournisseurs | `DASH` | Classement fournisseurs par volume d'achat |
| 47 | Comparatif Prix d'Achat | `PIVOT` | Evolution des prix d'achat par article dans le temps |
| 48 | Commandes en Cours Fournisseurs | `GRID` | Commandes non receptionnees avec delais |
| 49 | Analyse Delais Livraison Fournisseurs | `DASH` | Performance fournisseurs sur les delais |
| 50 | Achats par Depot | `PIVOT` | Repartition des achats par lieu de stockage |

### 2.3 Achats - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 51 | Scoring Fournisseurs | `DASH` | Note globale : prix, qualite, delai, fiabilite par fournisseur |
| 52 | Analyse des Ecarts de Prix | `PIVOT` | Prix commande vs prix facture vs prix historique |
| 53 | Dependance Fournisseur | `DASH` | % du volume d'achat par fournisseur avec alerte concentration |
| 54 | Delai Moyen de Livraison | `DASH` | Performance livraison par fournisseur avec tendance |
| 55 | Taux de Conformite Reception | `DASH` | % receptions conformes (quantite, qualite) par fournisseur |
| 56 | Prevision des Achats | `DASH` | Besoins projetes bases sur historique ventes et stock |
| 57 | Achats vs Budget | `DASH` | Comparaison achats reels vs budget prevu par categorie |
| 58 | Analyse des Litiges Fournisseurs | `GRID` | Historique des litiges : retards, non-conformites, ecarts prix |
| 59 | Cout Total d'Acquisition | `PIVOT` | Prix + transport + douane + stockage par article x fournisseur |
| 60 | Articles Multi-Fournisseurs | `PIVOT` | Comparatif prix/delai pour articles disponibles chez plusieurs fournisseurs |

**Sous-total Achats : 25 rapports** (8 GRID | 8 PIVOT | 9 DASH)

---

## 3. Cycle Stocks

### 3.1 Mouvements et Situation

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 61 | Mouvements de Stock | `GRID` | Journal complet des entrees/sorties |
| 62 | Entrees de Stock | `GRID` | Detail de toutes les entrees (achats, retours, transferts) |
| 63 | Sorties de Stock | `GRID` | Detail de toutes les sorties (ventes, pertes, transferts) |
| 64 | Etat du Stock Actuel | `GRID` | Situation en temps reel par article x depot |
| 65 | Stock par Depot | `GRID` | Situation de stock ventilee par emplacement |
| 66 | Articles en Rupture | `GRID` | Produits dont le stock est a zero ou sous seuil minimum |
| 67 | Articles en Surstock | `GRID` | Produits dont le stock depasse le seuil maximum |

### 3.2 Analyses Stocks

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 68 | Valorisation du Stock | `PIVOT` | Valeur du stock par article x depot x famille |
| 69 | Rotation des Stocks | `DASH` | Taux de rotation par article avec classification ABC |
| 70 | Evolution Stock Mensuelle | `DASH` | Courbe d'evolution des niveaux de stock |
| 71 | Stock Dormant | `GRID` | Articles sans mouvement depuis X mois |
| 72 | Analyse ABC Stock | `DASH` | Classification Pareto des articles (A/B/C) par valeur |
| 73 | Couverture de Stock | `DASH` | Nombre de jours de stock restant par article |
| 74 | Inventaire Comparatif | `PIVOT` | Ecarts entre stock theorique et physique |
| 75 | Transferts Inter-Depots | `GRID` | Historique des mouvements entre depots |

### 3.3 Stocks - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 76 | Classification ABC/XYZ | `DASH` | Matrice ABC (valeur) x XYZ (regularite) pour politique stock |
| 77 | Prevision de Rupture | `DASH` | Articles projetes en rupture dans les 7/14/30 prochains jours |
| 78 | Cout de Possession du Stock | `DASH` | Cout financier + stockage + obsolescence par famille |
| 79 | Taux de Peremption / Obsolescence | `DASH` | Articles proches de la date limite ou sans mouvement prolonge |
| 80 | Stock Minimum / Point de Commande | `GRID` | Comparaison stock actuel vs seuil de reapprovisionnement |
| 81 | Analyse des Ecarts d'Inventaire | `PIVOT` | Ecarts constates lors des inventaires par depot x famille |
| 82 | Flux de Stock par Depot | `DASH` | Visualisation des flux entrees/sorties/transferts par depot |
| 83 | Lead Time vs Stock Securite | `DASH` | Adequation du stock de securite par rapport aux delais fournisseurs |
| 84 | Valorisation Multi-Methodes | `PIVOT` | Comparaison valorisation FIFO / CMUP / dernier prix par article |
| 85 | Productivite Logistique | `DASH` | Nombre de lignes traitees par jour, par preparateur, par depot |

**Sous-total Stocks : 25 rapports** (10 GRID | 4 PIVOT | 11 DASH)

---

## 4. Cycle Comptabilite

### 4.1 Ecritures et Journaux

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 86 | Journal General | `GRID` | Toutes les ecritures comptables chronologiques |
| 87 | Ecritures par Journal | `GRID` | Filtrage par journal (achat, vente, banque, OD...) |
| 88 | Ecritures par Compte | `GRID` | Mouvements sur un compte comptable donne |
| 89 | Ecritures par Tiers | `GRID` | Mouvements lies a un client ou fournisseur |
| 90 | Grand Livre | `GRID` | Detail des mouvements par compte avec soldes |
| 91 | Balance Generale | `GRID` | Soldes debiteurs/crediteurs de tous les comptes |
| 92 | Balance Agee Fournisseurs | `GRID` | Anciennete des dettes fournisseurs |

### 4.2 Etats Financiers

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 93 | Bilan Synthetique | `DASH` | Actif vs Passif en un coup d'oeil avec graphes |
| 94 | Bilan Detaille Actif | `GRID` | Decomposition complete de l'actif |
| 95 | Bilan Detaille Passif | `GRID` | Decomposition complete du passif |
| 96 | CPC Synthetique | `DASH` | Compte de produits et charges avec marge, resultat |
| 97 | CPC Detaille | `GRID` | Detail de chaque poste du CPC |
| 98 | CPC Comparatif N/N-1 | `DASH` | Evolution des P&C vs annee precedente |
| 99 | Analyse des Charges par Nature | `PIVOT` | Charges croisees par nature x periode x centre |
| 100 | Analyse des Produits par Nature | `PIVOT` | Produits croises par nature x periode |
| 101 | Ratios Financiers | `DASH` | Indicateurs cles : liquidite, solvabilite, rentabilite |
| 102 | Tresorerie Previsionnelle | `DASH` | Flux de tresorerie projetes avec solde previsionnel |

### 4.3 Analytique

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 103 | Analytique par Centre de Cout | `PIVOT` | Charges par centre x nature x periode |
| 104 | Analytique par Projet/Affaire | `PIVOT` | Rentabilite par projet ou affaire |
| 105 | Budget vs Realise | `DASH` | Ecarts budgetaires par poste avec alertes |

### 4.4 Comptabilite - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 106 | Tableau de Flux de Tresorerie | `DASH` | Flux d'exploitation, investissement, financement (methode indirecte) |
| 107 | Analyse du BFR | `DASH` | Besoin en Fonds de Roulement : stocks + creances - dettes avec evolution |
| 108 | Ratios de Rentabilite | `DASH` | ROE, ROA, marge nette, marge brute, EBITDA avec tendance |
| 109 | Ratios de Liquidite | `DASH` | Liquidite generale, reduite, immediate avec seuils d'alerte |
| 110 | Ratios d'Endettement | `DASH` | Gearing, autonomie financiere, capacite de remboursement |
| 111 | Analyse du Seuil de Rentabilite | `DASH` | Point mort, marge de securite, levier operationnel |
| 112 | Budget vs Realise Detaille | `PIVOT` | Ecarts par poste comptable x centre x mois avec % |
| 113 | Ecritures d'Inventaire | `GRID` | Provisions, amortissements, regularisations de fin d'exercice |
| 114 | Rapprochement Bancaire | `GRID` | Etat de rapprochement par banque avec ecarts |
| 115 | TVA Collectee vs Deductible | `DASH` | Suivi de la TVA a declarer par periode avec detail |
| 116 | Charges Fixes vs Variables | `DASH` | Analyse de la structure des couts avec point mort |
| 117 | Consolidation Multi-Societes | `DASH` | Etats financiers consolides avec eliminations inter-societes |
| 118 | Cloture Mensuelle Checklist | `GRID` | Etat d'avancement des taches de cloture avec statut |

**Sous-total Comptabilite : 33 rapports** (11 GRID | 5 PIVOT | 17 DASH)

---

## 5. Cycle Recouvrement et Tresorerie

### 5.1 Encours et Echeances Clients

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 119 | Balance Agee Clients | `GRID` | Creances par tranche d'age (0-30, 31-60, 61-90, +90j) |
| 120 | Echeances Non Reglees | `GRID` | Detail de chaque echeance en retard |
| 121 | Echeances A Echoir | `GRID` | Echeances a venir avec niveau d'urgence |
| 122 | Factures Non Reglees | `GRID` | Factures avec reste a regler |
| 123 | Creances Douteuses | `GRID` | Clients a risque (retard > 120 jours) |

### 5.2 Reglements

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 124 | Reglements Clients par Periode | `PIVOT` | Encaissements par mois x mode de reglement |
| 125 | Reglements Clients par Mode | `PIVOT` | Repartition cheque/virement/espece/effet |
| 126 | Reglements Fournisseurs par Periode | `PIVOT` | Decaissements par mois x mode |
| 127 | Rapprochement Echeances/Reglements | `GRID` | Etat de lettrage des paiements |

### 5.3 Tableaux de Bord Tresorerie

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 128 | KPIs Recouvrement | `DASH` | Encours total, DSO, taux de recouvrement, alertes |
| 129 | DSO par Client | `DASH` | Delai moyen de paiement par client avec graphe |
| 130 | Tresorerie Journaliere | `DASH` | Solde de tresorerie jour par jour |
| 131 | Prevision de Tresorerie | `DASH` | Projection encaissements vs decaissements |
| 132 | Performance Recouvrement par Commercial | `DASH` | Efficacite de relance par commercial |
| 133 | Echeances par Client | `PIVOT` | Ventilation des echeances par client avec tranches d'age |

### 5.4 Recouvrement - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 134 | Scoring Risque Client | `DASH` | Score de risque base sur : anciennete retard, montant, frequence impaye |
| 135 | Prevision d'Encaissement | `DASH` | Projection des encaissements basee sur historique de paiement par client |
| 136 | Cash Flow Hebdomadaire | `DASH` | Suivi tresorerie semaine par semaine avec previsionnel |
| 137 | Efficacite des Relances | `DASH` | Taux de recouvrement apres 1ere, 2eme, 3eme relance |
| 138 | Analyse du DSO Tendanciel | `DASH` | Evolution du DSO sur 12 mois glissants par segment client |
| 139 | Concentration du Risque | `DASH` | Top 10 encours clients vs encours total avec % et alerte |
| 140 | Aging Report Multi-Devises | `PIVOT` | Balance agee avec conversion devise et risque de change |
| 141 | Suivi des Effets de Commerce | `GRID` | Portefeuille d'effets : remis, encaisses, impayes, en circulation |
| 142 | Tresorerie par Banque | `DASH` | Solde et mouvements par compte bancaire avec graphe |
| 143 | Cout du Credit Client | `DASH` | Cout financier de l'encours client (taux x montant x duree) |
| 144 | Plan de Tresorerie Glissant | `DASH` | Prevision rolling 13 semaines avec scenarios optimiste/pessimiste |

**Sous-total Recouvrement : 26 rapports** (7 GRID | 4 PIVOT | 15 DASH)

---

## 6. Cycle Commercial / CRM

### 6.1 CRM de Base

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 145 | Fiche Client 360 | `DASH` | Vue complete d'un client : CA, encours, commandes, historique |
| 146 | Portefeuille Clients par Commercial | `PIVOT` | Repartition des clients par vendeur avec CA |
| 147 | Clients Inactifs | `GRID` | Clients sans commande depuis X mois |
| 148 | Nouveaux Clients | `GRID` | Clients crees sur la periode avec premier CA |
| 149 | Taux de Conversion Devis vers Commande | `DASH` | Suivi pipeline commercial |
| 150 | Objectifs vs Realise Commerciaux | `DASH` | Atteinte des objectifs par vendeur |

### 6.2 CRM - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 151 | Pipeline Commercial | `DASH` | Entonnoir : prospect - devis - commande - facture avec taux conversion |
| 152 | Couverture Territoire | `DASH` | Carte des zones couvertes vs zones blanches par commercial |
| 153 | Activite Commerciale | `PIVOT` | Nombre de visites, devis, commandes par commercial x semaine |
| 154 | Cycle de Vente Moyen | `DASH` | Duree moyenne du cycle par commercial x type de produit x segment |
| 155 | Matrice BCG Clients | `DASH` | Classement clients par croissance CA x part de marche relative |
| 156 | Analyse de la Concurrence Prix | `PIVOT` | Positionnement prix vs concurrents par famille d'article |
| 157 | Potentiel Client Non Exploite | `DASH` | Gap entre achats potentiels et achats reels par client |
| 158 | Performance Promotions | `DASH` | Impact des operations promotionnelles sur le volume et la marge |
| 159 | Satisfaction Client (Score) | `DASH` | Indicateur base sur retours, delais, litiges, regularite commandes |

**Sous-total CRM : 15 rapports** (2 GRID | 3 PIVOT | 10 DASH)

---

## 7. Cycle Production / Industriel

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 160 | Suivi des Ordres de Fabrication | `GRID` | OF en cours, termines, en retard avec % d'avancement |
| 161 | TRS (Taux de Rendement Synthetique) | `DASH` | Disponibilite x Performance x Qualite par machine/ligne |
| 162 | Cout de Revient Industriel | `PIVOT` | Matiere + MO + charges par produit fini avec ecart vs standard |
| 163 | Consommation Matieres Premieres | `PIVOT` | Reel vs theorique par OF x article avec ecarts |
| 164 | Planning de Production | `DASH` | Gantt des OF avec charge machine et ressources |
| 165 | Taux de Rebut / Non-Conformite | `DASH` | % de rebut par produit x ligne x cause |
| 166 | Productivite par Atelier | `DASH` | Output par heure x operateur x machine |

**Sous-total Production : 7 rapports** (1 GRID | 2 PIVOT | 4 DASH)

---

## 8. Cycle RH et Paie

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 167 | Masse Salariale | `DASH` | Evolution mensuelle avec repartition par departement/fonction |
| 168 | Effectifs et Turnover | `DASH` | Entrees, sorties, taux de rotation par service |
| 169 | Absenteisme | `DASH` | Taux d'absence par service x motif x periode |
| 170 | Cout par Employe | `PIVOT` | Salaire + charges + avantages par employe x departement |
| 171 | Heures Supplementaires | `PIVOT` | Volume et cout des HS par service x mois |

**Sous-total RH : 5 rapports** (0 GRID | 2 PIVOT | 3 DASH)

---

## 9. Tableaux de Bord Direction

### 9.1 Direction de Base

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 172 | Dashboard Directeur General | `DASH` | KPIs cles : CA, marge, tresorerie, encours, stock |
| 173 | Dashboard Directeur Commercial | `DASH` | CA, top clients, pipeline, objectifs commerciaux |
| 174 | Dashboard Directeur Financier | `DASH` | Tresorerie, BFR, ratios, budget vs realise |
| 175 | Dashboard Directeur Logistique | `DASH` | Stock, ruptures, rotation, delais livraison |

### 9.2 Direction - Rapports Avances

| # | Rapport | Type | Description |
|---|---------|------|-------------|
| 176 | Synthese Mensuelle Multi-Societes | `DASH` | Consolidation des indicateurs par societe |
| 177 | Cockpit DG Temps Reel | `DASH` | 10 KPIs critiques avec alertes rouge/orange/vert en temps reel |
| 178 | Balanced Scorecard | `DASH` | 4 perspectives : Finance, Clients, Processus, Apprentissage |
| 179 | P&L Management par BU | `DASH` | Compte de resultat analytique par business unit |
| 180 | Dashboard de Conformite | `DASH` | Indicateurs reglementaires, fiscaux, delais de declaration |
| 181 | Analyse de Scenarios | `DASH` | Simulation What-If sur prix/volume/charges avec impact resultat |
| 182 | Benchmark Inter-Societes | `DASH` | Comparaison des performances entre entites du groupe |

**Sous-total Direction : 11 rapports** (0 GRID | 0 PIVOT | 11 DASH)

---

## Synthese Globale

### Par Type de Document

| Type | Quantite | Pourcentage |
|------|:--------:|:-----------:|
| GridView | 39 | 21% |
| Pivot | 30 | 17% |
| Dashboard | 113 | 62% |
| **Total** | **182** | **100%** |

### Par Cycle Metier

| Cycle | Grid | Pivot | Dash | Total |
|-------|:----:|:-----:|:----:|:-----:|
| Ventes | 8 | 12 | 15 | **35** |
| Achats | 8 | 8 | 9 | **25** |
| Stocks | 10 | 4 | 11 | **25** |
| Comptabilite | 11 | 5 | 17 | **33** |
| Recouvrement / Tresorerie | 7 | 4 | 15 | **26** |
| Commercial / CRM | 2 | 3 | 10 | **15** |
| Production | 1 | 2 | 4 | **7** |
| RH & Paie | 0 | 2 | 3 | **5** |
| Direction | 0 | 0 | 11 | **11** |
| **Total** | **47** | **40** | **95** | **182** |

### Matrice Priorite d'Implementation

| Priorite | Cycles | Justification |
|----------|--------|---------------|
| **P1 - Critique** | Ventes, Achats, Stocks | Cycle operationnel quotidien |
| **P2 - Important** | Comptabilite, Recouvrement | Suivi financier et tresorerie |
| **P3 - Strategique** | CRM, Direction | Pilotage et decision |
| **P4 - Optionnel** | Production, RH | Selon activite de l'entreprise |

---

> **Document genere pour OptiBoard - KAsoft**
> Derniere mise a jour : 14/02/2026
