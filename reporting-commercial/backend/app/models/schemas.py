"""Pydantic schemas for API responses"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date


# Base Response
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


# KPIs
class KPIData(BaseModel):
    label: str
    value: float
    formatted_value: str
    evolution: Optional[float] = None
    tendance: Optional[str] = None
    unite: Optional[str] = None


class DashboardKPIs(BaseModel):
    ca_ht: KPIData
    marge_brute: KPIData
    dso: KPIData
    encours_clients: KPIData
    nb_clients_actifs: KPIData
    creances_douteuses: KPIData


class AlerteData(BaseModel):
    type: str
    niveau: str  # info, warning, critical
    message: str
    valeur: Optional[float] = None


class DashboardResponse(BaseResponse):
    kpis: DashboardKPIs
    alertes: List[AlerteData] = []
    date_mise_a_jour: datetime


# Ventes
class VenteParPeriode(BaseModel):
    annee: int
    mois: int
    ca_ht: float
    ca_ttc: float
    cout_total: float
    marge_brute: float
    nb_clients: int
    nb_transactions: int


class VenteParGamme(BaseModel):
    gamme: str
    ca_ht: float
    ca_ttc: float
    cout_total: float
    marge_brute: float
    taux_marge: float
    nb_ventes: int
    pourcentage_ca: Optional[float] = None


class VenteParCanal(BaseModel):
    canal: str
    ca_ht: float
    ca_ttc: float
    cout_total: float
    nb_clients: int


class VenteParZone(BaseModel):
    zone: str
    ca_ht: float
    ca_ttc: float
    nb_clients: int


class VenteParCommercial(BaseModel):
    commercial: str
    ca_ht: float
    ca_ttc: float
    cout_total: float
    marge_brute: float
    nb_clients: int
    nb_ventes: int
    objectif: Optional[float] = None
    taux_realisation: Optional[float] = None


class TopClient(BaseModel):
    code_client: str
    nom_client: str
    commercial: Optional[str] = None
    ca_ht: float
    ca_ttc: float
    nb_transactions: int


class TopProduit(BaseModel):
    code_article: str
    designation: str
    gamme: Optional[str] = None
    quantite_vendue: float
    ca_ht: float
    cout_total: float


class VentesResponse(BaseResponse):
    ca_total_ht: float
    ca_total_ttc: float
    evolution_vs_n1: Optional[float] = None
    par_periode: List[VenteParPeriode] = []
    par_gamme: List[VenteParGamme] = []
    par_canal: List[VenteParCanal] = []
    par_zone: List[VenteParZone] = []
    par_commercial: List[VenteParCommercial] = []
    top_clients: List[TopClient] = []
    top_produits: List[TopProduit] = []


# Stocks
class StockParArticle(BaseModel):
    code_article: str
    designation: str
    gamme: Optional[str] = None
    entrees: float
    sorties: float
    stock_actuel: float
    cmup_moyen: Optional[float] = None
    valeur_stock: Optional[float] = None
    dernier_mouvement: Optional[datetime] = None


class StockDormant(BaseModel):
    code_article: str
    designation: str
    gamme: Optional[str] = None
    dernier_mouvement: Optional[datetime] = None
    jours_sans_mouvement: int
    stock_actuel: float
    valeur_stock: float


class RotationStock(BaseModel):
    gamme: str
    sorties_valeur: float
    stock_moyen_valeur: float
    rotation: float
    couverture_jours: Optional[float] = None


class MouvementStock(BaseModel):
    date_mouvement: datetime
    type_mouvement: str
    numero_piece: Optional[str] = None
    quantite: float
    sens_mouvement: str
    cmup: Optional[float] = None
    montant_stock: Optional[float] = None
    client: Optional[str] = None
    commercial: Optional[str] = None


class StocksResponse(BaseResponse):
    valeur_totale_stock: float
    nb_articles: int
    stock_dormant_valeur: float
    stock_dormant_nb_articles: int
    par_article: List[StockParArticle] = []
    articles_dormants: List[StockDormant] = []
    rotation_par_gamme: List[RotationStock] = []


# Recouvrement
class BalanceAgeeClient(BaseModel):
    client: str
    commercial: Optional[str] = None
    societe: Optional[str] = None
    encours: float
    tranche_0_30: float
    tranche_31_60: float
    tranche_61_90: float
    tranche_91_120: float
    tranche_plus_120: float
    impayes: float


class BalanceAgeeParCommercial(BaseModel):
    commercial: str
    nb_clients: int
    encours_total: float
    tranche_0_30: float
    tranche_31_60: float
    tranche_61_90: float
    tranche_91_120: float
    tranche_plus_120: float
    total_impayes: float


class RecouvrementResponse(BaseResponse):
    dso: float
    encours_total: float
    repartition_tranches: Dict[str, float]
    creances_douteuses: float
    taux_creances_douteuses: float
    par_commercial: List[BalanceAgeeParCommercial] = []
    top_encours: List[BalanceAgeeClient] = []
    creances_critiques: List[BalanceAgeeClient] = []


# Drill-Down
class DrillDownRequest(BaseModel):
    type: str  # ca, stock, recouvrement
    dimension: str  # gamme, client, commercial, article, etc.
    valeur: Optional[str] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    page: int = 1
    page_size: int = 50


class DrillDownResponse(BaseResponse):
    type: str
    dimension: str
    titre: str
    breadcrumb: List[str] = []
    data: List[Dict[str, Any]] = []
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


# Admin SQL
class QueryInfo(BaseModel):
    id: str
    name: str
    description: str
    sql: str
    table: str
    category: str
    avg_time: Optional[float] = None
    total_executions: Optional[int] = None
    last_execution: Optional[datetime] = None


class QueryExecuteRequest(BaseModel):
    query: str
    limit: int = 100


class QueryExecuteResponse(BaseResponse):
    data: List[Dict[str, Any]] = []
    columns: List[str] = []
    row_count: int
    execution_time: float


class QueryStatsResponse(BaseResponse):
    queries: List[Dict[str, Any]] = []
    slowest_queries: List[Dict[str, Any]] = []
    total_executions: int
    avg_execution_time: float


# Export
class ExportRequest(BaseModel):
    type: str  # pdf, excel
    module: str  # dashboard, ventes, stocks, recouvrement
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    filtres: Optional[Dict[str, Any]] = None


class ExportResponse(BaseResponse):
    file_path: str
    file_name: str
    file_size: int
