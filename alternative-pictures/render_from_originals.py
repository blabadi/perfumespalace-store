# Re-render all badged products from their ORIGINAL (pre-integration) photos.
# Original image paths come from main's products.json (git show main:products.json).
import glob, json, os, re, shutil, subprocess, unicodedata
from PIL import Image
import compose as C

raw = subprocess.run(['git', 'show', 'main:products.json'], capture_output=True)
old = json.loads(raw.stdout.decode('utf-8'))
old_by_id = {str(p['id']): p for p in old['products']}
overrides = json.load(open('alternative-pictures/source-overrides.json', encoding='utf-8')) \
    if os.path.exists('alternative-pictures/source-overrides.json') else {}

m = json.load(open('alternative-pictures/inspired-map.json', encoding='utf-8'))['entries']
by_id = {str(p['id']): p for p in json.load(open('products.json', encoding='utf-8'))['products']}

outputs = {}
for f in glob.glob(os.path.join(C.OUT, '*-alt.jpg')):
    outputs[os.path.basename(f).split('-')[0]] = os.path.basename(f)

done, failed = 0, []
for pid, entry in m.items():
    if entry.get('status') != 'known' or not entry.get('original') or pid not in by_id:
        continue
    p = by_id[pid]
    o = old_by_id.get(pid)
    if not o or not o['images']:
        failed.append((pid, 'no original image path')); continue
    names = [s.strip() for s in entry['original'].split('+')]
    bps = [b for b in (C.find_original([nm]) for nm in names) if b]
    if not bps:
        failed.append((pid, 'no badge images')); continue
    src_rel = overrides.get(pid) or o['images'][0]
    src = os.path.join(C.ROOT, src_rel.replace('/', os.sep))
    out_rel = outputs.get(pid) or (f"{pid}-{C.slug(p['name'][:24])}-alt.jpg")
    try:
        C.compose(src, bps, os.path.join(C.OUT, out_rel))
        shutil.copy2(os.path.join(C.OUT, out_rel), os.path.join(C.ROOT, 'images', '2026', '11', out_rel))
        done += 1
    except Exception as ex:
        failed.append((pid, repr(ex)))

print('rendered', done)
for f in failed:
    print('FAILED', f)
