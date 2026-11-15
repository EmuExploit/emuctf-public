"""Bounded, fair scheduling; socket I/O never waits for player REST requests.

An actor owns one player's recovery, chatter and delayed replies. Only one worker
can run that actor, preserving message order without a global conversation lock.
Workers take one message/maintenance turn, then return the actor to the FIFO tail.
"""

import time
import urllib.error
from collections import deque
from dataclasses import dataclass, field
from threading import Condition, Thread

from bot import config
from bot.delivery import deliver_due_questions, post_reply
from bot.recovery import RecoveryConversation, support_channel_reply
from bot.routing import route_direct_message
from bot.support_chat import SupportChatter
from common.mattermost import API


@dataclass
class Actor:
    recovery: RecoveryConversation = field(
        default_factory=lambda: RecoveryConversation(seen_limit=config.SEEN_POSTS_PER_USER)
    )
    chatter: SupportChatter = field(default_factory=SupportChatter)
    pending: dict = field(default_factory=dict)
    messages: deque = field(default_factory=deque)
    tokens: float = config.MESSAGE_BURST
    refilled: float = field(default_factory=time.monotonic)
    touched: float = field(default_factory=time.monotonic)
    queued: bool = False
    running: bool = False
    started: float = 0


class Dispatcher:
    def __init__(self, settings, api_factory=None, workers=None):
        self.settings = settings
        self.api_factory = api_factory or (
            lambda: API(token=settings['bot_token'], timeout=config.API_TIMEOUT_SECONDS)
        )
        self.actors = {}
        self.ready = deque()
        self.condition = Condition()
        self.stopping = False
        self.dropped = self.errors = self.completed = 0
        self.threads = [
            Thread(target=self._worker, name=f'bot-worker-{n}', daemon=True)
            for n in range(workers or config.WORKERS)
        ]
        for thread in self.threads:
            thread.start()

    def _schedule(self, user_id, actor):
        if not actor.queued and not actor.running:
            actor.queued = True
            self.ready.append(user_id)
            self.condition.notify()

    def submit(self, post, channel_type):
        if len(post.get('message', '')) > config.MAX_MESSAGE_CHARACTERS or (
            post['channel_id'] != self.settings['support_channel_id'] and channel_type != 'D'
        ):
            return False
        now = time.monotonic()
        with self.condition:
            if self.stopping:
                return False
            actor = self.actors.get(post['user_id'])
            if actor is None:
                # Idle actors hold no work; reclaim them before refusing users.
                for uid, old in list(self.actors.items()):
                    if (
                        not old.running
                        and not old.queued
                        and not old.messages
                        and not old.pending
                        and now - old.touched > 900
                    ):
                        del self.actors[uid]
                if len(self.actors) >= config.MAX_ACTIVE_USERS:
                    self.dropped += 1
                    return False
                actor = self.actors[post['user_id']] = Actor()
            actor.tokens = min(
                config.MESSAGE_BURST,
                actor.tokens + (now - actor.refilled) / config.MESSAGE_REFILL_SECONDS,
            )
            actor.refilled = now
            if actor.tokens < 1 or len(actor.messages) >= config.MAX_QUEUED_MESSAGES_PER_USER:
                self.dropped += 1
                return False
            actor.tokens -= 1
            actor.touched = now
            # Do not retain arbitrarily large Mattermost props/file metadata in
            # otherwise small text-message queues.
            compact = {
                key: post.get(key, '')
                for key in ('id', 'user_id', 'channel_id', 'message', 'root_id')
            }
            actor.messages.append(({**compact, '_received_at': now}, channel_type))
            self._schedule(post['user_id'], actor)
            return True

    def tick(self):
        now = time.monotonic()
        with self.condition:
            for uid, actor in self.actors.items():
                # The worker owns mutable conversation data until it yields.
                if actor.running:
                    continue
                due = any(now >= q.due or now - q.last_typing >= 3 for q in actor.pending.values())
                expired = any(
                    not s.finished
                    and not s.waiting
                    and s.awaiting_since is not None
                    and now - s.awaiting_since >= config.RECOVERY_REPLY_TIMEOUT_SECONDS
                    for s in actor.recovery.sessions.values()
                )
                if actor.messages or due or expired:
                    self._schedule(uid, actor)

    def snapshot(self):
        with self.condition:
            now = time.monotonic()
            return dict(
                work_queued=sum(len(a.messages) for a in self.actors.values()),
                workers_busy=sum(a.running for a in self.actors.values()),
                oldest_work_seconds=max(
                    (now - a.started for a in self.actors.values() if a.running), default=0
                ),
                work_completed=self.completed,
                work_errors=self.errors,
                work_dropped=self.dropped,
            )

    def _handle(self, api, actor, post, channel_type):
        if post['channel_id'] == self.settings['support_channel_id']:
            user = api.call('GET', '/users/' + post['user_id'])
            post_reply(
                api,
                post['channel_id'],
                support_channel_reply(user),
                post.get('root_id') or post['id'],
            )
            return
        channel = api.call('GET', '/channels/' + post['channel_id'])
        members = api.call('GET', '/channels/' + channel['id'] + '/members')
        if channel['type'] != 'D' or {m['user_id'] for m in members} != {
            self.settings['bot_id'],
            post['user_id'],
        }:
            return
        user = api.call('GET', '/users/' + post['user_id'])
        if not user.get('is_bot'):
            route_direct_message(api, actor.recovery, actor.pending, actor.chatter, user, post)

    def _worker(self):
        api = self.api_factory()
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.ready or self.stopping)
                if self.stopping:
                    return
                uid = self.ready.popleft()
                actor = self.actors[uid]
                actor.queued = False
                actor.running = True
                actor.started = time.monotonic()
                message = actor.messages.popleft() if actor.messages else None
            try:
                if message is not None:
                    self._handle(api, actor, *message)
                else:
                    deliver_due_questions(api, actor.recovery, actor.pending)
            except Exception as error:
                # A bad response or one player's request must not kill a worker
                # or reconnect the socket used by everybody else.
                permanent = not isinstance(error, (OSError, urllib.error.URLError)) or (
                    isinstance(error, urllib.error.HTTPError)
                    and 400 <= error.code < 500
                    and error.code not in (408, 429)
                )
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                print(f'IT Support player work failed: {type(error).__name__}', flush=True)
                with self.condition:
                    self.errors += 1
                for user_id, question in list(actor.pending.items()):
                    question.attempts += 1
                    if permanent or question.attempts >= config.DELIVERY_MAX_ATTEMPTS:
                        del actor.pending[user_id]
                    else:
                        question.due = time.monotonic() + 2**question.attempts
                        question.last_typing = time.monotonic()
                if not actor.pending:
                    for session in actor.recovery.sessions.values():
                        session.finished = True
                        session.waiting = False
                        session.awaiting_since = None
            finally:
                with self.condition:
                    actor.running = False
                    self.completed += 1
                    if actor.messages:
                        self._schedule(uid, actor)
            self.tick()

    def close(self):
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
        for thread in self.threads:
            thread.join(timeout=1)
