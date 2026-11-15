"""Validate submissions and build their stored email/attachment evidence."""

import hashlib
import mimetypes
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import format_datetime, make_msgid, parseaddr

from werkzeug.utils import secure_filename

from support import config, screening
from support.mail_screening import add_signal, attachment_filename, screen_attachment_metadata
from support.yara_client import scan_files


class UploadTooLarge(ValueError):
    """Individual or combined attachment bytes exceed the admission policy."""


ARCHIVE_EXTENSIONS = {
    'zip',
    'rar',
    '7z',
    'gzip',
    'gz',
    'tar',
    'tgz',
    'bz2',
    'tbz',
    'tbz2',
    'xz',
    'txz',
    'zst',
    'lz',
    'lzma',
    'cab',
    'arj',
}


def is_archive(extension, data):
    # Identify common containers without unpacking or following any contents.
    return (
        extension in ARCHIVE_EXTENSIONS
        or data.startswith(
            (
                b'PK\x03\x04',
                b'PK\x05\x06',
                b'PK\x07\x08',
                b'Rar!\x1a\x07',
                b'7z\xbc\xaf\x27\x1c',
                b'\x1f\x8b',
                b'BZh',
                b'\xfd7zXZ\x00',
                b'\x28\xb5\x2f\xfd',
                b'MSCF',
            )
        )
        or data[257:262] == b'ustar'
    )


def validate_submission(values, attachments):
    if values['terms_agreed'] != 'yes':
        return 'Please agree to the submission terms before sending.'
    if any(not values[n] for n in ('sender', 'subject', 'body')):
        return 'Please complete all fields.'
    if any(
        len(values[n]) > limit for n, limit in [('sender', 254), ('subject', 200), ('body', 100000)]
    ):
        return 'One or more fields are too long.'
    if (
        any(c in values['sender'] + values['subject'] for c in '\r\n')
        or '@' not in parseaddr(values['sender'])[1]
    ):
        return 'Enter a valid From address and a single-line subject.'
    if len(attachments) > config.MAX_ATTACHMENTS:
        return f'Attach at most {config.MAX_ATTACHMENTS} files.'
    for upload in attachments:
        if len(upload.filename.encode('utf-8')) > config.SUPPORT_MAX_FILENAME_BYTES or any(
            ord(char) < 32 or ord(char) == 127 for char in upload.filename
        ):
            return 'Attachment filenames must be at most 255 UTF-8 bytes and contain no control characters.'
    return None


def build_message(values, created):
    msg = EmailMessage(policy=SMTP)
    msg['From'] = values['sender']
    msg['To'] = config.SUPPORT_RECIPIENT
    msg['Subject'] = values['subject']
    msg['Date'] = format_datetime(created)
    msg['Message-ID'] = make_msgid(domain='ctf.emu.team')
    msg.set_content('This message contains an HTML body. Open it in an HTML-capable mail client.')
    msg.add_alternative(values['body'], subtype='html')
    return msg


def store_attachments(attachments, folder, msg, signals, reasons):
    files = []
    uploaded_bytes = 0
    for index, upload in enumerate(attachments):
        name = secure_filename(upload.filename)[:180] or 'attachment'
        stored = f'{index:02d}-{name}'
        data = upload.read(config.SUPPORT_MAX_ATTACHMENT_BYTES + 1)
        uploaded_bytes += len(data)
        if (
            len(data) > config.SUPPORT_MAX_ATTACHMENT_BYTES
            or uploaded_bytes > config.SUPPORT_MAX_UPLOAD_BYTES
        ):
            raise UploadTooLarge
        digest = hashlib.sha256(data).hexdigest()
        original_name, _, extension = attachment_filename(upload.filename)
        if extension in screening.SUPPORT_BLOCKED_EXTENSIONS:
            reasons.append(f'{name}: blocked extension .{extension}')
        archive = is_archive(extension, data)
        path = folder / stored
        path.write_bytes(data)
        identified = dict(description='Unavailable', mime='', error='Identification unavailable')
        if archive:
            add_signal(signals, 'ARCHIVE', f'{name}: archive delivery')
        files.append(
            dict(
                name=name,
                original_name=original_name,
                declared_mime=upload.mimetype,
                stored=stored,
                size=len(data),
                sha256=digest,
                yara='disabled',
                file_type=identified,
                archive=archive,
                manual_review='',
            )
        )
        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        main, sub = mime.split('/', 1)
        msg.add_attachment(data, maintype=main, subtype=sub, filename=name)
    return files


def screen_attachments(app, files, folder, signals, reasons):
    if config.YARA_ENABLED and files:
        try:
            scans = scan_files(files, folder)
            if not isinstance(scans, list) or len(scans) != len(files):
                raise ValueError('Missing scanner results')
        except Exception:
            app.logger.exception('Attachment scanner failed')
            scans = [
                dict(matched=False, complete=False, members=[], issues=['Scanner failed'])
                for _ in files
            ]
        for item, scan in zip(files, scans):
            item['file_type'] = scan.get('file_type', item['file_type'])
            item['yara_scan'] = scan
            item['yara'] = (
                'matches found'
                if scan['matched']
                else ('no matches' if scan['complete'] else 'incomplete')
            )
            if scan['matched']:
                reasons.append(f'{item["name"]}: YARA match')
                evidence = '; '.join(
                    f'{m["name"]}: {m["detail"]}' for m in scan['members'] if m['matched']
                )
                add_signal(signals, 'YARA', evidence[:4096])
            if not scan['complete']:
                item['manual_review'] = '; '.join(scan['issues'])[:4096]
                reasons.append(f'{item["name"]}: incomplete YARA scan')
                add_signal(signals, 'SCAN_ERROR', item['manual_review'])
    elif files:
        for item in files:
            item['manual_review'] = 'YARA unavailable: scanning is disabled'
            add_signal(signals, 'SCAN_ERROR', item['manual_review'])
    for item in files:
        screen_attachment_metadata(
            signals, item['original_name'], item['size'], item['declared_mime'], item['file_type']
        )
