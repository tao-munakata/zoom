#!/bin/bash
set -e

# PulseAudio (仮想オーディオシンク)
pulseaudio --start --exit-idle-time=-1 --daemon 2>/dev/null || true
sleep 1
pactl load-module module-null-sink sink_name=virtual_sink 2>/dev/null || true
pactl set-default-sink virtual_sink 2>/dev/null || true
echo "[entrypoint] PulseAudio ready"

# Xvfb
Xvfb :99 -screen 0 1920x1080x24 -ac &
export DISPLAY=:99
sleep 2
echo "[entrypoint] Xvfb :99 ready"

# x11vnc (noVNC のバックエンド)
x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever -bg -quiet 2>/dev/null || true
echo "[entrypoint] x11vnc ready"

# noVNC (WebSocket プロキシ)
websockify --web=/usr/share/novnc/ "${NOVNC_PORT:-6080}" localhost:5900 &
echo "[entrypoint] noVNC ready on :${NOVNC_PORT:-6080}"

# Recorder
exec python record.py
