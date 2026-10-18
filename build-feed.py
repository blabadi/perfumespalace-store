# -*- coding: utf-8 -*-
"""
Turn products.json into a Meta product feed -- the format the WhatsApp Business
catalogue, Facebook shops and Instagram shops all ingest. Writes feed.xml (RSS 2.0
with the g: namespace) and feed.csv with the same rows, so either URL can be pasted
into Commerce Manager -> Catalogue -> Data sources -> Scheduled feed, and that
catalogue is then connected to the WhatsApp Business number.

Run:  python build-feed.py                                 (feed.xml + feed.csv)
      python build-feed.py --base https://catalog.perfumespalace.store/
      python build-feed.py --out feed --check              (also HEAD-check image URLs)
      python build-feed.py --no-gpc                        (drop google_product_category)

Rules applied here:
  * a price is mandatory, so the «السعر عند الطلب» rows (price null) are skipped;
  * sold-out items stay in the feed, marked "out of stock";
  * WebP images point at the JPEG twin written by webp_to_jpeg.py, because Meta only
    accepts JPG/PNG for image_link;
  * prices are quoted in the catalogue currency with the ISO code ("280.00 ILS").

Feed URL for Commerce Manager: <base>/feed.xml  (or /feed.csv).
"""

import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webp_to_jpeg import twin_path            # noqa: E402  (needs the path tweak above)

SRC_JSON = "products.json"
DEFAULT_BASE = "https://catalog.perfumespalace.store/"
MAX_TITLE = 200           # Meta's limit
MAX_DESC = 5000           # Meta's limit
MAX_IMAGES = 10           # image_link + additional_image_link
GPC = "Health & Beauty > Personal Care > Cosmetics > Perfume & Cologne"
CHECK_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; catalogue-feed-check)"}


def text(value, limit):
    """Plain single-line text, stripped of characters XML cannot carry."""
    flat = " ".join(str(value or "").split())
    flat = "".join(c for c in flat if c >= " " or c == "\t")
    return flat[:limit].strip()


def money(amount, currency):
    return "%.2f %s" % (float(amount), currency)


def describe(product):
    """The store's own description, or a short one built from the row itself."""
    own = text(product.get("description"), MAX_DESC)
    if own:
        return own
    parts = [product.get("name"), product.get("brand"), product.get("category")]
    built = " — ".join(text(p, 200) for p in parts if p)
    values = []
    for value in (product.get("attributes") or {}).values():
        for item in (value if isinstance(value, list) else [value]):
            if item and text(item, 60) not in values:
                values.append(text(item, 60))
    if values:
        built += " — " + "، ".join(values[:6])
    return built[:MAX_DESC]


def image_urls(product, base):
    """Absolute, feed-safe image URLs: main first, then the rest of the gallery."""
    urls = []
    for src in product.get("images") or []:
        if not isinstance(src, str):
            continue
        if src.startswith("http://") or src.startswith("https://"):
            url = src
        else:
            url = base + urllib.parse.quote(twin_path(src), safe="/")
        if url not in urls:
            urls.append(url)
    return urls[:MAX_IMAGES]


def row_for(product, base, currency, with_gpc=True):
    """The feed fields for one product, or None when Meta cannot accept it."""
    price = product.get("price")
    if price in (None, "") or float(price) <= 0:
        return None                                   # price is required by Meta
    images = image_urls(product, base)
    if not images:
        return None

    was_price = product.get("compare_at_price")
    on_sale = was_price is not None and float(was_price) > float(price)
    row = {
        "id": str(product.get("id")),
        "title": text(product.get("name"), MAX_TITLE),
        "description": describe(product),
        "availability": "out of stock" if product.get("stock") == 0 else "in stock",
        "condition": "new",
        "price": money(was_price if on_sale else price, currency),
        "link": product.get("url") or base,
        "image_link": images[0],
        "brand": text(product.get("brand"), MAX_TITLE),
    }
    if on_sale:
        row["sale_price"] = money(price, currency)
    if len(images) > 1:
        row["additional_image_link"] = images[1:]
    if with_gpc:
        row["google_product_category"] = GPC
    return row


def field_names(rows):
    """Column order: the required core first, the optional ones after it."""
    core = ["id", "title", "description", "availability", "condition", "price",
            "sale_price", "link", "image_link", "additional_image_link", "brand",
            "google_product_category"]
    return [name for name in core if any(name in row for row in rows)]


