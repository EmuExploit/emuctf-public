"""Additional fictional project history and downloadable handovers.

Keep existing noise indices stable: additions are appended by noise.py.
"""


def p(author, message, reply=None, file=None):
    return {'author': author, 'message': message, 'reply': reply, 'reactions': (), 'file': file}


# A fixed mix: archive status is unrelated to whether a channel contains a clue.
ARCHIVED_CHANNELS = {
    'query-notes',
    'pottery',
    'canberra',
    'chall-reversing',
    'docs-builds',
    'meeting-about-meetings',
    'wireguard-rollout',
    'storage-move',
    'search-tuning',
    'terraform-plan',
    'test-notifications',
}

CHANNELS = {
    'wireguard-rollout': [
        p(
            'pl4nty',
            'branch office tunnel handover. keeping the WireGuard notes here, not in the login migration',
        ),
        p('h04x3d', 'which interface and UDP port did we settle on?'),
        p(
            'pl4nty',
            'wg-branch, UDP 51820. AllowedIPs is 10.44.0.0/16 only; no default route',
            reply=1,
        ),
        p('h04x3d', 'persistent keepalive?'),
        p(
            'pl4nty',
            '25 seconds on the branch peer behind NAT. zero on the office endpoint',
            reply=3,
        ),
        p(
            'expr',
            'attached the last handshake check. peer names are lab fixtures',
            file='wireguard-check.log',
        ),
        p('h04x3d', 'handshake works but DNS doesnt'),
        p(
            'pl4nty',
            'systemd-resolved split DNS for lab.emu.invalid. the tunnel does not magically configure DNS',
            reply=6,
        ),
        p('h04x3d', 'that explains the four hours'),
    ],
    'metrics-refresh': [
        p(
            'expr',
            'Prometheus scrape migration checklist. please reply here instead of changing targets during lunch',
        ),
        p('turbopenguin', 'what metric are we alerting on for the queue?'),
        p(
            'expr',
            'emu_jobs_oldest_age_seconds > 300 for 10m. queue depth alone pages us during every bulk import',
            reply=1,
        ),
        p('turbopenguin', 'and the scrape interval?'),
        p('expr', '30s, evaluation interval 30s. Alertmanager group_wait 45s', reply=3),
        p('hannnper', 'who receives the alert?'),
        p('expr', 'receiver office-ops. not the old all-staff email route', reply=5),
        p(
            'expr',
            'runbook attached with the example PromQL and silence labels',
            file='metrics-runbook.md',
        ),
        p('div', 'can it alert when an invoice is unpaid'),
        p('expr', 'it can, but im going to say no', reply=8),
    ],
    'build-cache': [
        p(
            'sealldev',
            'Bazel remote cache is up. this is build output caching, not the npm registry',
        ),
        p('pl4nty', 'what prefix invalidates the old entries?'),
        p(
            'sealldev',
            'instance_name emu-linux-v3. we bumped it after the toolchain update',
            reply=1,
        ),
        p('pl4nty', 'read only for laptops?'),
        p('sealldev', 'yes. CI writes, laptops read. compression zstd, max blob 64 MiB', reply=3),
        p('bradan', 'can i delete node_modules now'),
        p('sealldev', 'different cache brad', reply=5),
        p(
            'sealldev',
            'cache hit sample attached. no credentials in this one for once',
            file='bazel-cache.log',
        ),
    ],
    'storage-move': [
        p('ssparrow', 'MinIO bucket migration wrap-up. archive after the checksums are signed off'),
        p('ghostccamm', 'which bucket is the destination?'),
        p('ssparrow', 'emu-handouts-v2. region ap-southeast-2, path-style requests', reply=1),
        p('ghostccamm', 'object lock enabled?'),
        p('ssparrow', 'no, versioning yes. expire noncurrent versions after 14 days', reply=3),
        p('teddy', 'the dry run says 0 copied'),
        p('ssparrow', 'correct, that is why it is a dry run', reply=5),
        p(
            'ssparrow',
            'handover attached, includes rollback conditions',
            file='storage-handover.md',
        ),
        p('ghostccamm', 'checksum sample matches. marking migration finished'),
    ],
    'postgres-upgrade': [
        p('nullablevoidptr', 'PostgreSQL 16 rehearsal notes. no production changes today'),
        p('expr', 'logical slot name?'),
        p(
            'nullablevoidptr',
            'emu_upgrade_slot. publication emu_publication. do not drop it while the subscriber catches up',
            reply=1,
        ),
        p('expr', 'how much lag is acceptable before cutover?'),
        p(
            'nullablevoidptr',
            'under 1 MiB for 5 minutes, then stop writers and wait for zero',
            reply=3,
        ),
        p('bradan', 'is vacuum full just vacuum but better'),
        p(
            'nullablevoidptr',
            'it rewrites the table and takes an exclusive lock. please stop running it to make the dashboard green',
            reply=5,
        ),
        p(
            'nullablevoidptr',
            'rehearsal log attached; the repeated retry was a missing replication privilege',
            file='pg-rehearsal.log',
        ),
        p('div', 'sounds like we need a database alignment workshop'),
    ],
    'queue-workers': [
        p('turbopenguin', 'RabbitMQ consumer notes for the image pipeline'),
        p('teddy', 'what is the dead letter exchange called?'),
        p(
            'turbopenguin',
            'emu.images.dlx, routing key failed.thumbnail. quorum queue for the primary work queue',
            reply=1,
        ),
        p('teddy', 'prefetch value?'),
        p(
            'turbopenguin',
            '16. acknowledge after writing the thumbnail, not when receiving the message',
            reply=3,
        ),
        p('sealldev', 'what happens after the third retry?'),
        p(
            'turbopenguin',
            'dead letter it. no infinite requeue loop. the last one heated the meeting room',
            reply=5,
        ),
        p('teddy', 'finally infrastructure with a winter mode'),
    ],
    'search-tuning': [
        p(
            'ghostccamm',
            'OpenSearch relevance pass is finished. saving the settings before i forget',
        ),
        p('q3st1on', 'which analyzer for the title field?'),
        p('ghostccamm', 'english, with a keyword subfield title.raw for sorting', reply=1),
        p('q3st1on', 'and refresh interval?'),
        p('ghostccamm', '30s. one primary shard, one replica for the docs index', reply=3),
        p('bradan', 'searching for my password returns no results'),
        p('ghostccamm', 'thats probably the best test result we have had', reply=5),
        p(
            'ghostccamm',
            'attached the evaluation, query 7 still ranks the lunch menu too highly',
            file='search-evaluation.md',
        ),
    ],
    'device-enrolment': [
        p('hannnper', 'FleetDM laptop onboarding checklist v4'),
        p('bradan', 'what label does a finished laptop get?'),
        p(
            'hannnper',
            'office-managed. disk encryption policy is FileVault enabled, not just supported',
            reply=1,
        ),
        p('bradan', 'which osquery table checks battery cycles?'),
        p(
            'hannnper',
            'battery. cycle_count. this is not a reason to discharge every laptop to zero',
            reply=3,
        ),
        p(
            'pl4nty',
            'the enrolment secret is a bootstrap credential, please dont put it on the asset sticker',
        ),
        p('bradan', 'i used the sticker for the serial number'),
        p('hannnper', 'good. suspiciously good actually', reply=6),
    ],
    'certificate-renewal': [
        p('pl4nty', 'ACME renewal drill notes for the lab wildcard'),
        p('expr', 'HTTP-01 or DNS-01?'),
        p(
            'pl4nty',
            'DNS-01 through the RFC2136 provider. zone lab.emu.invalid, TSIG key acme-updater',
            reply=1,
        ),
        p('expr', 'propagation timeout?'),
        p('pl4nty', '120 seconds. recursive lookup must see the TXT before finalizing', reply=3),
        p('teddy', 'i put the TXT value in a text file'),
        p('pl4nty', 'different TXT', reply=5),
        p(
            'pl4nty',
            'fake rehearsal transcript attached so nobody confuses it with a live renewal',
            file='acme-rehearsal.log',
        ),
    ],
    'vault-lab': [
        p('h04x3d', 'Vault lab is ready. secrets engine kv-v2 mounted at workshop/'),
        p('q3st1on', 'what is the response wrapping TTL?'),
        p('h04x3d', '90 seconds. a wrapping token is single-use, not the secret itself', reply=1),
        p('q3st1on', 'which policy should the demo container have?'),
        p(
            'h04x3d',
            'thumbnail-reader. read only workshop/data/thumbnail, no list on the parent',
            reply=3,
        ),
        p('bradan', 'if i wrap it twice is it two factor'),
        p('h04x3d', 'thats a sandwich', reply=5),
        p(
            'h04x3d',
            'policy worksheet attached. sample tokens are placeholders',
            file='vault-workshop.md',
        ),
        p('div', 'please wrap my invoice in a purchase order'),
    ],
    'terraform-plan': [
        p('pl4nty', 'Terraform state move completed. old local state is read-only evidence now'),
        p('expr', 'backend key?'),
        p('pl4nty', 'office/network.tfstate in emu-tfstate-lab. workspace office-prod', reply=1),
        p('expr', 'provider version pinned?'),
        p(
            'pl4nty',
            'hashicorp/aws 5.82.0. dont run init -upgrade as a troubleshooting step',
            reply=3,
        ),
        p('bradan', 'plan says 0 to add so why does apply exist'),
        p('pl4nty', 'for days when the plan says something else', reply=5),
        p('pl4nty', 'saved the reviewed plan summary', file='network-plan.txt'),
    ],
    'mail-routing': [
        p('hannnper', 'Postfix relay changes for office notifications'),
        p('expr', 'submission port and auth mode?'),
        p(
            'hannnper',
            '587 with STARTTLS, SASL via Dovecot. port 25 is not our app submission interface',
            reply=1,
        ),
        p('expr', 'DKIM selector?'),
        p('hannnper', 'office2026. DMARC policy quarantine while we collect reports', reply=3),
        p('bradan', 'sent a test email to myself. havent answered yet'),
        p('hannnper', 'escalate to yourself after two business days', reply=5),
        p(
            'hannnper',
            'delivery sample attached, recipient addresses are invented',
            file='mail-delivery.log',
        ),
    ],
    'artifact-signing': [
        p(
            'sealldev',
            'Cosign rollout for container releases. this is unrelated to employee sign-in',
        ),
        p('teddy', 'keyless or key pair?'),
        p('sealldev', 'keyless in CI. Fulcio certificate plus Rekor transparency entry', reply=1),
        p('teddy', 'what predicate for provenance?'),
        p(
            'sealldev',
            'SLSA provenance v1. verify the workflow identity, not just that any signature exists',
            reply=3,
        ),
        p('bradan', 'can we sign it with my email signature'),
        p('sealldev', 'only if your email signature implements an OIDC issuer', reply=5),
        p('sealldev', 'release checklist attached', file='signing-checklist.md'),
    ],
    'redis-sessions': [
        p('expr', 'Redis session store trial. not changing the identity provider'),
        p('nullablevoidptr', 'eviction policy?'),
        p('expr', 'noeviction. session TTL 1800 seconds, prefix portal:sess:', reply=1),
        p('nullablevoidptr', 'AOF fsync mode?'),
        p(
            'expr',
            'everysec. no passwords in redis.conf; injected from the service secret',
            reply=3,
        ),
        p('bradan', 'the session expired while i was reading the instructions'),
        p('expr', 'you opened them yesterday', reply=5),
        p('expr', 'latency baseline p99 2.4ms. if it gets slower check disk before increasing TTL'),
    ],
    'incident-tabletop': [
        p('q3st1on', 'tabletop exercise only: the pretend CDN is returning stale content'),
        p('ghostccamm', 'what cache header are we checking?'),
        p(
            'q3st1on',
            'Age and X-Cache first. surrogate key release-2026-07 invalidates the release assets',
            reply=1,
        ),
        p('ghostccamm', 'who declares rollback?'),
        p(
            'q3st1on',
            'incident commander. severity SEV2 for the exercise, comms every 15 minutes',
            reply=3,
        ),
        p('div', 'i declare a lunch break'),
        p('q3st1on', 'not in the runbook', reply=5),
        p('q3st1on', 'minutes attached; no actual incident or outage', file='tabletop-minutes.md'),
        p('ghostccamm', 'action item: stop calling every cache a database'),
    ],
    'test-notifications': [
        p('sealldev', 'test'),
        p('sealldev', 'test 2'),
        p('teddy', 'received both. unfortunately'),
        p('sealldev', 'test 3 sorry'),
    ],
    'test-webhook-v2': [
        p('expr', 'payload arrived?'),
        p('bradan', 'what payload'),
        p('expr', 'never mind wrong channel'),
    ],
    'new-channel-please-ignore': [
        p('div', 'reserved for a future strategic initiative'),
        p('toasterpwn', 'you clicked create by accident'),
        p('div', 'discovery phase complete'),
    ],
}

