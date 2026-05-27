# Task

## Summary

- Task name: Zoom 自動録画・AI 要約システム — 第一段階（録画〜文字起こし）
- Requested by: tao
- Owner: Codex
- Status: planning
- 設計書: `/home/tao/Desktop/zoom-auto.txt`（v1.0）

## Goal

Docker コンテナ群で Zoom 会議の自動参加・録画・音声抽出・文字起こしパイプラインを構築する。
第一段階ではポイント抽出（Step 5）は手動とし、Step 1〜4 の安定稼働を目標とする。

プロジェクトパス: `/home/tao/myapp/zoom/`

## Background

- Ubuntu 24.04 LTS の常時起動型 miniPC（Intel N100 / i5）で動作
- クラウド API 不使用：ランニングコスト削減・データプライバシー確保
- 各処理をコンテナ単位で分離し、共有ボリューム経由でデータを受け渡す
- LLM 自動要約（Step 5）は第二段階以降で実装予定

## Done When（第一段階）

- [ ] `docker compose up` で全コンテナが起動する
- [ ] Zoom URL を登録するとスケジューラが指定時刻に自動録画を開始する
- [ ] 録画終了後に FFmpeg が音声（.opus / 16kHz モノラル）を自動抽出する
- [ ] Whisper（faster-whisper）が文字起こし .txt/.srt を出力する
- [ ] noVNC でブラウザからヘッドレス画面を確認できる
- [ ] `restart: unless-stopped` でコンテナが自動復帰する
- [ ] 7日超の録画ファイルが自動削除される

## Non Goals（第一段階）

- LLM コンテナ（llm）の稼働
- React/Flask ダッシュボードの実装
- Gmail/Slack 通知連携
- Obsidian / Notion 出力連携
- 第二〜四段階の全機能

## Inputs

- 設計書: `/home/tao/Desktop/zoom-auto.txt`
- ハードウェア: Intel N100 または i5 miniPC（/dev/dri 利用可能想定）
- ストレージマウント先: `/opt/zoom-ai/data`（ホスト）

## Open Questions（確定済み）

- [x] miniPC の RAM → 8GB 以上 → Whisper モデル: `small`
- [x] Zoom ログイン方式 → Web UI（scheduler）で URL・開始時刻・ID・PW を案件ごとに入力
- [x] noVNC ポート → 6080
- [x] 録画フォーマット → MP4
