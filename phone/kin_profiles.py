"""Select the active avatar and Piper alias from the launcher's Kin ID."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

def start_voice_proxy(voice):
    class SpeechHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path != '/v1/audio/speech':
                self.send_error(404)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536:
                    raise ValueError
                speech = json.loads(self.rfile.read(size))
                if not isinstance(speech, dict):
                    raise ValueError
                speech['voice'] = voice
            except (ValueError, UnicodeError):
                self.send_error(400)
                return
            request = Request('http://127.0.0.1:8001/v1/audio/speech',
                              json.dumps(speech).encode(),
                              {'Content-Type': 'application/json'})
            try:
                upstream = urlopen(request, timeout=100)
            except HTTPError as exc:
                exc.close()
                self.send_error(exc.code, 'Piper rejected the voice request')
                return
            except OSError:
                self.send_error(502, 'Piper is unavailable')
                return
            with upstream:
                self.send_response(200)
                self.send_header('Content-Type', upstream.headers.get_content_type())
                self.end_headers()
                while chunk := upstream.read(65536):
                    self.wfile.write(chunk)
    server = ThreadingHTTPServer(('127.0.0.1', 8002), SpeechHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
