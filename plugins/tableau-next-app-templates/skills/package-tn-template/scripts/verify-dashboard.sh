#!/bin/zsh
# Verify every extension widget on a created dashboard resolved to a namespaced LWC.
# Usage: verify-dashboard.sh <org-alias> <dashboard api name or 0Tr id>
set -u
ORG=$1; DASH=$2
export PATH=$HOME/.nvm/versions/node/v22.23.1/bin:$PATH
sf api request rest "/services/data/v67.0/tableau/dashboards/$DASH?" -o $ORG 2>/dev/null > /tmp/vd_dash.json
sf data query -t -q "SELECT Id, DeveloperName, NamespacePrefix FROM LightningComponentBundle" -o $ORG --json 2>/dev/null > /tmp/vd_lwc.json
python3 - <<'PY'
import json
s=open('/tmp/vd_dash.json').read(); d=json.loads(s[s.index('{'):])
s=open('/tmp/vd_lwc.json').read(); lw=json.loads(s[s.index('{'):])['result']['records']
byid={r['Id']:(r['NamespacePrefix'],r['DeveloperName']) for r in lw}
print('dashboard', d.get('id'), d.get('name'))
ok=True
for name,w in d.get('widgets',{}).items():
    if w.get('type')!='extension': continue
    src=w.get('source',{}); fqn=w.get('parameters',{}).get('fullyQualifiedName')
    b=byid.get(src.get('id'))
    line=f"  {name}: status={w.get('status')} name={src.get('name')} ns={src.get('namespace')} fqn={fqn} bundle={b}"
    bad = w.get('status')!='Ok' or not (src.get('name') or '').count(':') or (b and b[0] is None) or src.get('namespace') in (None,'c')
    print(('FAIL ' if bad else 'ok   ')+line); ok = ok and not bad
print('RESULT', 'PASS' if ok else 'FAIL', '(open the dashboard in a browser and check the tile renders)')
PY
