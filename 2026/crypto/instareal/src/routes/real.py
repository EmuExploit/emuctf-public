import time

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from models import Real
from utils import fetch_random_real_id, fetch_random_reals, get_session

real_bp = Blueprint("real", __name__)


# --- Template routes ---


@real_bp.get("/")
@real_bp.get("/real")
def real_root():
    real_id = fetch_random_real_id()
    if real_id:
        return redirect(url_for("real.real_view", real_id=real_id))
    return redirect(url_for("profile.profile_page"))


@real_bp.get("/real/<real_id>")
def real_view(real_id):
    if not Real.objects(real_id=real_id).first():
        abort(404)
    return render_template("real.html", initial_real_id=real_id)


# --- API routes ---


@real_bp.get("/api/reals")
def reals_api():
    REAL_BATCH_SIZE = 6

    initial_id = request.args.get("initial")
    session = get_session()
    excluded_ids = set(session.seen_real_ids if session.seen_real_ids else [])
    initial = (
        Real.objects(real_id=initial_id, prevent_autodiscover__ne=True)
        .first()
        .to_dict()
        if initial_id
        else None
    )

    if initial_id:
        excluded_ids.add(initial_id)
    reals = fetch_random_reals(exclude=list(excluded_ids), sample=REAL_BATCH_SIZE)
    if initial:
        reals.insert(0, initial)

    reals = reals[:REAL_BATCH_SIZE]
    returned_ids = [real["real_id"] for real in reals]
    if returned_ids:
        session.seen_real_ids = list(set((session.seen_real_ids or []) + returned_ids))
        session.save()

    now = int(time.time())
    reals = [Real.objects(real_id=real["real_id"]).first().to_dict() for real in reals]
    for real in reals:
        minutes = max(1, (now - real.pop("timestamp")) // 60)
        real["age"] = f"{minutes}m ago" if minutes < 60 else f"{minutes // 60}h ago"
    return jsonify(reals)


@real_bp.get("/api/real/<real_id>")
def get_real(real_id):
    real = Real.objects(real_id=real_id).first()
    if not real:
        abort(404)
    return real.content


@real_bp.post("/api/real/<real_id>/like")
def like_real(real_id):
    real = Real.objects(real_id=real_id).first()
    if not real:
        abort(404)
    real.likes = (real.likes or 0) + 1
    real.save()
    return jsonify({"likes": real.likes})
