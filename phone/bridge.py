"""Phone launcher entry point for avatar, voice and chat-image profiles."""
import json
import os
import runpy
from pathlib import Path

from aipi_images import start
from kin_profiles import start_voice_proxy

if __name__ == '__main__':
    folder = Path(__file__).resolve().parent
    profile = json.loads((folder / 'data/kin-profiles.json').read_text())
    kin_id = os.environ['KINDROID_AI_ID']
    harley = kin_id == profile['harley_id']
    voice = profile['harley_voice'] if harley else profile['default_voice']
    start_voice_proxy(voice)
    try:
        start(os.environ['KINDROID_API_KEY'], kin_id, folder / 'data/.config.yaml',
              avatar=b'H' if harley else b'G')
    except (OSError, ValueError) as exc:
        print(f'AiPi display relay could not start: {exc}', flush=True)
    print(f'AiPi profile: {"Harley" if harley else "Gamora"}, Piper voice: {voice}', flush=True)
    runpy.run_path(str(folder / 'bridge.voice.py'), run_name='__main__')
