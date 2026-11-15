import base64
import hashlib
import pickle
import random
import time

from flask import Blueprint, redirect, render_template, request, url_for

from utils import trim_admin_logs, trim_user_logs
from config import REAL_CATEGORIES
from models import AdminLog, Real, Settings, current_user, user_log_collection

post_bp = Blueprint("post", __name__)


# --- Template routes ---


@post_bp.get("/post")
def post_page():
    user = current_user()
    cats = [cat.capitalize() for cat in REAL_CATEGORIES]
    return render_template("post.html", user=user, categories=cats)


# --- Action routes ---


@post_bp.post("/post")
def post_reals():
    user = current_user()

    if not user:
        return redirect(url_for("auth.login"))
    username = user["username"]

    category = request.form.get("category", "").strip().lower()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not category or not title or not content:
        return "Category, title, and content are required", 400
    if category not in REAL_CATEGORIES:
        return "Invalid category", 400

    settings = Settings.objects(id="seeded").first()
    rng = random.Random()
    rng.setstate(pickle.loads(base64.b64decode(settings.upload_rng_state)))
    timestamp = int(time.time())
    max_real = Real.objects().order_by("-counter_id").first()
    counter_id = max_real.counter_id + 1 if max_real else 1

    real_salt = rng.getrandbits(32)
    real_id = hashlib.sha256(f"{counter_id}:{real_salt}".encode()).hexdigest()
    real = Real(
        counter_id=counter_id,
        real_id=real_id,
        timestamp=timestamp,
        creator=username,
        category=category,
        title=title,
        content=content,
    )
    real.save()

    # Duplicate the real into the admin's log collection for auditing purposes
    if not AdminLog.objects(real_id=real.real_id).first():
        AdminLog(
            counter_id=counter_id,
            real_salt=real_salt,
            real_id=real_id,
            timestamp=timestamp,
            creator=username,
            category=category,
            title=title,
            content=content,
        ).save()
        trim_admin_logs()

    # Add the real to the user's personal log collection
    UserLog = user_log_collection(username)
    if not UserLog.find_one({"real_id": real.real_id}):
        UserLog.insert_one(
            {
                "real_id": real.real_id,
                "timestamp": real.timestamp,
                "creator": real.creator,
                "category": real.category,
                "title": real.title,
                "content": real.content,
            }
        )
        trim_user_logs(UserLog)

    Settings.objects(id="seeded").update_one(
        set__upload_rng_state=base64.b64encode(pickle.dumps(rng.getstate())).decode(),
        upsert=True,
    )

    return redirect(url_for("profile.profile_page"))
