"""Corporate operations dashboard, invoked by stack.sh monitor."""

import curses
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Fixture imports happen only for live probes; pure render helpers are testable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

SERVICES = (
    'caddy',
    'frontend',
    'support',
    'reviewer',
    'notifications',
    'bot',
    'bootstrap',
    'scanner',
    'mattermost',
    'database',
)
STORAGE = r"""
from pathlib import Path
import json, shutil, sqlite3
root = Path('/var/lib/corporate/submissions')
usage = shutil.disk_usage(root)
size = files = 0
for p in root.rglob('*'):
    try:
        if p.is_file():
            size += p.stat().st_size
            files += 1
    except FileNotFoundError:
        pass
result = dict(total=usage.total, free=usage.free, used=usage.used, files=files, bytes=size, states={})
db = root / 'mailbox.sqlite'
if db.exists():
    with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=3) as connection:
        result['states'] = dict(connection.execute('SELECT state, count(*) FROM submissions GROUP BY state'))
        result['latest'] = connection.execute('SELECT max(created) FROM submissions').fetchone()[0]
print(json.dumps(result))
"""
BOT_PROBE = r"""
import json
import urllib.request
from bot.health import read_status
from common.mattermost import API_URL
result = read_status()
try:
    with urllib.request.urlopen(API_URL + '/system/ping', timeout=3) as response:
        result['mattermost_ok'] = response.status == 200
except OSError:
    result['mattermost_ok'] = False
print(json.dumps(result))
"""
CHAT = r"""
SET statement_timeout = '3s';
BEGIN READ ONLY;
WITH cutoff AS (SELECT (extract(epoch FROM now()) * 1000)::bigint AS ms),
bot_channels AS (
    SELECT DISTINCT cm.channelid FROM channelmembers cm JOIN bots b ON b.userid = cm.userid
), events AS (
    SELECT p.createat, p.userid, u.username, (b.userid IS NOT NULL) AS isbot, c.type,
           p.channelid IN (SELECT channelid FROM bot_channels) AS bot_channel
    FROM posts p JOIN users u ON u.id = p.userid LEFT JOIN bots b ON b.userid = u.id
    JOIN channels c ON c.id = p.channelid CROSS JOIN cutoff t
    WHERE p.deleteat = 0 AND p.type = '' AND p.createat >= t.ms - 3600000
      AND NOT (p.props::jsonb ? 'corporate_seed')
), recent AS (SELECT e.* FROM events e, cutoff t WHERE e.createat >= t.ms - 300000),
talkers AS (
    SELECT username, count(*) AS messages FROM recent WHERE NOT isbot
    GROUP BY username ORDER BY messages DESC, username LIMIT 8
)
SELECT json_build_object(
    'staff_count', (SELECT count(*) FROM users WHERE deleteat = 0 AND username IN (SELECT json_array_elements_text(:'staff_names'::json))),
    'accounts', (SELECT count(*) FROM users u WHERE u.deleteat = 0 AND NOT EXISTS (SELECT 1 FROM bots b WHERE b.userid = u.id)),
    'online', (SELECT count(*) FROM status s JOIN users u ON u.id = s.userid
               WHERE s.status = 'online' AND u.deleteat = 0 AND NOT EXISTS (SELECT 1 FROM bots b WHERE b.userid = u.id)),
    'authors', (SELECT count(DISTINCT userid) FROM recent WHERE NOT isbot),
    'messages_1m', (SELECT count(*) FROM recent e, cutoff t WHERE NOT e.isbot AND e.createat >= t.ms - 60000),
    'messages_5m', (SELECT count(*) FROM recent WHERE NOT isbot),
    'bot_inbound', (SELECT count(*) FROM recent WHERE NOT isbot AND bot_channel AND type IN ('D','G')),
    'bot_replies', (SELECT count(*) FROM recent WHERE isbot),
    'last_message', (SELECT max(createat) FROM events WHERE NOT isbot),
    'last_bot_message', (SELECT max(p.createat) FROM posts p JOIN users u ON u.id = p.userid
        WHERE u.username = :'bot_username' AND p.deleteat = 0 AND p.type = ''
          AND NOT (p.props::jsonb ? 'corporate_seed')),
    'talkers', (SELECT coalesce(json_agg(talkers), '[]'::json) FROM talkers)
);
ROLLBACK;
"""


