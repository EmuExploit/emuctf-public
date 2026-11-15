import time

from flask import Flask, redirect, request, session, url_for

from config import SESSION_SECRET
from models import client, current_user
from routes import register_blueprints
from seeds import seed_database

app = Flask(__name__)
app.secret_key = SESSION_SECRET

register_blueprints(app)


# ── Auth guard — all routes require login except /login, /signup, and static ──

PUBLIC_ENDPOINTS = {"auth.login", "auth.signup", "static"}


@app.before_request
def require_auth():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return
    if not current_user():
        session.clear()
        return redirect(url_for("auth.login"))


def init_db():
    for _ in range(30):
        try:
            client.admin.command("ping")
            seed_database()
            print("Database ready")
            break
        except Exception:
            time.sleep(1)
    else:
        print("Warning: could not connect to database")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
