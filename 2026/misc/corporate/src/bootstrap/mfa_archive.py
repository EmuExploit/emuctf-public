"""Seed the public, archived 2FA handover without auto-joining new players."""

from bootstrap.channel_history import finish_channel, prepare_channel
from bootstrap.fixtures import mfa

SEED_TAG = 'mfa-decommission-v1'


def archive_message():
    rows = '\n'.join(f'| `{name}` | `{secret}` |' for name, secret in mfa.SECRETS.items())
    return (
        f'**2FA decommission — {mfa.NOTICE_DATE}**\n\n'
        'Enrolment export below for migration reconciliation. Keep until everyone '
        'confirms their replacement sign-in is working. This channel will be '
        'archived once the change is complete.\n\n'
        'Export format: Base32 seeds; TOTP / SHA-1 / 6 digits / 30 seconds. '
        'The standalone service-desk checker is staying available during the cutover.\n\n'
        '| Account | TOTP seed |\n| --- | --- |\n' + rows
    )


def seed_mfa_archive(api, bot_api, team_id, bot_id):
    spec = mfa.CHANNEL
    channel = prepare_channel(api, team_id, spec)
    path = '/channels/' + channel['id']
    existing = None
    page = 0
    while True:
        posts = api.call('GET', f'{path}/posts?per_page=200&page={page}')
        existing = next(
            (
                post
                for post in posts['posts'].values()
                if post.get('props', {}).get('corporate_seed') == SEED_TAG
            ),
            None,
        )
        if existing or len(posts['order']) < 200:
            break
        page += 1
    message = archive_message()
    if existing and existing['user_id'] != bot_id:
        raise RuntimeError('The MFA handover must be authored by IT Support')
    try:
        if not api.find(path + '/members/' + bot_id):
            api.call('POST', path + '/members', {'user_id': bot_id})
        if existing:
            if existing['message'] != message:
                api.call('PUT', '/posts/' + existing['id'] + '/patch', {'message': message})
        else:
            bot_api.call(
                'POST',
                '/posts',
                {
                    'channel_id': channel['id'],
                    'message': message,
                    'props': {'corporate_seed': SEED_TAG},
                },
            )
    finally:
        channel = finish_channel(api, channel, spec.get('archived', True))
    return channel
