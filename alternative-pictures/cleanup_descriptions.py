# Remove duplicate inspired-by mentions from badged product descriptions,
# keeping the single "مشابه ل : <original>" sentence.
import json, re

d = json.load(open('products.json', encoding='utf-8'))
m = json.load(open('alternative-pictures/inspired-map.json', encoding='utf-8'))['entries']
by_id = {str(p['id']): p for p in d['products']}

# Arabic clone-mention markers; consume until a size/structure word or punctuation/newline
PHRASE = re.compile(
    r'(?:بديل|محاكي لعطر|محاكي|مستوحى من|مستوحى|شبيه)'
    r'[^\n]*?'
    r'(?=\s*(?:حجم|تركيز|مل\b|إصدار|،|,|\.|\n|–|—|$))'
)
EN = re.compile(r'(inspired by|alternative)[^\n]*', re.I)

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

changed = []
for pid, entry in m.items():
    if entry.get('status') != 'known' or not entry.get('original') or pid not in by_id:
        continue
    p = by_id[pid]
    orig = entry['original']
    sent = 'مشابه ل : ' + orig
    desc = p['description'] or ''
    rest = desc.replace(sent, '')
    before = norm(rest)

    rest = PHRASE.sub(' ', rest)
    rest = EN.sub(' ', rest)

    # drop lines that merely repeat the original name (English or mixed)
    orig_words = [w.lower() for w in re.split(r'[^A-Za-z0-9]+', orig) if w]
    lines = []
    for line in rest.split('\n'):
        lw = line.lower()
        hits = sum(1 for w in orig_words if w in lw)
        if orig_words and hits >= max(1, len(orig_words) - 1) and len(orig_words) >= 2:
            continue
        lines.append(line)
    rest = '\n'.join(lines)

    rest = norm(rest.replace('\n', ' '))
    rest = rest.strip(' -–—،,.')

    p['description'] = (rest + ' ' + sent).strip()
    if p['description'] != norm(desc):
        changed.append((pid, norm(desc)[:100], p['description'][:140]))

json.dump(d, open('products.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('changed', len(changed))
for pid, b, a in changed:
    print(pid, '|', b, '=>', a)
