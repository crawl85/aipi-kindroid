"""Send Harley's speech requests to the on-device Android TTS bridge."""
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

KEY_FILE = Path(__file__).resolve().parent / "data/pockettts-bridge.key"
URL = "http://127.0.0.1:8765/speech"
FORMATS = {
    "mp3": ("mp3", "audio/mpeg"),
    "opus": ("opus", "audio/ogg"),
    "aac": ("adts", "audio/aac"),
    "flac": ("flac", "audio/flac"),
    "pcm": ("s16le", "application/octet-stream"),
}


def synthesize(text, output_format):
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValueError("Unsupported speech input")
    if output_format != "wav" and output_format not in FORMATS:
        raise ValueError("Unsupported audio format")
    key = KEY_FILE.read_text().strip()
    if not key:
        raise ValueError("Missing pairing key")
    request = Request(URL, text.encode("utf-8"), {
        "Authorization": f"Bearer {key}",
        "Content-Type": "text/plain; charset=utf-8",
    })
    with urlopen(request, timeout=23) as response:
        wav = response.read(8_000_001)
    if len(wav) > 8_000_000 or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        raise ValueError("Invalid WAV from PocketTTS")
    if output_format == "wav":
        return wav, "audio/wav"
    codec_format, mime_type = FORMATS[output_format]
    options = ["-ar", "24000", "-ac", "1"] if output_format == "pcm" else []
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         *options, "-f", codec_format, "pipe:1"],
        input=wav, capture_output=True, check=True, timeout=10,
    )
    return result.stdout, mime_type
