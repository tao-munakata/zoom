import os, time, glob, logging
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

AUDIO_DIR      = '/data/audio'
TRANSCRIPT_DIR = '/data/transcripts'
STATUS_DIR     = '/data/status'
MODEL_DIR      = '/data/models'
MODEL_NAME     = os.environ.get('WHISPER_MODEL', 'small')

for d in (TRANSCRIPT_DIR, STATUS_DIR, MODEL_DIR):
    os.makedirs(d, exist_ok=True)

logging.info(f"Loading Whisper model '{MODEL_NAME}' ...")
model = WhisperModel(MODEL_NAME, device='cpu', compute_type='int8', download_root=MODEL_DIR)
logging.info("Model ready")

processed: set = set()


def fmt_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s   = divmod(rem, 60)
    ms     = int((s % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


while True:
    for audio_file in glob.glob(f'{AUDIO_DIR}/*.opus'):
        base = os.path.basename(audio_file).replace('.opus', '')
        if base in processed:
            continue
        txt_out = f'{TRANSCRIPT_DIR}/{base}.txt'
        srt_out = f'{TRANSCRIPT_DIR}/{base}.srt'
        if os.path.exists(txt_out):
            processed.add(base)
            continue

        logging.info(f"Transcribing: {audio_file}")
        open(f'{STATUS_DIR}/{base}.transcribing', 'w').close()

        try:
            segments, _ = model.transcribe(audio_file, language='ja', beam_size=5)

            plain, srt_lines = [], []
            for i, seg in enumerate(segments, 1):
                text = seg.text.strip()
                plain.append(text)
                srt_lines += [str(i), f"{fmt_time(seg.start)} --> {fmt_time(seg.end)}", text, '']

            with open(txt_out, 'w', encoding='utf-8') as f:
                f.write('\n'.join(plain))
            with open(srt_out, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))

            # status: transcribing → done
            try:
                os.remove(f'{STATUS_DIR}/{base}.transcribing')
            except FileNotFoundError:
                pass
            open(f'{STATUS_DIR}/{base}.done', 'w').close()
            logging.info(f"Done: {txt_out}")

        except Exception as e:
            logging.error(f"Transcribe error {base}: {e}")
            open(f'{STATUS_DIR}/{base}.error', 'w').close()

        processed.add(base)

    time.sleep(15)
