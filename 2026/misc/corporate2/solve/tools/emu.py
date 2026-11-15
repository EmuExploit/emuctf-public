#!/usr/bin/env python3
"""Manual Windows malware lab. Configuration lives in /etc/emu-lab.json."""
import argparse
from collections import OrderedDict
import csv
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid

CONFIG = Path('/etc/emu-lab.json')
TOOLS = ('qemu-system-x86_64', 'qemu-img', 'ip', 'nft', 'dumpcap', 'tshark',
         'xorriso', 'setpriv', 'systemd-run', 'remote-viewer', 'tail', 'sysctl')
BLOCKED = ['0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8',
           '169.254.0.0/16', '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24',
           '192.168.0.0/16', '198.18.0.0/15', '198.51.100.0/24',
           '203.0.113.0/24', '224.0.0.0/4', '240.0.0.0/4']


def run(*args, **kw):
    timeout = kw.pop('timeout', 1800)
    input_data = kw.pop('input', None)
    if input_data is not None:
        kw['stdin'] = subprocess.PIPE
    with subprocess.Popen([str(a) for a in args], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw) as proc:
        started = time.monotonic()
        while True:
            try:
                stdout, stderr = proc.communicate(input=input_data, timeout=1)
                break
            except subprocess.TimeoutExpired:
                # communicate retains partially sent input internally. Supplying
                # it again on a retry would fail or duplicate the request.
                input_data = None
                notify()
                if os.environ.get('EMU_WORKER') == '1':
                    if process_identity(int(os.environ['EMU_PARENT'])) != os.environ['EMU_PARENT_START']:
                        proc.kill()
                        raise RuntimeError('Controller disappeared during ' + str(args[0]))
                if time.monotonic() - started > timeout:
                    proc.kill()
                    raise RuntimeError(str(args[0]) + ' timed out')
        result = subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
    if result.returncode:
        raise RuntimeError(f'{shlex.join(str(a) for a in args)} failed: {result.stderr.strip()}')
    return result.stdout


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


def configuration():
    if not CONFIG.exists():
        raise RuntimeError(f'Missing {CONFIG}: setup has not completed successfully. '
                           'If setup reported a permission/ACL error, resolve that first, then rerun '
                           "sudo ./setup.sh 'your-existing-fixed-flag'. Do not delete VM disks or reinstall Windows.")
    cfg = json.loads(CONFIG.read_text())
    cfg['root'] = Path(cfg['root'])
    return cfg


def preflight(cfg):
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo.')
    missing = [name for name in TOOLS if not shutil.which(name)]
    if missing:
        raise RuntimeError('Missing executable(s): ' + ', '.join(missing))
    if os.uname().machine != 'x86_64':
        raise RuntimeError('KVM host must be Intel/AMD x86-64.')
    if not os.access('/dev/kvm', os.R_OK | os.W_OK):
        raise RuntimeError('/dev/kvm is unavailable; enable hardware virtualization and load kvm_intel or kvm_amd.')
    if not Path('/dev/net/tun').is_char_device():
        raise RuntimeError('/dev/net/tun is unavailable; load the tun module with sudo modprobe tun. '
                           'The lab requires a native host with network namespace and TAP support.')
    if not Path('/run/systemd/system').exists():
        raise RuntimeError('A booted systemd host is required for fail-closed supervision.')
    if Path('/proc/sys/net/ipv4/ip_forward').read_text().strip() != '1':
        raise RuntimeError('IPv4 forwarding is off; see setup.sh and the README.')
    account = pwd.getpwnam('emulab')
    check_account_file(account, Path('/dev/kvm'), writable=True)
    if not sys.stdin.isatty():
        raise RuntimeError('An interactive terminal is required.')
    try:
        import curses
    except ImportError:
        raise RuntimeError('Python curses is unavailable; install Ubuntu python3 with its standard library.') from None
    if not os.environ.get('TERM') or os.environ['TERM'] == 'dumb':
        raise RuntimeError('The live terminal view requires TERM to name a capable terminal, such as xterm-256color.')
    try:
        curses.setupterm()
    except curses.error as exc:
        raise RuntimeError(f'Terminal initialization failed for TERM={os.environ["TERM"]}: {exc}') from None
    if not os.environ.get('SUDO_UID') or int(os.environ['SUDO_UID']) == 0:
        raise RuntimeError('Use sudo from your desktop user, so the viewer can open on that desktop.')
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise RuntimeError('No desktop display found; run sudo from a graphical desktop terminal.')
    if shutil.disk_usage(cfg['root']).free < 8 * 1024**3:
        raise RuntimeError(f'Less than 8 GiB free in {cfg["root"]}.')


def notify():
    address = os.environ.get('NOTIFY_SOCKET')
    if address:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect('\0' + address[1:] if address.startswith('@') else address)
            sock.sendall(b'WATCHDOG=1')


