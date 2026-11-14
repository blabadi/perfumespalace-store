# Keep both Arabic and English inspired-by mentions in badged descriptions.
# Restore the pre-cleanup description content (from git commit 100813e) and
# re-append the single English "مشابه ل : <original>" sentence.
import json, re

OLD = r'C:\Users\boodi\AppData\Local\Temp\opencode\products-precleanup.json'
old = json.load(open(OLD, encoding='utf-8'))
old_by_id = {str(p['id']): p for p in old['products']}

d = json.load(open('products.json', encoding='utf-8'))
m = json.load(open('alternative-pictures/inspired-map.json', encoding='utf-8'))['entries']
by_id = {str(p['id']): p for p in d['products']}

AR_MENTION = re.compile(r'(?:بديل|محاكي|مستوحى|شبيه)')

restored, no_arabic = 0, []
for pid, entry in m.items():
    if entry.get('status') != 'known' or not entry.get('original') or pid not in by_id:
        continue
    p = by_id[pid]
    orig = entry['original']
    sent = 'مشابه ل : ' + orig
    o = old_by_id.get(pid)
    if not o:
        continue
    content = (o['description'] or '').replace(sent, '').strip()
    # re-apply the light polish (no double dashes / dangling commas)
    content = re.sub(r'\s+([–—])\s+\1+\s*', r' \1 ', content)
    content = re.sub(r'\s*،\s*\.\s*', ' ', content)
    content = re.sub(r'\s{2,}', ' ', content).strip(' -–—')
    p['description'] = (content + ' ' + sent).strip()
    restored += 1
    if not AR_MENTION.search(content):
        no_arabic.append((pid, p['name'][:40]))

json.dump(d, open('products.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('restored', restored, 'descriptions (Arabic + English)')
print('no Arabic mention in original text:')
for pid, name in no_arabic:
    print(' ', pid, name)
