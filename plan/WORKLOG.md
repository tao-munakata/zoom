# Worklog

## 2026-05-28

- plan/ を `/home/tao/myapp/zoom/plan/` に新規作成
- 設計書（zoom-auto.txt）を元に TASK.md / ARCHITECTURE.md / IMPLEMENTATION.md を作成
- ステータス: v0.1.0 実装完了（Docker コンテナ 4 本 + Web UI）
- Open Questions を全て確定（RAM: 8GB / Whisper: small / noVNC: 6080 / MP4）
- zoom/plan/ を zoom/ 内に独立配置

## 2026-05-28（ローカル初回起動）

### 実施内容
- `docker compose up --build` を初めて実行 → ビルドエラー 2 件を修正

### 修正 1: whisper/Dockerfile
- エラー: `pkg-config is required for building PyAV` → `gcc` 不足
- 対応: `pkg-config`, `build-essential`, `libavformat-dev` 等を追加
- あわせて `faster-whisper` を `1.0.1` → `1.2.1` に更新

### 修正 2: recorder/Dockerfile
- エラー: `tzdata` のインタラクティブ入力でビルドが停止
- 対応: `ENV DEBIAN_FRONTEND=noninteractive` を追加

### 結果
- 全4コンテナ（scheduler / recorder / audio / whisper）が正常起動
- http://localhost:8080 (Scheduler UI) ✓
- http://localhost:6080 (noVNC) ✓ 動作確認済み

## 2026-05-28（初回録画テスト → タイムゾーンバグ発見）

### 実施内容
- Scheduler UI から Zoom URL を登録（POST /tasks 成功）
- タスク start_at=15:00 を登録したが録画が発火しないことを確認

### 原因
- schedulerコンテナがUTC動作のため、ユーザーが入力したJST 15:00をUTC 15:00（JST翌日0:00）と解釈していた
- `check_tasks()` の `datetime.now()` がUTCを返すため、JST入力値と9時間のズレが発生

### 修正 3: docker-compose.yml — TZ=Asia/Tokyo 追加
- 対象: scheduler / recorder / audio / whisper 全コンテナ
- 全コンテナに `environment: TZ=Asia/Tokyo` を追加
- `docker compose up -d` で再起動、コンテナログのタイムスタンプがJSTに変更されたことを確認

### バージョン
- v0.1.0 → **v0.1.1**
