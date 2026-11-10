#!/bin/bash
# Render every 1080p scene composition of the 60-second sample.
# Usage: bash studio/render_scenes.sh [output_dir]
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
OUT="${1:-$HERE/remotion/out/sample60}"
LIBS="$REPO/.tools/espeak-root"
export LD_LIBRARY_PATH="$LIBS/usr/lib/x86_64-linux-gnu:$LIBS/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

mkdir -p "$OUT"
cd "$HERE/remotion" || exit 1

SCENES=(S1ColdOpen S2LagoonMap S3Foundations S4Stats S5Mose S6Closing)
for scene in "${SCENES[@]}"; do
  target="$OUT/${scene}.mp4"
  if [ -s "$target" ]; then
    echo "[skip] $scene already rendered"
    continue
  fi
  echo "[render] $scene -> $target"
  npx remotion render src/index.ts "$scene" "$target" \
    --concurrency=2 --log=error || { echo "[FAIL] $scene"; exit 1; }
done
echo "[done] scenes in $OUT"
ls -la "$OUT"
