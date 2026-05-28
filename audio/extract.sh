#!/bin/bash
RECORDINGS=/data/recordings
AUDIO=/data/audio
STATUS=/data/status

mkdir -p "$AUDIO" "$STATUS"

echo "[audio] Watching $RECORDINGS ..."

while true; do
    # .ready フラグがあるものだけ処理（録画完了を保証）
    for ready in "$RECORDINGS"/*.ready; do
        [ -f "$ready" ] || continue
        base=$(basename "$ready" .ready)
        f="$RECORDINGS/${base}.mp4"
        [ -f "$f" ] || continue

        out="$AUDIO/${base}.opus"
        if [ -f "$out" ]; then
            rm -f "$ready"
            continue
        fi

        echo "[audio] Extracting: $f"
        touch "$STATUS/${base}.extracting"

        if ffmpeg -y -i "$f" -vn -acodec libopus -ar 16000 -ac 1 "$out" 2>&1; then
            rm -f "$STATUS/${base}.extracting"
            rm -f "$ready"
            echo "[audio] Done: $out"
        else
            rm -f "$STATUS/${base}.extracting"
            touch "$STATUS/${base}.error"
            echo "[audio] Error: $f"
        fi
    done
    sleep 10
done
