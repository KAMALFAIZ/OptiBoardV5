"""
Ajoute Valorisation + ValorisationCA à DS_CA_DETAIL_COMPLET, DS_MARGE_NEGATIVE, DS_MARGE_PAR_GAMME
et met à jour leurs requêtes SQL pour utiliser @Valorisation (CASE WHEN) et @ValorisationCA.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database_unified import get_central_connection

VALO_PARAM = {
    "name": "Valorisation",
    "type": "select",
    "source": "fixed",
    "required": True,
    "label": "Méthode de valorisation",
    "default": "Prix de revient",
    "options": ["Prix de revient", "CMUP", "Dernier Prix d'achat", "Prix d'achat", "Coût standard"]
}

VALO_CA_PARAM = {
    "name": "ValorisationCA",
    "type": "select",
    "source": "fixed",
    "required": False,
    "label": "Valorisation CA",
    "default": "HT",
    "options": ["HT", "TTC"]
}

# ─── Helper CASE expressions ────────────────────────────────────────────────

def case_valo(prefix="", indent="                "):
    p = f"{prefix}." if prefix else ""
    return (
        f"CASE @Valorisation\n"
        f"{indent}    WHEN 'Prix de revient'       THEN {p}[Prix de revient]\n"
        f"{indent}    WHEN 'CMUP'                  THEN {p}[CMUP]\n"
        f"{indent}    WHEN 'Dernier Prix d''achat'  THEN {p}[Dernier Prix d''achat]\n"
        f"{indent}    WHEN 'Prix d''achat'          THEN {p}[Prix d''achat]\n"
        f"{indent}    WHEN 'Coût standard'          THEN {p}[Coût standard]\n"
        f"{indent}    ELSE 0\n"
        f"{indent}END"
    )

def case_ca(prefix="", indent="                "):
    p = f"{prefix}." if prefix else ""
    return f"CASE @ValorisationCA WHEN 'TTC' THEN {p}[Montant TTC Net] ELSE {p}[Montant HT Net] END"

# ─── Nouvelles requêtes ──────────────────────────────────────────────────────

QUERY_MARGE_NEGATIVE = """\
SELECT
                [societe] AS [Société],
                [Date BL] AS [Date],
                [N° Pièce] AS [Num Piece],
                [Code client] AS [Code Client],
                [Intitulé client] AS [Client],
                [Code article] AS [Code Article],
                [Désignation ligne] AS [Designation],
                [Catalogue 1] AS [Catalogue],
                [Gamme 1] AS [Gamme],
                [Quantité] AS [Qte],
                [Prix unitaire] AS [PU HT],
                CASE @Valorisation
                    WHEN 'Prix de revient'       THEN [Prix de revient]
                    WHEN 'CMUP'                  THEN [CMUP]
                    WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                    WHEN 'Prix d''achat'          THEN [Prix d''achat]
                    WHEN 'Coût standard'          THEN [Coût standard]
                    ELSE 0
                END AS [Cout Revient],
                CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END AS [CA],
                CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END
                    - ISNULL(CASE @Valorisation
                        WHEN 'Prix de revient'       THEN [Prix de revient]
                        WHEN 'CMUP'                  THEN [CMUP]
                        WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                        WHEN 'Prix d''achat'          THEN [Prix d''achat]
                        WHEN 'Coût standard'          THEN [Coût standard]
                        ELSE 0 END, 0) * [Quantité] AS [Marge],
                CASE WHEN (CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END) <> 0
                    THEN ROUND((
                        (CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END)
                        - ISNULL(CASE @Valorisation
                            WHEN 'Prix de revient'       THEN [Prix de revient]
                            WHEN 'CMUP'                  THEN [CMUP]
                            WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                            WHEN 'Prix d''achat'          THEN [Prix d''achat]
                            WHEN 'Coût standard'          THEN [Coût standard]
                            ELSE 0 END, 0) * [Quantité]
                    ) * 100.0 / (CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %],
                [Code représentant] AS [Code Commercial],
                [Nom représentant] AS [Commercial]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (
                (CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END)
                - ISNULL(CASE @Valorisation
                    WHEN 'Prix de revient'       THEN [Prix de revient]
                    WHEN 'CMUP'                  THEN [CMUP]
                    WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                    WHEN 'Prix d''achat'          THEN [Prix d''achat]
                    WHEN 'Coût standard'          THEN [Coût standard]
                    ELSE 0 END, 0) * [Quantité]
              ) < 0
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            ORDER BY (
                (CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END)
                - ISNULL(CASE @Valorisation
                    WHEN 'Prix de revient'       THEN [Prix de revient]
                    WHEN 'CMUP'                  THEN [CMUP]
                    WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                    WHEN 'Prix d''achat'          THEN [Prix d''achat]
                    WHEN 'Coût standard'          THEN [Coût standard]
                    ELSE 0 END, 0) * [Quantité]
            ) ASC"""

QUERY_MARGE_PAR_GAMME = """\
SELECT
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)') AS [Gamme],
                ISNULL(NULLIF([Gamme 2], ''), '(Non classé)') AS [Sous Gamme],
                [societe] AS [Société],
                SUM(CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END) AS [CA],
                SUM(ISNULL(CASE @Valorisation
                    WHEN 'Prix de revient'       THEN [Prix de revient]
                    WHEN 'CMUP'                  THEN [CMUP]
                    WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                    WHEN 'Prix d''achat'          THEN [Prix d''achat]
                    WHEN 'Coût standard'          THEN [Coût standard]
                    ELSE 0 END, 0) * [Quantité]) AS [Cout Revient],
                SUM(
                    CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END
                    - ISNULL(CASE @Valorisation
                        WHEN 'Prix de revient'       THEN [Prix de revient]
                        WHEN 'CMUP'                  THEN [CMUP]
                        WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                        WHEN 'Prix d''achat'          THEN [Prix d''achat]
                        WHEN 'Coût standard'          THEN [Coût standard]
                        ELSE 0 END, 0) * [Quantité]
                ) AS [Marge],
                CASE WHEN SUM(CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END) > 0
                    THEN ROUND(
                        SUM(
                            CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END
                            - ISNULL(CASE @Valorisation
                                WHEN 'Prix de revient'       THEN [Prix de revient]
                                WHEN 'CMUP'                  THEN [CMUP]
                                WHEN 'Dernier Prix d''achat'  THEN [Dernier Prix d''achat]
                                WHEN 'Prix d''achat'          THEN [Prix d''achat]
                                WHEN 'Coût standard'          THEN [Coût standard]
                                ELSE 0 END, 0) * [Quantité]
                        ) * 100.0
                        / SUM(CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END)
                    , 2)
                    ELSE 0 END AS [Marge %],
                SUM([Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)'),
                ISNULL(NULLIF([Gamme 2], ''), '(Non classé)'),
                [societe]
            ORDER BY [Marge] DESC"""

QUERY_CA_DETAIL_COMPLET = """\
SELECT
                e.[Type Document],
                e.societe AS [Société entête],
                e.Souche,
                e.Statut,
                e.[Intitulé client],
                e.[Code client],
                e.[Nom représentant],
                e.Date,
                e.[N° pièce],
                e.Etat,
                e.[Intitulé tiers payeur],
                e.[N° Compte Payeur],
                e.[Code d'affaire],
                e.[Intitulé affaire],
                e.[Catégorie Comptable],
                e.Cours,
                e.Référence,
                e.[Montant réglé],
                e.[Montant net à payer],
                e.[Entête 1],
                e.[Entête 2],
                e.[Entête 3],
                e.[Entête 4],
                e.Devise,
                e.[Type frais],
                e.[Valeur frais],
                e.[Montant TTC] AS [Montant TTC Entete],
                e.[Montant HT] AS [Montant HT Entete],
                l.[Valorise CA],
                l.[N° Pièce BL],
                l.[Date BL],
                l.[N° Pièce BC],
                l.[Date BC],
                l.[N° pièce PL],
                l.[Date PL],
                l.[Désignation ligne] AS [Désignation Ligne],
                l.Colisage,
                l.[N° Série/Lot],
                l.Taxe1,
                l.[Type taux taxe 1],
                l.[Remise 1],
                l.[Frais d'approche],
                l.[Prix unitaire],
                l.[Prix unitaire TTC],
                l.Quantité,
                l.[Montant HT Net],
                l.[Montant TTC Net],
                CASE @ValorisationCA WHEN 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END AS [CA],
                c.Ville,
                c.Région,
                a.[Code Famille],
                a.[Intitulé famille],
                a.[Désignation Article],
                a.[Libellé Gamme 1],
                a.[Libellé Gamme 2],
                a.[Catalogue 1],
                a.[Catalogue 2],
                a.[Catalogue 3],
                a.[Catalogue 4],
                a.[Unité Vente],
                l.[PU Devise],
                e.Dépôt,
                l.[Gamme 1],
                l.[Gamme 2],
                l.[Poids brut],
                l.[Poids net],
                a.[Prix d'achat],
                c.[Catégorie tarifaire],
                CASE @Valorisation
                    WHEN 'Prix de revient'       THEN l.[Prix de revient]
                    WHEN 'CMUP'                  THEN l.[CMUP]
                    WHEN 'Dernier Prix d''achat'  THEN l.[Dernier Prix d''achat]
                    WHEN 'Prix d''achat'          THEN l.[Prix d''achat]
                    WHEN 'Coût standard'          THEN l.[Coût standard]
                    ELSE 0
                END AS [Coût Unitaire],
                l.Quantité * ISNULL(CASE @Valorisation
                    WHEN 'Prix de revient'       THEN l.[Prix de revient]
                    WHEN 'CMUP'                  THEN l.[CMUP]
                    WHEN 'Dernier Prix d''achat'  THEN l.[Dernier Prix d''achat]
                    WHEN 'Prix d''achat'          THEN l.[Prix d''achat]
                    WHEN 'Coût standard'          THEN l.[Coût standard]
                    ELSE 0 END, 0) AS [Coût Total],
                CASE @ValorisationCA WHEN 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END
                    - l.Quantité * ISNULL(CASE @Valorisation
                        WHEN 'Prix de revient'       THEN l.[Prix de revient]
                        WHEN 'CMUP'                  THEN l.[CMUP]
                        WHEN 'Dernier Prix d''achat'  THEN l.[Dernier Prix d''achat]
                        WHEN 'Prix d''achat'          THEN l.[Prix d''achat]
                        WHEN 'Coût standard'          THEN l.[Coût standard]
                        ELSE 0 END, 0) AS [Marge],
                CASE WHEN (CASE @ValorisationCA WHEN 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END) <> 0
                    THEN ROUND((
                        (CASE @ValorisationCA WHEN 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END)
                        - l.Quantité * ISNULL(CASE @Valorisation
                            WHEN 'Prix de revient'       THEN l.[Prix de revient]
                            WHEN 'CMUP'                  THEN l.[CMUP]
                            WHEN 'Dernier Prix d''achat'  THEN l.[Dernier Prix d''achat]
                            WHEN 'Prix d''achat'          THEN l.[Prix d''achat]
                            WHEN 'Coût standard'          THEN l.[Coût standard]
                            ELSE 0 END, 0)
                    ) * 100.0 / (CASE @ValorisationCA WHEN 'TTC' THEN l.[Montant TTC Net] ELSE l.[Montant HT Net] END), 2)
                    ELSE 0 END AS [Marge %]
            FROM Entête_des_ventes AS e
            INNER JOIN Clients AS c
                ON e.[Code client] = c.[Code client] AND e.societe = c.societe
            INNER JOIN Lignes_des_ventes AS l
                ON e.societe = l.societe AND e.[Type Document] = l.[Type Document] AND e.[N° pièce] = l.[N° Pièce]
            INNER JOIN Articles AS a
                ON l.societe = a.societe AND l.[Code article] = a.[Code Article]
            WHERE l.[Date BL] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR e.societe = @societe)
              AND l.[Valorise CA] = 'Oui'
            ORDER BY e.Date DESC, e.[N° pièce]"""


# ─── Appliquer ───────────────────────────────────────────────────────────────

UPDATES = {
    'DS_MARGE_NEGATIVE':    QUERY_MARGE_NEGATIVE,
    'DS_MARGE_PAR_GAMME':   QUERY_MARGE_PAR_GAMME,
    'DS_CA_DETAIL_COMPLET': QUERY_CA_DETAIL_COMPLET,
}

conn = get_central_connection()
cur  = conn.cursor()

for code, new_query in UPDATES.items():
    cur.execute("SELECT id, parameters FROM APP_DataSources_Templates WHERE code=?", (code,))
    row = cur.fetchone()
    if not row:
        print(f"  [SKIP] {code} — introuvable")
        continue

    ds_id, params_raw = row
    params = json.loads(params_raw) if params_raw else []

    # Ajouter Valorisation si absent
    if not any(p.get('name') == 'Valorisation' for p in params):
        params.append(VALO_PARAM)
        print(f"  [{code}] + Valorisation ajouté")

    # Ajouter ValorisationCA si absent
    if not any(p.get('name') == 'ValorisationCA' for p in params):
        params.append(VALO_CA_PARAM)
        print(f"  [{code}] + ValorisationCA ajouté")

    params_json = json.dumps(params, ensure_ascii=False)

    cur.execute(
        "UPDATE APP_DataSources_Templates SET query_template=?, parameters=? WHERE id=?",
        (new_query, params_json, ds_id)
    )
    print(f"  [{code}] ✓ Sauvegardé (id={ds_id})")

conn.commit()
conn.close()
print("\n[DONE] Datasources marge mises à jour.")
