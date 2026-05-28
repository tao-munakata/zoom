import asyncio, os, json, subprocess, time, logging, glob
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

TRIGGER_DIR = '/data/trigger'
STATUS_DIR  = '/data/status'
REC_DIR     = '/data/recordings'

for d in (REC_DIR, STATUS_DIR):
    os.makedirs(d, exist_ok=True)


def write_status(task_id, status):
    # 同タスクの古いステータスファイルを削除してから書く
    for old in Path(STATUS_DIR).glob(f'{task_id}.*'):
        old.unlink(missing_ok=True)
    Path(f'{STATUS_DIR}/{task_id}.{status}').touch()


async def join_zoom(page, zoom_url, meeting_id, password):
    logging.info(f"Goto: {zoom_url}")
    await page.goto(zoom_url, wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(3)

    # "Join from your Browser" を探す
    for sel in [
        'a[href*="wc/join"]',
        'a:has-text("Join from your Browser")',
        'a:has-text("ブラウザから参加")',
        '#btnJoinByBrowser',
    ]:
        try:
            await page.click(sel, timeout=3000)
            await asyncio.sleep(2)
            break
        except Exception:
            pass

    # 名前入力
    for sel in ['#input-for-name', 'input[placeholder="Your Name"]', 'input[autocomplete="name"]']:
        try:
            if await page.is_visible(sel, timeout=5000):
                await page.fill(sel, 'Auto Recorder')
                break
        except Exception:
            pass

    # パスワード入力
    if password:
        for sel in ['#input-for-pwd', 'input[type="password"]']:
            try:
                if await page.is_visible(sel, timeout=3000):
                    await page.fill(sel, password)
                    break
            except Exception:
                pass

    # 参加ボタン
    for sel in [
        'button.preview-join-button',
        'button:has-text("Join")',
        'button:has-text("参加")',
        '#btnJoin',
    ]:
        try:
            await page.click(sel, timeout=3000)
            break
        except Exception:
            pass

    # オーディオダイアログ
    await asyncio.sleep(4)
    for sel in [
        'button:has-text("Join Audio by Computer")',
        'button:has-text("コンピューターでオーディオに参加")',
        '.join-audio-by-voip__join-btn',
    ]:
        try:
            await page.click(sel, timeout=3000)
            break
        except Exception:
            pass

    logging.info("Joined (or joining)")


SETTLE_SEC = 90  # 参加直後の読み込み待機時間（この間はURL/title検知しない）

async def wait_for_end(page, max_sec=7200):
    end_texts = [
        # ホストが終了
        'text=This meeting has been ended',
        'text=The host has ended this meeting',
        'text=このミーティングは終了',
        'text=ミーティングは終了しました',
        'text=ホストがミーティングを終了しました',
        # 自分が退出
        'text=You have left the meeting',
        'text=あなたはこのミーティングから退出しました',
        'text=ミーティングから退出しました',
        # 参加前にすでに終了していた
        'text=This meeting is not currently available',
        'text=This meeting has ended',
        'text=Meeting Ended',
        'text=このミーティングは現在ご利用いただけません',
    ]
    t0 = time.time()
    while time.time() - t0 < max_sec:
        if page.is_closed():
            return 'closed'
        # テキスト検知（常時）
        for sel in end_texts:
            try:
                if await page.is_visible(sel, timeout=300):
                    return 'ended'
            except Exception:
                pass
        # URL変化検知（参加直後SETTLE_SEC秒は読み込み中のため無視）
        elapsed = time.time() - t0
        if elapsed > SETTLE_SEC:
            try:
                url = page.url
                if url and 'zoom.us/wc/' not in url and 'zoom.us/j/' not in url:
                    logging.info(f"URL changed to: {url}")
                    return 'redirected'
            except Exception:
                pass
        await asyncio.sleep(5)
    return 'timeout'


MAX_RECORD_SEC = 7200  # 最大録画時間: 2時間

def calc_max_sec(task):
    """end_at が設定されていれば残り秒数、なければ MAX_RECORD_SEC を返す（上限は MAX_RECORD_SEC）"""
    end_at_str = task.get('end_at', '')
    if end_at_str:
        try:
            end_at = datetime.fromisoformat(end_at_str)
            remaining = (end_at - datetime.now()).total_seconds()
            return max(60, min(remaining, MAX_RECORD_SEC))
        except ValueError:
            pass
    return MAX_RECORD_SEC


async def process_task(task):
    task_id  = str(task['id'])
    zoom_url = task['zoom_url']
    meeting_id = task.get('meeting_id', '')
    password   = task.get('password', '')
    out_mp4    = f'{REC_DIR}/{task_id}.mp4'
    max_sec    = calc_max_sec(task)

    if os.path.exists(out_mp4):
        logging.info(f"Already recorded: {out_mp4}")
        write_status(task_id, 'done')
        return

    logging.info(f"Max recording time: {int(max_sec)}s ({max_sec/60:.0f}min)")
    write_status(task_id, 'recording')

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-f', 'x11grab', '-video_size', '1920x1080', '-framerate', '15', '-i', ':99',
        '-f', 'pulse', '-i', 'virtual_sink.monitor',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
        '-c:a', 'aac', '-b:a', '64k',
        out_mp4,
    ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logging.info(f"Recording: {out_mp4}")

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream',
                '--autoplay-policy=no-user-gesture-required',
            ])
            ctx  = await browser.new_context(permissions=['microphone', 'camera'])
            page = await ctx.new_page()
            try:
                await join_zoom(page, zoom_url, meeting_id, password)
                reason = await wait_for_end(page, max_sec=max_sec)
                logging.info(f"Meeting ended: {reason}")
            except Exception as e:
                logging.error(f"Meeting error: {e}")
            finally:
                await browser.close()
    finally:
        ffmpeg_proc.terminate()
        try:
            ffmpeg_proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            logging.warning("FFmpeg did not exit in time, killing")
            ffmpeg_proc.kill()
            ffmpeg_proc.wait()

    logging.info(f"Saved: {out_mp4}")
    # audio コンテナへの完了通知（race condition 防止）
    Path(f'{REC_DIR}/{task_id}.ready').touch()
    write_status(task_id, 'done')


async def main():
    processed: set = set()
    logging.info("Recorder watching /data/trigger/ ...")
    while True:
        for tf in glob.glob(f'{TRIGGER_DIR}/*.json'):
            tid = os.path.basename(tf).replace('.json', '')
            if tid in processed:
                continue
            processed.add(tid)
            try:
                with open(tf) as f:
                    task = json.load(f)
                logging.info(f"Task {tid}: {task.get('title','')}")
                await process_task(task)
            except Exception as e:
                logging.error(f"Task {tid} error: {e}")
                write_status(tid, 'error')
        await asyncio.sleep(10)


if __name__ == '__main__':
    asyncio.run(main())
