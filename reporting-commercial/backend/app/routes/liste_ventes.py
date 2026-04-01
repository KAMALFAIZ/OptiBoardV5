"""Liste Ventes API - Aggregation par Client/Article"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
import time

from ..database_unified import execute_app as execute_query
from ..services.calculs import get_periode_dates
from ..services.query_logger import query_logger

router = APIRouter(prefix="/api/liste-ventes", tags=["Liste Ventes"])

# Table source: Chiffre_Affaires_Groupe_Bis
TABLE_SOURCE = "[GROUPE_ALBOUGHAZE].[dbo].[Chiffre_Affaires_Groupe_Bis]"

# Requete SQL pour l'aggregation (sans code client/article)
LISTE_VENTES_AGREGEE = f"""
SELECT
    [Catalogue 1] AS Gamme,
    [Catalogue 2] AS Catalogue2,
    [Catalogue 3] AS Catalogue3,
    [Désignation] AS Designation,
    [Intitulé client] AS Intitule_Client,
    [Représentant] AS Commercial,
    [Catégorie_] AS Canal,
    [Souche] AS Zone,
    [Région] AS Region,
    [Ville] AS Ville,
    [GROUPE_] AS Groupe_Client,
    [Société] AS Societe,
    SUM([Quantité]) AS Quantite_Totale,
    SUM([Montant HT Net]) AS Montant_HT,
    SUM([Montant TTC Net]) AS Montant_TTC,
    SUM([Coût]) AS Cout_Total,
    SUM([Montant HT Net]) - SUM([Coût]) AS Marge_Brute,
    CASE
        WHEN SUM([Montant HT Net]) > 0
        THEN (SUM([Montant HT Net]) - SUM([Coût])) / SUM([Montant HT Net]) * 100
        ELSE 0
    END AS Taux_Marge,
    MIN([Prix unitaire]) AS Prix_Unit_Min,
    MAX([Prix unitaire]) AS Prix_Unit_Max,
    AVG([Prix unitaire]) AS Prix_Unit_Moyen,
    MIN([Prix unitaire TTC]) AS Prix_Unit_TTC_Min,
    MAX([Prix unitaire TTC]) AS Prix_Unit_TTC_Max,
    COUNT(*) AS Nb_Transactions,
    MIN([Date BL]) AS Premiere_Vente,
    MAX([Date BL]) AS Derniere_Vente,
    COUNT(DISTINCT [N° Pièce]) AS Nb_Factures
FROM {TABLE_SOURCE}
WHERE YEAR([Date BL]) = 2025
{{filters}}
GROUP BY
    [Catalogue 1],
    [Catalogue 2],
    [Catalogue 3],
    [Désignation],
    [Intitulé client],
    [Représentant],
    [Catégorie_],
    [Souche],
    [Région],
    [Ville],
    [GROUPE_],
    [Société]
