"""
Script pour initialiser les rapports (GridViews et Pivots) dans la base de donnees
Execute ce script une fois pour creer tous les rapports standards
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import execute_query, get_db_cursor
import json

# =============================================================================
# SOURCES DE DONNEES
# =============================================================================

DATA_SOURCES = [
    # --- VENTES ---
    {
        "nom": "Ventes Detail",
        "description": "Detail de toutes les ventes (BL/Factures)",
        "query_template": """
SELECT
    [Date BL] as DatePiece,
    FORMAT([Date BL], 'yyyy-MM') as Periode,
    YEAR([Date BL]) as Annee,
    MONTH([Date BL]) as Mois,
    [N° Pièce] as NumeroPiece,
    [Code client] as CodeClient,
    [Intitulé client] as NomClient,
    [Code article] as CodeArticle,
    [Désignation] as Designation,
    [Catalogue 1] as Famille,
    [Quantité] as Quantite,
    [Montant HT Net] as MontantHT,
    [Montant TTC Net] as MontantTTC,
    [Coût] as Cout,
    [Montant HT Net] - [Coût] as Marge,
    CASE WHEN [Montant HT Net] > 0 THEN (([Montant HT Net] - [Coût]) / [Montant HT Net]) * 100 ELSE 0 END as TauxMarge,
    [Représentant] as Commercial,
    [Catégorie_] as Canal,
    [Souche] as Zone,
    [Société] as Societe
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
""",
        "category": "Ventes"
    },
    {
        "nom": "CA par Client",
        "description": "Chiffre d'affaires agrege par client",
        "query_template": """
SELECT
    [Code client] as CodeClient,
    [Intitulé client] as NomClient,
    [Représentant] as Commercial,
    [Catégorie_] as Canal,
    COUNT(DISTINCT [N° Pièce]) as NbFactures,
    SUM([Quantité]) as QuantiteTotale,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Montant TTC Net]) as CA_TTC,
    SUM([Coût]) as CoutTotal,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    CASE WHEN SUM([Montant HT Net]) > 0 THEN ((SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net])) * 100 ELSE 0 END as TauxMarge
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
GROUP BY [Code client], [Intitulé client], [Représentant], [Catégorie_]
""",
        "category": "Ventes"
    },
    {
        "nom": "CA par Article",
        "description": "Chiffre d'affaires agrege par article",
        "query_template": """
SELECT
    [Code article] as CodeArticle,
    [Désignation] as Designation,
    [Catalogue 1] as Famille,
    COUNT(DISTINCT [Code client]) as NbClients,
    SUM([Quantité]) as QuantiteVendue,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Coût]) as CoutTotal,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    CASE WHEN SUM([Montant HT Net]) > 0 THEN ((SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net])) * 100 ELSE 0 END as TauxMarge,
    AVG([Montant HT Net] / NULLIF([Quantité], 0)) as PrixMoyenVente
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
GROUP BY [Code article], [Désignation], [Catalogue 1]
""",
        "category": "Ventes"
    },
    {
        "nom": "CA par Commercial",
        "description": "Performance commerciale par representant",
        "query_template": """
SELECT
    [Représentant] as Commercial,
    COUNT(DISTINCT [Code client]) as NbClients,
    COUNT(DISTINCT [N° Pièce]) as NbFactures,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Montant TTC Net]) as CA_TTC,
    SUM([Coût]) as CoutTotal,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    CASE WHEN SUM([Montant HT Net]) > 0 THEN ((SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net])) * 100 ELSE 0 END as TauxMarge,
    SUM([Montant HT Net]) / NULLIF(COUNT(DISTINCT [Code client]), 0) as CAMoyenParClient
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
GROUP BY [Représentant]
""",
        "category": "Ventes"
    },
    {
        "nom": "CA par Famille Produit",
        "description": "Repartition du CA par famille de produits",
        "query_template": """
SELECT
    [Catalogue 1] as Famille,
    COUNT(DISTINCT [Code article]) as NbArticles,
    COUNT(DISTINCT [Code client]) as NbClients,
    SUM([Quantité]) as QuantiteVendue,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Coût]) as CoutTotal,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    CASE WHEN SUM([Montant HT Net]) > 0 THEN ((SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net])) * 100 ELSE 0 END as TauxMarge
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
GROUP BY [Catalogue 1]
""",
        "category": "Ventes"
    },
    {
        "nom": "Top Clients",
        "description": "Classement des meilleurs clients",
        "query_template": """
SELECT TOP 100
    ROW_NUMBER() OVER (ORDER BY SUM([Montant HT Net]) DESC) as Rang,
    [Code client] as CodeClient,
    [Intitulé client] as NomClient,
    [Représentant] as Commercial,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    COUNT(DISTINCT [N° Pièce]) as NbFactures,
    SUM([Montant HT Net]) * 100.0 / (SELECT SUM([Montant HT Net]) FROM DashBoard_CA WHERE [Date BL] BETWEEN @dateDebut AND @dateFin) as PartCA
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
GROUP BY [Code client], [Intitulé client], [Représentant]
ORDER BY CA_HT DESC
""",
        "category": "Ventes"
    },
    {
        "nom": "Top Produits",
        "description": "Classement des meilleurs produits",
        "query_template": """
