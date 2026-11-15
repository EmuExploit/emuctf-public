# Correlated signals contribute only their strongest weight. Thresholds use >=.
SUPPORT_BLOCKED_EXTENSIONS = {
    'ps1',
    'psm1',
    'psd1',
    'bat',
    'cmd',
    'vbs',
    'vbe',
    'js',
    'jse',
    'wsf',
    'wsh',
    'hta',
    'sct',
    'py',
    'pyw',
    'pyc',
    'pyo',
    'pyz',
    'pyzw',
    'ipynb',
    'sh',
    'bash',
    'pl',
    'rb',
    'rbw',
    'jar',
    'class',
}

SUPPORT_EMAIL_KEYWORDS = (
    'powershell',
    'pwsh',
    'defender',
    'antivirus',
    'anti-virus',
    'amsi',
    'cmd.exe',
    'mshta',
    'rundll32',
    'regsvr32',
    'certutil',
    'bitsadmin',
    'executionpolicy',
    'encodedcommand',
    'set-mppreference',
)

SUPPORT_BASE64_MIN_LENGTH = 64

SUPPORT_EMAIL_REJECTION_THRESHOLD = 100

SUPPORT_ATTACHMENT_REJECTION_THRESHOLD = 100

SUPPORT_COMBINED_REJECTION_THRESHOLD = 120

SUPPORT_PRETEXT_MIN_WORDS = 35

SUPPORT_SCREENING_RULES = {
    'LINK': ('LINK', 'informational', 10, None),
    'REMOTE_CONTENT': ('REMOTE CONTENT', 'informational', 15, None),
    'HIDDEN_HTML': ('HIDDEN HTML', 'informational', 20, None),
    'BASE64': ('BASE64', 'informational', 30, None),
    # Archive/container trade-off; extracted members receive YARA only.
    # Below the attachment threshold alone; stronger format signals cover it.
    'ARCHIVE': ('ARCHIVE', 'malicious', 40, 'bad_payload'),
    'SCAN_ERROR': ('SCAN ERROR', 'malicious', 100, 'bad_payload'),
    'PUNYCODE': ('PUNYCODE', 'informational', 100, None),
    'PUNCTUATION': ('PUNCTUATION', 'informational', 5, None),
    'ALL_CAPS': ('ALL CAPS', 'informational', 15, None),
    'LANGUAGE': ('LANGUAGE', 'informational', 0, None),
    'INFORMAL_LANGUAGE': ('INFORMAL LANGUAGE', 'informational', 5, None),
    'COMMAND_LANGUAGE': ('TOOL / SECURITY TERM', 'informational', 20, None),
    'RICH_HTML': ('COMPLEX HTML', 'informational', 0, None),
    'ARCHIVE_PASSWORD': ('ARCHIVE PASSWORD', 'informational', 20, None),
    'GENERIC_GREETING': ('GENERIC GREETING', 'informational', 0, None),
    'REPLY_SUBJECT': ('REPLY SUBJECT', 'informational', 0, None),
    'ENCODED_TEXT': ('ENCODED TEXT', 'informational', 10, None),
    'MIME_MISMATCH': ('DECLARED MIME MISMATCH', 'informational', 10, None),
    'TYPE_UNVERIFIED': ('TYPE UNVERIFIED', 'informational', 10, None),
    'NO_EXTENSION': ('NO EXTENSION', 'informational', 10, None),
    'SECURITY_BYPASS': ('SECURITY BYPASS', 'malicious', 100, 'bad_email'),
    'RUN_COMMAND': ('RUN COMMAND', 'malicious', 100, 'bad_email'),
    'DEPENDENCY_INSTALL': ('INSTALL RUNTIME / DEPENDENCIES', 'malicious', 100, 'bad_email'),
    'EXECUTION_REQUEST': ('DIRECT EXECUTION REQUEST', 'malicious', 50, 'bad_email'),
    'THIN_PRETEXT': ('THIN DELIVERY PRETEXT', 'malicious', 50, 'bad_email'),
    'ACTIVE_HTML': ('ACTIVE HTML', 'malicious', 100, 'bad_email'),
    'EMBEDDED_DOWNLOAD': ('EMBEDDED FILE DOWNLOAD', 'malicious', 100, 'bad_email'),
    'HTML_FORM': ('HTML FORM', 'malicious', 100, 'bad_email'),
    'CREDENTIAL_REQUEST': ('CREDENTIAL REQUEST', 'malicious', 100, 'bad_email'),
    'PRIVILEGED_ACTION': ('ENABLE ACTIVE CONTENT / ADMIN', 'malicious', 100, 'bad_email'),
    'SENSITIVE_FILE_REQUEST': ('SENSITIVE FILE REQUEST', 'malicious', 100, 'bad_email'),
    'MALWARE_LANGUAGE': ('PAYLOAD / C2 LANGUAGE', 'malicious', 60, 'bad_email'),
    'URGENCY': ('URGENCY', 'malicious', 20, 'spam'),
    'THREATS': ('THREATS', 'malicious', 40, 'spam'),
    'SECRECY': ('SECRECY', 'malicious', 50, 'bad_email'),
    'FINANCIAL_REQUEST': ('PAYMENT / GIFT CARD REQUEST', 'malicious', 50, 'spam'),
    'SENDER_CLAIM': ('SENDER CLAIM MISMATCH', 'malicious', 40, 'bad_email'),
    'SHORT_LINK': ('SHORT LINK', 'malicious', 25, 'bad_email'),
    'IP_LINK': ('IP LINK', 'informational', 0, None),
    'DECEPTIVE_URL': ('URL USER-INFO', 'malicious', 60, 'bad_email'),
    'LINK_MISMATCH': ('LINK TEXT MISMATCH', 'malicious', 60, 'bad_email'),
    'DOWNLOAD_LINK': ('EXECUTABLE DOWNLOAD LINK', 'malicious', 70, 'bad_email'),
    'NETWORK_PATH': ('NETWORK FILE LINK', 'malicious', 70, 'bad_email'),
    'DANGEROUS_URI': ('OS HANDLER LINK', 'malicious', 100, 'bad_email'),
    'YARA': ('YARA', 'malicious', 100, 'bad_payload'),
    'EXTENSION': ('EXTENSION', 'malicious', 100, 'bad_payload'),
    'TYPE_MISMATCH': ('TYPE MISMATCH', 'malicious', 80, 'bad_payload'),
    'EXECUTABLE': ('EXECUTABLE', 'malicious', 60, 'bad_payload'),
    'SCRIPT': ('SCRIPT / INTERPRETER FILE', 'malicious', 100, 'bad_payload'),
    'SHORTCUT': ('SHORTCUT / URL FILE', 'malicious', 60, 'bad_payload'),
    'DISK_IMAGE': ('DISK IMAGE', 'malicious', 60, 'bad_payload'),
    'MACRO_CAPABLE': ('MACRO-CAPABLE DOCUMENT', 'malicious', 80, 'bad_payload'),
    'HTML_ATTACHMENT': ('HTML / SVG ATTACHMENT', 'malicious', 60, 'bad_payload'),
    'ENCODED_SCRIPT': ('ENCODED SCRIPT TYPE', 'malicious', 100, 'bad_payload'),
    'DOUBLE_EXTENSION': ('MISLEADING DOUBLE EXTENSION', 'malicious', 50, 'bad_payload'),
    'FILENAME_BIDI': ('FILENAME DIRECTION CONTROL', 'malicious', 100, 'bad_payload'),
    'FILENAME_TRICK': ('FILENAME NORMALIZATION TRICK', 'malicious', 60, 'bad_payload'),
    'PAYLOAD_NAME': ('OBVIOUS PAYLOAD NAME', 'malicious', 50, 'bad_payload'),
    'PLATFORM_MISMATCH': ('NON-WINDOWS PAYLOAD TYPE', 'malicious', 100, 'bad_payload'),
    'EMPTY_FILE': ('EMPTY ATTACHMENT', 'malicious', 100, 'bad_payload'),
    'SIZE': ('SIZE', 'malicious', 40, 'bad_payload'),
}

