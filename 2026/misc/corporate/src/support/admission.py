"""Fair upload admission; call while holding BEGIN IMMEDIATE."""

import math

from support import config


def submission_capacity(db, owner, source, now, enqueue=False):
    db.execute('DELETE FROM submission_waiters WHERE expires<=?', (now,))
    recent, oldest = db.execute(
        'SELECT COUNT(*), MIN(stamp) FROM submission_attempts WHERE client=? AND stamp>?',
        (owner, now - 60),
    ).fetchone()
    active = db.execute(
        'SELECT COUNT(*) FROM submission_attempts WHERE processing_until>?', (now,)
    ).fetchone()[0]
    head = db.execute('SELECT owner FROM submission_waiters ORDER BY position LIMIT 1').fetchone()
    # Once the head can submit, polling cannot extend its lease forever.
    # Ninety seconds accommodates the 60-second upload deadline plus retries.
    if active >= config.SUPPORT_MAX_CONCURRENT_SUBMISSIONS or (head and head[0] != owner):
        db.execute(
            'UPDATE submission_waiters SET expires=? WHERE owner=?',
            (now + config.SUPPORT_WAITER_LEASE_SECONDS, owner),
        )
    count = db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0]
    if count + active >= config.SUPPORT_MAX_SUBMISSIONS:
        return dict(
            error='The support queue is full. Please contact the organizers.', code='queue_full'
        )
    if recent >= config.SUBMISSIONS_PER_MINUTE:
        db.execute('DELETE FROM submission_waiters WHERE owner=?', (owner,))
        return dict(
            error='Waiting for your submission limit to reset.',
            code='rate_limited',
            retry_after=max(1, math.ceil(oldest + 60 - now)),
        )
    source_recent, source_oldest = db.execute(
        'SELECT COUNT(*), MIN(stamp) FROM submission_source_attempts WHERE client=? AND stamp>?',
        (source, now - 60),
    ).fetchone()
    if source_recent >= config.SUBMISSIONS_PER_SOURCE_PER_MINUTE:
        db.execute('DELETE FROM submission_waiters WHERE owner=?', (owner,))
        return dict(
            error='Waiting for the network submission limit to reset.',
            code='rate_limited',
            retry_after=max(1, math.ceil(source_oldest + 60 - now)),
        )
    if active >= config.SUPPORT_MAX_CONCURRENT_SUBMISSIONS or (head and head[0] != owner):
        if enqueue:
            waiting = db.execute('SELECT COUNT(*) FROM submission_waiters').fetchone()[0]
            if waiting < config.SUPPORT_MAX_WAITERS:
                db.execute(
                    'INSERT OR IGNORE INTO submission_waiters(owner, expires) VALUES (?, ?)',
                    (owner, now + config.SUPPORT_WAITER_LEASE_SECONDS),
                )
        return dict(
            error='Waiting for your turn in the submission queue.', code='busy', retry_after=3
        )
    return None
