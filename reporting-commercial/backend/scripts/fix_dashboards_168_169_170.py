# -*- coding: utf-8 -*-
"""
Corriger les widgets chart corrompus dans les dashboards 168, 169, 170.
Problemes:
  - widget.x = nom DS (string) au lieu d'un entier de position
  - widget.y = type chart ("bar") au lieu d'un entier de position
  - widget.w = 0 (zero width)
  - config.dataSourceCode = 6 (entier APP_DataSources) au lieu d'un code string Templates
  - type = "chart" (inexistant) au lieu de "chart_bar" / "chart_line"
"""
import sys, os, json, pyodbc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;'
    'UID=sa;PWD=SQL@2019;TrustServerCertificate=yes'
)
conn.autocommit = True
cur = conn.cursor()

# Configuration des corrections par dashboard
FIXES = {
    168: {
        'nom': 'TB Commercial',
        'charts': {
            'c1': {
                'type': 'chart_bar',
                'title': 'Evolution CA mensuel',
                'x': 0, 'y': 3, 'w': 6, 'h': 4,
                'config': {
                    'dataSourceCode': 'DS_COM_CA_PAR_PERIODE',
                    'dataSourceOrigin': 'template',
                    'x_field': 'Mois',
                    'y_field': 'CA',
                    'color': '#3b82f6',
                    'show_grid': True,
                    'limit_rows': 12,
                    'sort_field': 'Mois',
                    'sort_direction': 'asc'
                }
            },
            'c2': {
                'type': 'chart_bar',
                'title': 'Top 10 Clients',
                'x': 6, 'y': 3, 'w': 6, 'h': 4,
                'config': {
                    'dataSourceCode': 'DS_TOP_CLIENTS',
                    'dataSourceOrigin': 'template',
                    'x_field': 'Client',
                    'y_field': 'CA HT',
                    'color': '#10b981',
                    'horizontal': True,
                    'show_grid': True,
                    'limit_rows': 10,
                    'sort_field': 'CA HT',
                    'sort_direction': 'desc'
                }
            }
        }
    },
    169: {
        'nom': 'TB Responsable Commercial',
        'charts': {
            'c1': {
                'type': 'chart_bar',
                'title': 'CA par Representant',
                'x': 0, 'y': 3, 'w': 6, 'h': 4,
                'config': {
                    'dataSourceCode': 'DS_CA_AGREGE_REPRESENTANT',
                    'dataSourceOrigin': 'template',
                    'x_field': 'CA',
                    'y_field': 'CA',
                    'color': '#8b5cf6',
                    'horizontal': True,
                    'show_grid': True,
                    'limit_rows': 10,
                    'sort_field': 'CA',
                    'sort_direction': 'desc'
                }
            },
            'c2': {
                'type': 'chart_line',
                'title': 'Evolution CA mensuel',
                'x': 6, 'y': 3, 'w': 6, 'h': 4,
                'config': {
                    'dataSourceCode': 'DS_COM_CA_PAR_PERIODE',
                    'dataSourceOrigin': 'template',
                    'x_field': 'Mois',
                    'y_field': 'CA',
                    'color': '#3b82f6',
                    'show_grid': True,
                    'limit_rows': 12,
                    'sort_field': 'Mois',
                    'sort_direction': 'asc'
                }
            }
        }
    },
    170: {
        'nom': 'TB Direction Generale',
        'charts': {
            'c1': {
                'type': 'chart_bar',
                'title': 'Evolution CA mensuel',
                'x': 0, 'y': 3, 'w': 6, 'h': 4,
                'config': {
                    'dataSourceCode': 'DS_COM_CA_PAR_PERIODE',
                    'dataSourceOrigin': 'template',
                    'x_field': 'Mois',
                    'y_field': 'CA',
                    'color': '#3b82f6',
                    'show_grid': True,
                    'limit_rows': 12,
                    'sort_field': 'Mois',
                    'sort_direction': 'asc'
                }
            },
            'c2': {
                'type': 'chart_bar',
                'title': 'Balance Agee',
                'x': 6, 'y': 3, 'w': 6, 'h': 4,
                'config': {
                    'dataSourceCode': 'DS_REC_BALANCE_AGEE',
                    'dataSourceOrigin': 'template',
                    'x_field': 'Client',
                    'y_field': 'Solde Total',
                    'color': '#ef4444',
                    'horizontal': True,
                    'show_grid': True,
                    'limit_rows': 10,
                    'sort_field': 'Solde Total',
                    'sort_direction': 'desc'
                }
            }
        }
    }
}

for db_id, fix in FIXES.items():
    cur.execute(f"SELECT widgets FROM APP_Dashboards WHERE id={db_id}")
    row = cur.fetchone()
    if not row:
        print(f"[{db_id}] INTROUVABLE"); continue

    ws = json.loads(row[0] or '[]')
    changed = 0
    for w in ws:
        wid = w.get('id')
        if wid in fix['charts']:
            patch = fix['charts'][wid]
            w['type']   = patch['type']
            w['title']  = patch['title']
            w['x']      = patch['x']
            w['y']      = patch['y']
            w['w']      = patch['w']
            w['h']      = patch['h']
            w['config'] = patch['config']
            changed += 1

    if changed:
        new_json = json.dumps(ws, ensure_ascii=False)
        cur.execute("UPDATE APP_Dashboards SET widgets=? WHERE id=?", (new_json, db_id))
        print(f"[{db_id}] {fix['nom']} -> {changed} widget(s) corriges")
    else:
        print(f"[{db_id}] {fix['nom']} -> rien a corriger")

print("\nVerification finale:")
for db_id in [168, 169, 170]:
    cur.execute(f"SELECT widgets FROM APP_Dashboards WHERE id={db_id}")
    ws = json.loads(cur.fetchone()[0])
    print(f"  DB {db_id}:")
    for w in ws:
        cfg = w.get('config', {}) or {}
        print(f"    [{w['id']}] type={w['type']:12} x={w['x']} y={w['y']} w={w['w']}  ds={str(cfg.get('dataSourceCode',''))!r}")

conn.close()
