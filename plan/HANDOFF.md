# Handoff

## ステータス

**ローカル動作確認済み（2026-05-28）**

## 確認済み事項

- `docker compose up --build` でビルド・起動が通ることを確認
- http://localhost:8080 (Scheduler UI) 動作確認済み
- http://localhost:6080 (noVNC) 動作確認済み

## 修正済みファイル

| ファイル | 修正内容 |
|---|---|
| `whisper/Dockerfile` | `pkg-config`, `build-essential`, `libav*` 追加 |
| `whisper/requirements.txt` | `faster-whisper` 1.0.1 → 1.2.1 |
| `recorder/Dockerfile` | `ENV DEBIAN_FRONTEND=noninteractive` 追加 |

## 次アクション

1. Scheduler UI (http://localhost:8080) から Zoom 案件を登録してテスト録画
2. 録画ファイルが `~/zoom-data/recordings/` に保存されることを確認
3. Whisper 文字起こしが `~/zoom-data/transcripts/` に出力されることを確認

## Open Questions（確定済み）

- [x] RAM: 8GB → Whisper `small` モデル
- [x] Zoom ログイン: scheduler Web UI で案件ごとに入力
- [x] noVNC: port 6080
- [x] 録画: MP4
