#!/bin/bash
# Add a finished reel to the posting queue (run on your Mac).
#   ./queue_add.sh <reel-folder> [cover-second]
# e.g. ./queue_add.sh ../content/reels/003-layout-review-02-flexi 1.2
# Copies <folder>/<folder-name>.mp4 as reel.mp4 (remuxed with faststart),
# grabs a cover.jpg from the video, copies <folder>/caption.txt, writes post.json (approved).
set -euo pipefail
cd "$(dirname "$0")"
SRC="${1:?usage: queue_add.sh <reel-folder> [cover-second]}"
AT="${2:-1.2}"
SRC="$(cd "$SRC" && pwd)"; NAME="$(basename "$SRC")"
MP4="$SRC/$NAME.mp4"; CAP="$SRC/caption.txt"
[ -f "$MP4" ] || { echo "missing $MP4"; exit 1; }
[ -f "$CAP" ] || { echo "missing $CAP"; exit 1; }
if ls queue 2>/dev/null | grep -q -- "-$NAME\$"; then echo "$NAME is already queued"; exit 1; fi
mkdir -p queue
LAST=$(ls queue 2>/dev/null | grep -E '^[0-9]{2}-' | sort | tail -1 | cut -c1-2 || true)
NN=$(printf "%02d" $((10#${LAST:-0} + 1)))
DEST="queue/$NN-$NAME"; mkdir -p "$DEST"
ffmpeg -y -loglevel error -i "$MP4" -c copy -movflags +faststart "$DEST/reel.mp4"
ffmpeg -y -loglevel error -ss "$AT" -i "$MP4" -frames:v 1 -q:v 2 "$DEST/cover.jpg"
cp "$CAP" "$DEST/caption.txt"
printf '{\n  "source": "%s",\n  "approved": true\n}\n' "$NAME" > "$DEST/post.json"
echo "queued $DEST ($(du -h "$DEST/reel.mp4" | cut -f1))"
