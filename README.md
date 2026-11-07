# قصر العطور — Arabic RTL product catalogue (Perfumes Palace)

A WooCommerce-style product catalogue in **Arabic and right-to-left**, built from a plain
JSON file that lives in this repo. `products.json` is the source of truth — nothing here
reads a store API, scrapes a site or downloads anything at build time. No build step, no
dependencies — open it in a browser.

```
index.html          page structure (lang="ar" dir="rtl")
styles.css          all styling (logical properties, light + dark theme, responsive)
app.js              loads products.json, builds facets, filters, sorts, renders, handles the cart
products.json       the catalogue data (189 products) — the source of truth, edit it here
images/             every product photo, self-hosted (see "The pictures")
brand_aliases.py    brands written two ways, folded onto the one to keep
visibility.py       the hide/show rule for products.json, shared by the page and the feed
set-visibility.py   command line to hide/show products without editing the JSON by hand
admin.py            local browser page for editing name, price and visibility  (run it, don't deploy it)
build-feed.py       writes feed.xml + feed.csv (the Meta/WhatsApp feed) and sets.json
webp_to_jpeg.py     JPEG twins of the WebP photos — Meta only accepts JPG/PNG
create-sets.py      pushes sets.json into a Meta catalogue as product sets
feed.xml, feed.csv  the generated feed, public at <domain>/feed.xml
sets.json           one Meta product set per brand, ready to push
products.demo.json  the original hand-written sample catalogue (kept as a backup)
serve.cmd           optional: starts a local server (Python) so fetch() is allowed
admin.cmd           optional: starts admin.py and opens the local editing page
```

## Run it

Browsers block `fetch()` on `file://` pages, so serve the folder:

```
python -m http.server 8000
```

then open <http://localhost:8000>. On Windows you can double-click `serve.cmd` instead.

