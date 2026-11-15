import hashlib

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, current_user

auth_bp = Blueprint("auth", __name__)


# --- Template & Action routes ---


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("real.real_root"))
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return (
            render_template(
                "login.html", error="Please enter your username and password."
            ),
            400,
        )

    user = User.objects(username=username).first()
    if not user:
        return (
            render_template("login.html", error="We couldn't find that account."),
            403,
        )
    if not user.password_hash or not check_password_hash(user.password_hash, password):
        return render_template("login.html", error="Incorrect password."), 403

    session["user_id"] = str(user.id)
    return redirect(url_for("real.real_root"))


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("real.real_root"))
        return render_template("index.html", error=None)

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template("index.html", error="Please check your details."), 400
    if User.objects(username=username).first():
        return (
            render_template("index.html", error="That username is already taken."),
            409,
        )

    user_id = hashlib.sha256(username.lower().encode()).hexdigest()


    User(
        id=user_id, username=username, password_hash=generate_password_hash(password)
    ).save()
    session["user_id"] = user_id
    return redirect(url_for("real.real_root"))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
