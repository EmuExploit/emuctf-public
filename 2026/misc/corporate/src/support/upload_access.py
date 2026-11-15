"""Exact-origin CORS around body limits, and token authorization without cookies."""

import time

from flask import abort, current_app, request
from itsdangerous import BadData
from werkzeug.wrappers import Response

from common.upload_tokens import verify_upload_token

UPLOAD_METHODS = {'/malware': 'POST', '/malware/availability': 'GET'}


class UploadCors:
    """Wrap the body reader too, so its busy/oversize errors remain readable."""

    def __init__(self, app, origin):
        self.app = app
        self.origin = origin

    def __call__(self, environ, start_response):
        method = UPLOAD_METHODS.get(environ.get('PATH_INFO'))
        if not method:
            return self.app(environ, start_response)
        environ['corporate.upload_started'] = time.time()
        origin = environ.get('HTTP_ORIGIN')

        def cors_start(status, headers, exc_info=None):
            headers.append(('Vary', 'Origin'))
            if origin == self.origin:
                headers.extend(
                    [
                        ('Access-Control-Allow-Origin', self.origin),
                        ('Access-Control-Expose-Headers', 'Retry-After'),
                    ]
                )
            return start_response(status, headers, exc_info)

        if origin and origin != self.origin:
            return Response('Origin not allowed', status=403)(environ, cors_start)
        if environ['REQUEST_METHOD'] == 'OPTIONS':
            headers = {
                h.strip().lower()
                for h in environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '').split(',')
                if h.strip()
            }
            if (
                origin != self.origin
                or environ.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD') != method
                or not headers <= {'authorization', 'content-type'}
            ):
                return Response('Preflight not allowed', status=403)(environ, cors_start)
            return Response(
                status=204,
                headers={
                    'Access-Control-Allow-Methods': method,
                    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
                    'Access-Control-Max-Age': '300',
                },
            )(environ, cors_start)
        return self.app(environ, cors_start)


def token_owner():
    authorization = request.headers.get('Authorization', '')
    if authorization:
        if not authorization.startswith('Bearer '):
            abort(403)
        token = authorization[7:]
    else:
        # Ordinary browser form posts cannot set an Authorization header.
        token = request.form.get('upload_token', '') if request.method == 'POST' else ''
    try:
        return verify_upload_token(
            current_app, token, request.environ.get('corporate.upload_started')
        )
    except BadData:
        abort(
            401, description='Upload authorization expired. Please submit again from the platform.'
        )
