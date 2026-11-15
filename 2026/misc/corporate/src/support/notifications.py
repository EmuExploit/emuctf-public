"""Best-effort queue notifications, after the submission commits."""

import json
import urllib.request
from email.utils import parseaddr

from support import config
from support.mail_screening import screening_report


def notify_queue(app, meta, pending_count):
    webhook = config.SUPPORT_NOTIFICATION_URL
    if not webhook:
        return
    # Keep the player-controlled title inside its code fence. Markdown escapes
    # are literal inside code blocks, so replace backticks rather than escaping.
    title = ''.join(char if char.isprintable() else ' ' for char in meta['subject']).replace(
        '`', 'ˋ'
    )
    sender = ''.join(
        char if char.isprintable() else ' ' for char in parseaddr(meta['sender'])[1]
    ).replace('`', 'ˋ')
    score = screening_report(meta)['score']
    content = (
        f'Submission Passed:\n```\n{title}\n```\n\n'
        f'From: `{sender}`\n'
        f'Reference: `{meta["id"]}`\n\n'
        f'Score: `{score}`\nBody: `{len(meta["body"])}` chars\n'
        f'Attachments: `{len(meta["files"])}`\n\n'
        f'--\n\nQueue: {pending_count} awaiting review (including this submission)'
    )
    payload = json.dumps({'content': content, 'allowed_mentions': {'parse': []}}).encode('utf-8')
    try:
        request = urllib.request.Request(
            webhook, data=payload, headers={'Content-Type': 'application/json'}, method='POST'
        )
        with urllib.request.urlopen(request, timeout=3):
            pass
    except Exception:
        app.logger.warning('Could not send queue notification')
