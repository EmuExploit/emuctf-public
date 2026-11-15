"""Channel migration helpers shared by the historical imports."""

from bootstrap.fixtures import workspace


def prepare_channel(api, team_id, spec):
    lookup = '/teams/' + team_id + '/channels/name/'
    channel = api.find(lookup + spec['name'] + '?include_deleted=true')
    legacy = workspace.CHANNEL_RENAMES.get(spec['name'])
    if not channel and legacy:
        channel = api.find(lookup + legacy + '?include_deleted=true')
    fields = {key: value for key, value in spec.items() if key not in ('archived', 'members')}
    if not channel:
        return api.call('POST', '/channels', {**fields, 'team_id': team_id})
    path = '/channels/' + channel['id']
    if channel.get('delete_at'):
        channel = api.call('POST', path + '/restore')
    if any(channel.get(key) != value for key, value in fields.items()):
        channel = api.call('PUT', path + '/patch', fields)
    return channel


def finish_channel(api, channel, archived):
    if archived:
        api.call('DELETE', '/channels/' + channel['id'])
    return api.call('GET', '/channels/' + channel['id'])
