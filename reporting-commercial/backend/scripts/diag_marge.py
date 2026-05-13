# -*- coding: utf-8 -*-
"""Diagnostic complet du problème Marge = 100%"""
import pyodbc

# Test sur les 2 DWH
for db in ['DWH_KA', 'DWH_GO']:
    print(f"\n{'='*60}")
    print(f"=== {db} ===")
    print(f"{'='*60}")
    try:
        conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=kasoft.selfip.net;DATABASE={db};UID=sa;PWD=SQL@2019', timeout=15)
        c = conn.cursor()

        # 1. Vérifier les colonnes CMUP / CMUP
        print("\n--- Colonnes prix/cout dans Lignes_des_ventes ---")
        c.execute("""SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
                     WHERE TABLE_NAME = 'Lignes_des_ventes'
                     AND (COLUMN_NAME LIKE '%prix%' OR COLUMN_NAME LIKE '%cout%' OR COLUMN_NAME LIKE '%revient%' OR COLUMN_NAME LIKE '%CMUP%')
                     ORDER BY COLUMN_NAME""")
        cols = c.fetchall()
        for col in cols:
            print(f"  {col[0]} ({col[1]})")

        # 2. Vérifier si CMUP a des valeurs non-nulles
        print("\n--- Valeurs CMUP ---")
        c.execute("""SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN [CMUP] IS NULL THEN 1 ELSE 0 END) AS nb_null,
            SUM(CASE WHEN [CMUP] = 0 THEN 1 ELSE 0 END) AS nb_zero,
            SUM(CASE WHEN [CMUP] > 0 THEN 1 ELSE 0 END) AS nb_positif,
            AVG(CASE WHEN [CMUP] > 0 THEN [CMUP] END) AS avg_positif
        FROM Lignes_des_ventes
        WHERE [Valorise CA] = 'Oui'""")
        r = c.fetchone()
        print(f"  Total lignes CA: {r[0]}")
        print(f"  NULL: {r[1]}, Zero: {r[2]}, Positif: {r[3]}")
        print(f"  Moyenne (positifs): {r[4]}")

        # 3. Tester le calcul marge
        print("\n--- Test calcul marge (TOP 5 par CA) ---")
        c.execute("""SELECT TOP 5
            [Code article], [Montant HT Net], [CMUP], [Quantité],
            ISNULL([CMUP], 0) * [Quantité] AS [Cout_Calc],
            [Montant HT Net] - ISNULL([CMUP], 0) * [Quantité] AS [Marge_Calc]
        FROM Lignes_des_ventes
        WHERE [Valorise CA] = 'Oui' AND [CMUP] > 0
        ORDER BY [Montant HT Net] DESC""")
        for r in c.fetchall():
            print(f"  Art={r[0]}, CA={r[1]:.2f}, PdR={r[2]:.2f}, Qte={r[3]:.2f}, Cout={r[4]:.2f}, Marge={r[5]:.2f}")

        # 4. Vérifier aussi dans Lignes_des_achats
        print("\n--- Colonnes prix/cout dans Lignes_des_achats ---")
        c.execute("""SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
                     WHERE TABLE_NAME = 'Lignes_des_achats'
                     AND (COLUMN_NAME LIKE '%prix%' OR COLUMN_NAME LIKE '%cout%' OR COLUMN_NAME LIKE '%revient%' OR COLUMN_NAME LIKE '%CMUP%')
                     ORDER BY COLUMN_NAME""")
        for col in c.fetchall():
            print(f"  {col[0]} ({col[1]})")

        # 5. Vérifier Lignes_des_achats CMUP
        print("\n--- Valeurs CMUP (achats) ---")
        try:
            c.execute("""SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN [CMUP] IS NULL THEN 1 ELSE 0 END) AS nb_null,
                SUM(CASE WHEN [CMUP] = 0 THEN 1 ELSE 0 END) AS nb_zero,
                SUM(CASE WHEN [CMUP] > 0 THEN 1 ELSE 0 END) AS nb_positif
            FROM Lignes_des_achats""")
            r = c.fetchone()
            print(f"  Total: {r[0]}, NULL: {r[1]}, Zero: {r[2]}, Positif: {r[3]}")
        except Exception as e:
            print(f"  Erreur: {str(e)[:100]}")

        conn.close()
    except Exception as e:
        print(f"  ERREUR connexion: {str(e)[:100]}")
