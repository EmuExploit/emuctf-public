from flask import Flask

from routes.auth import auth_bp
from routes.real import real_bp
from routes.post import post_bp
from routes.profile import profile_bp


def register_blueprints(app: Flask):
    app.register_blueprint(auth_bp)
    app.register_blueprint(real_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(post_bp)
