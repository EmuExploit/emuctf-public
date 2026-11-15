#!/usr/bin/env python3
"""Write the bot's direct/group conversations to bot-conversations.html."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path


def export_conversations(api, bot_id):
    channels = api.call('GET', f'/users/{bot_id}/channels')
    conversations = []
    users = {}

    def user_details(user_id):
        if user_id not in users:
            user = api.call('GET', f'/users/{user_id}')
            users[user_id] = {
                key: user.get(key, '')
                for key in (
                    'id',
                    'username',
                    'nickname',
                    'first_name',
                    'last_name',
                    'email',
                    'position',
                    'roles',
                    'locale',
                    'auth_service',
                    'email_verified',
                    'is_bot',
                    'create_at',
                    'update_at',
                    'delete_at',
                    'last_picture_update',
                    'timezone',
                    'props',
                )
            }
        return users[user_id]

    for channel in sorted(channels, key=lambda item: (item['type'], item['id'])):
        if channel['type'] not in {'D', 'G'}:
            continue
        channel_id = channel['id']
        members = []
        page = 0
        while True:
            batch = api.call('GET', f'/channels/{channel_id}/members?per_page=200&page={page}')
            members.extend(user_details(member['user_id']) for member in batch)
            if len(batch) < 200:
                break
            page += 1

        posts = {}
        page = 0
        while True:
            batch = api.call('GET', f'/channels/{channel_id}/posts?per_page=200&page={page}')
            posts.update(batch['posts'])
            if len(batch['order']) < 200:
                break
            page += 1
        messages = []
        for post in sorted(posts.values(), key=lambda item: (item['create_at'], item['id'])):
            if post.get('user_id'):
                user_details(post['user_id'])
            messages.append(
                {
                    'id': post['id'],
                    'user_id': post.get('user_id', ''),
                    'create_at': post['create_at'],
                    'created_utc': datetime.fromtimestamp(
                        post['create_at'] / 1000, timezone.utc
                    ).isoformat(),
                    'edit_at': post.get('edit_at', 0),
                    'root_id': post.get('root_id', ''),
                    'type': post.get('type', ''),
                    'message': post['message'],
                    'file_ids': post.get('file_ids', []),
                }
            )
        conversations.append(
            {
                'channel_id': channel_id,
                'type': channel['type'],
                'name': channel.get('name', ''),
                'display_name': channel.get('display_name', ''),
                'participants': members,
                'messages': messages,
            }
        )
    return {
        'exported_utc': datetime.now(timezone.utc).isoformat(),
        'bot': user_details(bot_id),
        'users': users,
        'conversations': conversations,
    }


def timestamp(value):
    if not value:
        return 'Not set'
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()


def display_name(user):
    username = user.get('username') or user.get('id') or 'Unknown user'
    nickname = user.get('nickname')
    return f'{nickname} (@{username})' if nickname else f'@{username}'


def profile_html(user):
    fields = [
        ('Nickname', user.get('nickname')),
        ('Username', user.get('username')),
        ('Email', user.get('email')),
        ('First name', user.get('first_name')),
        ('Last name', user.get('last_name')),
        ('Position', user.get('position')),
        ('Roles', user.get('roles')),
        ('Email verified', 'Yes' if user.get('email_verified') else 'No'),
        ('Account type', 'Bot' if user.get('is_bot') else 'User'),
        ('Account status', 'Deactivated' if user.get('delete_at') else 'Active'),
        ('Sign-in service', user.get('auth_service') or 'Local'),
        ('Locale', user.get('locale')),
        ('Profile picture updated (UTC)', timestamp(user.get('last_picture_update'))),
        ('Account created (UTC)', timestamp(user.get('create_at'))),
        ('Profile updated (UTC)', timestamp(user.get('update_at'))),
        ('User ID', user.get('id')),
    ]
    for label, key in (('Timezone', 'timezone'), ('Custom profile properties', 'props')):
        value = user.get(key)
        if value:
            fields.append((label, json.dumps(value, ensure_ascii=False, sort_keys=True)))
    rows = ''.join(
        f'<dt>{escape(label)}</dt><dd>{escape(str(value or "Not set"))}</dd>'
        for label, value in fields
    )
    return (
        '<article class="profile"><h3>'
        + escape(display_name(user))
        + '</h3><dl>'
        + rows
        + '</dl></article>'
    )


def message_html(message, author, anchor, known_ids, bot_id):
    post_anchor = escape(f'{anchor}-post-{message["id"]}', quote=True)
    root_id = message.get('root_id', '')
    reply = ''
    if root_id:
        reply = '<span class="reply">Thread reply</span>'
        if root_id in known_ids:
            target = escape(f'{anchor}-post-{root_id}', quote=True)
            reply = f'<a class="reply" href="#{target}">↳ Reply to message</a>'
    style = 'message bot' if message['user_id'] == bot_id else 'message'
    edited = ' · edited' if message.get('edit_at') else ''
    identity = (
        'Nickname: '
        + (author.get('nickname') or 'Not set')
        + ' · Email: '
        + (author.get('email') or 'Not set')
        + ' · Position: '
        + (author.get('position') or 'Not set')
    )
    return (
        f'<article class="{style}" id="{post_anchor}"><header><strong>'
        + escape(display_name(author) if author else 'System')
        + '</strong><time>'
        + escape(message['created_utc'])
        + edited
        + '</time></header>'
        + '<p class="identity">'
        + escape(identity)
        + '</p>'
        + reply
        + '<div class="body">'
        + escape(message['message'])
        + '</div></article>'
    )


def render_html(data):
    bot_id = data['bot']['id']
    navigation, sections = [], []
    total = sum(len(c['messages']) for c in data['conversations'])
    for index, conversation in enumerate(data['conversations']):
        participants = conversation['participants']
        peers = [p for p in participants if p['id'] != bot_id]
        if conversation['type'] in {'D', 'G'}:
            title = ', '.join(display_name(p) for p in peers) or 'Self conversation'
        else:
            title = conversation['display_name'] or conversation['name']
        title = escape(title)
        anchor = f'conversation-{index}'
        count = len(conversation['messages'])
        navigation.append(f'<a href="#{anchor}">{title}<small>{count} messages</small></a>')
        # Include departed authors as well as current channel members.
        profiles = {p['id']: p for p in participants}
        profiles.update(
            {
                m['user_id']: data['users'][m['user_id']]
                for m in conversation['messages']
                if m['user_id']
            }
        )
        people = ''.join(profile_html(user) for user in profiles.values())
        known_ids = {m['id'] for m in conversation['messages']}
        messages = ''.join(
            message_html(m, data['users'].get(m['user_id'], {}), anchor, known_ids, bot_id)
            for m in conversation['messages']
        )
        sections.append(
            f'<section id="{anchor}"><h2>{title}</h2><p class="meta">'
            + escape(conversation['type'])
            + ' · '
            + str(count)
            + ' messages · channel '
            + escape(conversation['channel_id'])
            + '</p><div class="profiles">'
            + people
            + '</div>'
            + (messages or '<p>No messages.</p>')
            + '</section>'
        )
    return (
        """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>IT Support conversations</title><style>