ORDER BY Montant_HT DESC
"""


def add_filters(societe: Optional[str] = None, gamme: Optional[str] = None,
                commercial: Optional[str] = None, canal: Optional[str] = None,
                zone: Optional[str] = None, region: Optional[str] = None,
                ville: Optional[str] = None, groupe: Optional[str] = None,
                catalogue2: Optional[str] = None, catalogue3: Optional[str] = None) -> tuple:
    """Construit les filtres SQL dynamiquement."""
    filters = []
    params = []

    if societe:
        filters.append("AND [Société] = ?")
        params.append(societe)
    if gamme:
        filters.append("AND [Catalogue 1] = ?")
        params.append(gamme)
    if catalogue2:
        filters.append("AND [Catalogue 2] = ?")
        params.append(catalogue2)
    if catalogue3:
        filters.append("AND [Catalogue 3] = ?")
        params.append(catalogue3)
    if commercial:
        filters.append("AND [Représentant] = ?")
        params.append(commercial)
    if canal:
        filters.append("AND [Catégorie_] = ?")
        params.append(canal)
    if zone:
        filters.append("AND [Souche] = ?")
        params.append(zone)
    if region:
        filters.append("AND [Région] = ?")
        params.append(region)
    if ville:
        filters.append("AND [Ville] = ?")
        params.append(ville)
    if groupe:
        filters.append("AND [GROUPE_] = ?")
        params.append(groupe)

    return " ".join(filters), params


@router.get("")
async def get_liste_ventes(
    societe: Optional[str] = Query(None, description="Filtre par societe"),
    gamme: Optional[str] = Query(None, description="Filtre par gamme/catalogue 1"),
    catalogue2: Optional[str] = Query(None, description="Filtre par catalogue 2"),
    catalogue3: Optional[str] = Query(None, description="Filtre par catalogue 3"),
    commercial: Optional[str] = Query(None, description="Filtre par commercial"),
    canal: Optional[str] = Query(None, description="Filtre par canal de vente"),
    zone: Optional[str] = Query(None, description="Filtre par zone/souche"),
    region: Optional[str] = Query(None, description="Filtre par region"),
    ville: Optional[str] = Query(None, description="Filtre par ville"),
    groupe: Optional[str] = Query(None, description="Filtre par groupe client"),
    page: int = Query(1, ge=1, description="Numero de page"),
    page_size: int = Query(50, ge=10, le=500, description="Taille de page")
):
    """
    Recupere la liste des ventes agregees (annee 2025).

    Colonnes retournees:
    - Gamme, Catalogue 2, Catalogue 3
    - Commercial, Canal, Zone, Region, Ville
    - Groupe Client, Societe
    - Quantite totale
    - Montant HT, Montant TTC
    - Cout total, Marge brute, Taux de marge
    - Prix unitaire min/max/moyen
    - Nombre de transactions
    - Date premiere/derniere vente
    - Nombre de factures
    """
    try:
        # Construire les filtres
        filter_sql, filter_params = add_filters(
            societe=societe, gamme=gamme, commercial=commercial, canal=canal,
            zone=zone, region=region, ville=ville, groupe=groupe,
            catalogue2=catalogue2, catalogue3=catalogue3
        )

        # Construire la requete (annee 2025 fixe)
        query = LISTE_VENTES_AGREGEE.format(filters=filter_sql)
        params = tuple(filter_params)

        # Executer la requete
        start_time = time.time()
        data = execute_query(query, params)
        query_time = time.time() - start_time

        query_logger.log_query(
            "liste_ventes",
            "Liste Ventes Agregee 2025",
            query,
            query_time,
            len(data)
        )

        # Calculer les totaux
        total_records = len(data)
        total_quantite = sum(row.get('Quantite_Totale', 0) or 0 for row in data)
        total_ht = sum(row.get('Montant_HT', 0) or 0 for row in data)
        total_ttc = sum(row.get('Montant_TTC', 0) or 0 for row in data)
        total_marge = sum(row.get('Marge_Brute', 0) or 0 for row in data)

        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_data = data[start_idx:end_idx]

        # Formater les resultats
        result = []
        for row in paginated_data:
            result.append({
                "gamme": row.get('Gamme', ''),
                "catalogue2": row.get('Catalogue2', ''),
                "catalogue3": row.get('Catalogue3', ''),
                "designation": row.get('Designation', ''),
                "intitule_client": row.get('Intitule_Client', ''),
                "commercial": row.get('Commercial', ''),
                "canal": row.get('Canal', ''),
                "zone": row.get('Zone', ''),
                "region": row.get('Region', ''),
                "ville": row.get('Ville', ''),
                "groupe_client": row.get('Groupe_Client', ''),
                "societe": row.get('Societe', ''),
                "quantite_totale": row.get('Quantite_Totale', 0) or 0,
                "montant_ht": row.get('Montant_HT', 0) or 0,
                "montant_ttc": row.get('Montant_TTC', 0) or 0,
                "cout_total": row.get('Cout_Total', 0) or 0,
                "marge_brute": row.get('Marge_Brute', 0) or 0,
                "taux_marge": round(row.get('Taux_Marge', 0) or 0, 2),
                "prix_unit_min": round(row.get('Prix_Unit_Min', 0) or 0, 2),
                "prix_unit_max": round(row.get('Prix_Unit_Max', 0) or 0, 2),
                "prix_unit_moyen": round(row.get('Prix_Unit_Moyen', 0) or 0, 2),
                "prix_unit_ttc_min": round(row.get('Prix_Unit_TTC_Min', 0) or 0, 2),
                "prix_unit_ttc_max": round(row.get('Prix_Unit_TTC_Max', 0) or 0, 2),
                "nb_transactions": row.get('Nb_Transactions', 0) or 0,
                "premiere_vente": row.get('Premiere_Vente').strftime("%Y-%m-%d") if row.get('Premiere_Vente') else None,
                "derniere_vente": row.get('Derniere_Vente').strftime("%Y-%m-%d") if row.get('Derniere_Vente') else None,
                "nb_factures": row.get('Nb_Factures', 0) or 0
            })

        return {
            "success": True,
            "data": result,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": (total_records + page_size - 1) // page_size
            },
            "totaux": {
                "quantite_totale": total_quantite,
                "montant_ht": total_ht,
                "montant_ttc": total_ttc,
                "marge_brute": total_marge,
                "taux_marge_global": round((total_marge / total_ht * 100) if total_ht > 0 else 0, 2)
            },
            "annee": 2025
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filtres")
async def get_filtres_disponibles():
    """Recupere les valeurs distinctes pour les filtres (annee 2025)."""
    try:
        # Recuperer les gammes (Catalogue 1)
        gammes_query = f"""
        SELECT DISTINCT [Catalogue 1] AS Gamme
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Catalogue 1] IS NOT NULL
        ORDER BY [Catalogue 1]
        """
        gammes = execute_query(gammes_query)

        # Recuperer Catalogue 2
        catalogue2_query = f"""
        SELECT DISTINCT [Catalogue 2] AS Catalogue2
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Catalogue 2] IS NOT NULL
        ORDER BY [Catalogue 2]
        """
        catalogue2 = execute_query(catalogue2_query)

        # Recuperer Catalogue 3
        catalogue3_query = f"""
        SELECT DISTINCT [Catalogue 3] AS Catalogue3
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Catalogue 3] IS NOT NULL
        ORDER BY [Catalogue 3]
        """
        catalogue3 = execute_query(catalogue3_query)

        # Recuperer les commerciaux
        commerciaux_query = f"""
        SELECT DISTINCT [Représentant] AS Commercial
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Représentant] IS NOT NULL
        ORDER BY [Représentant]
        """
        commerciaux = execute_query(commerciaux_query)

        # Recuperer les canaux
        canaux_query = f"""
        SELECT DISTINCT [Catégorie_] AS Canal
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Catégorie_] IS NOT NULL
        ORDER BY [Catégorie_]
        """
        canaux = execute_query(canaux_query)

        # Recuperer les zones (Souche)
        zones_query = f"""
        SELECT DISTINCT [Souche] AS Zone
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Souche] IS NOT NULL
        ORDER BY [Souche]
        """
        zones = execute_query(zones_query)

        # Recuperer les regions
        regions_query = f"""
        SELECT DISTINCT [Région] AS Region
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Région] IS NOT NULL
        ORDER BY [Région]
        """
        regions = execute_query(regions_query)

        # Recuperer les villes
        villes_query = f"""
        SELECT DISTINCT [Ville] AS Ville
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Ville] IS NOT NULL
        ORDER BY [Ville]
        """
        villes = execute_query(villes_query)

        # Recuperer les groupes clients
        groupes_query = f"""
        SELECT DISTINCT [GROUPE_] AS Groupe
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [GROUPE_] IS NOT NULL
        ORDER BY [GROUPE_]
        """
        groupes = execute_query(groupes_query)

        # Recuperer les societes
        societes_query = f"""
        SELECT DISTINCT [Société] AS Societe
        FROM {TABLE_SOURCE}
        WHERE YEAR([Date BL]) = 2025 AND [Société] IS NOT NULL
        ORDER BY [Société]
        """
        societes = execute_query(societes_query)

        return {
            "success": True,
            "gammes": [row['Gamme'] for row in gammes if row.get('Gamme')],
            "catalogue2": [row['Catalogue2'] for row in catalogue2 if row.get('Catalogue2')],
            "catalogue3": [row['Catalogue3'] for row in catalogue3 if row.get('Catalogue3')],
            "commerciaux": [row['Commercial'] for row in commerciaux if row.get('Commercial')],
            "canaux": [row['Canal'] for row in canaux if row.get('Canal')],
            "zones": [row['Zone'] for row in zones if row.get('Zone')],
            "regions": [row['Region'] for row in regions if row.get('Region')],
            "villes": [row['Ville'] for row in villes if row.get('Ville')],
            "groupes": [row['Groupe'] for row in groupes if row.get('Groupe')],
            "societes": [row['Societe'] for row in societes if row.get('Societe')]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_liste_ventes(
    societe: Optional[str] = Query(None),
    gamme: Optional[str] = Query(None),
    catalogue2: Optional[str] = Query(None),
    catalogue3: Optional[str] = Query(None),
    commercial: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    ville: Optional[str] = Query(None),
    groupe: Optional[str] = Query(None)
):
    """
    Exporte toutes les donnees (sans pagination) pour export Excel (annee 2025).
    """
    try:
        filter_sql, filter_params = add_filters(
            societe=societe, gamme=gamme, commercial=commercial, canal=canal,
            zone=zone, region=region, ville=ville, groupe=groupe,
            catalogue2=catalogue2, catalogue3=catalogue3
        )

        query = LISTE_VENTES_AGREGEE.format(filters=filter_sql)
        params = tuple(filter_params)

        data = execute_query(query, params)

        result = []
        for row in data:
            result.append({
                "gamme": row.get('Gamme', ''),
                "catalogue2": row.get('Catalogue2', ''),
                "catalogue3": row.get('Catalogue3', ''),
                "designation": row.get('Designation', ''),
                "intitule_client": row.get('Intitule_Client', ''),
                "commercial": row.get('Commercial', ''),
                "canal": row.get('Canal', ''),
                "zone": row.get('Zone', ''),
                "region": row.get('Region', ''),
                "ville": row.get('Ville', ''),
                "groupe_client": row.get('Groupe_Client', ''),
                "societe": row.get('Societe', ''),
                "quantite_totale": row.get('Quantite_Totale', 0) or 0,
                "montant_ht": row.get('Montant_HT', 0) or 0,
                "montant_ttc": row.get('Montant_TTC', 0) or 0,
                "cout_total": row.get('Cout_Total', 0) or 0,
                "marge_brute": row.get('Marge_Brute', 0) or 0,
                "taux_marge": round(row.get('Taux_Marge', 0) or 0, 2),
                "prix_unit_min": round(row.get('Prix_Unit_Min', 0) or 0, 2),
                "prix_unit_max": round(row.get('Prix_Unit_Max', 0) or 0, 2),
                "prix_unit_moyen": round(row.get('Prix_Unit_Moyen', 0) or 0, 2),
                "prix_unit_ttc_min": round(row.get('Prix_Unit_TTC_Min', 0) or 0, 2),
                "prix_unit_ttc_max": round(row.get('Prix_Unit_TTC_Max', 0) or 0, 2),
                "nb_transactions": row.get('Nb_Transactions', 0) or 0,
                "premiere_vente": row.get('Premiere_Vente').strftime("%Y-%m-%d") if row.get('Premiere_Vente') else None,
                "derniere_vente": row.get('Derniere_Vente').strftime("%Y-%m-%d") if row.get('Derniere_Vente') else None,
                "nb_factures": row.get('Nb_Factures', 0) or 0
            })

        return {
            "success": True,
            "data": result,
            "total_records": len(result),
            "annee": 2025
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