SELECT TOP 100
    ROW_NUMBER() OVER (ORDER BY SUM([Montant HT Net]) DESC) as Rang,
    [Code article] as CodeArticle,
    [Désignation] as Designation,
    [Catalogue 1] as Famille,
    SUM([Quantité]) as QuantiteVendue,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    CASE WHEN SUM([Montant HT Net]) > 0 THEN ((SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net])) * 100 ELSE 0 END as TauxMarge
FROM DashBoard_CA
WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
GROUP BY [Code article], [Désignation], [Catalogue 1]
ORDER BY CA_HT DESC
""",
        "category": "Ventes"
    },

    # --- RECOUVREMENT ---
    {
        "nom": "Balance Agee Detail",
        "description": "Balance agee detaillee par client",
        "query_template": """
SELECT
    [CLIENTS ] as Client,
    [Représenant] as Commercial,
    [SOCIETE] as Societe,
    [Solde Clôture] as Encours,
    [0-30] as Tranche_0_30,
    [31-60] as Tranche_31_60,
    [61-90] as Tranche_61_90,
    [91-120] as Tranche_91_120,
    [+120] as Tranche_Plus_120,
    [Impayés] as Impayes,
    CASE
        WHEN [Solde Clôture] > 0 THEN ([+120] + [Impayés]) * 100.0 / [Solde Clôture]
        ELSE 0
    END as TauxRisque
FROM BalanceAgee
WHERE [Solde Clôture] <> 0
""",
        "category": "Recouvrement"
    },
    {
        "nom": "Balance Agee par Commercial",
        "description": "Encours clients agreges par commercial",
        "query_template": """
SELECT
    [Représenant] as Commercial,
    COUNT(*) as NbClients,
    SUM([Solde Clôture]) as EncoursTotal,
    SUM([0-30]) as Tranche_0_30,
    SUM([31-60]) as Tranche_31_60,
    SUM([61-90]) as Tranche_61_90,
    SUM([91-120]) as Tranche_91_120,
    SUM([+120]) as Tranche_Plus_120,
    SUM([Impayés]) as TotalImpayes,
    CASE
        WHEN SUM([Solde Clôture]) > 0 THEN (SUM([+120]) + SUM([Impayés])) * 100.0 / SUM([Solde Clôture])
        ELSE 0
    END as TauxRisque
FROM BalanceAgee
GROUP BY [Représenant]
""",
        "category": "Recouvrement"
    },
    {
        "nom": "Creances Douteuses",
        "description": "Clients avec creances a risque (+120j ou impayes)",
        "query_template": """
SELECT
    [CLIENTS ] as Client,
    [Représenant] as Commercial,
    [SOCIETE] as Societe,
    [Solde Clôture] as Encours,
    [+120] as Creances_Plus_120,
    [Impayés] as Impayes,
    [+120] + [Impayés] as TotalRisque,
    CASE
        WHEN [Solde Clôture] > 0 THEN ([+120] + [Impayés]) * 100.0 / [Solde Clôture]
        ELSE 0
    END as TauxRisque
FROM BalanceAgee
WHERE [+120] > 0 OR [Impayés] > 0
ORDER BY TotalRisque DESC
""",
        "category": "Recouvrement"
    },
    {
        "nom": "Top Encours Clients",
        "description": "Les plus gros encours clients",
        "query_template": """
SELECT TOP 50
    ROW_NUMBER() OVER (ORDER BY [Solde Clôture] DESC) as Rang,
    [CLIENTS ] as Client,
    [Représenant] as Commercial,
    [SOCIETE] as Societe,
    [Solde Clôture] as Encours,
    [0-30] as Tranche_0_30,
    [31-60] as Tranche_31_60,
    [61-90] as Tranche_61_90,
    [91-120] as Tranche_91_120,
    [+120] as Tranche_Plus_120,
    [Impayés] as Impayes
FROM BalanceAgee
ORDER BY [Solde Clôture] DESC
""",
        "category": "Recouvrement"
    },

    # --- STOCKS ---
    {
        "nom": "Mouvements Stock",
        "description": "Historique des mouvements de stock",
        "query_template": """
SELECT
    [Date Mouvement] as DateMouvement,
    [Type Mouvement] as TypeMouvement,
    [N° Pièce] as NumeroPiece,
    [Code article] as CodeArticle,
    [Désignation] as Designation,
    [Catalogue 1] as Famille,
    [Quantité] as Quantite,
    [Sens de mouvement] as Sens,
    [CMUP] as CMUP,
    [Prix unitaire] as PrixUnitaire,
    [Montant Stock] as MontantStock,
    [Intitulé client] as Client,
    [Représentant] as Commercial
