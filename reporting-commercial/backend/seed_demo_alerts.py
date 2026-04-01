"""Script d'injection d'historique demo pour les alertes KPI."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import random

from app.database_unified import set_tenant_context, write_client, execute_client

random.seed(42)

set_tenant_context(dwh_code='SG')

demo_entries = [
    (4,  97.3,    'critical', 'DSO critique : 97.3 j (seuil 90 j) - action immediate requise.',              0, 0),
    (4,  94.1,    'critical', 'DSO critique : 94.1 j (seuil 90 j) - action immediate requise.',              2, 0),
    (4,  91.8,    'critical', 'DSO critique : 91.8 j (seuil 90 j) - action immediate requise.',              5, 1),
    (5,  73.5,    'warning',  'DSO eleve : 73.5 j (seuil 60 j) - suivi recommande.',                        0, 0),
    (5,  68.2,    'warning',  'DSO eleve : 68.2 j (seuil 60 j) - suivi recommande.',                        3, 1),
    (6,  23.7,    'critical', 'Taux creances douteuses : 23.7% (seuil 20%) - revue immediate.',              1, 0),
    (7,  18.4,    'warning',  'Taux creances douteuses : 18.4% (seuil 15%) - surveillance accrue.',          0, 0),
    (7,  16.9,    'warning',  'Taux creances douteuses : 16.9% (seuil 15%) - surveillance accrue.',          4, 1),
    (8,  1247500, 'critical', 'Impayes critiques : 1 247 500 MAD (seuil 1 000 000 MAD) - relance urgente.', 0, 0),
    (8,  1089300, 'critical', 'Impayes critiques : 1 089 300 MAD (seuil 1 000 000 MAD) - relance urgente.', 3, 1),
    (9,  724800,  'warning',  'Impayes eleves : 724 800 MAD (seuil 500 000 MAD) - plan recouvrement.',       0, 0),
    (9,  612400,  'warning',  'Impayes eleves : 612 400 MAD (seuil 500 000 MAD) - plan recouvrement.',       6, 1),
    (10, 5843200, 'critical', 'Encours clients critique : 5 843 200 MAD (seuil 5 000 000 MAD).',            1, 0),
    (11, 4120000, 'warning',  'Encours clients eleve : 4 120 000 MAD (seuil 3 000 000 MAD).',               0, 0),
    (11, 3680000, 'warning',  'Encours clients eleve : 3 680 000 MAD (seuil 3 000 000 MAD).',               7, 1),
    (13, -14.3,   'warning',  'Evolution CA negative : -14.3% (seuil -10%) - analyse commerciale.',         2, 0),
    (15, 1.4,     'warning',  'Rotation des stocks faible : 1.4x (seuil 2x) - verifier les niveaux.',      1, 0),
    (15, 1.7,     'warning',  'Rotation des stocks faible : 1.7x (seuil 2x) - verifier les niveaux.',      8, 1),
]

# Clear existing demo history
write_client('DELETE FROM APP_KPI_AlertHistory WHERE rule_id BETWEEN 4 AND 15')
print('Cleared old demo history entries')

inserted = 0
for rule_id, metric_value, niveau, message, days_ago, is_ack in demo_entries:
    h = random.randint(8, 17)
    m = random.randint(0, 59)
    triggered_at = (datetime.now().replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
    if is_ack:
        ack_dt = (datetime.strptime(triggered_at, '%Y-%m-%d %H:%M:%S') + timedelta(hours=random.randint(1, 4))).strftime('%Y-%m-%d %H:%M:%S')
        write_client(
            'INSERT INTO APP_KPI_AlertHistory (rule_id, metric_value, niveau, message, triggered_at, is_acknowledged, acknowledged_by, acknowledged_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)',
            (rule_id, metric_value, niveau, message, triggered_at, 'admin', ack_dt)
        )
    else:
        write_client(
            'INSERT INTO APP_KPI_AlertHistory (rule_id, metric_value, niveau, message, triggered_at, is_acknowledged) VALUES (?, ?, ?, ?, ?, 0)',
            (rule_id, metric_value, niveau, message, triggered_at)
        )
    inserted += 1
    print(f'  [{rule_id}] {message[:65]}')

# Update last_triggered and last_checked for each rule
for rid in set(e[0] for e in demo_entries):
    write_client(
        '''UPDATE APP_KPI_AlertRules
           SET last_triggered = (SELECT TOP 1 triggered_at FROM APP_KPI_AlertHistory WHERE rule_id = ? ORDER BY triggered_at DESC),
               last_checked   = GETDATE()
           WHERE id = ?''',
        (rid, rid)
    )

rows = execute_client('SELECT COUNT(*) AS cnt FROM APP_KPI_AlertHistory WHERE rule_id BETWEEN 4 AND 15', use_cache=False)
unread = execute_client('SELECT COUNT(*) AS cnt FROM APP_KPI_AlertHistory WHERE rule_id BETWEEN 4 AND 15 AND is_acknowledged=0', use_cache=False)
print(f'\nDone: {rows[0]["cnt"]} total entries, {unread[0]["cnt"]} unread')
