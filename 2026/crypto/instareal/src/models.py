import hashlib

import pymongo
from flask import session
from mongoengine import (
    Document,
    StringField,
    IntField,
    BooleanField,
    ListField,
    connect,
)

import re

from config import HUE_MODULO, HUE_OFFSET, TILT_CENTER, TILT_RANGE, MONGO_URI


## Borrowed this from gemini :D
def normalize_mongo_collection(name: str) -> str:
    """
    Normalizes a string into a standard MongoDB collection name.
    Converts to lowercase, replaces spaces/hyphens with underscores,
    strips out forbidden characters, and removes any 'system.' prefix.
    """
    if not name:
        raise ValueError("Collection name cannot be empty.")

    # 1. Convert to lowercase and trim whitespace
    normalized = name.strip().lower()

    # 2. Replace spaces and hyphens with underscores
    normalized = re.sub(r"[\s\-]+", "_", normalized)

    # 3. Strip out forbidden characters: $, .
    normalized = re.sub(r"[$.]", "", normalized)

    # 4. Remove leading/trailing underscores that might have been created
    normalized = normalized.strip("_")

    # 5. Prevent system. prefix restriction
    if normalized.startswith("system_") or normalized == "system":
        normalized = normalized.replace("system", "sys", 1)

    if not normalized:
        raise ValueError(
            f"String '{name}' does not contain any valid characters for a MongoDB collection name."
        )
    return normalized


# ── MongoEngine ORM models ──────────────────────────────────────


class User(Document):
    """User account document."""

    id = StringField(primary_key=True)
    username = StringField(required=True, unique=True)
    password_hash = StringField()

    meta = {"collection": "USERS"}

    def to_dict(self):
        return {k: getattr(self, k) for k in ["id", "username", "password_hash"]}


class Real(Document):
    """Reals collection — arbitrary fields from seeding or user uploads."""

    counter_id = IntField(unique=True)
    real_id = StringField(unique=True)
    timestamp = IntField()
    prevent_autodiscover = BooleanField(default=False)
    creator = StringField()
    category = StringField()
    title = StringField()
    content = StringField()
    likes = IntField(default=0)

    meta = {"collection": "REALS"}

    def to_dict(self):
        raw = {
            k: getattr(self, k)
            for k in [
                "real_id",
                "timestamp",
                "content",
                "prevent_autodiscover",
                "creator",
                "category",
                "title",
                "likes",
            ]
        }
        digest = hashlib.sha256(self.real_id.encode()).digest()
        hue = int.from_bytes(digest[:2], "big") % HUE_MODULO
        raw["art"] = (
            f"linear-gradient(145deg,hsl({hue} 72% 66%),hsl({(hue + HUE_OFFSET) % HUE_MODULO} 58% 22%))"
        )
        raw["tilt"] = digest[12] % TILT_RANGE - TILT_CENTER
        return raw


class Settings(Document):
    """Application settings (seeded flag, RNG state, etc.)."""

    id = StringField(primary_key=True)
    flag_counter = IntField()
    upload_rng_state = StringField()

    meta = {
        "collection": "SETTINGS",
    }


class Session(Document):
    """Feed session tracking."""

    id = StringField(primary_key=True)
    seen_real_ids = ListField(StringField())

    meta = {"collection": "SESSIONS"}


class AdminLog(Document):
    """Admin log record."""

    counter_id = IntField()
    real_salt = IntField()
    real_id = StringField()
    timestamp = IntField()
    creator = StringField()
    category = StringField()
    title = StringField()
    content = StringField()

    meta = {"collection": "ADMIN-LOGS"}

    def to_dict(self):
        return {
            k: getattr(self, k)
            for k in [
                "counter_id",
                "real_salt",
                "real_id",
                "timestamp",
                "creator",
                "category",
                "title",
                "content",
            ]
        }


# ── Raw pymongo access for aggregation / dynamic collections ─────

connect("instareal", host=MONGO_URI, serverSelectionTimeoutMS=3000)

client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = client["instareal"]


def current_user():
    """Get the currently logged-in user dict from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = User.objects(id=user_id).first()
    return user.to_dict() if user else None


def user_log_collection(username: str):
    """
    Return a pymongo collection for the given user's audit log.
    The collection name is dynamic so we use pymongo directly.
    """

    col_name = normalize_mongo_collection(username).upper()
    return db[f"{col_name}-LOGS"]
