import json, re
d = json.load(open('products.json', encoding='utf-8'))
n = 0
for p in d['products']:
    desc = p['description'] or ''
    new = re.sub(r'\s*،\s*\.\s*', ' ', desc)
    new = re.sub(r'\s+([–—])\s+\1+\s*', r' \1 ', new)
    new = re.sub(r'\s{2,}', ' ', new).strip()
    if new != desc:
        p['description'] = new
        n += 1
json.dump(d, open('products.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('polished', n)
for p in d['products']:
    if str(p['id']) in ('900001', '2955'):
        print(p['id'], p['description'][:130])
