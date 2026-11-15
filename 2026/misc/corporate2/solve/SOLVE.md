# corporate2

This is part 2 of corporate. It requires solving that challenge to complete this.

0. Description and Support Email

The challenge description says the flag is at `C:\Users\support\Desktop\flag.txt`.

The platform page on corporate has a support contact, that is an email composer with attachments and states "Use this form to ask for help with a CTF challenge.".

1. Payload/Email Scoring

Submitting sample data shows a modal stating if the email was delivered or rejected. It notes points for the email and attachments, with a rejection thresshold.

You can attempt to send common payloads, suspicious URLs or tell support to run a command to discover how you can earn points!

2. Execution

Delivered emails are sent to a queue, this is manually reviewed and payloads will be attempted on a sandbox, if it functions you will retrieve your flag!

3. Criteria

The scoring uses heuristics and YARA rules. The general concept is to block trivial or low effort attempts, such as instruction to run commands or unmodified sliver payloads. Some file extensions and other small things are blocked, but you can attach archive files or even directly EXEs and still win.

Almost anything original (e.g loader in go) will pass so long as the email is reasonable. Be creative!

--------

## Disclaimer: This is a slop recap of the scoring mechanism

Each signal counts once per submission, regardless of repeated words or multiple attachments. Signals in the same group contribute only the highest score in that group. All other signals add together.

| Score | Rejected at |
|---|---:|
| Email | **100 or more** |
| Attachments | **100 or more** |
| Combined email + attachments | **120 or more** |

Attachment scoring

File types can be detected from the filename or identified contents.

| Signal | What triggers it | Points | Group |
|---|---|---:|---|
| Executable | Recognized executable extension or executable contents | **60** | File format |
| Shortcut / URL file | Windows shortcut, URL or related launcher format | **60** | File format |
| Disk image | Recognized disk-image extension or contents | 60 | File format |
| Macro-capable document | A recognized macro-capable or legacy Office extension; macros need not actually exist | 80 | File format |
| HTML / SVG attachment | Recognized HTML/SVG extension or contents | 60 | File format |
| Archive | Recognized archive/container, including ZIP-based document/package containers | 40 | File format |
| Misleading double extension | A document/image extension followed by an executable, script or shortcut extension | **50** | File format |
| Blocked extension | A configured blocked script/interpreter extension | 100 | File format |
| Script / interpreter file | Recognized script, interpreter or bytecode extension/content | 100 | File format |
| Encoded script | `.jse` or `.vbe` | 100 | File format |
| Type mismatch | Identified contents conflict with an expected file type | 80 | File disguise |
| Filename direction control | Unicode characters that alter filename display direction | 100 | File disguise |
| Filename normalization trick | Invisible spacing, normalization changes or trailing-dot/space tricks | 60 | File disguise |
| Obvious payload name | Recognized payload/malware/framework wording in the filename | 50 | — |
| Non-Windows type | Recognized non-Windows extension or ELF/Mach-O executable contents | 100 | — |
| Empty attachment | Zero-byte file | 100 | — |
| YARA match | Any active signature matches the attachment or an extracted archive member | 100 | — |
| Scan error | File identification or security scanning fails or cannot complete | 100 | — |
| Size | File exceeds the configured attachment limit | 40* | — |

*Normal submissions exceeding 20 MiB per file or 20 MiB combined are refused during upload, before a scored delivery completes.

Informational signals — no points

| Signal | Points |
|---|---:|
| Ordinary links or IP-address links | 0 |
| Remote images/resources | 0 |
| Hidden HTML | 0 |
| Base64 or encoded/invisible text | 0 |
| Complex HTML, including SVG/MathML elements alone | 0 |
| Punycode/internationalized hostnames | 0 |
| Archive-password wording | 0 |
| Generic greetings or reply/forward subject prefixes | 0 |
| Capitals, punctuation, grammar or informal language | 0 |
| Security/tool names alone | 0 |
| Uploader-declared MIME mismatch | 0 |
| Unverified file type or missing filename extension | 0 |

How grouping affects the total

| Group | Calculation |
|---|---|
| Execution instructions | Highest of security bypass, command execution, dependency installation and privileged-action signals |
| Delivery pretext | Highest of direct execution request and thin pretext |
| Pressure | Highest of threats and urgency |
| HTML execution | Highest of active HTML and embedded download |
| URL deception | Highest of link-text mismatch and URL user-info |
| File format | Highest format score across the submission, including double-extension scoring |
| File disguise | Highest of direction controls, type mismatch and normalization tricks |

Archive members receive YARA scanning, rather than separate extension/type scores. Incomplete scans always reject.

Manual review still assesses the delivery, originality, Windows compatibility, execution with protection enabled, and successful flag retrieval.