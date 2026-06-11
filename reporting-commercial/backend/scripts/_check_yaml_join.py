"""Check what the YAML actually produces for Lignes des ventes JOIN F_FAMILLE."""
import yaml, re, os

yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'etl', 'config', 'sync_tables.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

for table in config.get('tables', []):
    if table.get('name') == 'Lignes des ventes':
        q = table['source']['query']
        q_norm = q.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        q_norm = re.sub(r'\s+', ' ', q_norm).strip()

        print("=== RAW F_FAMILLE lines ===")
        for line in q.split('\n'):
            if 'F_FAMILLE' in line:
                print(repr(line))

        print("\n=== NORMALIZED search ===")
        print(f"LEFT OUTER JOIN F_FAMILLE: {'LEFT OUTER JOIN F_FAMILLE' in q_norm}")
        print(f"INNER JOIN F_FAMILLE: {'INNER JOIN F_FAMILLE' in q_norm}")

        # Show the JOIN context
        idx = q_norm.find('F_FAMILLE')
        if idx >= 0:
            print(f"\nContext around F_FAMILLE: ...{q_norm[max(0,idx-40):idx+60]}...")
        break
