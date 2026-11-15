# Corporate CTF submission signatures

`index.yar` is the active entry point. This is a deliberately selected ruleset
for a roughly 30-hour, mostly beginner CTF: recognize stock framework output and
basic wrapping without banning every custom executable or OS API. It is not a
general antivirus feed and does not guarantee a particular solve count.

## Included coverage

- Elastic Security: the existing Sliver and Cobalt Strike signatures, plus
  Windows/Linux/macOS Metasploit, Linux Meterpreter and patched Linux UPX.
- Neo23x0 signature-base: Metasploit payload templates and an older loader,
  specific Python reverse/PTY shells, pyminifier wrappers and a specific
  obfuscated JavaScript/PowerShell pattern. These script signatures are narrow,
  not general behavior detectors.
- Yara-Rules: only `generic_javascript_obfuscation` selected from
  `Javascript_exploit_and_obfuscation.yar`. The upstream broad Base64 detector
  and unrelated phishing-kit rule are intentionally omitted.
- Locally authored `Course_Policy.yar`: recognizable UPX packing on executable
  files; Python network/process/redirection combinations; Python decode/execute
  wrappers; Node network/process/shell combinations; Windows Script Host
  download/write/execute combinations; JavaScript decode/execute combinations.

The policy rules do not reject a lone `os`, `subprocess`, `fs`, `child_process`,
network call, file read, or Base64 use. They can still flag benign utilities
combining these capabilities. They scan text and bytes, not actual runtime
behavior. They do not parse source syntax or distinguish comments from code.
No generic entropy, compiler, unsigned-PE, Go/Rust, or PyInstaller ban is enabled.

## Provenance and licenses

New downloads were retrieved on 2026-11-01 at pinned upstream commits. Exact
URLs, commits, local SHA-256 hashes and the selected-rule exception are recorded
in `sources.json`. The three pre-existing Elastic rule files are retained
unchanged; their original revision is unknown and explicitly marked as such.
No malware samples are bundled.

- Elastic: `ELASTIC-LICENSE-2.0.txt` (includes hosted/managed service restrictions).
- Signature-base: `SIGNATURE-BASE-LICENSE.txt` (Detection Rule License 1.1).
- Yara-Rules selection: `YARA-RULES-GPL-2.0.txt`.
- Local policy: `COURSE-POLICY-LICENSE.txt` (MIT).

Retain upstream metadata and these license texts when distributing the rules.
DRL 1.1 also requires supplied author attribution in messages based on matches;
the mail scanner uses `yara -m` to include metadata in its recorded results.

## Difficulty and integration

The mail screener independently scores `.py`/`.js` and other interpreter files
as rejected by extension. These YARA rules do not change that policy; they also
inspect script content in renamed files. A no-match YARA result does not mean
the overall submission passes email, filename, file-type, or reviewer checks.

Independently written simple payloads are not deliberately blocked as a class.
Passing synthetic fixtures establishes that basic operations remain possible;
it does not establish an end-to-end solve. Before release, have a human tester
complete the intended solve under the no-AI constraint. Validate the exact
framework versions, architectures and output formats you want rejected: a
signature match fixture does not prove every stock msfvenom payload is covered.
Freeze the rules for the event instead of tracking upstream HEAD automatically.

YARA is enabled by default. Settings live in `src/support/config.py`; packaged rules
live at `/rules` in the scanner. Each YARA invocation has a five-second timeout. Archives
are decoded by the isolated networkless scanner within configured budgets; regular
members receive YARA only. Incomplete scans require manual review. Rebuild both
support and scanner after changing bundled rules; scanner startup validates
`index.yar`. File identification also runs in the isolated scanner.

## Validation

Run `PYTHONPATH=src python -m unittest discover -s tests -p test_yara_rules.py -v` from the challenge directory in an
environment with the YARA CLI. Checks cover bundle compilation, inert signature
and policy fixtures, match attribution, benign/simple-content negatives and a
5 MiB input within the scanner deadline. Fixtures are never executed.

Validated using YARA 4.5.7 in the existing Alpine-based challenge image. This is
a regression check of the curated gate, not a malware detection-rate benchmark.