def run(command, source=None):
    result = subprocess.run(command, input=source, capture_output=True, text=True, timeout=12)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[-180:] or 'Command failed')
    return result.stdout


def size_bytes(value):
    match = re.fullmatch(r'\s*([\d.]+)\s*([A-Za-z]*)\s*', value)
    if not match:
        raise ValueError('Unrecognised Docker memory value')
    number, unit = match.groups()
    units = {
        'B': 1,
        'kB': 1000,
        'KB': 1000,
        'MB': 1000**2,
        'GB': 1000**3,
        'TB': 1000**4,
        'KiB': 1024,
        'MiB': 1024**2,
        'GiB': 1024**3,
        'TiB': 1024**4,
        '': 1,
    }
    return float(number) * units[unit]


def human(value):
    if value is None:
        return '--'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(value) < 1024 or unit == 'TiB':
            return f'{value:.1f} {unit}'
        value /= 1024


def clean(value):
    return ''.join(c if c.isprintable() else ' ' for c in str(value))


def snapshot():
    from bootstrap.fixtures.identities import USERS
    from bootstrap.fixtures.workspace import BOT

    report = {'time': time.time(), 'warnings': [], 'services': [], 'stats': {}}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {
            'ids': pool.submit(run, COMPOSE + ['ps', '-a', '-q']),
            'stats': pool.submit(run, ['docker', 'stats', '--no-stream', '--format', '{{json .}}']),
            'engine': pool.submit(run, ['docker', 'info', '--format', '{{json .}}']),
        }
        for key, job in jobs.items():
            try:
                raw = job.result()
                if key == 'ids':
                    report['ids'] = raw.split()
                elif key == 'stats':
                    for line in raw.splitlines():
                        item = json.loads(line)
                        item['bytes'] = size_bytes(item['MemUsage'].split('/')[0])
                        report['stats'][item['Name']] = item
                else:
                    engine = json.loads(raw)
                    report['capacity'] = engine['MemTotal']
                    report['cpus'] = engine['NCPU']
            except Exception as error:
                report['warnings'].append(f'{key}: {error}')
    if report.get('ids'):
        try:
            report['services'] = json.loads(run(['docker', 'inspect', *report['ids']]))
        except Exception as error:
            report['warnings'].append(f'Container inspection: {error}')
    running = set()
    present = set()
    for container in report['services']:
        service = container['Config']['Labels']['com.docker.compose.service']
        present.add(service)
        state = container['State']
        if state['Running']:
            running.add(service)
        if state.get('OOMKilled'):
            report['warnings'].append(f'{service}: killed for exceeding memory limit')
        if state.get('Health', {}).get('Status') == 'unhealthy':
            report['warnings'].append(f'{service}: unhealthy')
        if not state['Running'] and not (service == 'bootstrap' and state['ExitCode'] == 0):
            report['warnings'].append(f'{service}: {state["Status"]}, exit {state["ExitCode"]}')
    missing = set(SERVICES) - present
    if missing:
        report['warnings'].append('Not created: ' + ', '.join(sorted(missing)))
    queries = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        if 'support' in running:
            queries['storage'] = pool.submit(
                run, COMPOSE + ['exec', '-T', 'support', 'python', '-'], STORAGE
            )
        if 'bot' in running:
            queries['bot'] = pool.submit(
                run, COMPOSE + ['exec', '-T', 'bot', 'python', '-'], BOT_PROBE
            )
        if 'database' in running:
            queries['chat'] = pool.submit(
                run,
                COMPOSE
                + [
                    'exec',
                    '-T',
                    'database',
                    'sh',
                    '-c',
                    'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"',
                    'monitor',
                    '-v',
                    'staff_names=' + json.dumps([user['username'] for user in USERS]),
                    '-v',
                    'bot_username=' + BOT['username'],
                ],
                CHAT,
            )
        for key, job in queries.items():
            try:
                report[key] = json.loads(job.result())
            except Exception as error:
                report['warnings'].append(f'{key}: {error}')
    storage = report.get('storage')
    if storage and storage['used'] / storage['total'] >= 0.85:
        report['warnings'].append('Malware storage filesystem is at least 85% full')
    return report


