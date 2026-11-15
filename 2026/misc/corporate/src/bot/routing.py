"""Route direct messages without owning the WebSocket or worker pool."""

import random
import re
import time

from bot import config
from bot.delivery import PendingQuestion, expire_recovery_attempts, post_reply, publish_typing
from bot.profile_images import profile_picture_matches
from bot.recovery import (
    EMAIL,
    contains_keywords,
    contains_link,
    identify_employee,
    is_abusive,
    is_prompt_injection,
    is_rushed,
)
from bot.support_chat import KEY_SHARING_WARNING, casual_reply


def is_terminal_message(message):
    return (
        contains_link(message)
        or is_abusive(message)
        or is_prompt_injection(message)
        or re.search(r'\bflags?\b', message, re.I)
    )


def handle_direct_message(api, recovery, pending, user, post):
    """Handle a verification-thread message; chat routing happens separately."""
    previous = recovery.sessions.get(user['id'])
    previous_stage = previous.stage if previous else None
    starting = (
        previous is None
        or previous.finished
        or post['message'].strip().casefold() == config.RECOVERY_RESTART_COMMAND.casefold()
    )
    picture_matches = False
    if starting and not is_terminal_message(post['message']):
        employee, rejection = identify_employee(user)
        if not rejection:
            picture_matches = profile_picture_matches(api, user, employee)
    reply = recovery.reply(user, post['message'], post['id'], picture_matches)
    if reply is None:
        return
    session = recovery.sessions[user['id']]
    root_id = post.get('root_id', '')
    session.thread_id = root_id
    session.channel_id = post['channel_id']
    followups = (KEY_SHARING_WARNING,) if session.key_issued else ()
    queued = pending.get(user['id'])
    if queued and (queued.session is not session or session.immediate):
        del pending[user['id']]
        queued = None
    rushed = is_rushed(post['message']) and not session.immediate
    advanced = session is not previous or session.stage != previous_stage
    pause = (
        not rushed
        and advanced
        and not session.finished
        and not session.aside
        and session.stage != 'request'
        and random.random() < config.RECOVERY_RANDOM_DELAY_CHANCE
    )
    if rushed or pause:
        now = time.monotonic()
        due = now + random.randint(*config.RECOVERY_DELAY_SECONDS)
        if queued and session.aside:
            # An aside must not grow or indefinitely postpone the queued gate.
            pass
        else:
            session.waiting = True
            pending[user['id']] = PendingQuestion(
                due=due,
                channel_id=post['channel_id'],
                message=reply,
                session=session,
                root_id=root_id,
                last_typing=now,
                followups=followups,
            )
        reply = (
            'dont rush me. give me a moment to check'
            if rushed
            else random.choice(config.RECOVERY_PAUSE_MESSAGES)
        )
        followups = ()
    post_reply(api, post['channel_id'], reply, root_id, followups)
    if not session.finished and not session.waiting:
        session.awaiting_since = time.monotonic()
    if rushed or pause:
        # A posted message clears typing in the client: publish after "1 sec".
        publish_typing(api, post['channel_id'], root_id)


def route_direct_message(api, recovery, pending, chatter, user, post):
    """Only an explicit key/platform request opens a verification thread."""
    if len(post['message']) > config.MAX_MESSAGE_CHARACTERS:
        return
    text = EMAIL.sub('', post['message'])
    session = recovery.sessions.get(user['id'])
    root_id = post.get('root_id', '')
    expired = expire_recovery_attempts(api, recovery, pending, post.get('_received_at'))
    if user['id'] in expired and root_id == session.thread_id:
        return
    if is_terminal_message(post['message']):
        handle_direct_message(api, recovery, pending, user, post)
        return
    requested = contains_keywords(text, config.RECOVERY_REQUEST_KEYWORDS)
    restart = post['message'].strip().casefold() == config.RECOVERY_RESTART_COMMAND.casefold()
    if requested or restart:
        # A request in an old thread gets a new top-level root of its own.
        if root_id:
            root = api.call(
                'POST',
                '/posts',
                {
                    'channel_id': post['channel_id'],
                    'message': 'oh right yeah, lets start a fresh verification here',
                },
            )
            thread_id = root['id']
        else:
            thread_id = post['id']
        if session:
            session.finished = True
        pending.pop(user['id'], None)
        verification_post = {**post, 'root_id': thread_id}
        if restart:
            verification_post['message'] = config.RECOVERY_REQUEST_KEYWORDS[0]
        handle_direct_message(api, recovery, pending, user, verification_post)
        return
    if session and not session.finished and root_id and root_id == session.thread_id:
        handle_direct_message(api, recovery, pending, user, post)
        return
    reply = casual_reply(chatter, user['id'], text)
    post_reply(api, post['channel_id'], reply, root_id)
