"""Mailbox states and public/reviewer response projections."""

from datetime import datetime, timezone

from support import config
from support.mail_screening import screening_report, screening_tags

ADMIN_PATH = config.SUPPORT_ADMIN_PATH
REVIEW_STATES = {
    'new': 'NEW',
    'spam': 'SPAM',
    'flag': 'FLAG',
    'bad_email': 'BAD EMAIL',
    'bad_payload': 'BAD PAYLOAD',
    'other': 'OTHER',
}


def queue_summary(meta):
    report = screening_report(meta)
    return dict(
        id=meta['id'],
        created=meta['created'],
        sender=meta.get('sender', ''),
        subject=meta.get('subject', ''),
        tags=screening_tags(report=report),
        attachments=len(meta.get('files', [])),
        score=report['score'],
    )


def review_tab(state):
    return 'queue' if state == 'new' else 'accepted' if state == 'flag' else 'rejected'


def apply_automatic_rejection(meta):
    report = screening_report(meta)
    state = report['suggested_state']
    if state:
        meta.update(
            state=state,
            status='rejected',
            auto_rejection=dict(
                state=state,
                scores=report['scores'],
                thresholds=report['thresholds'],
                triggered=report['triggered'],
                at=datetime.now(timezone.utc).isoformat(),
            ),
        )
    return state


def player_result(meta):
    """Allowlisted receipt; never expose evidence or other attempts' references."""
    report = screening_report(meta)
    rejected = bool(meta.get('auto_rejection'))
    return dict(
        id=meta['id'],
        created=meta['created'],
        outcome='rejected' if rejected else 'accepted',
        message=(
            ''
            if rejected
            else 'This is not a challenge acceptance. To execute your payload, please find torry2\n\n'
            'Please save your reference. If this was a test/spam this attempt will be discarded.'
        ),
        scores=report['scores'],
        thresholds=report['thresholds'],
        triggered=report['triggered'],
        signals=[
            {
                key: signal[key]
                for key in ('label', 'source', 'points', 'rule_points', 'covered_by')
                if key in signal
            }
            for signal in report['signals']
        ],
    )
