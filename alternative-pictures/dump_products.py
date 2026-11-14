import json, os
os.makedirs("alternative-pictures", exist_ok=True)
data = json.load(open("products.json", encoding="utf-8"))
products = data["products"] if isinstance(data, dict) else data
lines = []
for p in sorted(products, key=lambda x: (x.get("brand", ""), x["id"])):
    desc = (p.get("description") or "").replace("\n", " ").strip()
    lines.append(f"{p['id']}\t{p.get('brand','')}\t{p['name']}\t{desc[:130]}")
open("alternative-pictures/list.txt", "w", encoding="utf-8").write("\n".join(lines))
print(len(lines))
