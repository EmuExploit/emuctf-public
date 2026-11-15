"""Bound body reads before a slow client can occupy every application thread."""

import json
import socket
import tempfile
import threading

from werkzeug.wrappers import Response
from werkzeug.wsgi import ClosingIterator


class BoundedRequestBodies:
    def __init__(self, app, max_bytes, seconds=60, readers=2):
        self.app = app
        self.max_bytes = max_bytes
        self.seconds = seconds
        self.readers = threading.BoundedSemaphore(readers)

    @staticmethod
    def refuse(environ, start_response, status, message, retry=False):
        # Do not let Gunicorn drain an unfinished body on a keepalive connection.
        headers = {'Connection': 'close', 'Cache-Control': 'no-store'}
        if retry:
            headers['Retry-After'] = '3'
            return Response(
                json.dumps(dict(error=message, code='busy', retry_after=3)),
                status=status,
                headers=headers,
                content_type='application/json',
            )(environ, start_response)
        return Response(
            message, status=status, headers=headers, content_type='text/plain; charset=utf-8'
        )(environ, start_response)

    def __call__(self, environ, start_response):
        raw_length = environ.get('CONTENT_LENGTH', '')
        try:
            length = int(raw_length) if raw_length else None
        except ValueError:
            return self.refuse(environ, start_response, 400, 'Invalid content length.')
        if length is not None and (length < 0 or length > self.max_bytes):
            return self.refuse(environ, start_response, 413, 'Request body is too large.')
        # Gunicorn marks all streams terminated, including bodyless GETs.
        no_gunicorn_body = (
            'gunicorn.socket' in environ
            and length is None
            and not environ.get('HTTP_TRANSFER_ENCODING')
        )
        if (
            length == 0
            or no_gunicorn_body
            or (length is None and not environ.get('wsgi.input_terminated'))
        ):
            return self.app(environ, start_response)
        if not self.readers.acquire(blocking=False):
            return self.refuse(
                environ, start_response, 429, 'Please retry your upload in a moment.', retry=True
            )

        try:
            body = tempfile.SpooledTemporaryFile(max_size=256 * 1024, mode='w+b')
        except BaseException:
            self.readers.release()
            raise
        expired = threading.Event()
        connection = environ.get('gunicorn.socket')
        timer_lock = threading.Lock()
        finished = False

        def interrupt():
            with timer_lock:
                if finished:
                    return
                expired.set()
                if connection is not None:
                    try:
                        connection.shutdown(socket.SHUT_RD)
                    except OSError:
                        pass

        # Absolute deadline: a client sending a byte periodically cannot renew it.
        timer = threading.Timer(self.seconds, interrupt)
        timer.daemon = True
        timer.start()
        status, message = None, None
        try:
            total = 0
            while length is None or total < length:
                wanted = min(
                    65536, (length - total) if length is not None else self.max_bytes + 1 - total
                )
                block = environ['wsgi.input'].read(wanted)
                if expired.is_set():
                    status, message = 408, 'Request body took too long.'
                    break
                if not block:
                    if length is not None and total != length:
                        status, message = 400, 'Incomplete request body.'
                    break
                total += len(block)
                if total > self.max_bytes:
                    status, message = 413, 'Request body is too large.'
                    break
                body.write(block)
        except (OSError, ValueError):
            status = 408 if expired.is_set() else 400
            message = (
                'Request body took too long.' if expired.is_set() else 'Incomplete request body.'
            )
        finally:
            with timer_lock:
                finished = True
                timer.cancel()
            self.readers.release()
        if status is not None:
            body.close()
            return self.refuse(environ, start_response, status, message)
        body.seek(0)
        environ['wsgi.input'] = body
        try:
            return ClosingIterator(self.app(environ, start_response), [body.close])
        except BaseException:
            body.close()
            raise
