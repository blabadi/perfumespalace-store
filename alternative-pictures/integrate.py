# Phase 5: copy approved alt renders into images/2026/11/ and point products.json at them
import glob, json, os, shutil, re

ROOT = os.path.dirname(os.path.abspath('x'))
ROOT = os.getcwd()
AP = os.path.join(ROOT, 'alternative-pictures')
OUT = os.path.join(AP, 'output')
DEST_DIR = os.path.join(ROOT, 'images', '2026', '11')
os.makedirs(DEST_DIR, exist_ok=True)

products = json.load(open(os.path.join(ROOT, 'products.json'), encoding='utf-8'))
m = json.load(open(os.path.join(AP, 'inspired-map.json'), encoding='utf-8'))['entries']
by_id = {str(p['id']): p for p in products['products']}

# map id -> output file (id is the filename prefix)
outputs = {}
for f in glob.glob(os.path.join(OUT, '*-alt.jpg')):
    base = os.path.basename(f)
    mid = base.split('-')[0]
    outputs[mid] = base

swapped, missing = [], []
for pid, entry in m.items():
    if entry.get('status') == 'known' and entry.get('original') and pid in by_id:
        if pid not in outputs:
            missing.append(pid); continue
        base = outputs[pid]
        dest_rel = f"images/2026/11/{base}"
        dest_abs = os.path.join(ROOT, dest_rel.replace('/', os.sep))
        if not os.path.exists(dest_abs):
            shutil.copy2(os.path.join(OUT, base), dest_abs)
        p = by_id[pid]
        if dest_rel not in p['images']:
            p['images'] = [dest_rel] + p['images']
        swapped.append(pid)

json.dump(products, open(os.path.join(ROOT, 'products.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('swapped', len(swapped), 'products')
print('missing renders for known ids:', missing or 'none')