To change product names, prices or visibility, use the local editing page instead — see
[Editing products in a browser](#editing-products-in-a-browser-local-admin-page).

## Where the data lives

`products.json` is the only data source: the page fetches it, `build-feed.py` reads it, and
`admin.py` / `set-visibility.py` edit it. Nothing in this project calls a store API, scrapes
a page or downloads anything at build time — the photos are already in `images/`.

To add a product:

1. put its photo under `images/` (e.g. `images/2026/11/bujairami-hectic.jpg`);
2. append a row to `products` in `products.json` — the shape is in
   [Editing the data by hand](#editing-the-data-by-hand);
3. run `python build-feed.py --sets` so `feed.xml`, `feed.csv` and `sets.json` include it;
4. commit the JSON, the photo and the three generated files.

`added` is plain data too — write the date you started selling the product. The `جديد` badge
compares each row against the newest `added` value in the catalogue (30-day window), so a
new row with today's date makes it the reference point.

## What the page does

- **Arabic + RTL.** `dir="rtl"`, filter sidebar on the right, mirrored price slider, badges
  and modal close button on the correct side, Arabic `Intl` money/date formatting
  (Cairo + Amiri fonts).
- **Animated hero.** The top band is a modern animated hero built from the data: drifting
  colour blobs and a light beam behind the headline, a staggered entrance, a light parallax that
  follows the pointer, a headline whose last word rotates (`نيش → ديزاينر → بدائل → تقسيمات` —
  the words are parsed out of `meta.tagline`, not hard-coded), animated stat counters (products,
  brands, sale count, lowest price), a continuous brand-name marquee (paused on hover), and a
  Ken-Burns image carousel with a caption card (brand, name, price, struck price), a `خصم N%`
  badge and dots. Each hero image is a button that opens that product's quick-view modal.
  Autoplay pauses on hover, when the hero scrolls out of view, or when the tab is hidden, and the
  whole thing collapses to a static layout under `prefers-reduced-motion`. Two hero buttons jump
  to the results: `تصفّح الكتالوج` and `منتجات عليها تخفيضات` (which applies the sale filter).
- **Facets built from the data.** Brand (العلامة التجارية — 49 values), Price, and the product
  attributes (`التصنيف`) are the groups shown. Every attribute key in the JSON becomes its own
  filter group automatically, then the titles listed in `HIDDEN_FACETS` in `app.js`
  (`الفئة`, `التوفر`, `الحجم`) are skipped — delete a name from that set to bring its group
  back. Season, day/night and scent direction are not here at all: they were removed from
  `products.json` and from `KEEP_ATTRS`, not just hidden. Keys with a single value across the
  catalogue are skipped too. Long groups (more than 12 values) get a **search box inside the
  group** and a **«عرض المزيد» button** that reveals the remaining values; groups far down the
  list render collapsed and expand on click.
- **Multi-value attributes.** An attribute may hold a list — one product is listed with two
  sizes: `"الحجم": ["105 مل", "علبة اصلية كاملة (100 مل)"]`.
  Each value becomes its own filter row, and a product matches if it carries any of the
  selected values. In the card and spec table the values are shown joined: `105 مل، علبة اصلية كاملة (100 مل)`.
- **Price filter** with a dual-handle slider plus typed min/max fields, derived from the
  lowest/highest priced product (40 – 1,500 ₪ here). Products with `price: null` are always
  kept and show `السعر عند الطلب`.
- **Availability** (عليها تخفيضات / متوفر في المخزون): its facet group is hidden, but both
  filters still work — the hero's `منتجات عليها تخفيضات` button turns the sale filter on, and
  the active chip removes it. The **rating** group and the star
  lines appear only when at least one product actually has reviews — this store has none, so
  they are hidden instead of showing empty 4.5★ rows.
- **Facet counts** update as you filter, and each group's count ignores its own selection —
  the same behaviour WooCommerce uses. Rows that would return nothing are dimmed.
- **Search** across name, brand, category, SKU, description, tags and attribute values, with
  Arabic normalisation: `مقلاه` matches `مقلاة`, `ادارة` matches `إدارة`
  (diacritics removed, أ/إ/آ → ا, ى → ي, ة → ه).
- **Sort**: مختارة، السعر ↑/↓، الأعلى تقييماً، الأحدث، الأسماء أبجدياً.
- **Grid / list** layouts, sale and stock badges, light/dark theme. The product **image is the
  button**: clicking it (or pressing Enter on it) opens the quick-view modal with image gallery,
  spec table, a link to the real product page and a WhatsApp order link. The same applies to the
  cart thumbnails, which open the modal above the drawer (`z-index` 68 vs 65).
- **Rotating thumbnails.** A product with more than one photo cycles through them inside the
  card: two stacked frames cross-fade, advancing one image every ~3.2 s (staggered card by card)
  and ~4× faster while the pointer or the keyboard focus is on that card. Only cards on screen are
  cycled, each image is downloaded just before it is shown, the quick-view modal pauses the
  rotation, and a hidden tab or `prefers-reduced-motion` stops it entirely. Tuning constants:
  `ROTATE_TICK`, `ROTATE_EVERY`, `ROTATE_MARGIN` in `app.js`.
- **Cart drawer.** `أضف` on a card (or in the quick-view modal) opens a side drawer listing
  every added product with its thumbnail, quantity stepper (`−` / `+`), line total and remove
  link; the footer shows piece count, savings from sale prices, how many lines are
  `السعر عند الطلب`, and the total. `إتمام الطلب عبر واتساب` builds a `wa.me` message with the
  full order summary and sends it to `meta.whatsapp`. The cart survives reloads
  (`localStorage` key `northline_cart`, `{ productId: qty }`), the cart badge shows the total
  number of pieces, add buttons read `في السلة (N)`, and out-of-stock products cannot be
  added. Esc or the backdrop closes the drawer.
- **Shareable URLs.** Every filter is written into the URL hash, e.g.
  `#brand=Creed&attr.التصنيف=نيش&sale=1&sort=price-desc&view=list`, so a filtered view can
  be bookmarked or linked (Arabic keys included).
- **Sticky filter bar.** The result count, sort/view controls and the chips of the filters you
  have selected are pinned under the top bar while you scroll (`#results-head`, `top: var(--stick)`,
  which `syncStickyOffset()` sets from the real top-bar height), so you can remove a filter or
  press `مسح الكل` without scrolling back up. Many chips wrap inside the bar and scroll locally
  (max 84 px) instead of pushing the products down. The filter sidebar is sticky too, and both
  its offset and the mobile filter panel follow `--stick`.
- **Random hero images.** The five hero products are drawn at random on every load (any
  in-stock priced product with an image, always five different brands, gallery photos preferred
  inside the randomness), and the carousel visits them in a shuffled order rather than 1→2→3→4→5.
  `خلط الصور` under the images redraws the band with a fresh random set.
- **Offline-safe images.** If an image fails to load, the card falls back to a generated SVG
  placeholder instead of a broken-image icon.

## The pictures

Every product photo lives in `images/` inside this repo, so the page has **no dependency on
any external site** (and no hotlink/CORS surprises). `products.json` stores relative paths
like `images/2026/09/yclzhj.jpg`.

- Layout: `images/<yyyy>/<mm>/<name>.<ext>` (the year/month is just where the photo was filed,
  it no longer drives anything) and `images/misc/` for undated ones. Any path under `images/`
  works — `images/2026/11/bujairami-hectic.jpg` was added by hand.
- `images/jpg/…` holds the JPEG twins of the 102 WebP photos, written by
  `python webp_to_jpeg.py`; that folder exists only because Meta does not accept WebP.
  The site itself loads the smaller WebP files.
- `images/manifest.json` maps the original external URL → local file for the photos that came
  from the old store import. It is provenance only — nothing reads it at runtime, and no script
  downloads images any more.
- 296 product images (~88 MB with the JPEG twins). Nothing here is generated at build time.
- To change a photo, drop the new file under `images/` and point the row's `images` array at it.

## Meta / WhatsApp product feed

The WhatsApp Business catalogue (and Facebook/Instagram shops) is Meta's own list of items — a
website cannot be pointed at it. What you can hand over is a **product feed**, generated from
`products.json`:

```
python webp_to_jpeg.py         # JPEG twins for the WebP images (Meta only accepts JPG/PNG)
python build-feed.py           # writes feed.xml + feed.csv
python build-feed.py --check   # same, then HEAD-check every image URL
```

Both files live in the repo root, so once pushed they are public:

- <https://catalog.perfumespalace.store/feed.xml> — RSS 2.0 with the `g:` namespace (recommended)
- <https://catalog.perfumespalace.store/feed.csv> — the same rows, same column names

`--base` overrides the URL prefix (it defaults to the domain in `CNAME`), e.g.
`python build-feed.py --base https://blabadi.github.io/perfumespalace-store/`.

### Connecting it to WhatsApp

1. **Commerce Manager** (<https://business.facebook.com/commerce>) → create a catalogue of type
   *E-commerce*, currency **ILS**.
2. In that catalogue: **Data sources → Scheduled feed** → paste the `feed.xml` URL → daily
   schedule.
3. Read **Diagnostics** after the first fetch: anything Meta rejects is listed with a reason, so
   you fix the data or the builder and re-run.
4. **WhatsApp Manager → your WhatsApp Business account → catalogue** → connect this catalogue to
   the number (Meta moves that toggle around; it sits with the account's business settings).
5. The items then show on the WhatsApp Business profile and are reachable at
   `https://wa.me/c/972566008917`, where a customer can build a cart and send it to you.

### What the feed contains

- One row per priced, visible catalogue row (**175** rows): `id` (the product id — the same value
  the WhatsApp Cloud API calls `retailer_id`), `title`, `description`, `availability`, `condition`,
  `price`, `sale_price` (153 rows), `link` (the catalogue home,
  `https://catalog.perfumespalace.store/`, so a tap opens the catalogue), `image_link` +
  `additional_image_link` (up to 10), `brand`, and `google_product_category` (drop it with
  `--no-gpc`).
- Prices carry the ISO code — `280.00 ILS`. `compare_at_price` becomes `sale_price`, with the
  higher price left in `price` so Meta can strike it through.
- **1 row is skipped**: products tagged «السعر عند الطلب» have no price, and Meta requires one
  (today that is Dior Homme Parfum).
- Sold-out rows stay in the feed as `out of stock` (`stock == 0` → `in stock` otherwise). There is
  no sold-out row in the current data, so every row today is `in stock`.
- WebP pictures point at a JPEG twin under `images/jpg/…` (102 files, ~14 MB) and everything else
  keeps its own file. The site itself still loads the smaller WebP files. One twin is 394×450 px
  while Meta recommends at least 500×500 — replace that product's photo if you want it perfect.
- After changing products.json, re-run both scripts and push, so the feed matches the catalogue
  (`python build-feed.py --sets` also refreshes the product sets below).

### Product sets by brand

A **product set** is Meta's own saved filter over the catalogue — Commerce Manager shows it as
*Brand is French Avenue*. It is not a copy of the items, so the set follows the feed: when a new
French Avenue product arrives with the next upload, it is inside the set already. Sets are what
Advantage+ catalog ads, shop collections and the Cloud API `product_set_id` arguments point at.

```
python build-feed.py --sets      # writes sets.json next to feed.xml
python create-sets.py            # plan only: what it would create/update, no API call
python create-sets.py --list     # what is already in the catalogue
python create-sets.py --apply    # write for real
```

`sets.json` holds one entry per brand: the rule (`{"brand": {"eq": "French Avenue"}}`), a stable
`retailer_id` (`set_french_avenue`) so the script recognises its own sets on the next run, the
item count, and metadata (cover image + a deep link back to
`https://catalog.perfumespalace.store/#brand=French+Avenue`).

Before it can write, give it two things — both are secrets, so keep them in the environment:

```
set META_CATALOG_ID=1234567890     # Commerce Manager -> Catalogue -> Settings -> Catalogue ID
set META_TOKEN=EAAG...             # system-user token with the catalog_management permission
```

The token comes from **Business Settings → Users → System users** → create one, add it as an admin
of the catalogue, *Generate token*, and grant `catalog_management`. Then:

```
python create-sets.py --only French --apply    # one brand first, to see it land in the UI
python create-sets.py --apply                  # then all of them
```

The run is idempotent: sets are matched by `retailer_id`, then by rule, then by name, so a second
run reports `already correct` instead of creating duplicates (Meta refuses a duplicate rule with
error 10803 anyway). A set you made by hand is never renamed or rewritten — if it already carries
the same rule the script skips it, and if it holds your name with a different rule you get a
`conflict` line to resolve. `--delete-stale` removes only *our* sets (`set_*`) that fell out of
`sets.json`; nothing else is touched.

Tuning the split:

- `--sets-min 3` keeps only brands with at least that many items; `--sets-min 1` takes every brand.
- `--sets-keep-unspecified` also makes a set out of «غير محدد», the "no brand" value
  (skipped by default).
- `--sets-prefix "Brand: "` renames them, e.g. so they sort together in Commerce Manager.
- `--sets-field product_type --sets-op i_contains` builds the rules on another feed column.
- `--sets-by ids` freezes the current items with `{"retailer_id": {"is_any": [...]}}` instead of a
  rule — only useful if you want a set that must *not* change.

Today that is **25 sets** out of 48 brand values: 22 brands have a single item (a one-item set is
noise in the UI) and «غير محدد» is skipped, so 144 of the 175 feed rows are covered (the other 9
have no brand). Two things worth knowing:

- `brand_aliases.py` folds two spellings of one house onto the spelling with more products
  (`Lattafa` → `لطافة Lattafa`), so one house means one facet on the site and one set in Meta.
  build-feed.py applies it, so the feed and the sets agree even if a row in products.json uses
  the other spelling; delete the entry once the catalogue uses one spelling.
- Arabic brand names are fine in set names and rules (Meta only forbids non-ASCII characters in
  *label* filters), so `لطافة Lattafa` and `العز للعود` get real rules.

## Deploying it

Live on **GitHub Pages**: <https://catalog.perfumespalace.store/> (custom domain, HTTPS enforced)
and <https://blabadi.github.io/perfumespalace-store/> (which redirects to it). Every push to
`main` redeploys automatically.

### Custom domain (`catalog.perfumespalace.store`)

Fully live and HTTPS-enforced: <https://catalog.perfumespalace.store/> (`http://` 301s to
`https://`, `https_enforced: true`). The custom domain is set in *Settings → Pages*, the repo
carries the `CNAME` file GitHub wrote, and the DNS record sits at Cloudflare:

| Type | Name | Target | Proxy |
| --- | --- | --- | --- |
| `CNAME` | `catalog` | `blabadi.github.io` | **DNS only** (grey cloud) |

⚠️ The `@` and `www` records **must not be touched** — `perfumespalace.store` itself points at
the Cloudflare-proxied WooCommerce store; sending the apex to GitHub Pages would take the store
offline. For an apex domain you would need `A` records to `185.199.108.153`, `185.199.109.153`,
`185.199.110.153`, `185.199.111.153` and `AAAA` records to `2606:50c0:8000::153`,
`2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`, all DNS-only.

**Troubleshooting: HTTPS stays on GitHub's `*.github.io` certificate** (the browser warns
"wrong principal"/name mismatch) because the certificate was never issued. Saving the custom
domain again — or clearing it and re-adding it — starts a fresh provisioning cycle; the
certificate then shows as `approved` in `GET /repos/{owner}/{repo}/pages` (`https_certificate`)
within minutes, after which **Enforce HTTPS** can be switched on. Keep the record DNS-only the
whole time: proxying it through Cloudflare stops GitHub from issuing its certificate.

### Other hosts

The site is plain static files — host the whole folder anywhere:

- **GitHub Pages** (free): repo → *Settings → Pages → Deploy from a branch → `main` / `/ (root)`.
  Note that **Pages on a private repo needs a paid plan** (Pro/Team); on GitHub Free the repo
  must be public. Pages allows 1 GB per site and 100 GB/month of traffic — this site is ~74 MB.
- **Cloudflare Pages / Netlify** (free): connect the repo or drag-and-drop the folder. Works with
  a private repo and has no bandwidth limit; good choice if the code must stay private.
- On the store's own hosting: copy the folder into `public_html/<subfolder>/`.

The only external request left is Google Fonts (Cairo + Amiri). To go 100% self-contained,
download the two font families into `fonts/` and add `@font-face` rules to `styles.css`.

## Editing products in a browser (local admin page)

`admin.py` is a page for the three things that change most often — a product's **name**, its
**price**, and whether it is **shown**. It runs on your own computer only.

```
python admin.py          # starts it and opens http://127.0.0.1:8123
```

or double-click `admin.cmd`. Close the window (or press Ctrl+C) when you are done.
`--port 8124` and `--no-browser` are there if you want them.

The page is in Arabic: search by name / model / product number, filter by brand, and the
dropdown offers **الظاهرة فقط**, **المخفية فقط**, **التي نفدت كميتها** and **بلا سعر**.
Each row shows the photo, an editable name, an editable price, the stock state, and a
**ظاهرة** tick box. Leave the price empty for **السعر عند الطلب**.

Every **حفظ** does three things:

1. copies `products.json` to `products.json.bak` (the file as it was before that save);
2. writes the row back in the file's own shape — indent=2, Arabic unescaped, CRLF — so
   `git diff` stays two lines instead of five thousand;
3. runs `build-feed.py --sets`, so `feed.xml`, `feed.csv` and `sets.json` always match the
   data — Meta can never be left holding an old price or a product you hid.

Nothing reaches the internet until you press **نشر على الموقع**. That button runs
`git add` + `git commit` + `git push` for the four data files only (never `app.js`, never
`index.html`), with a commit message listing what you changed. Pages serves it a minute or
two later.

Why it cannot leak:

- it binds to `127.0.0.1`, so nothing else on the network — let alone the internet — can
  open it;
- there is no `admin.html` in the repository: the page is generated by `admin.py`, so
  `catalog.perfumespalace.store` has nothing to serve;
- if `products.json` changes while the page is open (another window, or a
  `python set-visibility.py` run), the page refuses to save and asks you to reload, so
  an old page can never overwrite a new file;
- the tick box writes the same `visible` flag as `set-visibility.py`, and the header tick
  box is the `meta.show_out_of_stock` switch — both follow the one rule in `visibility.py`.
  **أزل** on a row drops its hand-made flag and returns it to the general rule.

What the page does not offer is still done in the JSON: `compare_at_price` (the `خصم N%`
badge), `attributes`, images and `brand`.

## Editing the data by hand

Each product in `products.json`:

```json
{
  "id": 3572,
  "sku": "IBRAQ-TOB-SET-9X20",
  "name": "Ibraq Tobacco Collection Set 9x20ml ابراق مجموعة توباكو 9×20 مل",
  "brand": "Ibraheem Al Qurashi",
  "category": "مجموعات",
  "price": 280,
  "compare_at_price": null,
  "rating": 0,
  "reviews": 0,
  "stock": null,
  "added": "2026-09-01",
  "images": ["images/2026/09/yclzhj.jpg"],
  "attributes": { "التصنيف": "نيش", "الحجم": "علبة اصلية كاملة (100 مل)" },
  "tags": ["متاح للتقسيم"],
  "description": "مجموعة IBRAQ التوباكو 9×20 مل — Extrait de Parfum",
  "categories": []
}
```

- `compare_at_price` — higher than `price` gives a `خصم N%` badge and a struck-through
  price; `null` for a normal price.
- `price: null` — shows `السعر عند الطلب` and is excluded from the slider range.
- `stock` — `0` shows `نفدت الكمية` and disables add-to-cart; a number 8 or lower shows
  `بقي N فقط`; `null` means available with an unlisted quantity.
- `visible` (optional) — `false` leaves the product out of the page **and** out of the Meta feed;
  `true` keeps it listed even when sold out. Omit it to follow `meta.show_out_of_stock`.
- `added` — the `جديد` badge compares each product with the **newest product date in the
  catalogue** (30-day window), not with `meta.updated`.
- `attributes` — free-form key/value pairs, string or list. The key becomes the filter group
  title, so write it in Arabic (`"الشاشة": "13 بوصة"` gives a **الشاشة** filter).
- `images` — relative paths under `images/` (or absolute URLs — both work). The first one is used
  on the card, all of them appear in the quick-view gallery.
- `id` — must be unique; a hand-added row can use any unused number (`900001` is one).
- `meta` — `store` (name), `tagline` (split on `—` into the hero headline plus the rotating
  words), `currency`, `locale`, `updated` (the date shown in the header), `whatsapp` (adds the
  «اطلب عبر واتساب» link), `source` (the public catalogue URL).

### Hiding products (out of stock, or one you no longer sell)

Two switches, both inside `products.json`, both read by the page (`app.js`) and by the Meta feed
(`build-feed.py`) — so a hidden product disappears from the grid, the filter counts, the cart and
the WhatsApp catalogue at the same time.

| switch | where | effect |
| --- | --- | --- |
| `"show_out_of_stock": false` | `meta` | every row with `stock: 0` is left out |
| `"visible": false` | one product row | that row is left out, whatever its stock |
| `"visible": true` | one product row | that row stays, even while the switch above is `false` |

A product's own flag always wins over the bulk switch. Nothing is deleted: the row keeps its id,
so the product returns the moment the flag goes away.

Editing 5,000 lines of JSON by hand is awkward, so there is a helper:

```
python set-visibility.py list                          # what is hidden, what is sold out
python set-visibility.py oos off                       # hide everything that is sold out
python set-visibility.py oos on                        # show it again (the default)
python set-visibility.py hide 2681                     # by product id
python set-visibility.py hide "نجدية" "French Avenue"  # by name, brand or sku
python set-visibility.py hide --oos                    # flag every sold-out row one by one
python set-visibility.py show 2681                     # bring one back
python set-visibility.py clear                         # remove every "visible" flag
```

Add `--dry-run` to preview, or `--file copy.json` to try it on a copy first.

The rule itself lives in `visibility.py` and is mirrored in `app.js`, so the page and the feed
cannot disagree. After changing it, rebuild the feed:

```
python build-feed.py --sets      # hidden rows leave feed.xml / feed.csv / sets.json
python create-sets.py --apply    # only when the sets' item counts changed
```

Meta's side: a scheduled feed re-import replaces the catalogue items, so a hidden product is
removed from the Facebook / WhatsApp catalogue on the next fetch. To keep sold-out items listed
but unbuyable instead, leave `show_out_of_stock` alone — they go out as `availability:
out of stock` and the page shows `نفدت الكمية`.

### Currency and numerals

`meta.currency` is an ISO code passed to `Intl.NumberFormat` (`ILS` here, also `SAR`, `AED`,
`USD`, …). `meta.locale` controls formatting:

| `meta.locale` | price renders as | date renders as |
| --- | --- | --- |
| `ar-EG-u-nu-latn` (current) | 140 ₪ | 13 أكتوبر 2026 |
| `ar-EG` | ١٤٠ ₪ (Arabic-Indic digits) | ١٣ أكتوبر ٢٠٢٦ |

Fraction digits follow the value: `140 ₪` and `140.50 ₪` both render correctly.

## Making it LTR / English again

Set `<html lang="en" dir="ltr">` in `index.html` and translate the strings in `app.js`
(facet titles, badges, sort labels) and `index.html`. The layout, slider, modal and cart drawer
already use logical properties (`margin-inline-start`, `inset-inline-end`, `padding-inline`) —
the drawer slides from the inline-end side in both directions — so they flip back automatically
with the document direction.

## Notes

- `products.demo.json` is the original sample catalogue (Arabic home/office goods with
  picsum.photos images) in case you want the demo back: copy it over `products.json`.
- After editing `styles.css` or `app.js`, bump the `?v=` query on the asset links in
  `index.html`, otherwise the browser serves the cached copy.
- `load()` in `app.js` is the single place to change if you want to fetch from a live API
  instead of the static file.
