"""Contact validation, bounded rate limits and fixed-destination delivery."""

import html
import json
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.request

from frontend import config


def webhook_text(value):
    """Keep player input inside a literal block, without mentions or HTML."""
    value = ''.join(c for c in value if c in '\n\t' or not unicodedata.category(c).startswith('C'))
    return html.escape(value, quote=True).replace('@', '＠').replace('`', 'ˋ')


def validate_contact(values):
    errors = {}
    if not 1 <= len(values['name']) <= 120:
        errors['name'] = 'Enter a name of 1-120 characters.'
    if len(values['email']) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']):
        errors['email'] = 'Enter a valid email address.'
    if not 1 <= len(values['message']) <= 4000:
        errors['message'] = 'Enter a message of 1-4,000 characters.'
    return errors


class ContactLimiter:
    """One process owns the global interval and bounded per-source history."""

    def __init__(self):
        self.lock = threading.Lock()
        self.last_contact = float('-inf')
        self.client_contacts = {}

    def allow(self, client):
        with self.lock:
            now = time.monotonic()
            expired = [
                key for key, attempts in self.client_contacts.items() if now - attempts[-1] >= 60
            ]
            for key in expired:
                del self.client_contacts[key]
            attempts = [stamp for stamp in self.client_contacts.get(client, []) if now - stamp < 60]
            limited = (
                now - self.last_contact < config.CONTACT_GLOBAL_INTERVAL_SECONDS
                or len(attempts) >= config.CONTACT_REQUESTS_PER_MINUTE
            )
            # Refuse new clients when full rather than evicting active limits.
            limited = limited or (
                client not in self.client_contacts
                and len(self.client_contacts) >= config.CONTACT_MAX_CLIENTS
            )
            if not limited:
                self.last_contact = now
                self.client_contacts[client] = attempts + [now]
        return not limited


def deliver_contact(webhook, values):
    text = '\n'.join(f'{field.title()}: {webhook_text(value)}' for field, value in values.items())
    # Only text is forwarded: no user-selected channel, props, username or attachments.
    payload = json.dumps({'text': 'Feedback:\n```\n' + text + '\n```'}).encode()
    outgoing = urllib.request.Request(
        webhook, data=payload, headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(outgoing, timeout=4) as response:
            if not 200 <= response.status < 300:
                raise ValueError('Webhook rejected message')
        return 'Your enquiry has been sent.', 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return 'The message gateway is offline. Your message has not been sent.', 503
