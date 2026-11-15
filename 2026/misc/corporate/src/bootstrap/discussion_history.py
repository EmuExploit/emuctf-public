"""Seed project discussions using each speaker's own account."""

from bootstrap import config
from bootstrap.channel_history import finish_channel, prepare_channel
from bootstrap.fixtures import workspace
from common.mattermost import API


def seed_archived_discussion(api, team_id, actors, sessions, spec, messages, version='v1'):
    channel = prepare_channel(api, team_id, spec)
    path = '/channels/' + channel['id']
    # Keep the legacy namespace so channel renames never duplicate posts.
    namespace = workspace.CHANNEL_RENAMES.get(spec['name'], spec['name']) + ':'
    prefix = namespace + version + ':'
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
    try:
        for tag, post in existing.items():
            if tag.startswith(namespace) and not tag.startswith(prefix):
                api.call('DELETE', '/posts/' + post['id'])
        seeded = []
        for index, message in enumerate(messages):
            tag = f'{prefix}{index}'
            post = existing.get(tag)
            author = message['author']
            user_id = actors[author]['id']
            root_id = ''
            if message.get('reply') is not None:
                parent = seeded[message['reply']]
                root_id = parent.get('root_id') or parent['id']
            if post and post['user_id'] != user_id:
                raise RuntimeError(f'The {spec["name"]} discussion has an unexpected author')
            if not api.find(path + '/members/' + user_id):
                api.call('POST', path + '/members', {'user_id': user_id})
            if author not in sessions:
                credentials = next(user for user in config.USERS if user['username'] == author)
                sessions[author] = API()
                sessions[author].call(
                    'POST',
                    '/users/login',
                    {'login_id': author, 'password': credentials['password']},
                )
            # Mattermost does not support changing a post's thread. Recreate only
            # the explicitly moved clue reply, leaving all other history intact.
            if post and post.get('root_id', '') != root_id:
                api.call('DELETE', '/posts/' + post['id'])
                post = None
            if post:
                if post['message'] != message['message']:
                    post = sessions[author].call(
                        'PUT', '/posts/' + post['id'] + '/patch', {'message': message['message']}
                    )
            else:
                post = sessions[author].call(
                    'POST',
                    '/posts',
                    {
                        'channel_id': channel['id'],
                        'message': message['message'],
                        'root_id': root_id,
                        'props': {'corporate_seed': tag},
                    },
                )
            seeded.append(post)
    finally:
        channel = finish_channel(api, channel, spec.get('archived', True))
    return channel