def gauge(used, total, width=22):
    if not total:
        return '[unavailable]'
    percent = used / total
    filled = min(width, max(0, round(percent * width)))
    return '[' + '#' * filled + '-' * (width - filled) + f'] {100 * percent:5.1f}%'


def service_health(container, report):
    service = container['Config']['Labels']['com.docker.compose.service']
    state = container['State']
    if service == 'bootstrap' and state['Status'] == 'exited' and state['ExitCode'] == 0:
        return 'complete'
    if not state['Running']:
        return '--'
    if service == 'mattermost':
        probe = report.get('bot', {}).get('mattermost_ok')
        return 'HTTP OK' if probe is True else 'HTTP FAIL' if probe is False else 'no probe'
    return state.get('Health', {}).get('Status', 'not set')


def message_time(stamp):
    if not stamp:
        return 'none'
    age = max(0, int(time.time() - stamp / 1000))
    elapsed = (
        f'{age}s ago' if age < 60 else f'{age // 60}m ago' if age < 3600 else f'{age // 3600}h ago'
    )
    return (
        datetime.fromtimestamp(stamp / 1000).astimezone().strftime('%H:%M:%S %Z') + f' ({elapsed})'
    )


def lines(report, view):
    output = []

    def add(text='', style=0):
        output.append((clean(text), style))

    stats = report['stats']
    all_ram = sum(item['bytes'] for item in stats.values())
    stack_stats = [
        stats[c['Name'].lstrip('/')] for c in report['services'] if c['Name'].lstrip('/') in stats
    ]
    stack_ram = sum(item['bytes'] for item in stack_stats)
    stack_cpu = sum(float(item['CPUPerc'].rstrip('%')) for item in stack_stats)
    capacity = report.get('capacity')
    add(f'DOCKER RAM  {human(all_ram):>11} / {human(capacity):<11} {gauge(all_ram, capacity)}', 1)
    add(
        f'THIS STACK  {human(stack_ram):>11} RAM    {stack_cpu:6.1f}% CPU    Docker CPUs: {report.get("cpus", "--")}'
    )
    add(
        'RAM = docker stats working usage; Docker total includes other stacks. CPU: 100% = one core.',
        3,
    )
    add()
    if view == 0:
        add(
            f'{"SERVICE":<12} {"STATE":<10} {"HEALTH":<10} {"CPU":>6} {"RAM / LIMIT":>23} {"RST":>3} {"PID":>4}',
            1,
        )
        by_service = {
            c['Config']['Labels']['com.docker.compose.service']: c for c in report['services']
        }
        for name in SERVICES:
            container = by_service.get(name)
            if not container:
                add(f'{name:<12} missing', 2)
                continue
            state = container['State']
            health = service_health(container, report)
            item = stats.get(container['Name'].lstrip('/'), {})
            label = 'OOM KILLED' if state.get('OOMKilled') else state['Status']
            color = (
                2
                if health in ('unhealthy', 'HTTP FAIL')
                or state.get('OOMKilled')
                or (not state['Running'] and health != 'complete')
                else 0
            )
            add(
                f'{name:<12} {label:<10} {health:<10} {item.get("CPUPerc", "--"):>6} {item.get("MemUsage", "--"):>23} {container["RestartCount"]:>3} {item.get("PIDs", "--"):>4}',
                color,
            )
        add()
    if view == 3:
        add('HEALTHCHECKS', 1)
        descriptions = {
            'caddy': 'Caddy local configuration API',
            'frontend': 'Frontend /healthz including Mattermost ping',
            'support': 'Support /healthz',
            'reviewer': 'Reviewer /healthz',
            'notifications': 'Notification relay /healthz',
            'bot': 'Authenticated WebSocket, fresh loop heartbeat and ping/pong',
            'bootstrap': 'One-shot setup: exit 0 means complete',
            'scanner': 'Scanner Unix socket exists',
            'mattermost': 'Live /system/ping from bot container (monitor probe)',
            'database': 'PostgreSQL pg_isready',
        }
        by_service = {
            c['Config']['Labels']['com.docker.compose.service']: c for c in report['services']
        }
        for service in SERVICES:
            container = by_service.get(service)
            health = service_health(container, report) if container else 'missing'
            add(
                f'{service.upper():<12} {health}',
                2 if health in ('unhealthy', 'HTTP FAIL', 'missing') else 1,
            )
            add('  ' + descriptions[service])
            if container:
                checks = container['State'].get('Health', {})
                logs = checks.get('Log', [])
                if logs:
                    latest = logs[-1]
                    add(
                        f'  Last: {latest["End"]} | exit {latest["ExitCode"]} | failures {checks.get("FailingStreak", 0)}',
                        3,
                    )
                    if latest.get('Output', '').strip():
                        add('  ' + latest['Output'].strip()[:240], 3)
            add()
    if view in (0, 1):
        add('MATTERMOST  | live activity; seeded posts and system messages excluded', 1)
        chat = report.get('chat')
        if chat:
            staff = chat.get('staff_count')
            staff_label = (
                f'includes {staff} seeded staff' if staff is not None else 'staff count unavailable'
            )
            add(f'Online: {chat["online"]}    Posting users (5m): {chat["authors"]}')
            add(f'Human accounts: {chat["accounts"]} ({staff_label})')
            add(
                f'Human messages: {chat["messages_1m"]}/1m, {chat["messages_5m"]}/5m    Bot DM/group input: {chat["bot_inbound"]}/5m    Bot replies: {chat["bot_replies"]}/5m'
            )
            stamp = chat.get('last_message')
            last = (
                datetime.fromtimestamp(stamp / 1000).astimezone().strftime('%H:%M:%S %Z')
                if stamp
                else 'none in the past hour'
            )
            add('Last human message: ' + last)
            if view == 1:
                add()
                add('RECENT TALKERS (5 minutes)', 1)
                for item in chat['talkers']:
                    add(f'  @{item["username"]:<28} {item["messages"]:>5} messages')
                if not chat['talkers']:
                    add('  No recent human messages.')
                add()
                add('Online is Mattermost presence, not a count of browser connections.', 3)
                add(
                    'Counts include staff/admin activity. Message bodies and credentials are never fetched.',
                    3,
                )
        else:
            add('Activity unavailable (database stopped, starting or query failed).', 2)
        bot = report.get('bot', {})
        connected = bot.get('healthy', False)
        state = bot.get('state', 'unavailable / bot stopped')
        add('IT Support bot: ' + state, 0 if connected else 2)
        add(
            'Last bot message: '
            + (message_time(chat.get('last_bot_message')) if chat else 'unavailable')
        )
        add()
    if view in (0, 2):
        add('MALWARE / REVIEW', 1)
        storage = report.get('storage')
        if storage:
            add(
                f'Disk free: {human(storage["free"])}    {gauge(storage["used"], storage["total"])}',
                2 if storage['used'] / storage['total'] >= 0.85 else 0,
            )
            add(
                f'Stored: {human(storage["bytes"])} in {storage["files"]} files    Submissions: {sum(storage["states"].values())}'
            )
            if view == 2:
                for state, count in sorted(storage['states'].items()):
                    add(f'  {state:<24} {count:>7}')
            else:
                add(
                    'Queue: '
                    + (
                        '  '.join(
                            f'{state}={count}' for state, count in sorted(storage['states'].items())
                        )
                        or 'empty'
                    )
                )
            add('Latest submission: ' + (storage.get('latest') or 'none'))
            if view == 2:
                add()
                add(
                    'Disk capacity belongs to the underlying Docker filesystem, shared with images/logs.',
                    3,
                )
                add(
                    'Stored size includes attachments, emails, metadata and SQLite; it is not a quota.',
                    3,
                )
        else:
            add('Storage unavailable (support must be running).', 2)
        add()
    for warning in report['warnings']:
        add('! ' + warning, 2)
    return output