FROM Mouvement_stock
WHERE [Date Mouvement] BETWEEN @dateDebut AND @dateFin
""",
        "category": "Stocks"
    },
    {
        "nom": "Stock par Article",
        "description": "Situation du stock par article",
        "query_template": """
SELECT
    [Code article] as CodeArticle,
    [Désignation] as Designation,
    [Catalogue 1] as Famille,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE 0 END) as Entrees,
    SUM(CASE WHEN [Sens de mouvement] = 'S' THEN [Quantité] ELSE 0 END) as Sorties,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) as StockActuel,
    AVG([CMUP]) as CMUPMoyen,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) * AVG([CMUP]) as ValeurStock,
    MAX([Date Mouvement]) as DernierMouvement
FROM Mouvement_stock
GROUP BY [Code article], [Désignation], [Catalogue 1]
""",
        "category": "Stocks"
    },
    {
        "nom": "Stock Dormant",
        "description": "Articles sans mouvement depuis plus de 180 jours",
        "query_template": """
SELECT
    [Code article] as CodeArticle,
    [Désignation] as Designation,
    [Catalogue 1] as Famille,
    MAX([Date Mouvement]) as DernierMouvement,
    DATEDIFF(DAY, MAX([Date Mouvement]), GETDATE()) as JoursSansMouvement,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) as StockActuel,
    SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) * AVG([CMUP]) as ValeurStock
FROM Mouvement_stock
GROUP BY [Code article], [Désignation], [Catalogue 1]
HAVING DATEDIFF(DAY, MAX([Date Mouvement]), GETDATE()) > 180
   AND SUM(CASE WHEN [Sens de mouvement] = 'E' THEN [Quantité] ELSE -[Quantité] END) > 0
ORDER BY ValeurStock DESC
""",
        "category": "Stocks"
    },

    # --- ANALYSE ---
    {
        "nom": "Analyse ABC Clients",
        "description": "Classification ABC des clients par CA",
        "query_template": """
WITH ClientCA AS (
    SELECT
        [Code client] as CodeClient,
        [Intitulé client] as NomClient,
        [Représentant] as Commercial,
        SUM([Montant HT Net]) as CA_HT
    FROM DashBoard_CA
    WHERE [Date BL] BETWEEN @dateDebut AND @dateFin
    GROUP BY [Code client], [Intitulé client], [Représentant]
),
ClientRank AS (
    SELECT *,
        SUM(CA_HT) OVER (ORDER BY CA_HT DESC) as CACumule,
        SUM(CA_HT) OVER () as CATotal
    FROM ClientCA
)
SELECT
    CodeClient,
    NomClient,
    Commercial,
    CA_HT,
    CACumule,
    CACumule * 100.0 / CATotal as PourcentCumule,
    CASE
        WHEN CACumule * 100.0 / CATotal <= 80 THEN 'A'
        WHEN CACumule * 100.0 / CATotal <= 95 THEN 'B'
        ELSE 'C'
    END as ClasseABC
FROM ClientRank
ORDER BY CA_HT DESC
""",
        "category": "Analyse"
    },
    {
        "nom": "Comparatif Mensuel",
        "description": "CA mensuel avec comparaison N-1",
        "query_template": """
SELECT
    YEAR([Date BL]) as Annee,
    MONTH([Date BL]) as Mois,
    FORMAT([Date BL], 'yyyy-MM') as Periode,
    SUM([Montant HT Net]) as CA_HT,
    SUM([Montant TTC Net]) as CA_TTC,
    SUM([Montant HT Net]) - SUM([Coût]) as Marge,
    COUNT(DISTINCT [Code client]) as NbClients,
    COUNT(DISTINCT [N° Pièce]) as NbFactures
