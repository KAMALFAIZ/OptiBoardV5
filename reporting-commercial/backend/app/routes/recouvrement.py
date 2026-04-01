"""Recouvrement et DSO API routes - Version enrichie avec Échéances et Imputations"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional, List
import time
from collections import defaultdict

from ..database_unified import execute_app as execute_query
from ..sql.query_templates import (
    BALANCE_AGEE,
    CHIFFRE_AFFAIRES_PAR_PERIODE,
    # Nouvelles sources de données
    ECHEANCES_VENTES,
    ECHEANCES_VENTES_NON_REGLEES,
    ECHEANCES_PAR_CLIENT,
    ECHEANCES_PAR_COMMERCIAL,
    ECHEANCES_PAR_MODE_REGLEMENT,
    ECHEANCES_A_ECHOIR,
    IMPUTATIONS_FACTURES,
    REGLEMENTS_PAR_PERIODE,
    REGLEMENTS_PAR_CLIENT,
    REGLEMENTS_PAR_MODE,
    FACTURES_NON_REGLEES,
    HISTORIQUE_REGLEMENTS_CLIENT,
    KPIS_RECOUVREMENT,
    EVOLUTION_RECOUVREMENT
)
from ..services.calculs import (
    get_periode_dates,
    calculer_dso,
    parse_number
)
from ..services.query_logger import query_logger

router = APIRouter(prefix="/api/recouvrement", tags=["Recouvrement"])


def get_parsed_balance_data(societe: Optional[str] = None):
    """Récupère et parse les données de balance âgée avec filtre société optionnel."""
    if societe:
        query = BALANCE_AGEE + " WHERE [SOCIETE] = ?"
        data = execute_query(query, (societe,))
    else:
        data = execute_query(BALANCE_AGEE)
    for row in data:
        # Convertir les valeurs formatées en nombres
        row['Solde_Cloture_Num'] = parse_number(row.get('Solde_Cloture'))
        row['Impayes_Num'] = parse_number(row.get('Impayes'))
        row['0-30_Num'] = parse_number(row.get('0-30'))
        row['31-60_Num'] = parse_number(row.get('31-60'))
        row['61-90_Num'] = parse_number(row.get('61-90'))
        row['91-120_Num'] = parse_number(row.get('91-120'))
        row['+120_Num'] = parse_number(row.get('+120'))
    return data


def add_societe_filter_ca(query: str, societe: Optional[str]) -> tuple:
    """Ajoute le filtre société à une requête CA."""
    if not societe:
        return query, False
    if "GROUP BY" in query:
        modified = query.replace("GROUP BY", f"AND [Société] = ? GROUP BY")
    elif "ORDER BY" in query:
        modified = query.replace("ORDER BY", f"AND [Société] = ? ORDER BY")
    else:
        modified = query + f" AND [Société] = ?"
    return modified, True


def aggregate_by_commercial(balance_data):
    """Agrège les données par commercial."""
    commerciaux = defaultdict(lambda: {
        'nb_clients': 0,
        'encours_total': 0,
        'tranche_0_30': 0,
        'tranche_31_60': 0,
        'tranche_61_90': 0,
        'tranche_91_120': 0,
        'tranche_plus_120': 0,
        'total_impayes': 0
    })

    for row in balance_data:
        comm = row.get('Representant', 'Non défini') or 'Non défini'
        commerciaux[comm]['nb_clients'] += 1
        commerciaux[comm]['encours_total'] += row.get('Solde_Cloture_Num', 0)
        commerciaux[comm]['tranche_0_30'] += row.get('0-30_Num', 0)
        commerciaux[comm]['tranche_31_60'] += row.get('31-60_Num', 0)
        commerciaux[comm]['tranche_61_90'] += row.get('61-90_Num', 0)
        commerciaux[comm]['tranche_91_120'] += row.get('91-120_Num', 0)
        commerciaux[comm]['tranche_plus_120'] += row.get('+120_Num', 0)
        commerciaux[comm]['total_impayes'] += row.get('Impayes_Num', 0)

    result = []
    for comm, data in commerciaux.items():
        result.append({
            'commercial': comm,
            **data
        })

    return sorted(result, key=lambda x: x['encours_total'], reverse=True)


@router.get("")
async def get_recouvrement(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société"),
    commercial: Optional[str] = Query(None)
):
    """
    Récupère les données de recouvrement et DSO.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Balance âgée complète avec valeurs parsées et filtre société
        start_time = time.time()
        balance_data = get_parsed_balance_data(societe)
        query_logger.log_query(
            "balance_agee", "Balance Âgée",
            BALANCE_AGEE, time.time() - start_time, len(balance_data)
        )

        # Balance par commercial (calculée en Python)
        par_commercial = aggregate_by_commercial(balance_data)

        # Top encours (ordre par Solde_Cloture parsé)
        top_encours_sorted = sorted(
            balance_data,
            key=lambda x: x.get('Solde_Cloture_Num', 0),
            reverse=True
        )[:10]

        # Créances douteuses
        creances = [
            row for row in balance_data
            if row.get('+120_Num', 0) > 0 or row.get('Impayes_Num', 0) > 0
        ]
        creances = sorted(creances, key=lambda x: x.get('+120_Num', 0), reverse=True)

        # CA pour calcul DSO (avec filtre société)
        ca_query, has_soc = add_societe_filter_ca(CHIFFRE_AFFAIRES_PAR_PERIODE, societe)
        ca_params = (date_debut_str, date_fin_str, societe) if has_soc else (date_debut_str, date_fin_str)
        ca_data = execute_query(ca_query, ca_params)
        ca_ttc = sum(row.get('CA_TTC', 0) or 0 for row in ca_data)

        # Filtrer par commercial si spécifié
        if commercial:
            balance_data = [b for b in balance_data if b.get('Representant') == commercial]

        # Calculs agrégés
        encours_total = sum(row.get('Solde_Cloture_Num', 0) for row in balance_data)
        total_0_30 = sum(row.get('0-30_Num', 0) for row in balance_data)
        total_31_60 = sum(row.get('31-60_Num', 0) for row in balance_data)
        total_61_90 = sum(row.get('61-90_Num', 0) for row in balance_data)
        total_91_120 = sum(row.get('91-120_Num', 0) for row in balance_data)
        total_plus_120 = sum(row.get('+120_Num', 0) for row in balance_data)
        total_impayes = sum(row.get('Impayes_Num', 0) for row in balance_data)

        # DSO
        dso = calculer_dso(encours_total, ca_ttc)

        # Taux de créances douteuses
        taux_creances = round(total_plus_120 / encours_total * 100, 2) if encours_total > 0 else 0

        return {
            "success": True,
            "dso": dso,
            "encours_total": round(encours_total, 2),
            "repartition_tranches": {
                "0_30": round(total_0_30, 2),
                "31_60": round(total_31_60, 2),
                "61_90": round(total_61_90, 2),
                "91_120": round(total_91_120, 2),
                "plus_120": round(total_plus_120, 2)
            },
            "repartition_pct": {
                "0_30": round(total_0_30 / encours_total * 100, 2) if encours_total > 0 else 0,
                "31_60": round(total_31_60 / encours_total * 100, 2) if encours_total > 0 else 0,
                "61_90": round(total_61_90 / encours_total * 100, 2) if encours_total > 0 else 0,
                "91_120": round(total_91_120 / encours_total * 100, 2) if encours_total > 0 else 0,
                "plus_120": round(total_plus_120 / encours_total * 100, 2) if encours_total > 0 else 0
            },
            "creances_douteuses": round(total_plus_120, 2),
            "taux_creances_douteuses": taux_creances,
            "total_impayes": round(total_impayes, 2),
            "nb_clients": len(balance_data),
            "par_commercial": par_commercial,
            "top_encours": [
                {
                    "client": row.get('CLIENTS', ''),
                    "commercial": row.get('Representant'),
                    "societe": row.get('SOCIETE'),
                    "encours": row.get('Solde_Cloture_Num', 0),
                    "tranche_0_30": row.get('0-30_Num', 0),
                    "tranche_31_60": row.get('31-60_Num', 0),
                    "tranche_61_90": row.get('61-90_Num', 0),
                    "tranche_91_120": row.get('91-120_Num', 0),
                    "tranche_plus_120": row.get('+120_Num', 0),
                    "impayes": row.get('Impayes_Num', 0)
                }
                for row in top_encours_sorted
            ],
            "creances_critiques": [
                {
                    "client": row.get('CLIENTS', ''),
                    "commercial": row.get('Representant'),
                    "societe": row.get('SOCIETE'),
                    "creances_plus_120": row.get('+120_Num', 0),
                    "impayes": row.get('Impayes_Num', 0),
                    "encours_total": row.get('Solde_Cloture_Num', 0)
                }
                for row in creances[:20]
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dso")
async def get_dso(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """
    Calcule le DSO global.
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        # Encours avec parse et filtre société
        balance_data = get_parsed_balance_data(societe)
        encours_total = sum(row.get('Solde_Cloture_Num', 0) for row in balance_data)

        # CA TTC avec filtre société
        ca_query, has_soc = add_societe_filter_ca(CHIFFRE_AFFAIRES_PAR_PERIODE, societe)
        ca_params = (date_debut_str, date_fin_str, societe) if has_soc else (date_debut_str, date_fin_str)
        ca_data = execute_query(ca_query, ca_params)
        ca_ttc = sum(row.get('CA_TTC', 0) or 0 for row in ca_data)

        dso = calculer_dso(encours_total, ca_ttc)

        return {
            "success": True,
            "dso": dso,
            "encours_total": round(encours_total, 2),
            "ca_ttc": round(ca_ttc, 2),
            "interpretation": (
                "Excellent" if dso < 30 else
                "Bon" if dso < 45 else
                "Acceptable" if dso < 60 else
                "À surveiller" if dso < 90 else
                "Critique"
            )
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance-agee")
async def get_balance_agee(
    societe: Optional[str] = Query(None, description="Filtre par société"),
    commercial: Optional[str] = Query(None),
    tranche: Optional[str] = Query(None, description="0-30, 31-60, 61-90, 91-120, +120")
):
    """
    Récupère la balance âgée détaillée.
    """
    try:
        data = get_parsed_balance_data(societe)

        # Filtrer par commercial
        if commercial:
            data = [d for d in data if d.get('Representant') == commercial]

        result = []
        for row in data:
            entry = {
                "client": row.get('CLIENTS', ''),
                "commercial": row.get('Representant'),
                "societe": row.get('SOCIETE'),
                "encours": row.get('Solde_Cloture_Num', 0),
                "impayes": row.get('Impayes_Num', 0),
                "tranche_0_30": row.get('0-30_Num', 0),
                "tranche_31_60": row.get('31-60_Num', 0),
                "tranche_61_90": row.get('61-90_Num', 0),
                "tranche_91_120": row.get('91-120_Num', 0),
                "tranche_plus_120": row.get('+120_Num', 0)
            }

            # Filtrer par tranche si spécifié
            if tranche:
                tranche_key = f"tranche_{tranche.replace('-', '_').replace('+', 'plus_')}"
                if entry.get(tranche_key, 0) > 0:
                    result.append(entry)
            else:
                result.append(entry)

        return {
            "success": True,
            "data": result,
            "total": len(result)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{client_id}")
async def get_client_detail(
    client_id: str,
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """
    Récupère le détail d'un client (encours, historique).
    """
    try:
        data = get_parsed_balance_data(societe)
        client_data = [d for d in data if d.get('CLIENTS', '').strip() == client_id.strip()]

        if not client_data:
            raise HTTPException(status_code=404, detail="Client non trouvé")

        client = client_data[0]

        return {
            "success": True,
            "client": client.get('CLIENTS', ''),
            "commercial": client.get('Representant'),
            "societe": client.get('SOCIETE'),
            "encours_total": client.get('Solde_Cloture_Num', 0),
            "impayes": client.get('Impayes_Num', 0),
            "repartition": {
                "0_30": client.get('0-30_Num', 0),
                "31_60": client.get('31-60_Num', 0),
                "61_90": client.get('61-90_Num', 0),
                "91_120": client.get('91-120_Num', 0),
                "plus_120": client.get('+120_Num', 0)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commercial/{commercial_id}")
async def get_commercial_encours(
    commercial_id: str,
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """
    Récupère l'encours d'un commercial.
    """
    try:
        data = get_parsed_balance_data(societe)
        commercial_data = [d for d in data if d.get('Representant', '').strip() == commercial_id.strip()]

        encours_total = sum(d.get('Solde_Cloture_Num', 0) for d in commercial_data)

        clients = [
            {
                "client": d.get('CLIENTS', ''),
                "societe": d.get('SOCIETE'),
                "encours": d.get('Solde_Cloture_Num', 0),
                "impayes": d.get('Impayes_Num', 0),
                "plus_120": d.get('+120_Num', 0)
            }
            for d in commercial_data
        ]

        return {
            "success": True,
            "commercial": commercial_id,
            "nb_clients": len(commercial_data),
            "encours_total": round(encours_total, 2),
            "clients": sorted(clients, key=lambda x: x['encours'], reverse=True)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tranche/{tranche}")
async def get_clients_par_tranche(
    tranche: str,
    societe: Optional[str] = Query(None, description="Filtre par société"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère les clients d'une tranche d'âge spécifique.
    """
    try:
        data = get_parsed_balance_data(societe)

        # Mapper le nom de tranche
        tranche_map = {
            "0-30": "0-30_Num",
            "31-60": "31-60_Num",
            "61-90": "61-90_Num",
            "91-120": "91-120_Num",
            "+120": "+120_Num",
            "plus120": "+120_Num"
        }
        tranche_col = tranche_map.get(tranche)
        if not tranche_col:
            raise HTTPException(status_code=400, detail="Tranche invalide")

        # Filtrer les clients avec montant > 0 dans cette tranche
        filtered = [
            {
                "client": d.get('CLIENTS', ''),
                "commercial": d.get('Representant'),
                "societe": d.get('SOCIETE'),
                "montant_tranche": d.get(tranche_col, 0),
                "encours_total": d.get('Solde_Cloture_Num', 0)
            }
            for d in data
            if d.get(tranche_col, 0) > 0
        ]

        # Trier par montant décroissant
        filtered = sorted(filtered, key=lambda x: x['montant_tranche'], reverse=True)

        # Pagination
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        return {
            "success": True,
            "tranche": tranche,
            "data": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "total_montant": sum(d['montant_tranche'] for d in filtered)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# NOUVEAUX ENDPOINTS - ECHEANCES VENTES
# =====================================================

@router.get("/echeances")
async def get_echeances(
    societe: Optional[str] = Query(None, description="Filtre par société"),
    client: Optional[str] = Query(None, description="Filtre par code client"),
    commercial: Optional[str] = Query(None, description="Filtre par code collaborateur"),
    tranche: Optional[str] = Query(None, description="Filtre par tranche: a_echoir, 0-30, 31-60, 61-90, 91-120, +120"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    Récupère les échéances non réglées avec détail complet.
    Source: Echéances_Ventes
    """
    try:
        start_time = time.time()

        # Construire la requête avec filtres
        query = ECHEANCES_VENTES_NON_REGLEES
        conditions = []
        params = []

        if societe:
            conditions.append("[DB_Caption] = ?")
            params.append(societe)
        if client:
            conditions.append("[Code client] = ?")
            params.append(client)
        if commercial:
            conditions.append("[Code collaborateur] = ?")
            params.append(commercial)

        if conditions:
            # Insérer les conditions avant ORDER BY ou à la fin
            query = query.replace(
                "WHERE [Montant échéance] > ISNULL([Régler], 0)",
                f"WHERE [Montant échéance] > ISNULL([Régler], 0) AND {' AND '.join(conditions)}"
            )

        data = execute_query(query, tuple(params) if params else None)

        query_logger.log_query(
            "echeances_non_reglees", "Échéances non réglées",
            query, time.time() - start_time, len(data)
        )

        # Filtrer par tranche si spécifié
        if tranche:
            tranche_map = {
                "a_echoir": "A échoir",
                "0-30": "0-30 jours",
                "31-60": "31-60 jours",
                "61-90": "61-90 jours",
                "91-120": "91-120 jours",
                "+120": "+120 jours",
                "plus120": "+120 jours"
            }
            tranche_label = tranche_map.get(tranche)
            if tranche_label:
                data = [d for d in data if d.get('Tranche_Age') == tranche_label]

        # Calculs agrégés
        total_encours = sum(d.get('Reste_A_Regler', 0) or 0 for d in data)

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        return {
            "success": True,
            "data": paginated,
            "total": total,
            "total_encours": round(total_encours, 2),
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/echeances/par-client")
async def get_echeances_par_client(
    societe: Optional[str] = Query(None, description="Filtre par société"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère les échéances agrégées par client avec balance âgée dynamique.
    Source: Echéances_Ventes
    """
    try:
        start_time = time.time()

        query = ECHEANCES_PAR_CLIENT
        if societe:
            query = query.replace(
                "WHERE [Montant échéance] > ISNULL([Régler], 0)",
                f"WHERE [Montant échéance] > ISNULL([Régler], 0) AND [DB_Caption] = ?"
            )
            data = execute_query(query, (societe,))
        else:
            data = execute_query(query)

        query_logger.log_query(
            "echeances_par_client", "Échéances par client",
            query, time.time() - start_time, len(data)
        )

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        return {
            "success": True,
            "data": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/echeances/par-commercial")
async def get_echeances_par_commercial(
    societe: Optional[str] = Query(None, description="Filtre par société")
):
    """
    Récupère les échéances agrégées par commercial/chargé de recouvrement.
    Source: Echéances_Ventes
    """
    try:
        start_time = time.time()

        query = ECHEANCES_PAR_COMMERCIAL
        if societe:
            query = query.replace(
                "WHERE [Montant échéance] > ISNULL([Régler], 0)",
                f"WHERE [Montant échéance] > ISNULL([Régler], 0) AND [DB_Caption] = ?"
            )
            data = execute_query(query, (societe,))
        else:
            data = execute_query(query)

        query_logger.log_query(
            "echeances_par_commercial", "Échéances par commercial",
            query, time.time() - start_time, len(data)
        )

        # Calculs totaux
        total_encours = sum(d.get('Encours_Total', 0) or 0 for d in data)
        total_clients = sum(d.get('Nb_Clients', 0) or 0 for d in data)

        return {
            "success": True,
            "data": data,
            "total_encours": round(total_encours, 2),
            "total_clients": total_clients,
            "nb_commerciaux": len(data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/echeances/par-mode-reglement")
async def get_echeances_par_mode_reglement():
    """
    Récupère les échéances agrégées par mode de règlement.
    Source: Echéances_Ventes
    """
    try:
        start_time = time.time()
        data = execute_query(ECHEANCES_PAR_MODE_REGLEMENT)

        query_logger.log_query(
            "echeances_par_mode", "Échéances par mode règlement",
            ECHEANCES_PAR_MODE_REGLEMENT, time.time() - start_time, len(data)
        )

        return {
            "success": True,
            "data": data,
            "total": len(data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/echeances/a-echoir")
async def get_echeances_a_echoir(
    societe: Optional[str] = Query(None, description="Filtre par société"),
    urgence: Optional[str] = Query(None, description="semaine, 15j, 30j, plus30j"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    Récupère les échéances à venir (non encore échues).
    Source: Echéances_Ventes
    """
    try:
        start_time = time.time()

        query = ECHEANCES_A_ECHOIR
        if societe:
            query = query.replace(
                "WHERE [Date d'échéance] >= GETDATE()",
                f"WHERE [Date d'échéance] >= GETDATE() AND [DB_Caption] = ?"
            )
            data = execute_query(query, (societe,))
        else:
            data = execute_query(query)

        query_logger.log_query(
            "echeances_a_echoir", "Échéances à échoir",
            query, time.time() - start_time, len(data)
        )

        # Filtrer par urgence
        if urgence:
            urgence_map = {
                "semaine": "Cette semaine",
                "15j": "Sous 15 jours",
                "30j": "Sous 30 jours",
                "plus30j": "Plus de 30 jours"
            }
            urgence_label = urgence_map.get(urgence)
            if urgence_label:
                data = [d for d in data if d.get('Urgence') == urgence_label]

        # Calculs
        total_a_echoir = sum(d.get('Montant_A_Regler', 0) or 0 for d in data)

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        return {
            "success": True,
            "data": paginated,
            "total": total,
            "total_a_echoir": round(total_a_echoir, 2),
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# NOUVEAUX ENDPOINTS - REGLEMENTS / IMPUTATIONS
# =====================================================

@router.get("/reglements")
async def get_reglements(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante")
):
    """
    Récupère l'évolution des règlements par période.
    Source: Imputation_Factures_Ventes
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        start_time = time.time()
        data = execute_query(REGLEMENTS_PAR_PERIODE, (date_debut_str, date_fin_str))

        query_logger.log_query(
            "reglements_par_periode", "Règlements par période",
            REGLEMENTS_PAR_PERIODE, time.time() - start_time, len(data)
        )

        # Calculs totaux
        total_reglements = sum(d.get('Total_Reglements', 0) or 0 for d in data)
        nb_total = sum(d.get('Nb_Reglements', 0) or 0 for d in data)

        return {
            "success": True,
            "data": data,
            "total_reglements": round(total_reglements, 2),
            "nb_reglements": nb_total,
            "periode": {"debut": date_debut_str, "fin": date_fin_str}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reglements/par-client")
async def get_reglements_par_client(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Récupère les règlements agrégés par client avec délai moyen.
    Source: Imputation_Factures_Ventes
    """
    try:
        start_time = time.time()
        data = execute_query(REGLEMENTS_PAR_CLIENT)

        query_logger.log_query(
            "reglements_par_client", "Règlements par client",
            REGLEMENTS_PAR_CLIENT, time.time() - start_time, len(data)
        )

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        return {
            "success": True,
            "data": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reglements/par-mode")
async def get_reglements_par_mode(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante")
):
    """
    Récupère les règlements agrégés par mode de règlement.
    Source: Imputation_Factures_Ventes
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        start_time = time.time()
        data = execute_query(REGLEMENTS_PAR_MODE, (date_debut_str, date_fin_str))

        query_logger.log_query(
            "reglements_par_mode", "Règlements par mode",
            REGLEMENTS_PAR_MODE, time.time() - start_time, len(data)
        )

        return {
            "success": True,
            "data": data,
            "total": len(data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factures-non-reglees")
async def get_factures_non_reglees(
    societe: Optional[str] = Query(None, description="Filtre par société"),
    client: Optional[str] = Query(None, description="Filtre par code client"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    Récupère les factures non entièrement réglées.
    Source: Imputation_Factures_Ventes
    """
    try:
        start_time = time.time()

        query = FACTURES_NON_REGLEES
        conditions = []
        params = []

        if societe:
            conditions.append("[DB_Caption] = ?")
            params.append(societe)
        if client:
            conditions.append("[Code client] = ?")
            params.append(client)

        if conditions:
            query = query.replace(
                "WHERE [Montant facture TTC] > ISNULL([Montant régler], 0)",
                f"WHERE [Montant facture TTC] > ISNULL([Montant régler], 0) AND {' AND '.join(conditions)}"
            )

        data = execute_query(query, tuple(params) if params else None)

        query_logger.log_query(
            "factures_non_reglees", "Factures non réglées",
            query, time.time() - start_time, len(data)
        )

        # Calculs
        total_reste = sum(d.get('Reste_A_Regler', 0) or 0 for d in data)

        # Pagination
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = data[start:end]

        return {
            "success": True,
            "data": paginated,
            "total": total,
            "total_reste_a_regler": round(total_reste, 2),
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historique-client/{code_client}")
async def get_historique_reglements_client(code_client: str):
    """
    Récupère l'historique complet des règlements d'un client.
    Source: Imputation_Factures_Ventes
    """
    try:
        start_time = time.time()
        data = execute_query(HISTORIQUE_REGLEMENTS_CLIENT, (code_client,))

        query_logger.log_query(
            "historique_client", f"Historique client {code_client}",
            HISTORIQUE_REGLEMENTS_CLIENT, time.time() - start_time, len(data)
        )

        if not data:
            return {
                "success": True,
                "code_client": code_client,
                "data": [],
                "total_regle": 0,
                "delai_moyen": 0,
                "nb_reglements": 0
            }

        # Calculs
        total_regle = sum(d.get('Montant_réglement', 0) or 0 for d in data)
        delais = [d.get('Delai_Reglement_Jours', 0) for d in data if d.get('Delai_Reglement_Jours') is not None]
        delai_moyen = sum(delais) / len(delais) if delais else 0

        return {
            "success": True,
            "code_client": code_client,
            "data": data,
            "total_regle": round(total_regle, 2),
            "delai_moyen_jours": round(delai_moyen, 1),
            "nb_reglements": len(data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# KPIs ENRICHIS
# =====================================================

@router.get("/kpis")
async def get_kpis_recouvrement():
    """
    Récupère les KPIs enrichis du recouvrement.
    Sources: Echéances_Ventes + Imputation_Factures_Ventes
    """
    try:
        start_time = time.time()
        data = execute_query(KPIS_RECOUVREMENT)

        query_logger.log_query(
            "kpis_recouvrement", "KPIs Recouvrement",
            KPIS_RECOUVREMENT, time.time() - start_time, 1
        )

        if data:
            kpis = data[0]
            encours = kpis.get('Encours_Total', 0) or 0
            echu = kpis.get('Echu', 0) or 0

            return {
                "success": True,
                "encours_total": round(encours, 2),
                "a_echoir": round(kpis.get('A_Echoir', 0) or 0, 2),
                "echu": round(echu, 2),
                "taux_echu": round(echu / encours * 100, 2) if encours > 0 else 0,
                "nb_echeances_retard": kpis.get('Nb_Echeances_Retard', 0) or 0,
                "nb_clients_retard": kpis.get('Nb_Clients_Retard', 0) or 0,
                "reglements_mois": round(kpis.get('Reglements_Mois', 0) or 0, 2),
                "retard_moyen_jours": round(kpis.get('Retard_Moyen_Jours', 0) or 0, 1)
            }

        return {"success": True, "message": "Aucune donnée disponible"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution")
async def get_evolution_recouvrement(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante")
):
    """
    Récupère l'évolution mensuelle des règlements.
    Source: Imputation_Factures_Ventes
    """
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        start_time = time.time()
        data = execute_query(EVOLUTION_RECOUVREMENT, (date_debut_str, date_fin_str))

        query_logger.log_query(
            "evolution_recouvrement", "Évolution recouvrement",
            EVOLUTION_RECOUVREMENT, time.time() - start_time, len(data)
        )

        return {
            "success": True,
            "data": data,
            "periode": {"debut": date_debut_str, "fin": date_fin_str}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
