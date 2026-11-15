"""Route support messages to the single, stateful recovery conversation."""

import json
import time
import urllib.error
from collections import deque
from contextlib import closing

import websocket

from bot.dispatcher import Dispatcher
from bot.health import BotStatus
from common.mattermost import API_URL, runtime


def run():
    settings = runtime()
    dispatcher = Dispatcher(settings)
    status = BotStatus(settings['bot_id'])
    seen = deque(maxlen=1024)
    while True:
        try:
            status.update('connecting')
            with closing(
                websocket.create_connection(
                    API_URL.replace('http://', 'ws://') + '/websocket',
                    suppress_origin=True,
                    timeout=30,
                )
            ) as socket:
                # Wake regularly to deliver questions without blocking other players.
                socket.settimeout(1)
                socket.send(
                    json.dumps(
                        {
                            'seq': 1,
                            'action': 'authentication_challenge',
                            'data': {'token': settings['bot_token']},
                        }
                    )
                )
                status.update('authenticating')
                last_ping = time.monotonic()
                authenticated = False
                print('IT Support bot WebSocket opened; waiting for authentication.', flush=True)
                while True:
                    dispatcher.tick()
                    status.update(**dispatcher.snapshot())
                    if not authenticated and time.monotonic() - last_ping > 30:
                        raise websocket.WebSocketTimeoutException('Bot authentication timed out')
                    if authenticated:
                        if time.time() - status.data['last_pong_at'] > 60:
                            raise websocket.WebSocketTimeoutException(
                                'Bot WebSocket pong timed out'
                            )
                        if time.monotonic() - last_ping >= 20:
                            socket.ping()
                            last_ping = time.monotonic()
                    try:
                        opcode, payload = socket.recv_data(control_frame=True)
                        if opcode == websocket.ABNF.OPCODE_PONG:
                            status.update(last_pong_at=time.time())
                            continue
                        if opcode == websocket.ABNF.OPCODE_CLOSE:
                            raise websocket.WebSocketConnectionClosedException(
                                'Mattermost closed the socket'
                            )
                        if opcode != websocket.ABNF.OPCODE_TEXT:
                            continue
                        try:
                            event = json.loads(payload)
                            if not isinstance(event, dict):
                                continue
                        except (ValueError, RecursionError):
                            continue
                    except websocket.WebSocketTimeoutException:
                        continue
                    if event.get('seq_reply') == 1:
                        if event.get('status') != 'OK':
                            raise websocket.WebSocketException(
                                'Mattermost rejected bot authentication'
                            )
                        authenticated = True
                        status.update(
                            'connected', connected_at=time.time(), last_pong_at=time.time()
                        )
                        print('IT Support bot authenticated and ready.', flush=True)
                        continue
                    if event.get('event') != 'posted':
                        continue
                    try:
                        if not isinstance(event.get('data'), dict):
                            continue
                        post = json.loads(event['data']['post'])
                        if not isinstance(post, dict) or not all(
                            isinstance(post.get(key), str)
                            for key in ('id', 'user_id', 'channel_id', 'message')
                        ):
                            continue
                        props = post.get('props') or {}
                        if (
                            not isinstance(props, dict)
                            or post['user_id'] == settings['bot_id']
                            or post['id'] in seen
                            or post.get('type')
                            or props.get('from_webhook')
                        ):
                            continue
                        seen.append(post['id'])
                        dispatcher.submit(post, event['data'].get('channel_type'))
                    except (ValueError, KeyError, TypeError, RecursionError):
                        print('IT Support ignored an invalid post event.', flush=True)
        except (websocket.WebSocketException, OSError, urllib.error.URLError) as error:
            status.update('reconnecting')
            print(f'IT Support bot reconnecting after {type(error).__name__}: {error}', flush=True)
            time.sleep(2)


if __name__ == '__main__':
    run()
