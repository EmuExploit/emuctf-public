from flask import Blueprint, jsonify, redirect, render_template, url_for

from models import Real, current_user, user_log_collection

profile_bp = Blueprint("profile", __name__)

# --- Template routes ---


@profile_bp.get("/profile")
def profile_page():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    uploads = [real.to_dict() for real in Real.objects(creator=user["username"])]
    return render_template("profile.html", user=user, uploads=uploads)


# --- API routes ---


@profile_bp.get("/api/self/recent-reals")
def recent_reals():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    # Reuse the audit log collection because I'm too lazy to implement recent reals properly :D
    UserLog = user_log_collection(user["username"])

    logs = [
        {k: v for k, v in doc.items() if k != "_id"}
        for doc in UserLog.find().sort("_id", 1)
    ]
    return jsonify(logs)
