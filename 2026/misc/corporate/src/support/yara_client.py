"""Send attachment bytes to the isolated scanner; never expose mailbox paths."""

import json
import socket
import struct

from support import config


def scan_files(files, folder):
    limits = dict(
        entries=config.YARA_ARCHIVE_MAX_ENTRIES,
        member_bytes=config.YARA_ARCHIVE_MAX_MEMBER_BYTES,
        expanded_bytes=config.YARA_ARCHIVE_MAX_EXPANDED_BYTES,
        depth=config.YARA_ARCHIVE_MAX_DEPTH,
        seconds=config.YARA_SUBMISSION_TIMEOUT_SECONDS,
        yara_seconds=config.YARA_TIMEOUT_SECONDS,
    )
    header = json.dumps(
        dict(
            limits=limits,
            rules_file=config.YARA_RULES_FILE,
            files=[
                dict(name=f['original_name'], size=f['size'], archive=f['archive']) for f in files
            ],
        )
    ).encode()
    try:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(config.YARA_SUBMISSION_TIMEOUT_SECONDS + 5)
            connection.connect(config.YARA_SCANNER_SOCKET)
            connection.sendall(struct.pack('!I', len(header)) + header)
            for item in files:
                with (folder / item['stored']).open('rb') as source:
                    while block := source.read(65536):
                        connection.sendall(block)
            connection.shutdown(socket.SHUT_WR)
            response = bytearray()
            while block := connection.recv(65536):
                response.extend(block)
                if len(response) > 256 * 1024:
                    raise ValueError('Scanner response too large')
        result = json.loads(response)
        if 'error' in result:
            raise ValueError(result['error'])
        if not isinstance(result['files'], list) or len(result['files']) != len(files):
            raise ValueError('Incomplete scanner response')
        for report in result['files']:
            if (
                not isinstance(report, dict)
                or type(report.get('matched')) is not bool
                or type(report.get('complete')) is not bool
                or not isinstance(report.get('members'), list)
                or not isinstance(report.get('issues'), list)
                or any(not isinstance(issue, str) for issue in report['issues'])
            ):
                raise ValueError('Invalid scanner report')
            identified = report.get('file_type')
            if (
                not isinstance(identified, dict)
                or 'error' not in identified
                or not isinstance(identified.get('description'), str)
                or len(identified['description']) > 1024
                or not isinstance(identified.get('mime'), str)
                or len(identified['mime']) > 256
                or (
                    identified.get('error') is not None and not isinstance(identified['error'], str)
                )
                or (report['complete'] and identified.get('error') is not None)
            ):
                raise ValueError('Invalid scanner identification')
            for member in report['members']:
                if (
                    not isinstance(member, dict)
                    or type(member.get('matched')) is not bool
                    or any(
                        not isinstance(member.get(key), str) for key in ('name', 'status', 'detail')
                    )
                ):
                    raise ValueError('Invalid scanner member')
            if (report['complete'] and (report['issues'] or not report['members'])) or report[
                'matched'
            ] != any(member['matched'] for member in report['members']):
                raise ValueError('Inconsistent scanner report')
        return result['files']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [
            dict(
                file_type=dict(description='Unavailable', mime='', error='Scanner unavailable'),
                matched=False,
                complete=False,
                members=[],
                issues=[f'Scanner unavailable or incomplete: {str(exc)[:300]}'],
            )
            for _ in files
        ]
