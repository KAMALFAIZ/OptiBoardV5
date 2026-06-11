"""
Ajoute Valorisation + ValorisationCA à DS_VENTES_PAR_GAMME, DS_VENTES_PAR_CATALOGUE, DS_VENTES_GAMME_MOIS
et remplace [CMUP] hardcodé par CASE @Valorisation + [Montant HT Net] par CASE @ValorisationCA.
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

QUERY_VENTES_PAR_GAMME = """\
SELECT
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)') AS [Gamme],
                ISNULL(NULLIF([Gamme 2], ''), '(Non classé)') AS [Sous Gamme],
                [societe] AS [Société],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
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
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Documents]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)'),
                ISNULL(NULLIF([Gamme 2], ''), '(Non classé)'),
                [societe]
            ORDER BY [CA] DESC"""

QUERY_VENTES_PAR_CATALOGUE = """\
SELECT
                ISNULL([Catalogue 1], '(Non classé)') AS [Catalogue],
                ISNULL([Catalogue 2], '(Non classé)') AS [Sous Catalogue],
                COUNT(DISTINCT [Code article]) AS [Nb Articles],
                SUM([Quantité]) AS [Qte Vendue],
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
                COUNT(DISTINCT [Code client]) AS [Nb Clients],
                CASE WHEN COUNT(DISTINCT [Code article]) > 0
                    THEN ROUND(
                        SUM(CASE @ValorisationCA WHEN 'TTC' THEN [Montant TTC Net] ELSE [Montant HT Net] END)
                        / COUNT(DISTINCT [Code article]), 2)
                    ELSE 0 END AS [CA Moyen par Article]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY
                ISNULL([Catalogue 1], '(Non classé)'),
                ISNULL([Catalogue 2], '(Non classé)')
            ORDER BY [CA] DESC"""

QUERY_VENTES_GAMME_MOIS = """\
SELECT
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)') AS [Gamme],
                FORMAT([Date BL], 'yyyy-MM') AS [Periode],
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
                SUM([Quantité]) AS [Qte Vendue],
                COUNT(DISTINCT [Code client]) AS [Nb Clients]
            FROM [Lignes_des_ventes]
            WHERE [Valorise CA] = 'Oui'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date BL] BETWEEN @dateDebut AND @dateFin
            GROUP BY
                ISNULL(NULLIF([Gamme 1], ''), '(Non classé)'),
                FORMAT([Date BL], 'yyyy-MM'),
                [societe]
            ORDER BY [Gamme], [Periode]"""


UPDATES = {
    'DS_VENTES_PAR_GAMME':    QUERY_VENTES_PAR_GAMME,
    'DS_VENTES_PAR_CATALOGUE': QUERY_VENTES_PAR_CATALOGUE,
    'DS_VENTES_GAMME_MOIS':   QUERY_VENTES_GAMME_MOIS,
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

    if not any(p.get('name') == 'Valorisation' for p in params):
        params.append(VALO_PARAM)
        print(f"  [{code}] + Valorisation ajouté")

    if not any(p.get('name') == 'ValorisationCA' for p in params):
        params.append(VALO_CA_PARAM)
        print(f"  [{code}] + ValorisationCA ajouté")

    cur.execute(
        "UPDATE APP_DataSources_Templates SET query_template=?, parameters=? WHERE id=?",
        (new_query, json.dumps(params, ensure_ascii=False), ds_id)
    )
    print(f"  [{code}] ✓ Sauvegardé (id={ds_id})")

conn.commit()
conn.close()
print("\n[DONE]")