ADDITIONS = {
    'docs-onboarding': [
        p(
            'hannnper',
            'July onboarding addendum: the access project decision and current sign-in handover are in ~identity-setup. use the dated cutover decision rather than the original evaluation',
        ),
    ],
    'platform-dev': [
        p(
            'sealldev',
            'latest link preview feature handover moved to ~claude-pilot with the assisted-dev pilot notes. release status is in the replies to my unreleased checklist item',
        ),
    ],
    'docs-internal': [
        p(
            'expr',
            'updated the office service map. project channels hold their own handovers now',
            file='office-services.md',
        ),
    ],
    'chall-web': [
        p('panc4kes', 'finished hello-admin. source handout attached', file='hello-admin.py'),
        p('sealldev', 'the entire challenge is print("EMU{fake flag}")', reply=None),
        p('panc4kes', 'zero dependencies, extremely reliable solve rate'),
        p('sealldev', 'marking completed, please never release this'),
    ],
    'chall-crypto': [
        p(
            'teddy',
            'completed perfect-secrecy. generate a fresh 256-bit key, XOR the flag, delete the key, publish only ciphertext',
        ),
        p('q3st1on', 'any known plaintext or reused key?'),
        p('teddy', 'no. no oracle either'),
        p(
            'q3st1on',
            'so every possible flag has an equally valid key. mathematically unsolvable. completed is doing a lot of work here',
        ),
        p('teddy', 'the encryption part is completed'),
    ],
    'chall-reversing': [
        p(
            'nullablevoidptr',
            'completed reverse-psychology, handout attached',
            file='reverse-psychology.c',
        ),
        p('ghostccamm', 'it prints EMU{fake flag} before checking any input'),
        p('nullablevoidptr', 'yes but compiled with -O2 so it counts as reversing'),
    ],
    'chall-pwn': [
        p(
            'toasterpwn',
            'completed impossible-door. win requires x == 7 && x == 9 at the same time. x is a local constant and there is no input, file access or network',
        ),
        p('nullablevoidptr', 'what is the vulnerability'),
        p('toasterpwn', 'optimism'),
        p('nullablevoidptr', 'closed as impossible to solve. congrats on completing it'),
    ],
}

