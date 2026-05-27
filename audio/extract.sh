#!/bin/bash
RECORDINGS=/data/recordings
AUDIO=/data/audio
STATUS=/data/status

mkdir -p "$AUDIO" "$STATUS"

declare -A processed

echo "[audio] Watching $RECORDINGS ..."

while true; do
    for f in "$RECORDINGS"/*.mp4; do
        [ -f "$f" ] || continue
        base=$(basename "$f" .mp4)
        [ -n "${processed[$base]}" ] && continue
        processed[$base]=1

        out="$AUDIO/${base}.opus"
        [ -f "$out" ] && continue

        echo "[audio] Extracting: $f"
        touch "$STATUS/${base}.extracting"

        if ffmpeg -y -i "$f" -vn -acodec libopus -ar 16000 -ac 1 "$out" 2>&1; then
            rm -f "$STATUS/${base}.extracting"
            echo "[audio] Done: $out"
        else
            rm -f "$STATUS/${base}.extracting"
            touch "$STATUS/${base}.error"
            echo "[audio] Error: $f"
        fi
    done
    sleep 10
done
