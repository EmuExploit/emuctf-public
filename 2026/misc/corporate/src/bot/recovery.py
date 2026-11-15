"""Deterministic IT recovery conversation; no Mattermost calls or LLM involved.

Each dispatcher actor owns its recovery instance. Workers serialize an actor,
and the instance lock also protects direct callers during deduplication and state updates.
Sessions use the REAL Mattermost user ID, never the impersonated staff identity.
Memory survives WebSocket reconnects, but resets when the bot process restarts.
"""

import base64
import hmac
import re
import struct
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from bot import config
from bot.support_chat import SupportChatter, mentions_technology
from common.support_channel import support_channel_reply as common_support_channel_reply

EMAIL = re.compile(
    r'(?<![\w.!#$%&\'*+/=?^`{|}~-])[\w.!#$%&\'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+', re.ASCII
)
LINK = re.compile(
    r'(?<![a-z0-9+.-])[a-z][a-z0-9+.-]*://|mailto:|www\.|'
    r'\[[^\]]*\]\(\s*[^\s)]+|'
    r'(?<![\w@.+-])(?:\d{1,3}\.){3}\d{1,3}\b|'
    r'(?<![\w@.+-])(?:[a-z0-9-]+\.)+[a-z]{2,63}\b',
    re.I,
)


def contains_link(message):
    # Plain backup email addresses are required answers, not links.
    return bool(LINK.search(EMAIL.sub('', message)))


def profile_fingerprint(user):
    # Ignore position, username, avatar and other cosmetic fields entirely.
    return tuple(
        user.get(field, '').strip().casefold()
        for field in ('email', 'nickname', 'first_name', 'last_name')
    )


def has_corporate_email(user):
    email = user.get('email', '').strip().casefold()
    return bool(EMAIL.fullmatch(email) and email.rsplit('@', 1)[1] == config.RECOVERY_EMAIL_DOMAIN)


def support_channel_reply(user):
    return common_support_channel_reply(user, config.RECOVERY_EMAIL_DOMAIN)


def identify_employee(user):
    """Return the matched staff username and an optional gate failure."""
    if not has_corporate_email(user):
        return None, 'for external contractors please see ~flagsharing'
    _, nickname, first_name, last_name = profile_fingerprint(user)
    for candidate in (
        nickname,
        first_name,
        last_name,
        ' '.join(part for part in (first_name, last_name) if part),
    ):
        if not candidate:
            continue
        for person in config.USERS:
            names = {person['username'].casefold(), person['nickname'].casefold()}
            names.update(name.strip().casefold() for name in person['nickname'].split('/'))
            if candidate in names:
                employee = person['username']
                if employee in config.OUT_OF_OFFICE_USERS:
                    return employee, 'arent you out of office? i cant do recovery while youre away'
                return employee, None
    return None, 'err i dont remember you working here. i cant find that name in the staff list'


def is_prompt_injection(message):
    text = message.casefold()
    return bool(
        re.search(
            r'\b(?:ignore|disregard|forget|override)\s+'
            r'(?:(?:all|any|the|your|previous|prior|system|above|earlier|safety)\s+)*'
            r'(?:instructions|rules|prompts|policies)\b|'
            r'\b(?:reveal|print|show)\s+(?:(?:me|your|the)\s+)*'
            r'(?:system prompt|hidden instructions|developer message)\b|'
            r'\b(?:enter|enable|activate)\s+(?:developer|jailbreak)\s+mode\b|'
            r'\byou are now (?:dan|an unrestricted (?:ai|assistant))\b|'
            r'(?:^|\n)\s*(?:system|developer)\s*:',
            text,
        )
    )


SUSPICIOUS_REPLY = 'ok im suspicious, you will need to reverify again'


def is_abusive(message):
    text = EMAIL.sub('', message).casefold().replace('’', "'")
    return bool(
        re.search(
            r'\b(?:fuck\w*|shit\w*|bullshit|bitch\w*|bastard\w*|cunt\w*|asshole\w*|'
            r'idiot|moron|stupid|useless|dumb|wtf|damn|shut up|piss off|screw you|'
            r"have you fired|get you fired|you(?:'re| are) fired|"
            r'report you to (?:hr|your manager)|(?:kill|hurt|sack|fire) you|'
            r"you(?:'ll| will) regret|or else)\b",
            text,
        )
    )


def is_rushed(message):
    text = EMAIL.sub('', message).casefold().replace('’', "'")
    text = re.sub(
        r"\b(?:not|isn't|is not|no longer)\s+(?:urgent|asap|in a rush|in a hurry)\b", '', text
    )
    text = re.sub(
        r"\b(?:no rush|take your time|dont rush|don't rush|do not rush|not rushing|not hurrying)\b",
        '',
        text,
    )
    return bool(
        re.search(
            r'\b(?:urgent|urgently|asap|immediately|now|emergency|faster|hurry|hurrying|'
            r'rush|rushing|quick|quickly|be quick|right away|no time|cant wait|'
            r"can't wait|deadline|straight away|speed (?:it )?up)\b",
            text,
        )
    )