SUPPORT_SCREENING_GROUPS = {
    'execution_instructions': (
        'SECURITY_BYPASS',
        'DEPENDENCY_INSTALL',
        'RUN_COMMAND',
        'PRIVILEGED_ACTION',
    ),
    'delivery_pretext': ('EXECUTION_REQUEST', 'THIN_PRETEXT'),
    'pressure': ('THREATS', 'URGENCY'),
    'url_deception': ('LINK_MISMATCH', 'DECEPTIVE_URL'),
    'html_execution': ('ACTIVE_HTML', 'EMBEDDED_DOWNLOAD'),
    # A double extension is another presentation of the delivery format, rather
    # than a second charge on top of an executable or shortcut's format score.
    'file_format': (
        'EXTENSION',
        'ENCODED_SCRIPT',
        'SHORTCUT',
        'EXECUTABLE',
        'SCRIPT',
        'DISK_IMAGE',
        'MACRO_CAPABLE',
        'HTML_ATTACHMENT',
        'ARCHIVE',
        'DOUBLE_EXTENSION',
    ),
    'file_disguise': ('FILENAME_BIDI', 'TYPE_MISMATCH', 'FILENAME_TRICK'),
}

SUPPORT_ATTACHMENT_SIGNALS = {
    'ARCHIVE',
    'SCAN_ERROR',
    'MIME_MISMATCH',
    'TYPE_UNVERIFIED',
    'NO_EXTENSION',
}

