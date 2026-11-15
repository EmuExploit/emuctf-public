"""Small Mattermost API client shared by setup and the bot."""

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import shared_config as config

API_URL = config.MATTERMOST_API_URL
RUNTIME = Path(config.MATTERMOST_RUNTIME_FILE)
FRONTEND_RUNTIME = Path(config.FRONTEND_RUNTIME_FILE)


class API:
    def __init__(self, base=API_URL, token='', timeout=15):
        self.base, self.token, self.timeout = base, token, timeout

    def call(self, method, path, data=None):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request(
            self.base + path,
            method=method,
            headers=headers,
            data=None if data is None else json.dumps(data).encode(),
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            self.token = response.headers.get('Token', self.token)
            body = response.read()
            return json.loads(body) if body else None

    def find(self, path):
        try:
            return self.call('GET', path)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise

    def set_profile_image(self, user_id, path):
        """Upload a bundled avatar using the authenticated organiser session."""
        boundary = uuid.uuid4().hex
        body = (
            (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
                'Content-Type: image/png\r\n\r\n'
            ).encode()
            + path.read_bytes()
            + f'\r\n--{boundary}--\r\n'.encode()
        )
        request = urllib.request.Request(
            self.base + '/users/' + user_id + '/image',
            data=body,
            headers={
                'Authorization': 'Bearer ' + self.token,
                'Content-Type': 'multipart/form-data; boundary=' + boundary,
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()

    def get_profile_image(self, user_id):
        request = urllib.request.Request(
            self.base + '/users/' + user_id + '/image',
            headers={'Authorization': 'Bearer ' + self.token},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read()

    def upload_file(self, channel_id, filename, content):
        """Attach a small bundled text document to a seeded staff post."""
        boundary = uuid.uuid4().hex
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="channel_id"\r\n\r\n'
                f'{channel_id}\r\n--{boundary}\r\n'
                f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
                'Content-Type: text/plain\r\n\r\n'
            ).encode()
            + content.encode()
            + f'\r\n--{boundary}--\r\n'.encode()
        )
        request = urllib.request.Request(
            self.base + '/files',
            data=body,
            headers={
                'Authorization': 'Bearer ' + self.token,
                'Content-Type': 'multipart/form-data; boundary=' + boundary,
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())['file_infos'][0]['id']


def runtime():
    return json.loads(RUNTIME.read_text())


def frontend_runtime():
    return json.loads(FRONTEND_RUNTIME.read_text())
