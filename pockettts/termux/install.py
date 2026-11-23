"""Pair with the Android bridge and patch the existing AiPi profile setup."""
import getpass
import re
import shutil
from pathlib import Path

root = Path.home() / "aipi-phone"
bridge = root / "bridge.py"
proxy = root / "kin_profiles.py"
adapter = Path(__file__).with_name("pockettts_adapter.py")
bridge_old = "    start_voice_proxy(voice)"
bridge_new = "    start_voice_proxy(voice, use_pockettts=harley)"
proxy_old = "def start_voice_proxy(voice):"
proxy_new = """from pockettts_adapter import synthesize
import subprocess

def start_voice_proxy(voice, use_pockettts=False):"""
marker = "            request = Request('http://127.0.0.1:8001/v1/audio/speech',"
routing = """            if use_pockettts:
                try:
                    audio, content_type = synthesize(
                        speech.get('input'), speech.get('response_format') or 'mp3')
                except (OSError, ValueError, subprocess.SubprocessError):
                    print('PocketTTS unavailable. Using Piper for this reply.', flush=True)
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(audio)))
                    self.end_headers()
                    self.wfile.write(audio)
                    return
"""


def update(path, contents, mode=None):
    temp = path.with_name(path.name + ".pockettts-new")
    temp.touch(mode=0o600, exist_ok=False)
    try:
        temp.write_text(contents)
        temp.chmod(mode if mode is not None else path.stat().st_mode & 0o777)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    launcher = bridge.read_text()
    source = proxy.read_text()
    if bridge_new not in launcher:
        if launcher.count(bridge_old) != 1 or "harley =" not in launcher:
            raise SystemExit("This bridge.py does not match the installed Kin profiles layout.")
        launcher = launcher.replace(bridge_old, bridge_new, 1)
    if proxy_new not in source:
        if source.count(proxy_old) != 1 or source.count(marker) != 1:
            raise SystemExit("This kin_profiles.py does not match the expected Piper proxy.")
        source = source.replace(proxy_old, proxy_new, 1).replace(marker, routing + marker, 1)
    compile(launcher, str(bridge), "exec")
    compile(source, str(proxy), "exec")
    key = getpass.getpass("Paste the AiPi PocketTTS Bridge pairing key: ").strip()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", key):
        raise SystemExit("Invalid pairing key. No files were changed.")
    for path in (bridge, proxy):
        backup = path.with_name(path.name + ".before-pockettts")
        if not backup.exists():
            shutil.copy2(path, backup)
    update(root / "pockettts_adapter.py", adapter.read_text(), 0o600)
    update(root / "data/pockettts-bridge.key", key + "\n", 0o600)
    update(proxy, source)
    update(bridge, launcher)
    if not shutil.which("ffmpeg"):
        print("Install FFmpeg with pkg install ffmpeg for non-WAV requests.")
    print("Paired. Start the Android bridge, then run bash ~/start-aipi.sh.")


if __name__ == "__main__":
    main()