FROM DashBoard_CA
WHERE [Date BL] >= DATEADD(YEAR, -2, GETDATE())
GROUP BY YEAR([Date BL]), MONTH([Date BL]), FORMAT([Date BL], 'yyyy-MM')
ORDER BY Annee, Mois
""",
        "category": "Analyse"
    }
]

# =============================================================================
# GRIDVIEWS
# =============================================================================

GRIDVIEWS = [
    # --- VENTES ---
    {
        "nom": "Detail des Ventes",
        "description": "Liste detaillee de toutes les transactions de vente",
        "data_source": "Ventes Detail",
        "columns": [
            {"field": "DatePiece", "header": "Date", "format": "date", "width": 100},
            {"field": "NumeroPiece", "header": "N Piece", "width": 120},
            {"field": "CodeClient", "header": "Code Client", "width": 100},
            {"field": "NomClient", "header": "Client", "width": 200},
            {"field": "CodeArticle", "header": "Code Article", "width": 120},
            {"field": "Designation", "header": "Designation", "width": 250},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "Quantite", "header": "Qte", "format": "number", "width": 80, "align": "right"},
            {"field": "MontantHT", "header": "Montant HT", "format": "currency", "width": 120, "align": "right"},
            {"field": "MontantTTC", "header": "Montant TTC", "format": "currency", "width": 120, "align": "right"},
            {"field": "Marge", "header": "Marge", "format": "currency", "width": 100, "align": "right"},
            {"field": "TauxMarge", "header": "% Marge", "format": "percent", "width": 80, "align": "right"},
            {"field": "Commercial", "header": "Commercial", "width": 120},
            {"field": "Canal", "header": "Canal", "width": 100},
            {"field": "Zone", "header": "Zone", "width": 100}
        ],
        "default_sort": {"field": "DatePiece", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["MontantHT", "MontantTTC", "Marge", "Quantite"]
    },
    {
        "nom": "CA par Client",
        "description": "Chiffre d'affaires par client",
        "data_source": "CA par Client",
        "columns": [
            {"field": "CodeClient", "header": "Code", "width": 100},
            {"field": "NomClient", "header": "Client", "width": 250},
            {"field": "Commercial", "header": "Commercial", "width": 120},
            {"field": "Canal", "header": "Canal", "width": 100},
            {"field": "NbFactures", "header": "Nb Fact.", "format": "number", "width": 80, "align": "right"},
            {"field": "QuantiteTotale", "header": "Qte Totale", "format": "number", "width": 100, "align": "right"},
            {"field": "CA_HT", "header": "CA HT", "format": "currency", "width": 130, "align": "right"},
            {"field": "CA_TTC", "header": "CA TTC", "format": "currency", "width": 130, "align": "right"},
            {"field": "Marge", "header": "Marge", "format": "currency", "width": 120, "align": "right"},
            {"field": "TauxMarge", "header": "% Marge", "format": "percent", "width": 80, "align": "right"}
        ],
        "default_sort": {"field": "CA_HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA_HT", "CA_TTC", "Marge", "NbFactures"]
    },
    {
        "nom": "CA par Article",
        "description": "Chiffre d'affaires par article",
        "data_source": "CA par Article",
        "columns": [
            {"field": "CodeArticle", "header": "Code", "width": 120},
            {"field": "Designation", "header": "Designation", "width": 280},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "NbClients", "header": "Nb Clients", "format": "number", "width": 90, "align": "right"},
            {"field": "QuantiteVendue", "header": "Qte Vendue", "format": "number", "width": 100, "align": "right"},
            {"field": "CA_HT", "header": "CA HT", "format": "currency", "width": 130, "align": "right"},
            {"field": "Marge", "header": "Marge", "format": "currency", "width": 120, "align": "right"},
            {"field": "TauxMarge", "header": "% Marge", "format": "percent", "width": 80, "align": "right"},
            {"field": "PrixMoyenVente", "header": "Prix Moyen", "format": "currency", "width": 100, "align": "right"}
        ],
        "default_sort": {"field": "CA_HT", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["CA_HT", "Marge", "QuantiteVendue"]
    },
    {
        "nom": "Performance Commerciale",
        "description": "Resultats par commercial",
        "data_source": "CA par Commercial",
        "columns": [
            {"field": "Commercial", "header": "Commercial", "width": 150},
            {"field": "NbClients", "header": "Nb Clients", "format": "number", "width": 100, "align": "right"},
            {"field": "NbFactures", "header": "Nb Factures", "format": "number", "width": 100, "align": "right"},
            {"field": "CA_HT", "header": "CA HT", "format": "currency", "width": 140, "align": "right"},
            {"field": "Marge", "header": "Marge", "format": "currency", "width": 130, "align": "right"},
            {"field": "TauxMarge", "header": "% Marge", "format": "percent", "width": 90, "align": "right"},
            {"field": "CAMoyenParClient", "header": "CA Moy/Client", "format": "currency", "width": 120, "align": "right"}
        ],
        "default_sort": {"field": "CA_HT", "direction": "desc"},
        "page_size": 25,
        "show_totals": True,
        "total_columns": ["CA_HT", "Marge", "NbClients", "NbFactures"]
    },
    {
        "nom": "Top 100 Clients",
        "description": "Les 100 meilleurs clients",
        "data_source": "Top Clients",
        "columns": [
            {"field": "Rang", "header": "#", "width": 50, "align": "center"},
            {"field": "CodeClient", "header": "Code", "width": 100},
            {"field": "NomClient", "header": "Client", "width": 250},
            {"field": "Commercial", "header": "Commercial", "width": 120},
            {"field": "CA_HT", "header": "CA HT", "format": "currency", "width": 140, "align": "right"},
            {"field": "Marge", "header": "Marge", "format": "currency", "width": 120, "align": "right"},
            {"field": "NbFactures", "header": "Nb Fact.", "format": "number", "width": 90, "align": "right"},
            {"field": "PartCA", "header": "% CA", "format": "percent", "width": 80, "align": "right"}
        ],
        "default_sort": {"field": "Rang", "direction": "asc"},
        "page_size": 100,
        "show_totals": True,
        "total_columns": ["CA_HT", "Marge"]
    },
    {
        "nom": "Top 100 Produits",
        "description": "Les 100 meilleurs produits",
        "data_source": "Top Produits",
        "columns": [
            {"field": "Rang", "header": "#", "width": 50, "align": "center"},
            {"field": "CodeArticle", "header": "Code", "width": 120},
            {"field": "Designation", "header": "Designation", "width": 280},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "QuantiteVendue", "header": "Qte", "format": "number", "width": 90, "align": "right"},
            {"field": "CA_HT", "header": "CA HT", "format": "currency", "width": 140, "align": "right"},
            {"field": "Marge", "header": "Marge", "format": "currency", "width": 120, "align": "right"},
            {"field": "TauxMarge", "header": "% Marge", "format": "percent", "width": 80, "align": "right"}
        ],
        "default_sort": {"field": "Rang", "direction": "asc"},
        "page_size": 100,
        "show_totals": True,
        "total_columns": ["CA_HT", "Marge", "QuantiteVendue"]
    },

    # --- RECOUVREMENT ---
    {
        "nom": "Balance Agee",
        "description": "Encours clients par anciennete",
        "data_source": "Balance Agee Detail",
        "columns": [
            {"field": "Client", "header": "Client", "width": 250},
            {"field": "Commercial", "header": "Commercial", "width": 120},
            {"field": "Societe", "header": "Societe", "width": 100},
            {"field": "Encours", "header": "Encours", "format": "currency", "width": 130, "align": "right"},
            {"field": "Tranche_0_30", "header": "0-30j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_31_60", "header": "31-60j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_61_90", "header": "61-90j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_91_120", "header": "91-120j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_Plus_120", "header": "+120j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Impayes", "header": "Impayes", "format": "currency", "width": 110, "align": "right"},
            {"field": "TauxRisque", "header": "% Risque", "format": "percent", "width": 90, "align": "right"}
        ],
        "default_sort": {"field": "Encours", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Encours", "Tranche_0_30", "Tranche_31_60", "Tranche_61_90", "Tranche_91_120", "Tranche_Plus_120", "Impayes"]
    },
    {
        "nom": "Encours par Commercial",
        "description": "Encours agreges par commercial",
        "data_source": "Balance Agee par Commercial",
        "columns": [
            {"field": "Commercial", "header": "Commercial", "width": 150},
            {"field": "NbClients", "header": "Nb Clients", "format": "number", "width": 100, "align": "right"},
            {"field": "EncoursTotal", "header": "Encours Total", "format": "currency", "width": 140, "align": "right"},
            {"field": "Tranche_0_30", "header": "0-30j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_31_60", "header": "31-60j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_61_90", "header": "61-90j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_91_120", "header": "91-120j", "format": "currency", "width": 110, "align": "right"},
            {"field": "Tranche_Plus_120", "header": "+120j", "format": "currency", "width": 110, "align": "right"},
            {"field": "TotalImpayes", "header": "Impayes", "format": "currency", "width": 110, "align": "right"},
            {"field": "TauxRisque", "header": "% Risque", "format": "percent", "width": 90, "align": "right"}
        ],
        "default_sort": {"field": "EncoursTotal", "direction": "desc"},
        "page_size": 25,
        "show_totals": True,
        "total_columns": ["EncoursTotal", "Tranche_0_30", "Tranche_31_60", "Tranche_61_90", "Tranche_91_120", "Tranche_Plus_120", "TotalImpayes"]
    },
    {
        "nom": "Creances Douteuses",
        "description": "Clients a risque (+120j ou impayes)",
        "data_source": "Creances Douteuses",
        "columns": [
            {"field": "Client", "header": "Client", "width": 250},
            {"field": "Commercial", "header": "Commercial", "width": 120},
            {"field": "Societe", "header": "Societe", "width": 100},
            {"field": "Encours", "header": "Encours", "format": "currency", "width": 130, "align": "right"},
            {"field": "Creances_Plus_120", "header": "+120j", "format": "currency", "width": 120, "align": "right"},
            {"field": "Impayes", "header": "Impayes", "format": "currency", "width": 120, "align": "right"},
            {"field": "TotalRisque", "header": "Total Risque", "format": "currency", "width": 130, "align": "right"},
            {"field": "TauxRisque", "header": "% Risque", "format": "percent", "width": 90, "align": "right"}
        ],
        "default_sort": {"field": "TotalRisque", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Encours", "Creances_Plus_120", "Impayes", "TotalRisque"]
    },

    # --- STOCKS ---
    {
        "nom": "Mouvements Stock",
        "description": "Historique des mouvements",
        "data_source": "Mouvements Stock",
        "columns": [
            {"field": "DateMouvement", "header": "Date", "format": "date", "width": 100},
            {"field": "TypeMouvement", "header": "Type", "width": 100},
            {"field": "NumeroPiece", "header": "N Piece", "width": 120},
            {"field": "CodeArticle", "header": "Code Article", "width": 120},
            {"field": "Designation", "header": "Designation", "width": 250},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "Quantite", "header": "Qte", "format": "number", "width": 80, "align": "right"},
            {"field": "Sens", "header": "E/S", "width": 50, "align": "center"},
            {"field": "CMUP", "header": "CMUP", "format": "currency", "width": 100, "align": "right"},
            {"field": "MontantStock", "header": "Montant", "format": "currency", "width": 120, "align": "right"},
            {"field": "Client", "header": "Client", "width": 150},
            {"field": "Commercial", "header": "Commercial", "width": 100}
        ],
        "default_sort": {"field": "DateMouvement", "direction": "desc"},
        "page_size": 50,
        "show_totals": False
    },
    {
        "nom": "Situation Stock",
        "description": "Stock actuel par article",
        "data_source": "Stock par Article",
        "columns": [
            {"field": "CodeArticle", "header": "Code", "width": 120},
            {"field": "Designation", "header": "Designation", "width": 280},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "Entrees", "header": "Entrees", "format": "number", "width": 100, "align": "right"},
            {"field": "Sorties", "header": "Sorties", "format": "number", "width": 100, "align": "right"},
            {"field": "StockActuel", "header": "Stock", "format": "number", "width": 100, "align": "right"},
            {"field": "CMUPMoyen", "header": "CMUP", "format": "currency", "width": 100, "align": "right"},
            {"field": "ValeurStock", "header": "Valeur", "format": "currency", "width": 130, "align": "right"},
            {"field": "DernierMouvement", "header": "Dernier Mvt", "format": "date", "width": 100}
        ],
        "default_sort": {"field": "ValeurStock", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["Entrees", "Sorties", "StockActuel", "ValeurStock"]
    },
    {
        "nom": "Stock Dormant",
        "description": "Articles sans mouvement +180j",
        "data_source": "Stock Dormant",
        "columns": [
            {"field": "CodeArticle", "header": "Code", "width": 120},
            {"field": "Designation", "header": "Designation", "width": 280},
            {"field": "Famille", "header": "Famille", "width": 120},
            {"field": "StockActuel", "header": "Stock", "format": "number", "width": 100, "align": "right"},
            {"field": "ValeurStock", "header": "Valeur", "format": "currency", "width": 130, "align": "right"},
            {"field": "DernierMouvement", "header": "Dernier Mvt", "format": "date", "width": 100},
            {"field": "JoursSansMouvement", "header": "Jours Inactif", "format": "number", "width": 100, "align": "right"}
        ],
        "default_sort": {"field": "ValeurStock", "direction": "desc"},
        "page_size": 50,
        "show_totals": True,
        "total_columns": ["StockActuel", "ValeurStock"]
    },

    # --- ANALYSE ---
    {
        "nom": "Classification ABC Clients",
        "description": "Analyse ABC des clients",
        "data_source": "Analyse ABC Clients",
        "columns": [
            {"field": "ClasseABC", "header": "Classe", "width": 70, "align": "center"},
            {"field": "CodeClient", "header": "Code", "width": 100},
            {"field": "NomClient", "header": "Client", "width": 250},
            {"field": "Commercial", "header": "Commercial", "width": 120},
            {"field": "CA_HT", "header": "CA HT", "format": "currency", "width": 140, "align": "right"},
            {"field": "CACumule", "header": "CA Cumule", "format": "currency", "width": 140, "align": "right"},
            {"field": "PourcentCumule", "header": "% Cumule", "format": "percent", "width": 100, "align": "right"}
        ],
        "default_sort": {"field": "CA_HT", "direction": "desc"},
        "page_size": 100,
        "show_totals": True,
        "total_columns": ["CA_HT"]
    }
]

# =============================================================================
# PIVOTS
# =============================================================================

PIVOTS = [
    {
        "nom": "CA par Client x Mois",
        "description": "Evolution du CA par client et par mois",
        "data_source": "Ventes Detail",
        "rows": ["NomClient", "Commercial"],
        "columns": ["Periode"],
        "values": ["MontantHT"],
        "aggregation": "sum"
    },
    {
        "nom": "CA par Famille x Client",
        "description": "Matrice Famille produit / Client",
        "data_source": "Ventes Detail",
        "rows": ["Famille"],
        "columns": ["NomClient"],
        "values": ["MontantHT", "Marge"],
        "aggregation": "sum"
    },
    {
        "nom": "CA par Commercial x Mois",
        "description": "Performance commerciale mensuelle",
        "data_source": "Ventes Detail",
        "rows": ["Commercial"],
        "columns": ["Periode"],
        "values": ["MontantHT", "Marge"],
        "aggregation": "sum"
    },
    {
        "nom": "Encours par Commercial x Tranche",
        "description": "Balance agee par commercial",
        "data_source": "Balance Agee Detail",
        "rows": ["Commercial", "Client"],
        "columns": [],
        "values": ["Encours", "Tranche_0_30", "Tranche_31_60", "Tranche_61_90", "Tranche_91_120", "Tranche_Plus_120"],
        "aggregation": "sum"
    },
    {
        "nom": "Stock par Famille",
        "description": "Valeur stock par famille produit",
        "data_source": "Stock par Article",
        "rows": ["Famille"],
        "columns": [],
        "values": ["StockActuel", "ValeurStock", "Entrees", "Sorties"],
        "aggregation": "sum"
    }
]


def create_data_source(ds):
    """Cree une source de donnees"""
    try:
        # Verifier si existe deja
        existing = execute_query(
            "SELECT id FROM APP_DataSources WHERE nom = ?",
            (ds['nom'],),
            use_cache=False
        )
        if existing:
            print(f"  Source '{ds['nom']}' existe deja (id={existing[0]['id']})")
            return existing[0]['id']

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_DataSources (nom, type, query_template, parameters, description)
                VALUES (?, 'query', ?, '{}', ?)
            """, (ds['nom'], ds['query_template'], ds['description']))
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            print(f"  Source '{ds['nom']}' creee (id={new_id})")
            return new_id
    except Exception as e:
        print(f"  ERREUR source '{ds['nom']}': {e}")
        return None


