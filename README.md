# SmartMatch — AI-Powered Campus Lost & Found Platform

> Students report lost and found items with a photo. Gemini suggests structured attributes, the student
> confirms them, a **deterministic** engine ranks likely matches with explanations, and a
> **server-verified, finder-approved** claim process protects ownership and contact privacy.
>
> *Core principle: AI is an assistance tool, not an authority.*

| | |
|---|---|
| **Live URL** | `<LIVE_URL — add after deployment, see "Deployment">` |
| **Health check** | `<LIVE_URL>/api/health` |
| **CI** | GitHub Actions: `.github/workflows/ci.yml` runs `bash scripts/test.sh` |

---

## ⚖️ Judge Quick Start — Under 5 Minutes

No registration or data entry needed: the app seeds synthetic demo accounts and reports on first start.
All seeded reports carry a **DEMO DATA** badge.

### Demo accounts (synthetic, demo-only)

| Persona | Email | Password | Use it to… |
|---|---|---|---|
| Alice (student who lost items) | `alice@campus.edu` | `student123` | See matches for her lost wallet, submit claims |
| Bob (finder) | `bob@campus.edu` | `finder123` | Review and approve claims on items he found |
| Campus Admin | `admin@campus.edu` | `admin123` | Admin dashboard, AI logs, report oversight |

The yellow banner at the top of the page has one-click login buttons for each account.

### 5-minute walkthrough

