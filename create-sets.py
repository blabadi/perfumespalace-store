# -*- coding: utf-8 -*-
"""
Push sets.json into a Meta catalogue as product sets (Commerce Manager -> Catalogue
-> Product sets), one per brand. Built by build-feed.py --sets.

A set is a saved filter rule, e.g. {"brand": {"eq": "French Avenue"}}, so it follows
the feed: new products of that brand appear in the set by themselves, nothing has to
be re-created. Each set also carries a stable retailer_id (set_french_avenue) so this
script can recognise its own sets on the next run and update them instead of creating
duplicates.

Run:  python create-sets.py                       plan only, no network call
      python create-sets.py --list                what is already in the catalogue
      python create-sets.py --only French         plan for the sets matching "French"
      python create-sets.py --apply               create / update for real
      python create-sets.py --apply --delete-stale   also remove our old sets that are
                                                     no longer in sets.json

Credentials (never commit them):
      set META_CATALOG_ID=1234567890        from Commerce Manager -> Catalogue ->
                                           Settings -> Catalogue ID
      set META_TOKEN=EAAG...                a system-user access token that has the
                                           catalog_management permission

Graph API: POST /{catalog}/product_sets to create, POST /{product-set-id} to update.
Error 10803 means a set with the same filter already exists, which counts as success.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.facebook.com"
VERSION = "v26.0"
SETS_JSON = "sets.json"
READ_FIELDS = "id,name,filter,retailer_id,product_count"
RETRY_CODES = {1, 2, 4, 80009}          # unknown / transient / rate limited
DUPLICATE_CODE = 10803                  # "product set with the same filters already exists"


class GraphError(Exception):
    def __init__(self, message, code=None, subcode=None, trace=None):
        super().__init__(message)
        self.code, self.subcode, self.trace = code, subcode, trace

    def __str__(self):
        bits = [super().__str__()]
        if self.code is not None:
            bits.append("code %s" % self.code)
        if self.subcode is not None:
            bits.append("subcode %s" % self.subcode)
        if self.trace:
            bits.append("fbtrace %s" % self.trace)
        return " — ".join(str(b) for b in bits)


def graph(path, params=None, token="", method="GET", version=VERSION, retries=3):
    """One Graph API call. `path` may be a /node/edge path or an absolute paging URL."""
    params = dict(params or {})
    if token:
        params.setdefault("access_token", token)
    if path.startswith("http"):
        url = urllib.parse.urlparse(path)
        keep = {k for k, _ in urllib.parse.parse_qsl(url.query)}
        extra = {k: v for k, v in params.items() if k not in keep}
        url = path + ("".join("&%s=%s" % (k, urllib.parse.quote(str(v))) for k, v in extra.items()))
    else:
        base = API + "/" + version + path
        query = urllib.parse.urlencode(params)
        url = base + ("?" + query if query and method == "GET" else "")

    body = None if method == "GET" else urllib.parse.urlencode(params).encode("utf-8")
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url, data=body, method=method,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                err = (json.loads(raw).get("error") or {})
            except ValueError:
                err = {}
            message = err.get("message") or raw[:200] or str(exc)
            code = err.get("code")
            if code in RETRY_CODES and attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise GraphError(message, code, err.get("error_subcode"), err.get("fbtrace_id"))
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise GraphError("network: %s" % exc.reason)
    raise GraphError("unreachable")


def list_sets(catalog, token, version=VERSION):
    """Every product set in the catalogue, paging through the edge."""
    found, path, params = [], "/%s/product_sets" % catalog, {
        "fields": READ_FIELDS, "limit": 250}
    while path:
        page = graph(path, params, token, version=version)
        found.extend(page.get("data") or [])
        nxt = (page.get("paging") or {}).get("next")
        path, params = (nxt, None) if nxt else (None, None)
    return found


def rule(value):
    """Parse a filter rule into comparable data; Meta returns it as a JSON string."""
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else {}
        except ValueError:
            return {"raw": value}
    return value or {}


def plan_for(sets, existing):
    """Decide create / update / skip / conflict for each planned set.

    A set is recognised by its retailer_id first (that is one of ours), then by an
    identical rule, then by its name. Someone else's set is never renamed or rewritten:
    if it already carries the same rule we skip it, and if the name is taken by a
    different rule we report a conflict instead of hijacking it.
    """
    by_retailer = {item.get("retailer_id"): item for item in existing if item.get("retailer_id")}
    by_name = {(item.get("name") or "").strip(): item for item in existing}
    by_rule = {}
    for item in existing:
        by_rule.setdefault(json.dumps(rule(item.get("filter")), sort_keys=True), item)

    plan = []
    for item in sets:
        want = json.dumps(rule(item["filter"]), sort_keys=True)
        current, matched = None, None
        if item["retailer_id"] in by_retailer:
            current, matched = by_retailer[item["retailer_id"]], "retailer_id"
        elif want in by_rule:
            current, matched = by_rule[want], "rule"
        elif item["name"] in by_name:
            current, matched = by_name[item["name"]], "name"

        if current is None:
            plan.append(("create", item, None))
        elif matched == "retailer_id":
            same = json.dumps(rule(current.get("filter")), sort_keys=True) == want \
                and (current.get("name") or "").strip() == item["name"]
            plan.append(("skip" if same else "update", item, current))
        elif matched == "rule":
            plan.append(("skip", item, current))
        else:                                   # our name, someone else's rule
            plan.append(("conflict", item, current))
    return plan


def push(item, catalog, token, version=VERSION, set_id=None, with_metadata=True):
    """Create or update one set. Returns the Graph id of the set."""
    params = {
        "name": item["name"],
        "filter": json.dumps(item["filter"], ensure_ascii=False),
        "retailer_id": item["retailer_id"],
    }
    metadata = item.get("metadata") or {}
    if metadata and with_metadata:
        params["metadata"] = json.dumps(metadata, ensure_ascii=False)
    path = "/%s" % set_id if set_id else "/%s/product_sets" % catalog
    answer = graph(path, params, token, method="POST", version=version)
    return answer.get("id") or set_id or answer.get("success")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    args = sys.argv[1:]
    sets_file, version = SETS_JSON, VERSION
    catalog = os.environ.get("META_CATALOG_ID", "")
    token = os.environ.get("META_TOKEN", "")
    apply_changes = list_only = delete_stale = False
    with_metadata = True
    only = ""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--sets", "--sets-file"):
            index += 1
            sets_file = args[index]
        elif arg in ("--catalog", "--catalog-id"):
            index += 1
            catalog = args[index]
        elif arg == "--token":
            index += 1
            token = args[index]
        elif arg == "--api-version":
            index += 1
            version = args[index]
        elif arg == "--only":
            index += 1
            only = args[index]
        elif arg == "--apply":
            apply_changes = True
        elif arg == "--dry-run":
            apply_changes = False
        elif arg == "--no-metadata":
            with_metadata = False
        elif arg == "--list":
            list_only = True
        elif arg == "--delete-stale":
            delete_stale = True
        else:
            sys.exit("unknown argument: %s" % arg)
        index += 1

    with open(sets_file, encoding="utf-8") as fh:
        planned = json.load(fh)["sets"]
    if only:
        needle = only.lower()
        planned = [item for item in planned
                   if needle in item["name"].lower() or needle in item["retailer_id"]]
    print("  sets file: %s (%d set%s)" % (sets_file, len(planned), "" if len(planned) == 1 else "s"))

    if not catalog or not token:
        print("  catalogue: %s" % (catalog or "not set — META_CATALOG_ID"))
        print("  token: %s" % ("set" if token else "not set — META_TOKEN"))
        print("  plan (no API call, nothing was read or written):")
        for item in planned:
            print("        create  %-26s %3d items  %s" % (
                item["name"], item["items"], json.dumps(item["filter"], ensure_ascii=False)[:64]))
        print("  dry run only. set META_CATALOG_ID and META_TOKEN, then re-run with --apply")
        return

    print("  catalogue: %s   api: %s" % (catalog, version))
    try:
        existing = list_sets(catalog, token, version)
    except GraphError as exc:
        sys.exit("  could not read the catalogue: %s" % exc)
    print("  existing sets in the catalogue: %d" % len(existing))
    for item in existing:
        print("        #%-14s %-26s %4s items  %s" % (
            item.get("id"), (item.get("name") or "")[:26], item.get("product_count"),
            json.dumps(rule(item.get("filter")), ensure_ascii=False)[:56]))
    if list_only:
        return

    plan = plan_for(planned, existing)
    todo = [row for row in plan if row[0] in ("create", "update")]
    clashes = [row for row in plan if row[0] == "conflict"]
    covered = [row for row in plan if row[0] == "skip" and not row[2].get("retailer_id")]
    print("  to create: %d, to update: %d, already correct: %d, conflicts: %d" % (
        sum(1 for row in plan if row[0] == "create"),
        sum(1 for row in plan if row[0] == "update"),
        sum(1 for row in plan if row[0] == "skip"),
        len(clashes)))
    for item in covered:
        print("        note: %s is already covered by set #%s (%s) — left alone" % (
            item["name"], item[1].get("id"), (item[1].get("name") or "")[:30]))
    for item, current in [(row[1], row[2]) for row in clashes]:
        print("        conflict: the name %s is used by set #%s with another rule — "
              "rename one of them" % (item["name"], current.get("id")))
    if not apply_changes:
        for action, item, current in todo:
            print("        %-6s %-26s %s" % (
                action, item["name"], json.dumps(item["filter"], ensure_ascii=False)[:64]))
            if current:
                print("               was: %s" % json.dumps(rule(current.get("filter")), ensure_ascii=False)[:64])
        print("  dry run — add --apply to write these to catalogue %s" % catalog)
        return

    done = failed = 0
    for action, item, current in todo:
        try:
            ident = push(item, catalog, token, version,
                         set_id=current.get("id") if action == "update" else None,
                         with_metadata=with_metadata)
            done += 1
            print("        %-6s %-26s -> %s" % (action, item["name"], ident))
        except GraphError as exc:
            if exc.code == DUPLICATE_CODE:
                done += 1
                print("        exists  %-26s (same filter already in the catalogue)" % item["name"])
                continue
            failed += 1
            print("        FAILED  %-26s %s" % (item["name"], exc))
    print("  written: %d, failed: %d" % (done, failed))
    if failed and with_metadata:
        print("  if the failures mention metadata or the cover image, re-run with --no-metadata")

    if delete_stale:
        keep = {item["retailer_id"] for item in json.load(open(sets_file, encoding="utf-8"))["sets"]}
        stale = [item for item in existing
                 if (item.get("retailer_id") or "").startswith("set_") and item["retailer_id"] not in keep]
        for item in stale:
            try:
                graph("/%s" % item["id"], {}, token, method="DELETE", version=version)
                print("        deleted  %s" % item["name"])
            except GraphError as exc:
                print("        FAILED to delete %s: %s" % (item.get("name"), exc))
        print("  stale sets removed: %d" % len(stale))


if __name__ == "__main__":
    main()
