# -*- coding: utf-8 -*-
import pyodbc

DWH_KA = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_KA;UID=sa;PWD=SQL@2019'
DWH_GO = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=kasoft.selfip.net;DATABASE=DWH_GO;UID=sa;PWD=SQL@2019'

for db_name, conn_str in [('DWH_KA', DWH_KA), ('DWH_GO', DWH_GO)]:
    print(f"\n{'='*50}")
    print(f"=== {db_name} ===")
    try:
        conn = pyodbc.connect(conn_str, timeout=15)
        c = conn.cursor()

        # Vérifier tables
        for tbl in ['Lignes_des_ventes', 'Etat_Stock', 'Echéances_Ventes', 'Échéances_Ventes']:
            try:
                c.execute(f"SELECT TOP 1 1 FROM [{tbl}]")
                c.fetchone()
                print(f"  [{tbl}]: EXISTS")
            except Exception as e:
                print(f"  [{tbl}]: MISSING - {str(e)[:60]}")

        # Test query complète
        print("\n--- Query complète ---")
        try:
            c.execute("""
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
                (SELECT CASE WHEN ISNULL(SUM([Montant HT Net]), 0) > 0
                    THEN ROUND(SUM([Montant HT Net] - ISNULL([CMUP], 0) * [Quantité]) * 100.0 / SUM([Montant HT Net]), 2)
                    ELSE 0 END
                 FROM [Lignes_des_ventes]
                 WHERE [Valorise CA] = 'Oui'
                   AND [Date BL] BETWEEN @dateDebut AND @dateFin
                   AND (@societe IS NULL OR [societe] = @societe)) AS TauxMarge,
                (SELECT COUNT(DISTINCT [Code article])
                 FROM [Lignes_des_ventes]
                 WHERE [Valorise CA] = 'Oui'
                   AND [Date BL] BETWEEN @dateDebut AND @dateFin
                   AND (@societe IS NULL OR [societe] = @societe)) AS NbArticlesVendus,
                (SELECT ISNULL(SUM([Valeur du stock (montant)]), 0)
                 FROM [Etat_Stock]
                 WHERE (@societe IS NULL OR [societe] = @societe)) AS ValeurStock,
                (SELECT ISNULL(SUM([Montant échéance] - ISNULL([Montant du règlement], 0)), 0)
                 FROM [Échéances_Ventes]
                 WHERE [Montant échéance] > ISNULL([Montant du règlement], 0)
                   AND (@societe IS NULL OR [societe] = @societe)) AS Encours,
                (SELECT COUNT(DISTINCT [Code client])
                 FROM [Lignes_des_ventes]
                 WHERE [Valorise CA] = 'Oui'
                   AND [Date BL] BETWEEN @dateDebut AND @dateFin
                   AND (@societe IS NULL OR [societe] = @societe)) AS NbClientsActifs
            """)
            r = c.fetchone()
            if r:
                print(f"  CA={r[0]}, Marge={r[1]}, TauxMarge={r[2]}, NbArticles={r[3]}, ValeurStock={r[4]}, Encours={r[5]}, NbClients={r[6]}")
            else:
                print("  NO RESULT")
        except Exception as e:
            print(f"  ERREUR: {e}")

        conn.close()
    except Exception as e:
        print(f"ERREUR connexion: {e}")
