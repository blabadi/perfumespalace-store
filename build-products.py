# -*- coding: utf-8 -*-
"""
Build products.json for the Arabic RTL catalogue from perfumespalace.store.

The store runs WooCommerce, so the data comes from its public Store API:
    /wp-json/wc/store/v1/products?per_page=100&page=N

Run:  python build-products.py
Out:  products.json   (the catalogue file the page reads)
      products.demo.json is kept as the original sample catalogue.
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://perfumespalace.store"
API = BASE + "/wp-json/wc/store/v1/products"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) catalogue-import",
    "Accept": "application/json",
}

# Attribute taxonomies to keep as filter groups (Arabic name -> taxonomy).
# pa_brand becomes the "brand" field instead of an attribute group.
KEEP_ATTRS = {
    "pa_classification": "التصنيف",
    "pa_size": "الحجم",
    "pa_season": "الموسم",
    "pa_usage": "الاستعمال",
    "pa_direction": "الاتجاه",
}
# Single-value taxonomies are not useful as filters -> turned into a tag instead.
TAG_ATTRS = {"pa_samples": "متاح للتقسيم"}
PRICE_TAG = "السعر عند الطلب"

# Download the product photos into ./images and store relative paths in the JSON.
# Set to False (or run with IMAGES=remote) to keep absolute store URLs instead.
LOCAL_IMAGES = os.environ.get("IMAGES", "local").lower() != "remote"

JUNK = re.compile(r"اضف لقائمة التسوق.*|موجود حاليا في قائمة التسوق.*")
UPLOAD_DATE = re.compile(r"/wp-content/uploads/(\d{4})/(\d{2})/")


def get_json(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as err:
            last = err
            print("  retry %d for %s (%s)" % (attempt + 1, url, err))
    raise SystemExit("fetch failed: %s -> %s" % (url, last))


def fetch_all_products():
    products, page = [], 1
    while True:
        url = "%s?per_page=100&page=%d&catalog_visibility=visible" % (API, page)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=40) as r:
            batch = json.loads(r.read().decode("utf-8"))
            total = int(r.headers.get("x-wp-total", "0"))
        if not batch:
            break
        products.extend(batch)
        print("  page %d -> %d products (%d/%d)" % (page, len(batch), len(products), total))
        if len(products) >= total:
            break
        page += 1
        if page > 40:
            break
    return products


def clean_html(raw):
    """WooCommerce descriptions are HTML; some carry wishlist-plugin junk."""
    if not raw:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|li|ul|ol|div|h[1-6]|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[\u200e\u200f\u202a-\u202e\ufeff]", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line or JUNK.fullmatch(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def term_name(value, slug_to_name):
    """Variation option values arrive as slugs; map them back to the Arabic term name."""
    decoded = urllib.parse.unquote(str(value or ""))
    return slug_to_name.get(decoded) or slug_to_name.get(decoded.lower()) or decoded


def added_from_images(images, fallback):
    for img in images:
        m = UPLOAD_DATE.search(img.get("src") or "")
        if m:
            return "%s-%s-01" % (m.group(1), m.group(2))
    return fallback


def to_number(value, minor_unit):
    try:
        return round(int(value) / (10 ** minor_unit), 2)
    except (TypeError, ValueError):
        return None


def add_terms(attrs, name, terms):
    """Collect attribute terms without duplicates; order follows the store."""
    current = attrs.setdefault(name, [])
    for term in terms:
        if term not in current:
            current.append(term)


def map_product(p, fallback_date, parent=None):
    prices = p.get("prices") or {}
    minor = int(prices.get("currency_minor_unit", 0))
    price = to_number(prices.get("price"), minor)
    regular = to_number(prices.get("regular_price"), minor)
    sale = to_number(prices.get("sale_price"), minor)
    if sale is not None and regular is not None and regular > sale:
        price, compare = sale, regular
    elif regular is not None and price is not None and regular > price:
        compare = regular
    else:
        compare = None
    if price == 0:
        price = None  # the store lists no price for this product (price on request)

    attrs, tags, brand = {}, [], ""
    for group in p.get("attributes") or []:
        taxonomy = group.get("taxonomy") or ""
        terms = [t.get("name", "") for t in (group.get("terms") or []) if t.get("name")]
        if not terms:
            continue
        if taxonomy == "pa_brand":
            brand = terms[0]
        elif taxonomy in KEEP_ATTRS:
            add_terms(attrs, KEEP_ATTRS[taxonomy], terms)
        elif taxonomy in TAG_ATTRS:
            tags.append(TAG_ATTRS[taxonomy])

    # Variation rows only carry option slugs; resolve them with the parent's term list.
    if parent is not None:
        for group in parent.get("attributes") or []:
            if group.get("taxonomy") not in KEEP_ATTRS:
                continue
            slug_to_name = {t.get("slug"): t.get("name") for t in (group.get("terms") or [])}
            slug_to_name.update({urllib.parse.unquote(s): n for s, n in slug_to_name.items()})
            for opt in p.get("attributes") or []:
                if opt.get("name") != group.get("name"):
                    continue
                name = term_name(opt.get("value"), slug_to_name)
                if name:
                    add_terms(attrs, KEEP_ATTRS[group["taxonomy"]], [name])

    # A product may carry several terms for one attribute (e.g. seasons). Keep them as a
    # list so the catalogue can filter on each term separately; a single term stays a string.
    attrs = {k: (v[0] if len(v) == 1 else v) for k, v in attrs.items() if v}

    for t in p.get("tags") or []:
        if t.get("name"):
            tags.append(t["name"])
    if price is None:
        tags.append(PRICE_TAG)

    categories = [c.get("name") for c in (p.get("categories") or []) if c.get("name")]
    images = [img.get("src") for img in (p.get("images") or []) if img.get("src")]

    in_stock = p.get("is_in_stock")
    low = p.get("low_stock_remaining")
    if not in_stock:
        stock = 0
    elif isinstance(low, int):
        stock = low
    else:
        stock = None  # WooCommerce hides exact quantities; null means "available"

    short = clean_html(p.get("short_description"))
    full = clean_html(p.get("description"))
    description = short or (full[:700] if full else "")

    sku = p.get("sku") or "PP-%d" % p["id"]

    return {
        "id": p["id"],
        "sku": sku,
        "name": html.unescape(p.get("name") or "").strip(),
        "brand": brand or "غير محدد",
        "category": categories[0] if categories else "غير محدد",
        "price": price,
        "compare_at_price": compare,
        "rating": float(p.get("average_rating") or 0),
        "reviews": int(p.get("review_count") or 0),
        "stock": stock,
        "added": added_from_images(p.get("images") or [], fallback_date),
        "images": images,
        "attributes": attrs,
        "tags": sorted(set(tags)),
        "description": description,
        "categories": categories,
        "url": p.get("permalink") or "",
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    except AttributeError:
        pass
    print("reading %s" % API)
    raw = fetch_all_products()

    # keep the newest-first order the store already returns
    today = date.today().isoformat()
    out, expanded = [], 0
    for p in raw:
        if p.get("type") == "variable" and p.get("variations"):
            # one catalogue row per variation, each with its own price and size
            for var in p["variations"]:
                detail = get_json("%s/%d" % (API, var["id"]))
                merged = dict(p)
                merged.update({k: v for k, v in detail.items() if k not in ("attributes", "variations")})
                merged["attributes"] = var.get("attributes") or []
                out.append(map_product(merged, today, parent=p))
                expanded += 1
        else:
            out.append(map_product(p, today))

    out = [p for p in out if p["name"]]
    meta = {
        "store": "قصر العطور",
        "tagline": "عطور أصلية من وكالاتها المعتمدة — نيش وديزاينر وبدائل، وتقسيمات متوفرة.",
        "currency": "ILS",
        "locale": "ar-EG-u-nu-latn",
        "updated": today,
        "source": BASE,
        "whatsapp": "+972566008917",
    }

    with open("products.json", "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "products": out}, fh, ensure_ascii=False, indent=2)

    # Host the pictures ourselves: pull every image into ./images and point the
    # catalogue at those relative paths, so the site does not depend on the store
    # staying online (and deploys to GitHub Pages as a single self-contained folder).
    if LOCAL_IMAGES:
        try:
            import download_images
            download_images.localize("products.json")
        except Exception as err:
            print("  image localization skipped: %s" % err)

    brands = {}
    cats = {}
    attrs = {}
    on_sale = sold_out = no_price = 0
    for p in out:
        brands[p["brand"]] = brands.get(p["brand"], 0) + 1
        cats[p["category"]] = cats.get(p["category"], 0) + 1
        for k, v in p["attributes"].items():
            values = v if isinstance(v, list) else [v]
            attrs.setdefault(k, set()).update(values)
        on_sale += 1 if p["compare_at_price"] else 0
        sold_out += 1 if p["stock"] == 0 else 0
        no_price += 1 if p["price"] is None else 0

    prices = [p["price"] for p in out if p["price"] is not None]
    print("wrote products.json")
    print("  products      : %d (%d variable rows expanded)" % (len(out), expanded))
    print("  brands        : %d" % len(brands))
    print("  categories    : %d" % len(cats))
    print("  attr groups   : %s" % ", ".join("%s(%d)" % (k, len(v)) for k, v in attrs.items()))
    print("  price range   : %.2f - %.2f %s" % (min(prices), max(prices), meta["currency"]))
    print("  on sale       : %d" % on_sale)
    print("  sold out      : %d" % sold_out)
    print("  price on request: %d" % no_price)
    print("  with images   : %d" % sum(1 for p in out if p["images"]))
    print("  with gallery  : %d" % sum(1 for p in out if len(p["images"]) > 1))
    print("  with text     : %d" % sum(1 for p in out if p["description"]))


if __name__ == "__main__":
    main()
