# Live demo script (5 minutes)

## 0. Start everything
```bash
cd SIH26188
cp .env.example .env
docker compose up --build      # first build ~5-10 min
```
Wait for `backend` to log `Started ScreeningApplication`.
Open http://localhost:8081 → login `officer1` / `password`.

## 1. Make demo images
```bash
pip install pillow
python scripts/make_demo_image.py genuine.jpg
python scripts/make_demo_image.py tampered.jpg --tampered
python scripts/make_demo_image.py flagged.jpg --blacklist
```

## 2. Genuine document
- New Verification → PASSPORT → `genuine.jpg` → Run screening.
- Expect: MRZ check digits valid, low tamper, `validationStatus` may be FAIL only because
  the ICAO sample passport is expired (2012) — point that out as the expiry rule working.
- Show the **Reasons** panel: every signal is listed, not just a number.

## 3. Tampered passport number  (fraud case #5)
- Verify `tampered.jpg`.
- Expect: "MRZ passport-number check digit FAILED", EXIF "processed by editing software",
  higher risk, `finalResult = REJECT`.

## 4. Blacklisted document  (fraud case #11)
- Verify `flagged.jpg`.
- Expect: `blacklistStatus = HIT`, reason from the seeded watchlist, `finalResult = REJECT`.

## 5. Blockchain integrity  (Spec Part 5, step 14)
- Open the genuine verification, click **Run integrity check** → `INTACT`.
- In a shell:
  ```bash
  docker compose exec postgres psql -U screening -d screening \
    -c "UPDATE verification_results SET final_result='CLEAR', risk_level='LOW' WHERE id=1;"
  ```
- Click **Run integrity check** again → `TAMPERED`. The DB was edited directly; the
  ledger hash no longer matches the re-hash.

## 6. Face / multi-identity  (stretch, cases #7 #9 #15)
- Verify two different documents with the **same** live face photo.
- The second one flags "Multiple-identity: face matches stored embedding for document …".

## Talking point
No single module catches every fraud type. Case #15 — a genuine, unaltered,
non-blacklisted document held by the wrong person — is caught only by face
verification. That is why all four modules exist.
