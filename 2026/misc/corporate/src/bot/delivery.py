"""Bounded reply delivery and delayed-question maintenance."""

import time
import urllib.error
from dataclasses import dataclass

from bot import config
from bot.recovery import Conversation


@dataclass
class PendingQuestion:
    due: float
    channel_id: str
    message: str
    session: Conversation
    root_id: str = ''
    last_typing: float = 0
    followups: tuple = ()
    attempts: int = 0


def post_reply(api, channel_id, message, root_id='', followups=()):
    payload = {'channel_id': channel_id, 'message': message[: config.MAX_REPLY_CHARACTERS]}
    if root_id:
        payload['root_id'] = root_id
    api.call('POST', '/posts', payload)
    for followup in followups:
        api.call('POST', '/posts', {**payload, 'message': followup[: config.MAX_REPLY_CHARACTERS]})


def publish_typing(api, channel_id, root_id=''):
    # Cosmetic events must never stop verification if Mattermost rejects them.
    try:
        api.call('POST', '/users/me/typing', {'channel_id': channel_id, 'parent_id': root_id})
    except (OSError, urllib.error.URLError) as error:
        print(f'IT Support typing indicator unavailable: {type(error).__name__}', flush=True)
        if isinstance(error, urllib.error.HTTPError):
            error.close()


def deliver_due_questions(api, recovery, pending):
    """Deliver replies and refresh typing without sleeping the socket loop."""
    now = time.monotonic()
    for user_id, question in list(pending.items()):
        session = recovery.sessions.get(user_id)
        if session is not question.session:
            del pending[user_id]
        elif now >= question.due:
            try:
                post_reply(
                    api, question.channel_id, question.message, question.root_id, question.followups
                )
            except (OSError, urllib.error.URLError) as error:
                question.attempts += 1
                permanent = (
                    isinstance(error, urllib.error.HTTPError)
                    and 400 <= error.code < 500
                    and error.code not in (408, 429)
                )
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                if permanent or question.attempts >= config.DELIVERY_MAX_ATTEMPTS:
                    del pending[user_id]
                    session.waiting = False
                    session.finished = True
                    session.awaiting_since = None
                    print('IT Support discarded an undeliverable question.', flush=True)
                else:
                    question.due = time.monotonic() + 2**question.attempts
                continue
            session.waiting = False
            session.awaiting_since = time.monotonic()
            del pending[user_id]
        elif now - question.last_typing >= 3:
            publish_typing(api, question.channel_id, question.root_id)
            question.last_typing = now
    expire_recovery_attempts(api, recovery, pending, now)


def expire_recovery_attempts(api, recovery, pending, now=None):
    """Only time spent awaiting a player's reply counts toward the timeout."""
    now = time.monotonic() if now is None else now
    expired = set()
    for user_id, session in recovery.sessions.items():
        if (
            session.finished
            or session.waiting
            or session.awaiting_since is None
            or now - session.awaiting_since < config.RECOVERY_REPLY_TIMEOUT_SECONDS
        ):
            continue
        session.finished = True
        session.awaiting_since = None
        pending.pop(user_id, None)
        post_reply(
            api,
            session.channel_id,
            'youre taking too long, i have other work to do. start a fresh verification when youre ready',
            session.thread_id,
        )
        expired.add(user_id)
    return expired
