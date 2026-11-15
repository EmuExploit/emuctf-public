import hashlib
import secrets

from flask import session

from config import (
    CREATOR_ADJECTIVES,
    CREATOR_NOUNS,
    CREATOR_SUFFIXES,
    MAX_AUDIT_RECORDS,
)
from models import AdminLog, Real, Session


def creator_username(real_id):
    digest = hashlib.sha256(real_id.encode()).digest()
    return (
        f"{CREATOR_ADJECTIVES[digest[0] % len(CREATOR_ADJECTIVES)]}_"
        f"{CREATOR_NOUNS[digest[1] % len(CREATOR_NOUNS)]}_"
        f"{CREATOR_SUFFIXES[digest[2] % len(CREATOR_SUFFIXES)]}"
    )


def fetch_random_reals(exclude=None, sample=1):
    exclude = list(set(exclude)) if exclude else []
    pipeline = [
        {
            "$match": {
                "prevent_autodiscover": {"$ne": True},
                **({"real_id": {"$nin": exclude}} if exclude else {}),
            }
        },
        {"$sample": {"size": sample}},
    ]

    return list(Real._get_collection().aggregate(pipeline))


def fetch_random_real_id(exclude=None):
    reals = fetch_random_reals(exclude=exclude, sample=1)
    return reals[0]["real_id"] if reals else None


def get_session():
    session_id = session.get("session_id")
    if not session_id:
        session_id = secrets.token_urlsafe(24)
        session["session_id"] = session_id
        Session(id=session_id, seen_real_ids=[]).save()
    return Session.objects(id=session_id).first()


def real_age(now, timestamp):
    minutes = max(1, (now - timestamp) // 60)
    return f"{minutes}m ago" if minutes < 60 else f"{minutes // 60}h ago"


def trim_admin_logs():
    excess = AdminLog.objects.count() - MAX_AUDIT_RECORDS
    if excess > 0:
        old_ids = AdminLog.objects.order_by("counter_id").limit(excess).scalar("id")
        AdminLog.objects(id__in=list(old_ids)).delete()


def trim_user_logs(coll):
    excess = coll.count_documents({}) - MAX_AUDIT_RECORDS
    if excess > 0:
        old_ids = [
            d["_id"]
            for d in coll.find({}, {"_id": 1})
            .sort([("timestamp", 1), ("_id", 1)])
            .limit(excess)
        ]
        coll.delete_many({"_id": {"$in": old_ids}})
