# قصر العطور — Arabic RTL product catalogue (Perfumes Palace)

A WooCommerce-style product catalogue in **Arabic and right-to-left**, built from a plain
JSON file that is generated from the live store **perfumespalace.store**. No build step, no
dependencies — open it in a browser.

```
index.html          page structure (lang="ar" dir="rtl")
styles.css          all styling (logical properties, light + dark theme, responsive)
app.js              loads products.json, builds facets, filters, sorts, renders, handles the cart
products.json       the catalogue data (188 products) — generated, but you can edit it too
images/             every product photo, downloaded from the store (see "Hosting the pictures")
build-products.py   reads the store's WooCommerce Store API and rewrites products.json
download_images.py  downloads the product photos into images/ and rewrites the JSON paths
products.demo.json  the original hand-written sample catalogue (kept as a backup)
serve.cmd           optional: starts a local server (Python) so fetch() is allowed
```

## Run it

Browsers block `fetch()` on `file://` pages, so serve the folder:

```
python -m http.server 8000
```

then open <http://localhost:8000>. On Windows you can double-click `serve.cmd` instead.

## Refreshing the data from the store

```
python build-products.py
```

It reads `https://perfumespalace.store/wp-json/wc/store/v1/products` (the public WooCommerce
Store API, no auth) page by page, and writes `products.json`. What it does:

- **185 store products → 188 catalogue rows**: the 2 variable products are expanded into one
  row per variation, each with its own price and size.
- `pa_brand` becomes `brand`; WooCommerce categories become `category`; the attribute
  taxonomies `pa_classification`, `pa_size`, `pa_season`, `pa_usage`, `pa_direction` become
  the Arabic attribute keys `التصنيف`, `الحجم`, `الموسم`, `الاستعمال`, `الاتجاه` — which is
  what turns them into filter groups.
- `pa_samples` (single value) becomes the tag `متاح للتقسيم` instead of a useless filter.
- Prices come from `prices.price` / `regular_price` (ILS, 0 decimals); a real sale price
  higher than the current price becomes `compare_at_price` → `خصم N%` badge.
- Products the store lists with no price get `price: null` and the tag `السعر عند الطلب`.
- `stock` is `0` when out of stock, otherwise `null` (WooCommerce does not expose exact
  quantities through this API).
- `added` is taken from the image upload month (`/wp-content/uploads/2026/09/…`), which is
  the closest thing to a date-added this API offers.
- Descriptions are HTML → plain text, with the wishlist-plugin junk removed.

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
- **Facets built from the data.** Brand (العلامة التجارية — 49 values) and Category (الفئة)
  are fixed groups; every other attribute key in the JSON becomes its own filter group
  automatically. Keys with a single value across the catalogue are skipped. Long groups get
  a **search box inside the group** and a local scroll area; groups far down the list render
  collapsed and expand on click.
- **Multi-value attributes.** An attribute may hold a list (`"الموسم": ["خريفي", "شتوي"]`).
  Each value becomes its own filter row, and a product matches if it carries any of the
  selected values. In the card and spec table the values are shown joined: `خريفي، شتوي`.
- **Price filter** with a dual-handle slider plus typed min/max fields, derived from the
  lowest/highest priced product (40 – 1,500 ₪ here). Products with `price: null` are always
  kept and show `السعر عند الطلب`.
- **Availability** (عليها تخفيضات / متوفر في المخزون). The **rating** group and the star
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

## Hosting the pictures

Every product photo lives in `images/` inside this repo, so the page has **no dependency on the
store staying online** (and no hotlink/CORS surprises). `products.json` stores relative paths
like `images/2026/09/yclzhj.jpg`.

```
python download_images.py          # download what is missing, rewrite products.json
```

- Layout mirrors the store's uploads folders: `images/<yyyy>/<mm>/<name>.<ext>` (`images/misc/`
  when a URL has no upload date). The year/month is the same information `added` is computed from.
- `images/manifest.json` maps the original store URL → local file. Repeat runs skip anything
  already downloaded, and two different URLs that share a file name never collide (`-<hash8>`
  suffix). Raw Arabic characters in store URLs are percent-encoded for the request only, so the
  readable URL stays in the manifest.
- `build-products.py` runs this automatically (unless `IMAGES=remote` is set), so a data refresh
  stays self-hosted: `IMAGES=remote python build-products.py` keeps absolute store URLs instead.
- 295 images, ~74 MB total. Nothing is deleted, so re-running is always safe.

## Deploying it

Live on **GitHub Pages**: <https://blabadi.github.io/perfumespalace-store/> — and
<https://catalog.perfumespalace.store/> once the DNS record below is in place. Every push to
`main` redeploys automatically.

### Custom domain (`catalog.perfumespalace.store`)

The GitHub side is already configured — the custom domain is set in *Settings → Pages* and the
repo carries the `CNAME` file GitHub wrote (`catalog.perfumespalace.store`). Only the DNS record
is left, and it must be added at the DNS provider (Cloudflare for this domain):

| Type | Name | Target | Proxy |
| --- | --- | --- | --- |
| `CNAME` | `catalog` | `blabadi.github.io` | **DNS only** (grey cloud) |

⚠️ The `@` and `www` records **must not be touched** — `perfumespalace.store` itself points at
the Cloudflare-proxied WooCommerce store; sending the apex to GitHub Pages would take the store
offline. For an apex domain you would need `A` records to `185.199.108.153`, `185.199.109.153`,
`185.199.110.153`, `185.199.111.153` and `AAAA` records to `2606:50c0:8000::153`,
`2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`, all DNS-only.

After DNS propagates, tick **Enforce HTTPS** in *Settings → Pages*; GitHub issues a free
Let's Encrypt certificate.

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
  "attributes": { "التصنيف": "نيش", "الحجم": "علبة اصلية كاملة (100 مل)", "الموسم": ["خريفي", "شتوي"] },
  "tags": ["متاح للتقسيم"],
  "description": "مجموعة IBRAQ التوباكو 9×20 مل — Extrait de Parfum",
  "url": "https://perfumespalace.store/product/…"
}
```

- `compare_at_price` — higher than `price` gives a `خصم N%` badge and a struck-through
  price; `null` for a normal price.
- `price: null` — shows `السعر عند الطلب` and is excluded from the slider range.
- `stock` — `0` shows `نفدت الكمية` and disables add-to-cart; a number 8 or lower shows
  `بقي N فقط`; `null` means available with an unlisted quantity.
- `added` — the `جديد` badge compares each product with the **newest product date in the
  catalogue** (30-day window), not with `meta.updated`.
- `attributes` — free-form key/value pairs, string or list. The key becomes the filter group
  title, so write it in Arabic (`"الشاشة": "13 بوصة"` gives a **الشاشة** filter).
- `images` — relative paths under `images/` (or absolute URLs — both work). The first one is used
  on the card, all of them appear in the quick-view gallery.
- `url` (optional) — adds the «فتح المنتج في المتجر» link in the modal.
- `meta` — `store` (name), `tagline` (split on `—` into the hero headline plus the rotating
  words), `currency`, `locale`, `updated` (the date shown in the header), `whatsapp` (adds the
  «اطلب عبر واتساب» link), `source`.

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
