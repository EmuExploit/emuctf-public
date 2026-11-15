"""Report the authenticated WebSocket state without exporting bot credentials."""

import json
import os
import time
from pathlib import Path

STATUS_FILE = Path('/tmp/bot-status.json')


class BotStatus:
    def __init__(self, bot_id):
        self.data = {'bot_id': bot_id, 'state': 'connecting', 'pid': os.getpid()}
        self.written = 0
        self.update(force=True)

    def update(self, state=None, force=False, **values):
        if state is not None:
            self.data['state'] = state
            force = True
        self.data.update(values)
        now = time.time()
        if force or now - self.written >= 5:
            self.data['checked_at'] = now
            temporary = STATUS_FILE.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.data))
            temporary.replace(STATUS_FILE)
            self.written = now


def read_status():
    try:
        data = json.loads(STATUS_FILE.read_text())
        fresh = 0 <= time.time() - data['checked_at'] < 45
        pong_fresh = 0 <= time.time() - data.get('last_pong_at', 0) < 60
        data['healthy'] = (
            data['state'] == 'connected'
            and fresh
            and pong_fresh
            and data.get('oldest_work_seconds', 0) < 45
        )
        if not fresh:
            data['state'] = 'stale heartbeat'
        elif data['state'] == 'connected' and not pong_fresh:
            data['state'] = 'no WebSocket pong'
        return data
    except (OSError, ValueError, KeyError):
        return {'state': 'not ready', 'healthy': False}


if __name__ == '__main__':
    status = read_status()
    print(status['state'])
    raise SystemExit(0 if status['healthy'] else 1)