def create_gridview(gv, data_source_id):
    """Cree une GridView"""
    try:
        # Verifier si existe deja
        existing = execute_query(
            "SELECT id FROM APP_GridViews WHERE nom = ?",
            (gv['nom'],),
            use_cache=False
        )
        if existing:
            print(f"  GridView '{gv['nom']}' existe deja (id={existing[0]['id']})")
            return existing[0]['id']

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_GridViews (nom, description, data_source_id, columns_config, default_sort, page_size, show_totals, total_columns, is_public, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
            """, (
                gv['nom'],
                gv['description'],
                data_source_id,
                json.dumps(gv['columns']),
                json.dumps(gv.get('default_sort')),
                gv.get('page_size', 25),
                gv.get('show_totals', False),
                json.dumps(gv.get('total_columns', []))
            ))
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            print(f"  GridView '{gv['nom']}' creee (id={new_id})")
            return new_id
    except Exception as e:
        print(f"  ERREUR GridView '{gv['nom']}': {e}")
        return None


def create_pivot(pv, data_source_id):
    """Cree un Pivot"""
    try:
        # Verifier si existe deja
        existing = execute_query(
            "SELECT id FROM APP_Pivots WHERE nom = ?",
            (pv['nom'],),
            use_cache=False
        )
        if existing:
            print(f"  Pivot '{pv['nom']}' existe deja (id={existing[0]['id']})")
            return existing[0]['id']

        # Preparer les configs JSON pour chaque champ
        rows_config = json.dumps(pv.get('rows', []))
        columns_config = json.dumps(pv.get('columns', []))
        values_config = json.dumps([{"field": v, "aggregation": pv.get('aggregation', 'sum')} for v in pv.get('values', [])])
        filters_config = json.dumps({})

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO APP_Pivots (nom, description, data_source_id, rows_config, columns_config, values_config, filters_config, is_public, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
            """, (
                pv['nom'],
                pv['description'],
                data_source_id,
                rows_config,
                columns_config,
                values_config,
                filters_config
            ))
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]
            print(f"  Pivot '{pv['nom']}' cree (id={new_id})")
            return new_id
    except Exception as e:
        print(f"  ERREUR Pivot '{pv['nom']}': {e}")
        return None


