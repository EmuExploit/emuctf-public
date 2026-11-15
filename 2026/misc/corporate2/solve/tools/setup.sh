#!/usr/bin/env bash
# Ubuntu 24.04 LTS / 26.04 LTS, x86-64. Run from your desktop user's sudo session.
set -euo pipefail
if [[ $EUID != 0 || -z ${SUDO_UID:-} || ${SUDO_UID:-0} == 0 ]]; then
    echo 'Run: sudo ./setup.sh "your-fixed-flag" (defaults to your ~/malware)' >&2
    exit 1
fi
if [[ $# != 1 && $# != 2 ]]; then
    echo 'Usage: sudo ./setup.sh "your-fixed-flag" OR sudo ./setup.sh "/absolute/storage/path" "your-fixed-flag"' >&2
    exit 1
fi
if [[ $# == 1 ]]; then
    operator_home=$(getent passwd "$SUDO_UID" | cut -d: -f6)
    set -- "$operator_home/malware" "$1"
fi
source /etc/os-release
if [[ $ID != ubuntu || ( $VERSION_ID != 24.04 && $VERSION_ID != 26.04 ) || $(uname -m) != x86_64 ]]; then
    echo 'Requires Ubuntu 24.04 or 26.04 LTS on Intel/AMD x86-64.' >&2
    exit 1
fi
if [[ $1 != /* || $1 == *','* || $1 == *$'\n'* ]]; then
    echo 'Storage path must be absolute, without commas or newlines. Spaces are supported.' >&2
    exit 1
fi
EMU_STORAGE=$1 EMU_FLAG=$2 python3 - <<'PY'
import json
import os
from pathlib import Path
config = Path('/etc/emu-lab.json')
wanted = dict(root=str(Path(os.environ['EMU_STORAGE']).resolve()), flag=os.environ['EMU_FLAG'])
if config.exists() and json.loads(config.read_text()) != wanted:
    raise SystemExit('/etc/emu-lab.json has different settings; refusing to alter the existing lab. See README.')
PY
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 qemu-system-x86 qemu-utils seabios iproute2 nftables \
    wireshark-common tshark xorriso virt-viewer util-linux procps coreutils acl kmod
if ! id emulab >/dev/null 2>&1; then
    useradd --system --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin emulab
fi
usermod -a -G kvm emulab
# Forwarding is needed for the routed namespace, and does not weaken its nft guards.
printf '%s\n' 'net.ipv4.ip_forward=1' > /etc/sysctl.d/90-emu-lab.conf
sysctl -p /etc/sysctl.d/90-emu-lab.conf
EMU_STORAGE=$1 EMU_FLAG=$2 python3 - <<'PY'
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid

required = ('python3', 'qemu-system-x86_64', 'qemu-img', 'ip', 'nft', 'dumpcap',
            'tshark', 'xorriso', 'setpriv', 'systemd-run', 'remote-viewer', 'tail', 'sysctl', 'setfacl')
for executable in required:
    path = shutil.which(executable)
    if not path:
        raise SystemExit(f'Missing installed executable: {executable}')
    print(f'{executable}: {path}', flush=True)
if not Path('/run/systemd/system').is_dir():
    raise SystemExit('systemd is not running as host init; a container is unsupported.')
if not Path('/dev/kvm').exists():
    raise SystemExit('/dev/kvm missing. Enable Intel VT-x or AMD-V in firmware and load the appropriate kvm module.')
if not Path('/dev/net/tun').is_char_device():
    module = subprocess.run(['modprobe', 'tun'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if module.returncode or not Path('/dev/net/tun').is_char_device():
        raise SystemExit('/dev/net/tun unavailable; cannot create the guest TAP interface. '
                         f'modprobe tun: {module.stderr.strip()}')
subprocess.run(['nft', 'list', 'tables'], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['remote-viewer', '--version'], check=True)
subprocess.run(['dumpcap', '--version'], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['tshark', '--version'], check=True, stdout=subprocess.DEVNULL)
# Verify emulab can open KVM and QEMU can create the supported SPICE Unix backend.
account = pwd.getpwnam('emulab')
# A real, isolated network smoke test. It never connects to a host uplink.
namespace = 'emu-smoke-' + uuid.uuid4().hex[:8]
def network_command(*args, **kwargs):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        raise SystemExit(f'Network smoke test failed: {" ".join(args)}\n{result.stderr.strip()}')
    return result.stdout

network_command('ip', 'netns', 'add', namespace)
try:
    prefix = ('ip', 'netns', 'exec', namespace)
    network_command(*prefix, 'ip', 'tuntap', 'add', 'tap0', 'mode', 'tap', 'user', str(account.pw_uid))
    network_command(*prefix, 'ip', 'addr', 'add', '10.77.0.1/24', 'dev', 'tap0')
    network_command(*prefix, 'ip', 'link', 'set', 'tap0', 'up')
    network_command(*prefix, 'ip', 'link', 'show', 'dev', 'tap0')
    network_command(*prefix, 'nft', '-f', '-', input='''
add table inet smoke
add set inet smoke denied { type ipv4_addr; flags interval; auto-merge; elements = { 10.0.0.0/8, 10.77.0.0/24 }; }
add chain inet smoke forward { type filter hook forward priority 0; policy drop; }
add rule inet smoke forward ip daddr @denied drop
''')
    with tempfile.TemporaryDirectory(prefix='emu-capture-smoke-', dir='/run') as directory:
        capture = Path(directory) / 'capture.pcap'
        with capture.open('xb', buffering=0) as output:
            os.fchmod(output.fileno(), 0o600)
            result = subprocess.run([*prefix, 'dumpcap', '-i', 'tap0', '-F', 'pcap',
                                     '-a', 'duration:1', '-w', '-'],
                                    stdout=output, stderr=subprocess.PIPE, text=True, timeout=10)
        if result.returncode or capture.stat().st_size < 24:
            raise SystemExit('Capture smoke test failed while writing through a preopened private file:\n'
                             + result.stderr.strip())
finally:
    already_failed = sys.exc_info()[0] is not None
    cleanup = subprocess.run(['ip', 'netns', 'delete', namespace], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cleanup.returncode:
        message = f'Network smoke-test cleanup failed for {namespace}: {cleanup.stderr.strip()}'
        if already_failed:
            print(message, file=sys.stderr)
        else:
            raise SystemExit(message)

with tempfile.TemporaryDirectory(prefix='emu-smoke-', dir='/run') as directory:
    os.chown(directory, account.pw_uid, account.pw_gid)
    base = Path(directory)
    log = base / 'qemu.log'
    with log.open('wb') as output:
        proc = subprocess.Popen(['setpriv', '--reuid', str(account.pw_uid),
                                 '--regid', str(account.pw_gid), '--init-groups',
                                 'qemu-system-x86_64', '-enable-kvm', '-machine', 'q35',
                                 '-cpu', 'host', '-m', '256', '-S', '-nodefaults', '-no-user-config',
                                 '-device', 'VGA', '-display', 'none',
                                 '-spice', f'unix=on,addr={base}/display.sock,disable-ticketing=on',
                                 '-qmp', f'unix:{base}/qmp.sock,server=on,wait=off'],
                                stdout=output, stderr=output)
        try:
            deadline = time.monotonic() + 15
            while not (base / 'qmp.sock').exists():
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise SystemExit('KVM/SPICE smoke test failed: ' + log.read_text() +
                                     '\nCheck journalctl -k for AppArmor denials. No protections were disabled.')
                time.sleep(.1)
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(5)
                sock.connect(str(base / 'qmp.sock'))
                stream = sock.makefile('rwb', buffering=0)
                json.loads(stream.readline())
                def command(name):
                    stream.write(json.dumps({'execute': name}).encode() + b'\n')
                    while True:
                        response = json.loads(stream.readline())
                        if 'error' in response:
                            raise SystemExit(f'QMP {name}: {response}')
                        if 'return' in response:
                            return response['return']
                command('qmp_capabilities')
                if not command('query-kvm').get('enabled'):
                    raise SystemExit('QEMU did not enable KVM.')
                if not command('query-spice').get('enabled') or not (base / 'display.sock').is_socket():
                    raise SystemExit('QEMU SPICE Unix backend did not start.')
                command('quit')
                stream.close()
            proc.wait(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

root = Path(os.environ['EMU_STORAGE']).resolve()
operator = pwd.getpwuid(int(os.environ['SUDO_UID']))
if root == Path('/') or root == Path(operator.pw_dir) or root in Path(operator.pw_dir).parents:
    raise SystemExit('Storage must be a dedicated subdirectory, such as ~/malware, not your home or an ancestor.')
if ',' in str(root):
    raise SystemExit('Resolved storage path contains a comma, which QEMU cannot accept here.')
flag = os.environ['EMU_FLAG']
if not flag or '\n' in flag or '\r' in flag:
    raise SystemExit('Use a nonempty single-line flag.')
config = Path('/etc/emu-lab.json')
wanted = dict(root=str(root), flag=flag)
if config.exists() and json.loads(config.read_text()) != wanted:
    raise SystemExit('/etc/emu-lab.json already has different settings. Refusing to change a lab silently. See README.')
root.mkdir(parents=True, exist_ok=True)
os.chown(root, operator.pw_uid, operator.pw_gid)
root.chmod(0o750)
# Allow only the VM account to traverse private home/storage ancestors, without
# granting directory listing or read access to other home files.
def probe_directory(path):
    # Some external test implementations inspect mode bits and ignore ACLs.
    # Actually entering the directory checks the kernel's effective permissions.
    return subprocess.run(['setpriv', '--reuid', str(account.pw_uid), '--regid', str(account.pw_gid),
                           '--init-groups', sys.executable, '-I', '-c',
                           'import os,sys; os.chdir(sys.argv[1])', str(path)],
                          cwd='/', text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

for parent in reversed((root, *root.parents)):
    if probe_directory(parent).returncode:
        subprocess.run(['setfacl', '-m', 'u:emulab:--x', str(parent)], check=True)
        result = probe_directory(parent)
        if result.returncode:
            permissions = subprocess.run(['getfacl', '-p', str(parent)], text=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            raise SystemExit(f'emulab cannot enter {parent} after ACL setup.\n'
                             f'Access probe: {result.stderr.strip()}\n{permissions.stdout}'
                             'Setup stopped before writing /etc/emu-lab.json. Existing VM disks are untouched.')
# Verify directory traversal as the actual VM account after applying the ACLs.
result = probe_directory(root)
if result.returncode:
    raise SystemExit(f'emulab cannot enter {root}: {result.stderr.strip()}\n'
                     'Setup stopped before writing /etc/emu-lab.json. Existing VM disks are untouched.')
for name in ('prepare', 'baseline', 'out', 'work'):
    path = root / name
    path.mkdir(exist_ok=True)
    os.chown(path, 0, account.pw_gid)
    path.chmod(0o700 if name == 'out' else 0o750)
if shutil.disk_usage(root).free < 8 * 1024**3:
    raise SystemExit('Storage has less than 8 GiB free. Allocate at least 120 GiB for real use.')
temp = config.with_suffix('.tmp')
temp.write_text(json.dumps(wanted, indent=2) + '\n')
temp.chmod(0o600)
os.replace(temp, config)
print('Setup passed: installed dependencies, namespace/TAP/nft/capture smoke test, unprivileged KVM and SPICE Unix backend.')
print('No TPM or UEFI variables are used. No Windows guest or GUI viewer session was tested.')
print(f'Storage: {root}. Next: follow README to prepare Windows and test isolation.')
PY
