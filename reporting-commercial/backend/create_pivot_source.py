"""Create a data source for pivot testing"""
import pyodbc
import json

# Connection settings
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=kasoft.selfip.net;"
    "DATABASE=GROUPE_ALBOUGHAZE;"
    "UID=sa;"
    "PWD=SQL@2019;"
    "TrustServerCertificate=yes;"
)

def create_pivot_source():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Create the data source
    query_template = """
    SELECT
        [Représentant] as Commercial,
        [Catalogue 1] as Gamme,
        DATENAME(MONTH, [Date BL]) + ' ' + CAST(YEAR([Date BL]) AS VARCHAR) as Mois,
        SUM([Montant HT Net]) as CA
    FROM [DashBoard_CA]
    WHERE [Représentant] IS NOT NULL
        AND [Date BL] IS NOT NULL
    GROUP BY
        [Représentant],
        [Catalogue 1],
        DATENAME(MONTH, [Date BL]) + ' ' + CAST(YEAR([Date BL]) AS VARCHAR)
    """

    cursor.execute(
        """INSERT INTO APP_DataSources (nom, type, description, query_template, parameters)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "Ventes Detail Pivot",
            "query",
            "Detail des ventes avec mois pour pivot",
            query_template,
            "{}"
        )
    )
    conn.commit()

    # Get the new ID
    cursor.execute("SELECT @@IDENTITY")
    new_id = cursor.fetchone()[0]
    print(f"Data source created with ID: {new_id}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_pivot_source()
