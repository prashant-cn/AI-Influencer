import os
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -----------------------
# CONFIG
# -----------------------
DOWNLOADS_DIR = "downloads/financewithanubhav_"
WHISPER_MODEL = "small"   # tiny / base / small / medium / large-v3
DEVICE = "cpu"            # "cuda" if GPU available
COMPUTE_TYPE = "int8"     # int8 for CPU, float16 for GPU
CONVERT_TO_HINGLISH = False


# -----------------------
# Extract Audio
# -----------------------
def extract_audio(video_path):
    audio_path = video_path.with_suffix(".wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path)
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path


# -----------------------
# Convert Hindi → Hinglish
# -----------------------
def convert_to_hinglish(text):
    try:
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        return text


# -----------------------
# Transcribe
# -----------------------
def transcribe(audio_path, model):
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        language="hi"
    )


    full_text = " ".join(segment.text for segment in segments)

    if CONVERT_TO_HINGLISH:
        full_text = convert_to_hinglish(full_text)

    return full_text.strip()


# -----------------------
# Save Script
# -----------------------
def save_text(video_path, text):
    script_path = video_path.parent / f"script_{video_path.stem}.txt"

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ Saved: {script_path.name}")


# -----------------------
# Main
# -----------------------
def main():
    downloads = Path(DOWNLOADS_DIR)

    videos = list(downloads.glob("*.mp4"))
    if not videos:
        print("⚠ No videos found.")
        return

    print("🔍 Loading Faster Whisper model...")
    model = WhisperModel(
        WHISPER_MODEL,
        device=DEVICE,
        compute_type=COMPUTE_TYPE
    )

    for video in videos:
        script_file = video.parent / f"script_{video.stem}.txt"

        if script_file.exists():
            print(f"⏭ Skipping {video.name}")
            continue

        print(f"\n🎬 Processing {video.name}")

        audio = extract_audio(video)
        text = transcribe(audio, model)
        save_text(video, text)

        if os.path.exists(audio):
            os.remove(audio)

    print("\n🎉 Done processing all reels!")


if __name__ == "__main__":
    main()
