# Rasterize logo.svg (simple gold shapes) to a transparent PNG with Pillow
from PIL import Image, ImageDraw

def bezier(p0, p1, p2, p3, n=60):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
        y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts

S = 4  # supersample
W, H = 512 * S, 336 * S
img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
GOLD = (207, 165, 36, 255)  # #cfa524
sc = lambda v: v * S

# circles
for cx, cy, r in [(256, 44, 30), (76, 86, 30), (436, 86, 30)]:
    d.ellipse([sc(cx-r), sc(cy-r), sc(cx+r), sc(cy+r)], fill=GOLD)

# crown path (from logo.svg, converted to absolute)
pts = bezier((98, 232), (92, 196), (84, 150), (76, 112))
pts += bezier((76, 112), (118, 215), (214, 215), (256, 74))[1:]
pts += bezier((256, 74), (298, 215), (394, 215), (436, 112))[1:]
pts += bezier((436, 112), (428, 150), (420, 196), (414, 232))[1:]
d.polygon([(sc(x), sc(y)) for x, y in pts], fill=GOLD)

# rounded bar
d.rounded_rectangle([sc(104), sc(262), sc(408), sc(316)], radius=sc(12), fill=GOLD)

img = img.resize((512, 336), Image.LANCZOS)
img.save('alternative-pictures/assets/logo.png')
print('saved', img.size)
