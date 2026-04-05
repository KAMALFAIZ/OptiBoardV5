"""KPIs globaux pour le dashboard."""
from fastapi import APIRouter
from ..database import execute

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard_kpis():
    """KPIs globaux : contacts, tickets, campagnes, livraisons."""
    contacts = execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN segment='prospect' THEN 1 ELSE 0 END) AS prospects,
             SUM(CASE WHEN segment='lead'     THEN 1 ELSE 0 END) AS leads,
             SUM(CASE WHEN segment='client'   THEN 1 ELSE 0 END) AS clients,
             SUM(CASE WHEN CAST(created_at AS DATE)=CAST(GETDATE() AS DATE) THEN 1 ELSE 0 END) AS today
           FROM HUB_Contacts WHERE actif=1"""
    )
    tickets = execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN statut='open'        THEN 1 ELSE 0 END) AS open_count,
             SUM(CASE WHEN statut='in_progress'  THEN 1 ELSE 0 END) AS inprog_count,
             SUM(CASE WHEN statut='overdue'      THEN 1 ELSE 0 END) AS overdue_count,
             SUM(CASE WHEN statut='resolved' AND CAST(resolved_at AS DATE)=CAST(GETDATE() AS DATE) THEN 1 ELSE 0 END) AS resolved_today,
             AVG(CASE WHEN resolved_at IS NOT NULL THEN DATEDIFF(HOUR, created_at, resolved_at) END) AS avg_resolution_h
           FROM HUB_Tickets"""
    )
    campaigns = execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN statut='active' THEN 1 ELSE 0 END) AS active_count,
             SUM(CASE WHEN statut='draft'  THEN 1 ELSE 0 END) AS draft_count
           FROM HUB_Campaigns"""
    )
    deliveries = execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN statut='sent'   THEN 1 ELSE 0 END) AS sent_count,
             SUM(CASE WHEN statut='failed' THEN 1 ELSE 0 END) AS failed_count,
             SUM(CASE WHEN CAST(sent_at AS DATE)=CAST(GETDATE() AS DATE) THEN 1 ELSE 0 END) AS today_count
           FROM HUB_DeliveryLog"""
    )

    return {
        "success": True,
        "data": {
            "contacts": contacts[0] if contacts else {},
            "tickets": tickets[0] if tickets else {},
            "campaigns": campaigns[0] if campaigns else {},
            "deliveries": deliveries[0] if deliveries else {},
        },
    }


@router.get("/contacts/evolution")
async def contacts_evolution():
    """Évolution des contacts sur les 30 derniers jours."""
    rows = execute(
        """SELECT CAST(created_at AS DATE) AS date, COUNT(*) AS count
           FROM HUB_Contacts
           WHERE created_at >= DATEADD(DAY, -30, GETDATE())
           GROUP BY CAST(created_at AS DATE)
           ORDER BY date"""
    )
    return {"success": True, "data": rows}


@router.get("/contacts/by-product")
async def contacts_by_product():
    rows = execute(
        """SELECT c.product_code, p.nom AS product_nom, p.couleur,
                  COUNT(*) AS total,
                  SUM(CASE WHEN c.segment='prospect' THEN 1 ELSE 0 END) AS prospects,
                  SUM(CASE WHEN c.segment='lead'     THEN 1 ELSE 0 END) AS leads,
                  SUM(CASE WHEN c.segment='client'   THEN 1 ELSE 0 END) AS clients
           FROM HUB_Contacts c
           JOIN HUB_Products p ON p.code=c.product_code
           WHERE c.actif=1
           GROUP BY c.product_code, p.nom, p.couleur"""
    )
    return {"success": True, "data": rows}


@router.get("/tickets/by-product")
async def tickets_by_product():
    rows = execute(
        """SELECT t.product_code, p.nom AS product_nom, p.couleur,
                  COUNT(*) AS total,
                  SUM(CASE WHEN t.statut IN ('open','in_progress') THEN 1 ELSE 0 END) AS open_count,
                  SUM(CASE WHEN t.statut='overdue' THEN 1 ELSE 0 END) AS overdue_count
           FROM HUB_Tickets t
           JOIN HUB_Products p ON p.code=t.product_code
           GROUP BY t.product_code, p.nom, p.couleur"""
    )
    return {"success": True, "data": rows}


@router.get("/deliveries/by-channel")
async def deliveries_by_channel():
    rows = execute(
        """SELECT channel,
                  COUNT(*) AS total,
                  SUM(CASE WHEN statut='sent'   THEN 1 ELSE 0 END) AS sent,
                  SUM(CASE WHEN statut='failed' THEN 1 ELSE 0 END) AS failed
           FROM HUB_DeliveryLog
           GROUP BY channel"""
    )
    return {"success": True, "data": rows}
