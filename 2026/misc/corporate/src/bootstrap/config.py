from .fixtures import identities

ADMIN = {
    'username': 'admin',
    'email': 'admin@ctf.emu.team',
    'password': 'changeme',
}

STAFF_PASSWORDS = {
    'div': 'changeme',
    'toasterpwn': 'changeme',
    'teddy': 'changeme',
    'torry2': 'changeme',
    'msimonelli': 'changeme',
    'anvbis': 'changeme',
    'bradan': 'changeme',
    'expr': 'changeme',
    'ghostccamm': 'changeme',
    'h04x3d': 'changeme',
    'hannnper': 'changeme',
    'itsironiciinsist': 'changeme',
    'kabiracharya': 'changeme',
    'nullablevoidptr': 'changeme',
    'panc4kes': 'changeme',
    'pew': 'changeme',
    'pl4nty': 'changeme',
    'pwnpope': 'changeme',
    'q3st1on': 'changeme',
    'sealldev': 'changeme',
    'ssparrow': 'changeme',
    'turbopenguin': 'changeme',
}

USERS = [{**user, 'password': STAFF_PASSWORDS[user['username']]} for user in identities.USERS]
AVATAR_DIRECTORY = '/app/bootstrap/fixtures/avatars'
WAIT_ATTEMPTS = 120
WAIT_INTERVAL_SECONDS = 2
