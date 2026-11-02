#!/bin/bash
# Stage temporary OpenArena content next to the web build (dev only, nothing is committed).
#   tools/stage-web-openarena.sh [build-web/Release]
# Writes <out>/baseoa -> content/openarena/baseoa (symlink), our QVMs into baseoa/vm,
# and <out>/arena-config.full.json listing every pk3 + vm/*.qvm.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-build-web/Release}
SRC=content/openarena/baseoa
[ -d "$SRC" ] || { echo "no $SRC — see docs/build.md (OpenArena from apt)"; exit 1; }
mkdir -p "$SRC/vm"
cp build-web/Release/baseq3/vm/*.qvm "$SRC/vm/"
ln -sfn "$PWD/$SRC" "$OUT/baseoa"
python3 - "$SRC" "$OUT/arena-config.full.json" <<'PY'
import json, os, sys
src, out = sys.argv[1:]
files = [{"src": f"baseoa/{f}", "dst": "/baseoa"} for f in sorted(os.listdir(src)) if f.endswith(".pk3")]
files += [{"src": f"baseoa/vm/{f}", "dst": "/baseoa/vm"} for f in ("cgame.qvm", "qagame.qvm", "ui.qvm")]
json.dump({"baseoa": {"files": files}}, open(out, "w"), indent=1)
print(f"{out}: {len(files)} files")
PY
