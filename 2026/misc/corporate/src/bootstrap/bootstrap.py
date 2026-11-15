"""Create the workspace before starting the public listener and bot."""

import json
import time
import urllib.error

from bootstrap import config
from bootstrap.discussion_history import seed_archived_discussion
from bootstrap.fixtures import authentik, conversations, identities, ssrf, workspace
from bootstrap.mfa_archive import seed_mfa_archive
from bootstrap.noise import seed_noise
from bootstrap.player_permissions import restrict_player_permissions
from bootstrap.profile_images import seed_profile_images
from common.mattermost import API, FRONTEND_RUNTIME, RUNTIME
from common.support_channel import support_channel_reply


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


def setup():
    started = time.monotonic()
    api = API()
    print('Waiting for Mattermost to start (ARM emulation can take a few minutes)...', flush=True)
    for attempt in range(config.WAIT_ATTEMPTS):
        try:
            api.call('GET', '/system/ping')
            break
        except (OSError, urllib.error.URLError):
            if attempt and attempt % 10 == 0:
                print(
                    f'Still waiting for Mattermost ({time.monotonic() - started:.0f}s elapsed)...',
                    flush=True,
                )
            time.sleep(config.WAIT_INTERVAL_SECONDS)
    else:
        raise RuntimeError('Mattermost did not start')

    if RUNTIME.exists():
        try:
            saved = json.loads(RUNTIME.read_text())
            current = API(token=saved['bot_token']).call('GET', '/users/me')
            if current['id'] == saved['bot_id'] and (
                FRONTEND_RUNTIME.exists() or saved.get('contact_webhook_url')
            ):
                # Migrate the previous shared runtime without exposing its token
                # through the new frontend-only volume.
                if not FRONTEND_RUNTIME.exists():
                    write_json(
                        FRONTEND_RUNTIME, {'contact_webhook_url': saved['contact_webhook_url']}
                    )
                if 'contact_webhook_url' in saved:
                    saved.pop('contact_webhook_url')
                    write_json(RUNTIME, saved)
                print(
                    'Existing Mattermost setup is ready; keeping bot credentials and chat.',
                    flush=True,
                )
                return
        except (OSError, ValueError, KeyError):
            pass

    print('Mattermost is responding; configuring organiser access.', flush=True)
    login = {'login_id': config.ADMIN['username'], 'password': config.ADMIN['password']}
    try:
        admin = api.call('POST', '/users/login', login)
    except urllib.error.HTTPError as error:
        if error.code not in (400, 401):
            raise
        api.call('POST', '/users', config.ADMIN)
        admin = api.call('POST', '/users/login', login)

    print('Restricting member permissions to existing channels and direct messages.', flush=True)
    restrict_player_permissions(api)

    print('Configuring the team and IT Support bot.', flush=True)
    team = api.find('/teams/name/' + workspace.TEAM['name'])
    if not team:
        team = api.call(
            'POST', '/teams', {**workspace.TEAM, 'type': 'O', 'allow_open_invite': True}
        )
    team_path = '/teams/' + team['id']
    bot = api.find('/users/username/' + workspace.BOT['username'])
    if not bot:
        created = api.call('POST', '/bots', workspace.BOT)
        bot = api.call('GET', '/users/' + created['user_id'])
    bot = api.call(
        'PUT',
        '/users/' + bot['id'] + '/patch',
        {
            'first_name': workspace.BOT['display_name'],
            'nickname': workspace.BOT['display_name'],
        },
    )
    for token in api.call('GET', '/users/' + bot['id'] + '/tokens'):
        if token['description'] == 'corporate bot':
            api.call('POST', '/users/tokens/revoke', {'token_id': token['id']})
    bot_token = api.call(
        'POST', '/users/' + bot['id'] + '/tokens', {'description': 'corporate bot'}
    )['token']

    actors = {'$admin': admin, '$bot': bot}
    sessions = {'$admin': api, '$bot': API(token=bot_token)}
    staff_credentials = {spec['username']: spec['password'] for spec in config.USERS}
    for spec in config.USERS:
        username = spec['username']
        print(
            f'Preparing staff account {len(actors) - 1}/{len(config.USERS)}: {username}', flush=True
        )
        user = api.find('/users/username/' + username)
        password = spec['password']
        profile = {'nickname': spec['nickname'], 'position': spec['position']}
        if not user:
            user = api.call('POST', '/users', {**spec, **profile, 'password': password})
        elif any(user.get(key) != value for key, value in profile.items()):
            user = api.call('PUT', '/users/' + user['id'] + '/patch', profile)
        actors[username] = user
        # Recover a temporary historical-import role if startup was interrupted.
        if user.get('roles') != 'system_user':
            api.call('PUT', '/users/' + user['id'] + '/roles', {'roles': 'system_user'})
    print('Setting staff and IT Support profile pictures.', flush=True)
    seed_profile_images(api, actors.values())
    print('Adding staff to the team.', flush=True)
    for user in actors.values():
        api.call('POST', team_path + '/members', {'team_id': team['id'], 'user_id': user['id']})

    channels = {}
    for spec in conversations.CHANNELS:
        print(f'Preparing channel: {spec["name"]}', flush=True)
        channel = api.find(team_path + '/channels/name/' + spec['name'])
        if not channel:
            channel = api.call(
                'POST',
                '/channels',
                {**{k: v for k, v in spec.items() if k != 'members'}, 'team_id': team['id']},
            )
        elif channel['display_name'] != spec['display_name']:
            channel = api.call(
                'PUT',
                '/channels/' + channel['id'] + '/patch',
                {'display_name': spec['display_name']},
            )
        channels[spec['name']] = channel['id']
        members = set(spec.get('members', [])) | {'$admin'}
        members.update(m['author'] for m in conversations.MESSAGES if m['channel'] == spec['name'])
        if spec['name'] == workspace.SUPPORT_CHANNEL:
            members.add('$bot')
        for member in members:
            api.call(
                'POST', '/channels/' + channel['id'] + '/members', {'user_id': actors[member]['id']}
            )

    # Earlier builds created a separate General; the required default now fills that role.
    if workspace.GENERAL_CHANNEL == 'town-square':
        old_general = api.find(team_path + '/channels/name/general')
        if old_general and not old_general.get('delete_at'):
            print('Archiving the replaced standalone General channel.', flush=True)
            api.call('DELETE', '/channels/' + old_general['id'])

    # Mattermost joins these channels whenever a player joins the team.
    # Seeding staff memberships alone does not affect newly registered users.
    print('Configuring automatic channel membership for new players.', flush=True)
    api.call(
        'PUT',
        '/config/patch',
        {
            'TeamSettings': {
                'ExperimentalViewArchivedChannels': True,
                'EnableCustomUserStatuses': True,
                'TeammateNameDisplay': 'nickname_full_name',
                'LockTeammateNameDisplay': True,
                'ExperimentalDefaultChannels': [
                    channel['name'] for channel in conversations.CHANNELS if channel['type'] == 'O'
                ],
            }
        },
    )

    print('Setting out-of-office staff statuses.', flush=True)
    for username in identities.OUT_OF_OFFICE_USERS:
        api.call(
            'PUT',
            '/users/' + actors[username]['id'] + '/status/custom',
            {
                'emoji': 'palm_tree',
                'text': 'Out of office',
                'duration': '',
            },
        )
    for spec in config.USERS:
        username = spec['username']
        if username in identities.OUT_OF_OFFICE_USERS:
            continue
        status = json.loads(actors[username].get('props', {}).get('customStatus') or '{}')
        if status.get('text') == 'Out of office' and status.get('emoji') == 'palm_tree':
            api.call('DELETE', '/users/' + actors[username]['id'] + '/status/custom')

    for username, (emoji, text) in conversations.STAFF_CUSTOM_STATUSES.items():
        if username not in identities.OUT_OF_OFFICE_USERS:
            api.call(
                'PUT',
                '/users/' + actors[username]['id'] + '/status/custom',
                {
                    'emoji': emoji,
                    'text': text,
                    'duration': '',
                },
            )

    print('Populating the seeded conversation.', flush=True)
    # Tags avoid duplicate seed messages when bootstrap is rerun.
    seeded = {}
    for channel_id in channels.values():
        page = 0
        while True:
            posts = api.call('GET', f'/channels/{channel_id}/posts?per_page=200&page={page}')
            for post in posts['posts'].values():
                tag = post.get('props', {}).get('corporate_seed')
                if tag is not None:
                    seeded[tag] = post
            if len(posts['order']) < 200:
                break
            page += 1
    for index, message in enumerate(conversations.MESSAGES):
        tag = str(index)
        if tag not in seeded or seeded[tag]['message'] != message['message']:
            author = message['author']
            if tag in seeded and seeded[tag]['user_id'] != actors[author]['id']:
                raise RuntimeError(f'Unexpected author for seeded message {tag}')
            if author not in sessions:
                client = API()
                client.call(
                    'POST',
                    '/users/login',
                    {'login_id': author, 'password': staff_credentials[author]},
                )
                sessions[author] = client
            if tag in seeded:
                seeded[tag] = sessions[author].call(
                    'PUT', '/posts/' + seeded[tag]['id'] + '/patch', {'message': message['message']}
                )
            else:
                seeded[tag] = sessions[author].call(
                    'POST',
                    '/posts',
                    {
                        'channel_id': channels[message['channel']],
                        'message': message['message'],
                        'props': {'corporate_seed': tag},
                    },
                )
        if message['channel'] == workspace.SUPPORT_CHANNEL and message['author'] != '$bot':
            reply_tag = 'support-reply:' + tag
            reply_text = support_channel_reply(
                actors[message['author']], workspace.CORPORATE_EMAIL_DOMAIN
            )
            if reply_tag not in seeded:
                seeded[reply_tag] = sessions['$bot'].call(
                    'POST',
                    '/posts',
                    {
                        'channel_id': channels[message['channel']],
                        'root_id': seeded[tag]['id'],
                        'message': reply_text,
                        'props': {'corporate_seed': reply_tag},
                    },
                )
            elif seeded[reply_tag]['message'] != reply_text:
                if seeded[reply_tag]['user_id'] != bot['id']:
                    raise RuntimeError('Unexpected author for seeded support reply')
                seeded[reply_tag] = sessions['$bot'].call(
                    'PUT', '/posts/' + seeded[reply_tag]['id'] + '/patch', {'message': reply_text}
                )

    print('Preparing the archived 2FA handover.', flush=True)
    seed_mfa_archive(api, sessions['$bot'], team['id'], bot['id'])

    print('Preparing the link-preview project discussion.', flush=True)
    seed_archived_discussion(
        api, team['id'], actors, sessions, ssrf.CHANNEL, ssrf.MESSAGES, version=ssrf.SEED_VERSION
    )

    print('Preparing the identity migration discussion.', flush=True)
    seed_archived_discussion(
        api,
        team['id'],
        actors,
        sessions,
        authentik.CHANNEL,
        authentik.MESSAGES,
        version=authentik.SEED_VERSION,
    )

    print('Preparing workspace conversation history.', flush=True)
    seed_noise(api, team['id'], actors, sessions)

    print('Connecting website enquiries to the feedback channel.', flush=True)
    contact_id = channels[workspace.CONTACT_CHANNEL]
    hooks = api.call('GET', '/hooks/incoming?team_id=' + team['id'])
    hook = next((h for h in hooks if h['channel_id'] == contact_id), None)
    if not hook:
        hook = api.call(
            'POST',
            '/hooks/incoming',
            {'channel_id': contact_id, 'display_name': 'Website enquiries', 'channel_locked': True},
        )
    write_json(
        FRONTEND_RUNTIME,
        {
            'contact_webhook_url': api.base.removesuffix('/api/v4') + '/hooks/' + hook['id'],
        },
    )
    write_json(
        RUNTIME,
        {
            'mattermost_site_url': api.call('GET', '/config')['ServiceSettings']['SiteURL'],
            'bot_token': bot_token,
            'bot_id': bot['id'],
            'support_channel_id': channels[workspace.SUPPORT_CHANNEL],
        },
    )
    for actor, client in sessions.items():
        if actor != '$bot':
            client.call('POST', '/users/logout')
    print(
        f'Mattermost users, channels and messages ready ({time.monotonic() - started:.0f}s). Bootstrap complete.',
        flush=True,
    )
