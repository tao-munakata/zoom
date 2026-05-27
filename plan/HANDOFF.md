# Handoff

## ステータス

実装前（Codex 待ち）

## 次アクション

1. Open Questions を解消してから Codex に実装依頼する
   - miniPC の RAM 容量確認 → Whisper モデルサイズ決定
   - Zoom ログイン方式確認 → `.env` の値決定
2. Codex に `plan/IMPLEMENTATION.md` を渡して Step 0〜6 を実行依頼する

## Open Questions（確定済み）

- [x] RAM: 8GB → Whisper `small` モデル
- [x] Zoom ログイン: scheduler Web UI で案件ごとに入力
- [x] noVNC: port 6080
- [x] 録画: MP4
