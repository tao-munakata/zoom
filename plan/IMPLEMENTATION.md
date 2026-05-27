# Implementation

Codex はこの手順を上から順に実行すること。
各ステップ完了後に `plan/WORKLOG.md` に記録すること。

---

## 前提確認（作業開始前に必ず確認）

```bash
# GPU デバイスの存在確認
ls /dev/dri/

# Docker・Docker Compose のバージョン確認
docker --version
docker compose version

# ホストのデータディレクトリ作成
sudo mkdir -p /opt/zoom-ai/data/recordings
sudo mkdir -p /opt/zoom-ai/data/audio
sudo mkdir -p /opt/zoom-ai/data/transcripts
sudo chown -R $USER:$USER /opt/zoom-ai/data
```

---

## Step 0: プロジェクト基盤

### 0-1. ディレクトリ構造の作成

```bash
cd /home/tao/myapp/zoom
mkdir -p scheduler recorder audio whisper data
```

### 0-2. `.env` ファイルの作成

```
ZOOM_EMAIL=your@email.com
ZOOM_PASSWORD=yourpassword
ZOOM_MEETING_ID=
ZOOM_MEETING_PW=
NOVNC_PORT=6080
DATA_DIR=/opt/zoom-ai/data
WHISPER_MODEL=small
```

> Open Question: Zoom ログイン方式が確定してから値を埋める

---

## Step 1: scheduler コンテナ

### 1-1. `scheduler/requirements.txt`

```
schedule==1.2.1
```

### 1-2. `scheduler/db.py`

SQLite でタスクを管理する CRUD モジュール。

テーブル定義:
```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zoom_url TEXT NOT NULL,
    meeting_id TEXT,
    password TEXT,
    start_at TEXT NOT NULL,          -- ISO 8601
    status TEXT DEFAULT 'pending',   -- pending / running / done / error
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

必要な関数:
- `create_task(zoom_url, meeting_id, password, start_at) -> int`
- `get_pending_tasks() -> list[dict]`
- `update_status(task_id, status)`

### 1-3. `scheduler/main.py`

- 起動時に `db.py` でテーブル初期化
- 毎分 `get_pending_tasks()` をポーリング
- `start_at` が現在時刻から 1 分以内のタスクを `running` に更新し、recorder コンテナへシグナル送信
  - シグナル方法: `/data/trigger/{task_id}.json` にタスク情報を書き込む
- 7日超の録画ファイル削除を毎日 0:00 に実行

### 1-4. `scheduler/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## Step 2: recorder コンテナ

### 2-1. `recorder/requirements.txt`

```
playwright==1.44.0
```

### 2-2. `recorder/entrypoint.sh`

1. Xvfb を `:99` で起動（`1920x1080x24`）
2. noVNC を起動（ポート `$NOVNC_PORT`、パスワードなし）
3. `record.py` を実行

### 2-3. `recorder/record.py`

- `/data/trigger/` を監視し、新しい `.json` が出現したら処理開始
- Playwright で Chromium を起動（`DISPLAY=:99`）
- `zoom_url` を開き、Zoom Web クライアントに接続
  - 「ミーティングに参加」ボタンをクリック
  - マイク・カメラ OFF で参加
- `ffmpeg` をサブプロセスで起動し、仮想ディスプレイを MP4 録画
  ```bash
  ffmpeg -f x11grab -video_size 1920x1080 -i :99 \
    -c:v libx264 -preset ultrafast \
    /data/recordings/{task_id}.mp4
  ```
- Zoom 終了（参加者 0 or タイムアウト）を検知したら ffmpeg を停止
- `/data/trigger/{task_id}.json` に `status: done` を書き込む

### 2-4. `recorder/Dockerfile`

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
RUN apt-get update && apt-get install -y \
    xvfb x11vnc novnc ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
