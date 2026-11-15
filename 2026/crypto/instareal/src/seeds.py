import base64
import hashlib
import pickle
import random
import secrets
import time

from werkzeug.security import generate_password_hash

from config import (
    ADMIN_PASSWORD,
    FLAG,
    FLAG_COUNTER_ID_MAX,
    FLAG_COUNTER_ID_MIN,
    LIKES_BASE,
    LIKES_MAX,
    MAX_AUDIT_RECORDS,
    REAL_CATEGORIES,
    REAL_CONTENTS,
    REAL_TITLES,
    SEED_REALS,
)
from models import AdminLog, Real, Settings, User
from utils import creator_username


def _wipe():
    Real.objects.delete()
    AdminLog.objects.delete()
    Settings.objects(id="seeded").delete()


def _seed_is_valid(settings):
    if "upload_rng_state" not in settings or "flag_counter" not in settings:
        return False
    if AdminLog.objects.count() != MAX_AUDIT_RECORDS:
        return False
    if Real.objects.count() != SEED_REALS:
        return False
    first = Real.objects.order_by("counter_id").first()
    latest = Real.objects.order_by("-counter_id").first()
    return bool(
        first and first.counter_id == 1 and latest and latest.counter_id == SEED_REALS
    )


def _seed_fresh():
    rng = random.Random()
    flag_counter = (
        secrets.randbelow(FLAG_COUNTER_ID_MAX - FLAG_COUNTER_ID_MIN + 1)
        + FLAG_COUNTER_ID_MIN
    )
    now = int(time.time())
    first_logged = SEED_REALS - MAX_AUDIT_RECORDS + 1

    for counter_id in range(1, SEED_REALS + 1):
        real_salt = rng.getrandbits(32)
        real_id = hashlib.sha256(f"{counter_id}:{real_salt}".encode()).hexdigest()
        digest = hashlib.sha256(real_id.encode()).digest()
        is_flag = counter_id == flag_counter
        common = dict(
            counter_id=counter_id,
            real_id=real_id,
            timestamp=now - (SEED_REALS - counter_id),
            creator=creator_username(real_id),
            category=REAL_CATEGORIES[counter_id % len(REAL_CATEGORIES)],
            title=REAL_TITLES[counter_id % len(REAL_TITLES)],
            content=FLAG if is_flag else REAL_CONTENTS[counter_id % len(REAL_CONTENTS)],
        )

        Real(
            **common,
            prevent_autodiscover=is_flag,
            likes=int.from_bytes(digest[7:10], "big") % LIKES_MAX + LIKES_BASE,
        ).save()
        if counter_id >= first_logged:
            AdminLog(**common, real_salt=real_salt).save()

    Settings.objects(id="seeded").update_one(
        set__flag_counter=flag_counter,
        set__upload_rng_state=base64.b64encode(pickle.dumps(rng.getstate())).decode(),
        upsert=True,
    )
    if not User.objects(id="admin").first():
        User(
            id="admin",
            username="admin",
            password_hash=generate_password_hash(ADMIN_PASSWORD),
        ).save()


def seed_database():
    settings = Settings.objects(id="seeded").first()
    if settings and _seed_is_valid(settings):
        return
    if settings:
        _wipe()
    _seed_fresh()
