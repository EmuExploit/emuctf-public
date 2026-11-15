"""Networkless Unix-socket scanner. Archive paths are labels, never output paths."""

import json
import math
import os
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from scanner import config as settings

SOCKET, MAX_INPUT, MAX_REPLY, CEILINGS = (
    settings.SOCKET,
    settings.MAX_INPUT,
    settings.MAX_REPLY,
    settings.CEILINGS,
)


def exact(stream, size):
    data = bytearray()
    while len(data) < size:
        block = stream.read(min(size - len(data), 65536))
        if not block:
            raise ValueError('Incomplete scanner request')
        data.extend(block)
    return bytes(data)


def read_request(stream):
    size = struct.unpack('!I', exact(stream, 4))[0]
    if size > settings.MAX_HEADER:
        raise ValueError('Scanner header too large')
    header = json.loads(exact(stream, size))
    files = header['files']
    if not 0 <= len(files) <= settings.MAX_FILES:
        raise ValueError('Too many attachments')
    sizes = [f['size'] for f in files]
    if (
        any(type(n) is not int or not 0 <= n <= settings.MAX_FILE_BYTES for n in sizes)
        or sum(sizes) > MAX_INPUT
    ):
        raise ValueError('Scanner input too large')
    limits = {
        key: max(1, min(int(header['limits'][key]), ceiling)) for key, ceiling in CEILINGS.items()
    }
    rules_file = header.get('rules_file', 'index.yar')
    if (
        not isinstance(rules_file, str)
        or Path(rules_file).name != rules_file
        or rules_file in ('', '.', '..')
    ):
        raise ValueError('Invalid rules filename')
    return files, limits, [exact(stream, n) for n in sizes], rules_file


def identify_file(path, remaining):
    try:

        def run(*options):
            return (
                subprocess.run(
                    ['file', '--brief', *options, '--', str(path)],
                    capture_output=True,
                    timeout=min(3, remaining()),
                    check=True,
                )
                .stdout.decode('utf-8', 'replace')
                .strip()
            )

        return dict(description=run()[:1024], mime=run('--mime-type')[:256], error=None)
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return dict(
            description='Unavailable', mime='', error='file identification failed or timed out'
        )