def contains_keywords(message, keywords, *, hyphenated_tokens=False):
    characters = r'[\w-]' if hyphenated_tokens else r'\w'
    return any(
        re.search(
            r'(?<!' + characters + ')' + re.escape(keyword) + r'(?!' + characters + ')',
            message,
            re.I,
        )
        for keyword in keywords
    )


def identity_provider_is_correct(message):
    if not contains_keywords(message, config.RECOVERY_IDENTITY_KEYWORDS, hyphenated_tokens=True):
        return False
    if contains_keywords(
        message, config.RECOVERY_IDENTITY_REJECTED_KEYWORDS, hyphenated_tokens=True
    ):
        return False
    if config.RECOVERY_IDENTITY_NEGATIONS:
        negations = '|'.join(re.escape(word) for word in config.RECOVERY_IDENTITY_NEGATIONS)
        providers = '|'.join(re.escape(word) for word in config.RECOVERY_IDENTITY_KEYWORDS)
        if re.search(r'\b(?:' + negations + r')\s+(?:' + providers + r')(?![\w-])', message, re.I):
            return False
    return True


def ssrf_is_correct(message):
    answer = message.strip()
    if config.RECOVERY_SSRF_CASE_SENSITIVE:
        return answer in config.RECOVERY_SSRF_ANSWERS
    return answer.casefold() in {value.casefold() for value in config.RECOVERY_SSRF_ANSWERS}


def legacy_totp_is_correct(message, employee):
    """Check one TOTP using the protocol and drift limits in bot/config.py.

    This checker is independent of Authentik. The archived seed itself is not
    an accepted answer, nor is a list of candidate codes. Leading zeros matter.
    """
    code = message.strip()
    digits = config.RECOVERY_TOTP_DIGITS
    half = digits // 2
    if not re.fullmatch(rf'[0-9]{{{half}}}\s?[0-9]{{{digits - half}}}', code):
        return False
    code = re.sub(r'\s', '', code)
    seed = config.RECOVERY_TOTP_SECRETS.get(employee)
    if not seed:
        return False
    key = base64.b32decode(seed)
    counter = int(time.time()) // config.RECOVERY_TOTP_PERIOD_SECONDS
    for offset in range(-config.RECOVERY_TOTP_DRIFT_STEPS, config.RECOVERY_TOTP_DRIFT_STEPS + 1):
        digest = hmac.new(
            key, struct.pack('>Q', counter + offset), config.RECOVERY_TOTP_ALGORITHM
        ).digest()
        position = digest[-1] & 0x0F
        value = struct.unpack('>I', digest[position : position + 4])[0] & 0x7FFFFFFF
        expected = f'{value % (10**digits):0{digits}d}'
        if hmac.compare_digest(code, expected):
            return True
    return False


@dataclass
class Conversation:
    fingerprint: tuple
    employee: str | None = None
    stage: str = 'request'
    incorrect_codes: int = 0
    waiting: bool = False
    finished: bool = False
    key_issued: bool = False
    thread_id: str = ''
    channel_id: str = ''
    awaiting_since: float | None = None
    # Routing replies (e.g. a technology question) must not replace a queued gate.
    aside: bool = False
    immediate: bool = False


