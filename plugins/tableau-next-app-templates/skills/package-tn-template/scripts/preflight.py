#!/usr/bin/env python3
"""Preflight an AppFrameworkTemplateBundle project for managed packaging.

Usage: preflight.py <force-app dir> --namespace <ns>

Exit 1 if any blocking finding. Prints findings as BLOCK / WARN / OK.
"""
import argparse, glob, json, os, re, sys

BLOCK, WARN, OK = "BLOCK", "WARN", "OK"
findings = []

def add(level, msg):
    findings.append((level, msg))

def load(p):
    with open(p) as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("force_app")
    ap.add_argument("--namespace", required=True)
    a = ap.parse_args()
    ns = a.namespace
    root = a.force_app.rstrip("/")
    default = os.path.join(root, "main", "default")

    # ContentAsset
    if glob.glob(os.path.join(default, "contentassets", "*")):
        add(BLOCK, "contentassets/ present: ContentAsset names are not namespace-rewritten inside template JSON. Use an LWC image widget + StaticResource.")

    # .forceignore
    fi = os.path.join(os.path.dirname(root), ".forceignore")
    if os.path.exists(fi):
        txt = open(fi).read()
        for needle in ("code-analyzer.yml", "CodeAnalyzerReport"):
            if needle not in txt:
                add(WARN, f".forceignore does not exclude {needle}")
    else:
        add(WARN, ".forceignore missing")

    # LWCs present
    lwcs = [os.path.basename(d) for d in glob.glob(os.path.join(default, "lwc", "*")) if os.path.isdir(d)]

    for tdir in glob.glob(os.path.join(default, "appTemplates", "*")):
        tname = os.path.basename(tdir)
        ti_p = os.path.join(tdir, "template-info.json")
        if not os.path.exists(ti_p):
            add(BLOCK, f"{tname}: no template-info.json"); continue
        ti = load(ti_p)
        if ti.get("name") != tname:
            add(WARN, f"{tname}: template-info name '{ti.get('name')}' differs from folder name")
        for cd in ti.get("chainDefinitions") or []:
            if cd.get("name") is not None:
                add(BLOCK, f"{tname}: chainDefinitions[].name must be null (got '{cd.get('name')}') or Create App returns CHAINNOTFOUND")
        asset_v = ti.get("assetVersion")

        # chain
        for chain_file in {cd.get("file") for cd in ti.get("chainDefinitions") or [] if cd.get("file")}:
            cp = os.path.join(tdir, chain_file)
            if not os.path.exists(cp):
                add(BLOCK, f"{tname}: chain file {chain_file} missing"); continue
            c = load(cp)
            nodes = (c.get("definition") or {}).get("nodes") or {}
            bad_runas = [k for k, n in nodes.items() if ((n.get("parameters") or {}).get("runAs") or n.get("runAs")) != "CurrentUser"]
            if bad_runas:
                add(BLOCK, f"{tname}: runAs is not CurrentUser on {bad_runas[:5]}")
            if asset_v and float(asset_v) >= 67:
                missing = [k for k, n in nodes.items() if not (n.get("parameters") or {}).get("minorVersion")]
                if missing:
                    add(BLOCK, f"{tname}: assetVersion {asset_v} but {len(missing)} node(s) lack parameters.minorVersion, e.g. {missing[:3]}")
            for k, n in nodes.items():
                f = (n.get("parameters") or {}).get("file")
                if f and ".." in f:
                    add(BLOCK, f"{tname}: node {k} file ref contains '..': {f}")
            if c.get("dominoVariant", "").startswith("sfdc_internal__"):
                add(WARN, f"{tname}: dominoVariant is {c.get('dominoVariant')} (tooling default; state it in reviewer notes)")

        # every json in bundle: traversal + widgets
        for jp in glob.glob(os.path.join(tdir, "**", "*.json"), recursive=True):
            txt = open(jp).read()
            if re.search(r'"[^"]*\.\./[^"]*"', txt):
                add(BLOCK, f"{tname}: '..' path in {os.path.relpath(jp, tdir)}")
        for dp in glob.glob(os.path.join(tdir, "dashboards", "*.json")):
            d = load(dp)
            for wname, w in (d.get("widgets") or {}).items():
                t = w.get("type")
                if t == "image":
                    add(BLOCK, f"{tname}/{os.path.basename(dp)}: native image widget '{wname}' references ContentAsset '{(w.get('source') or {}).get('name')}'; replace with an LWC extension widget")
                if t == "extension":
                    src = (w.get("source") or {}).get("name", "")
                    fqn = ((w.get("parameters") or {}).get("fullyQualifiedName", ""))
                    nsf = (w.get("source") or {}).get("namespace")
                    for label, val in (("source.name", src), ("parameters.fullyQualifiedName", fqn)):
                        if not val.startswith(ns + ":"):
                            add(BLOCK, f"{tname}/{os.path.basename(dp)}: extension '{wname}' {label} is '{val}', must be '{ns}:<component>'")
                    if nsf != ns:
                        add(BLOCK, f"{tname}/{os.path.basename(dp)}: extension '{wname}' source.namespace is '{nsf}', must be '{ns}'")
                    comp = src.split(":")[-1]
                    if lwcs and comp not in lwcs:
                        add(BLOCK, f"{tname}: extension '{wname}' references LWC '{comp}' which is not under lwc/ (did `sf project delete source` remove it?)")
                    for f in ("id", "status"):
                        if f in w:
                            add(WARN, f"{tname}/{os.path.basename(dp)}: widget '{wname}' carries org-specific '{f}'; strip it")
                    if "id" in (w.get("source") or {}):
                        add(WARN, f"{tname}/{os.path.basename(dp)}: widget '{wname}' source.id is org-specific; strip it")
        # variables / rules
        vp = os.path.join(tdir, "variables.json")
        if os.path.exists(vp) and load(vp):
            add(WARN, f"{tname}: variables.json is non-empty; document each variable's type for the reviewer")
        if os.path.exists(os.path.join(tdir, "rules.json")):
            add(WARN, f"{tname}: rules.json present; document its targets for the reviewer")

    # LWC hygiene
    for lwc in lwcs:
        meta = glob.glob(os.path.join(default, "lwc", lwc, "*.js-meta.xml"))
        if meta:
            m = open(meta[0]).read()
            if "<isExposed>true</isExposed>" not in m:
                add(WARN, f"lwc/{lwc}: isExposed is not true; it will not appear in the dashboard extension picker")
            if "analytics__Dashboard" not in m:
                add(WARN, f"lwc/{lwc}: no analytics__Dashboard target")
        for js in glob.glob(os.path.join(default, "lwc", lwc, "*.js")):
            s = open(js).read()
            if re.search(r"/resource/", s) and "resourceUrl" not in s:
                add(WARN, f"lwc/{lwc}: builds /resource/ URLs at runtime without @salesforce/resourceUrl; the namespace will not be applied")
            if re.search(r"fetch\(|XMLHttpRequest|innerHTML|document\.write|localStorage|eval\(", s):
                add(WARN, f"lwc/{lwc}: contains a pattern reviewers grep for (fetch/XHR/innerHTML/storage/eval)")

    if not findings:
        add(OK, "no findings")
    blocks = 0
    for level, msg in findings:
        print(f"{level:5} {msg}")
        blocks += level == BLOCK
    print(f"\n{blocks} blocking, {sum(1 for l,_ in findings if l==WARN)} warnings")
    sys.exit(1 if blocks else 0)

if __name__ == "__main__":
    main()