def archive_kind(path):
    # Potential issue (F05): leading-magic detection skips prefixed/SFX or
    # embedded archives with nonarchive filenames. Accepted challenge policy;
    # a clean result does not guarantee that every embedded member was scanned.
    with open(path, 'rb') as source:
        magic = source.read(512)
    if magic.startswith(b'\x1f\x8b'):
        return 'gzip'
    # Include older tar variants whose headers lack the ustar signature.
    tar_header = False
    if len(magic) == 512:
        try:
            checksum = int(magic[148:156].strip(b'\x00 '), 8)
            tar_header = checksum == sum(magic[:148]) + 8 * 32 + sum(magic[156:])
        except ValueError:
            pass
    if (
        tar_header
        or magic.startswith(
            (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08', b'7z\xbc\xaf\x27\x1c', b'Rar!\x1a\x07')
        )
        or magic[257:262] == b'ustar'
    ):
        return 'archive'
    if magic.startswith((b'BZh', b'\xfd7zXZ\x00', b'\x28\xb5\x2f\xfd', b'MSCF')):
        return 'unsupported'
    return None


def scan(files, limits, blobs, rules_file='index.yar'):
    import libarchive

    deadline = time.monotonic() + limits['seconds']
    budget = dict(entries=0, expanded_bytes=0)
    reports = []

    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError('Submission scan time limit reached')
        return seconds

    with tempfile.TemporaryDirectory(prefix='yara-') as scratch:
        scratch = Path(scratch)
        sequence = 0

        def temporary():
            nonlocal sequence
            sequence += 1
            return scratch / str(sequence)

        def visit(path, label, depth, report, expected_archive=False):
            remaining()
            # Preserve upstream author attribution in match metadata (DRL 1.1).
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                result = subprocess.run(
                    [
                        'yara',
                        '-w',
                        '-m',
                        '-a',
                        str(max(1, math.ceil(min(remaining(), limits['yara_seconds'])))),
                        str(Path(settings.RULES_DIRECTORY) / rules_file),
                        str(path),
                    ],
                    stdout=output,
                    stderr=errors,
                    timeout=min(remaining(), limits['yara_seconds']),
                )
                output.seek(0)
                detail = output.read(4097).decode('utf-8', 'replace')
                errors.seek(0)
                error_detail = errors.read(1024).decode('utf-8', 'replace')
            matched = bool(detail.strip())
            record = dict(
                name=label[:1024],
                matched=matched,
                status='matched' if matched else 'clean',
                detail=(detail[:4096] + ('\n' + error_detail if error_detail else '')),
            )
            report['members'].append(record)
            if result.returncode or len(detail) > 4096:
                record['status'] = 'error' if result.returncode else 'matched (output truncated)'
                report['issues'].append(f'{label[:512]}: YARA error or truncated output')
            report['matched'] |= matched
            kind = archive_kind(path)
            if not kind:
                if expected_archive:
                    report['issues'].append(f'{label[:512]}: unsupported or unrecognised archive')
                return
            if kind == 'unsupported':
                report['issues'].append(f'{label[:512]}: unsupported archive format')
                return
            if depth >= limits['depth']:
                report['issues'].append(f'{label[:512]}: archive nesting limit reached')
                return
            # Gzip is decoded as one raw member; a tar stream inside is then
            # visited normally. No archive-provided pathname is used on disk.
            format_name = 'raw' if kind == 'gzip' else 'all'
            try:
                with libarchive.file_reader(str(path), format_name=format_name) as archive:
                    for entry in archive:
                        remaining()
                        budget['entries'] += 1
                        if budget['entries'] > limits['entries']:
                            raise ValueError('Archive entry limit reached')
                        member_label = f'{label[:512]} / {str(entry.pathname)[:512]}'
                        if entry.isdir:
                            continue
                        if not entry.isfile or entry.issym or entry.islnk:
                            report['issues'].append(
                                f'{member_label}: link or special entry skipped'
                            )
                            continue
                        if entry.size is not None and entry.size > limits['member_bytes']:
                            raise ValueError('Archive member exceeds file size limit')
                        member = temporary()
                        written = 0
                        try:
                            with member.open('wb') as target:
                                for block in entry.get_blocks():
                                    remaining()
                                    written += len(block)
                                    budget['expanded_bytes'] += len(block)
                                    if (
                                        written > limits['member_bytes']
                                        or budget['expanded_bytes'] > limits['expanded_bytes']
                                    ):
                                        raise ValueError('Archive expanded size limit reached')
                                    target.write(block)
                            visit(member, member_label, depth + 1, report)
                        finally:
                            member.unlink(missing_ok=True)
            except Exception as exc:
                report['issues'].append(
                    f'{label[:512]}: incomplete archive scan ({str(exc)[:300]})'
                )

        for info, blob in zip(files, blobs):
            report = dict(
                matched=False,
                members=[],
                issues=[],
                file_type=dict(
                    description='Unavailable', mime='', error='Identification unavailable'
                ),
            )
            reports.append(report)
            path = temporary()
            path.write_bytes(blob)
            try:
                report['file_type'] = identify_file(path, remaining)
                if report['file_type']['error']:
                    report['issues'].append(report['file_type']['error'])
                visit(path, str(info['name'])[:512], 0, report, bool(info.get('archive')))
            except Exception as exc:
                report['issues'].append(f'Scan incomplete: {str(exc)[:300]}')
            finally:
                path.unlink(missing_ok=True)
            report['complete'] = not report['issues']
    return dict(files=reports)


def serve():
    subprocess.run(
        ['yara', '-w', str(Path(settings.RULES_DIRECTORY) / 'index.yar'), '/dev/null'],
        check=True,
        timeout=10,
        stdout=subprocess.DEVNULL,
    )
    os.umask(0o077)
    print('Scanner listening on ' + SOCKET, flush=True)
    Path(SOCKET).unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(SOCKET)
        server.listen(8)
        while True:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(35)
                child = None
                try:
                    with connection.makefile('rb') as stream:
                        files, limits, blobs, rules_file = read_request(stream)
                    header = json.dumps(
                        dict(files=files, limits=limits, rules_file=rules_file)
                    ).encode()
                    packet = struct.pack('!I', len(header)) + header + b''.join(blobs)
                    # Kill the entire process group on timeout, including YARA.
                    with (
                        tempfile.TemporaryFile() as output,
                        tempfile.TemporaryDirectory(prefix='scan-job-') as jobdir,
                    ):
                        child = subprocess.Popen(
                            [sys.executable, '-B', '-m', 'scanner.worker', '--job'],
                            stdin=subprocess.PIPE,
                            stdout=output,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True,
                            env={**os.environ, 'TMPDIR': jobdir},
                        )
                        try:
                            child.communicate(packet, timeout=limits['seconds'] + 1)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait()
                            raise TimeoutError('Scanner timed out; manual review required')
                        output.seek(0)
                        reply = output.read(MAX_REPLY + 1)
                    if child.returncode or not reply or len(reply) > MAX_REPLY:
                        raise ValueError(
                            'Scanner failed or result limit reached; manual review required'
                        )
                    connection.sendall(reply)
                    print(
                        f'Scan completed: {len(files)} attachments, {sum(len(blob) for blob in blobs)} bytes',
                        flush=True,
                    )
                except Exception as exc:
                    print(f'Scan request failed: {exc}', flush=True)
                    try:
                        connection.sendall(json.dumps(dict(error=str(exc)[:500])).encode())
                    except OSError:
                        pass


if __name__ == '__main__':
    if '--job' in sys.argv:
        print(json.dumps(scan(*read_request(sys.stdin.buffer))))
    else:
        serve()
