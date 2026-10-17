# -*- coding: utf-8 -*-
"""
Make the catalogue self-hosted: download every product image into ./images and
rewrite the paths inside products.json from absolute store URLs to relative ones.

Why: the page then keeps working even if perfumespalace.store changes its URLs,
blocks hotlinking, or goes offline -- which also makes the repo deployable to
GitHub Pages with the pictures served from the same origin.

Run standalone:   python download_images.py            (rewrites products.json)
Called by build-products.py after it writes a fresh products.json.

Layout:  images/<yyyy>/<mm>/<name>.<ext>   (year/month come from the uploads path)
         images/misc/<name>.<ext>         (when the URL has no uploads date)
Manifest: images/manifest.json maps the original URL -> relative path, so repeat
          runs skip files that are already downloaded and never rename them.
"""

import concurrent.futures
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) catalogue-images",
    "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
}
UPLOAD_PATH = re.compile(r"/wp-content/uploads/(\d{4})/(\d{2})/")
IMAGE_DIR = "images"
MANIFEST = os.path.join(IMAGE_DIR, "manifest.json")
EXT_FROM_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
}
SAFE_CHARS = "/%:@&=+$,~!*'()"


def ascii_url(url):
    """Some store URLs carry raw Arabic characters; urllib needs them percent-encoded.
    The original (readable) URL is what stays in products.json."""
    parts = urllib.parse.urlsplit(url)
    try:
        parts.path.encode("ascii")
        parts.query.encode("ascii")
    except UnicodeEncodeError:
        return urllib.parse.urlunsplit((
            parts.scheme, parts.netloc,
            urllib.parse.quote(parts.path, safe=SAFE_CHARS),
            urllib.parse.quote(parts.query, safe=SAFE_CHARS + "?"),
            parts.fragment,
        ))
    return url


def safe_name(url):
    """Readable, ASCII-only file name for a URL (Windows + URL safe)."""
    path = urllib.parse.urlparse(url).path
    name = urllib.parse.unquote(os.path.basename(path))
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"[^\w.-]+", "-", stem, flags=re.ASCII).strip("-_.") or "img"
    ext = re.sub(r"[^A-Za-z0-9.]+", "", ext).lower()
    return stem[:80] + ext, stem


def subdir_for(url):
    m = UPLOAD_PATH.search(urllib.parse.urlparse(url).path)
    return "%s/%s" % (m.group(1), m.group(2)) if m else "misc"


def fetch(url, tries=3):
    target = ascii_url(url)
    last = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(target, headers=HEADERS), timeout=60) as r:
                return r.read(), r.headers.get("Content-Type", "").split(";")[0].strip()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as err:
            last = err
    raise last


def download(url, taken):
    """
    Download one image. `taken` is the set of relative paths already used by other
    URLs, so two different sources that share a file name get distinct targets.
    Returns the relative path, or None when the image cannot be fetched.
    """
    name, stem = safe_name(url)
    folder = IMAGE_DIR + "/" + subdir_for(url)
    rel = folder + "/" + name
    if rel in taken:
        rel = "%s/%s-%s%s" % (folder, stem, hashlib.sha1(url.encode("utf-8")).hexdigest()[:8],
                              os.path.splitext(name)[1])
    if os.path.exists(rel) and os.path.getsize(rel) > 0:
        return rel
    try:
        data, ctype = fetch(url)
    except Exception as err:
        print("  ! %s (%s)" % (url, err))
        return None
    if not os.path.splitext(rel)[1] and ctype in EXT_FROM_TYPE:
        rel += EXT_FROM_TYPE[ctype]
    os.makedirs(os.path.dirname(rel), exist_ok=True)
    with open(rel, "wb") as fh:
        fh.write(data)
    return rel


def localize(json_path="products.json", workers=8):
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    urls = []
    for p in data["products"]:
        for src in p.get("images") or []:
            if isinstance(src, str) and src.startswith(("http://", "https://")) and src not in urls:
                urls.append(src)

    os.makedirs(IMAGE_DIR, exist_ok=True)
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)

    todo = [u for u in urls if manifest.get(u) and os.path.exists(manifest[u])]
    pending = [u for u in urls if u not in todo]
    mapping = {u: manifest[u] for u in todo}
    taken = set(mapping.values())
    print("images: %d referenced, %d cached, %d to download" % (len(urls), len(todo), len(pending)))

    done = 0
    if pending:
        # Serialise the collision check: reserve the target path before writing.
        def work(url):
            nonlocal done
            name, stem = safe_name(url)
            folder = IMAGE_DIR + "/" + subdir_for(url)
            rel = folder + "/" + name
            if rel in taken:
                rel = "%s/%s-%s%s" % (folder, stem, hashlib.sha1(url.encode()).hexdigest()[:8],
                                      os.path.splitext(name)[1])
            taken.add(rel)
            if os.path.exists(rel) and os.path.getsize(rel) > 0:
                return url, rel
            try:
                body, ctype = fetch(url)
            except Exception as err:
                print("  ! %s (%s)" % (url, err))
                return url, None
            if not os.path.splitext(rel)[1] and ctype in EXT_FROM_TYPE:
                rel += EXT_FROM_TYPE[ctype]
            os.makedirs(os.path.dirname(rel), exist_ok=True)
            with open(rel, "wb") as fh:
                fh.write(body)
            done += 1
            if done % 25 == 0:
                print("  %d/%d ..." % (done, len(pending)))
            return url, rel

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for url, rel in pool.map(work, pending):
                if rel:
                    mapping[url] = rel

    # Rewrite the catalogue in place; keep any non-http src (e.g. data: URIs) as-is.
    missing = 0
    for p in data["products"]:
        images = []
        for src in p.get("images") or []:
            if isinstance(src, str) and isinstance(mapping.get(src), str) and mapping[src]:
                local = mapping[src]
                if local not in images:
                    images.append(local)
            else:
                if isinstance(src, str) and src.startswith(("http://", "https://")):
                    missing += 1
                if src not in images:
                    images.append(src)
        p["images"] = images

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        # Merge, never replace: a later run only sees the URLs that are still remote.
        merged = {u: p for u, p in list(manifest.items()) + list(mapping.items()) if os.path.exists(p)}
        json.dump(merged, fh, ensure_ascii=False, indent=2, sort_keys=True)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    total = sum(os.path.getsize(v) for v in mapping.values() if os.path.exists(v))
    print("  downloaded now: %d, mapped: %d, failed: %d" % (done, len(mapping), missing))
    print("  local image bytes: %.1f MB" % (total / 1048576.0))
    if missing:
        print("  note: %d image(s) kept pointing at the store" % missing)
    return mapping


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    localize(sys.argv[1] if len(sys.argv) > 1 else "products.json")


if __name__ == "__main__":
    main()
