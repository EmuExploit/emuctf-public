"""Public submission and reviewer apps share code, but run with separate authority."""

import os
from urllib.parse import urlsplit

from flask import Flask, redirect, render_template, request, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix

from common.request_bodies import BoundedRequestBodies
from common.upload_tokens import configure_uploads
from support import config
from support.support_mail import install
from support.upload_access import UploadCors


def create_app(test_config=None):
    app = Flask(__name__, static_url_path='/malware/static')
    app.config.update(
        FLAG=config.FLAG,
        MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
        SUPPORT_ROLE=os.environ.get('SUPPORT_ROLE', 'public'),
    )
    app.config.update(config.SESSION_SETTINGS)
    if test_config:
        app.config.update(test_config)
    if app.config['SUPPORT_ROLE'] == 'reviewer':
        if (
            not (app.config.get('SECRET_KEY') or config.SESSION_SECRET)
            or not config.SUPPORT_ADMIN_PASSWORD
        ):
            raise ValueError('Reviewer requires its own session secret and password')
        secure = (
            urlsplit(
                os.environ.get('REVIEW_SITE_ADDRESS', 'https://review.corporate.ctf.emu.team')
            ).scheme
            == 'https'
        )
        app.config.update(
            SESSION_COOKIE_NAME='__Host-corporate-review' if secure else 'corporate-review-dev',
            SESSION_COOKIE_SECURE=secure,
            SESSION_COOKIE_DOMAIN=None,
            SESSION_COOKIE_PATH='/',
            SESSION_COOKIE_SAMESITE='Strict',
        )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    app.wsgi_app = BoundedRequestBodies(app.wsgi_app, app.config['MAX_CONTENT_LENGTH'])
    app.jinja_loader = ChoiceLoader([app.jinja_loader, FileSystemLoader('/app/shared-templates')])
    # Shared error/form templates link back to the frontend's public routes.
    for endpoint, path in {
        'index': '/',
        'about': '/about.aspx',
        'team': '/people.aspx',
        'pricing': '/pricing.aspx',
        'careers': '/careers.aspx',
        'privacy': '/privacy.aspx',
        'terms': '/terms.aspx',
        'platform': '/platform.aspx',
    }.items():
        app.add_url_rule(path, endpoint, build_only=True)
    install(app)
    if app.config['SUPPORT_ROLE'] != 'reviewer':
        configure_uploads(app)
        if app.config['UPLOAD_SITE_ADDRESS']:
            app.wsgi_app = UploadCors(app.wsgi_app, app.config['SITE_ADDRESS'])
    if app.config['SUPPORT_ROLE'] == 'reviewer':

        @app.get('/')
        def review_home():
            return redirect(url_for('support_admin'))

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}

    @app.errorhandler(401)
    def unauthorized(error):
        if app.config.get('UPLOAD_SITE_ADDRESS') and app.config['SUPPORT_ROLE'] == 'public':
            if request.accept_mimetypes.best == 'application/json':
                return dict(error=error.description, code='upload_authorization'), 401
            return render_template(
                'upload_receipt.html',
                message=error.description,
                result=None,
                platform_url=app.config['SITE_ADDRESS'] + '/platform',
            ), 401
        return error

    @app.errorhandler(413)
    def too_large(_error):
        return render_template(
            'error.html',
            title='Request too large',
            message='Attachments must total at most 20 MiB. Please shorten your submission.',
            page='',
        ), 413

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    return app


app = create_app()
