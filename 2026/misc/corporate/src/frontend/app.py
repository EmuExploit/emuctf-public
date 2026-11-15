"""Corporate website, platform key form and contact form."""

import hmac
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, Response, abort, redirect, render_template, request, session, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix

from bootstrap.fixtures.members import ADVISOR, MEMBERS
from common.mattermost import API_URL, FRONTEND_RUNTIME, frontend_runtime
from common.request_bodies import BoundedRequestBodies
from common.sessions import TransportSessionInterface
from common.upload_tokens import TOKEN_SECONDS, configure_uploads, issue_upload_token
from frontend import config
from frontend.contact import ContactLimiter, deliver_contact, validate_contact

STATIC_PAGES = {
    'about': ('/about.aspx', 'about.html', 'Company'),
    'team': ('/people.aspx', 'team.html', 'Our people'),
    'pricing': ('/pricing.aspx', 'pricing.html', 'Pricing'),
    'careers': ('/careers.aspx', 'careers.html', 'Careers'),
    'privacy': ('/privacy.aspx', 'privacy.html', 'Privacy policy'),
    'terms': ('/terms.aspx', 'terms.html', 'Terms of service'),
}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        FLAG=config.FLAG,
        PLATFORM_ACCESS_KEY=config.PLATFORM_ACCESS_KEY,
        MATTERMOST_WEBHOOK_URL=config.MATTERMOST_WEBHOOK_URL,
        MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
    )
    if test_config:
        app.config.update(test_config)
    # Only Caddy publishes ports and supplies the forwarding headers.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    app.wsgi_app = BoundedRequestBodies(app.wsgi_app, app.config['MAX_CONTENT_LENGTH'])
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY') or config.SESSION_SECRET
    app.config.update(config.SESSION_SETTINGS)
    configure_uploads(app)
    app.session_interface = TransportSessionInterface()
    app.jinja_loader = ChoiceLoader([app.jinja_loader, FileSystemLoader('/app/shared-templates')])
    # Build-only route: requests are served by the separate support container.
    app.add_url_rule('/malware', 'support_submit', build_only=True)
    cached_pages = {}
    contact_limiter = ContactLimiter()
    mattermost_env = dict(
        line.split('=', 1)
        for line in Path('/app/mattermost.env').read_text().splitlines()
        if line.startswith('MM_') and '=' in line
    )

    @app.after_request
    def headers(response):
        if request.path in ('/platform', '/platform.aspx', '/platform/upload-token'):
            response.headers['Cache-Control'] = 'no-store'
        if request.path in ('/platform', '/platform.aspx'):
            upload = app.config['UPLOAD_SITE_ADDRESS']
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                "object-src 'none'; frame-src 'self' about:; "
                "frame-ancestors 'none'; base-uri 'none'; "
                f"connect-src 'self' {upload}; form-action 'self' {upload}"
            )
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Powered-By'] = 'ASP.NET'
        response.headers['X-AspNet-Version'] = '4.0.30319'
        if request.method == 'POST':
            response.headers['Cache-Control'] = 'no-store'
        return response

    for endpoint, (path, template, title) in STATIC_PAGES.items():
        app.add_url_rule(path, endpoint, lambda endpoint=endpoint: cached_pages[endpoint])

    @app.get('/marketing.aspx')
    def marketing():
        return redirect(url_for('pricing'), code=301)

    @app.route('/', methods=['GET', 'POST'])
    @app.route('/default.aspx', methods=['GET', 'POST'])
    def index():
        if request.method == 'GET':
            return cached_pages['index']
        if request.content_length and request.content_length > config.CONTACT_MAX_BYTES:
            return too_large(None)
        values = {
            field: request.form.get(field, '').strip() for field in ('name', 'email', 'message')
        }
        errors = validate_contact(values)
        message, status = None, 400
        if not errors:
            integration = frontend_runtime() if FRONTEND_RUNTIME.exists() else {}
            webhook = app.config['MATTERMOST_WEBHOOK_URL'] or integration.get(
                'contact_webhook_url', ''
            )
            if not webhook:
                message, status = (
                    'The message gateway is offline. Your message has not been sent.',
                    503,
                )
            elif not contact_limiter.allow(request.remote_addr or 'unknown'):
                message, status = 'Please wait a moment before submitting another enquiry.', 429
            else:
                message, status = deliver_contact(webhook, values)
        return render_template(
            'index.html',
            title='Emu Industries',
            page='index',
            values=values,
            errors=errors,
            message=message,
        ), status

    @app.route('/platform', methods=['GET', 'POST'])
    @app.route('/platform.aspx', methods=['GET', 'POST'])
    def platform():
        error = None
        if request.method == 'POST':
            supplied = request.form.get('access_key', '')
            if supplied and hmac.compare_digest(
                supplied.encode(), app.config['PLATFORM_ACCESS_KEY'].encode()
            ):
                import secrets

                session['platform_access'] = True
                session['csrf'] = secrets.token_hex(32)
                return redirect(url_for('platform'), code=303)
            error = 'Access key not recognised. Contact IT.'
        if request.method == 'GET' and session.get('platform_access'):
            return render_template(
                'flag.html',
                title='Contact support',
                page='platform',
                flag=app.config['FLAG'],
                values={},
                upload_action=(app.config['UPLOAD_SITE_ADDRESS'] + '/malware')
                if app.config['UPLOAD_SITE_ADDRESS']
                else url_for('support_submit'),
                upload_token=issue_upload_token(app, session['csrf'])
                if app.config['UPLOAD_SITE_ADDRESS']
                else '',
                upload_token_url=url_for('upload_token'),
            )
        return render_template(
            'platform.html', title='Platform', page='platform', error=error
        ), 401 if error else 200

    @app.post('/platform/upload-token')
    def upload_token():
        csrf = session.get('csrf', '')
        supplied = request.headers.get('X-CSRF-Token', '')
        if (
            not app.config['UPLOAD_SITE_ADDRESS']
            or not session.get('platform_access')
            or not csrf
            or not hmac.compare_digest(csrf.encode(), supplied.encode())
        ):
            abort(403)
        return dict(token=issue_upload_token(app, csrf), expires_in=TOKEN_SECONDS)

    @app.get('/robots.txt')
    def robots():
        return Response(
            'User-agent: *\nDisallow: /chat\nDisallow: /App_Data/\n', mimetype='text/plain'
        )

    @app.get('/App_Data/IT-handover.txt')
    def handover():
        return app.send_static_file('IT-handover.txt')

    @app.get('/healthz')
    def healthz():
        try:
            with urllib.request.urlopen(API_URL + '/system/ping', timeout=2) as response:
                if response.status != 200:
                    return {'status': 'unavailable', 'mattermost': 'unavailable'}, 503
        except (urllib.error.URLError, TimeoutError, OSError):
            return {'status': 'unavailable', 'mattermost': 'unavailable'}, 503
        return {'status': 'ok'}

    @app.errorhandler(404)
    def not_found(_error):
        integration = frontend_runtime() if FRONTEND_RUNTIME.exists() else {}
        environment = {
            **mattermost_env,
            'MM_SERVICESETTINGS_SITEURL': integration.get(
                'mattermost_site_url', request.url_root.rstrip('/') + '/chat'
            ),
        }
        return render_template('not_found.html', path=request.path, environment=environment), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template(
            'error.html',
            title='Request too large',
            message='Please shorten your submission.',
            page='',
        ), 413

    # Render public marketing pages once.
    with app.test_request_context():
        for endpoint, (_, template, title) in STATIC_PAGES.items():
            cached_pages[endpoint] = render_template(
                template, title=title, page=endpoint, advisor=ADVISOR, members=MEMBERS
            )
        cached_pages['index'] = render_template(
            'index.html', title='Emu Industries', page='index', values={}, errors={}, message=None
        )
    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
