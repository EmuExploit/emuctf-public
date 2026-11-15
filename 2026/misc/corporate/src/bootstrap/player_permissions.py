"""Keep ordinary workspace members limited to reading and sending messages."""

PLAYER_ROLE_PERMISSIONS = {
    'system_user': {
        'create_direct_channel',
        'join_public_teams',
        'list_public_teams',
        'view_members',
    },
    'team_user': {
        'view_team',
        'list_team_channels',
        'read_public_channel',
        'join_public_channels',
    },
    'channel_user': {'read_channel', 'read_channel_content', 'create_post'},
    # Channel/team admins still inherit the basic member role. Only system
    # admins may manage the workspace, including previously created channels.
    'team_admin': set(),
    'channel_admin': set(),
}


def restrict_player_permissions(api):
    """Apply the policy to built-in roles, covering existing and future users."""
    roles = api.call('GET', '/roles')
    required = {'system_user', 'team_user', 'channel_user'}
    if not required.issubset({role['name'] for role in roles}):
        raise RuntimeError('Mattermost default member roles are missing')
    for role in roles:
        allowed = PLAYER_ROLE_PERMISSIONS.get(role['name'])
        if allowed is None:
            continue
        permissions = [p for p in role['permissions'] if p in allowed]
        if permissions != role['permissions']:
            api.call(
                'PUT',
                '/roles/' + role['id'] + '/patch',
                {
                    'permissions': permissions,
                },
            )
