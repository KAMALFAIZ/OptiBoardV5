import requests
r = requests.get("http://localhost:8080/api/menus/user/1")
d = r.json()
stocks = [x for x in d['data'] if x['code']=='stocks'][0]
for sub in stocks['children']:
    print(f"  {sub['nom']}:")
    for item in sub['children']:
        print(f"    {item['nom']:30s} target_id={item['target_id']:3d} target_name={item.get('target_name','?')}")
