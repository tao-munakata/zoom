# Architecture

## プロジェクト概要

**名前**: Zoom 自動録画・AI 要約システム（第一段階）
**場所**: `/home/tao/myapp/zoom/`
**目的**: Docker コンテナ群で Zoom の自動参加〜文字起こしを完全ローカルで自動化する

---

## 設計判断

| 項目 | 採用案 | 理由 |
|------|--------|------|
| コンテナ管理 | Docker Compose v2 | 単一ファイルで依存・ボリューム・ネットワークを管理できる |
| 録画ブラウザ | Chromium + Playwright | Selenium より安定した非同期 API、noVNC デバッグが容易 |
| 仮想ディスプレイ | Xvfb | ヘッドレス環境で Chromium を動かす標準的な手段 |
| 音声コーデック | libopus / 16kHz モノラル | Whisper の推奨入力フォーマットと一致 |
| 文字起こし | faster-whisper（CTranslate2） | オリジナル Whisper より 4〜8 倍高速、int8 量子化でメモリ節約 |
| GPU アクセス | /dev/dri パスなし＋QSV | Docker でホスト GPU を共有、Intel VPL/VAAPI 経由 |
| スケジューラ DB | SQLite | 依存なしで軽量、タスク数が少ないため十分 |
| デバッグ UI | noVNC (port 6080) | ブラウザだけで録画状況を確認できる |

---

## コンテナ構成

```
zoom/
├── docker-compose.yml
├── .env                        # ZOOM_EMAIL, ZOOM_PASSWORD, etc.
├── scheduler/
│   ├── Dockerfile
│   ├── main.py                 # タスクキュー・ステータス管理
│   ├── db.py                   # SQLite CRUD
│   └── requirements.txt
├── recorder/
│   ├── Dockerfile
│   ├── entrypoint.sh           # Xvfb + noVNC + Chromium 起動
│   ├── record.py               # Playwright で Zoom に参加・録画
│   └── requirements.txt
├── audio/
│   ├── Dockerfile
│   └── extract.sh              # FFmpeg で音声抽出（録画終了をポーリング検知）
├── whisper/
│   ├── Dockerfile
│   └── transcribe.py           # faster-whisper で文字起こし
└── data/                       # ← /opt/zoom-ai/data にバインドマウント
    ├── recordings/             # MP4 録画ファイル
    ├── audio/                  # .opus 音声ファイル
    └── transcripts/            # .txt / .srt 文字起こし結果
```

**スコープ外（今回は作成しない）:**
- `llm/` コンテナ（第二段階）
- `dashboard/` フロントエンド（第三段階）

---

## データフロー

```
[scheduler] タスク登録（URL/時刻/ID/PW）
    ↓ 指定時刻に起動
[recorder]  Xvfb + Chromium で Zoom 参加 → MP4 録画 → data/recordings/
    ↓ 録画完了イベント（ファイル出現をポーリング）
[audio]     FFmpeg で音声抽出 → data/audio/*.opus
    ↓ 音声ファイル出現をポーリング
[whisper]   faster-whisper で STT → data/transcripts/*.txt + *.srt
    ↓（第一段階ここで終了）
[手動]      担当者が .txt を開きポイントを抽出
```

---

## ボリューム・ネットワーク設計

```yaml
volumes:
  zoom-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/zoom-ai/data

networks:
  zoom-internal:
    driver: bridge
```

- 全コンテナが `zoom-data` を `/data` にマウント
- コンテナ間通信は `zoom-internal` ネットワーク内で完結
- noVNC のみ外部ポート 6080 を公開

---

## ハードウェア最適化

| 項目 | 設定 |
|------|------|
| GPU パススルー | `devices: [/dev/dri:/dev/dri]` を recorder・audio コンテナに追加 |
| FFmpeg エンコード | `-hwaccel qsv` オプションで Intel QSV を使用 |
| Whisper 量子化 | `compute_type="int8"` で RAM 使用量を削減 |
| Whisper モデル | RAM 8GB → `small`、RAM 4GB → `base` |
| メモリ上限 | `deploy.resources.limits.memory` で各コンテナに設定 |

---

## 安定稼働・運用設計

- `restart: unless-stopped` を全コンテナに設定
- ヘルスチェック: recorder コンテナが N 分無応答 → scheduler がアラートログ出力
- ストレージ管理: `find /data/recordings -mtime +7 -delete` を cron or scheduler 内で定期実行
- ログ: `docker logs --tail 100 <container>` で確認できるよう stdout/stderr に出力

---

## 非対象範囲

- Zoom クライアント（ネイティブアプリ）の利用 → Chromium Web クライアントで代替
- Windows / macOS 環境
- 複数 Zoom アカウントの同時録画
- クラウドストレージへの自動アップロード
