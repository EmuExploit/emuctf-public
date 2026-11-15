from .identities import USERS
from .workspace import CONTACT_CHANNEL, GENERAL_CHANNEL, SUPPORT_CHANNEL

_STAFF = [user['username'] for user in USERS]

CHANNELS = [
    {'name': GENERAL_CHANNEL, 'display_name': 'General', 'type': 'O', 'members': _STAFF},
    {
        'name': SUPPORT_CHANNEL,
        'display_name': 'IT Support',
        'type': 'O',
        'header': 'For platform access, contact @it-support.',
        'members': [*_STAFF, '$bot'],
    },
    {
        'name': CONTACT_CHANNEL,
        'display_name': 'Feedback',
        'type': 'O',
        'purpose': 'Enquiries submitted through the company website.',
        'members': _STAFF,
    },
    {'name': 'flagsharing', 'display_name': 'Flagsharing', 'type': 'O', 'members': _STAFF},
    {'name': 'layoffs', 'display_name': 'Layoffs', 'type': 'O', 'members': _STAFF},
]

STAFF_CUSTOM_STATUSES = {
    'div': ('receipt', 'Preparing an invoice'),
    'bradan': ('file_folder', 'Looking for the downloads folder'),
    'panc4kes': ('pancakes', 'Reviewing what Claude wrote'),
    'hannnper': ('mahjong', 'East wind after 5'),
    'expr': ('coffee', 'Waiting for the build'),
    'teddy': ('hammer_and_wrench', 'Do not touch the redstone'),
}

MESSAGES = [
    {
        'channel': GENERAL_CHANNEL,
        'author': 'torry2',
        'message': 'we need to pick a flag for this challenge before in our next meeting.',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'teddy',
        'message': 'EMU{th1s_m33t1ng_c0uld_h4v3_b33n_4n_3m41l}',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'div',
        'message': 'too long. go with EMU{synergy} trust (ive sent invoice)',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'toasterpwn',
        'message': 'you cannot invoice us for suggesting one word',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'div',
        'message': 'strategic advisory services, cant keep giving for free',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'panc4kes',
        'message': 'EMU{p4nc4k3s_4r3_4_bu51n355_3xp3n53}',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'div',
        'message': 'ive reviewed all staff. results are in ~layoffs',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'torry2',
        'message': 'just do EMU{p3r_my_l4st_3m41l} its my challenge anyway',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'teddy',
        'message': 'approved pending approval from the flag approval committee',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'toasterpwn',
        'message': 'there is no flag approval committee',
    },
    {
        'channel': GENERAL_CHANNEL,
        'author': 'div',
        'message': 'there is now, very important for the ctf',
    },
    {
        'channel': SUPPORT_CHANNEL,
        'author': 'bradan',
        'message': 'trying to log in. is my username my name or my email? i tried "my name" and it says incorrect',
    },
    {
        'channel': SUPPORT_CHANNEL,
        'author': 'bradan',
        'message': 'downloaded the login instructions but where did the file go? do i need to download the downloads folder first?',
    },
    {
        'channel': SUPPORT_CHANNEL,
        'author': 'bradan',
        'message': 'when i type my password it turns into dots. am i meant to log in with the dots instead?',
    },
    {
        'channel': SUPPORT_CHANNEL,
        'author': 'bradan',
        'message': 'still cant log in. i put my email in both boxes so it definitely knows who i am. what else does it want?',
    },
    {
        'channel': SUPPORT_CHANNEL,
        'author': 'bradan',
        'message': 'closed the login tab by accident. is my account in the recycle bin now or do i have to make another one?',
    },
]
