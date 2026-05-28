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

**⚠️ 方式変更を検討中（2026-05-28）**

Playwright によるブラウザ自動操作は不安定なため、方式変更を予定。

### これまでに確認できた問題点
1. Zoom 終了検知が不安定（テキスト・URL・タイトル どれも信頼性低）
2. end_at タイミングのズレ（トリガーが古くなる問題）
3. audio race condition（録画中 MP4 を読んで moov atom エラー）
4. 古いトリガーファイルの再実行
5. フォームの UX（リロードによる入力消失）

### 方式変更の方向性（検討事項）
- Zoom SDK / Zoom Apps を使う
- または ffmpeg の直接スケジューリング（`at` コマンド等）で Playwright を排除
- または OBS + Zoom の組み合わせ

### 現在のコード状態
- v0.1.5 まで修正済み、GitHub にプッシュ済み
- 動作はするが本番運用には不安定

## Open Questions（確定済み）

- [x] RAM: 8GB → Whisper `small` モデル
- [x] Zoom ログイン: scheduler Web UI で案件ごとに入力
- [x] noVNC: port 6080
- [x] 録画: MP4
