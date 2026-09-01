#!/bin/zsh
# Create an app from an installed template and monitor it to completion.
# Usage: create-app.sh <org-alias> <template 1zD id> <AppName> [label]
# Run detached for long chains:  nohup zsh create-app.sh ... > run.log 2>&1 &
set -u
ORG=$1; TID=$2; NAME=$3; LABEL=${4:-$3}
export PATH=$HOME/.nvm/versions/node/v22.23.1/bin:$PATH
TMP=$(mktemp -d)
printf '{"templateSourceId":"%s","label":"%s","name":"%s","templateValues":{}}' "$TID" "$LABEL" "$NAME" > $TMP/create.json
APP=$(sf api request rest "/services/data/v67.0/app-framework/apps?" --method POST --body @$TMP/create.json -o $ORG 2>/dev/null \
  | python3 -c "import sys,json; s=sys.stdin.read(); j=json.loads(s[s.index('{'):]); a=j.get('app',j); print(a.get('id') or json.dumps(j))")
echo "app $APP"
case "$APP" in 1zA*) ;; *) echo "create failed: $APP"; exit 1;; esac
for i in $(seq 1 120); do
  ST=$(sf api request rest "/services/data/v67.0/app-framework/apps/$APP?" -o $ORG 2>/dev/null \
    | python3 -c "import sys,json; s=sys.stdin.read(); j=json.loads(s[s.index('{'):]); a=j.get('app',j); print(a.get('applicationStatus'))")
  echo "$(date +%H:%M:%S) $ST"
  case "$ST" in SuccessStatus|FailedStatus) break;; esac
  sleep 60
done
RT=$(sf api request rest "/services/data/v67.0/app-framework/apps/$APP/activities/latest?" -o $ORG 2>/dev/null \
  | python3 -c "import sys,json; s=sys.stdin.read(); j=json.loads(s[s.index('{'):]); print(j['runtimeRequest']['id'])")
sf api request rest "/services/data/v67.0/domino/runtimes/$RT?" -o $ORG 2>/dev/null > $TMP/run.json
python3 - $TMP/run.json <<'PY'
import sys,json,html
s=open(sys.argv[1]).read(); j=json.loads(s[s.index('{'):])
print('FINAL', j.get('requestStatus'), json.dumps(j.get('taskSummary')), 'seconds', j.get('durationInSeconds'))
for ref,n in j['definition']['nodes'].items():
    ex=(n.get('results') or {}).get('execute') or {}
    msg=html.unescape(str(ex.get('statusMessage') or ''))
    if 'dashboard' in ref or 'Failed' in msg: print(ref, ex.get('taskStatus'), '->', msg[:600])
PY
echo "runtime json: $TMP/run.json"
