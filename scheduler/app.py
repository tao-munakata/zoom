import os, json, threading, time, logging, glob, subprocess
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import schedule
from db import init_db, create_task, get_all_tasks, get_pending_tasks, update_status, delete_task

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

TRIGGER_DIR = '/data/trigger'
STATUS_DIR  = '/data/status'
for d in (TRIGGER_DIR, STATUS_DIR):
    os.makedirs(d, exist_ok=True)


# ─── スケジューラジョブ ───────────────────────────────────────

def check_tasks():
    """pending タスクの開始時刻が 1 分以内ならトリガーファイルを作成"""
    now = datetime.now()
    for task in get_pending_tasks():
        try:
            start = datetime.fromisoformat(task['start_at'])
        except ValueError:
            continue
        diff = (start - now).total_seconds()
        if -60 <= diff <= 60:
            logging.info(f"Triggering task {task['id']}: {task['title']}")
            update_status(task['id'], 'running')
            trigger_path = os.path.join(TRIGGER_DIR, f"{task['id']}.json")
            with open(trigger_path, 'w') as f:
                json.dump(task, f)


def check_status_files():
    """recorder/whisper が書いたステータスファイルを読んで DB を更新"""
    for fname in os.listdir(STATUS_DIR):
        parts = fname.rsplit('.', 1)
        if len(parts) != 2:
            continue
        task_id_str, new_status = parts
        if not task_id_str.isdigit():
            continue
        task_id = int(task_id_str)
        logging.info(f"Status: task {task_id} → {new_status}")
        update_status(task_id, new_status)
        try:
            os.remove(os.path.join(STATUS_DIR, fname))
        except FileNotFoundError:
            pass


def cleanup_old_files():
    for d in ('/data/recordings', '/data/audio'):
        subprocess.run(['find', d, '-mtime', '+7', '-name', '*.mp4', '-delete'], check=False)
        subprocess.run(['find', d, '-mtime', '+7', '-name', '*.opus', '-delete'], check=False)


schedule.every(1).minutes.do(check_tasks)
schedule.every(10).seconds.do(check_status_files)
schedule.every().day.at("00:00").do(cleanup_old_files)


def scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(5)


# ─── Flask ルート ────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', tasks=get_all_tasks())


@app.route('/tasks', methods=['POST'])
def add_task():
    create_task(
        request.form['title'],
        request.form['zoom_url'],
        request.form.get('meeting_id', ''),
        request.form.get('password', ''),
        request.form['start_at'],
    )
    return redirect(url_for('index'))


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def remove_task(task_id):
    delete_task(task_id)
    return redirect(url_for('index'))


@app.route('/transcripts/<int:task_id>')
def view_transcript(task_id):
    files = glob.glob(f'/data/transcripts/{task_id}.txt')
    if not files:
        return "<p>文字起こしファイルが見つかりません</p>", 404
    with open(files[0], encoding='utf-8') as f:
        content = f.read()
    return (
        f'<!doctype html><html><head><meta charset="utf-8">'
        f'<title>文字起こし #{task_id}</title></head>'
        f'<body><pre style="white-space:pre-wrap;padding:20px;font-size:14px">'
        f'{content}</pre></body></html>'
    )


if __name__ == '__main__':
    init_db()
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=8080, use_reloader=False)
