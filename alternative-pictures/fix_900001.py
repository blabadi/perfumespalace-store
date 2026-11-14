import json
d = json.load(open('products.json', encoding='utf-8'))
for p in d['products']:
    if str(p['id']) == '900001' and 'للجنسين المقدمة' in (p['description'] or ''):
        p['description'] = p['description'].replace('للجنسين المقدمة', 'للجنسين. المقدمة')
        print('fixed 900001')
json.dump(d, open('products.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
