#!/bin/bash
# Stage the Pangea content pak next to the slim OpenArena pak for the web build (laptop):
#   <out>/slim/arena-pangea-<sha8>.pk3 and arena-config.json listing both paks (dst /baseoa).
# Run after tools/stage-web-slim.sh. Usage: tools/stage-web-pangea.sh [build-web/Release]
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-build-web/Release}
PAK=$(ls content/build/arena-pangea-*.pk3 | head -1)
mkdir -p "$OUT/slim"
rm -f "$OUT/slim"/arena-pangea-*.pk3
cp "$PAK" "$OUT/slim/"
python3 - "$OUT" "$(basename "$PAK")" <<'PY'
import json, sys
out, pak = sys.argv[1:]
cfg_path = f"{out}/arena-config.json"
cfg = json.load(open(cfg_path))
files = [f for f in cfg["baseoa"]["files"] if "arena-pangea-" not in f["src"]]
# keep OpenArena pak first; ours sorts later alphabetically inside the engine anyway
files.insert(1, {"src": f"slim/{pak}", "dst": "/baseoa"})
cfg["baseoa"]["files"] = files
json.dump(cfg, open(cfg_path, "w"), indent=1)
print(f"{cfg_path} += {pak}")
PY
