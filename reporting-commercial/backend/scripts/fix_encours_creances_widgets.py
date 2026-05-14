# -*- coding: utf-8 -*-
"""
Fix : Reconfigure les widgets "Encours Clients" et "Creances Douteuses"
dans TOUS les dashboards pour utiliser DS_TB_SYNTHESE_RECOUVREMENT
au lieu de DS_KPI_RESUME (ou toute autre source incorrecte).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import get_db_cursor

# Mapping titre widget → config correcte
WIDGET_FIXES = {
    "encours clients": {
        "dataSourceCode": "DS_TB_SYNTHESE_RECOUVREMENT",
        "dataSourceOrigin": "template",
        "value_field": "Encours Total",
        "aggregation": "FIRST",
        "suffix": " DH",
        "kpi_color": "#dc2626",
    },
    "créances douteuses": {
        "dataSourceCode": "DS_TB_SYNTHESE_RECOUVREMENT",
        "dataSourceOrigin": "template",
        "value_field": "Creances Douteuses 120j",
        "aggregation": "FIRST",
        "suffix": " DH",
        "kpi_color": "#991b1b",
    },
    "creances douteuses": {
        "dataSourceCode": "DS_TB_SYNTHESE_RECOUVREMENT",
        "dataSourceOrigin": "template",
        "value_field": "Creances Douteuses 120j",
        "aggregation": "FIRST",
        "suffix": " DH",
        "kpi_color": "#991b1b",
    },
}

def fix_widgets():
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id, nom, code, widgets FROM APP_Dashboards WHERE actif=1 AND widgets IS NOT NULL AND widgets != '[]'")
        rows = cursor.fetchall()

    total_fixed = 0

    for row in rows:
        db_id, db_nom, db_code, widgets_json = row[0], row[1], row[2], row[3]
        try:
            widgets = json.loads(widgets_json)
        except Exception:
            continue

        changed = False
        for w in widgets:
            title_lower = (w.get("title") or "").strip().lower()
            fix = WIDGET_FIXES.get(title_lower)
            if not fix:
                continue

            cfg = w.setdefault("config", {})
            old_ds = cfg.get("dataSourceCode", "")

            # Ne rien faire si déjà correct
            if cfg.get("dataSourceCode") == fix["dataSourceCode"] and \
               cfg.get("value_field") == fix["value_field"]:
                print(f"  [OK] '{w['title']}' dans '{db_nom}' est deja correct")
                continue

            print(f"  [FIX] '{w['title']}' dans '{db_nom}' (id={db_id})")
            print(f"        {old_ds} -> {fix['dataSourceCode']}  value_field={fix['value_field']}")

            for key, val in fix.items():
                cfg[key] = val
            # Supprimer dataSourceId si présent (evite conflit avec code template)
            cfg.pop("dataSourceId", None)
            changed = True

        if changed:
            new_json = json.dumps(widgets, ensure_ascii=False)
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE APP_Dashboards SET widgets = ? WHERE id = ?",
                    (new_json, db_id)
                )
            total_fixed += 1
            print(f"  -> Dashboard '{db_nom}' mis a jour")

    print(f"\n=== Termine : {total_fixed} dashboard(s) mis a jour ===")


if __name__ == "__main__":
    print("=== Fix Encours Clients + Creances Douteuses ===\n")
    fix_widgets()
