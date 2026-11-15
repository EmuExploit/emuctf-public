"""Deterministic mailbox signals. Nothing is fetched, unpacked or executed."""

import base64
import binascii
import html
import ipaddress
import re
import unicodedata
from email.utils import parseaddr
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import nh3

from support import config, screening


def add_signal(signals, code, detail):
    existing = next((item for item in signals if item['code'] == code), None)
    if existing:
        if detail not in existing['details'] and len(existing['details']) < 12:
            existing['details'].append(detail)
        return
    label, severity, points, outcome = screening.SUPPORT_SCREENING_RULES[code]
    signals.append(
        dict(
            code=code,
            label=label,
            severity=severity,
            points=points,
            outcome=outcome,
            details=[detail],
        )
    )


class EmailHTML(HTMLParser):
    def __init__(self, signals):
        super().__init__(convert_charrefs=True)
        self.signals, self.links, self.anchors = signals, [], []
        self.anchor = None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or '' for key, value in attrs}
        if tag in {'script', 'iframe', 'object', 'embed', 'applet', 'base'}:
            add_signal(self.signals, 'ACTIVE_HTML', f'Active HTML element: {tag}')
        if tag in {'svg', 'math'}:
            add_signal(
                self.signals,
                'RICH_HTML',
                f'Complex HTML element: {tag}; not proof of script execution',
            )
        if tag == 'form' or tag == 'input' and attrs.get('type', '').lower() == 'password':
            add_signal(self.signals, 'HTML_FORM', 'Email contains a form or password field')
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh':
            add_signal(self.signals, 'ACTIVE_HTML', 'HTML refresh redirect')
        if (
            tag == 'a'
            and 'download' in attrs
            and (attrs.get('href') or '').strip().casefold().startswith(('data:', 'blob:'))
        ):
            add_signal(
                self.signals,
                'EMBEDDED_DOWNLOAD',
                'Download attribute points to an inline data/blob URL; possible HTML smuggling',
            )
        for key, value in attrs.items():
            value = value or ''
            if key.startswith('on') or key == 'srcdoc':
                add_signal(self.signals, 'ACTIVE_HTML', f'Active HTML attribute: {key}')
            if key in {'href', 'src', 'srcset', 'action', 'background', 'data', 'xlink:href'}:
                compact = re.sub(r'\s+', '', html.unescape(value)).lower()
                if compact.startswith(('javascript:', 'vbscript:', 'data:text/html')):
                    add_signal(self.signals, 'ACTIVE_HTML', 'Executable URL in email HTML')
                if key == 'href' and value:
                    self.links.append(value)
                    if tag == 'a':
                        self.finish_anchor()
                        self.anchor = {'href': value, 'text': ''}
                if (key != 'href' or tag == 'link') and compact.startswith(
                    ('http:', 'https:', '//')
                ):
                    add_signal(self.signals, 'REMOTE_CONTENT', 'Email loads remote content')
            if key == 'style':
                if re.search(r'url\s*\(|@import', value, re.I):
                    add_signal(
                        self.signals, 'REMOTE_CONTENT', 'CSS references an external resource'
                    )
                if re.search(
                    r'display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\D|$)|font-size\s*:\s*0',
                    value,
                    re.I,
                ):
                    add_signal(self.signals, 'HIDDEN_HTML', 'Hidden HTML content')
            if key == 'hidden':
                add_signal(self.signals, 'HIDDEN_HTML', 'Hidden HTML content')

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a':
            self.finish_anchor()

    def finish_anchor(self):
        if self.anchor is not None:
            self.anchors.append(self.anchor)
            self.anchor = None


def canonical_host(host):
    try:
        return (
            (host or '').rstrip('.').casefold().encode('idna').decode('ascii').removeprefix('www.')
        )
    except UnicodeError:
        return (host or '').casefold()


def parsed_link(value):
    value = html.unescape(value).strip()
    if value.startswith('//'):
        value = 'https:' + value
    try:
        return urlsplit(value)
    except ValueError:
        return None


def action_matches(pattern, text):
    """Ignore direct negations, e.g. 'do not disable Defender'. Not an NLP model."""
    for match in re.finditer(pattern, text, re.I):
        before = text[max(0, match.start() - 65) : match.start()]
        if not re.search(
            r'\b(?:do not|don.t|never|avoid|must not|should not|not to)\s+(?:(?:ever|please|try to|attempt to)\s+){0,2}$',
            before,
            re.I,
        ):
            yield match