def dashboard(screen):
    global INTERVAL
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.timeout(150)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for number, color in (
            (1, curses.COLOR_CYAN),
            (2, curses.COLOR_RED),
            (3, curses.COLOR_YELLOW),
        ):
            curses.init_pair(number, color, -1)
    colors = {0: 0, 1: curses.A_BOLD, 2: curses.A_BOLD, 3: curses.A_DIM}
    if curses.has_colors():
        colors.update(
            {
                number: curses.color_pair(number) | (curses.A_BOLD if number != 3 else 0)
                for number in (1, 2, 3)
            }
        )
    results = queue.Queue()
    worker = None
    report = None
    next_poll = 0
    paused = False
    view = scroll = 0
    refresh = True

    def collect():
        try:
            results.put(snapshot())
        except Exception as error:
            results.put(
                {'time': time.time(), 'services': [], 'stats': {}, 'warnings': [str(error)]}
            )

    while True:
        now = time.monotonic()
        try:
            report = results.get_nowait()
            next_poll = time.monotonic() + INTERVAL
        except queue.Empty:
            pass
        if (
            (worker is None or not worker.is_alive())
            and not paused
            and (refresh or now >= next_poll)
        ):
            worker = threading.Thread(target=collect, daemon=True)
            worker.start()
            refresh = False
        screen.erase()
        height, width = screen.getmaxyx()

        def draw(row, text, style=0):
            if 0 <= row < height and width > 1:
                try:
                    screen.addnstr(row, 0, clean(text), width - 1, colors[style])
                except curses.error:
                    pass

        draw(0, 'CORPORATE OPERATIONS', 1)
        busy = worker is not None and worker.is_alive()
        stamp = (
            datetime.fromtimestamp(report['time']).astimezone().strftime('%H:%M:%S %Z')
            if report
            else '--'
        )
        state = (
            'PAUSED'
            if paused
            else 'refreshing...'
            if busy
            else f'next in {max(0, int(next_poll - time.monotonic()))}s'
        )
        draw(1, f'Updated {stamp} | every {INTERVAL}s | {state}', 3)
        draw(
            2,
            '   '.join(
                f'{i + 1} {name}' + (' *' if view == i else '')
                for i, name in enumerate(('Overview', 'Mattermost', 'Storage', 'Healthchecks'))
            ),
            1,
        )
        content = (
            lines(report, view) if report else [('Collecting Docker, chat and storage stats...', 0)]
        )
        available = max(0, height - 5)
        scroll = min(scroll, max(0, len(content) - available))
        for row, (text, style) in enumerate(content[scroll : scroll + available], 4):
            draw(row, text, style)
        draw(
            height - 1,
            'q quit | r refresh | p pause | +/- interval | 1-4 views | arrows/PgUp/PgDn scroll',
            3,
        )
        screen.refresh()
        key = screen.getch()
        if key in (ord('q'), ord('Q'), 27):
            return
        if key in (ord('1'), ord('2'), ord('3'), ord('4')):
            view, scroll = key - ord('1'), 0
        elif key in (ord('r'), ord('R')):
            refresh, paused = True, False
        elif key in (ord('p'), ord('P'), ord(' ')):
            paused = not paused
        elif key in (ord('+'), ord('=')):
            INTERVAL += 5
        elif key == ord('-'):
            INTERVAL = max(5, INTERVAL - 5)
            next_poll = min(next_poll, time.monotonic() + INTERVAL)
        elif key == curses.KEY_DOWN:
            scroll += 1
        elif key == curses.KEY_UP:
            scroll = max(0, scroll - 1)
        elif key == curses.KEY_NPAGE:
            scroll += max(1, available)
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - max(1, available))


def main():
    global INTERVAL, COMPOSE
    INTERVAL = int(sys.argv[1])
    COMPOSE = ['docker', 'compose'] if sys.argv[2] == 'plugin' else ['docker-compose']
    try:
        if sys.stdout.isatty() and os.environ.get('TERM', '') not in ('', 'dumb'):
            with open('/dev/tty', 'rb', buffering=0) as terminal:
                os.dup2(terminal.fileno(), 0)
                curses.wrapper(dashboard)
        else:
            report = snapshot()
            for text, _ in lines(report, 0):
                print(text)
    except KeyboardInterrupt:
        pass
    except (OSError, curses.error) as error:
        print(f'Monitor: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
