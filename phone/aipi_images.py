"""Kindroid chat-image relay for the phone-hosted AiPi-Lite."""
import ipaddress
import json
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = 'https://api.kindroid.ai/v1/get-chat-messages'
POLL_SECONDS = 180
PHOTO_LIFETIME = 300
MAX_IMAGE = 16 * 1024 * 1024
PIXEL_BYTES = 128 * 128 * 2

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = build_opener(NoRedirect())

def read_url(url, cap, headers=None):
    with opener.open(Request(url, headers=headers or {}), timeout=15) as response:
        blob = response.read(cap + 1)
    if len(blob) > cap:
        raise ValueError('response exceeds size limit')
    return blob

def to_pixels(blob):
    if blob.startswith(b'\xff\xd8\xff'):
        demuxer = 'jpeg_pipe'
    elif blob.startswith(b'\x89PNG\r\n\x1a\n'):
        demuxer = 'png_pipe'
    elif blob.startswith(b'RIFF') and blob[8:12] == b'WEBP':
        demuxer = 'webp_pipe'
    else:
        raise ValueError('unsupported image format')
    result = subprocess.run(
        ['ffmpeg', '-nostdin', '-loglevel', 'error', '-protocol_whitelist', 'pipe',
         '-max_pixels', '16777216', '-threads', '1', '-f', demuxer, '-i', 'pipe:0',
         '-filter_threads', '1', '-vf',
         'scale=128:128:force_original_aspect_ratio=decrease,pad=128:128:(ow-iw)/2:(oh-ih)/2',
         '-frames:v', '1', '-pix_fmt', 'rgb565le', '-f', 'rawvideo', 'pipe:1'],
        input=blob, capture_output=True, check=True, timeout=20)
    if len(result.stdout) != PIXEL_BYTES:
        raise ValueError('unexpected decoded image size')
    return result.stdout

def download_pixels(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.port not in (None, 443)):
        raise ValueError('unsupported image URL')
    addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('image URL needs a public host')
    return to_pixels(read_url(url, MAX_IMAGE))

class Relay:
    def __init__(self, key, ai_id):
        self.key = key
        self.ai_id = ai_id
        self.cursor = None
        self.initializing = True
        self.photo = None
        self.seen = {}

    def poll(self):
        query = {'ai_id': self.ai_id, 'limit': 100}
        if self.cursor is not None:
            query['start_after_timestamp'] = self.cursor
        feed = json.loads(read_url(API + '?' + urlencode(query), 4 * 1024 * 1024,
                                   {'Authorization': 'Bearer ' + self.key}))
        pagination = feed['pagination']
        messages = feed['messages']
        cursor = pagination.get('lastTimestamp')
        more = pagination['hasMore']
        if more and (cursor is None or cursor == self.cursor):
            raise ValueError('Kindroid history cursor did not advance')
        candidates = []
        for message in messages:
            for url in message.get('image_urls') or []:
                if not isinstance(url, str):
                    continue
                key = (message.get('id'), url)
                if key not in self.seen:
                    self.seen[key] = None
                    candidates.append(url)
        while len(self.seen) > 1000:
            del self.seen[next(iter(self.seen))]
        if not self.initializing:
            for url in reversed(candidates):
                try:
                    pixels = download_pixels(url)
                except (OSError, ValueError, subprocess.SubprocessError):
                    print('AiPi images: an attachment could not be converted.', flush=True)
                    continue
                self.photo = (time.monotonic(), secrets.token_hex(16).encode() + pixels)
                print('AiPi images: new chat image ready.', flush=True)
                break
        if more:
            self.cursor = cursor
        elif len(messages) > 12:
            # Revisit recent entries in case a generated image is attached later.
            self.cursor = messages[-13]['timestamp']
        if not more and self.initializing:
            self.initializing = False
            print('AiPi images: ready for new chat images.', flush=True)
        return more

    def run(self):
        # Limit startup bursts. Long histories continue at the regular polling interval.
        fast_pages = 10
        while True:
            delay = POLL_SECONDS
            try:
                if self.poll() and fast_pages:
                    fast_pages -= 1
                    delay = 6
            except HTTPError as exc:
                print(f'AiPi images: chat API returned HTTP {exc.code}.', flush=True)
                delay = 900 if exc.code == 429 else POLL_SECONDS
            except (OSError, ValueError, KeyError, TypeError):
                print('AiPi images: chat history check failed. Retrying later.', flush=True)
            time.sleep(delay)

def start(key, ai_id, config, avatar=b'G'):
    has_ffmpeg = shutil.which('ffmpeg') is not None
    match = re.search(r"""^\s*websocket:\s*['"]?wss?://([0-9.]+):""",
                      Path(config).read_text(), re.MULTILINE)
    if not match:
        raise ValueError('expected a numeric hotspot IP in the websocket setting')
    host = ipaddress.IPv4Address(match[1])
    if not any(host in ipaddress.IPv4Network(net)
               for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        raise ValueError('expected a private hotspot IP')
    relay = Relay(key, ai_id)

    class PhotoHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            route = urlsplit(self.path)
            if route.path == '/aipi/avatar':
                self.send_response(200)
                self.send_header('Content-Length', '1')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(avatar)
                return
            if route.path != '/aipi/image':
                self.send_error(404)
                return
            photo = relay.photo
            after = parse_qs(route.query).get('after', [''])[0]
            payload = b''
            if photo and time.monotonic() - photo[0] < PHOTO_LIFETIME:
                if photo[1][:32].decode() != after:
                    payload = photo[1]
            self.send_response(200 if payload else 204)
            self.send_header('Cache-Control', 'no-store')
            if payload:
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)

    server = ThreadingHTTPServer((str(host), 8082), PhotoHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if has_ffmpeg:
        threading.Thread(target=relay.run, daemon=True).start()
    else:
        print('AiPi chat images paused. Install ffmpeg to enable them.', flush=True)
    print(f'AiPi images: listening on {host}:8082.', flush=True)
