#!/usr/bin/env python3
"""Print the facts a security reviewer checks, for the reviewer documents.

Usage: audit.py <force-app dir> --namespace <ns> [--json]
"""
import argparse, collections, glob, json, os, re, subprocess, sys

GREPS = {
    "network": r"fetch\(|XMLHttpRequest|WebSocket|EventSource|SharedWorker",
    "dom_string_writes": r"innerHTML|outerHTML|document\.write|insertAdjacentHTML|DOMParser",
    "storage": r"localStorage|sessionStorage|indexedDB|document\.cookie",
    "dynamic_code": r"import\(|<script|eval\(",
    "suppressions": r"eslint-disable|SuppressWarnings",
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("force_app"); ap.add_argument("--namespace", required=True); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(); root = a.force_app.rstrip("/"); d = os.path.join(root, "main", "default")
    out = {"namespace": a.namespace, "templates": [], "lwc": [], "static_resources": [], "other_types": []}
    for t in sorted(glob.glob(os.path.join(d, "appTemplates", "*"))):
        ti = json.load(open(os.path.join(t, "template-info.json")))
        rec = {"name": os.path.basename(t), "label": ti.get("label"), "assetVersion": ti.get("assetVersion"),
               "chainDefinitions_name_null": all(c.get("name") is None for c in ti.get("chainDefinitions") or [])}
        pol = os.path.join(t, "template-policy.json"); rec["template_policy"] = json.load(open(pol)) if os.path.exists(pol) else None
        vp = os.path.join(t, "variables.json"); rec["variables"] = json.load(open(vp)) if os.path.exists(vp) else None
        rec["rules_json"] = os.path.exists(os.path.join(t, "rules.json"))
        for cf in {c.get("file") for c in ti.get("chainDefinitions") or []}:
            c = json.load(open(os.path.join(t, cf))); nodes = c["definition"]["nodes"]
            rec["dominoVariant"] = c.get("dominoVariant")
            rec["node_count"] = len(nodes)
            rec["node_types"] = dict(collections.Counter(n["graphNodeType"]["name"] for n in nodes.values()))
            rec["runAs"] = dict(collections.Counter(((n.get("parameters") or {}).get("runAs") or n.get("runAs")) for n in nodes.values()))
            rec["nodes_missing_minorVersion"] = [k for k, n in nodes.items() if not (n.get("parameters") or {}).get("minorVersion")]
            files = [(n.get("parameters") or {}).get("file") for n in nodes.values() if (n.get("parameters") or {}).get("file")]
            rec["file_refs"] = len(files); rec["traversal_refs"] = [f for f in files if ".." in f]
        alljson = "".join(open(p).read() for p in glob.glob(os.path.join(t, "**", "*.json"), recursive=True))
        rec["any_dotdot_in_json"] = bool(re.search(r'"[^"]*\.\./[^"]*"', alljson))
        rec["dashboards"] = []
        for dp in glob.glob(os.path.join(t, "dashboards", "*.json")):
            dd = json.load(open(dp)); ws = dd.get("widgets") or {}
            rec["dashboards"].append({"file": os.path.basename(dp), "widget_types": dict(collections.Counter(w.get("type") for w in ws.values())),
                "extensions": [{"name": k, "source": w.get("source"), "fqn": (w.get("parameters") or {}).get("fullyQualifiedName")} for k, w in ws.items() if w.get("type") == "extension"]})
        rec["csvs"] = len(glob.glob(os.path.join(t, "csvs", "*")))
        out["templates"].append(rec)
    for l in sorted(glob.glob(os.path.join(d, "lwc", "*"))):
        if not os.path.isdir(l): continue
        rec = {"name": os.path.basename(l), "files": sorted(os.listdir(l)), "greps": {}}
        meta = glob.glob(os.path.join(l, "*.js-meta.xml"))
        if meta:
            m = open(meta[0]).read(); rec["isExposed"] = "<isExposed>true" in m; rec["targets"] = re.findall(r"<target>([^<]+)</target>", m)
            rec["properties"] = re.findall(r'name="([^"]+)"', m)
        src = "".join(open(p).read() for p in glob.glob(os.path.join(l, "*")) if os.path.isfile(p))
        for k, pat in GREPS.items(): rec["greps"][k] = len(re.findall(pat, src))
        rec["uses_resourceUrl"] = "@salesforce/resourceUrl" in src
        out["lwc"].append(rec)
    for s in glob.glob(os.path.join(d, "staticresources", "*.resource-meta.xml")):
        out["static_resources"].append({"name": os.path.basename(s).replace(".resource-meta.xml", ""), "contentType": (re.search(r"<contentType>([^<]+)", open(s).read()) or [None, None])[1]})
    for sub in sorted(os.listdir(d)):
        if sub not in ("appTemplates", "lwc", "staticresources") and os.listdir(os.path.join(d, sub)):
            out["other_types"].append(sub)
    out["metadata_file_count"] = sum(len(f) for _, _, f in os.walk(root))
    if a.json: print(json.dumps(out, indent=1)); return
    for t in out["templates"]:
        print(f"TEMPLATE {t['name']} (label {t['label']}, assetVersion {t['assetVersion']})")
        print(f"  nodes {t.get('node_count')} {t.get('node_types')}")
        print(f"  runAs {t.get('runAs')}  | dominoVariant {t.get('dominoVariant')}")
        print(f"  chainDefinitions name null: {t['chainDefinitions_name_null']} | nodes missing minorVersion: {len(t.get('nodes_missing_minorVersion') or [])}")
        print(f"  file refs {t.get('file_refs')} traversal {t.get('traversal_refs')} any '..' in json: {t['any_dotdot_in_json']}")
        print(f"  template-policy {t['template_policy']} | variables {t['variables']} | rules.json {t['rules_json']} | csvs {t['csvs']}")
        for db in t["dashboards"]:
            print(f"  dashboard {db['file']} widgets {db['widget_types']}")
            for e in db["extensions"]: print(f"    extension {e['name']}: {e['source']} fqn={e['fqn']}")
    for l in out["lwc"]:
        print(f"LWC {l['name']} exposed={l.get('isExposed')} targets={l.get('targets')} props={l.get('properties')} resourceUrl={l['uses_resourceUrl']}")
        print(f"  greps (all should be 0): {l['greps']}")
    print("STATIC RESOURCES", out["static_resources"]); print("OTHER METADATA DIRS", out["other_types"]); print("metadata files", out["metadata_file_count"])

if __name__ == "__main__":
    main()