def cell(name, value):
    if isinstance(value, list):
        return ", ".join(value)
    return value


def write_xml(path, rows, names, meta, base):
    title = text(meta.get("store") or meta.get("tagline") or "Perfumes Palace", 200)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">',
           "<channel>",
           "  <title>%s</title>" % escape(title),
           "  <link>%s</link>" % escape(base),
           "  <description>%s</description>" % escape(title)]
    for row in rows:
        out.append("  <item>")
        for name in names:
            if name not in row:
                continue
            out.append("    <g:%s>%s</g:%s>" % (name, escape(cell(name, row[name])), name))
        out.append("  </item>")
    out.append("</channel>")
    out.append("</rss>")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


def write_csv(path, rows, names):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(names)
        for row in rows:
            writer.writerow([cell(name, row.get(name, "")) for name in names])


def check_urls(urls):
    """HEAD every image URL and report the ones that do not answer 200."""
    def head(url):
        request = urllib.request.Request(url, method="HEAD", headers=CHECK_HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return url, response.status
        except Exception as exc:                       # noqa: BLE001 - reported below
            return url, str(exc)[:60]

    with ThreadPoolExecutor(max_workers=12) as pool:
        return list(pool.map(head, urls))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    args = sys.argv[1:]
    base = DEFAULT_BASE
    out = "feed"
    with_gpc = True
    do_check = False
    positional = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--base":
            index += 1
            base = args[index]
        elif arg == "--out":
            index += 1
            out = args[index]
        elif arg == "--no-gpc":
            with_gpc = False
        elif arg == "--check":
            do_check = True
        else:
            positional.append(arg)
        index += 1
    if positional:
        source_json = positional[0]
    else:
        source_json = SRC_JSON

    # Default to whatever custom domain the repo publishes on.
    if base == DEFAULT_BASE and os.path.exists("CNAME"):
        with open("CNAME", encoding="utf-8") as fh:
            host = fh.read().strip()
        if host:
            base = "https://%s/" % host
    base = base.rstrip("/") + "/"

    with open(source_json, encoding="utf-8") as fh:
        data = json.load(fh)
    meta = data.get("meta") or {}
    currency = (meta.get("currency") or "ILS").upper()

    rows, skipped, missing_twin = [], [], []
    for product in data["products"]:
        row = row_for(product, base, currency, with_gpc)
        if row is None:
            skipped.append(product.get("name") or product.get("id"))
            continue
        # A WebP image whose JPEG twin was never written would 404 for Meta.
        for src in product.get("images") or []:
            if isinstance(src, str) and src.lower().endswith(".webp") and not os.path.exists(twin_path(src)):
                missing_twin.append(twin_path(src))
        rows.append(row)

    names = field_names(rows)
    xml_path, csv_path = out + ".xml", out + ".csv"
    write_xml(xml_path, rows, names, meta, base)
    write_csv(csv_path, rows, names)

    print("  products: %d -> feed rows %d, skipped %d" % (len(data["products"]), len(rows), len(skipped)))
    for name in skipped[:5]:
        print("        skipped (no price): %s" % text(name, 60))
    print("  columns: %s" % ", ".join(names))
    print("  files: %s (%.1f KB), %s (%.1f KB)" % (
        xml_path, os.path.getsize(xml_path) / 1024.0,
        csv_path, os.path.getsize(csv_path) / 1024.0))
    print("  sale prices: %d, out of stock: %d" % (
        sum(1 for row in rows if "sale_price" in row),
        sum(1 for row in rows if row["availability"] == "out of stock")))
    if missing_twin:
        print("  note: %d WebP image(s) have no JPEG twin on disk -- run "
              "`python webp_to_jpeg.py` (Meta only accepts JPG/PNG for image_link)"
              % len(set(missing_twin)))
    print("  feed URL for Commerce Manager: %s%s.xml" % (base, out))

    if do_check:
        urls = sorted({url for row in rows for url in [row["image_link"]] + row.get("additional_image_link", [])})
        results = check_urls(urls)
        bad = [(url, status) for url, status in results if status != 200]
        print("  image check: %d unique URLs, %d not OK" % (len(urls), len(bad)))
        for url, status in bad[:10]:
            print("        %s -> %s" % (status, url))
        print("  row check: %d rows, %d item links, %d missing link" % (
            len(rows), sum(1 for row in rows if row.get("link")), sum(1 for row in rows if not row.get("link"))))


if __name__ == "__main__":
    main()
