"""Handwritten workspace history. Public channels, never default memberships.

Each reply points to an earlier message's zero-based index in the same channel.
Dates and small gaps are historical fixtures, not sleeps during startup.
"""

import random
import urllib.error
from datetime import datetime, timedelta, timezone

from bootstrap import config
from bootstrap.channel_history import finish_channel, prepare_channel
from bootstrap.fixtures import workspace_expansion as expansion
from bootstrap.fixtures.noise import CHANNELS, LAYOFFS, PINNED
from common.mattermost import API


def seed_noise(api, team_id, actors, sessions):
    """Seed quickly with actual authors, historical dates, threads and reactions.

    Mattermost only accepts create_at from system administrators. Staff sessions
    are temporarily elevated during this startup-only import, then ALWAYS put
    back to system_user. Player roles and default memberships are never changed.
    """
    site_url = api.call('GET', '/config')['ServiceSettings']['SiteURL'].rstrip('/')
    media_url = site_url.removesuffix('/chat') + '/static/noise'
    conversations = {**CHANNELS, 'layoffs': LAYOFFS}
    staff = {person['username']: person for person in config.USERS}
    elevated = set()
    counts = {'channels': 0, 'posts': 0, 'reactions': 0}
    # Perth office hours. Channel histories start on different days in October.
    epoch = datetime(2026, 10, 5, 9, tzinfo=timezone(timedelta(hours=8)))
    try:
        for name, messages in conversations.items():
            rng = random.Random('emu-history-v1:' + name)
            print(f'Seeding workspace history: {name}', flush=True)
            channel = prepare_channel(
                api, team_id, {'name': name, 'display_name': name, 'type': 'O'}
            )
            path = '/channels/' + channel['id']

            # Only authors and a few recurring readers join. Never add $bot or
            # players, and never append these channels to conversations.CHANNELS.
            readers = set(rng.sample(sorted(staff), 2))
            readers.update(message['author'] for message in messages)
            for message in messages:
                readers.update(author for author, _ in message['reactions'])
            members = {
                member['user_id'] for member in api.call('GET', path + '/members?per_page=200')
            }
            for author in sorted(readers):
                user_id = actors[author]['id']
                if user_id not in members:
                    api.call('POST', path + '/members', {'user_id': user_id})

            existing = {}
            page = 0
            while True:
                posts = api.call('GET', f'{path}/posts?per_page=200&page={page}')
                for post in posts['posts'].values():
                    tag = post.get('props', {}).get('corporate_seed')
                    if tag is not None:
                        existing[tag] = post
                if len(posts['order']) < 200:
                    break
                page += 1

            def client(author):
                # Staff have deliberately restricted roles outside the import.
                if author not in elevated:
                    elevated.add(author)
                    api.call(
                        'PUT',
                        '/users/' + actors[author]['id'] + '/roles',
                        {'roles': 'system_user system_admin'},
                    )
                    # Login again so the session definitely sees the import role.
                    if author in sessions:
                        sessions[author].call('POST', '/users/logout')
                    sessions[author] = API()
                    sessions[author].call(
                        'POST',
                        '/users/login',
                        {'login_id': author, 'password': staff[author]['password']},
                    )
                return sessions[author]

            timestamp = int(
                (epoch + timedelta(days=rng.randrange(18), hours=rng.randrange(8))).timestamp()
                * 1000
            )
            seeded = []
            for index, message in enumerate(messages):
                timestamp += rng.choice((32, 58, 95, 180, 420, 1500, 4200)) * 1000
                tag = f'noise:v1:{name}:{index}'
                text = message['message'].replace('$MEDIA', media_url)
                root_id = ''
                if message['reply'] is not None:
                    parent = seeded[message['reply']]
                    root_id = parent.get('root_id') or parent['id']
                post = existing.get(tag)
                file_ids = post.get('file_ids', []) if post else []
                if message.get('file') and not file_ids:
                    filename = message['file']
                    file_ids = [
                        client(message['author']).upload_file(
                            channel['id'], filename, expansion.FILES[filename]
                        )
                    ]
                if post:
                    if post['user_id'] != actors[message['author']]['id']:
                        raise RuntimeError(f'Unexpected author for {tag}')
                    if post['message'] != text or post.get('file_ids', []) != file_ids:
                        post = client(message['author']).call(
                            'PUT',
                            '/posts/' + post['id'] + '/patch',
                            {'message': text, 'file_ids': file_ids},
                        )
                else:
                    post = client(message['author']).call(
                        'POST',
                        '/posts?set_online=false',
                        {
                            'channel_id': channel['id'],
                            'message': text,
                            'root_id': root_id,
                            'create_at': timestamp,
                            'file_ids': file_ids,
                            'props': {'corporate_seed': tag},
                        },
                    )
                    if post['create_at'] != timestamp:
                        raise RuntimeError('Mattermost did not preserve the historical post date')
                    counts['posts'] += 1
                seeded.append(post)

                # Seeded RNG keeps reactions stable across restarts. Draw from
                # real channel members and avoid reacting to your own message.
                reactions = list(message['reactions'])
                if rng.random() < 0.4:
                    candidates = sorted(readers - {message['author']})
                    for reader in rng.sample(candidates, min(len(candidates), rng.randint(1, 3))):
                        reactions.append(
                            (reader, rng.choice(('+1', 'eyes', 'joy', 'sob', 'heart')))
                        )
                present = api.call('GET', '/posts/' + post['id'] + '/reactions') or []
                present = {(item['user_id'], item['emoji_name']) for item in present}
                for reader, emoji in reactions:
                    if (actors[reader]['id'], emoji) not in present:
                        client(reader).call(
                            'POST',
                            '/reactions',
                            {
                                'user_id': actors[reader]['id'],
                                'post_id': post['id'],
                                'emoji_name': emoji,
                            },
                        )
                        counts['reactions'] += 1
                if index in PINNED.get(name, ()) and not post.get('is_pinned'):
                    api.call('POST', '/posts/' + post['id'] + '/pin')
            finish_channel(api, channel, name in expansion.ARCHIVED_CHANNELS)
    finally:
        # Attempt every cleanup even if one API call fails. Bootstrap also resets
        # staff roles before imports, recovering safely from an interrupted run.
        failures = []
        for author in sorted(elevated):
            try:
                api.call(
                    'PUT', '/users/' + actors[author]['id'] + '/roles', {'roles': 'system_user'}
                )
            except (OSError, urllib.error.URLError) as error:
                failures.append(author)
                print(
                    f'Could not restore staff role for {author}: {type(error).__name__}', flush=True
                )
        if failures:
            raise RuntimeError('Staff role restoration failed: ' + ', '.join(failures))
    print(f'Workspace history ready: {counts}', flush=True)
    return counts