def attachment_filename(filename):
    original = filename.replace('\\', '/').rsplit('/', 1)[-1]
    normalized = unicodedata.normalize('NFKC', original).rstrip(' .')
    extension = normalized.rsplit('.', 1)[-1].casefold() if '.' in normalized else ''
    return original, normalized, extension


def screen_links(signals, parser, text):
    links = set(parser.links + re.findall(r'https?://[^\s<>"\']+', text, re.I))
    if links:
        add_signal(signals, 'LINK', f'{len(links)} unique link(s) in email')
    risky_extensions = (
        screening.SUPPORT_EXECUTABLE_EXTENSIONS
        | screening.SUPPORT_SCRIPT_EXTENSIONS
        | screening.SUPPORT_SHORTCUT_EXTENSIONS
    )
    for link in links:
        parsed = parsed_link(link)
        if parsed is None:
            continue
        host = canonical_host(parsed.hostname)
        if host in screening.SUPPORT_SHORT_LINK_HOSTS:
            add_signal(signals, 'SHORT_LINK', f'Shortened URL: {host}')
        if parsed.username is not None:
            add_signal(
                signals, 'DECEPTIVE_URL', f'URL contains user-info before destination host: {host}'
            )
        if host.startswith('xn--') or '.xn--' in host:
            add_signal(
                signals, 'PUNYCODE', 'Internationalized/punycode URL hostname; no reputation check'
            )
        try:
            ipaddress.ip_address(host)
            add_signal(
                signals, 'IP_LINK', f'URL uses an IP address: {host}; common in this challenge'
            )
        except ValueError:
            pass
        if parsed.scheme.casefold() in screening.SUPPORT_DANGEROUS_URI_SCHEMES:
            add_signal(signals, 'DANGEROUS_URI', f'Link invokes an OS handler: {parsed.scheme}')
        if parsed.scheme.casefold() == 'file':
            add_signal(signals, 'NETWORK_PATH', 'Email contains a file:// link')
        if parsed.scheme.casefold() in {'http', 'https'}:
            extension = attachment_filename(unquote(parsed.path))[2]
            if extension in risky_extensions:
                add_signal(
                    signals,
                    'DOWNLOAD_LINK',
                    f'URL path ends in .{extension}; destination not fetched',
                )
    if re.search(r'\\\\[a-z0-9][^\s<>"\']*\\', text, re.I):
        add_signal(signals, 'NETWORK_PATH', 'Email contains a Windows network path')
    for anchor in parser.anchors:
        label = anchor['text'].strip()
        # Compare only a URL/domain explicitly presented as the link label.
        # "Open ticket" or a brand name makes no checkable hostname claim.
        if not re.fullmatch(r'(?:https?://|www\.)[^\s]+|[\w-]+(?:\.[\w-]+)+/?', label, re.I):
            continue
        shown = parsed_link(label if '://' in label else 'https://' + label)
        actual = parsed_link(anchor['href'])
        if (
            shown
            and actual
            and shown.hostname
            and actual.hostname
            and canonical_host(shown.hostname) != canonical_host(actual.hostname)
        ):
            add_signal(
                signals,
                'LINK_MISMATCH',
                f'Visible host {canonical_host(shown.hostname)} differs from link host {canonical_host(actual.hostname)}',
            )


