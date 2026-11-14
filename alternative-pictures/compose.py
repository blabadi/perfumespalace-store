# Alternative Pictures — compositing recipe
# Renders product image(s) with "inspired by" badge bottle(s) in the top-left.
# Reads only from alternative-pictures/ and the catalog images/; writes ONLY to alternative-pictures/output/.
import json, os, re, sys, unicodedata
from PIL import Image, ImageDraw, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AP = os.path.join(ROOT, 'alternative-pictures')
ORIG = os.path.join(AP, 'originals')
OUT = os.path.join(AP, 'output')
os.makedirs(OUT, exist_ok=True)

# ---- recipe knobs (change these after user review) ----
BADGE_RATIO = 0.20      # badge box size as fraction of canvas edge
CORNER = 'top-left'
MARGIN = 0.03           # badge margin from edges, fraction of canvas edge
BACKING = True
BACKING_COLOR = (255, 255, 255, 230)
BACKING_RADIUS_FRAC = 0.03   # rounded-corner radius, fraction of badge size
BADGE_PADDING = 0.10    # padding inside backing box, fraction of badge size
WATERMARK_RATIO = 0.19  # watermark width as fraction of canvas edge
WATERMARK_OPACITY = 0.85
WATERMARK_MARGIN = 0.03 # fraction of canvas edge
LOGO_PATH = os.path.join(AP, 'assets', 'logo-full.png')
PAD_TO_SQUARE = True    # white-pad non-square product photos to a square
MAX_SIDE = 1600         # cap longest side before compositing (file size)
# ------------------------------------------------------

def slug(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s

def find_original(names):
    aliases = {
        'Maison Francis Kurkdjian Baccarat Rouge 540': 'MFK Baccarat Rouge 540',
        'YSL Myself': 'YSL MYSLF',
        'Jean Paul Gaultier Le Male Elixir Absolu': 'Le Male Elixir Absolu',
        'Giorgio Armani Stronger With You Sandalwood': 'Giorgio Armani Stronger With You Intensely',
    }
    for n in names:
        n = aliases.get(n, n)
        p = os.path.join(ORIG, slug(n) + '.jpg')
        if os.path.exists(p):
            return p
        p = os.path.join(ORIG, slug(n) + '.png')
        if os.path.exists(p):
            return p
    return None

def compose(product_path, badge_paths, out_path, size=None):
    img = Image.open(product_path).convert('RGB')
    img = ImageOps.exif_transpose(img)
    if PAD_TO_SQUARE:
        w, h = img.size
        side = max(w, h)
        sq = Image.new('RGB', (side, side), (255, 255, 255))
        sq.paste(img, ((side - w) // 2, (side - h) // 2))
        img = sq
    if size:
        img = img.resize((size, size), Image.LANCZOS)
    elif max(img.size) > MAX_SIDE:
        f = MAX_SIDE / max(img.size)
        img = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
    W, H = img.size
    edge = min(W, H)
    box = int(edge * BADGE_RATIO)
    n = len(badge_paths)
    # badges laid out in a row starting at the corner
    pad = int(box * BADGE_PADDING)
    cell = box + 2 * pad
    mx = int(edge * MARGIN)
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i, bp in enumerate(badge_paths):
        badge = Image.open(bp).convert('RGBA')
        badge = ImageOps.contain(badge, (box, box))
        # center badge in its cell
        bw, bh = badge.size
        x0 = mx + i * cell
        y0 = mx
        if CORNER == 'top-right':
            x0 = W - mx - (n - i) * cell
        # backing: rounded rect behind bottle
        if BACKING:
            r = int(cell * BACKING_RADIUS_FRAC)
            d.rounded_rectangle([x0, y0, x0 + cell, y0 + cell], radius=r, fill=BACKING_COLOR)
        # contain badge into padded area
        avail = (box, box)
        badge = ImageOps.contain(badge, avail)
        bw, bh = badge.size
        bx = x0 + (cell - bw) // 2
        by = y0 + (cell - bh) // 2
        overlay.alpha_composite(badge, (bx, by))
    out = img.convert('RGBA')
    # watermark: Perfumes Palace logo, top-right
    wm = Image.open(LOGO_PATH).convert('RGBA')
    ww = int(edge * WATERMARK_RATIO)
    wm = ImageOps.contain(wm, (ww, int(ww * wm.height / wm.width)))
    if WATERMARK_OPACITY < 1:
        a = wm.getchannel('A')
        a = a.point(lambda v: int(v * WATERMARK_OPACITY))
        wm.putalpha(a)
    wmx = W - int(edge * WATERMARK_MARGIN) - wm.width
    wmy = int(edge * WATERMARK_MARGIN)
    out.alpha_composite(wm, (wmx, wmy))
    out.alpha_composite(overlay)
    out.convert('RGB').save(out_path, 'JPEG', quality=92)
    print('wrote', out_path)

def main():
    # no args = render every badged product; args = specific product ids
    products = json.load(open(os.path.join(ROOT, 'products.json'), encoding='utf-8'))['products']
    m = json.load(open(os.path.join(AP, 'inspired-map.json'), encoding='utf-8'))['entries']
    by_id = {str(p['id']): p for p in products}
    targets = sys.argv[1:]
    if not targets:
        targets = [pid for pid, entry in m.items()
                   if entry.get('status') == 'known' and entry.get('original') and pid in by_id]
    rendered, failed = [], []
    for tid in targets:
        p = by_id.get(tid)
        entry = m.get(tid, {})
        orig = entry.get('original')
        if not p or not orig:
            failed.append((tid, 'no product or original')); continue
        names = [s.strip() for s in orig.split('+')]
        bps = []
        for nm in names:
            bp = find_original([nm])
            if bp:
                bps.append(bp)
            else:
                failed.append((tid, f'missing badge image: {nm}'))
        if not bps:
            continue
        try:
            product_path = os.path.join(ROOT, p['images'][0])
            out_path = os.path.join(OUT, f'{tid}-{slug(p["name"][:24])}-alt.jpg')
            compose(product_path, bps, out_path)
            rendered.append(tid)
        except Exception as ex:
            failed.append((tid, repr(ex)))
    json.dump({r: os.path.basename(f'{r}-alt.jpg') for r in rendered},
              open(os.path.join(AP, 'output', '_render-index.json'), 'w'), indent=1)
    print(f'rendered {len(rendered)} / {len(targets)}')
    for tid, why in failed:
        print('FAILED', tid, why)

if __name__ == '__main__':
    main()
