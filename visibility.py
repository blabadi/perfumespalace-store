# -*- coding: utf-8 -*-
"""
One visibility rule for products.json, shared by the site (app.js) and the Meta feed
(build-feed.py), so a product cannot be hidden in one place and still show up in
another.

Two levers, both edited in products.json:

  meta.show_out_of_stock   true  (default) -> sold-out rows are listed, marked «نفدت الكمية»
                           false           -> rows with stock 0 are left out everywhere

  "visible": false         on one product  -> always left out, whatever its stock
  "visible": true          on one product  -> always listed, even when sold out

A product's own flag always wins over the bulk switch, so one row can stay on the
site while the rest of the sold-out list is hidden.

Hand-editing 5,000 lines of JSON is awkward, so set-visibility.py writes these two
levers for you:  python set-visibility.py list
"""

BULK_KEY = "show_out_of_stock"        # the meta switch
FLAG = "visible"                      # the per-product switch

# Hand-typed JSON often arrives as a string; treat these as "off".
FALSEY = ("false", "0", "no", "off", "")


def truthy(value):
    """True unless the value is explicitly an off switch."""
    if isinstance(value, str):
        return value.strip().lower() not in FALSEY
    return bool(value)


def sold_out(product):
    """stock 0 means sold out; null means "in stock, quantity not published"."""
    stock = product.get("stock")
    if stock is None or isinstance(stock, bool):
        return False
    try:
        return float(stock) == 0
    except (TypeError, ValueError):
        return str(stock).strip().lower() in FALSEY


def is_visible(product, meta=None):
    """Should this row appear on the site and in the feed?"""
    flag = product.get(FLAG)
    if flag is not None:
        return truthy(flag)
    if sold_out(product):
        return truthy((meta or {}).get(BULK_KEY, True))
    return True


def split(products, meta=None):
    """(shown, hidden) for a list of product rows."""
    shown, hidden = [], []
    for product in products:
        (shown if is_visible(product, meta) else hidden).append(product)
    return shown, hidden


def why_hidden(product, meta=None):
    """Short Arabic reason for a hidden row, "" when the row is shown."""
    if is_visible(product, meta):
        return ""
    if product.get(FLAG) is not None:
        return '"%s": false' % FLAG
    if sold_out(product):
        return "نفدت الكمية + show_out_of_stock=false"
    return ""