def screen_email(values, *, has_attachments=False):
    signals = []
    raw = '\n'.join(values.values())
    spaced = re.sub(r'</?(?:p|div|br|li|tr|h[1-6])\b[^>]*>', ' ', values['body'], flags=re.I)
    plain = html.unescape(nh3.clean(spaced, tags=set(), attributes={}, link_rel=None))
    parser = EmailHTML(signals)
    parser.feed(values['body'])
    parser.close()
    parser.finish_anchor()
    texts = [html.unescape(values['subject'] + '\n' + values['body']), plain]
    found_base64 = bool(re.search(r';base64\s*,', raw, re.I))
    pattern = (
        r'(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{%d,}={0,2}(?![A-Za-z0-9+/_=-])'
        % screening.SUPPORT_BASE64_MIN_LENGTH
    )
    for match in re.finditer(pattern, texts[0]):
        candidate = match.group()
        if re.fullmatch(r'[0-9a-fA-F]+', candidate):
            continue
        try:
            decoded = base64.b64decode(
                candidate + '=' * (-len(candidate) % 4), altchars=b'-_', validate=True
            )
        except (ValueError, binascii.Error):
            continue
        found_base64 = True
        texts.append(decoded.decode('utf-8', 'ignore'))
        if len(decoded) % 2 == 0:
            texts.append(decoded.decode('utf-16-le', 'ignore'))
    if found_base64:
        add_signal(signals, 'BASE64', 'Base64-encoded content in email')
    normalized = unicodedata.normalize('NFKC', '\n'.join(texts))
    without_hidden = re.sub('[\u200b\u200c\u200d\u2060\ufeff]', '', normalized)
    if without_hidden != normalized or re.search(r'(?:&#(?:x[0-9a-f]+|\d+);?){4,}', raw, re.I):
        add_signal(
            signals,
            'ENCODED_TEXT',
            'Invisible separators or a run of character references in email',
        )
    searchable = re.sub(r'\s+', ' ', without_hidden).casefold()
    for keyword in screening.SUPPORT_EMAIL_KEYWORDS:
        if re.search(r'(?<!\w)' + re.escape(keyword) + r'(?!\w)', searchable):
            add_signal(signals, 'COMMAND_LANGUAGE', f'Matched term: {keyword}')
    families = (
        ('SECURITY_BYPASS', screening.SUPPORT_SECURITY_INSTRUCTIONS),
        ('RUN_COMMAND', screening.SUPPORT_RUN_COMMAND_PATTERNS),
        ('DEPENDENCY_INSTALL', screening.SUPPORT_DEPENDENCY_INSTALL_PATTERNS),
        ('EXECUTION_REQUEST', screening.SUPPORT_EXECUTION_REQUEST_PATTERNS),
        ('PRIVILEGED_ACTION', screening.SUPPORT_PRIVILEGED_ACTION_PATTERNS),
        ('CREDENTIAL_REQUEST', screening.SUPPORT_CREDENTIAL_PATTERNS),
        ('SENSITIVE_FILE_REQUEST', screening.SUPPORT_SENSITIVE_FILE_PATTERNS),
        ('FINANCIAL_REQUEST', screening.SUPPORT_FINANCIAL_PATTERNS),
    )
    for code, patterns in families:
        for pattern in patterns:
            for match in action_matches(pattern, searchable):
                add_signal(signals, code, f'Matched instruction: {match.group()[:180]}')
    for pattern in screening.SUPPORT_SECRECY_PATTERNS:
        if re.search(pattern, searchable):
            add_signal(signals, 'SECRECY', 'Requests secrecy or avoiding support/security staff')
    for phrase in screening.SUPPORT_URGENCY_TERMS:
        if re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', searchable):
            add_signal(signals, 'URGENCY', f'Matched urgency: {phrase}')
    for pattern in screening.SUPPORT_THREAT_PATTERNS:
        if re.search(pattern, searchable):
            add_signal(signals, 'THREATS', 'Threat of suspension, loss, or punishment')
    if re.search(screening.SUPPORT_EMAIL_PAYLOAD_PATTERN, searchable, re.I):
        add_signal(
            signals,
            'MALWARE_LANGUAGE',
            'Email explicitly mentions a payload, reverse shell, or C2 tool',
        )
    if re.search(
        r'\b(?:(?:zip|archive|7z|rar).{0,25}password|password\s+(?:for|to)\s+(?:the\s+)?(?:zip|archive|attachment))\b',
        searchable,
    ):
        add_signal(
            signals,
            'ARCHIVE_PASSWORD',
            'Email supplies or discusses an archive password; contents need manual review',
        )
    if re.search(r'\b(?:dear|hello|hi)\s+(?:user|customer|sir|madam|recipient)\b', searchable):
        add_signal(signals, 'GENERIC_GREETING', 'Generic greeting; no rejection points')
    if re.match(r'\s*(?:re|fw|fwd)\s*:', values['subject'], re.I):
        add_signal(
            signals,
            'REPLY_SUBJECT',
            'Reply/forward prefix; conversation history cannot be verified here',
        )
    display, address = parseaddr(values['sender'])
    sender_host = canonical_host(address.rpartition('@')[2])
    claimed_emails = re.findall(r'[\w.+-]+@([\w.-]+)', display)
    internal_claim = re.search(screening.SUPPORT_INTERNAL_DISPLAY_PATTERN, display, re.I)
    if (internal_claim and sender_host not in screening.SUPPORT_INTERNAL_DOMAINS) or any(
        canonical_host(host) != sender_host for host in claimed_emails
    ):
        add_signal(
            signals,
            'SENDER_CLAIM',
            'Display name claims another email domain or the internal organization; From is user-supplied',
        )
    screen_links(signals, parser, '\n'.join(texts))

    # Language flags describe surface features; they are informational and score zero.
    words = re.findall(r'\b[^\W\d_]+\b', plain, re.UNICODE)
    delivery = has_attachments or any(
        item['code'] in {'DOWNLOAD_LINK', 'NETWORK_PATH', 'EXECUTION_REQUEST', 'EMBEDDED_DOWNLOAD'}
        for item in signals
    )
    if delivery:
        pretext = re.sub(r'https?://[^\s<>]+', ' ', plain, flags=re.I)
        pretext_words = re.findall(r'\b[^\W\d_]+\b', pretext, re.UNICODE)
        if len(pretext_words) < screening.SUPPORT_PRETEXT_MIN_WORDS:
            add_signal(
                signals,
                'THIN_PRETEXT',
                f'{len(pretext_words)} visible body words excluding URLs; review minimum is {screening.SUPPORT_PRETEXT_MIN_WORDS}. Word count alone does not establish a convincing pretext.',
            )
    if re.search(r'[!?]{3,}|\.{4,}', plain):
        add_signal(signals, 'PUNCTUATION', 'Repeated exclamation/question marks or excessive dots')
    if len(words) >= 25 and not re.search(r'[.!?]', plain):
        add_signal(signals, 'PUNCTUATION', 'Long message without sentence punctuation')
    if re.search(r'[a-z][.!?][A-Z]', plain):
        add_signal(signals, 'PUNCTUATION', 'Missing space after sentence punctuation')
    if (
        len(words) >= 10
        and sum(word.isupper() for word in words if len(word) > 1) / len(words) >= 0.6
    ):
        add_signal(signals, 'ALL_CAPS', 'Most words are uppercase')
    if re.search(
        r'\b(?:you is|we is|i is|they is|you has|we has|i has|please to|kindly to)\b|\b([a-z]{3,})\s+\1\b',
        plain,
        re.I,
    ):
        add_signal(signals, 'LANGUAGE', 'Possible grammar error or repeated word')
    if re.search(r'\b(?:u|ur|pls|plz|thx)\b', plain, re.I):
        add_signal(signals, 'INFORMAL_LANGUAGE', 'Informal abbreviations')
    return signals


