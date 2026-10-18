# -*- coding: utf-8 -*-
"""
Meta catalogue feeds (Facebook, Instagram, the WhatsApp Business catalogue) accept
only JPG or PNG for image_link, while a third of the images the store serves are WebP.
This writes a JPEG twin for every .webp that products.json references, so the site
keeps using the smaller WebP files and the feed can point at JPEG instead.

Run standalone:  python webp_to_jpeg.py            (writes images/jpg/**, prints a summary)
Used by:         build-feed.py -- it maps every .webp image to its twin here.

Layout:  images/2026/09/yclzhj.webp  ->  images/jpg/2026/09/yclzhj.jpg

Notes:   transparent WebP is flattened onto white, because JPEG has no alpha;
         files that are already up to date are skipped, so repeat runs are cheap;
         the originals are never modified or deleted.
"""

import json
import os
import sys

from PIL import Image

SRC_JSON = "products.json"
TWIN_DIR = "images/jpg"
QUALITY = 88
MIN_SIDE = 500            # Meta recommends at least 500x500 px
MAX_BYTES = 8 * 1048576   # Meta rejects images above 8 MB


def twin_path(rel):
    """The JPEG twin of a catalogue image path, always with forward slashes.

    images/2026/09/x.webp -> images/jpg/2026/09/x.jpg  (anything non-WebP -> itself)
    Both the file system (Windows accepts /) and feed URLs use this one form.
    """
    rel = rel.replace("\\", "/")
    if not rel.lower().endswith(".webp"):
        return rel
    head, _ = os.path.splitext(rel)
    parts = head.split("/")
    if parts and parts[0] == "images":
        parts = parts[1:]
    return "/".join([TWIN_DIR] + parts) + ".jpg"


def convert(src, dst):
    """Write dst as a baseline-progressive JPEG and return its (width, height)."""
    with Image.open(src) as im:
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.split()[-1])
            im = flat
        elif im.mode != "RGB":
            im = im.convert("RGB")
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        im.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        return im.size


def webp_in(data):
    """Every distinct WebP path products.json points at, sorted."""
    return sorted({
        src for product in data["products"] for src in (product.get("images") or [])
        if isinstance(src, str) and src.lower().endswith(".webp")
    })


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    json_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else SRC_JSON
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    sources = webp_in(data)
    if not sources:
        print("  no WebP images referenced in %s -- nothing to do" % json_path)
        return

    written = fresh = failed = 0
    small, huge, bytes_out = [], [], 0
    for rel in sources:
        dst = twin_path(rel)
        if not os.path.exists(rel):
            print("  missing source: %s" % rel)
            failed += 1
            continue
        if not (os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(rel)):
            try:
                convert(rel, dst)
                written += 1
            except Exception as exc:                     # noqa: BLE001 - report and continue
                print("  failed %s: %s" % (rel, exc))
                failed += 1
                continue
        else:
            fresh += 1
        with Image.open(dst) as im:
            width, height = im.size
        size = os.path.getsize(dst)
        bytes_out += size
        if min(width, height) < MIN_SIDE:
            small.append("%s (%dx%d)" % (dst, width, height))
        if size > MAX_BYTES:
            huge.append(dst)

    print("  webp images: %d -> written %d, up to date %d, failed %d" % (len(sources), written, fresh, failed))
    print("  jpeg twins: %d, %.1f MB" % (len(sources) - failed, bytes_out / 1048576.0))
    if small:
        print("  note: %d twin(s) under %dpx -- Meta recommends at least %dpx" % (len(small), MIN_SIDE, MIN_SIDE))
        for row in small[:5]:
            print("        %s" % row)
    if huge:
        print("  note: %d twin(s) above 8 MB -- Meta rejects those" % len(huge))
        for row in huge[:5]:
            print("        %s" % row)
    if failed:
        print("  note: %d source image(s) could not be converted" % failed)


if __name__ == "__main__":
    main()