SUPPORT_INTERNAL_DOMAINS = {'ctf.emu.team', 'emu.team'}

SUPPORT_INTERNAL_DISPLAY_PATTERN = r'\b(?:emu industries|emu ctf|ctf\.emu\.team)\b'

SUPPORT_SECURITY_INSTRUCTIONS = (
    r'\b(?:disable|turn off|switch off|deactivate|bypass)\s+(?:(?:your|the|windows|microsoft)\s+){0,3}(?:defender|antivirus|anti-virus|amsi|smartscreen|security|protection|real.time protection)\b',
    r'\b(?:ignore|dismiss|bypass)\s+(?:(?:any|the|your|security|antivirus|defender|browser)\s+){0,3}(?:warnings?|alerts?|protection)\b',
    r'\b(?:add|create)\s+(?:(?:an?|antivirus|defender)\s+){0,2}exclusion\b',
    r'\b(?:set-mppreference|disablerealtimemonitoring)\b',
    r'\b(?:unblock|remove)\b.{0,35}\b(?:mark.of.the.web|motw|security block)\b',
)

SUPPORT_RUN_COMMAND_PATTERNS = (
    r'\b(?:run|execute|paste|type|enter)\s+(?:(?:this|the|following|these|a|below)\s+){0,3}(?:(?:powershell|shell|terminal)\s+)?commands?\b',
    r'\b(?:copy|paste)\b.{0,80}\b(?:powershell|terminal|command prompt|run (?:box|dialog))\b',
    r'\b(?:press|hit|use)\s+(?:windows|win)\s*\+\s*r\b',
    r'\b(?:open|launch)\s+(?:a\s+)?(?:powershell|terminal|command prompt)\b.{0,60}\b(?:paste|type|execute|run)\b',
    r'\b(?:powershell(?:\.exe)?|pwsh(?:\.exe)?)\s+-(?:enc(?:odedcommand)?|e|nop(?:rofile)?|w(?:indowstyle)?|executionpolicy|command|c)\b',
    r'\bcmd(?:\.exe)?\s+/[ck]\b',
)

SUPPORT_DEPENDENCY_INSTALL_PATTERNS = (
    r'\b(?:install|download|set up)\s+(?:(?:the|a|an|latest|required)\s+){0,3}(?:python(?:\s*3)?|pip|node(?:\.js|js)?|java|ruby|perl|\.net (?:runtime|sdk)|visual c\+\+ (?:runtime|redistributable))\b',
    r'\b(?:pip3?|python(?:3|\.exe)?\s+-m\s+pip)\s+install\b',
    r'\bnpm\s+(?:install|i)\b',
    r'\b(?:requires?|needs?)\s+(?:(?:an?|the|existing|installed)\s+){0,3}(?:python(?:\s*3)?|pip|node(?:\.js|js)?|java|ruby|perl)\b',
)

SUPPORT_EXECUTION_REQUEST_PATTERNS = (
    r'\b(?:open|run|execute|launch|start|double[ -]?click)\b.{0,65}\b(?:attachment|attached|executable|exe|program|utility|tool|helper|installer|file)\b',
    r'\b(?:double[ -]?click)\s+(?:it|this|that)\b',
)

SUPPORT_PRIVILEGED_ACTION_PATTERNS = (
    r'\b(?:enable|allow|activate)\s+(?:(?:the|all|active|editing|document)\s+){0,2}(?:macros?|content|editing)\b',
    r'\b(?:run|open|launch)\s+(?:(?:it|this|the (?:file|attachment|program))\s+)?as\s+(?:an?\s+)?administrator\b',
)

SUPPORT_CREDENTIAL_PATTERNS = (
    r'\b(?:confirm|verify|send|provide|enter|share|reply with|type)\s+(?:(?:your|the|current|account|login|work|corporate)\s+){0,3}(?:password|credentials|login details|verification code|one.time (?:password|code)|mfa code|2fa code|recovery code|seed phrase)\b',
)

SUPPORT_SENSITIVE_FILE_PATTERNS = (
    r'\b(?:send|upload|email|share|attach|paste|forward)\b.{0,70}\b(?:flag\.txt|(?:desktop[/\\])?flag file|(?:files?|contents?) (?:on|from) your desktop)\b',
)

SUPPORT_SECRECY_PATTERNS = (
    r'\b(?:do not|don.t|never)\s+(?:tell|inform|notify|contact)\b.{0,40}\b(?:it|security|support|anyone|manager)\b',
    r'\b(?:keep this (?:secret|confidential|between us)|do not forward|don.t forward)\b',
)

SUPPORT_FINANCIAL_PATTERNS = (
    r'\b(?:buy|purchase|send|provide)\b.{0,40}\bgift cards?\b',
    r'\b(?:wire|transfer|send)\b.{0,30}\b(?:money|payment|funds|bitcoin|cryptocurrency)\b',
)