1. **Open the live URL** and click **Alice** in the top banner.
2. **Deterministic matching:** open **Browse Reports → Black Leather Bifold Wallet**. The *Potential Matches*
   panel (visible only to the report's owner) ranks **Found Black Leather Wallet** first
   (~97/100, *Strong candidate*) with an 8-signal score breakdown, matched attributes, conflicts and unknowns.
   The score is a *ranking score*, not a probability.
3. **Server-verified claim:** click **Claim Item** on the found wallet.
   - Type a wrong answer (e.g. *"it is a plain black wallet"*). The server rejects it with a generic
     message and shows the remaining attempts (max 3, then locked with HTTP 429).
   - Type the right answer: *"there is a metro pass behind my student card"*. The claim becomes **verified**
     (the finder's private clue is checked on the server and is never sent to the browser).
4. **Finder decision:** click **Bob** in the banner → **Claims Review**. Only verified claims appear.
   Approve Alice's claim. The item becomes **Resolved** and disappears from search and matching.
5. **Contact privacy:** as Alice, open **My Items → My Claims → View Handover Contact**. The contact is
   released only to the finder and the approved claimant. Any other account (including admin) gets 403.
6. *(Optional)* **Report + AI review:** as any user, click **Found an Item**, add a photo and description, click
   **Analyze with AI**, edit the suggested attributes, set a private clue, and submit. If Gemini is
   unavailable, the form says so and the report still saves with manually confirmed attributes.

Other private clues in the seed data: water bottle = *"mountain sticker on the lid"*; car keys =
*"bronze gym tag and key engraved with letter A"* (Alice already has a verified, pending claim on the keys
for Bob to review).

---

## 1. Problem

Campus lost-and-found relies on notice boards and chat groups. Students describe the same object in different
words ("wallet" vs "card holder", "navy" vs "dark blue"), photos carry details that text omits, manual searching is
slow, public listings make dishonest claims easy, and personal contact details should not be exposed.

## 2. Solution and key features

- **Lost/found reports** with a **mandatory photo** (JPEG/PNG/WebP, max 5 MB, real format verified).
- **Gemini multimodal extraction** → structured attributes, kept separate as *user-stated*, *visually observed* and
  *unknown*. The reporter **reviews and edits** the suggestions before saving.
- **Manual fallback:** if Gemini is down, rate-limited, slow (bounded timeout) or returns invalid JSON, the report is
  still saved with manually confirmed attributes; `ai_status` records `completed`, `failed` or `manual`.
- **Deterministic matching** (pure Python, fixed weights, fixed synonym and compatibility dictionaries,
  deterministic tie-breaks, versioned config) with human-readable explanations.
- **Claims with server-side verification:** the finder sets a private clue; claimant answers are compared on the
  server; at most 3 attempts (atomic counter), then locked (429). One claim per user per item (unique index).
- **Finder approval** of verified claims; approving one claim rejects competing claims.
- **Contact privacy:** contact details only via `/api/reports/<id>/contact`, for the finder and the approved claimant only.
- **Lifecycle:** `active → claim_pending → resolved / closed`; resolved, closed and inactive items are excluded from
  search and matching.

## 3. Technology stack

| Layer | Choice |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript (Fetch API), served by Flask |
| Backend | Python 3.12, Flask 3.1 REST API (modular monolith), gunicorn in production |
| Database | MongoDB Atlas (PyMongo); images mirrored to **GridFS** for persistence on ephemeral hosts |
| AI | Gemini (`gemini-2.5-flash`) via the official `google-genai` SDK; Pydantic output validation |
| Auth | Flask-JWT-Extended (JWT), bcrypt password hashing |
| Tests/CI | pytest (unit, integration, e2e; Gemini mocked), GitHub Actions |
| Hosting | Render (free web service) + MongoDB Atlas (free M0) |

## 4. Architecture

```
Browser (HTML/CSS/JS)
   │  JSON / multipart over HTTPS
   ▼
Flask app (app/__init__.py) ── routes/      HTTP, JWT auth, rate limits
                               services/    business rules (reports, matching, claims, contact)
                               ai/          Gemini client, prompts, Pydantic schemas, normalizer
                               repositories/ MongoDB access + indexes
                               utils/       validation, image checks, storage, rate limiting
   │
   ├── MongoDB Atlas: users, reports, matches, claims, ai_logs, verification_clues, images (GridFS)
   └── Gemini API (server-side only; the browser never sees the key)
```

Report flow: `POST /api/reports/analyze` (suggestions only, nothing saved) → user edits → `POST /api/reports`
(saves the confirmed attributes; links the analysis log) → `GET /api/matches/<id>` (deterministic ranking).

Full details: [docs/design.md](docs/design.md).

## 5. Deterministic matching

| Signal | Weight | Rule |
|---|---:|---|
| Category | 20 | equal = full; "other" = half; different = 0 (conflict) |
| Object type | 15 | equal = full; configured-compatible (e.g. wallet ~ card holder) = 80%; shared word = 70% |
| Brand / logo | 15 | overlap = full; unknown on either side = neutral (50%) |
| Colour | 15 | overlap = full; same colour family (navy ~ blue) = 70%; different = 0 |
| Material + shape | 10 | 5 + 5; unknown = neutral |
| Distinctive features | 15 | whole-word keyword overlap (sticker, engraved, keychain…) |
| Location | 5 | same > related (substring) > different |
| Date | 5 | same day 5; ≤2 days 4.5; ≤7 days 3.5; ≤14 days 2; >14 days 0 |

Labels: ≥70 *Strong candidate*, ≥40 *Possible match*, otherwise *Low similarity*.
Tie-breaks: score ↓, date proximity ↑, created_at ↑, report id ↑. Every match stores `algorithm_version`
and `config_version` (`app/config.py`). Only lost↔found pairs of open reports from **different users** are
compared; a report is never compared with itself.

## 6. Security and privacy

- Identity and role always come from the verified JWT. Public registration creates **students only**; admin accounts
  require the server-side `ADMIN_INVITE_CODE` (or the seed).
- bcrypt password hashes; unique email index; login/register/claim/analyze endpoints are rate-limited (429).
- Matches are visible only to the report owner (or an admin). Private clues live in a separate collection and are
  never returned by any endpoint. Verification answers are visible only to the claimant, the finder and admins.
- Uploads: extension *and* decoded image format checked (415), size cap (413), random server-side filenames,
  decompression-bomb guard, files served only by a strict filename pattern.
- JSON error responses without stack traces; security headers (nosniff, frame deny, HSTS on HTTPS).
- CORS disabled by default (the frontend is same-origin). Production refuses to start with default secrets and
  never silently falls back to an in-memory database.
- `.env` is git-ignored; CI uses dummy secrets and mocks Gemini.

## 7. Local setup

Prerequisites: Python 3.12+ (3.14 tested locally), Git.

```bash
git clone <YOUR_REPO_URL>
cd smartmatch
python -m venv venv
# Windows: venv\Scripts\activate      Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Edit `.env`:

| Variable | Value |
|---|---|
| `MONGODB_URI` | Atlas connection string (leave empty for an in-memory demo database) |
| `GEMINI_API_KEY` | key from https://aistudio.google.com/apikey (leave empty to test the manual fallback) |
| `SECRET_KEY`, `JWT_SECRET_KEY` | long random strings: `python -c "import secrets;print(secrets.token_hex(32))"` |

Run:

```bash
python run.py            # http://127.0.0.1:5000 (auto-seeds demo data if the database is empty)
```

Re-seed manually (wipes all collections, so it asks for `--force` on a real database):

```bash
python scripts/seed_database.py            # in-memory database
python scripts/seed_database.py --force    # real MongoDB: DELETES and re-creates demo data
```

## 8. Tests

```bash
bash scripts/test.sh                 # what CI runs; exit code 0 only if all tests pass
python -m pytest tests/ -v           # same tests directly
python -m pytest tests/integration/test_spec_acceptance.py -v   # organizer acceptance tests
```

Gemini is mocked in tests; no network or API key is needed. See [docs/testing.md](docs/testing.md).

## 9. Deployment (Render + MongoDB Atlas)

`render.yaml` defines the web service (gunicorn, health check `/api/health`, generated secrets). Steps:

1. Push this repository to GitHub.
2. In Render: **New → Blueprint** → pick the repository → enter `MONGODB_URI` and `GEMINI_API_KEY` when prompted.
3. In Atlas **Network Access**, allow `0.0.0.0/0` (Render's outgoing IPs are not fixed on the free plan).
4. Open `https://<service>.onrender.com/api/health`. Expect `"database": {"status": "healthy", ...}`.

Uploaded images are written to local disk *and* GridFS, so they survive Render restarts and redeploys.
Free Render services sleep after ~15 minutes idle; the first request then takes ~30–60 s.

## 10. AI integration

- `app/ai/gemini_client.py`: Gemini call with `system_instruction`, JSON response mode, temperature 0.1,
  request timeout (`GEMINI_TIMEOUT_SECONDS`), one bounded retry, MIME type detected from image bytes.
- `app/ai/schemas.py`: Pydantic `ItemExtractionResult` validates every response before use.
- `app/ai/prompts.py`: forbids inventing hidden contents, serial numbers, unreadable brands or owner identity.
- `app/ai/report_analyzer.py`: keyword-based fallback when AI is unavailable; every call is logged in `ai_logs`
  (model, prompt/extraction version, status, error type; no personal data).
- `app/ai/normalizer.py`: fixed synonym dictionary (navy → dark_blue, billfold → wallet, …).
- Gemini never ranks matches, verifies claims or approves ownership.

## 11. Known limitations

- The verification check is keyword overlap (≥60% of the clue's significant words). It is deterministic and explainable,
  but not semantic; the finder still makes the final decision.
- The rate limiter is in-memory (one process). A multi-instance deployment needs a shared store (e.g. Redis).
- JWT logout is client-side (the token is discarded); tokens expire after 24 h. No server-side revocation list.
- Free-tier hosting sleeps when idle; Atlas M0 has 512 MB storage.

## 12. Future improvements

Notifications (email/push) for new strong matches, server-side token revocation, a Redis-backed rate limiter,
moderator tooling for flagged reports, multilingual input.

---

Documentation: [requirements](docs/requirements.md) · [design](docs/design.md) · [testing](docs/testing.md) ·
[AI usage log](docs/ai-usage-log.md) · [submission](SUBMISSION.md)
