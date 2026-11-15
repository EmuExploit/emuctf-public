import re

from .members import ADVISOR, MEMBERS
from .workspace import CORPORATE_EMAIL_DOMAIN

ALTERNATIVE_CONTACTS = {
    'div': 'daniel.afterhours@protonmail.example',
    'toasterpwn': 'toast.archive17@outlook.example',
    'teddy': 'theodore.bear42@gmail.example',
    'torry2': 't0rry.backup@gmail.example',
    'msimonelli': 'marco.sparebox@protonmail.example',
    'anvbis': 'night.jackal@outlook.example',
    'bradan': 'brad.lostdownloads@hotmail.example',
    'expr': 'alex.expressions@protonmail.example',
    'ghostccamm': 'cam.afterdark@gmail.example',
    'h04x3d': 'harry.zero4@yahoo.example',
    'hannnper': 'hannah.weekends@outlook.example',
    'itsironiciinsist': 'ironic.delivery@gmail.example',
    'kabiracharya': 'kabir.personal@protonmail.example',
    'nullablevoidptr': 'null.pointer.home@outlook.example',
    'panc4kes': 'jack.sundaystack@gmail.example',
    'pew': 'pew.mailbox77@yahoo.example',
    'pl4nty': 'plant.watered@protonmail.example',
    'pwnpope': 'sunday.heap@gmail.example',
    'q3st1on': 'jester.offduty@outlook.example',
    'sealldev': 'seal.bythesea@gmail.example',
    'ssparrow': 'sparrow.roost@protonmail.example',
    'turbopenguin': 'penguin.fastmail@outlook.example',
}

OUT_OF_OFFICE_USERS = ['msimonelli', 'anvbis', 'kabiracharya', 'pwnpope', 'ssparrow']

PUBLIC_ALTERNATIVE_CONTACT_USERS = {
    'div',
    'teddy',
    'msimonelli',
    'bradan',
    'ghostccamm',
    'hannnper',
    'kabiracharya',
    'panc4kes',
    'pl4nty',
    'q3st1on',
    'ssparrow',
}


USERS = []
for _person in [ADVISOR, *MEMBERS]:
    _username = re.sub(r'[^a-z0-9._-]', '', _person['name'].split()[0].lower()).lstrip('._-')
    _position = _person['role']
    if _username in PUBLIC_ALTERNATIVE_CONTACT_USERS:
        _position += f' | Alternative contact: {ALTERNATIVE_CONTACTS[_username]}'
    USERS.append(
        {
            'username': _username,
            'email': f'{_username}@{CORPORATE_EMAIL_DOMAIN}',
            'nickname': _person['name'],
            'position': _position,
        }
    )
