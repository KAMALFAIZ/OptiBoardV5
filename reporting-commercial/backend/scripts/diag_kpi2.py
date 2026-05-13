# -*- coding: utf-8 -*-
"""Diagnostic KPI widgets dashboard 166"""
import pyodbc

SAAS = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019'
DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'

# 1. Vérifier la config pivot/widgets pour dashboard 166
print("=== Widgets KPI du dashboard 166 ===")
conn = pyodbc.connect(SAAS, timeout=15)
c = conn.cursor()
c.execute("""
SELECT p.id, p.titre, p.datasource_code, p.type_affichage, p.config
FROM APP_Pivots_V2 p
WHERE p.dashboard_id = 166
ORDER BY p.id
""")
for row in c.fetchall():
    print(f"id={row[0]}, titre={row[1]}, ds={row[2]}, type={row[3]}")
    if row[4]:
        import json
        try:
            cfg = json.loads(row[4])
            # Show relevant keys
            for k in ['kpiField', 'valueField', 'metric', 'field', 'columns']:
                if k in cfg:
                    print(f"  {k}: {cfg[k]}")
        except:
            print(f"  config(raw): {str(row[4])[:200]}")
conn.close()

# 2. Tester la query complète DS_KPI_RESUME avec tables DWH_KA
print("\n=== Test query complète DS_KPI_RESUME sur DWH_KA ===")
try:
    conn2 = pyodbc.connect(DWH_KA, timeout=20)
    c2 = conn2.cursor()

    # Tester si les tables existent
    for tbl in ['Lignes_des_ventes', 'Etat_Stock', 'Echéances_Ventes', 'Échéances_Ventes']:
        try:
            c2.execute(f"SELECT TOP 1 1 FROM [{tbl}]")
            c2.fetchone()
            print(f"  Table [{tbl}]: OK")
        except Exception as e:
            print(f"  Table [{tbl}]: ERREUR - {str(e)[:80]}")

    # Tester la query complète
    print("\n--- Query complète avec paramètres ---")
    try:
        c2.execute("""
        DECLARE @dateDebut DATE = '2025-01-01'
        DECLARE @dateFin DATE = '2025-12-31'
        DECLARE @societe NVARCHAR(50) = NULL
        SELECT
            (SELECT ISNULL(SUM([Montant HT Net]), 0)
             FROM [Lignes_des_ventes]
             WHERE [Valorise CA] = 'Oui'
               AND [Date BL] BETWEEN @dateDebut AND @dateFin
               AND (@societe IS NULL OR [societe] = @societe)) AS CA,
            (SELECT ISNULL(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]), 0)
             FROM [Lignes_des_ventes]
             WHERE [Valorise CA] = 'Oui'
               AND [Date BL] BETWEEN @dateDebut AND @dateFin
               AND (@societe IS NULL OR [societe] = @societe)) AS Marge,
            (SELECT COUNT(DISTINCT [Code article])
             FROM [Lignes_des_ventes]
             WHERE [Valorise CA] = 'Oui'
               AND [Date BL] BETWEEN @dateDebut AND @dateFin
               AND (@societe IS NULL OR [societe] = @societe)) AS NbArticlesVendus,
            (SELECT ISNULL(SUM([Valeur du stock (montant)]), 0)
             FROM [Etat_Stock]
             WHERE (@societe IS NULL OR [societe] = @societe)) AS ValeurStock
        """)
        r = c2.fetchone()
        if r:
            print(f"  CA={r[0]}, Marge={r[1]}, NbArticles={r[2]}, ValeurStock={r[3]}")
        else:
            print("  Aucun résultat!")
    except Exception as e:
        print(f"  ERREUR query: {e}")

    conn2.close()
except Exception as e:
    print(f"Erreur connexion: {e}")
