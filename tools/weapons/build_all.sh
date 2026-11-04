#!/usr/bin/env bash
# Pangea Arena — build the tier-0 weapon pak from scratch (GPLv2+):
#   generate models -> bake textures -> export MD3/.skin -> hands -> flame frames -> icons
#   -> shader script -> content/build/arena-weapons-<sha8>.pk3
# Blender: $BLENDER or ~/opt/blender/blender (4.2 LTS, see docs/weapons/notes.md).
set -euo pipefail
cd "$(dirname "$0")/../.."
BLENDER=${BLENDER:-$HOME/opt/blender/blender}
PAK=content/pangea
LOG=content/build/weapons-log
mkdir -p "$LOG"
rm -rf "$PAK/models" "$PAK/icons" "$PAK/scripts/pangea_weapons.shader" content/build/weapons-meta

python3 tools/md3/test_md3.py

run() {
    local name=$1; shift
    local t0=$SECONDS
    if ! "$BLENDER" -b --factory-startup --python-exit-code 1 -P tools/weapons/run.py -- "$@" \
            > "$LOG/$name.log" 2>&1; then
        tail -40 "$LOG/$name.log"
        echo "FAILED: $name (log: $LOG/$name.log)" >&2
        exit 1
    fi
    grep -E "^(MODEL|HANDS|FX|ICON)" "$LOG/$name.log" || true
    echo "== $name: $((SECONDS - t0)) s"
}

run models model "$PAK"
run hands hands "$PAK"
run fx fx "$PAK"
run icons icons "$PAK"
python3 tools/weapons/pack.py "$PAK" content/build