def create_menu_structure(gridviews_ids, pivots_ids):
    """Cree la structure de menus pour les rapports"""
    try:
        # Verifier si les menus existent deja
        existing = execute_query(
            "SELECT id FROM APP_Menus WHERE code = 'rapports-ventes'",
            use_cache=False
        )
        if existing:
            print("  Structure de menus existe deja")
            return

        with get_db_cursor() as cursor:
            # Menu racine Rapports
            cursor.execute("""
                INSERT INTO APP_Menus (parent_id, nom, code, icon, type, ordre, is_active)
                VALUES (NULL, 'Rapports', 'rapports', 'FileSpreadsheet', 'folder', 1, 1)
            """)
            cursor.execute("SELECT @@IDENTITY AS id")
            rapports_id = cursor.fetchone()[0]

            # Sous-menu Ventes
            cursor.execute("""
                INSERT INTO APP_Menus (parent_id, nom, code, icon, type, ordre, is_active)
                VALUES (?, 'Ventes', 'rapports-ventes', 'ShoppingCart', 'folder', 1, 1)
            """, (rapports_id,))
            cursor.execute("SELECT @@IDENTITY AS id")
            ventes_id = cursor.fetchone()[0]

            # Sous-menu Recouvrement
            cursor.execute("""
                INSERT INTO APP_Menus (parent_id, nom, code, icon, type, ordre, is_active)
                VALUES (?, 'Recouvrement', 'rapports-recouvrement', 'Wallet', 'folder', 2, 1)
            """, (rapports_id,))
            cursor.execute("SELECT @@IDENTITY AS id")
            recouvrement_id = cursor.fetchone()[0]

            # Sous-menu Stocks
            cursor.execute("""
                INSERT INTO APP_Menus (parent_id, nom, code, icon, type, ordre, is_active)
                VALUES (?, 'Stocks', 'rapports-stocks', 'Package', 'folder', 3, 1)
            """, (rapports_id,))
            cursor.execute("SELECT @@IDENTITY AS id")
            stocks_id = cursor.fetchone()[0]

            # Sous-menu Analyse
            cursor.execute("""
                INSERT INTO APP_Menus (parent_id, nom, code, icon, type, ordre, is_active)
                VALUES (?, 'Analyse', 'rapports-analyse', 'BarChart3', 'folder', 4, 1)
            """, (rapports_id,))
            cursor.execute("SELECT @@IDENTITY AS id")
            analyse_id = cursor.fetchone()[0]

            # Ajouter les GridViews aux menus
            ordre = 1
            for name, gv_id in gridviews_ids.items():
                if gv_id:
                    parent = ventes_id
                    if 'Balance' in name or 'Encours' in name or 'Creances' in name:
                        parent = recouvrement_id
                    elif 'Stock' in name or 'Mouvement' in name:
                        parent = stocks_id
                    elif 'ABC' in name or 'Comparatif' in name:
                        parent = analyse_id

                    cursor.execute("""
                        INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, ordre, is_active)
                        VALUES (?, ?, ?, 'FileSpreadsheet', 'gridview', ?, ?, 1)
                    """, (parent, name, f"gv-{name.lower().replace(' ', '-')}", gv_id, ordre))
                    ordre += 1

            # Ajouter les Pivots aux menus
            ordre = 100
            for name, pv_id in pivots_ids.items():
                if pv_id:
                    parent = analyse_id
                    if 'Client' in name or 'Commercial' in name:
                        parent = ventes_id
                    elif 'Encours' in name:
                        parent = recouvrement_id
                    elif 'Stock' in name:
                        parent = stocks_id

                    cursor.execute("""
                        INSERT INTO APP_Menus (parent_id, nom, code, icon, type, target_id, ordre, is_active)
                        VALUES (?, ?, ?, 'Table2', 'pivot', ?, ?, 1)
                    """, (parent, name, f"pv-{name.lower().replace(' ', '-')}", pv_id, ordre))
                    ordre += 1

            print("  Structure de menus creee")
    except Exception as e:
        print(f"  ERREUR creation menus: {e}")


