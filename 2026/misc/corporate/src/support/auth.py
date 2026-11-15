"""Session checks and service-role boundary for mailbox routes."""

import hmac
import time

from flask import abort, redirect, request, session, url_for

from support import config
from support.models import ADMIN_PATH


def csrf_valid(name='review_csrf'):
    token = session.get(name, '')
    supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf', '')
    return bool(token and hmac.compare_digest(token.encode(), supplied.encode()))


def reviewer_logged_in():
    stamp = session.get('review_authenticated_at', 0)
    return bool(stamp and 0 <= time.time() - stamp < config.SUPPORT_ADMIN_SESSION_SECONDS)


def install_guards(app, role):
    @app.before_request
    def mailbox_cache():
        reviewing = request.path == ADMIN_PATH or request.path.startswith(ADMIN_PATH + '/')
        if role == 'public' and reviewing:
            abort(404)
        if (
            role == 'reviewer'
            and not reviewing
            and request.endpoint not in {'static', 'health', 'review_home'}
        ):
            abort(404)
        if (
            request.path == '/platform.aspx'
            or request.path == '/malware'
            or request.path.startswith('/malware/')
            or request.path.startswith(ADMIN_PATH)
        ):
            # Applied below as well to downloads and authentication responses.
            request.environ['support_private'] = True
        if request.path == ADMIN_PATH or request.path.startswith(ADMIN_PATH + '/'):
            if request.endpoint != 'support_login' and not reviewer_logged_in():
                if '/api/' in request.path or '/preview/' in request.path:
                    return {'error': 'Login required'}, 401
                return redirect(url_for('support_login'))

    @app.after_request
    def private_headers(response):
        if request.environ.get('support_private'):
            response.headers['Cache-Control'] = 'no-store'
            if request.endpoint == 'support_preview':
                return response
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; object-src 'none'; frame-src 'self' about:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            )
        return response