COPY . .
ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
```

---

## Step 3: audio コンテナ

### 3-1. `audio/extract.sh`

- `/data/recordings/` を監視（inotifywait または 10 秒ポーリング）
- 新しい `.mp4` が出現したら FFmpeg で音声抽出:
  ```bash
  ffmpeg -hwaccel qsv \
    -i /data/recordings/${BASENAME}.mp4 \
    -vn -acodec libopus -ar 16000 -ac 1 \
    /data/audio/${BASENAME}.opus
  ```
  > QSV が使えない場合は `-hwaccel qsv` を省いてフォールバック
- 抽出完了後に `/data/audio/${BASENAME}.done` を作成

### 3-2. `audio/Dockerfile`

```dockerfile
FROM jrottenberg/ffmpeg:6-ubuntu
RUN apt-get update && apt-get install -y inotify-tools && rm -rf /var/lib/apt/lists/*
COPY extract.sh /extract.sh
RUN chmod +x /extract.sh
CMD ["/extract.sh"]
```

---

## Step 4: whisper コンテナ

### 4-1. `whisper/requirements.txt`

```
faster-whisper==1.0.3
```

### 4-2. `whisper/transcribe.py`

- `/data/audio/` を監視し、新しい `.opus` が出現したら処理
- faster-whisper でテキスト変換:
  ```python
  from faster_whisper import WhisperModel
  model = WhisperModel(
      os.environ.get("WHISPER_MODEL", "small"),
      device="cpu",
      compute_type="int8"
  )
  segments, info = model.transcribe(audio_path, language="ja")
  ```
- `.txt`（プレーンテキスト）と `.srt`（タイムスタンプ付き）を `/data/transcripts/` に出力
- OpenVINO が使える場合は `device="auto"` にフォールバック可

### 4-3. `whisper/Dockerfile`

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "transcribe.py"]
```

---

## Step 5: docker-compose.yml

```yaml
services:
  scheduler:
    build: ./scheduler
    restart: unless-stopped
    volumes:
      - zoom-data:/data
    networks:
      - zoom-internal

  recorder:
    build: ./recorder
    restart: unless-stopped
    volumes:
      - zoom-data:/data
    devices:
      - /dev/dri:/dev/dri
    ports:
      - "${NOVNC_PORT:-6080}:6080"
    networks:
      - zoom-internal
    environment:
      - DISPLAY=:99
      - ZOOM_EMAIL=${ZOOM_EMAIL}
      - ZOOM_PASSWORD=${ZOOM_PASSWORD}
    deploy:
      resources:
        limits:
          memory: 2g

  audio:
    build: ./audio
    restart: unless-stopped
    volumes:
      - zoom-data:/data
    devices:
      - /dev/dri:/dev/dri
    networks:
      - zoom-internal
    deploy:
      resources:
        limits:
          memory: 512m

  whisper:
    build: ./whisper
    restart: unless-stopped
    volumes:
      - zoom-data:/data
    networks:
      - zoom-internal
    environment:
      - WHISPER_MODEL=${WHISPER_MODEL:-small}
    deploy:
      resources:
        limits:
          memory: 3g

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

---

## Step 6: 動作確認手順

```bash
# 1. ビルド
cd /home/tao/myapp/zoom
docker compose build

# 2. 起動
docker compose up -d

# 3. ログ確認
docker compose logs -f scheduler
docker compose logs -f recorder

# 4. noVNC でブラウザ確認
# http://localhost:6080

# 5. テスト用タスクを手動で scheduler DB に登録
docker compose exec scheduler python -c "
from db import create_task
from datetime import datetime, timedelta
start = (datetime.now() + timedelta(minutes=2)).isoformat()
create_task('https://zoom.us/j/TEST', 'TEST', '', start)
print('Task created')
"

# 6. 出力確認
ls /opt/zoom-ai/data/recordings/
ls /opt/zoom-ai/data/audio/
ls /opt/zoom-ai/data/transcripts/
```

---

## Rollback 方針

```bash
# 全コンテナ停止
docker compose down

# データは保持される（/opt/zoom-ai/data は手動削除が必要）
# コードは git で元に戻せる
git checkout -- .
```

---

## 完了報告

実装完了後、`plan/HANDOFF.md` に以下を記録すること:
- 各ステップの完了確認結果
- 動作確認で発見した問題と対処
- Open Questions への回答（判明したもの）
- 第二段階（LLM コンテナ追加）への推奨事項
