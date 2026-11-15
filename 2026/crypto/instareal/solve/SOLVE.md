# InstaReal solution

## Overview

The database is seeded with 2000 reals (counters 1–2000) using a single `random.Random()` instance. The flag real is embedded at a random counter between 500 and 1000, marked with `prevent_autodiscover=True` so it never appears in the public `/api/reals` feed.

## Attack

1. **Register as `admın`** — There exists a unicode collision that transforms `ı` to `I` when uppercased. The username `admın` allows the user logs collection to resolve to `"ADMIN-LOGS"` (the same collection used by the `AdminLog` model for audit entries). This grants access to the 500 seeded admin logs covering counters 1501–2000 via `/api/self/recent-reals`.

2. **Retrieve the first 500 records** — Call `GET /api/self/recent-reals` and extract the `real_salt` values from all returned entries (counters 1501–2000).

3. **Post 124 reals** — Submit 124 posts via `POST /post` with any category, title, and content. Each post advances the shared PRNG by one step, producing counters 2001–2124. After posting, call `/api/self/recent-reals` again and take the last 124 entries.

4. **Combine 624 samples** — Concatenate the initial 500 admin logs with the 124 user-generated logs to obtain 624 consecutive `real_salt` values. This is the minimum required by `randcrack` to recover the PRNG state.

5. **Recover PRNG state** — Feed all 624 salts into `randcrack.RandCrack`, submitting each via `cracker.submit(salt)`.

6. **Rewind the RNG** — The admin logs come from counters 1501–2000 (RNG indices ~1501–2000). To reach counter 500 (RNG index 499, which sits at position 0 in the RNG state that corresponds to index 1500), offset backward by 624 then by 1001.

7. **Predict and query** — For each counter_id in range(500, 1001):
    - Predict the salt: `salt = cracker.predict_getrandbits(32)`
    - Compute real_id: `sha256(f"{counter_id}:{salt}".encode()).hexdigest()`
    - Fetch content: `GET /api/real/{real_id}` — returns only `real.content`, used during brute force (the flag real has `prevent_autodiscover=True` so it never appears in `/api/reals`)

## Key endpoints

- Styled viewer: `/real/<id>` — renders the full page
- Flat API: `/api/real/<id>` — returns only `real.content`, used during brute force
