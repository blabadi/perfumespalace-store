# Append "مشابه ل : <original>" to each badged product description
import json

d = json.load(open('products.json', encoding='utf-8'))
m = json.load(open('alternative-pictures/inspired-map.json', encoding='utf-8'))['entries']
by_id = {str(p['id']): p for p in d['products']}

n = 0
for pid, entry in m.items():
    if entry.get('status') == 'known' and entry.get('original') and pid in by_id:
        p = by_id[pid]
        sent = 'مشابه ل : ' + entry['original']
        desc = p['description'] or ''
        if 'مشابه ل' in desc:
            continue
        if desc and not desc.endswith(' '):
            desc += ' '
        p['description'] = (desc + sent).strip()
        n += 1

json.dump(d, open('products.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('updated', n, 'descriptions')
