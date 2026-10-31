# -*- coding: utf-8 -*-
"""
Hide or show products in products.json without hand-editing 5,000 lines of Arabic.

Run:  python set-visibility.py list                 (what is hidden, what is sold out)
      python set-visibility.py hide 2681            (by id)
      python set-visibility.py hide نجدية "French Avenue"   (by name / brand / sku)
      python set-visibility.py hide --oos           (every sold-out row, one by one)
      python set-visibility.py show 2681
      python set-visibility.py oos off              (meta switch: hide all sold-out rows)
      python set-visibility.py oos on
      python set-visibility.py clear                (drop every "visible" flag)

Add --dry-run to any command to see what would change. The file is written back in
the same shape build-products.py writes it, so diffs stay readable.

What it edits, and what reads it back:
  "visible": false|true   on a product row  -> app.js, build-feed.py
  meta.show_out_of_stock  false|true        -> app.js, build-feed.py
Both rules live in visibility.py. build-products.py copies these choices onto a fresh
scrape, so a data refresh cannot undo them.
"""

import json
import os
import sys

from visibility import BULK_KEY, FLAG, is_visible, sold_out, truthy, why_hidden

SRC_JSON = "products.json"


def load(path):
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data.get("products"), list):
        sys.exit("%s has no products array" % path)
    return data


def save(path, data, dry_run):
    if dry_run:
        return
    # Same call build-products.py uses: indent=2, no escaping, and the file's usual
    # CRLF line endings come from the default newline handling.
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def label(product):
    return "%-8s %-46s %s" % (product.get("id"), (product.get("name") or "")[:46],
                              product.get("brand") or "")


def find(products, queries):
    """Rows named on the command line: a number is an id or sku, anything else is a
    substring of the name, brand or sku. Returns (matches, unmatched queries)."""
    matches, unmatched = [], []
    for query in queries:
        hits = []
        if query.isdigit():
            for p in products:
                if str(p.get("id")) == query or str(p.get("sku") or "") == query:
                    hits.append(p)
        if not hits:
            needle = query.lower()
            for p in products:
                hay = " ".join(str(p.get(key) or "") for key in ("name", "brand", "sku")).lower()
                if needle in hay:
                    hits.append(p)
        if not hits:
            unmatched.append(query)
        for p in hits:
            if p not in matches:
                matches.append(p)
    return matches, unmatched


def report(products, meta):
    shown, hidden = [], []
    for p in products:
        (shown if is_visible(p, meta) else hidden).append(p)
    bulk = meta.get(BULK_KEY, True)
    print("  meta.%s : %s" % (BULK_KEY, "true (sold-out rows are listed)"
                              if truthy(bulk) else "false (sold-out rows are hidden)"))
    flagged = [p for p in products if p.get(FLAG) is not None]
    print("  rows      : %d total, %d shown, %d hidden (%d with a %s flag)"
          % (len(products), len(shown), len(hidden), len(flagged), FLAG))
    oos = [p for p in products if sold_out(p)]
    print("  sold out  : %d" % len(oos))
    if oos:
        print("  sold-out rows:")
        for p in oos:
            reason = why_hidden(p, meta)
            if not reason:
                reason = ('kept by "%s": true' % FLAG) if p.get(FLAG) is not None else "shown"
            print("      %s  %s" % (label(p), reason))
    manual_hidden = [p for p in hidden if p.get(FLAG) is not None]
    if manual_hidden:
        print("  hidden by hand:")
        for p in manual_hidden:
            print("      %s" % label(p))
    bulk_hidden = [p for p in hidden if p.get(FLAG) is None]
    if bulk_hidden:
        print("  hidden by the bulk switch: %d" % len(bulk_hidden))
        for p in bulk_hidden[:10]:
            print("      %s" % label(p))
        if len(bulk_hidden) > 10:
            print("      … %d more" % (len(bulk_hidden) - 10))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    except AttributeError:
        pass

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    command, args = args[0], args[1:]

    path, dry_run, only_oos, queries = SRC_JSON, False, False, []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--oos":
            only_oos = True
        elif arg == "--file":
            index += 1
            path = args[index]
        elif arg.startswith("-"):
            sys.exit("unknown option: %s" % arg)
        else:
            queries.append(arg)
        index += 1

    if not os.path.exists(path):
        sys.exit("%s not found -- run it next to products.json" % path)
    data = load(path)
    meta = data.setdefault("meta", {})
    products = data["products"]

    if command == "list":
        report(products, meta)
        return

    if command == "oos":
        if len(queries) != 1 or queries[0].lower() not in ("on", "off", "true", "false"):
            sys.exit("usage: python set-visibility.py oos on|off")
        off = queries[0].lower() in ("off", "false")
        if off:
            meta[BULK_KEY] = False
        else:
            meta.pop(BULK_KEY, None)          # absent means the default: show them
        save(path, data, dry_run)
        shown, hidden = [p for p in products if is_visible(p, meta)], \
                        [p for p in products if not is_visible(p, meta)]
        print("  meta.%s = %s -> %d shown, %d hidden%s"
              % (BULK_KEY, json.dumps(meta.get(BULK_KEY, True)), len(shown), len(hidden),
                 "  (dry run, nothing written)" if dry_run else ""))
        return

    if command in ("hide", "show"):
        hiding = command == "hide"
        if only_oos:
            targets = [p for p in products if sold_out(p)]
        else:
            targets, missing = find(products, queries)
            if missing:
                sys.exit("no product matches: %s" % ", ".join(missing))
        if not targets:
            sys.exit("nothing to %s -- no row matched" % command)
        changed = 0
        for p in targets:
            if p.get(FLAG) is not None and truthy(p[FLAG]) == (not hiding):
                continue
            p[FLAG] = not hiding
            changed += 1
            print("  %s  %s" % ("hidden" if hiding else "shown ", label(p)))
        if not changed:
            print("  already %s: %d row(s)" % ("hidden" if hiding else "shown", len(targets)))
        save(path, data, dry_run)
        print("  %d row(s) %s%s" % (changed, "hidden" if hiding else "shown",
                                    "  (dry run, nothing written)" if dry_run else ""))
        return

    if command == "clear":
        changed = 0
        for p in products:
            if p.get(FLAG) is not None:
                print("  flag cleared  %s" % label(p))
                del p[FLAG]
                changed += 1
        save(path, data, dry_run)
        print("  %d flag(s) cleared%s" % (changed, "  (dry run, nothing written)" if dry_run else ""))
        return

    sys.exit("unknown command: %s (try: list, hide, show, oos, clear)" % command)


if __name__ == "__main__":
    main()
