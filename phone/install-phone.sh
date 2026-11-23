#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
package="$(cd -- "$(dirname -- "$0")" && pwd)"
python - "$package" <<'PY'
from pathlib import Path
import json
import re
import shutil
import sys

package = Path(sys.argv[1])
project = Path.home() / 'aipi-phone'
data = project / 'data'
config = data / '.config.yaml'
bridge = project / 'bridge.py'
voice_backup = project / 'bridge.voice.py'
config_backup = data / '.config.before-kin-profiles.yaml'
bridge_backup = project / 'bridge.before-kin-profiles.py'
images = project / 'aipi_images.py'
images_backup = project / 'aipi_images.before-kin-profiles.py'
if not config.is_file() or not bridge.is_file():
    raise SystemExit('The working aipi-phone config and bridge are required.')
text = config.read_text()
endpoint = re.compile(r"""(?m)^(\s*api_url:[ \t]*['"]?http://127\.0\.0\.1:)800[12](/v1/audio/speech['"]?[ \t]*)(?=\r?$)""")
updated, count = endpoint.subn(r'\g<1>8002\2', text)
if count != 1:
    raise SystemExit('Expected one local Piper api_url on port 8001 or 8002. No changes made.')
with open('/dev/tty') as tty:
    def ask(prompt):
        print(prompt, end='', flush=True)
        return tty.readline().strip()
    kin_id = ask('Harley Kindroid ID: ')
    if not kin_id:
        raise SystemExit('No Harley ID entered. No changes made.')
    default_voice = ask('Gamora Piper voice [alloy]: ') or 'alloy'
    harley_voice = ask('Harley Piper voice [nova]: ') or 'nova'
if not all(re.fullmatch(r'[A-Za-z0-9_-]+', voice) for voice in (default_voice, harley_voice)):
    raise SystemExit('Piper aliases may use letters, numbers, hyphens and underscores.')
if not voice_backup.exists():
    shutil.copy2(bridge, voice_backup)
if not bridge_backup.exists():
    shutil.copy2(bridge, bridge_backup)
if images.exists() and not images_backup.exists() and not config_backup.exists():
    shutil.copy2(images, images_backup)
if not config_backup.exists():
    shutil.copy2(config, config_backup)
def write_file(path, content):
    temp = path.with_name('.' + path.name + '.new')
    temp.write_bytes(content)
    temp.replace(path)
for name in ('aipi_images.py', 'kin_profiles.py'):
    write_file(project / name, (package / name).read_bytes())
write_file(data / 'kin-profiles.json', json.dumps(
    {'harley_id': kin_id, 'default_voice': default_voice, 'harley_voice': harley_voice},
    indent=2).encode())
write_file(config, updated.encode())
write_file(bridge, (package / 'bridge.py').read_bytes())
print('Installed. Run bash ~/start-aipi.sh and enter the Kin ID you want.')
PY
