import os
from pathlib import Path

from bootstrap.bootstrap import setup

os.umask(0o077)
Path('/tmp/corporate').mkdir(parents=True, exist_ok=True)
setup()
