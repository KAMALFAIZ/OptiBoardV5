# -*- coding: utf-8 -*-
"""
Documentation complète de tous les rapports OptiBoard (149 datasources).
Met à jour APP_GridViews et APP_Pivots_V2 avec les champs doc_*.
Utilise COALESCE : ne remplace pas une documentation déjà saisie manuellement.
"""
import sys
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=OptiBoard_SaaS;"
    "UID=sa;PWD=SQL@2019;"
    "TrustServerCertificate=yes"
)

# ══════════════════════════════════════════════════════════════════════
# DICTIONNAIRE DE DOCUMENTATION — ds_code → (description, fields, formula, advantage)
# ══════════════════════════════════════════════════════════════════════
DOCS = {

    # ── VENTES ───────────────────────────────────────────────────────
    "DS_VENTES_GLOBAL": (
        "Synthèse globale des ventes sur la période sélectionnée, toutes sociétés confondues.",
        "Société : entité commerciale\nCA HT : chiffre d'affaires hors taxes\nCA TTC : chiffre d'affaires toutes taxes\nMarge : CA HT - coût de revient\nMarge % : taux de marge brute\nNb Clients : clients distincts ayant acheté\nNb Documents : nombre de pièces de vente\nQte Totale : quantité totale vendue\nNb Lignes : nombre de lignes de vente\nCA Moyen par Client : CA HT / Nb Clients\nPanier Moyen : CA HT / Nb Documents",
        "Marge = CA HT - Coût Revient\nMarge % = Marge / CA HT × 100\nCA Moyen par Client = CA HT / Nb Clients\nPanier Moyen = CA HT / Nb Documents",
        "Vue d'ensemble immédiate de la performance commerciale sur la période. Idéal pour les tableaux de bord de direction."
    ),
    "DS_VENTES_PAR_MOIS": (
        "Évolution mensuelle du chiffre d'affaires et de la marge sur la période.",
        "Annee : année de la période\nMois : numéro de mois (1-12)\nPeriode : libellé YYYY-MM\nSociété : entité commerciale\nCA HT / CA TTC : chiffres d'affaires\nCout Revient : coût total des articles vendus\nMarge / Marge % : performance brute\nNb Clients / Nb Documents / Nb Articles : volumes\nQte Totale : quantités vendues",
        "Agrégation par YEAR(date) et MONTH(date)\nMarge = CA HT - Coût Revient\nMarge % = Marge / CA HT × 100",
        "Suivi de la tendance commerciale mois par mois. Permet de détecter les pics et creux saisonniers."
    ),
    "DS_VENTES_PAR_CLIENT": (
        "Performance des ventes agrégée par client sur la période.",
        "Code Client : identifiant Sage\nClient : raison sociale\nSociété : entité de vente\nCA HT / CA TTC : chiffres d'affaires\nMarge / Marge % : rentabilité par client\nNb Factures : nombre de documents\nQte Totale : volumes achetés\nPanier Moyen : CA HT / Nb Factures\nPremiere Vente / Derniere Vente : dates d'activité",
        "Marge % = Marge / CA HT × 100\nPanier Moyen = CA HT / Nb Factures",
        "Identifie les meilleurs clients et les clients en baisse d'activité. Base du classement ABC clients."
    ),
    "DS_VENTES_PAR_ARTICLE": (
        "Performance des ventes agrégée par article/produit sur la période.",
        "Code Article : référence Sage\nDesignation : libellé produit\nCatalogue1 / Catalogue2 : classification catalogue\nGamme1 / Gamme2 : classification gamme\nQte Vendue : quantités totales\nCA HT : chiffre d'affaires\nMarge / Marge % : rentabilité\nPrix Moyen : prix de vente moyen\nCout Moyen : coût moyen\nNb Clients : clients ayant acheté cet article",
        "Marge % = Marge / CA HT × 100\nPrix Moyen = CA HT / Qte Vendue",
        "Identifie les articles stars et les articles à faible marge. Essentiel pour la politique tarifaire et l'optimisation du catalogue."
    ),
    "DS_VENTES_PAR_CATALOGUE": (
        "Agrégation des ventes par famille catalogue (niveau 1 et 2).",
        "Catalogue : famille principale\nSous Catalogue : sous-famille\nNb Articles : articles vendus dans cette famille\nQte Vendue : quantités totales\nCA HT : chiffre d'affaires\nMarge / Marge % : rentabilité de la famille\nNb Clients : clients acheteurs\nCA Moyen par Article : CA HT / Nb Articles",
        "Marge % = Marge / CA HT × 100\nCA Moyen par Article = CA HT / Nb Articles",
        "Analyse la contribution de chaque famille de produits au CA global. Aide à prioriser les gammes à développer."
    ),
    "DS_VENTES_PAR_DEPOT": (
        "Répartition des ventes par dépôt/magasin/entrepôt de livraison.",
        "Code Depot / Depot : identifiant et libellé du dépôt\nSociété : entité commerciale\nCA HT : chiffre d'affaires\nMarge / Marge % : rentabilité\nQte Vendue : volumes\nNb Articles : références vendues\nNb Clients : clients servis\nNb Documents : pièces émises\nCA Moyen par Client : CA HT / Nb Clients",
        "Marge % = Marge / CA HT × 100",
        "Mesure la performance par point de vente ou entrepôt. Utile pour les réseaux multi-dépôts."
    ),
    "DS_VENTES_PAR_TYPE_DOC": (
        "Répartition des ventes par type de document (Facture, BL, Avoir, etc.).",
        "Société : entité commerciale\nNb Documents : nombre de pièces par type\nNb Lignes : lignes de détail\nQte Totale : quantités\nMontant HT / TTC : montants\nNb Clients : clients concernés\nNb Articles : articles distincts",
        "Agrégation par type de document Sage",
        "Contrôle la répartition entre documents de vente. Permet de détecter un volume anormal d'avoirs ou BL non facturés."
    ),
    "DS_FACTURES": (
        "Détail ligne à ligne de toutes les factures de vente sur la période.",
        "Société : entité\nNum Facture / Date Facture : identification\nCode Client / Client : acheteur\nCode Article / Designation : produit\nQte : quantité facturée\nPU HT : prix unitaire HT\nMontant HT / TTC : montants\nCout / Marge / Taux Marge % : rentabilité ligne\nReference Client : référence de commande client\nCode Affaire / Affaire : rattachement projet",
        "Marge = Montant HT - Cout\nTaux Marge % = Marge / Montant HT × 100",
        "Source de vérité pour l'audit de facturation. Permet d'analyser chaque ligne de vente avec sa marge réelle."
    ),
    "DS_BONS_LIVRAISON": (
        "Détail des bons de livraison émis sur la période.",
        "Société : entité\nNum BL / Num BC : numéros de pièces\nCode Client / Client : destinataire\nCode Article / Designation : produit livré\nQte BL / Qte BC : quantités livrées vs commandées\nMontant HT : valeur livrée\nCode Depot / Depot : dépôt expéditeur\nNum Serie Lot : traçabilité",
        "Taux livraison = Qte BL / Qte BC × 100",
        "Suivi des expéditions et de la traçabilité. Permet de détecter les BL partiels et les retards de livraison."
    ),
    "DS_BONS_COMMANDE": (
        "Détail des bons de commande clients en cours ou clôturés.",
        "Société : entité\nNum BC : numéro commande\nCode Client / Client : acheteur\nCode Article / Designation : produit commandé\nQte Commandee / Qte Livree / Reste A Livrer : suivi livraison\nTaux Livraison % : avancement\nPU HT / Montant HT : valeurs\nDate Livraison Prevue : planification\nReference Client / Code Affaire : rattachements",
        "Reste A Livrer = Qte Commandee - Qte Livree\nTaux Livraison % = Qte Livree / Qte Commandee × 100",
        "Pilotage du carnet de commandes et des délais de livraison. Essentiel pour la logistique et le service client."
    ),
    "DS_DEVIS": (
        "Liste des devis émis aux clients sur la période.",
        "Société : entité\nNum Devis / Date Devis : identification\nCode Client / Client : prospect/client\nCode Article / Designation : produit proposé\nQte / PU HT / Montant HT / TTC : données tarifaires\nReference / Code Affaire / Affaire : rattachements",
        "Montant HT = Qte × PU HT\nTaux transformation = Devis transformés / Total Devis × 100",
        "Analyse du pipeline commercial et du taux de transformation. Aide à cibler les relances commerciales."
    ),
    "DS_AVOIRS": (
        "Détail des avoirs clients émis sur la période.",
        "Société : entité\nNum Avoir / Date Avoir : identification\nCode Client / Client : bénéficiaire\nCode Article / Designation : produit retourné/corrigé\nQte / PU HT / Montant HT / TTC : montants\nReference : référence de la facture corrigée\nCode Depot : dépôt de retour",
        "Montant HT = Qte × PU HT (négatif = avoir)",
        "Contrôle des retours et litiges clients. Un volume élevé d'avoirs peut signaler des problèmes qualité ou de livraison."
    ),
    "DS_PREPARATIONS_LIVRAISON": (
        "Détail des préparations de livraison en cours.",
        "Société : entité\nNum PL / Num BC : numéros de pièces\nCode Client / Client : destinataire\nCode Article / Designation : produit\nQte PL / Qte BC : quantités préparées vs commandées\nPU HT / Montant HT : valeurs\nCode Depot / Depot : dépôt préparateur\nDate Livraison Prevue : planification",
        "Suivi de l'avancement des préparations",
        "Pilotage de l'atelier logistique. Permet d'anticiper les retards et d'optimiser la charge de préparation."
    ),
    "DS_VENTES_DETAIL": (
        "Détail exhaustif de toutes les lignes de vente (toutes pièces confondues).",
        "Société : entité\nNuméro Pièce / Date : identification document\nCode Client / Client : acheteur\nCode Article / Designation : produit\nQte / PU HT / PU TTC / Montant HT / TTC : tarification\nCout / Marge / Taux Marge % : rentabilité\nCode Depot / Depot : dépôt\nNum Serie Lot : traçabilité\nCode Affaire / Affaire / Reference Client : rattachements",
        "Marge = Montant HT - Cout\nTaux Marge % = Marge / Montant HT × 100",
        "Source la plus granulaire pour l'analyse des ventes. Base de tous les rapports de marge détaillée."
    ),
    "DS_VENTES_PAR_AFFAIRE": (
        "CA et marge agrégés par affaire/projet client.",
        "Code Affaire / Affaire : identification projet\nCode Client / Client : client associé\nSociété : entité\nCA HT / Marge / Marge % : performance\nNb Documents : pièces liées à l'affaire\nDate Debut / Date Fin : durée du projet",
        "Marge % = Marge / CA HT × 100",
        "Suivi de la rentabilité par projet. Essentiel pour les entreprises travaillant en mode affaire (BTP, services, industrie)."
    ),
    "DS_COMMANDES_EN_COURS": (
        "Commandes clients non intégralement livrées à ce jour.",
        "Société : entité\nNum BC : commande\nCode Client / Client : acheteur\nCode Article / Designation : produit\nQte Commandee / Qte Livree / Reste A Livrer : avancement\nTaux Livraison % : % réalisé\nPU HT / Montant Reste : valeur restante\nDate Livraison Prevue / Age Commande Jours : délais",
        "Reste A Livrer = Qte Commandee - Qte Livree\nAge = DATEDIFF(day, Date Commande, GETDATE())",
        "Tableau de bord des commandes en souffrance. Permet de prioriser les expéditions et d'alerter sur les retards."
    ),
    "DS_TOP_ARTICLES": (
        "Classement des articles les plus vendus sur la période.",
        "Code Article / Designation : produit\nCatalogue : famille\nQte Vendue : volumes\nCA HT / Marge / Marge % : performance\nNb Clients : clients acheteurs\nNb Ventes : occurrences",
        "Classement par CA HT décroissant",
        "Identifie les produits phares du catalogue. Base pour les décisions de réapprovisionnement et de mise en avant commerciale."
    ),
    "DS_TOP_CLIENTS": (
        "Classement des meilleurs clients par CA sur la période.",
        "Code Client / Client : acheteur\nSociété : entité\nCA HT / Marge / Marge % : performance\nNb Factures / Nb Articles : volumes\nPanier Moyen : CA HT / Nb Factures\nPremiere Vente / Derniere Vente : ancienneté",
        "Classement par CA HT décroissant\nPanier Moyen = CA HT / Nb Factures",
        "Top clients à fidéliser et à developper. Colonne vertébrale de la stratégie commerciale."
    ),
    "DS_VENTES_PAR_COMMERCIAL": (
        "Performance commerciale agrégée par représentant/vendeur.",
        "Code Commercial / Commercial : vendeur\nSociété : entité\nNb Clients : portefeuille actif\nNb Factures : activité\nCA HT / Marge / Marge % : performance\nCA Moyen par Client : CA HT / Nb Clients\nPanier Moyen : CA HT / Nb Factures",
        "CA Moyen par Client = CA HT / Nb Clients\nPanier Moyen = CA HT / Nb Factures",
        "Comparatif de performance entre commerciaux. Base des objectifs et des commissions."
    ),
    "DS_VENTES_PAR_ZONE": (
        "Répartition des ventes par zone géographique et canal de distribution.",
        "Zone : zone commerciale\nCanal : canal de vente (direct, revendeur, export...)\nSociété : entité\nNb Clients / CA HT / Marge / Marge %",
        "Agrégation par zone et canal Sage",
        "Analyse de la couverture territoriale et des canaux les plus performants."
    ),
    "DS_CA_DETAIL_COMPLET": (
        "Détail complet du CA avec tous les modes de valorisation de la marge (PR, CMUP, DPA).",
        "Société entête : entité\nMontant TTC / HT Entete : valeurs entête\nDésignation Ligne : libellé ligne\nMontant : valeur ligne\nDPA-Période / DPA-Vente / DPR-Vente : modes de valorisation Sage\nMarge PR / CMUP / DPA : marges selon méthode\nCoût PR / CMUP : coûts selon méthode",
        "Marge PR = Montant HT - Coût Prix Revient\nMarge CMUP = Montant HT - Coût CMUP\nMarge DPA = Montant HT - Dernier Prix d'Achat",
        "Rapport de référence pour l'analyse de marge multi-méthode. Permet de comparer les 3 méthodes de valorisation Sage."
    ),
    "DS_CA_MARGE_DYNAMIQUE": (
        "CA et marge agrégés avec choix du mode de valorisation (DPA, DPR, CMUP).",
        "Société : entité\nMontant : CA HT\nDPA-Période / DPA-Vente / DPR-Vente : coûts valorisés\nMarge : marge selon méthode choisie\nCoût marchandise : coût total\nType Valorisation : méthode appliquée",
        "Marge = Montant HT - Coût selon méthode sélectionnée",
        "Flexibilité d'analyse selon la politique de valorisation de l'entreprise."
    ),
    "DS_CA_AGREGE_CLIENT": (
        "CA et marge agrégés par client (source dynamique).",
        "Société : entité\nNb Documents : volume\nQte Totale : quantités\nCA / Marge / Marge % : performance\nCoût marchandise : coût total",
        "Marge % = Marge / CA × 100",
        "Version dynamique du rapport CA par client, compatible avec les pivots."
    ),
    "DS_CA_AGREGE_ARTICLE": (
        "CA et marge agrégés par article (source dynamique).",
        "Société : entité\nNb Clients / Nb Documents : volumes\nQte Vendue / CA / Marge / Marge % : performance\nPrix Moyen Vente / Coût Moyen : tarification",
        "Marge % = Marge / CA × 100\nPrix Moyen = CA / Qte Vendue",
        "Version dynamique pour les analyses croisées article × période en pivot."
    ),
    "DS_CA_AGREGE_CATALOGUE": (
        "CA et marge agrégés par famille catalogue (source dynamique).",
        "Société : entité\nNb Articles / Nb Clients / Qte Vendue / CA / Marge / Marge %",
        "Marge % = Marge / CA × 100",
        "Analyse de la contribution par gamme de produits, compatible pivot."
    ),
    "DS_CA_AGREGE_REPRESENTANT": (
        "CA et marge agrégés par représentant commercial (source dynamique).",
        "Société : entité\nReprésentant : vendeur\nNb Clients / Nb Documents / Qte Vendue / CA / Marge / Marge %",
        "Marge % = Marge / CA × 100",
        "Performance commerciale par vendeur, source optimisée pour les tableaux croisés."
    ),
    "DS_CA_PAR_MOIS_DYNAMIQUE": (
        "CA et marge par mois avec tous les axes d'analyse (source dynamique pour pivots).",
        "Société / Année / Mois / Période / Nb Clients / Nb Documents / Qte Vendue / CA / Marge / Marge %",
        "Marge % = Marge / CA × 100",
        "Source idéale pour les tableaux croisés temporels. Permet l'analyse Période × Commercial × Produit."
    ),
    "DS_PIVOT_VENTES_LIGNES": (
        "Source enrichie pour pivots de ventes — toutes les dimensions analytiques.",
        "Société / Date BL / Date Document / Année / Mois / Trimestre / Semestre / Période\nCode Client / Client / Région / Ville / Pays\nClassement Client / Catégorie Tarifaire\nCode Commercial / Commercial\nCode Article / Désignation / Famille / Sous Famille / Catalogue\n(+ dimensions financières)",
        "Source de faits pour les cubes analytiques de vente",
        "Source la plus complète pour construire n'importe quel axe d'analyse : géo × produit × commercial × temps."
    ),

    # ── ACHATS ────────────────────────────────────────────────────────
    "DS_ACHATS_GLOBAL": (
        "Synthèse globale des achats sur la période.",
        "Société : entité\nAchats HT / TTC : montants globaux\nNb Fournisseurs : fournisseurs actifs\nNb Documents : pièces d'achat\nQte Totale : volumes\nNb Lignes : lignes de détail\nAchat Moyen par Fournisseur : Achats HT / Nb Fournisseurs\nAchat Moyen par Document : Achats HT / Nb Documents",
        "Achat Moyen par Fournisseur = Achats HT / Nb Fournisseurs\nAchat Moyen par Document = Achats HT / Nb Documents",
        "Vue globale des dépenses fournisseurs. Première lecture du budget achats sur la période."
    ),
    "DS_ACHATS_PAR_MOIS": (
        "Évolution mensuelle des achats.",
        "Mois / Société / Achats HT / TTC / Nb Fournisseurs / Nb Documents / Qte Totale",
        "Agrégation mensuelle des pièces d'achat",
        "Suivi de la tendance des dépenses et détection des mois atypiques."
    ),
    "DS_ACHATS_PAR_FOURNISSEUR": (
        "Performance achats agrégée par fournisseur.",
        "Code Fournisseur / Fournisseur : identité\nQualite : évaluation fournisseur\nCatégorie Tarifaire : classification\nSociété : entité\nAchats HT / TTC : montants\nNb Documents / Qte Totale / Nb Articles : volumes\nAchat Moyen par Document / Prix Moyen Unitaire : indicateurs",
        "Achat Moyen = Achats HT / Nb Documents",
        "Analyse de la dépendance fournisseur et de la concentration des achats. Base des négociations tarifaires."
    ),
    "DS_ACHATS_PAR_ARTICLE": (
        "Achats agrégés par article/référence.",
        "Code Article / Designation / Famille / Société\nQte Achetee / Achats HT / Prix Moyen / CMUP Moyen / Nb Fournisseurs / Nb Documents",
        "Prix Moyen = Achats HT / Qte Achetee\nCMUP = Coût Moyen Unitaire Pondéré",
        "Identifie les articles à fort volume d'achat et les opportunités de consolidation fournisseur."
    ),
    "DS_ACHATS_PAR_FAMILLE": (
        "Achats agrégés par famille d'articles.",
        "Famille / Société / Qte Achetee / Achats HT / TTC / Nb Articles / Nb Fournisseurs / Achat Moyen par Article",
        "Achat Moyen par Article = Achats HT / Nb Articles",
        "Vue de la répartition des dépenses par catégorie de produits achetés."
    ),
    "DS_ACHATS_PAR_TYPE_DOC": (
        "Répartition des achats par type de document (Facture, BR, Commande, Avoir).",
        "Société / Nb Documents / Qte Totale / Montant HT / TTC / Nb Fournisseurs / Nb Articles",
        "Agrégation par type de document Sage",
        "Contrôle de la répartition entre types de pièces achats. Détecte les volumes anormaux d'avoirs fournisseurs."
    ),
    "DS_FACTURES_ACHATS": (
        "Détail des factures fournisseurs reçues sur la période.",
        "N Pièce : numéro facture\nCode Fournisseur / Fournisseur : émetteur\nCode Article / Designation : produit\nQuantite / Prix Unitaire / Montant HT / TTC : données\nFrais Approche : frais logistiques inclus\nSociété : entité",
        "Montant HT = Quantite × Prix Unitaire\nFrais Approche = coûts logistiques inclus dans le prix de revient",
        "Source de contrôle de la facturation fournisseur. Base du rapprochement BR / Facture."
    ),
    "DS_BONS_RECEPTION": (
        "Détail des bons de réception marchandises.",
        "N Pièce / Code Fournisseur / Fournisseur / Code Article / Designation\nQuantite / Prix Unitaire / Montant HT / N BC / Société",
        "Suivi des réceptions physiques",
        "Traçabilité des réceptions. Permet le rapprochement avec les commandes et les factures."
    ),
    "DS_COMMANDES_ACHATS": (
        "Détail des commandes fournisseurs émises.",
        "N Pièce / Code Fournisseur / Fournisseur / Code Article / Designation\nQuantite / Prix Unitaire / Montant HT / Date Livraison Prevue / Cloture / Société",
        "Suivi du statut des commandes (ouvertes/clôturées)",
        "Gestion du carnet de commandes fournisseurs et planification des approvisionnements."
    ),
    "DS_AVOIRS_ACHATS": (
        "Détail des avoirs reçus des fournisseurs.",
        "N Pièce / Code Fournisseur / Fournisseur / Code Article / Designation\nQuantite / Montant HT / TTC / Société",
        "Avoirs = montants négatifs récupérés sur fournisseurs",
        "Suivi des litiges et retours fournisseurs. Un volume élevé peut signaler des problèmes qualité."
    ),
    "DS_ACHATS_DETAIL": (
        "Détail exhaustif de toutes les lignes d'achat (toutes pièces).",
        "Société / Code Fournisseur / Fournisseur / N Pièce / Reference / Affaire / Code Affaire\nN BL / N BC / N PL / Code Article / Designation / Poids Brut / Poids Net / Lot Serie\nFrais Approche / Prix Devise / Prix Unitaire / Prix TTC\nQuantite / Montant HT / TTC / Prix Revient / Famille / Unite",
        "Prix Revient = Prix Unitaire + Frais Approche",
        "Source la plus granulaire pour l'audit des achats. Inclut les coûts logistiques et la traçabilité lot/série."
    ),
    "DS_COMMANDES_ACHATS_EN_COURS": (
        "Commandes fournisseurs non encore livrées intégralement.",
        "N Pièce / Code Fournisseur / Fournisseur / Code Article / Designation\nQte Commandee / Prix Unitaire / Montant HT / Date Livraison Prevue / Age Jours / Société",
        "Age = DATEDIFF(day, Date Commande, GETDATE())",
        "Pilotage des approvisionnements en attente. Détecte les retards fournisseurs."
    ),
    "DS_TOP_FOURNISSEURS": (
        "Classement des principaux fournisseurs par volume d'achat.",
        "Code Fournisseur / Fournisseur / Qualite / Société\nAchats HT / Nb Factures / Nb Articles / Qte Totale",
        "Classement par Achats HT décroissant",
        "Identifie les fournisseurs stratégiques et évalue le risque de dépendance."
    ),
    "DS_TOP_ARTICLES_ACHATS": (
        "Articles les plus achetés en valeur sur la période.",
        "Code Article / Designation / Famille / Société\nQte Achetee / Achats HT / Prix Moyen / Nb Fournisseurs",
        "Classement par Achats HT décroissant",
        "Identifie les articles à fort enjeu pour la négociation fournisseur."
    ),
    "DS_ACHATS_PAR_AFFAIRE": (
        "Achats rattachés à des affaires/projets.",
        "Code Affaire / Affaire / Société / Achats HT / TTC / Nb Fournisseurs / Nb Articles / Nb Documents",
        "Agrégation par code affaire Sage",
        "Suivi du budget achats par projet. Essentiel pour les entreprises en mode affaire."
    ),
    "DS_ACHATS_PAR_ACHETEUR": (
        "Performance par acheteur/responsable des achats.",
        "Société / Achats HT / TTC / Nb Fournisseurs / Nb Documents / Nb Articles",
        "Agrégation par acheteur Sage",
        "Évaluation de l'activité et de la performance des acheteurs."
    ),
    "DS_EVOLUTION_PRIX_ACHATS": (
        "Suivi de l'évolution des prix d'achat par article et par mois.",
        "Code Article / Designation / Mois / Société\nPrix Moyen / Prix Min / Prix Max / Qte Achetee / Nb Fournisseurs",
        "Prix Moyen = Achats HT / Qte Achetee sur le mois",
        "Détecte les dérives de prix fournisseur et évalue l'impact de l'inflation sur les coûts."
    ),
    "DS_ACHATS_PAR_CATALOGUE": (
        "Achats agrégés par famille catalogue.",
        "Catalogue / Société / Achats HT / Qte Achetee / Nb Articles / Nb Fournisseurs",
        "Agrégation par classification catalogue",
        "Répartition du budget achats par catégorie de produits."
    ),
    "DS_COMPARAISON_FOURNISSEURS": (
        "Comparatif des prix pratiqués par fournisseur pour un même article.",
        "Code Article / Designation / Code Fournisseur / Fournisseur / Société\nPrix Moyen / Prix Min / Prix Max / Qte Achetee / Nb Commandes / Dernier Achat",
        "Prix Moyen = Achats HT / Qte pour ce fournisseur",
        "Outil de mise en concurrence fournisseurs. Identifie les opportunités de renégociation ou de changement de source."
    ),
    "DS_ACHATS_VS_VENTES": (
        "Comparatif article par article entre prix d'achat et prix de vente.",
        "Code Article / Société\nPrix Achat Moy / Qte Achetee / Total Achats HT\nPrix Vente Moy / Qte Vendue / Total Ventes HT\nEcart / Marge Brute %",
        "Ecart = Prix Vente Moy - Prix Achat Moy\nMarge Brute % = Ecart / Prix Vente Moy × 100",
        "Vue croisée achat/vente par article. Détecte les articles vendus à perte ou à marge insuffisante."
    ),
    "DS_HISTORIQUE_PRIX_FOURNISSEUR": (
        "Historique des prix d'achat pratiqués par fournisseur et par article.",
        "Période / Code Fournisseur / Fournisseur / Code Article / Article / Société\nPrix Moyen / Prix Min / Prix Max / Qte / Montant HT",
        "Évolution mensuelle des prix unitaires",
        "Mémoire des négociations et suivi de la stabilité des prix fournisseurs."
    ),

    # ── STOCKS ────────────────────────────────────────────────────────
    "DS_MVT_STOCK_GLOBAL": (
        "Synthèse globale des mouvements de stock sur la période.",
        "Société : entité\nNb Mouvements : nombre de lignes de mouvement\nQte Entrees / Sorties : flux physiques\nValeur Entrees / Sorties : flux valorisés\nSolde Qte / Solde Valeur : bilan net",
        "Solde Qte = Qte Entrees - Qte Sorties\nSolde Valeur = Valeur Entrees - Valeur Sorties",
        "Vue d'ensemble de l'activité stock. Premier indicateur du niveau de rotation."
    ),
    "DS_MVT_PAR_DEPOT": (
        "Mouvements de stock détaillés par dépôt.",
        "Code Depot / Depot / Société\nNb Mouvements / Qte Entrees / Sorties / Valeur Entrees / Sorties / Nb Articles",
        "Solde = Entrees - Sorties par dépôt",
        "Analyse de l'activité de chaque dépôt. Identifie les dépôts sous-utilisés ou saturés."
    ),
    "DS_MVT_PAR_FAMILLE": (
        "Mouvements de stock agrégés par famille d'articles.",
        "Code Famille / Famille / Société\nNb Mouvements / Qte Entrees / Sorties / Valeur Entrees / Sorties / Nb Articles",
        "Solde = Entrees - Sorties par famille",
        "Suivi de la consommation par famille de produits."
    ),
    "DS_MVT_PAR_ARTICLE": (
        "Bilan de stock par article (entrées, sorties, solde).",
        "Code Article / Reference / Designation / Famille / Société\nQte Entrees / Sorties / Solde Qte / CMUP Moyen / Valeur Mvt Total",
        "Solde Qte = Qte Entrees - Qte Sorties\nValeur = Solde Qte × CMUP",
        "Bilan article par article. Base du contrôle d'inventaire et du réapprovisionnement."
    ),
    "DS_MVT_PAR_DOMAINE": (
        "Mouvements de stock par domaine (vente, achat, interne, etc.).",
        "Domaine / Société / Nb Mouvements / Qte Entrees / Sorties / Valeur Entrees / Sorties / Nb Articles",
        "Agrégation par domaine Sage (VT, AC, ST...)",
        "Comprendre la nature des flux : quelle part des sorties est due aux ventes vs transferts internes."
    ),
    "DS_MVT_PAR_TYPE": (
        "Mouvements par type de document générateur.",
        "Type Document / Domaine / Société / Nb Mouvements / Qte Totale / Valeur Totale / Nb Pièces / Nb Articles",
        "Agrégation par type de pièce Sage",
        "Cartographie des sources de mouvements de stock."
    ),
    "DS_MVT_ENTREES": (
        "Détail de toutes les entrées de stock sur la période.",
        "Date / Type / Domaine / N Pièce / Code Article / Designation / Code Depot / Depot\nQuantite / Prix Unitaire / Valeur / Lot Serie / Société",
        "Valeur = Quantite × Prix Unitaire",
        "Traçabilité complète des entrées. Base des contrôles de réception et de valorisation."
    ),
    "DS_MVT_SORTIES": (
        "Détail de toutes les sorties de stock sur la période.",
        "Date / Type / Domaine / N Pièce / Code Article / Designation / Code Depot / Depot\nQuantite / Prix Unitaire / Valeur / Lot Serie / Société",
        "Valeur = Quantite × CMUP à la date de sortie",
        "Traçabilité des consommations et expéditions. Analyse des causes de déstockage."
    ),
    "DS_STOCK_ACTUEL": (
        "Niveau de stock actuel par article et par dépôt.",
        "Code Article / Reference / Designation / Famille / Code Depot / Depot / Société\nStock Actuel : quantité en stock\nDernier CMUP : coût moyen unitaire pondéré\nValeur Stock : Stock × CMUP\nDernier Mouvement : date du dernier mouvement",
        "Valeur Stock = Stock Actuel × Dernier CMUP",
        "Photographie du stock à l'instant T. Base de l'inventaire et du suivi de ruptures."
    ),
    "DS_STOCK_PAR_DEPOT": (
        "Valorisation du stock total par dépôt.",
        "Code Depot / Depot / Société / Nb Articles / Stock Total Qte / Valeur Stock",
        "Valeur Stock = somme(Stock × CMUP) par dépôt",
        "Répartition de la valeur immobilisée en stock par entrepôt."
    ),
    "DS_MVT_PAR_MOIS": (
        "Évolution mensuelle des flux de stock.",
        "Mois / Société / Nb Mouvements / Qte Entrees / Sorties / Valeur Entrees / Sorties / Nb Articles",
        "Agrégation mensuelle des mouvements",
        "Détection de la saisonnalité des flux de stock."
    ),
    "DS_MVT_VENTES": (
        "Mouvements de stock générés par les ventes (sorties commerciales).",
        "Date / Type / N Pièce / Code Article / Designation / Code Depot\nQuantite / Prix Vente / Prix Revient / Valeur Stock / Marge / Société",
        "Marge = Prix Vente - Prix Revient\nValeur Stock = Qte × CMUP",
        "Analyse de la contribution des ventes aux sorties de stock avec la marge associée."
    ),
    "DS_MVT_ACHATS": (
        "Mouvements de stock générés par les achats (entrées fournisseurs).",
        "Date / Type / N Pièce / Code Article / Designation / Code Depot\nQuantite / Prix Achat / Valeur Stock / Société",
        "Valeur Stock = Qte × Prix Achat",
        "Traçabilité des entrées fournisseurs et impact sur la valorisation du stock."
    ),
    "DS_MVT_INTERNES": (
        "Mouvements de stock internes (transferts inter-dépôts, ajustements).",
        "Date / Type / N Pièce / Code Article / Designation / Code Depot / Depot / Sens / Quantite / Valeur / Société",
        "Sens = Entrée (+) ou Sortie (-)\nValeur = Qte × CMUP",
        "Suivi des transferts internes et des régularisations d'inventaire."
    ),
    "DS_STOCK_ROTATION": (
        "Taux de rotation et couverture de stock par article.",
        "Code Article / Reference / Designation / Famille / Société\nStock Actuel / CMUP / Valeur Stock\nSorties 12M : quantité sortie sur 12 mois glissants\nCouverture Jours : jours de stock restants\nTaux Rotation : Sorties 12M / Stock Actuel",
        "Couverture Jours = Stock Actuel / (Sorties 12M / 365)\nTaux Rotation = Sorties 12M / Stock Actuel",
        "Identifie les articles surStockés (faible rotation) et les risques de rupture (stock bas). Base des décisions de réapprovisionnement."
    ),
    "DS_STOCK_DORMANT": (
        "Articles sans mouvement depuis une longue période (stock dormant).",
        "Code Article / Reference / Designation / Famille / Société\nStock Qte / CMUP / Valeur Stock\nDernier Mouvement : date du dernier flux\nJours Sans Mvt : ancienneté d'immobilisation",
        "Jours Sans Mvt = DATEDIFF(day, Dernier Mouvement, GETDATE())",
        "Détecte le stock obsolète et immobilisé. Aide à déclencher des actions de déstockage ou de dépréciation."
    ),
    "DS_MVT_DETAIL": (
        "Détail exhaustif de tous les mouvements de stock (toutes natures).",
        "Date / Type / Domaine / Sens / N Pièce\nCode Article / Reference / Designation / Famille\nCode Depot / Depot / Quantite / Prix Unitaire / Prix Revient / Valeur Stock / Lot Serie / Société",
        "Valeur Stock = Qte × Prix Revient ou CMUP selon le paramétrage",
        "Source la plus granulaire de l'inventaire. Base des audits de stock et du contrôle interne."
    ),
    "DS_MVT_PAR_LOT": (
        "Mouvements de stock regroupés par numéro de lot ou série.",
        "Lot Serie / Code Article / Designation / Société\nNb Mouvements / Qte Entrees / Sorties / Solde Qte / Premier Mvt / Dernier Mvt",
        "Solde Qte = Qte Entrees - Qte Sorties par lot",
        "Traçabilité par lot et numéro de série. Essentiel pour les industries soumises à des obligations de traçabilité (agroalimentaire, pharmaceutique)."
    ),
    "DS_TOP_ARTICLES_MVT": (
        "Articles les plus actifs en termes de mouvements de stock.",
        "Code Article / Reference / Designation / Famille / Société\nNb Mouvements / Qte Sorties / Valeur Sorties / Qte Entrees / Nb Pièces",
        "Classement par Nb Mouvements décroissant",
        "Identifie les articles qui sollicitent le plus le stock. Base de l'optimisation de l'emplacement en entrepôt."
    ),
    "DS_MVT_CATALOGUE": (
        "Mouvements de stock agrégés par catalogue.",
        "Catalogue / Société / Nb Mouvements / Qte Entrees / Sorties / Valeur Sorties / Nb Articles",
        "Agrégation par famille catalogue",
        "Analyse de l'activité de stock par famille de produits."
    ),
    "DS_STOCK_VALORISATION": (
        "Valorisation du stock selon plusieurs méthodes (CMUP, Prix Revient, DPA).",
        "Code Article / Reference / Designation / Famille / Société\nStock Qte / CMUP / Valeur CMUP / Prix Revient / Valeur Prix Revient\nDPA Periode / Valeur DPA / Cout Standard / Valeur Cout Standard / Ecart CMUP vs Revient",
        "Valeur CMUP = Stock Qte × CMUP\nValeur PR = Stock Qte × Prix Revient\nEcart = Valeur CMUP - Valeur Prix Revient",
        "Analyse de l'impact du choix de valorisation sur la valeur totale du stock. Aide à la clôture comptable."
    ),
    "DS_STOCK_COUVERTURE": (
        "Couverture de stock et alertes de réapprovisionnement.",
        "Code Article / Reference / Designation / Famille / Société\nStock Actuel / CMUP / Valeur Stock\nVente Moy/Mois : sorties moyennes mensuelles sur 12 mois\nCouverture Mois : mois de stock restants\nAlerte : flag déclenchant une alerte (stock bas, rupture imminente)",
        "Couverture Mois = Stock Actuel / Vente Moy par Mois\nAlerte si Couverture < seuil paramétré",
        "Outil de gestion des approvisionnements. Signale les articles en risque de rupture avant qu'elle survienne."
    ),
    "DS_STOCK_PEREMPTION": (
        "Stock avec suivi des dates de péremption par lot.",
        "Code Article / Reference / Designation / Famille / Lot / Code Depot / Depot / Société\nDate Peremption / Date Fabrication / Stock Qte / CMUP / Valeur Stock / Jours Restants / Statut",
        "Jours Restants = DATEDIFF(day, GETDATE(), Date Peremption)\nStatut = Expiré / Critique / Normal",
        "Contrôle de la DLC/DLUO. Prioritaire pour les secteurs alimentaire, pharmaceutique et cosmétique."
    ),
    "DS_MVT_INTER_DEPOTS": (
        "Transferts de marchandises entre dépôts.",
        "Date / N Pièce / Code Article / Designation / Famille / Code Depot / Depot / Sens / Quantite / Valeur / Société",
        "Sens = Sortie du dépôt source, Entrée dans le dépôt cible",
        "Traçabilité des transferts inter-sites. Aide à l'optimisation de la répartition du stock entre dépôts."
    ),
    "DS_ARTICLES_COMPOSES": (
        "Mouvements et stock des articles composés (nomenclatures).",
        "Code Article / Reference / Designation / Famille / Article Compose / Société\nNb Mouvements / Qte Entrees / Sorties / Solde Qte / CMUP / Valeur Stock",
        "Solde Qte = Qte Entrees - Qte Sorties\nValeur = Solde × CMUP",
        "Gestion des articles à nomenclature. Suivi de la production et de la consommation des composants."
    ),

    # ── COMPTABILITÉ ─────────────────────────────────────────────────
    "DS_ECRITURES_GLOBAL": (
        "Synthèse globale des écritures comptables sur la période.",
        "Société : entité\nNb Ecritures : volume d'écritures\nTotal Debit / Total Credit : flux comptables\nSolde : Total Débit - Total Crédit\nNb Comptes / Nb Journaux : profondeur d'analyse",
        "Solde = Total Débit - Total Crédit",
        "Vue macro de l'activité comptable sur la période. Premier indicateur de la volumétrie de traitement."
    ),
    "DS_ECRITURES_PAR_JOURNAL": (
        "Activité comptable par journal (Achats, Ventes, Banque, OD, etc.).",
        "Journal / Type Journal / Société / Nb Ecritures / Total Debit / Total Credit / Nb Pièces",
        "Agrégation par journal Sage",
        "Contrôle de la complétude des saisies par journal. Détecte les journaux non clôturés ou vides."
    ),
    "DS_ECRITURES_PAR_COMPTE": (
        "Solde de chaque compte comptable sur la période.",
        "Compte / Intitule / Société / Total Debit / Total Credit / Solde / Nb Ecritures",
        "Solde = Total Débit - Total Crédit",
        "Revue analytique des comptes. Base de la balance de contrôle."
    ),
    "DS_ECRITURES_PAR_TIERS": (
        "Activité comptable agrégée par tiers (clients et fournisseurs).",
        "Code Tiers / Tiers / Type (client/fournisseur) / Société\nTotal Debit / Total Credit / Solde / Nb Ecritures / Nb Pièces",
        "Solde = Total Débit - Total Crédit",
        "Balance tiers comptable. Rapprochement avec la balance commerciale."
    ),
    "DS_ECRITURES_PAR_MOIS": (
        "Volume et montants des écritures comptables par mois.",
        "Annee / Société / Nb Ecritures / Total Debit / Total Credit / Nb Comptes / Nb Pièces",
        "Agrégation mensuelle",
        "Suivi du rythme de saisie comptable et détection des mois de sur/sous-activité."
    ),
    "DS_ECRITURES_DETAIL": (
        "Détail ligne par ligne de toutes les écritures comptables.",
        "Date / Journal / Pièce / Compte / Intitule Compte / Tiers / Libelle / Echéance / Mode de Règlement / Société",
        "Source : F_ECRITUREC Sage",
        "Journal comptable complet. Base de tout audit comptable et de la révision des comptes."
    ),
    "DS_GRAND_LIVRE": (
        "Grand livre comptable avec toutes les écritures par compte.",
        "Compte / Intitule / Date / Pièce / Libelle / Tiers / Société",
        "Source : F_ECRITUREC trié par compte et date",
        "Document de référence pour la révision comptable. Affiche l'historique chronologique de chaque compte."
    ),
    "DS_BALANCE_GENERALE": (
        "Balance comptable générale avec soldes débiteurs et créditeurs.",
        "Compte / Intitule / Nature / Société\nA Nouveau : report à nouveau\nMvt Debit / Mvt Credit : mouvements de la période\nTotal Debit / Total Credit : cumuls\nSolde / Solde Debiteur / Solde Crediteur : positions nettes",
        "Solde Débiteur = MAX(Total Débit - Total Crédit, 0)\nSolde Créditeur = MAX(Total Crédit - Total Débit, 0)",
        "Document comptable de référence. Base de la liasse fiscale et des états financiers."
    ),
    "DS_BILAN_ACTIF": (
        "Synthèse de l'actif du bilan.",
        "Société / Montant : valeur totale de l'actif / Nb Comptes : nombre de comptes actifs",
        "Agrégation des comptes de classe 1-5 côté actif",
        "Vision synthétique du patrimoine de l'entreprise côté emplois."
    ),
    "DS_ACTIF_IMMOBILISE": (
        "Détail de l'actif immobilisé (immobilisations corporelles et incorporelles).",
        "Classe / Société / Valeur Brute / Amortissements / Valeur Nette",
        "Valeur Nette = Valeur Brute - Amortissements",
        "État du patrimoine immobilisé. Base du tableau des immobilisations."
    ),
    "DS_ACTIF_CIRCULANT": (
        "Détail de l'actif circulant (stocks, créances, trésorerie).",
        "Categorie / Société / Montant",
        "Agrégation des comptes 3xx, 4xx clients, 5xx",
        "Analyse de la liquidité à court terme."
    ),
    "DS_BILAN_PASSIF": (
        "Synthèse du passif du bilan.",
        "Société / Montant : total des ressources / Nb Comptes",
        "Agrégation des comptes côté passif",
        "Vision des ressources : capitaux propres + dettes."
    ),
    "DS_CAPITAUX_PROPRES": (
        "Détail des capitaux propres (capital, réserves, résultat).",
        "Compte / Intitule / Société / Montant",
        "Agrégation des comptes de classe 1 (capitaux)",
        "Suivi de la situation nette et de l'évolution des fonds propres."
    ),
    "DS_DETTES": (
        "Détail des dettes fournisseurs et autres dettes.",
        "Fournisseur / Société / Montant / Nb Ecritures",
        "Agrégation des comptes fournisseurs (40x)",
        "Analyse de l'endettement commercial. Base de la gestion des règlements fournisseurs."
    ),
    "DS_CPC_GLOBAL": (
        "Compte de Produits et Charges (CPC) — résultat global de l'exercice.",
        "Société\nVentes Marchandises / Ventes Biens Services / Variation Stocks Produits / Immob Produites / Subventions Exploitation → Total Produits Exploitation\nAchats Marchandises / Achats Matières / Autres Charges Externes / Charges Personnel / Dotations Amortissements → Total Charges Exploitation\nResultat Exploitation / Produits Financiers / Charges Financieres / Resultat Net",
        "Résultat Exploitation = Total Produits - Total Charges\nRésultat Net = Résultat Exploitation + Résultat Financier",
        "Compte de résultat de l'entreprise. Document de référence pour les actionnaires et les banques."
    ),
    "DS_CPC_PRODUITS": (
        "Détail des produits du CPC par classe de compte.",
        "Classe / Société / Montant / Nb Comptes",
        "Agrégation des comptes de produits (7xx)",
        "Analyse détaillée des sources de revenus."
    ),
    "DS_CPC_CHARGES": (
        "Détail des charges du CPC par classe de compte.",
        "Classe / Société / Montant / Nb Comptes",
        "Agrégation des comptes de charges (6xx)",
        "Analyse détaillée des dépenses d'exploitation."
    ),
    "DS_CPC_PAR_MOIS": (
        "Évolution mensuelle du résultat (produits, charges, résultat).",
        "Annee / Société / Produits / Charges / Resultat",
        "Résultat mensuel = Produits - Charges",
        "Suivi du résultat en cours d'exercice. Détecte les mois déficitaires."
    ),
    "DS_BILAN_SYNTHETIQUE": (
        "Bilan synthétique — grandes masses actif/passif.",
        "Société\nActif : Immob Brut / Amortissements / Actif Immobilisé Net / Stocks / Créances / Trésorerie Actif\nPassif : Capitaux Propres / Dettes\nTotal Actif / Total Passif",
        "Total Actif = Total Passif (équilibre bilan)\nActif Immobilisé Net = Immob Brut - Amortissements",
        "Vision consolidée du bilan. Idéal pour les présentations aux partenaires financiers."
    ),
    "DS_ANALYTIQUE_GLOBAL": (
        "Comptabilité analytique — charges et produits par section.",
        "Plan / Compte / Intitule / Société / Montant / Quantite / Nb Ecritures",
        "Source : F_ECRITUREA Sage (écritures analytiques)",
        "Analyse de rentabilité par centre de coût/profit."
    ),
    "DS_ANALYTIQUE_PAR_PLAN": (
        "Synthèse analytique par plan comptable analytique.",
        "Plan / Société / Total Montant / Total Quantite / Nb Ecritures / Nb Comptes",
        "Agrégation par plan analytique Sage",
        "Vue synthétique de la performance par centre analytique."
    ),
    "DS_ANALYTIQUE_DETAIL": (
        "Détail des écritures analytiques par compte.",
        "Plan / Compte Analytique / Intitule / Montant / Quantite / Société",
        "Source : F_ECRITUREA",
        "Détail des affectations analytiques. Base de la répartition des coûts."
    ),
    "DS_TRESORERIE": (
        "Position de trésorerie par compte bancaire.",
        "Compte / Intitule / Société / Solde Initial / Encaissements / Decaissements / Solde Final",
        "Solde Final = Solde Initial + Encaissements - Décaissements",
        "Tableau de bord de la trésorerie. Essentiel pour la gestion de la liquidité."
    ),
    "DS_TRESORERIE_PAR_MOIS": (
        "Flux de trésorerie mensuels (encaissements et décaissements).",
        "Annee / Société / Encaissements / Decaissements / Flux Net",
        "Flux Net = Encaissements - Décaissements",
        "Suivi de la génération de cash sur l'exercice. Base du prévisionnel de trésorerie."
    ),
    "DS_ECHEANCES_COMPTABLES": (
        "Échéances comptables à venir ou en retard.",
        "Echéance / Compte / Tiers / Pièce / Libelle / Mode de Règlement / Société / Jours Avant Echéance",
        "Jours Avant Echéance = DATEDIFF(day, GETDATE(), Date Echéance)",
        "Gestion prévisionnelle des encaissements et décaissements. Base du plan de trésorerie."
    ),
    "DS_LETTRAGE": (
        "État du lettrage des comptes tiers (rapprochement facture/règlement).",
        "Compte / Intitule / Société / Nb Lettrees / Nb Non Lettrees / Solde Non Lettre",
        "Solde Non Lettré = somme des écritures non encore rapprochées",
        "Contrôle de la qualité du lettrage comptable. Un solde non lettré élevé signale des écarts à corriger."
    ),

    # ── RECOUVREMENT ─────────────────────────────────────────────────
    "DS_REC_BALANCE_AGEE_COMPLETE": (
        "Analyse complète de l'encours client par tranches d'ancienneté à une date donnée.\nPermet de piloter le recouvrement, mesurer la performance des encaissements (DSO)\net quantifier le coût financier du crédit client.",
        "Societe : société commerciale source\nClient : code + intitulé client\nTiers Payeur : payeur réel si différent du client facturé\nRepresentant : commercial responsable du client\nVille / Region : localisation géographique\nCaution : encours d'autorisation accordé\nNon Echu : créances dont l'échéance est après la date de fin\n0-30 jours / 31-60 / 61-90 / 91-120 / Plus de 120 jours : tranches de retard\nEncours Total / Echu / Non Echu : synthèse des créances\nReglements Non Echus / BL Non Factures / Impayes / Reglements Non Imputes : compléments\nChiffre Affaires : CA facturé sur la période\nDSO Global / DSO Retard / DSO Contractuel : délais de paiement (jours)\nCout DSO CA / Cout DSO Encours : coût financier à 8%/an\nFactures Retour / Taux Retour : retours marchandise\nAvoirs Financiers / Taux Avoirs : avoirs accordés\nNb Echeances / Nb Echeances Echues : compteurs",
        "DSO Global = Encours Total × Nb jours période / CA période\nDSO Retard = Encours Échu × Nb jours période / CA période\nDSO Contractuel = Encours Non Échu × Nb jours période / CA période\nCoût DSO = Montant × 8% × (Nb jours / 365)\nTranches = DATEDIFF(day, Date Échéance, @dateFin) → 6 intervalles\nSource : Échéances_Ventes jointure règlements au @dateFin",
        "Vue consolidée par client : balance âgée 6 tranches + DSO + coût financier.\nIdentifie les clients à risque, le coût du crédit et les anomalies.\nIndispensable pour le responsable recouvrement et la direction financière."
    ),
    "DS_BALANCE_AGEE": (
        "Balance âgée des créances clients par tranches de retard.",
        "Code Client / Client / Société\nNon Échu : pas encore en retard\n0-30j / 31-60j / 61-90j / 91-120j / +120j : tranches de retard\nTotal Créance / Total Échu : synthèse\nNb Échéances / Max Retard Jours : indicateurs de gravité",
        "Tranches calculées par DATEDIFF(day, Date Échéance, GETDATE())\nTotal Échu = somme des tranches 0-30j à +120j",
        "Outil principal du recouvrement. Classe les clients par urgence de relance."
    ),
    "DS_DSO": (
        "Délai moyen de paiement et DSO par client.",
        "Code Client / Client / Société\nEncours : créances en cours\nCA 12 Mois : chiffre d'affaires sur 12 mois glissants\nReglé 12 Mois : encaissements sur 12 mois\nDélai Moyen Paiement : historique des délais\nNb Règlements : volume d'activité\nDSO Jours : Days Sales Outstanding",
        "DSO = Encours × 365 / CA 12 Mois\nDélai Moyen = moyenne des DATEDIFF(Émission, Règlement)",
        "Mesure l'efficacité du recouvrement client. Un DSO élevé signale un risque de trésorerie."
    ),
    "DS_CREANCES_DOUTEUSES": (
        "Créances de plus de 120 jours de retard (potentiellement irrécouvrables).",
        "Code Client / Client / Société\nMontant +120j : encours en retard de plus de 4 mois\nTotal Créance : encours total\n% Douteux : part du créances à risque\nNb Echéances +120j : nombre de factures concernées\nMax Retard Jours : retard maximum",
        "% Douteux = Montant +120j / Total Créance × 100",
        "Identification des créances à provisionner comptablement. Base de la politique de provisionnement."
    ),
    "DS_ECHEANCES_NON_REGLEES": (
        "Détail de chaque échéance client non encore réglée.",
        "Société / Code Client / Client / Code Tier Payeur / Tier Payeur\nNuméro Pièce / Date Document / Date Échéance\nMontant Échéance / Montant TTC / Montant Réglé / Reste à Régler\nMode de Règlement / Jours de Retard / Tranche Age",
        "Reste à Régler = Montant Échéance - Montant Réglé\nJours de Retard = DATEDIFF(day, Date Échéance, GETDATE())",
        "Listing de relance opérationnel. Chaque ligne est une échéance à recouvrer."
    ),
    "DS_ECHEANCES_PAR_CLIENT": (
        "Balance âgée enrichie par client avec taux de recouvrement.",
        "Code Client / Client / Société\nNb Échéances / Total Échéances / Total Réglé / Reste à Régler\nA Echoir / 0-30j / 31-60j / 61-90j / 91-120j / +120j\nTaux Recouvrement % / Dernière Echéance / Max Jours Retard",
        "Taux Recouvrement % = Total Réglé / Total Échéances × 100\nA Echoir = échéances futures non encore dues",
        "Synthèse par client avec efficacité du recouvrement. Identifie les bons et mauvais payeurs."
    ),
    "DS_ECHEANCES_PAR_COMMERCIAL": (
        "Encours et retards par commercial — responsabilité de portefeuille.",
        "Code Commercial / Commercial / Nb Clients / Nb Échéances\nEncours Total / A Echoir / 0-30j / 31-60j / 61-90j / 91-120j / +120j",
        "Agrégation des échéances non réglées par responsable commercial",
        "Attribue les impayés aux commerciaux responsables. Base des objectifs de recouvrement par vendeur."
    ),
    "DS_ECHEANCES_PAR_MODE": (
        "Répartition des impayés par mode de règlement.",
        "Mode de Règlement / Code Mode / Nb Échéances\nTotal Échéances / Reste à Régler / Taux Recouvrement % / Retard Moyen Jours",
        "Taux Recouvrement % = (Total - Reste) / Total × 100",
        "Identifie les modes de règlement les plus risqués (chèque, traite, virement). Aide à adapter les conditions de paiement."
    ),
    "DS_ECHEANCES_A_ECHOIR": (
        "Échéances futures non encore dues — prévision d'encaissements.",
        "Société / Code Client / Client / Numéro Pièce / Date Document / Date Échéance\nMontant à Régler / Mode de Règlement / Commercial / Jours Avant Échéance / Urgence",
        "Jours Avant Échéance = DATEDIFF(day, GETDATE(), Date Échéance)\nUrgence = flag si < 7 jours",
        "Prévision des encaissements à venir. Permet d'anticiper les relances préventives avant échéance."
    ),
    "DS_REGLEMENTS_PAR_PERIODE": (
        "Évolution mensuelle des encaissements clients.",
        "Annee / Mois / Période / Nb Règlements / Total Règlements / Nb Clients / Délai Moyen Jours",
        "Délai Moyen = moyenne des DATEDIFF(Date Facture, Date Règlement)",
        "Suivi de la performance d'encaissement mois par mois. Détecte les mois avec pic ou creux de trésorerie."
    ),
    "DS_REGLEMENTS_PAR_CLIENT": (
        "Historique des règlements reçus par client.",
        "Code Client / Client / Société / Nb Règlements / Total Réglé\nPremier Règlement / Dernier Règlement / Délai Moyen Jours",
        "Délai Moyen = moyenne des délais de paiement historiques",
        "Profil de paiement de chaque client. Base pour ajuster les conditions de crédit."
    ),
    "DS_REGLEMENTS_PAR_MODE": (
        "Répartition des règlements reçus par mode de paiement.",
        "Mode de Règlement / Nb Règlements / Total Réglé / Nb Clients / Délai Moyen Jours",
        "Délai Moyen = moyenne par mode de règlement",
        "Analyse des canaux d'encaissement. Identifie les modes les plus rapides pour optimiser les conditions."
    ),
    "DS_FACTURES_NON_REGLEES": (
        "Factures émises non encore intégralement réglées.",
        "Société / Code Client / Client / Numéro Pièce / Date Document\nMontant TTC / Montant Réglé / Reste à Régler / Age Jours",
        "Reste à Régler = Montant TTC - Montant Réglé\nAge = DATEDIFF(day, Date Document, GETDATE())",
        "Liste opérationnelle des factures en attente. Différent des échéances : vue par facture entière."
    ),
    "DS_KPI_RECOUVREMENT": (
        "Indicateurs clés du recouvrement — tableau de bord synthétique.",
        "Encours Total : total des créances en cours\nA Echoir : part non encore due\nEchu : part en retard\nNb Echéances Retard / Nb Clients Retard : volumétrie\nReglements Mois : encaissements du mois\nRetard Moyen Jours : délai moyen de retard",
        "Calculs en temps réel sur l'ensemble du portefeuille",
        "Dashboard de direction pour le recouvrement. Une seule ligne = vision complète de la situation créances."
    ),
    "DS_PREVISION_ENCAISSEMENTS": (
        "Prévision des encaissements par semaine.",
        "Période / Semaine / Société / Nb Échéances / Nb Clients\nMontant Total / Déjà Réglé / Reste à Encaisser / Retard / A Venir",
        "Reste à Encaisser = Montant Total - Déjà Réglé\nRetard = échéances passées non réglées\nA Venir = échéances futures",
        "Prévisionnel de trésorerie à court terme basé sur les échéances clients."
    ),
    "DS_COMPORTEMENT_PAIEMENT": (
        "Analyse comportementale du profil de paiement de chaque client.",
        "Période / Délai Moyen / Nb Échéances / Montant Total / Code Client / Client / Société\nDélai Moyen Jours : habitude de paiement\nProfil Paiement : classification (ponctuel, retardataire, etc.)",
        "Délai Moyen = DATEDIFF(Date Emission, Date Règlement) en moyenne sur 12 mois",
        "Segmentation des clients par comportement de paiement. Base des politiques de crédit différenciées."
    ),

    # ── ANALYSE CLIENTS ──────────────────────────────────────────────
    "DS_PANIER_MOYEN_CLIENT": (
        "Analyse du panier moyen d'achat par client.",
        "Code Client / Client / Société\nNb Factures / CA HT Total / Panier Moyen HT\nNb Articles Distincts / Lignes Moy par Facture\nPremiere Vente / Derniere Vente / Ancienneté Jours",
        "Panier Moyen HT = CA HT Total / Nb Factures\nAncienneté = DATEDIFF(day, Première Vente, GETDATE())",
        "Profilage commercial des clients. Identifie les clients à fort panier à fidéliser."
    ),
    "DS_CLIENTS_NOUVEAUX": (
        "Clients ayant effectué leur premier achat sur la période.",
        "Date Premier Achat / Code Client / Client / Société\nCA HT Période / Nb Factures / Nb Articles",
        "Critère : Date Premier Achat dans la période sélectionnée",
        "Suivi de l'acquisition client. Mesure l'efficacité de la prospection commerciale."
    ),
    "DS_CLIENTS_PERDUS": (
        "Clients n'ayant pas acheté depuis un certain temps (clients perdus).",
        "Code Client / Client / Société\nDernière Vente / Jours Sans Achat\nCA HT Année Précédente / Nb Factures Année Précédente",
        "Jours Sans Achat = DATEDIFF(day, Dernière Vente, GETDATE())",
        "Identification des clients inactifs à réactiver. Base des campagnes de reconquête."
    ),
    "DS_SEGMENTATION_ABC": (
        "Segmentation ABC des clients par contribution au CA.",
        "Code Client / Client / Société / CA HT / CA Cumulé / CA Total / Rang / % Cumulé / Segment",
        "Segment A = 0-70% du CA cumulé\nSegment B = 70-90%\nSegment C = 90-100%",
        "Loi de Pareto appliquée aux clients. 20% des clients font généralement 80% du CA."
    ),
    "DS_CONCENTRATION_RISQUE": (
        "Analyse de la concentration du CA sur les principaux clients.",
        "Code Client / Client / Société / CA HT / CA Total / % du CA Total / Niveau Risque",
        "% du CA Total = CA Client / CA Total × 100\nNiveau Risque = fort si > 10% du CA",
        "Mesure la dépendance à certains clients majeurs. Un risque de concentration élevé peut fragiliser l'entreprise."
    ),
    "DS_EVOLUTION_ABC": (
        "Évolution du classement ABC client entre deux années.",
        "Code Client / Client / Société\nCA N / Segment N / CA N-1 / Segment N-1 / Evolution CA / Mouvement",
        "Mouvement = comparaison Segment N vs Segment N-1 (montée/descente/stable)",
        "Détecte les clients qui progressent ou régressent dans le classement. Cible les actions prioritaires."
    ),
    "DS_MATRICE_CLIENT_ARTICLE": (
        "Croisement client × article — quels clients achètent quels produits.",
        "Code Client / Client / Code Article / Article / Catalogue / Gamme / Société\nQte Totale / CA HT / Nb Commandes / Premier Achat / Dernier Achat",
        "Agrégation par couple (client, article)",
        "Analyse des associations produit/client. Identifie les opportunités de vente croisée."
    ),

    # ── PERFORMANCE COMMERCIALE ──────────────────────────────────────
    "DS_TAUX_TRANSFORMATION": (
        "Taux de conversion devis → commande par période.",
        "Annee / Mois / Période / Société\nNb Devis / Montant Devis HT\nNb Commandes / Montant Commandes HT\nTaux Transformation % / Taux Transformation Montant %",
        "Taux Transformation % = Nb Commandes issus de Devis / Nb Devis × 100\nTaux Transformation Montant % = Montant Commandes issues de Devis / Montant Devis × 100",
        "Mesure l'efficacité commerciale dans la transformation des offres en ventes."
    ),
    "DS_PIPELINE_COMMERCIAL": (
        "Pipeline commercial — volume de documents par étape.",
        "Etape / Société / Nb Documents / Nb Lignes / Montant HT / TTC / Nb Clients / Nb Articles / Qte Totale",
        "Étapes = Devis → BC → BL → Facture",
        "Vision du funnel commercial. Identifie les goulots d'étranglement dans le processus de vente."
    ),
    "DS_DELAIS_ETAPES": (
        "Délais de traitement entre étapes du processus commercial.",
        "Société / Période / Nb Documents\nDélai BC vers BL (j) / Délai BL vers Facture (j) / Délai Total BC vers Facture (j)\nMin / Max Délai BC-BL",
        "Délai BC→BL = DATEDIFF(day, Date BC, Date BL)\nDélai BL→Facture = DATEDIFF(day, Date BL, Date Facture)",
        "Analyse des délais opérationnels. Identifie les retards de traitement et les commandes en souffrance."
    ),
    "DS_PORTEFEUILLE_COMMERCIAL": (
        "Portefeuille de clients par commercial.",
        "Code Commercial / Commercial / Code Client / Client / Société\nCA HT / Marge / Nb Documents / Premier Achat / Dernier Achat / Jours Sans Achat",
        "Jours Sans Achat = DATEDIFF(day, Dernier Achat, GETDATE())",
        "Vue du portefeuille de chaque commercial. Identifie les clients à risque d'inactivité par vendeur."
    ),

    # ── MARGES ───────────────────────────────────────────────────────
    "DS_MARGE_PAR_GAMME": (
        "Rentabilité des ventes par gamme de produits.",
        "Gamme / Sous Gamme / Société / CA HT / Coût Revient / Marge / Marge % / Qte Vendue / Nb Articles",
        "Marge = CA HT - Coût Revient\nMarge % = Marge / CA HT × 100",
        "Analyse de la rentabilité par famille de produits. Guide les décisions de politique tarifaire par gamme."
    ),
    "DS_MARGE_NEGATIVE": (
        "Ventes réalisées avec une marge négative (vendues à perte).",
        "Société / Date / Num Pièce / Code Client / Client / Code Article / Designation\nCatalogue / Gamme / Qte / PU HT / Coût Revient / CA HT / Marge / Marge %\nCode Commercial / Commercial",
        "Marge = CA HT - Coût Revient (valeur négative)\nMarge % = Marge / CA HT × 100 (valeur négative)",
        "Alerte sur les ventes déficitaires. Chaque ligne est une vente qui dégrade la rentabilité globale."
    ),
    "DS_CONTRIBUTION_MARGINALE": (
        "Classement des clients par contribution marginale au CA (pareto étendu).",
        "Code Client / Client / Société / CA HT / Marge / Rang / CA Cumulé / CA Total / Marge Totale\n% CA / % CA Cumulé / % Marge",
        "% CA = CA Client / CA Total × 100\n% CA Cumulé = somme cumulative triée par CA décroissant",
        "Analyse de Pareto enrichie avec la marge. Identifie les clients qui contribuent le plus à la rentabilité réelle."
    ),

    # ── LOGISTIQUE & QUALITÉ ─────────────────────────────────────────
    "DS_BL_NON_FACTURES": (
        "Bons de livraison expédiés non encore facturés.",
        "Société / Num BL / Code Client / Client / Code Article / Designation\nQte BL / Montant HT / Code Depot / Depot / Age BL Jours",
        "Age BL = DATEDIFF(day, Date BL, GETDATE())",
        "Détecte le chiffre d'affaires non encore encaissé faute de facturation. Un BL âgé > 30 jours est une anomalie."
    ),
    "DS_DOCUMENTS_ANOMALIE": (
        "Documents présentant des anomalies (BL sans BC, factures sans BL, etc.).",
        "Type Anomalie / Num Pièce / Date Document / Client / Montant HT / Age Jours",
        "Anomalies : BL sans facture, facture sans BL, commande sans livraison, devis expiré",
        "Outil de contrôle qualité des flux commerciaux. Chaque ligne nécessite une action corrective."
    ),

    # ── TABLEAU DE BORD GLOBAL ───────────────────────────────────────
    "DS_COMPARATIF_ANNUEL": (
        "Comparatif des performances commerciales sur plusieurs années.",
        "Annee / CA HT / TTC / Marge / Marge % / Nb Clients / Nb Documents / Nb Lignes / Qte Totale\nPoids Net Total / Ticket Moyen HT / CA Moy par Client / Lignes Moy par Doc / Remise HT / Taux Remise %",
        "Ticket Moyen = CA HT / Nb Documents\nCA Moy par Client = CA HT / Nb Clients\nTaux Remise % = Remise HT / (CA HT + Remise HT) × 100",
        "Vue historique multi-années de la performance commerciale. Référence pour les présentations de direction."
    ),
    "DS_COMPARATIF_ANNUEL_PIVOT": (
        "Tableau croisé N vs N-1 avec écarts et évolutions.",
        "Annee N / Annee N-1\nCA HT N/N-1 / Ecart CA HT / Evol CA %\nCA TTC N/N-1\nMarge N/N-1 / Ecart Marge / Evol Marge % / Marge % N/N-1 / Ecart Marge %\nNb Clients N/N-1 / Ecart / Evol %\nNb Documents N/N-1 / Ecart\nNb Lignes / Qte Totale",
        "Ecart = Valeur N - Valeur N-1\nEvol % = Ecart / Valeur N-1 × 100",
        "Rapport de performance annuelle avec comparaison automatique N/N-1. Format idéal pour les revues de direction."
    ),
    "DS_COMPARATIF_MENSUEL": (
        "Comparatif mensuel N vs N-1 avec évolutions.",
        "Mois / Mois Label / Annee N / Annee N-1\nCA HT N/N-1 / Ecart CA / Evol CA %\nMarge N/N-1 / Ecart Marge / Marge % N/N-1\nNb Clients N/N-1 / Ecart\nNb Documents N/N-1 / Ecart\nQte N/N-1 / Ecart Qte\nTicket Moyen N/N-1 / CA Moy Client N",
        "Ecart = Valeur N - Valeur N-1\nEvol % = Ecart / Valeur N-1 × 100",
        "Analyse mois par mois de l'évolution commerciale. Détecte les mois en retard vs l'année précédente."
    ),

    # ── DIVERS ───────────────────────────────────────────────────────
    "DS_VENTES_PAR_CANAL": (
        "Répartition des ventes par canal de distribution.",
        "Canal de Vente / Société / Nb Clients / Nb Documents / Qte Vendue / CA HT / TTC / Marge / Marge %",
        "Agrégation par canal Sage (direct, revendeur, export, e-commerce...)",
        "Analyse de la performance par canal. Aide à arbitrer les investissements entre canaux de distribution."
    ),
    "DS_VENTES_PAR_GAMME": (
        "Ventes agrégées par gamme de produits.",
        "Gamme / Sous Gamme / Société / Nb Articles / Qte Vendue / CA HT / TTC / Marge / Marge % / Nb Clients / Nb Documents",
        "Marge % = Marge / CA HT × 100",
        "Analyse de la performance commerciale par gamme. Guide la stratégie produit."
    ),
    "DS_VENTES_PAR_CATEGORIE_TARIF": (
        "Ventes et marges par catégorie tarifaire client.",
        "Categorie Tarifaire / Société / Nb Clients / Qte Vendue / CA HT / Marge / Marge % / CA Moyen par Client / Nb Documents",
        "CA Moyen par Client = CA HT / Nb Clients",
        "Évalue la rentabilité par segment tarifaire. Aide à optimiser la politique de remises."
    ),
    "DS_VENTES_CLIENT_MOIS": (
        "Ventes mensuelles par client (source dynamique pour pivots).",
        "Annee / Mois / Période / Code Client / Client / Société / CA HT / TTC / Marge / Marge % / Nb Factures / Qte Totale",
        "Agrégation par (client, mois)",
        "Source optimisée pour les tableaux croisés Client × Période."
    ),
    "DS_VENTES_ARTICLE_MOIS": (
        "Ventes mensuelles par article (source dynamique).",
        "Annee / Mois / Période / Code Article / Article / Catalogue / Qte Vendue / CA HT / Marge / Marge %",
        "Agrégation par (article, mois)",
        "Source optimisée pour les tableaux croisés Article × Période."
    ),
    "DS_VENTES_COMMERCIAL_MOIS": (
        "Ventes mensuelles par commercial (source dynamique).",
        "Annee / Mois / Période / Code Commercial / Commercial / Société / Nb Clients / CA HT / Marge / Marge %",
        "Agrégation par (commercial, mois)",
        "Suivi mensuel des performances commerciales par vendeur."
    ),
    "DS_VENTES_CATALOGUE_MOIS": (
        "Ventes mensuelles par famille catalogue (source dynamique).",
        "Annee / Mois / Période / Catalogue / Sous Catalogue / Nb Articles / Qte Vendue / CA HT / Marge / Marge %",
        "Agrégation par (catalogue, mois)",
        "Source pour les analyses de tendances par famille de produits."
    ),
    "DS_VENTES_GAMME_MOIS": (
        "Ventes mensuelles par gamme de produits.",
        "Gamme / Période / Société / CA HT / Marge / Qte Vendue / Nb Clients",
        "Agrégation par (gamme, mois)",
        "Suivi de l'évolution des ventes par gamme dans le temps."
    ),
    "DS_VENTES_FAMILLE_MOIS": (
        "Ventes mensuelles par famille d'articles.",
        "Famille / Période / Société / CA HT / Marge / Qte Vendue / Nb Articles",
        "Agrégation par (famille, mois)",
        "Analyse de la tendance des ventes par famille produit."
    ),
    "DS_PIVOT_LIGNES_VENTES": (
        "Source de données enrichie pour tous les pivots de ventes.",
        "Dimensions temporelles : Annee / Mois / Période / Trimestre / Jour Semaine / Semestre\nDimensions client : Code Client / Client / Région / Ville / Pays / Classement / Catégorie Tarifaire\nDimensions commerciales : Code Commercial / Commercial\nDimensions produit : Code Article / Désignation / Reference / Famille / Sous Famille / Catalogue\nDimensions logistique : Code Depot / Depot / Num Serie Lot\nDimensions financières : Code Affaire / Affaire / Montant HT / TTC / PU / Qte / Prix Revient",
        "Source de faits étoile pour les cubes OLAP",
        "Source universelle pour construire n'importe quel pivot de ventes. Toutes les dimensions analytiques en une seule source."
    ),
    "DS_PIVOT_VENTES_CA": (
        "Source pivot avec CA, marge et coût pour tous les axes d'analyse.",
        "Dimensions temporelles : Annee / Mois / Période / Trimestre\nCode Client / Client / Code Article / Désignation / Code Depot / Code Affaire\nMontant HT / TTC / Qte / PU HT / Prix Revient / Coût Revient / Marge Brute / Taux Marge %",
        "Marge Brute = Montant HT - Coût Revient\nTaux Marge % = Marge Brute / Montant HT × 100",
        "Source pivot optimisée avec la marge intégrée. Idéale pour les analyses de rentabilité croisées."
    ),
    "DS_ECHEANCES_ACHATS": (
        "Échéances de paiement fournisseurs en cours.",
        "Société / Code Fournisseur / Fournisseur / Numéro Pièce / Date Document / Date Échéance\nMontant Échéance / Montant Réglé / Reste à Payer / Mode de Règlement / Jours de Retard / Tranche d'âge",
        "Reste à Payer = Montant Échéance - Montant Réglé\nJours de Retard = DATEDIFF(day, Date Échéance, GETDATE())",
        "Gestion des dettes fournisseurs. Prévention des pénalités de retard et optimisation du BFR."
    ),
}