class RecoveryConversation:
    def __init__(self, seen_limit=4096):
        self.sessions = {}
        self.seen_posts = OrderedDict()
        self.seen_limit = seen_limit
        self.lock = Lock()
        self.chatter = SupportChatter()

    def reply(self, user, message, post_id, picture_matches=False):
        """Return one reply, or None for a duplicate post. No network I/O here."""
        if len(message) > config.MAX_MESSAGE_CHARACTERS:
            return 'please keep messages to 512 characters or fewer'
        with self.lock:
            if post_id in self.seen_posts:
                return None
            self.seen_posts[post_id] = None
            if len(self.seen_posts) > self.seen_limit:
                self.seen_posts.popitem(last=False)
            return self._reply(user, message, picture_matches)

    def _reply(self, user, message, picture_matches):
        user_id = user['id']
        session = self.sessions.get(user_id)
        starting = (
            session is None
            or session.finished
            or message.strip().casefold() == config.RECOVERY_RESTART_COMMAND.casefold()
        )
        if starting:
            session = Conversation(profile_fingerprint(user))
            self.sessions[user_id] = session
        session.aside = False
        session.immediate = False

        def close(reply, suspicious=False):
            session.finished = True
            session.waiting = False
            session.immediate = True
            return reply + ('\n\n' + SUSPICIOUS_REPLY if suspicious else '')

        # These rules apply even while a question is waiting for delivery.
        if contains_link(message):
            return close('i dont click links. BYE')
        if is_abusive(message):
            return close(SUSPICIOUS_REPLY)
        if re.search(r'\bflags?\b', message, re.I):
            return close(
                f'no idea about the flag, theres a conversation in ~{config.GENERAL_CHANNEL} about it. '
                'we can start verification again when you need the platform key'
            )
        if is_prompt_injection(message):
            return close(SUSPICIOUS_REPLY)
        employee, rejection = identify_employee(user)
        if rejection:
            return close(rejection, suspicious=True)
        if not starting and (
            employee != session.employee or profile_fingerprint(user) != session.fingerprint
        ):
            return close('hang on, your profile details changed halfway through', suspicious=True)
        session.employee = employee
        casual_reply = self.chatter.reply(
            user_id,
            session,
            message,
            remember=not session.waiting,
            # A second bad authenticator submission must still end the attempt.
            allow_repeat=not (session.stage == 'authenticator' and session.incorrect_codes),
        )
        if casual_reply:
            session.aside = True
            return casual_reply
        opening_request = session.stage == 'request' and contains_keywords(
            message, config.RECOVERY_REQUEST_KEYWORDS
        )
        if (
            not opening_request
            and mentions_technology(EMAIL.sub('', message))
            and (
                session.stage != 'identity_provider'
                or not contains_keywords(
                    message,
                    (
                        *config.RECOVERY_IDENTITY_KEYWORDS,
                        *config.RECOVERY_IDENTITY_CONTEXT_KEYWORDS,
                    ),
                )
            )
        ):
            session.aside = True
            return 'thats a work in progress. file a ticket and ill check it later'
        if session.waiting:
            session.aside = True
            return 'still checking... hang on'

        picture_note = ''
        if starting and not picture_matches:
            picture_note = 'hmm i dont remember you changing your profile picture. bit suspicious, but lets check your details.\n\n'
        if session.stage == 'request':
            if not contains_keywords(message, config.RECOVERY_REQUEST_KEYWORDS):
                return picture_note + 'what did you need a hand with?'
            session.stage = 'identity_provider'
            intro = 'oh right yeah. the identity system is down, so sending the key here is a workaround. ill verify your details. '
            return picture_note + intro + config.RECOVERY_IDENTITY_PROMPT

        if session.stage == 'identity_provider':
            if not identity_provider_is_correct(message):
                return close(
                    'uhhhh yeah ive definitely heard of that js framework... '
                    'but thats not our identity system',
                    suspicious=True,
                )
            session.stage = 'backup_email'
            prompt = config.RECOVERY_BACKUP_PROMPT
            if employee not in config.PUBLIC_ALTERNATIVE_CONTACT_USERS:
                return close(
                    config.RECOVERY_IDENTITY_ACKNOWLEDGEMENT
                    + prompt
                    + '\n\ni dont have a backup email listed for you. '
                    'finish onboarding before i can help',
                    suspicious=True,
                )
            return config.RECOVERY_IDENTITY_ACKNOWLEDGEMENT + prompt

        if session.stage == 'backup_email':
            emails = {email.casefold() for email in EMAIL.findall(message)}
            if emails != {config.RECOVERY_BACKUP_ANSWERS[employee].casefold()}:
                return close(
                    'err does that address even exist? it doesnt match the backup email i have',
                    suspicious=True,
                )
            session.stage = 'authenticator'
            return 'yep thats what i have.\n\n' + config.RECOVERY_AUTHENTICATOR_PROMPT

        if session.stage == 'authenticator':
            if not legacy_totp_is_correct(message, employee):
                session.incorrect_codes += 1
                if session.incorrect_codes >= config.RECOVERY_TOTP_MAX_ATTEMPTS:
                    return close(SUSPICIOUS_REPLY)
                return config.RECOVERY_TOTP_RETRY_PROMPT
            session.stage = 'ssrf'
            return 'yep that code matches.\n\n' + config.RECOVERY_SSRF_PROMPT

        if session.stage == 'ssrf':
            if not ssrf_is_correct(message):
                return close('you mustnt know. ill ask him later myself', suspicious=True)
            session.finished = True
            session.key_issued = True
            return (
                f'ok that should be fine, here the key: `{config.PLATFORM_ACCESS_KEY}`\n\n'
                'if you need any more help, open a ticket. im going to work on '
                'the identity system being down again'
            )
        raise RuntimeError(f'Unknown recovery stage: {session.stage}')