def check_account_file(account, path, writable=False):
    mode = 'os.O_RDWR' if writable else 'os.O_RDONLY'
    result = subprocess.run(['setpriv', '--reuid', str(account.pw_uid),
                             '--regid', str(account.pw_gid), '--init-groups',
                             sys.executable, '-I', '-c',
                             f'import os,sys; os.close(os.open(sys.argv[1], {mode}))', str(path)],
                            cwd='/', text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        access = 'read/write' if writable else 'read'
        raise RuntimeError(f'{account.pw_name} cannot {access} {path}: {result.stderr.strip()}')


def process_identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return None if fields[0] in ('Z', 'X') else fields[19]
    except (OSError, IndexError):
        return None


def qmp_connect(path):
    sock = socket.socket(socket.AF_UNIX)
    sock.settimeout(2)
    sock.connect(str(path))
    stream = sock.makefile('rwb', buffering=0)
    json.loads(stream.readline())
    stream.write(b'{"execute":"qmp_capabilities"}\n')
    while True:
        line = stream.readline()
        if not line:
            raise RuntimeError('QMP disconnected during capabilities handshake.')
        response = json.loads(line)
        if 'error' in response:
            raise RuntimeError('QMP capabilities failed: ' + str(response['error']))
        if 'return' in response:
            break
    return sock, stream


def qemu_args(disk, runtime):
    return ['qemu-system-x86_64', '-enable-kvm', '-machine', 'q35',
            '-cpu', 'host', '-smp', '4', '-m', '4096', '-nodefaults',
            '-no-user-config', '-no-reboot', '-boot', 'menu=on',
            '-drive', f'file={disk},if=none,id=os,format=qcow2',
            '-device', 'ide-hd,drive=os,bus=ide.0',
            '-device', 'VGA', '-device', 'qemu-xhci', '-device', 'usb-tablet',
            '-display', 'none', '-spice',
            f'unix=on,addr={runtime}/display.sock,disable-ticketing=on,disable-copy-paste=on,disable-agent-file-xfer=on',
            '-qmp', f'unix:{runtime}/qmp.sock,server=on,wait=off',
            '-monitor', 'none', '-serial', 'none', '-parallel', 'none',
            '-nic', 'tap,ifname=tap0,script=no,downscript=no,model=e1000']


def terminal_text(value):
    """Only printable ASCII reaches the terminal, including names from packets."""
    return str(value).encode('unicode_escape').decode('ascii')


def elapsed_text(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


def size_text(value):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if value < 1024 or unit == 'GiB':
            return f'{value:.1f}{unit}' if unit != 'B' else f'{int(value)}B'
        value /= 1024


class NetworkActivity:
    """Bounded display indexes. The existing log and pcap retain the full evidence."""
    FIELDS = ['frame.time_epoch', 'ip.src', 'ip.dst', 'ip.proto', 'tcp.srcport',
              'tcp.dstport', 'udp.srcport', 'udp.dstport', 'tcp.flags.syn',
              'tcp.flags.ack', 'dns.flags.response', 'dns.qry.name',
              'tls.handshake.extensions_server_name', 'frame.len', 'tcp.flags.reset',
              'tcp.flags.fin', 'dns.a']
    MAX_HOSTS = 8192
    MAX_FLOWS = 4096

    def __init__(self):
        self.started = time.monotonic()
        self.epoch = time.time()
        self.ips, self.domains, self.flows, self.ip_names = (OrderedDict() for _ in range(4))
        self.tx = self.rx = self.tx_bytes = self.rx_bytes = 0
        self.dns_queries = self.syns = self.evicted_flows = self.unparsed = 0
        self.latest = None

    def discover(self, collection, value, stamp, kind, address=''):
        value = value.strip().lower().rstrip('.')
        if not value or len(value) > 255:
            return False
        fresh = value not in collection
        if fresh:
            if len(collection) >= self.MAX_HOSTS:
                raise RuntimeError('Live host index reached 8192 entries; stopping. Full observations remain in connections.log and capture.pcap.')
            collection[value] = dict(value=value, first=stamp, last=stamp,
                                     kind=kind, address=address, tx=0, rx=0)
            self.latest = (stamp, kind, value)
        item = collection[value]
        item['last'] = stamp
        # A DNS answer must not overwrite a stronger, directly observed TLS name.
        if item['kind'] != 'TLS' or kind == 'TLS':
            item['kind'] = kind
            item['address'] = address or item['address']
        return fresh

    def ingest(self, line):
        try:
            parts = next(csv.reader([line], delimiter='|', quotechar='"'))
            if len(parts) != len(self.FIELDS):
                self.unparsed += 1
                return
            epoch, src, dst, proto, ts, td, us, ud, syn, ack, dns, query, sni, length, rst, fin, answers = parts
            epoch = float(epoch)
            length = max(0, int(length or 0))
            stamp = max(0, epoch - self.epoch)
            outgoing = src == '10.77.0.2'
            incoming = dst == '10.77.0.2'
            if not (outgoing or incoming):
                return
            remote = dst if outgoing else src
            ipaddress.IPv4Address(remote)
        except (ValueError, csv.Error, StopIteration):
            self.unparsed += 1
            return
        if outgoing:
            self.tx += 1
            self.tx_bytes += length
        else:
            self.rx += 1
            self.rx_bytes += length
        fresh = self.discover(self.ips, remote, stamp, 'IP')
        host = self.ips[remote]
        host['tx' if outgoing else 'rx'] += 1
        names = [name for name in query.split(',') if name]
        is_reply = '1' in dns.split(',')
        if names:
            if outgoing and not is_reply:
                self.dns_queries += 1
            for name in names:
                fresh |= self.discover(self.domains, name, stamp, 'DNS reply' if is_reply else 'DNS query')
            # These are observed DNS associations, not proof of a connection.
            if is_reply:
                for address in answers.split(','):
                    try:
                        ipaddress.IPv4Address(address)
                    except ValueError:
                        continue
                    self.ip_names[address] = names[0].lower().rstrip('.')
                    self.ip_names.move_to_end(address)
                    if len(self.ip_names) > self.MAX_HOSTS:
                        self.ip_names.popitem(last=False)
        tls_names = [name for name in sni.split(',') if name]
        for name in tls_names:
            fresh |= self.discover(self.domains, name, stamp, 'TLS', remote)
        protocol = {'6': 'TCP', '17': 'UDP', '1': 'ICMP'}.get(proto, proto)
        local_port = (ts or us) if outgoing else (td or ud)
        port = (td or ud) if outgoing else (ts or us)
        key = (protocol, remote, port, local_port, query.lower() if names else '')
        if key not in self.flows:
            if len(self.flows) >= self.MAX_FLOWS:
                self.flows.popitem(last=False)
                self.evicted_flows += 1
            self.flows[key] = dict(first=stamp, last=stamp, protocol=protocol, remote=remote,
                                   port=port, tx=0, rx=0, bytes=0, state='SENT' if outgoing else 'INBOUND',
                                   name='', name_kind='', new=fresh, new_at=stamp)
        flow = self.flows[key]
        flow['last'] = stamp
        flow['tx' if outgoing else 'rx'] += 1
        flow['bytes'] += length
        if names:
            flow.update(state='DNS REPLY' if is_reply else 'DNS QUERY', name=names[0], name_kind='DNS')
        elif '1' in rst.split(','):
            flow['state'] = 'RESET'
        elif '1' in fin.split(','):
            flow['state'] = 'CLOSING'
        elif '1' in syn.split(','):
            if '1' in ack.split(','):
                flow['state'] = 'CONNECTED'
            else:
                self.syns += 1
                if flow['state'] not in ('CONNECTED', 'TLS', 'REPLIED'):
                    flow['state'] = 'ATTEMPT'
        elif incoming and flow['state'] in ('SENT', 'ATTEMPT', 'INBOUND'):
            flow['state'] = 'REPLIED' if protocol != 'TCP' else 'INBOUND'
        if tls_names:
            flow.update(name=tls_names[0], name_kind='TLS')
            if flow['state'] not in ('RESET', 'CLOSING'):
                flow['state'] = 'TLS'
        elif not flow['name'] and remote in self.ip_names:
            flow.update(name=self.ip_names[remote], name_kind='DNS')
        # Ordinary background packets update counts in place. New discoveries
        # can promote a flow, but repeated ACKs cannot bury a new callback.
        if fresh:
            flow['new'] = True
            flow['new_at'] = stamp
            self.flows.move_to_end(key)


class TerminalUI:
    """Standard-library curses view; two controls, no extra services or files."""
    def __init__(self, attempt, activity):
        self.attempt, self.activity = attempt, activity
        self.screen = None
        self.colors = {}
        self.sampled = time.monotonic()
        self.sample_bytes = self.rate = 0
        self.drawn = 0

    def __enter__(self):
        import curses
        self.curses = curses
        try:
            self.screen = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.screen.nodelay(True)
            self.screen.keypad(True)
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            if curses.has_colors():
                curses.start_color()
                try:
                    curses.use_default_colors()
                    background = -1
                except curses.error:
                    background = curses.COLOR_BLACK
                for index, (name, color) in enumerate((('new', curses.COLOR_YELLOW),
                                                       ('good', curses.COLOR_GREEN),
                                                       ('bad', curses.COLOR_RED),
                                                       ('title', curses.COLOR_CYAN)), 1):
                    curses.init_pair(index, color, background)
                    self.colors[name] = curses.color_pair(index)
            self.attempt.ui = self
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        self.attempt.ui = None
        if self.screen is not None:
            for operation in (lambda: self.screen.keypad(False), self.curses.nocbreak,
                              self.curses.echo, self.curses.endwin):
                try:
                    operation()
                except self.curses.error:
                    pass

    def keys(self):
        # Bound input handling so a pasted wall of text cannot starve supervision.
        for _ in range(32):
            key = self.screen.getch()
            if key == -1:
                break
            if key in (ord('n'), ord('q')):
                yield chr(key)

    def frame(self, width, height, current=None):
        """Build printable cells separately from curses for deterministic checks."""
        current = time.monotonic() if current is None else current
        activity, attempt = self.activity, self.attempt
        elapsed = current - activity.started
        reference = attempt.args.reference if attempt.args.command == 'attempt' else 'PREPARE'
        loaded = str(attempt.args.zip) if attempt.args.command == 'attempt' else (
            str(attempt.args.install_iso) if attempt.args.install_iso else 'Installed Windows preparation disk')
        if attempt.args.command == 'attempt' or attempt.args.install_iso:
            loaded = f'{Path(loaded).name}  ({loaded})'
        total_bytes = activity.tx_bytes + activity.rx_bytes
        if current - self.sampled >= 1:
            self.rate = (total_bytes - self.sample_bytes) / (current - self.sampled)
            self.sampled, self.sample_bytes = current, total_bytes
        try:
            capture_size = (attempt.output / 'capture.pcap').stat().st_size
        except OSError:
            capture_size = 0
        cells = []
        def put(y, x, text, style='', limit=None):
            if 0 <= y < height and x < width:
                limit = max(0, min(width - x - 1, limit if limit is not None else width))
                text = terminal_text(text)
                if len(text) > limit and limit >= 3:
                    text = text[:limit - 3] + '...'
                cells.append((y, x, text[:limit], style))
        put(0, 0, f'EMU | INTERNET {"CUT" if attempt.cut else "ON"} | REFERENCE: {reference}',
            'bad' if attempt.cut else 'title')
        put(1, 0, '[n] Cut Internet   [q] Stop everything', 'title')
        put(2, 0, 'FILE: ' + loaded)
        put(3, 0, f'RUN {elapsed_text(elapsed)}  IPs {len(activity.ips)}  Domains {len(activity.domains)}'
            f'  Packets OUT/IN {activity.tx}/{activity.rx}  {size_text(self.rate)}/s'
            f'  PCAP {size_text(capture_size)}/1GiB')
        if activity.latest:
            stamp, kind, value = activity.latest
            age = elapsed_text(elapsed - stamp)
            put(4, 0, f'LATEST NEW {kind.upper()} +{elapsed_text(stamp)} ({age} ago)  {value}', 'new')
        else:
            put(4, 0, 'Waiting for Windows traffic. New IPs and domains will appear here.', 'new')
        if width < 80 or height < 16:
            put(6, 0, 'Enlarge terminal to at least 80 columns x 16 rows for both panes.')
            for row, flow in enumerate(reversed(activity.flows.values()), 8):
                if row >= height - 2:
                    break
                put(row, 0, f'{elapsed_text(flow["first"])} {flow["state"]:<10} {flow["protocol"]} '
                    f'{flow["remote"]}:{flow["port"]} {flow["name"]}')
            return cells
        left = min(44, max(27, width // 3))
        right_x, right_width = left + 3, width - left - 4
        put(5, 0, '-' * (width - 1))
        for row in range(6, height - 2):
            put(row, left + 1, '|')
        put(6, 0, f'CONTACTED IPs ({len(activity.ips)})', 'title', left)
        put(6, right_x, f'FLOW ({len(activity.flows)} tracked; repeated packets grouped)', 'title', right_width)
        put(7, 0, '  FIRST  IP ADDRESS       OUT/IN', '', left)
        roomy = right_width >= 70
        heading = f'{"FIRST":<6} {"EVENT":<10} {"NET":<4} {"REMOTE":<21} '
        if roomy:
            heading += f'{"OUT/IN":<10} '
        if right_width >= 90:
            heading += f'{"BYTES":<9} '
        put(7, right_x, heading + 'NAME / EVIDENCE', '', right_width)
        body_height = height - 10
        ip_rows = max(2, body_height // 2)
        for index, host in enumerate(reversed(activity.ips.values())):
            if index >= ip_rows:
                break
            recent = elapsed - host['first'] < 15
            text = f'{"*" if recent else " "} {elapsed_text(host["first"])} {host["value"]:<15} {host["tx"]}/{host["rx"]}'
            put(8 + index, 0, text, 'new' if recent else '', left)
        domain_top = 8 + ip_rows
        put(domain_top, 0, f'DOMAINS ({len(activity.domains)})', 'title', left)
        domain_slots = max(0, (height - 3 - domain_top) // 2)
        for index, host in enumerate(reversed(activity.domains.values())):
            if index >= domain_slots:
                break
            row = domain_top + 1 + index * 2
            recent = elapsed - host['first'] < 15
            put(row, 0, ('* ' if recent else '  ') + host['value'], 'new' if recent else '', left)
            put(row + 1, 0, f'  +{elapsed_text(host["first"])} {host["kind"]} {host["address"]}', '', left)
        for index, flow in enumerate(reversed(activity.flows.values())):
            if index >= body_height:
                break
            endpoint = flow['remote'] + (':' + flow['port'] if flow['port'] else '')
            text = f'{elapsed_text(flow["first"]):<6} {flow["state"]:<10} {flow["protocol"]:<4} {endpoint:<21} '
            if roomy:
                text += f'{str(flow["tx"]) + "/" + str(flow["rx"]):<10} '
            if right_width >= 90:
                text += f'{size_text(flow["bytes"]):<9} '
            text += (f'{flow["name"]} [{flow["name_kind"]}]' if flow['name'] else '')
            style = 'new' if flow['new'] and elapsed - flow['new_at'] < 15 else ''
            if flow['state'] == 'RESET':
                style = 'bad'
            put(8 + index, right_x, text, style, right_width)
        put(height - 2, 0, 'Newest discoveries first. DNS = lookup/answer; TLS = visible hostname. IP attempt != success.')
        put(height - 1, 0, f'All packets: capture.pcap + connections.log | DNS queries {activity.dns_queries}'
            f' | SYNs {activity.syns} | Older flow rows {activity.evicted_flows} | Unparsed rows {activity.unparsed}')
        return cells

    def draw(self, force=False):
        current = time.monotonic()
        if not force and current - self.drawn < .2:
            return
        self.drawn = current
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        for y, x, text, style in self.frame(width, height, current):
            try:
                self.screen.addstr(y, x, text, self.colors.get(style, 0) | (self.curses.A_BOLD if style else 0))
            except self.curses.error:
                pass  # Resizing can invalidate coordinates between frames.
        self.screen.refresh()


class Attempt:
    def __init__(self, cfg, args):
        self.cfg, self.args = cfg, args
        self.root = cfg['root']
        self.token = uuid.uuid4().hex[:8]
        self.ns = 'emu-' + self.token
        self.uplink = 'ev' + self.token
        self.table = 'emu_' + self.token
        self.runtime = Path('/run') / self.ns
        self.runtime.mkdir(mode=0o750)
        self.user = pwd.getpwnam('emulab')
        self.uid = int(os.environ['SUDO_UID'])
        self.gid = int(os.environ['SUDO_GID'])
        os.chown(self.runtime, self.user.pw_uid, self.gid)
        self.runtime.chmod(0o750)
        self.state = self.root / 'work' / self.token
        self.state.mkdir(mode=0o700)
        os.chown(self.state, self.user.pw_uid, self.user.pw_gid)
        self.children = []
        self.network_created = False
        self.uplink_created = False
        self.table_created = False
        self.cut = False
        self.qemu = None
        self.capture = None
        self.viewer = None
        self.meta = None
        self.output = None
        self.qmp = None
        self.stream = None
        self.clean_shutdown = False
        self.parent = int(os.environ['EMU_PARENT'])
        self.parent_start = os.environ['EMU_PARENT_START']

    def tick(self):
        notify()
        if process_identity(self.parent) != self.parent_start:
            raise RuntimeError('Controller disappeared; stopping the attempt.')

    def spawn(self, args, log, **kw):
        handle = open(log, 'ab', buffering=0)
        try:
            proc = subprocess.Popen([str(a) for a in args], stdout=kw.pop('stdout', handle), stderr=handle, **kw)
        finally:
            handle.close()
        self.children.append(proc)
        return proc

    def net(self, *args, **kw):
        return run('ip', 'netns', 'exec', self.ns, *args, **kw)

    def start_capture(self):
        # The controller owns the private output directory. Pass an already-open
        # file instead of asking a privilege-dropping dumpcap to traverse it.
        capture_path = self.output / 'capture.pcap'
        with capture_path.open('xb', buffering=0) as capture_file:
            os.fchmod(capture_file.fileno(), 0o600)
            self.capture = self.spawn(['ip', 'netns', 'exec', self.ns, 'dumpcap',
                                       '-i', 'tap0', '-F', 'pcap', '-s', '0', '-B', '64',
                                       '-a', 'filesize:1048576', '-a', 'duration:7200',
                                       '-w', '-'], self.output / 'capture.log', stdout=capture_file)
        deadline = time.monotonic() + 10
        while True:
            self.tick()
            if self.capture.poll() is not None or time.monotonic() > deadline:
                details = (self.output / 'capture.log').read_text(errors='replace')[-8192:]
                raise RuntimeError(f'dumpcap did not start. See {self.output / "capture.log"}\n{details}')
            # Existence alone is no longer readiness: we created the file above.
            # Require the complete classic-pcap global header before booting QEMU.
            with capture_path.open('rb') as handle:
                header = handle.read(24)
            if len(header) == 24 and header[:4] in (b'\xd4\xc3\xb2\xa1', b'\xa1\xb2\xc3\xd4',
                                                    b'\x4d\x3c\xb2\xa1', b'\xa1\xb2\x3c\x4d'):
                return
            time.sleep(.1)

    def network(self):
        # Block every host address and every explicit host route, including VPN routes.
        denied = set(BLOCKED)
        for interface in json.loads(run('ip', '-j', '-4', 'addr')):
            for addr in interface.get('addr_info', []):
                denied.add(addr['local'] + '/32')
        for route in json.loads(run('ip', '-j', '-4', 'route', 'show', 'table', 'all')):
            dst = route.get('dst', 'default')
            if dst != 'default':
                denied.add(str(ipaddress.ip_network(dst, strict=False)))
        blocked = ', '.join(sorted(denied))
        routes = json.loads(run('ip', '-j', '-4', 'route', 'get', '1.1.1.1'))
        egress = routes[0].get('dev', '')
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', egress) or egress == 'lo':
            raise RuntimeError('Cannot determine a safe IPv4 Internet egress interface.')
        # A dedicated /30 is checked for collision before use.
        lab_networks = [ipaddress.ip_network('192.0.2.0/30'), ipaddress.ip_network('10.77.0.0/24')]
        for route in json.loads(run('ip', '-j', '-4', 'route', 'show', 'table', 'all')):
            dst = route.get('dst', 'default')
            if dst != 'default' and any(cidr.overlaps(ipaddress.ip_network(dst, strict=False)) for cidr in lab_networks):
                raise RuntimeError(f'Lab subnet overlaps host route {dst}; use a host without that conflicting route.')
        run('ip', 'netns', 'add', self.ns)
        self.network_created = True
        run('ip', 'link', 'add', self.uplink, 'type', 'veth', 'peer', 'name', 'wan0', 'netns', self.ns)
        self.uplink_created = True
        # Install host guards before enabling either end of the uplink.
        run('nft', '-f', '-', input=f'''
add table inet {self.table}
add set inet {self.table} denied {{ type ipv4_addr; flags interval; auto-merge; elements = {{ {blocked} }}; }}
add chain inet {self.table} input {{ type filter hook input priority -200; policy accept; }}
add rule inet {self.table} input iifname "{self.uplink}" drop
add chain inet {self.table} forward {{ type filter hook forward priority -200; policy accept; }}
add rule inet {self.table} forward iifname "{self.uplink}" meta nfproto ipv6 drop
add rule inet {self.table} forward iifname "{self.uplink}" ip daddr @denied drop
add rule inet {self.table} forward iifname "{self.uplink}" oifname != "{egress}" drop
add rule inet {self.table} forward iifname "{self.uplink}" ip saddr != 10.77.0.2 drop
add rule inet {self.table} forward oifname "{self.uplink}" ct state {{ established, related }} accept
add rule inet {self.table} forward oifname "{self.uplink}" drop
add chain inet {self.table} post {{ type nat hook postrouting priority srcnat; policy accept; }}
add rule inet {self.table} post ip saddr 10.77.0.2 iifname "{self.uplink}" masquerade
''')
        self.table_created = True
        self.net('sysctl', '-qw', 'net.ipv6.conf.all.disable_ipv6=1', 'net.ipv6.conf.default.disable_ipv6=1', 'net.ipv4.ip_forward=1')
        self.net('ip', 'addr', 'add', '192.0.2.2/30', 'dev', 'wan0')
        self.net('ip', 'tuntap', 'add', 'tap0', 'mode', 'tap', 'user', str(self.user.pw_uid))
        self.net('ip', 'addr', 'add', '10.77.0.1/24', 'dev', 'tap0')
        self.net('nft', '-f', '-', input=f'''
add table inet guard
add set inet guard denied {{ type ipv4_addr; flags interval; auto-merge; elements = {{ {blocked} }}; }}
add chain inet guard input {{ type filter hook input priority 0; policy drop; }}
add chain inet guard output {{ type filter hook output priority 0; policy drop; }}
add chain inet guard forward {{ type filter hook forward priority 0; policy drop; }}
add rule inet guard forward iifname "tap0" oifname "wan0" ip saddr 10.77.0.2 ip daddr @denied drop
add rule inet guard forward iifname "tap0" oifname "wan0" ip saddr 10.77.0.2 accept
add rule inet guard forward iifname "wan0" oifname "tap0" ip daddr 10.77.0.2 ct state {{ established, related }} accept
''')
        run('ip', 'addr', 'add', '192.0.2.1/30', 'dev', self.uplink)
        run('ip', 'link', 'set', self.uplink, 'up')
        run('ip', 'route', 'add', '10.77.0.0/24', 'via', '192.0.2.2', 'dev', self.uplink)
        self.net('ip', 'link', 'set', 'wan0', 'up')
        self.net('ip', 'link', 'set', 'tap0', 'up')
        self.net('ip', 'link', 'set', 'lo', 'up')
        self.net('ip', 'route', 'add', 'default', 'via', '192.0.2.1')

    def cut_internet(self):
        if self.uplink_created and not self.cut:
            # Cut the namespace's host-side uplink. This also works when startup
            # failed before tap0 was created, or the tap has disappeared.
            run('ip', 'link', 'set', self.uplink, 'down')
            self.cut = True
            if getattr(self, 'ui', None) is None:
                print('Internet cut.', flush=True)

    def media(self):
        media_dir = self.state / 'media'
        media_dir.mkdir()
        digest = hashlib.sha256()
        copied = media_dir / 'submission.zip'
        with open(self.args.zip, 'rb') as source, open(copied, 'xb') as dest:
            while chunk := source.read(1024 * 1024):
                self.tick()
                digest.update(chunk)
                if dest.tell() + len(chunk) > 2 * 1024**3:
                    raise RuntimeError('Submission grew beyond the 2 GiB limit while copying.')
                if shutil.disk_usage(self.root).free < 4 * 1024**3:
                    raise RuntimeError('Less than 4 GiB free while copying submission.')
                dest.write(chunk)
        self.meta['zip_sha256'] = digest.hexdigest()
        write_json(self.output / 'attempt.json', self.meta)
        # xorriso sees only the fixed host-created filename, never ZIP entries.
        run('xorriso', '-as', 'mkisofs', '-quiet', '-J', '-V', 'SUBMISSION',
            '-o', self.state / 'submission.iso', media_dir)
        os.chown(self.state / 'submission.iso', self.user.pw_uid, self.gid)

    def start(self):
        baseline = self.root / 'baseline' / 'windows.qcow2'
        if self.args.command == 'attempt':
            if not baseline.is_file():
                raise RuntimeError('No baseline. Prepare Windows with prepare --save-baseline first.')
            self.output = self.root / 'out' / self.args.reference
            self.output.mkdir(mode=0o700)  # Atomic refusal of existing references.
            self.meta = dict(reference=self.args.reference, zip_sha256=None,
                             started=now(), ended=None, outcome='starting', internet_cut_at=None)
            write_json(self.output / 'attempt.json', self.meta)
            self.network()
            self.media()
            disk = self.state / 'windows.qcow2'
            run('qemu-img', 'create', '-f', 'qcow2', '-F', 'qcow2', '-b', baseline, disk)
        else:
            self.output = self.root / 'prepare' / ('session-' + self.token)
            self.output.mkdir(mode=0o700)
            disk = self.root / 'prepare' / 'windows.qcow2'
            self.network()
            if not disk.exists():
                run('qemu-img', 'create', '-f', 'qcow2', disk, '80G')
        os.chown(disk, self.user.pw_uid, self.user.pw_gid)
        disk.chmod(0o600)
        # One capture, no rotating files. Hitting the cap ends the entire attempt.
        self.start_capture()
        args = qemu_args(disk, self.runtime)
        if self.args.command == 'attempt':
            args += ['-drive', f'file={self.state}/submission.iso,media=cdrom,readonly=on,if=none,id=cd,format=raw',
                     '-device', 'ide-cd,drive=cd,bus=ide.1']
        else:
            prep_media = self.state / 'preparation'
            prep_media.mkdir()
            (prep_media / 'flag.txt').write_text(self.cfg['flag'] + '\n')
            run('xorriso', '-as', 'mkisofs', '-quiet', '-J', '-V', 'PREPARATION',
                '-o', self.state / 'preparation.iso', prep_media)
            os.chown(self.state / 'preparation.iso', self.user.pw_uid, self.gid)
            args += ['-drive', f'file={self.state}/preparation.iso,media=cdrom,readonly=on,if=none,id=prep,format=raw',
                     '-device', 'ide-cd,drive=prep,bus=ide.2']
        if self.args.command == 'prepare' and self.args.install_iso:
            args += ['-drive', f'file={self.args.install_iso},media=cdrom,readonly=on,if=none,id=cd,format=raw',
                     '-device', 'ide-cd,drive=cd,bus=ide.1', '-boot', 'once=d,menu=on']
        self.qemu = self.spawn(['ip', 'netns', 'exec', self.ns,
                                'setpriv', '--reuid', self.user.pw_uid,
                                '--regid', self.user.pw_gid, '--init-groups',
                                '--no-new-privs', *args], self.output / 'qemu.log')
        deadline = time.monotonic() + 30
        while not (self.runtime / 'display.sock').exists() or not (self.runtime / 'qmp.sock').exists():
            self.tick()
            if self.qemu.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f'QEMU/display startup failed. See {self.output / "qemu.log"}; check journalctl -k for AppArmor denials.')
            time.sleep(.1)
        self.qmp, self.stream = qmp_connect(self.runtime / 'qmp.sock')
        self.qmp.setblocking(False)
        os.chown(self.runtime / 'display.sock', self.user.pw_uid, self.gid)
        (self.runtime / 'display.sock').chmod(0o660)
        viewer_env = dict(os.environ)
        viewer_env['HOME'] = pwd.getpwuid(self.uid).pw_dir
        viewer_env['XDG_RUNTIME_DIR'] = f'/run/user/{self.uid}'
        viewer_env.pop('NOTIFY_SOCKET', None)
        self.viewer = self.spawn(['setpriv', '--reuid', self.uid, '--regid', self.gid,
                                  '--init-groups', 'remote-viewer',
                                  f'spice+unix://{self.runtime}/display.sock'], self.output / 'viewer.log', env=viewer_env)
        if self.meta:
            self.meta['outcome'] = 'running'
            write_json(self.output / 'attempt.json', self.meta)
        print('Windows: use 10.77.0.2/24, gateway 10.77.0.1, DNS 1.1.1.1.', flush=True)
        self.monitor()

    def monitor(self):
        selector = selectors.DefaultSelector()
        selector.register(self.qmp, selectors.EVENT_READ, 'qmp')
        activity = NetworkActivity()
        # One capture, decoded without root. The complete quoted field rows still
        # go to connections.log; grouping and viewport limits affect only the UI.
        tail = subprocess.Popen(['tail', '-c', '+1', '--follow=descriptor',
                                 str(self.output / 'capture.pcap')], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
        self.children.append(tail)
        cmd = ['ip', 'netns', 'exec', self.ns, 'setpriv', '--reuid', str(self.user.pw_uid),
               '--regid', str(self.user.pw_gid), '--clear-groups', '--no-new-privs',
               'tshark', '-n', '-l', '-r', '-', '-Y', 'ip', '-T', 'fields',
               '-E', 'separator=|', '-E', 'quote=d']
        for field in NetworkActivity.FIELDS:
            cmd += ['-e', field]
        error = open(self.output / 'monitor.log', 'ab', buffering=0)
        try:
            observer = subprocess.Popen(cmd, stdin=tail.stdout, stdout=subprocess.PIPE, stderr=error)
        finally:
            error.close()
            tail.stdout.close()
        self.children.append(observer)
        os.set_blocking(observer.stdout.fileno(), False)
        selector.register(observer.stdout, selectors.EVENT_READ, 'traffic')
        buffer, qmp_buffer = b'', b''
        start = time.monotonic()
        try:
            with TerminalUI(self, activity) as ui, open(self.output / 'connections.log', 'a', buffering=1) as log:
                log.write('epoch|source|destination|protocol|tcp_src|tcp_dst|udp_src|udp_dst|syn|ack|dns_response|dns_name|tls_sni|frame_bytes|rst|fin|dns_answers\n')
                ui.draw(force=True)
                while True:
                    self.tick()
                    if log.tell() > 256 * 1024**2:
                        raise RuntimeError('connections.log reached 256 MiB; stopping before evidence storage grows further.')
                    if self.capture.poll() is not None:
                        raise RuntimeError(f'Capture ended or hit its 1 GiB/2 hour limit; see {self.output / "capture.log"}')
                    if observer.poll() is not None:
                        raise RuntimeError(f'Network observer exited; see {self.output / "monitor.log"}')
                    if time.monotonic() - start > 7100:
                        raise RuntimeError('Attempt reached its time limit.')
                    if shutil.disk_usage(self.root).free < 2 * 1024**3:
                        raise RuntimeError('Less than 2 GiB free; stopping to preserve evidence.')
                    for action in ui.keys():
                        if action == 'n':
                            self.cut_internet()
                            if self.meta and not self.meta.get('internet_cut_at'):
                                self.meta['internet_cut_at'] = now()
                                write_json(self.output / 'attempt.json', self.meta)
                        elif action == 'q':
                            return
                    # Give shutdown events precedence over a viewer disconnect.
                    events = sorted(selector.select(.1), key=lambda item: item[0].data != 'qmp')
                    for key, _ in events:
                        if key.data == 'qmp':
                            data = self.qmp.recv(65536)
                            qmp_buffer += data
                            while b'\n' in qmp_buffer:
                                line, qmp_buffer = qmp_buffer.split(b'\n', 1)
                                event = json.loads(line)
                                if event.get('event') == 'SHUTDOWN':
                                    self.clean_shutdown = event.get('data', {}).get('guest', False) and event.get('data', {}).get('reason') == 'guest-shutdown'
                            if not data:
                                return
                        else:
                            data = os.read(observer.stdout.fileno(), 65536)
                            buffer += data
                            while b'\n' in buffer:
                                line, buffer = buffer.split(b'\n', 1)
                                text = line.decode(errors='replace')
                                log.write(text + '\n')
                                activity.ingest(text)
                            if len(buffer) > 1024**2:
                                raise RuntimeError('Network observer produced an oversized row; full packets remain in capture.pcap.')
                    ui.draw()
                    if self.viewer.poll() is not None:
                        if any(key.data == 'qmp' for key, _ in selector.select(0)):
                            continue
                        raise RuntimeError(f'Viewer closed or failed; see {self.output / "viewer.log"}')
        finally:
            selector.close()
            if self.clean_shutdown:
                print('Windows reported a full guest shutdown; waiting for QEMU exit.', flush=True)

    def cleanup(self):
        errors = []
        try:
            self.cut_internet()
        except Exception as exc:
            errors.append(str(exc))
        # Stop the guest before capture, preserving final traffic and capture statistics.
        for child in reversed(self.children):
            if child.poll() is None:
                child.send_signal(signal.SIGINT if child is self.capture else signal.SIGTERM)
                try:
                    child.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        if self.capture and self.output:
            statistics = (self.output / 'capture.log').read_text(errors='replace')[-8192:]
            print('Capture statistics (inspect any reported drops):\n' + statistics, flush=True)
            if self.meta:
                self.meta['capture_statistics'] = statistics
        if self.stream:
            self.stream.close()
        if self.qmp:
            self.qmp.close()
        if self.network_created:
            try:
                run('ip', 'netns', 'delete', self.ns)
                # Peer deletion removes the host veth once the namespace has no users.
            except Exception as exc:
                errors.append(str(exc))
        if self.table_created:
            try:
                run('nft', 'delete', 'table', 'inet', self.table)
            except Exception as exc:
                errors.append(str(exc))
        shutil.rmtree(self.runtime)
        shutil.rmtree(self.state)
        if errors:
            raise RuntimeError('Cleanup errors: ' + '; '.join(errors))

    def save_baseline(self):
        if not self.clean_shutdown:
            raise RuntimeError('Baseline NOT saved: no QMP-confirmed Windows shutdown. In Windows run shutdown /s /t 0, and keep this controller open.')
        source = self.root / 'prepare' / 'windows.qcow2'
        target = self.root / 'baseline' / 'windows.qcow2'
        if target.exists():
            raise RuntimeError('Baseline already exists; refusing replacement. Use a separate storage directory to build a new lab.')
        temp = target.with_suffix('.partial')
        print('Windows shutdown confirmed by QMP; saving baseline.', flush=True)
        run('qemu-img', 'convert', '-O', 'qcow2', source, temp)
        run('qemu-img', 'check', temp)
        os.chown(temp, 0, self.user.pw_gid)
        temp.chmod(0o440)
        os.replace(temp, target)
        print(f'Baseline saved: {target}', flush=True)


def recover(cfg):
    """A dead service may leave inert kernel objects; never delete an active service's state."""
    namespaces = json.loads(run('ip', '-j', 'netns', 'list'))
    for entry in namespaces:
        name = entry['name']
        if not re.fullmatch(r'emu-[0-9a-f]{8}', name):
            continue
        if run('ip', 'netns', 'pids', name).strip():
            raise RuntimeError(f'Stale namespace {name} still contains processes. Stop its emu service with systemctl before retrying.')
        run('ip', 'netns', 'delete', name)
    tables = json.loads(run('nft', '-j', 'list', 'tables'))
    for item in tables.get('nftables', []):
        table = item.get('table', {})
        if table.get('family') == 'inet' and re.fullmatch(r'emu_[0-9a-f]{8}', table.get('name', '')):
            run('nft', 'delete', 'table', 'inet', table['name'])
    for runtime in Path('/run').glob('emu-*'):
        if re.fullmatch(r'emu-[0-9a-f]{8}', runtime.name) and runtime.is_dir():
            shutil.rmtree(runtime)
    for state in (cfg['root'] / 'work').iterdir():
        if re.fullmatch(r'[0-9a-f]{8}', state.name) and state.is_dir():
            shutil.rmtree(state)
    for path in (cfg['root'] / 'out').glob('*/attempt.json'):
        meta = json.loads(path.read_text())
        if meta.get('outcome') in ('starting', 'running'):
            meta.update(outcome='aborted', ended=now(),
                        error='Supervisor ended without final metadata; inspect service journal and capture.log. End time is recovery time.')
            write_json(path, meta)


def worker(args, cfg):
    # The systemd watchdog kills the complete process group if this loop hangs.
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupted)
    with open(cfg['root'] / 'lab.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another lab operation is active.') from None
        recover(cfg)
        attempt = Attempt(cfg, args)
        outcome, problem = 'stopped', None
        try:
            attempt.start()
            if attempt.qemu and attempt.qemu.poll() not in (None, 0):
                raise RuntimeError(f'QEMU exited with status {attempt.qemu.returncode}; see {attempt.output / "qemu.log"}')
            if attempt.clean_shutdown:
                try:
                    exit_code = attempt.qemu.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    attempt.clean_shutdown = False
                    raise RuntimeError('Windows signalled shutdown but QEMU did not exit; baseline will not be saved.') from None
                if exit_code != 0:
                    attempt.clean_shutdown = False
                    raise RuntimeError(f'QEMU exited with status {exit_code}; baseline will not be saved.')
                outcome = 'guest-shutdown'
        except KeyboardInterrupt:
            outcome = 'interrupted'
        except Exception as exc:
            outcome, problem = 'error', exc
        finally:
            try:
                attempt.cleanup()
            except Exception as exc:
                outcome = 'error'
                problem = RuntimeError(f'{problem}\nAdditional cleanup failure: {exc}') if problem else exc
            if problem and attempt.output:
                (attempt.output / 'error.log').write_text(str(problem) + '\n')
            if attempt.meta:
                attempt.meta.update(ended=now(), outcome=outcome, error=str(problem) if problem else None)
                write_json(attempt.output / 'attempt.json', attempt.meta)
        if problem:
            raise problem
        if args.command == 'prepare' and args.save_baseline:
            attempt.save_baseline()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare', help='Boot the persistent Windows preparation disk')
    prep.add_argument('--install-iso', type=Path, help='Attach Windows 10 x64 ISO; omit after installation')
    prep.add_argument('--save-baseline', action='store_true', help='Save after a QMP-confirmed guest shutdown')
    attempt = sub.add_parser('attempt')
    attempt.add_argument('reference')
    attempt.add_argument('zip', type=Path)
    argv = sys.argv[1:]
    if argv and argv[0] not in ('prepare', 'attempt', '-h', '--help'):
        argv.insert(0, 'attempt')
    args = parser.parse_args(argv)
    cfg = configuration()
    preflight(cfg)
    if args.command == 'prepare' and args.save_baseline and (cfg['root'] / 'baseline' / 'windows.qcow2').exists():
        raise RuntimeError('Baseline already exists; refusing replacement before starting Windows.')
    if args.command == 'attempt':
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', args.reference):
            raise RuntimeError('Reference must be 1-80 ASCII letters, digits, dots, underscores or hyphens, starting with a letter or digit.')
        args.zip = args.zip.resolve(strict=True)
        if not args.zip.is_file():
            raise RuntimeError('Submission must be a regular file.')
        if args.zip.stat().st_size > 2 * 1024**3:
            raise RuntimeError('Submission exceeds the 2 GiB limit.')
        if (cfg['root'] / 'out' / args.reference).exists():
            raise RuntimeError(f'Reference {args.reference} already exists; choose a new reference.')
    elif args.install_iso:
        args.install_iso = args.install_iso.resolve(strict=True)
        # QEMU runs unprivileged. Copy once into the preparation directory if necessary.
        if ',' in str(args.install_iso):
            raise RuntimeError('ISO path cannot contain a comma (QEMU option delimiter). Spaces are supported.')
        account = pwd.getpwnam('emulab')
        check_account_file(account, args.install_iso)
    if os.environ.get('EMU_WORKER') == '1':
        worker(args, cfg)
        return
    env = dict(os.environ, EMU_WORKER='1', EMU_PARENT=str(os.getpid()),
               EMU_PARENT_START=process_identity(os.getpid()))
    # A private PTY permits immediate single-key controls. systemd owns every child.
    unit = 'emu-' + uuid.uuid4().hex[:8]
    cmd = ['systemd-run', '--quiet', '--wait', '--collect', '--pty', '--service-type=exec',
           '--unit=' + unit, '-p', 'WatchdogSec=30', '-p', 'NotifyAccess=main',
           '-p', 'WatchdogSignal=SIGKILL', '-p', 'KillMode=control-group',
           '-p', 'TimeoutStopSec=15', '-p', 'RuntimeMaxSec=3h',
           '-p', 'MemoryMax=7G', '-p', 'TasksMax=128', '-p', 'LimitFSIZE=100G']
    for key in ('EMU_WORKER', 'EMU_PARENT', 'EMU_PARENT_START', 'SUDO_UID', 'SUDO_GID',
                'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'TERM'):
        if key in env:
            cmd.append('--setenv=' + key + '=' + env[key])
    cmd += [sys.executable, str(Path(__file__).resolve()), args.command]
    if args.command == 'attempt':
        cmd += [args.reference, str(args.zip)]
    else:
        if args.install_iso:
            cmd += ['--install-iso', str(args.install_iso)]
        if args.save_baseline:
            cmd += ['--save-baseline']
    print(f'Controller PID: {os.getpid()}. Supervisor: {unit}.service. Emergency stop: sudo systemctl stop {unit}.service', flush=True)
    child = subprocess.Popen(cmd)
    try:
        code = child.wait()
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        subprocess.run(['systemctl', 'stop', unit + '.service'], check=False)
        code = child.wait()
    if code:
        raise RuntimeError(f'Attempt service failed ({code}). Inspect sudo journalctl -u {unit}.service and the attempt logs.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f'emu: {exc}', file=sys.stderr)
        sys.exit(1)
