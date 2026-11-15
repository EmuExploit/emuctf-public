"""Short-lived upload authority, separate from Flask's session-cookie format."""

import hashlib
import os
import re
import time
from urllib.parse import urlsplit

from itsdangerous import BadData, URLSafeTimedSerializer

TOKEN_SECONDS = 300


def site_origin(value):
    """Accept an explicit HTTP(S) origin, never a path or browser-supplied host."""
    url = urlsplit(value)
    if (
        url.scheme not in {'http', 'https'}
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.path not in {'', '/'}
        or url.query
        or url.fragment
    ):
        raise ValueError('Site addresses must be HTTP(S) origins without paths or credentials')
    # Accessing port also validates its syntax/range.
    port = url.port
    host = f'[{url.hostname}]' if ':' in url.hostname else url.hostname
    if port and port != (443 if url.scheme == 'https' else 80):
        host += f':{port}'
    return f'{url.scheme}://{host}'


def configure_uploads(app):
    for key in ('SITE_ADDRESS', 'UPLOAD_SITE_ADDRESS'):
        value = app.config.get(key, os.environ.get(key, '')).strip()
        app.config[key] = site_origin(value) if value else ''
    if app.config['UPLOAD_SITE_ADDRESS']:
        if not app.config['SITE_ADDRESS'] or not app.secret_key:
            raise ValueError('Separate uploads require SITE_ADDRESS and a session signing secret')
        if app.config['SITE_ADDRESS'] == app.config['UPLOAD_SITE_ADDRESS']:
            raise ValueError('Upload and website origins must differ')


def owner_for_session(csrf):
    # Stable across token refreshes, identical to the existing per-login queue key.
    return hashlib.sha256(csrf.encode()).hexdigest()


def serializer(app):
    return URLSafeTimedSerializer(app.secret_key, salt='corporate-public-upload-v1')


def issue_upload_token(app, csrf):
    return serializer(app).dumps(
        dict(
            owner=owner_for_session(csrf),
            scope='submit',
            audience=app.config['UPLOAD_SITE_ADDRESS'],
            issuer=app.config['SITE_ADDRESS'],
        )
    )


def verify_upload_token(app, token, started=None):
    """Check expiry at request arrival, so body reading cannot expire an upload."""
    if not isinstance(token, str) or not 0 < len(token) <= 2048:
        raise BadData('Missing or invalid upload token')
    data, issued = serializer(app).loads(token, return_timestamp=True)
    age = (time.time() if started is None else started) - issued.timestamp()
    if (
        not 0 <= age <= TOKEN_SECONDS
        or not isinstance(data, dict)
        or data.get('scope') != 'submit'
        or data.get('audience') != app.config['UPLOAD_SITE_ADDRESS']
        or data.get('issuer') != app.config['SITE_ADDRESS']
        or not isinstance(data.get('owner'), str)
        or not re.fullmatch(r'[0-9a-f]{64}', data['owner'])
    ):
        raise BadData('Expired or invalid upload token')
    return data['owner']
