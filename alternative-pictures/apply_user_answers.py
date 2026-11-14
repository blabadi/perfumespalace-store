# Apply user's answers to the 15 unknowns in inspired-map.json (Nov 14 2026)
import json

path = "alternative-pictures/inspired-map.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

e = data["entries"]

def set_orig(pid, original, brand, notes):
    e[pid] = {
        "original": original,
        "original_brand": brand,
        "status": "known",
        "source": "user",
        "notes": notes,
    }

def set_skip(pid, name):
    e[pid] = {
        "status": "skip",
        "source": "user",
        "notes": f"{name} - user answered N/A, no badge",
    }

# 1. 2381 Afnan Supremacy Not Only Intense -> Creed Aventus
set_orig("2381", "Creed Aventus", "Creed", "user answered")
# 2. 2845 Afnan 9PM Rebel -> Baccarat Rouge (+ dup 3511)
set_orig("2845", "MFK Baccarat Rouge 540", "MFK", "user answered")
set_orig("3511", "MFK Baccarat Rouge 540", "MFK", "user answered (dup of 2845)")
# 3. 3500 9PM Night Out -> N/A
set_skip("3500", "Afnan 9PM Night Out")
# 4. 3222 AlHaramain Blue tester -> Bleu de Chanel EDP
set_orig("3222", "Chanel Bleu de Chanel", "Chanel", "user: EDP")
# 5. 2882 Dumont Nitro White -> Invictus + SWY Intensely (two originals)
set_orig("2882", "Paco Rabanne Invictus + Giorgio Armani Stronger With You Intensely",
         "Paco Rabanne / Giorgio Armani", "user gave two originals - badge design question pending")
# 6. 2884 Dumont Nitro Pour Homme -> user left blank, no badge for now
e["2884"] = {"status": "skip", "source": "user", "notes": "user left blank - no badge unless they say otherwise"}
# 7. 900002 Nitro Red Intensely -> Invictus confirmed
set_orig("900002", "Paco Rabanne Invictus", "Paco Rabanne", "user confirmed same as Nitro Red")
# 8. 3251 Royal Blend Nero -> N/A
set_skip("3251", "French Avenue Royal Blend Nero")
# 9. 3460 Zenith Santal -> SWY green bottle = Intensely
set_orig("3460", "Giorgio Armani Stronger With You Intensely", "Giorgio Armani", "user: correct, 'the green bottle' = SWY Intensely")
# 10. 3562 Grow -> N/A
set_skip("3562", "French Avenue Grow")
# 11. 2870 Big Ben -> BDK Gris Charnel
set_orig("2870", "BDK Gris Charnel", "BDK Parfums", "user identified 'جريس شارنيل' = Gris Charnel")
# 12. 3291 Glow Woods -> Tom Ford Tuscan Leather
set_orig("3291", "Tom Ford Tuscan Leather", "Tom Ford", "user answered")
# 13. 2589 Identity Rose & Leather -> Frederic Malle Rose & Cuir
set_orig("2589", "Frederic Malle Rose & Cuir", "Editions de Parfums Frédéric Malle", "user answered ('Fredric Mal, Rose & Cur')")
# 14. 2799 Lumière Homme Azraq -> D&G The One Luminous Night confirmed
set_orig("2799", "Dolce & Gabbana The One Luminous Night", "Dolce & Gabbana", "user confirmed")
# 15. 3564 Nabatieh -> N/A
set_skip("3564", "French Avenue Nabatieh")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# summary
from collections import Counter
c = Counter(v.get("status") for v in e.values())
print(c)