SUPPORT_URGENCY_TERMS = (
    'urgent',
    'immediately',
    'asap',
    'act now',
    'final notice',
    'within 24 hours',
    'within one hour',
)

SUPPORT_THREAT_PATTERNS = (
    r'account.{0,50}(?:suspend|terminat|delet|clos)',
    r'(?:fail|failure|refus).{0,60}(?:lose|loss|suspend|terminat|penalty|legal action)',
    r'(?:you will|you.ll).{0,30}(?:lose|be fired|be reported|be punished)',
    r'(?:legal action|permanent suspension|last warning)',
)

SUPPORT_SHORT_LINK_HOSTS = {'bit.ly', 'tinyurl.com', 't.co', 'is.gd', 'shorturl.at', 'rb.gy'}

SUPPORT_DANGEROUS_URI_SCHEMES = {'ms-msdt', 'search-ms', 'search', 'shell'}

SUPPORT_EMAIL_PAYLOAD_PATTERN = r'(?:^|[^a-z0-9])(?:payload|meterpreter|msfvenom|mimikatz|sliver|cobalt[ _-]?strike|beacon|rev(?:erse)?[ _-]?shell|shellcode|ransomware|keylogger|exfil(?:trat(?:e|ion))?)(?:[^a-z0-9]|$)'

SUPPORT_PAYLOAD_NAME_PATTERN = r'(?:^|[^a-z0-9])(?:payload|meterpreter|msfvenom|mimikatz|sliver|cobalt[ _-]?strike|beacon|shell|rev(?:erse)?(?:[ _-]?(?:shell|tcp|https?))?|shellcode|ransomware|keylogger|malware|exfil)(?:[^a-z0-9]|$)'

SUPPORT_EXECUTABLE_EXTENSIONS = {
    'exe',
    'dll',
    'scr',
    'com',
    'cpl',
    'pif',
    'msi',
    'msp',
    'msix',
    'appx',
    'jar',
    'xll',
}

SUPPORT_SCRIPT_EXTENSIONS = {
    'ps1',
    'psm1',
    'psd1',
    'bat',
    'cmd',
    'vbs',
    'vbe',
    'js',
    'jse',
    'wsf',
    'wsh',
    'hta',
    'sct',
    'py',
    'pyw',
    'pyc',
    'pyo',
    'pyz',
    'pyzw',
    'ipynb',
    'sh',
    'bash',
    'pl',
    'rb',
    'rbw',
    'jar',
    'class',
    'reg',
}

SUPPORT_ENCODED_SCRIPT_EXTENSIONS = {'jse', 'vbe'}

SUPPORT_SHORTCUT_EXTENSIONS = {
    'lnk',
    'url',
    'scf',
    'library-ms',
    'search-ms',
    'website',
    'settingcontent-ms',
}

SUPPORT_DISK_IMAGE_EXTENSIONS = {'iso', 'img', 'vhd', 'vhdx', 'dmg'}

SUPPORT_MACRO_EXTENSIONS = {
    'doc',
    'dot',
    'xls',
    'xlt',
    'ppt',
    'pot',
    'pps',
    'docm',
    'dotm',
    'xlsm',
    'xlsb',
    'xltm',
    'xlam',
    'pptm',
    'ppam',
    'potm',
    'ppsm',
    'sldm',
    'vsdm',
}

SUPPORT_HTML_EXTENSIONS = {'htm', 'html', 'xhtml', 'shtml', 'mht', 'mhtml', 'svg'}

SUPPORT_BENIGN_DISGUISE_EXTENSIONS = {
    'pdf',
    'txt',
    'doc',
    'docx',
    'xls',
    'xlsx',
    'ppt',
    'pptx',
    'rtf',
    'jpg',
    'jpeg',
    'png',
    'gif',
    'csv',
}

SUPPORT_NON_WINDOWS_EXTENSIONS = {'sh', 'bash', 'elf', 'dmg', 'app', 'deb', 'rpm', 'apk'}

SUPPORT_EXPECTED_MIME = {
    'pdf': {'application/pdf'},
    'png': {'image/png'},
    'jpg': {'image/jpeg'},
    'jpeg': {'image/jpeg'},
    'gif': {'image/gif'},
    'txt': {'text/plain'},
    'html': {'text/html', 'application/xhtml+xml'},
    'htm': {'text/html', 'application/xhtml+xml'},
    'svg': {'image/svg+xml', 'text/xml', 'application/xml'},
    'docx': {
        'application/zip',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },
    'xlsx': {
        'application/zip',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
    'pptx': {
        'application/zip',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    },
    'zip': {'application/zip', 'application/x-zip', 'application/x-zip-compressed'},
}
