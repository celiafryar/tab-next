#!/bin/zsh
# Code Analyzer scan + Checkmarx MDAPI zip for a Salesforce DX project.
# Usage: scan.sh <project dir> [package-slug] [version-label]
set -u
PROJ=${1:?project dir}; SLUG=${2:-Package}; VER=${3:-current}
export PATH=$HOME/.nvm/versions/node/v22.23.1/bin:$PATH
cd "$PROJ"
sf plugins 2>/dev/null | grep -q code-analyzer || sf plugins install code-analyzer
[ -f code-analyzer.yml ] || printf 'engines:\n  flow:\n    disable_engine: true\n' > code-analyzer.yml
grep -q code-analyzer.yml .forceignore 2>/dev/null || printf '\n# security-scan tooling (never package)\ncode-analyzer.yml\nCodeAnalyzerReport.html\nCodeAnalyzerReport.json\n**/CodeAnalyzerReport.html\n' >> .forceignore
mkdir -p docs/security-review
echo "== Code Analyzer =="
sf code-analyzer run --rule-selector AppExchange --rule-selector Recommended:Security --config-file code-analyzer.yml --target force-app \
  --output-file docs/security-review/CodeAnalyzerReport.html --output-file docs/security-review/CodeAnalyzerReport.json 2>&1 | grep -E "Found|violations|Executed|Error"
echo "== MDAPI conversion =="
OUT=$(mktemp -d)/${SLUG}-mdapi
sf project convert source --root-dir force-app --output-dir "$OUT" 2>&1 | grep -v -i "warning: @salesforce" | tail -1
cat "$OUT/package.xml"
ZIP=~/Downloads/${SLUG}-Managed-${VER}-mdapi.zip
rm -f "$ZIP"; (cd "$(dirname "$OUT")" && zip -qr "$ZIP" "$(basename "$OUT")")
echo "== zip =="; unzip -l "$ZIP" | head -4; ls -la "$ZIP"
echo "metadata files in force-app: $(find force-app -type f | wc -l | tr -d ' ')"
