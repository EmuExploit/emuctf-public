"""Tee a child process to Docker stdout and a bounded, persistent log file."""

import logging
import os
import signal
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from shared_config import LOG_BACKUPS, LOG_MAX_BYTES

os.umask(0o077)
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger('service')
logger.setLevel(logging.INFO)
logger.addHandler(RotatingFileHandler(path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS))
child = subprocess.Popen(
    sys.argv[2:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True
)


def forward(signum, _frame):
    try:
        os.killpg(child.pid, signum)
    except ProcessLookupError:
        pass


for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, forward)
for line in iter(child.stdout.readline, b''):
    text = line.decode('utf-8', 'replace').rstrip('\n')
    logger.info(text)
    print(text, flush=True)
sys.exit(child.wait())
