import json
from pathlib import Path

from bootstrap import config


def seed_profile_images(api, users):
    directory = Path(config.AVATAR_DIRECTORY)
    manifest_path = directory / 'manifest.json'
    if not manifest_path.exists():
        print('Avatar manifest is not available; keeping existing profile pictures.', flush=True)
        return
    manifest = json.loads(manifest_path.read_text())
    for user in users:
        avatar = manifest.get(user['username'])
        if avatar:
            api.set_profile_image(user['id'], directory / avatar['file'])
