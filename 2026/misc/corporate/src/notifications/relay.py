"""Private, fixed-destination Discord relay; public support has no Internet route."""

import json
import os
import re
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def destination(value):
    if not value:
        return ''
    parsed = urlsplit(value)
    if (
        parsed.scheme != 'https'
        or parsed.hostname not in {'discord.com', 'discordapp.com'}
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.path.startswith('/api/webhooks/')
    ):
        raise ValueError('Notification destination must be a Discord HTTPS webhook')
    return value


def make_handler(target, opener=None, ping_type='user', ping_id=''):
    target = destination(target)
    mentions = dict(parse=[])
    mention = ''
    if ping_id:
        if ping_type not in {'user', 'role'} or not re.fullmatch(r'[0-9]{17,20}', ping_id):
            raise ValueError('Discord ping requires type user/role and a 17-20 digit ID')
        mentions['users' if ping_type == 'user' else 'roles'] = [ping_id]
        mention = f'<@{ping_id}>' if ping_type == 'user' else f'<@&{ping_id}>'
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects())
    slots = threading.BoundedSemaphore(2)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log the destination credential or submitted title.

        def do_GET(self):
            self.send_response(200 if self.path == '/healthz' else 404)
            self.end_headers()

        def do_POST(self):
            self.connection.settimeout(3)
            self.close_connection = True
            if self.path != '/notify':
                self.send_error(404)
                return
            if not slots.acquire(blocking=False):
                self.send_error(429)
                return
            try:
                length = int(self.headers.get('Content-Length', '-1'))
                if not 0 < length <= 8192 or self.headers.get('Transfer-Encoding'):
                    raise ValueError('Invalid length')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('Incomplete body')
                payload = json.loads(raw)
                content = payload['content']
                if not isinstance(content, str) or len(content) > 2000:
                    raise ValueError('Invalid content')
                if mention:
                    content += '\n\n' + mention
                if len(content) > 2000:
                    raise ValueError('Notification including mention is too long')
                if target:
                    # Discord's edge rejects Python's default urllib User-Agent.
                    request = urllib.request.Request(
                        target,
                        method='POST',
                        headers={
                            'Content-Type': 'application/json',
                            'User-Agent': 'CorporateCTF-Notifications/1.0',
                        },
                        data=json.dumps(dict(content=content, allowed_mentions=mentions)).encode(),
                    )
                    with opener.open(request, timeout=3) as response:
                        if not 200 <= response.status < 300:
                            raise OSError('Notification refused')
                self.send_response(204)
                self.end_headers()
            except (ValueError, KeyError, TypeError):
                self.send_error(400)
            except urllib.error.HTTPError as error:
                # Do not log the exception URL: it contains the webhook token.
                print(f'Discord notification failed: HTTP {error.code}', flush=True)
                error.close()
                self.send_error(502)
            except OSError:
                print('Discord notification failed: connection or timeout error', flush=True)
                self.send_error(502)
            finally:
                slots.release()

    return Handler


if __name__ == '__main__':
    server = ThreadingHTTPServer(
        ('0.0.0.0', 8080),
        make_handler(
            os.environ.get('SUPPORT_DISCORD_WEBHOOK_URL', '').strip(),
            ping_type=os.environ.get('SUPPORT_DISCORD_PING_TYPE', 'user').strip(),
            ping_id=os.environ.get('SUPPORT_DISCORD_PING_ID', '').strip(),
        ),
    )
    server.serve_forever()
