import json

path = "alternative-pictures/inspired-map.json"
m = json.load(open(path, encoding="utf-8"))
E = m["entries"]

def set(id, original=None, brand=None, status=None, source=None, notes=None):
    e = E.setdefault(str(id), {"status": "unknown", "source": "none"})
    if original is not None: e["original"] = original
    if brand is not None: e["original_brand"] = brand
    if status is not None: e["status"] = status
    if source is not None: e["source"] = source
    if notes is not None: e["notes"] = notes

upd = [
    # --- French Avenue Vie line -> Bvlgari Le Gemme ---
    (2558, "Bvlgari Le Gemme Gyan", "Bvlgari", "probable", "web", "PickMyClone 78% dupe; 'Kashmir sapphire' notes match"),
    (2559, "Bvlgari Le Gemme Azaran", "Bvlgari", "probable", "web", "PickMyClone 72% dupe"),
    (2560, "Bvlgari Le Gemme Onekh", "Bvlgari", "probable", "web", "PickMyClone 72% dupe"),
    (2561, "Bvlgari Le Gemme Kobraa", "Bvlgari", "probable", "web", "PickMyClone/Perfumeo 78-85% dupe"),
    # --- Fragrance World ---
    (2563, "Nishane Shem", "Nishane", "probable", "web", "multiple sources 74-83%"),
    (2566, "YSL Tuxedo", "Yves Saint Laurent", "probable", "web", "90% match, multiple sources"),
    (2568, "Maison Margiela Replica Jazz Club", "Maison Margiela", "probable", "web", "notes (rum/vetiver/leather) match Jazz Club; one source said Music Festival"),
    (2570, "Parfums de Marly Althair", "Parfums de Marly", "probable", "web", "94% match consensus"),
    (3523, "Parfums de Marly Althair", "Parfums de Marly", "probable", "web", "Liquid Brun Limited Edition, same original"),
    (2573, "Parfums de Marly Layton", "Parfums de Marly", "probable", "web", "82% (2 sources); conflicting claim YSL L'Homme Ultime - confirm"),
    # --- Rue Broca ---
    (2584, "Parfums de Marly Greenley", "Parfums de Marly", "probable", "web", "87% match"),
    (2586, "Bvlgari Tygar", "Bvlgari", "probable", "web", "78%, two sources"),
    # --- others ---
    (3525, "Louis Vuitton Imagination", "Louis Vuitton", "probable", "web", "Arabiyat Marwa, 78%, multiple sources"),
    (2378, "Giorgio Armani My Way", "Giorgio Armani", "probable", "web", "9AM Pour Femme, 70% dupe of My Way"),
    (2581, "Gritti Duchessa", "Gritti", "probable", "web", "TikTok/community: dupe of Gritti Duchessa (black cherry)"),
    (2841, "Creed Aventus Absolu", "Creed", "probable", "web", "community: clone of Aventus Absolu"),
    (3224, "Xerjoff Erba Gold", "Xerjoff", "probable", "web", "Gold 999.9 -> Erba Gold (one source) vs Erba Pura (line) - confirm"),
    (3259, "Montale Arabians Tonka", "Montale", "probable", "web", "confirmed Dubai Night -> Montale Arabians Tonka"),
    (2799, "Dolce & Gabbana The One Luminous Night", "Dolce & Gabbana", "probable", "description", "desc garbled: 'ليل ساطع (لومينوس نايت) دولتشي غابانا ذا ون' - confirm with user"),
    (2962, "Parfums de Marly Perseus", "Parfums de Marly", "probable", "web", "desc said 'Perseus' = PdM Perseus, 78%"),
    (2961, "Lorenzo Pazzaglia Van Py Rhum", "Lorenzo Pazzaglia", "probable", "web", "desc 'Van by Ruhm' = Van Py Rhum, comparison video found"),
    (3037, "Stephane Humbert Lucas Sand Dance", "Stéphane Humbert Lucas", "probable", "description", "desc names 'ساند دانس من ستيفن لوكاس'"),
    (3042, "Guerlain L'Homme Idéal Platine Privé", "Guerlain", "probable", "web", "88% match, decodes 'لوم ايديال بلاتين'"),
    (3348, "Clive Christian Blonde Amber", "Clive Christian", "probable", "web", "76%, three sources; 'بلوند عمبر' = Blonde Amber"),
    (3452, "Room 1015 Wavechild", "Room 1015", "probable", "web", "93% match, 'ويڤ تشايلد' = Wavechild"),
    (3465, "Kilian Angels' Share On The Rocks", "Kilian", "probable", "web", "78%, multiple sources"),
    (3473, "Cartier Déclaration", "Cartier", "probable", "web", "two sources compare to Déclaration"),
    (3503, "YSL MYSLF", "Yves Saint Laurent", "probable", "web", "Aromatix Magnetiq -> YSL MYSLF community match"),
    (3508, "Kilian Smoking Hot", "Kilian", "probable", "web", "three sources"),
    (3545, "Memoirs of a Perfume Collector Tales from Zanzibar", "Memoirs of a Perfume Collector", "probable", "web", "medium confidence - confirm"),
    (3547, "Issey Miyake Le Sel d'Issey", "Issey Miyake", "probable", "web", "85% match"),
    (3564, "YSL Babycat", "Yves Saint Laurent", "probable", "web", "Nabatieh blends Oman Luxury Caden + YSL Babycat - primary? confirm"),
    (900003, "Kilian Angels' Share Paradis", "Kilian", "probable", "web", "86% match (updated from plain Angels' Share)"),
    (2555, "Fragrance One Office for Men", "Fragrance One", "probable", "web", "Ejaazi interpretation, medium confidence - confirm"),
]
for id, o, b, s, src, n in upd:
    set(id, o, b, s, src, n)

# remain unknown -> user list
still_unknown = {
    2381: "Afnan Supremacy Not Only Intense",
    2845: "Afnan 9PM Rebel (hints: بكرات? Black XS? Baccarat+Aventus blend?)",
    3500: "Afnan 9PM Night Out",
    2799: None,  # handled above as probable, but confirm
    3222: "AlHaramain Blue tester",
    2882: "Dumont Nitro White",
    2884: "Dumont Nitro Pour Homme",
    900002: "Dumont Nitro Red Intensely (melon/peach salty amber)",
    3251: "French Avenue Royal Blend Nero (conflict: Gissah Sava vs Kilian Angels' Share)",
    3460: "French Avenue Zenith Santal ('SWY sandalwood' - no such Armani release found)",
    3562: "French Avenue Grow (dates/saffron/davana, J-C Herault nose)",
    2870: "Sibrani Big Ben ('جريس شارنيل' unidentified)",
    3291: "Glow Woods",
    2589: "Paris Corner Identity Rose & Leather",
}
for id, note in still_unknown.items():
    if note and id != 2799:
        set(id, status="unknown", source="none", notes="web research failed - ASK USER: " + note)

json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

from collections import Counter
c = Counter(e["status"] for e in E.values())
print(dict(c))