def run(conn_str=CONN_STR):
    print(f"Connexion...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # S'assurer que les colonnes doc_* existent sur les deux tables
    for table in ("APP_GridViews", "APP_Pivots_V2"):
        for col in ("doc_description", "doc_fields", "doc_formula", "doc_advantage"):
            cursor.execute(f"""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.columns
                    WHERE object_id = OBJECT_ID('{table}') AND name = '{col}'
                )
                ALTER TABLE {table} ADD {col} NVARCHAR(MAX)
            """)
    conn.commit()
    print("Colonnes doc_* vérifiées.")

    updated_gv = 0
    updated_pv = 0
    skipped = 0

    for ds_code, (desc, fields, formula, advantage) in DOCS.items():
        # Mettre à jour APP_GridViews
        cursor.execute(
            "SELECT COUNT(1) FROM APP_GridViews WHERE data_source_code = ?", ds_code
        )
        gv_count = cursor.fetchone()[0]
        if gv_count:
            cursor.execute("""
                UPDATE APP_GridViews
                SET doc_description = COALESCE(NULLIF(doc_description, ''), ?),
                    doc_fields      = COALESCE(NULLIF(doc_fields, ''), ?),
                    doc_formula     = COALESCE(NULLIF(doc_formula, ''), ?),
                    doc_advantage   = COALESCE(NULLIF(doc_advantage, ''), ?),
                    updated_at      = GETDATE()
                WHERE data_source_code = ?
            """, desc, fields, formula, advantage, ds_code)
            updated_gv += gv_count
            print(f"  GV  {ds_code}")

        # Mettre à jour APP_Pivots_V2
        cursor.execute(
            "SELECT COUNT(1) FROM APP_Pivots_V2 WHERE data_source_code = ?", ds_code
        )
        pv_count = cursor.fetchone()[0]
        if pv_count:
            cursor.execute("""
                UPDATE APP_Pivots_V2
                SET doc_description = COALESCE(NULLIF(doc_description, ''), ?),
                    doc_fields      = COALESCE(NULLIF(doc_fields, ''), ?),
                    doc_formula     = COALESCE(NULLIF(doc_formula, ''), ?),
                    doc_advantage   = COALESCE(NULLIF(doc_advantage, ''), ?),
                    updated_at      = GETDATE()
                WHERE data_source_code = ?
            """, desc, fields, formula, advantage, ds_code)
            updated_pv += pv_count
            print(f"  PV  {ds_code}")

        if not gv_count and not pv_count:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"\n{'='*50}")
    print(f"GridViews mises à jour : {updated_gv}")
    print(f"Pivots mis à jour      : {updated_pv}")
    print(f"DS sans rapport actif  : {skipped}")
    print(f"Total DS documentés    : {len(DOCS)}")


if __name__ == "__main__":
    conn_str = sys.argv[1] if len(sys.argv) > 1 else CONN_STR
    run(conn_str)