# Downloadable files are deliberately concrete background, never additional gates.
FILES = {
    'wireguard-check.log': '2026-07-03T09:12:01+08:00 wg-branch peer=branch-lab latest_handshake=18s\n2026-07-03T09:12:02+08:00 rx=16384 tx=24576 allowed=10.44.0.0/16\n2026-07-03T09:12:03+08:00 dns lab.emu.invalid SERVFAIL (split DNS missing)\n',
    'metrics-runbook.md': '# Queue alert runbook\n\nPrometheus: scrape_interval 30s; evaluation_interval 30s.\nAlert: emu_jobs_oldest_age_seconds > 300 for 10m.\nReceiver: office-ops. Group wait: 45s.\nCheck worker health before scaling. Silence by service=thumbnail, never by all environments.\n',
    'bazel-cache.log': '09:40:11 instance=emu-linux-v3 compressor=zstd action=compile hit=true\n09:40:12 client=laptop permission=read-only upload=denied\n09:40:13 client=ci blob_bytes=1048576 upload=ok\n09:40:14 build completed cache_hits=184 cache_misses=7\n',
    'storage-handover.md': '# Object storage move\n\nDestination: emu-handouts-v2. Region: ap-southeast-2. Path style.\nVersioning enabled, noncurrent expiry 14 days, object lock disabled.\nRollback if checksum mismatch is nonzero. Keep old bucket read-only for seven days.\nOwner: ssparrow. Dry run is not a transfer.\n',
    'pg-rehearsal.log': '10:02:01 postgres16 subscription=emu_upgrade slot=emu_upgrade_slot\n10:02:02 ERROR permission denied to start WAL sender\n10:06:12 role=replicator replication=true retry=ok\n10:07:10 replay_lag_bytes=524288\n10:12:10 writers=stopped replay_lag_bytes=0 cutover=ready\n',
    'search-evaluation.md': '# Docs search evaluation\n\nIndex: office-docs. Analyzer: english. Sort: title.raw.\nOne primary, one replica, refresh 30s.\nQuery 7: "release procedure" returned the lunch menu at rank 2.\nAction: reduce title boost; do not add an exclusion for sandwiches.\n',
    'acme-rehearsal.log': 'REHEARSAL ONLY: invented zone, no real certificate\n11:30:01 challenge=dns-01 zone=lab.emu.invalid key=acme-updater\n11:30:02 provider=rfc2136 TXT=create\n11:30:32 recursive_lookup=NXDOMAIN waiting=true\n11:31:02 recursive_lookup=match finalize=ok\n',
    'vault-workshop.md': '# Vault policy worksheet\n\nMount: workshop/ (kv-v2). Policy: thumbnail-reader.\npath "workshop/data/thumbnail" { capabilities = ["read"] }\nNo list permission on the parent. Response wrapping TTL: 90s, single use.\nExample token: hvs.WORKSHOP_PLACEHOLDER_NOT_A_TOKEN\nExercise: explain why a consumed wrapping token cannot be unwrapped again.\n',
    'network-plan.txt': 'Terraform reviewed plan\nworkspace: office-prod\nbackend: emu-tfstate-lab/office/network.tfstate\nprovider: hashicorp/aws 5.82.0\nPlan: 0 to add, 0 to change, 0 to destroy.\nReviewer: expr\n',
    'mail-delivery.log': '12:04:01 postfix/submission connect client=lab-app\n12:04:01 TLS established port=587 sasl=dovecot\n12:04:02 queue=EMU0042 to=<test@lab.emu.invalid> status=sent\n12:04:02 opendkim selector=office2026 result=pass\n',
    'signing-checklist.md': '# Container release signing\n\nUse Cosign keyless signing from CI. Fulcio issues the short-lived certificate.\nRekor holds the transparency entry. Attach SLSA provenance v1.\nVerify workflow identity and issuer as well as the digest.\nDo not accept arbitrary signed images just because the signature is valid.\n',
    'tabletop-minutes.md': '# CDN exercise minutes\n\nExercise only. Severity SEV2. Update interval 15 minutes.\nInspect Age and X-Cache. Invalidate surrogate key release-2026-07.\nIncident commander owns rollback.\nAction: document the cache key, assign a backup comms owner, decline lunch-based severity changes.\n',
    'office-services.md': '# Office service map\n\nAccess project: identity-setup (dated decisions).\nDevice management: FleetDM / device-enrolment.\nBranch network: WireGuard / wireguard-rollout.\nMetrics: Prometheus / metrics-refresh.\nSecrets workshop: Vault / vault-lab.\nBuild caching: Bazel / build-cache.\nThese projects have separate owners and runbooks.\n',
    'hello-admin.py': 'print("EMU{fake flag}")\n',
    'reverse-psychology.c': '#include <stdio.h>\nint main(void) { puts("EMU{fake flag}"); return 0; }\n',
}
