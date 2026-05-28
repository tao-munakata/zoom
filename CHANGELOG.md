# Changelog

## [0.1.5] - 2026-05-28

### Fixed
- `end_at` を絶対時刻で判定するよう変更（処理開始が遅れても正確に止まる）
- 処理開始時に `end_at` が過去ならスキップ
- `process_task` 完了後（`finally`）にトリガーファイルを削除（再起動で古いタスクが再実行されなくなる）

---

## [0.1.4] - 2026-05-28

### Fixed
- **audio race condition**: recorder が FFmpeg 終了後に `{id}.ready` フラグを作成、audio コンテナはフラグがあるものだけ処理（録画中 MP4 の誤読み＝moov atom not found を解消）
- **ステータス誤検知**: `write_status` で書き込み前に同タスクの古いファイルを削除
- **FFmpeg 終了待機**: timeout 10s → 30s に延長、`TimeoutExpired` 時は SIGKILL にフォールバック

---

## [0.1.3] - 2026-05-28

### Fixed
- **録画が1分で終わる**: 参加直後のページタイトル `"Just a moment..."` を終了と誤検知していた → タイトル検知を削除、join 後 90 秒は URL 変化検知もスキップ（`SETTLE_SEC`）
- **フォーム入力が消える**: 30 秒自動リロードがフォーム入力中も発動していた → フォームが空のときだけリロード
- **短い文字列でも登録できる**: `zoom_url` を `type="url"` に変更、案件名に `minlength="2"` を追加

---

## [0.1.2] - 2026-05-28

### Added
- Scheduler UI に「終了日時」入力欄を追加
- DB に `end_at` カラムを追加（既存 DB は `ALTER TABLE` で自動マイグレーション）
- recorder: `end_at` から録画上限秒数を算出（未設定時は 2 時間、上限は 2 時間）

---

## [0.1.1] - 2026-05-28

### Fixed
- 全コンテナ（scheduler / recorder / audio / whisper）に `TZ=Asia/Tokyo` を追加
- `datetime.now()` が UTC を返すため JST で入力したスケジュール時刻と 9 時間ズレていた問題を解消

---

## [0.1.0] - 2026-05-28

### Added
- 初回リリース: Docker コンテナ 4 本（scheduler / recorder / audio / whisper）
- Scheduler Web UI（Flask）: Zoom URL・開始日時・ミーティングID・パスワードを登録
- Recorder: Playwright でヘッドレス Chromium を操作し Zoom に自動参加、FFmpeg で画面録画（MP4）
- Audio: FFmpeg で録画 MP4 から音声を抽出（Opus / 16kHz モノラル）
- Whisper: faster-whisper で文字起こし（`.txt` / `.srt` 出力）
- noVNC でブラウザからヘッドレス画面を確認（port 6080）

### Fixed（初回ビルドエラー修正）
- `whisper/Dockerfile`: `pkg-config`・`build-essential`・`libav*` 追加（PyAV ビルドエラー解消）
- `whisper/requirements.txt`: `faster-whisper` 1.0.1 → 1.2.1
- `recorder/Dockerfile`: `ENV DEBIAN_FRONTEND=noninteractive` 追加（tzdata 対話入力でビルドが停止する問題を解消）
