"""Use Secure cookies on HTTPS, including behind the trusted Caddy proxy."""

from flask import request
from flask.sessions import SecureCookieSessionInterface


class TransportSessionInterface(SecureCookieSessionInterface):
    def get_cookie_secure(self, app):
        return request.is_secure or super().get_cookie_secure(app)
