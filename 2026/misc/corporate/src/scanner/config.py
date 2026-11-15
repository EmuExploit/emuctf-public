from shared_config import MAX_FILE_BYTES, MAX_UPLOAD_BYTES

SOCKET = '/scanner-run/yara.sock'
RULES_DIRECTORY = '/rules'
MAX_INPUT = MAX_UPLOAD_BYTES
MAX_REPLY = 256 * 1024
MAX_HEADER = 8192
MAX_FILES = 5
# These ceilings apply even if a client requests larger budgets.
CEILINGS = dict(
    entries=500,
    member_bytes=MAX_FILE_BYTES,
    expanded_bytes=100 * 1024 * 1024,
    depth=5,
    seconds=30,
    yara_seconds=10,
)
