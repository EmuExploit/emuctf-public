import re

EMAIL = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+", re.ASCII)


def support_channel_reply(user, email_domain):
    mention = '@' + user['username']
    email = user.get('email', '').strip().casefold()
    if not (EMAIL.fullmatch(email) and email.rsplit('@', 1)[1] == email_domain):
        return f'Hey {mention}, for external contractors please see ~flagsharing'
    return f'Hey {mention}, please DM me'
