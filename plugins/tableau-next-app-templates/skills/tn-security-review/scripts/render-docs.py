#!/usr/bin/env python3
"""Fill the reviewer document templates and render PDFs with headless Chrome.

Usage:
  render-docs.py --package "XeoMatrix Sales Insights" --namespace xeomatrix \
    --version 04tQQ00000FxUsfYAF --version-label 1.0.0-6 --publisher XeoMatrix \
    --template Sales_Opportunity_Data --lwc xmDashboardImage \
    --static-resource APEX_essential_components --review-org {{YOUR_PUBLISHER_ORG}} \
    --workspace Sales_Opportunity --out docs/security-review [--pdf-only]

Placeholders in templates/*.md: {{PACKAGE}} {{SLUG}} {{NAMESPACE}} {{VERSION_ID}}
{{VERSION_LABEL}} {{PUBLISHER}} {{TEMPLATE}} {{LWC}} {{STATIC_RESOURCE}} {{REVIEW_ORG}}
{{WORKSPACE}} {{DATE}}
"""
import argparse, datetime, glob, html, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(os.path.dirname(HERE), "templates")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CSS = ('<meta charset="utf-8"><style>body{font-family:Helvetica,Arial,sans-serif;font-size:11pt;max-width:820px;margin:36px auto;'
       'line-height:1.45;color:#111}h1{font-size:20pt}h2{font-size:15pt;margin-top:22px}h3{font-size:12.5pt}table{border-collapse:collapse;margin:8px 0}'
       'td,th{border:1px solid #999;padding:4px 8px;vertical-align:top;font-size:10pt}th{background:#eee}code{background:#f2f2f2;padding:1px 3px;font-size:10pt}'
       'pre{background:#f2f2f2;padding:8px;white-space:pre-wrap;font-size:9.5pt}</style>')

def inline(s):
    s = html.escape(s, quote=False); s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s); return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

def md_to_html(md):
    out, lines, i, lst = [], md.split("\n"), 0, [None]
    def close():
        if lst[0]: out.append("</%s>" % lst[0]); lst[0] = None
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            close(); j = i + 1; buf = []
            while j < len(lines) and not lines[j].startswith("```"): buf.append(lines[j]); j += 1
            out.append("<pre>" + html.escape("\n".join(buf)) + "</pre>"); i = j + 1; continue
        if l.startswith("|"):
            close(); rows = []
            while i < len(lines) and lines[i].startswith("|"): rows.append(lines[i]); i += 1
            cells = [[inline(c.strip()) for c in r.strip().strip("|").split("|")] for r in rows if not re.match(r"^\|[\s\-|:]+\|$", r)]
            out.append("<table>" + "".join("<tr>" + "".join(("<th>%s</th>" if ri == 0 else "<td>%s</td>") % c for c in row) + "</tr>" for ri, row in enumerate(cells)) + "</table>"); continue
        m = re.match(r"^(#{1,4})\s+(.*)", l)
        if m: close(); n = len(m.group(1)); out.append("<h%d>%s</h%d>" % (n, inline(m.group(2)), n)); i += 1; continue
        m = re.match(r"^(\d+)\.\s+(.*)", l)
        if m:
            if lst[0] != "ol": close(); out.append("<ol>"); lst[0] = "ol"
            out.append("<li>" + inline(m.group(2)) + "</li>"); i += 1; continue
        m = re.match(r"^[-*]\s+(.*)", l)
        if m:
            if lst[0] != "ul": close(); out.append("<ul>"); lst[0] = "ul"
            out.append("<li>" + inline(m.group(1)) + "</li>"); i += 1; continue
        if not l.strip(): close(); i += 1; continue
        close(); out.append("<p>" + inline(l) + "</p>"); i += 1
    close(); return CSS + "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    for k in ("package", "namespace", "version", "version_label", "publisher", "template", "lwc", "static_resource", "review_org", "workspace"):
        ap.add_argument("--" + k.replace("_", "-"), default="")
    ap.add_argument("--out", required=True); ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]", "", a.package) or "Package"
    subs = {"PACKAGE": a.package, "SLUG": slug, "NAMESPACE": a.namespace, "VERSION_ID": a.version, "VERSION_LABEL": a.version_label,
            "PUBLISHER": a.publisher, "TEMPLATE": a.template, "LWC": a.lwc, "STATIC_RESOURCE": a.static_resource,
            "REVIEW_ORG": a.review_org, "WORKSPACE": a.workspace, "DATE": datetime.date.today().isoformat()}
    if not a.pdf_only:
        for t in glob.glob(os.path.join(TPL, "*.md")):
            s = open(t).read()
            for k, v in subs.items(): s = s.replace("{{%s}}" % k, v)
            left = sorted(set(re.findall(r"{{[A-Z_]+}}", s)))
            name = os.path.basename(t).replace("PKG", slug)
            open(os.path.join(a.out, name), "w").write(s)
            print("wrote", name, ("(unfilled: %s)" % ", ".join(left)) if left else "")
    for md in glob.glob(os.path.join(a.out, "*.md")):
        h = md[:-3] + ".html"; open(h, "w").write(md_to_html(open(md).read()))
        pdf = md[:-3] + ".pdf"
        if os.path.exists(CHROME):
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf=" + pdf, "file://" + os.path.abspath(h)], capture_output=True)
            os.remove(h); print("pdf", os.path.basename(pdf), os.path.getsize(pdf) if os.path.exists(pdf) else "FAILED")
        else:
            print("html", os.path.basename(h), "(Chrome not found; convert manually)")

if __name__ == "__main__":
    main()
