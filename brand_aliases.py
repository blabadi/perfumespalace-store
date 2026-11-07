# -*- coding: utf-8 -*-
"""Brand spellings that mean the same house, folded onto one value.

The same house can be written two ways — `Lattafa` next to `لطافة Lattafa`. One brand
should mean one thing: the site shows one facet value, and Meta gets one brand, so it
becomes one product set instead of two.

Applied by build-feed.py, so an alias in products.json never splits the feed. Keep the
spelling with more products, and drop an entry once the catalogue uses one spelling.
"""

UNSPECIFIED = "غير محدد"          # the brand value used when a row carries none

# spelling to drop -> the one to keep
BRAND_ALIASES = {
    "Lattafa": "لطافة Lattafa",
}


def canonical_brand(value):
    """The brand a product should be filed under."""
    name = " ".join(str(value or "").split())
    return BRAND_ALIASES.get(name, name) or UNSPECIFIED
