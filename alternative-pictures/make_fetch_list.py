import json, re, unicodedata, os, math
data = json.load(open('alternative-pictures/inspired-map.json', encoding='utf-8'))
origs = sorted(set(v['original'] for v in data['entries'].values() if v.get('status') == 'known' and v.get('original')))

def canon(o):
    o = o.replace('Maison Francis Kurkdjian Baccarat Rouge 540', 'MFK Baccarat Rouge 540')
    o = o.replace('YSL Myself', 'YSL MYSLF')
    o = o.replace('Paco Rabanne Invictus + Giorgio Armani Stronger With You Intensely', '__COMBO__')
    return o

seen = {}
for o in origs:
    c = canon(o)
    if c == '__COMBO__' or c in seen:
        continue
    seen[c] = o
origs = sorted(seen.values())

def slug(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s

lines = [f'{slug(o)}|{o}' for o in origs]
open('alternative-pictures/originals/_fetch-list.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print(len(lines))
per = math.ceil(len(lines) / 4)
for i in range(4):
    print(f'--- chunk {i+1} ---')
    print('\n'.join(lines[i * per:(i + 1) * per]))
