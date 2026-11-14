# QA: verify every rendered output opens, then build review contact sheets
import glob, os
from PIL import Image

OUT = 'alternative-pictures/output'
files = sorted(glob.glob(os.path.join(OUT, '*-alt.jpg')))
bad = []
imgs = []
for f in files:
    try:
        im = Image.open(f); im.verify()
        im = Image.open(f).convert('RGB')
        imgs.append((os.path.basename(f), im))
    except Exception as ex:
        bad.append((os.path.basename(f), repr(ex)))
print(len(files), 'files,', len(imgs), 'ok,', len(bad), 'bad')
for b in bad: print('BAD', b)

# contact sheets: 6 cols x 5 rows per sheet, thumb 300px
import math
TH = 300
COLS, ROWS = 6, 5
per = COLS * ROWS
sheets = math.ceil(len(imgs) / per)
for s in range(sheets):
    chunk = imgs[s*per:(s+1)*per]
    W, H = COLS*TH, ROWS*TH
    sheet = Image.new('RGB', (W, H), (240, 240, 240))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(chunk):
        im = im.copy(); im.thumbnail((TH, TH))
        x, y = (i % COLS)*TH, (i // COLS)*TH
        sheet.paste(im, (x + (TH-im.width)//2, y + (TH-im.height)//2))
        d.text((x+6, y+4), name.split('-')[0], fill=(200,0,0))
    sheet.save(os.path.join(OUT, f'_review-sheet-{s+1}.jpg'), quality=85)
    print('sheet', s+1, sheet.size, len(chunk), 'images')
