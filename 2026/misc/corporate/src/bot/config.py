from shared_config import PLATFORM_ACCESS_KEY as PLATFORM_ACCESS_KEY

from bootstrap.fixtures.identities import ALTERNATIVE_CONTACTS
from bootstrap.fixtures.identities import OUT_OF_OFFICE_USERS as OUT_OF_OFFICE_USERS
from bootstrap.fixtures.identities import (
    PUBLIC_ALTERNATIVE_CONTACT_USERS as PUBLIC_ALTERNATIVE_CONTACT_USERS,
)
from bootstrap.fixtures.identities import USERS as USERS
from bootstrap.fixtures.mfa import SECRETS as MFA_SECRETS
from bootstrap.fixtures.workspace import CORPORATE_EMAIL_DOMAIN
from bootstrap.fixtures.workspace import GENERAL_CHANNEL as GENERAL_CHANNEL

RECOVERY_EMAIL_DOMAIN = CORPORATE_EMAIL_DOMAIN
RECOVERY_REQUEST_KEYWORDS = ('platform', 'key')
RECOVERY_RESTART_COMMAND = 'restart'
RECOVERY_DELAY_SECONDS = (2, 5)
RECOVERY_RANDOM_DELAY_CHANCE = 0.5
RECOVERY_REPLY_TIMEOUT_SECONDS = 60
RECOVERY_PAUSE_MESSAGES = ('1 sec', 'ummm, 1 sec', 'errr, let me check')

RECOVERY_IDENTITY_PROMPT = 'first, what identity system do we use for sign-in?'
RECOVERY_IDENTITY_KEYWORDS = ('authentik',)
RECOVERY_IDENTITY_REJECTED_KEYWORDS = ('okta', 'keycloak', 'entra', 'auth0', 'onelogin', 'adfs')
RECOVERY_IDENTITY_NEGATIONS = ('not', "isn't", 'is not')
RECOVERY_IDENTITY_CONTEXT_KEYWORDS = ('idp', 'identity provider')
RECOVERY_IDENTITY_ACKNOWLEDGEMENT = 'yep, Authentik. '

RECOVERY_BACKUP_PROMPT = 'whats your backup email?'
# These mappings also supply the seeded Mattermost clues; edit the fixture files.
RECOVERY_BACKUP_ANSWERS = ALTERNATIVE_CONTACTS

RECOVERY_AUTHENTICATOR_PROMPT = 'do you still have that old 2fa code? send me the six-digit code'
RECOVERY_TOTP_SECRETS = MFA_SECRETS
RECOVERY_TOTP_ALGORITHM = 'sha1'
RECOVERY_TOTP_DIGITS = 6
RECOVERY_TOTP_PERIOD_SECONDS = 30
RECOVERY_TOTP_DRIFT_STEPS = 1
RECOVERY_TOTP_MAX_ATTEMPTS = 2
RECOVERY_TOTP_RETRY_PROMPT = 'that code doesnt match. maybe wait 30 seconds for it to sync up, then send the new six-digit code'

RECOVERY_SSRF_PROMPT = 'oh also, has @panc4kes finished that latest link preview feature?'
# Exact answers after trimming outer whitespace, not substring matches.
RECOVERY_SSRF_ANSWERS = ('obviously',)
RECOVERY_SSRF_CASE_SENSITIVE = True

# Bound CPU work per player message before regex processing.
MAX_MESSAGE_CHARACTERS = 512

# One socket reader, with bounded and ordered work for each real player.
WORKERS = 4
MAX_ACTIVE_USERS = 512
MAX_QUEUED_MESSAGES_PER_USER = 4
SEEN_POSTS_PER_USER = 128
MESSAGE_BURST = 8
MESSAGE_REFILL_SECONDS = 1
API_TIMEOUT_SECONDS = 3
MAX_REPLY_CHARACTERS = 4000
DELIVERY_MAX_ATTEMPTS = 3
