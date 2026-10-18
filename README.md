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
- **Facets built from the data.** Brand (العلامة التجارية — 49 values), Price, and the product
  attributes (`التصنيف`) are the groups shown. Every attribute key in the JSON becomes its own
  filter group automatically, then the titles listed in `HIDDEN_FACETS` in `app.js`
  (`الفئة`, `التوفر`, `الحجم`, `الموسم`, `الاستعمال`, `الاتجاه`) are skipped — delete a name
  from that set to bring its group back. Keys with a single value across the catalogue are
  skipped too. Long groups (more than 12 values) get a **search box inside the group** and a
  **«عرض المزيد» button** that reveals the remaining values; groups far down the list render
  collapsed and expand on click.
- **Multi-value attributes.** An attribute may hold a list (`"الموسم": ["خريفي", "شتوي"]`).
  Each value becomes its own filter row, and a product matches if it carries any of the
  selected values. In the card and spec table the values are shown joined: `خريفي، شتوي`.
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

- One row per catalogue row (**185** rows): `id` (the product id — the same value the WhatsApp
  Cloud API calls `retailer_id`), `title`, `description`, `availability`, `condition`, `price`,
  `sale_price` (165 rows), `link` (the WooCommerce product page, so a catalogue tap leads to the
  real checkout), `image_link` + `additional_image_link` (up to 10), `brand`, and
  `google_product_category` (drop it with `--no-gpc`).
- Prices carry the ISO code — `280.00 ILS`. `compare_at_price` becomes `sale_price`, with the
  higher price left in `price` so Meta can strike it through.
- **3 rows are skipped**: products tagged «السعر عند الطلب» have no price, and Meta requires one.
- Sold-out rows stay in the feed as `out of stock` (`stock == 0` → `in stock` otherwise). The one
  sold-out product in the current data is also priceless, which is why every row today is
  `in stock`.
- WebP pictures point at a JPEG twin under `images/jpg/…` (102 files, ~14 MB) and everything else
  keeps its own file. The site itself still loads the smaller WebP files. One twin is 394×450 px
  while Meta recommends at least 500×500 — replace that product's photo if you want it perfect.
- After a data refresh, re-run both scripts and push, so the feed matches the new catalogue.

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
