# -*- coding: utf-8 -*-
"""Brand spellings the store uses more than once, folded onto one value.

Products are tagged with the `pa_brand` taxonomy in WooCommerce, and the same house
sometimes turns up under two spellings — `Lattafa` next to `لطافة Lattafa`. One brand
should mean one thing: the site shows one facet value, and Meta gets one brand, so it
becomes one product set instead of two.

The real fix is the store's tag; until that happens this map is applied by
build-products.py (so products.json and the site agree) and again by build-feed.py
(so the feed is right even from an un-normalised products.json). Keep the spelling
with more products, and drop an entry once the store agrees with it.
"""

UNSPECIFIED = "غير محدد"          # what the store calls a product with no brand tag

# spelling to drop -> the one to keep
BRAND_ALIASES = {
    "Lattafa": "لطافة Lattafa",
}


def canonical_brand(value):
    """The brand a product should be filed under."""
    name = " ".join(str(value or "").split())
    return BRAND_ALIASES.get(name, name) or UNSPECIFIED
