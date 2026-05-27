import asyncio, os, json, subprocess, time, logging, glob
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

TRIGGER_DIR = '/data/trigger'
STATUS_DIR  = '/data/status'
REC_DIR     = '/data/recordings'

for d in (REC_DIR, STATUS_DIR):
    os.makedirs(d, exist_ok=True)


def write_status(task_id, status):
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


async def wait_for_end(page, max_sec=7200):
    end_texts = [
        'text=This meeting has been ended',
        'text=このミーティングは終了',
        'text=The host has ended this meeting',
    ]
    t0 = time.time()
    while time.time() - t0 < max_sec:
        for sel in end_texts:
            try:
                if await page.is_visible(sel, timeout=500):
                    return 'ended'
            except Exception:
                pass
        if page.is_closed():
            return 'closed'
        await asyncio.sleep(15)
    return 'timeout'


async def process_task(task):
    task_id  = str(task['id'])
    zoom_url = task['zoom_url']
    meeting_id = task.get('meeting_id', '')
    password   = task.get('password', '')
    out_mp4    = f'{REC_DIR}/{task_id}.mp4'

    if os.path.exists(out_mp4):
        logging.info(f"Already recorded: {out_mp4}")
        write_status(task_id, 'done')
        return

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
                reason = await wait_for_end(page)
                logging.info(f"Meeting ended: {reason}")
            except Exception as e:
                logging.error(f"Meeting error: {e}")
            finally:
                await browser.close()
    finally:
        ffmpeg_proc.terminate()
        ffmpeg_proc.wait(timeout=10)

    logging.info(f"Saved: {out_mp4}")
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