:root{font-family:system-ui,sans-serif;color:#202938;background:#f4f6f9;line-height:1.5}
*{box-sizing:border-box}body{margin:0}a{color:#2458a5}a:focus-visible,summary:focus-visible{outline:3px solid #e99a20}
aside{position:fixed;inset:0 auto 0 0;width:280px;overflow:auto;padding:24px;background:#172338;color:#fff}
aside h1{font-size:20px;margin:0 0 8px}aside p{font-size:13px;color:#bdcbe0}
nav a{display:block;color:#fff;padding:12px 8px;border-top:1px solid #344257;text-decoration:none;overflow-wrap:anywhere}
nav a:hover{background:#293b55}nav small{display:block;color:#bdcbe0}
main{margin-left:280px;max-width:1250px;padding:32px 40px}section{scroll-margin-top:20px;margin-bottom:64px}
h2{overflow-wrap:anywhere;margin-bottom:4px}.meta,time{color:#637086;font-size:12px;overflow-wrap:anywhere}
.profiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px;margin:20px 0 28px}
.profile{background:#fff;border:1px solid #dce2eb;border-radius:8px;padding:16px;min-width:0}
.profile h3{margin:0 0 12px;font-size:16px;overflow-wrap:anywhere}
dl{margin:0;font-size:12px}dt{font-weight:600;color:#637086;margin-top:8px}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.identity{font-size:12px;color:#637086;margin:6px 0;overflow-wrap:anywhere}
.message{background:white;border:1px solid #dce2eb;border-left:4px solid #bcc9db;border-radius:8px;padding:16px 20px;margin:12px 0;scroll-margin-top:20px}
.message.bot{background:#edf4ff;border-left-color:#4380d5}.message:target{outline:3px solid #e99a20}
header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}header strong{overflow-wrap:anywhere}
.body{white-space:pre-wrap;overflow-wrap:anywhere;margin-top:8px}.reply{display:block;font-size:12px;margin-top:6px}
@media(max-width:760px){aside{position:static;width:auto;max-height:300px}main{margin:0;padding:20px}}
@media print{aside{display:none}main{margin:0;padding:0}.message{break-inside:avoid}}
</style></head><body><aside><h1>IT Support conversations</h1><p>"""
        + f'{len(data["conversations"])} conversations · {total} messages<br>'
        + 'Exported '
        + escape(data['exported_utc'])
        + '</p><nav>'
        + ''.join(navigation)
        + '</nav></aside><main><p class="meta">Profiles are current at export time; '
        + 'historical nickname, email and picture changes are not recorded in messages. All times are UTC.</p>'
        + (''.join(sections) or '<p>No conversations found.</p>')
        + '</main></body></html>\n'
    )


def compose_command():
    for command in (['docker', 'compose'], ['docker-compose']):
        try:
            result = subprocess.run(
                command + ['version', '--short'], capture_output=True, text=True
            )
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            if result.stdout.strip().lstrip('v').startswith('1.'):
                raise ValueError(
                    'Legacy Docker Compose v1 is unsupported; upgrade to modern Compose v2+.'
                )
            return command
    raise ValueError('Install Docker Compose: either docker compose or docker-compose is required.')


def main():
    if sys.argv[1:] == ['--inside']:
        from common.mattermost import API, runtime

        settings = runtime()
        sys.stdout.write(
            render_html(export_conversations(API(token=settings['bot_token']), settings['bot_id']))
        )
        return
    if len(sys.argv) != 1:
        raise ValueError('Usage: python3 botdump.py')
    command = compose_command()
    directory = Path(__file__).resolve().parent
    output = directory / 'bot-conversations.html'
    temporary = output.with_suffix('.html.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as target:
            subprocess.run(
                command + ['exec', '-T', 'bot', 'python', '-', '--inside'],
                cwd=directory,
                input=Path(__file__).read_bytes(),
                stdout=target,
                check=True,
            )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Saved {output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(f'Export failed: {error}', file=sys.stderr)
        sys.exit(1)
