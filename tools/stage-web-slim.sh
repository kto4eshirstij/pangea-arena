#!/bin/bash
# Stage the slim pak (tools/pk3slim.py output) next to the web build:
#   <out>/slim/arena-oa-<sha8>.pk3, <out>/slim/vm/*.qvm, <out>/arena-config.slim.json
# Writes <out>/arena-config.json (the default of arena.html). Full OpenArena: tools/stage-web-openarena.sh
# + arena.html?config=./arena-config.full.json
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-build-web/Release}
PAK=$(ls content/build/arena-oa-*.pk3 | head -1)
rm -rf "$OUT/slim" && mkdir -p "$OUT/slim/vm"
cp "$PAK" "$OUT/slim/"
cp build-web/Release/baseq3/vm/*.qvm "$OUT/slim/vm/"
python3 - "$OUT" "$(basename "$PAK")" <<'PY'
import json, os, sys
out, pak = sys.argv[1:]
files = [{"src": f"slim/{pak}", "dst": "/baseoa"}] + \
        [{"src": f"slim/vm/{q}", "dst": "/baseoa/vm"} for q in ("cgame.qvm", "qagame.qvm", "ui.qvm")]
for f in files:  # sizes: arena-boot.js shows pak progress against the full total at once
    f["size"] = os.path.getsize(f"{out}/{f['src']}")
json.dump({"baseoa": {"files": files}}, open(f"{out}/arena-config.json", "w"), indent=1)
print(f"{out}/arena-config.json -> {pak}")
PY