def screen_attachment_metadata(signals, filename, size, declared_mime, identified):
    original, normalized, extension = attachment_filename(filename)
    # Escape format/control characters in evidence so the review text itself
    # cannot conceal the extension with Unicode direction overrides.
    name = ''.join(
        f'\\u{ord(char):04x}' if unicodedata.category(char) in {'Cc', 'Cf'} else char
        for char in original
    )
    risky = (
        screening.SUPPORT_EXECUTABLE_EXTENSIONS
        | screening.SUPPORT_SCRIPT_EXTENSIONS
        | screening.SUPPORT_SHORTCUT_EXTENSIONS
        | screening.SUPPORT_MACRO_EXTENSIONS
    )
    if extension in screening.SUPPORT_BLOCKED_EXTENSIONS:
        add_signal(signals, 'EXTENSION', f'{name}: blocked extension .{extension}')
    if size == 0:
        add_signal(signals, 'EMPTY_FILE', f'{name}: zero-byte attachment')
    if size > config.SUPPORT_MAX_ATTACHMENT_BYTES:
        add_signal(
            signals,
            'SIZE',
            f'{name}: exceeds {config.SUPPORT_MAX_ATTACHMENT_BYTES // (1024 * 1024)} MiB review limit',
        )
    if not extension:
        add_signal(signals, 'NO_EXTENSION', f'{name}: filename has no extension')
    if any(char in original for char in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'):
        add_signal(
            signals, 'FILENAME_BIDI', f'{name}: filename contains Unicode direction controls'
        )
    parts = normalized.casefold().split('.')
    if extension in risky and any(
        part in screening.SUPPORT_BENIGN_DISGUISE_EXTENSIONS for part in parts[1:-1]
    ):
        add_signal(
            signals,
            'DOUBLE_EXTENSION',
            f'{name}: benign document/image extension precedes .{extension}',
        )
    hidden_name = re.search('[\u200b\u200c\u200d\u2060\ufeff]', original)
    if (
        (original != normalized and extension in risky)
        or hidden_name
        or (extension in risky and re.search(r'\s{4,}', original))
    ):
        add_signal(
            signals,
            'FILENAME_TRICK',
            f'{name}: Unicode normalization, invisible spacing, or Windows trailing dots/spaces change the name',
        )
    if re.search(screening.SUPPORT_PAYLOAD_NAME_PATTERN, normalized, re.I):
        add_signal(
            signals, 'PAYLOAD_NAME', f'{name}: explicit payload/C2 filename; not a signature match'
        )
    categories = (
        ('EXECUTABLE', screening.SUPPORT_EXECUTABLE_EXTENSIONS),
        ('SCRIPT', screening.SUPPORT_SCRIPT_EXTENSIONS),
        ('SHORTCUT', screening.SUPPORT_SHORTCUT_EXTENSIONS),
        ('DISK_IMAGE', screening.SUPPORT_DISK_IMAGE_EXTENSIONS),
        ('MACRO_CAPABLE', screening.SUPPORT_MACRO_EXTENSIONS),
        ('HTML_ATTACHMENT', screening.SUPPORT_HTML_EXTENSIONS),
        ('ENCODED_SCRIPT', screening.SUPPORT_ENCODED_SCRIPT_EXTENSIONS),
    )
    for code, extensions in categories:
        if extension in extensions:
            add_signal(
                signals,
                code,
                f'{name}: filename extension .{extension}; contents not inspected by this heuristic',
            )
    if extension in screening.SUPPORT_NON_WINDOWS_EXTENSIONS:
        add_signal(
            signals,
            'PLATFORM_MISMATCH',
            f'{name}: .{extension} targets a different OS; support endpoint is Windows',
        )
    if identified['error']:
        add_signal(signals, 'SCAN_ERROR', f'{name}: {identified["error"]}')
        return
    description, mime = identified['description'], identified['mime'].casefold()
    if re.search(r'\b(?:PE32|ELF|Mach-O|MS-DOS executable)\b', description) or mime in {
        'application/x-dosexec',
        'application/vnd.microsoft.portable-executable',
        'application/x-executable',
        'application/x-pie-executable',
        'application/x-sharedlib',
        'application/x-mach-binary',
    }:
        add_signal(signals, 'EXECUTABLE', f'{name}: file identifies {description}')
    if re.search(
        r'\b(?:script|batch file|JavaScript source|byte-compiled Python|Python byte-code)\b',
        description,
        re.I,
    ) or mime in {
        'application/javascript',
        'text/javascript',
        'text/x-shellscript',
        'text/x-python',
        'text/x-perl',
        'application/x-powershell',
        'application/x-bytecode.python',
        'application/x-python-code',
    }:
        add_signal(signals, 'SCRIPT', f'{name}: file identifies {description}')
    if re.search(r'\b(?:ELF|Mach-O)\b', description):
        add_signal(
            signals, 'PLATFORM_MISMATCH', f'{name}: file identifies a non-Windows executable'
        )
    if re.search(
        r'(?:MS Windows|Windows).*shortcut|Internet shortcut', description, re.I
    ) or mime in {'application/x-ms-shortcut', 'application/x-mswinurl'}:
        add_signal(signals, 'SHORTCUT', f'{name}: file identifies {description}')
    if re.search(r'ISO 9660|disk image|VHDX?', description, re.I):
        add_signal(signals, 'DISK_IMAGE', f'{name}: file identifies {description}')
    if mime in {'text/html', 'application/xhtml+xml', 'image/svg+xml'}:
        add_signal(signals, 'HTML_ATTACHMENT', f'{name}: file identifies {mime}')

    declared = declared_mime.casefold().split(';', 1)[0].strip()
    generic = {
        '',
        'application/octet-stream',
        'binary/octet-stream',
        'application/x-empty',
        'inode/x-empty',
    }
    expected = screening.SUPPORT_EXPECTED_MIME.get(extension)
    if expected and size and mime not in expected:
        # Unknown data and loosely identified Office/ZIP/XML files need manual
        # review, rather than claiming a positive masquerading detection.
        uncertain = mime in generic or (
            extension in {'docx', 'xlsx', 'pptx'}
            and mime
            in {'application/x-ole-storage', 'application/cdfv2', 'text/xml', 'application/xml'}
        )
        add_signal(
            signals,
            'TYPE_UNVERIFIED' if uncertain else 'TYPE_MISMATCH',
            f'{name}: .{extension} versus identified MIME {mime or "unknown"}',
        )
    if (
        declared not in generic
        and mime not in generic
        and declared != mime
        and not (expected and declared in expected and mime in expected)
    ):
        add_signal(
            signals,
            'MIME_MISMATCH',
            f'{name}: uploader declares {declared}, file identifies {mime}; uploader MIME is untrusted',
        )


def saved_signals(meta):
    """Normalize pre-signals and duplicate-era records without changing storage."""
    # Historical duplicate signals no longer affect scores or tags.
    signals = [item for item in meta.get('signals', []) if item['code'] != 'DUPLICATE']
    # Older records keep their existing tags/reasons without schema changes.
    if not signals:
        signals = []
        for reason in meta.get('reasons', []):
            lower = reason.lower()
            if lower.startswith('duplicate:'):
                continue
            code = (
                'BASE64'
                if lower.startswith('base64:')
                else 'COMMAND_LANGUAGE'
                if lower.startswith('email:')
                else 'EXTENSION'
                if 'extension' in lower
                else 'YARA'
                if 'yara match' in lower
                else 'SCAN_ERROR'
                if 'yara' in lower
                else 'SIZE'
            )
            add_signal(signals, code, reason)
        if meta.get('manual_review'):
            add_signal(signals, 'ARCHIVE', 'Archive contents need manual review')
    return signals


def screening_report(meta):
    signals = saved_signals(meta)
    classified = []
    for item in signals:
        source = (
            'attachment'
            if item['outcome'] == 'bad_payload'
            or item['code'] in screening.SUPPORT_ATTACHMENT_SIGNALS
            else 'email'
        )
        classified.append({**item, 'source': source, 'rule_points': item['points']})
    # Keep every tag/evidence item. Award only the strongest code within a
    # correlated family, with configuration order resolving equal weights.
    for codes in screening.SUPPORT_SCREENING_GROUPS.values():
        members = sorted(
            (item for item in classified if item['code'] in codes),
            key=lambda item: codes.index(item['code']),
        )
        if not members:
            continue
        winner = max(members, key=lambda item: item['points'])
        for item in members:
            if item is not winner and item['points']:
                item['covered_by'] = winner['label']
                item['points'] = 0
    email = sum(item['points'] for item in classified if item['source'] == 'email')
    attachment = sum(item['points'] for item in classified if item['source'] == 'attachment')
    scores = dict(email=email, attachment=attachment, combined=email + attachment)
    thresholds = dict(
        email=screening.SUPPORT_EMAIL_REJECTION_THRESHOLD,
        attachment=screening.SUPPORT_ATTACHMENT_REJECTION_THRESHOLD,
        combined=screening.SUPPORT_COMBINED_REJECTION_THRESHOLD,
    )
    triggered = [name for name in scores if scores[name] >= thresholds[name]]
    if any(item['code'] == 'SCAN_ERROR' for item in classified):
        # Incomplete inspection is always rejected, even if thresholds change.
        suggested = 'bad_payload'
        triggered.append('scan_error')
    elif 'email' in triggered and 'attachment' in triggered:
        suggested = (
            'bad_payload'
            if attachment / thresholds['attachment'] >= email / thresholds['email']
            else 'bad_email'
        )
    elif 'attachment' in triggered:
        suggested = 'bad_payload'
    elif 'email' in triggered:
        suggested = 'bad_email'
    elif 'combined' in triggered:
        suggested = 'other'
    else:
        suggested = None
    return dict(
        signals=classified,
        score=scores['combined'],
        scores=scores,
        thresholds=thresholds,
        triggered=triggered,
        suggested_state=suggested,
    )


def screening_tags(meta=None, *, report=None):
    if report is None:
        report = screening_report(meta)
    return [
        dict(code=item['code'], label=item['label'], severity=item['severity'])
        for item in report['signals']
    ]
