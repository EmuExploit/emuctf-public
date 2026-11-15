"""Wire mailbox storage, role guards and role-specific routes."""

from common.sessions import TransportSessionInterface
from support import config
from support.auth import install_guards
from support.mailbox import Mailbox
from support.models import ADMIN_PATH as ADMIN_PATH
from support.models import player_result as player_result
from support.public import register_public_routes
from support.reviewer import register_reviewer_routes


def install(app):
    role = app.config.get('SUPPORT_ROLE', 'public')
    if role not in {'public', 'reviewer', 'combined'} or (role == 'combined' and not app.testing):
        raise ValueError('Invalid support service role')
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY') or config.SESSION_SECRET
    app.session_interface = TransportSessionInterface()
    mailbox = Mailbox(app.config.get('SUPPORT_STORAGE', config.SUPPORT_STORAGE))
    app.extensions['mailbox'] = mailbox
    install_guards(app, role)
    if role in {'public', 'combined'}:
        register_public_routes(app, mailbox)
    if role in {'reviewer', 'combined'}:
        register_reviewer_routes(app, mailbox)