def main():
    print("=" * 60)
    print("INITIALISATION DES RAPPORTS")
    print("=" * 60)

    # Index pour retrouver les IDs des sources par nom
    source_ids = {}
    gridviews_ids = {}
    pivots_ids = {}

    # 1. Creer les sources de donnees
    print("\n[1/4] Creation des sources de donnees...")
    for ds in DATA_SOURCES:
        ds_id = create_data_source(ds)
        if ds_id:
            source_ids[ds['nom']] = ds_id

    # 2. Creer les GridViews
    print("\n[2/4] Creation des GridViews...")
    for gv in GRIDVIEWS:
        ds_id = source_ids.get(gv['data_source'])
        if ds_id:
            gv_id = create_gridview(gv, ds_id)
            if gv_id:
                gridviews_ids[gv['nom']] = gv_id
        else:
            print(f"  ERREUR: Source '{gv['data_source']}' introuvable pour GridView '{gv['nom']}'")

    # 3. Creer les Pivots
    print("\n[3/4] Creation des Pivots...")
    for pv in PIVOTS:
        ds_id = source_ids.get(pv['data_source'])
        if ds_id:
            pv_id = create_pivot(pv, ds_id)
            if pv_id:
                pivots_ids[pv['nom']] = pv_id
        else:
            print(f"  ERREUR: Source '{pv['data_source']}' introuvable pour Pivot '{pv['nom']}'")

    # 4. Creer la structure de menus
    print("\n[4/4] Creation de la structure de menus...")
    create_menu_structure(gridviews_ids, pivots_ids)

    print("\n" + "=" * 60)
    print("TERMINE!")
    print(f"  - {len(source_ids)} sources de donnees")
    print(f"  - {len(gridviews_ids)} GridViews")
    print(f"  - {len(pivots_ids)} Pivots")
    print("=" * 60)


if __name__ == "__main__":
    main()

