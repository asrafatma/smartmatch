# SmartMatch — AI-Powered Campus Lost & Found Platform

> **Reuniting Campus Belongings with Intelligent Precision & Verified Privacy**
> 
> *Core Principle: AI is an assistance tool, not an authority.*

---

## ⚖️ Judge Quick Start — Under 5 Minutes

SmartMatch is designed for rapid, friction-free evaluation. You do not need to register accounts or manually enter test data — the application comes pre-loaded with synthetic judge accounts and paired lost/found reports.

### Option 1: Live Local Server (Recommended)
1. **Clone & Install Dependencies:**
   ```bash
   git clone <repo-url>
   cd smartmatch
   pip install -r requirements.txt
   ```
2. **Start the Application:**
   ```bash
   python run.py
   ```
   *Note: If the database is fresh, the server automatically seeds the synthetic demo reports and judge accounts on launch.*
3. **Open Browser:**
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).

### Option 2: Pre-Seeded Judge Credentials
Use the 1-click quick-access buttons in the top banner or log in manually:

| Persona | Email | Password | Role | Primary Demo Task |
|---|---|---|---|---|
| **Alice (Student)** | `alice@campus.edu` | `student123` | Student | Lost a black leather wallet & hydro flask |
| **Bob (Finder)** | `bob@campus.edu` | `finder123` | Student / Finder | Found a black leather wallet & Honda keys |
| **Charlie (Admin)** | `admin@campus.edu` | `admin123` | Administrator | Moderates all campus reports & AI audit logs |

### 5-Minute Evaluation Walkthrough:
1. **Explore the Catalog:** Click **Browse Reports** to view active lost & found items with photo thumbnails, categories, and locations.
2. **Inspect Deterministic Matching:** 
   - Open the **Black Leather Bifold Wallet** report.
   - Inspect the **Potential Matches** panel on the right.
   - Observe the **Found Black Leather Wallet** ranked **#1 with a 97.0 / 100 ("Strong candidate")** score.
   - Examine the 8-category score breakdown (Category 20/20, Object Type 15/15, Brand 15/15, Color 15/15, Material/Shape 10/10, Distinctive Features 15/15, Location 4/5, Date 5/5) and the transparent matched pills (green) vs unknown pills (gray).
3. **Submit an Ownership Claim:**
   - As **Alice**, click **Claim Item** on the Honda Car Keys report.
   - Enter private verification details (e.g. *"Bronze gym tag under fob, initial 'A' engraved on brass key"*).
4. **Review Claim as Finder (Privacy Verification):**
   - Click the top-bar button for **Bob (Finder)** to switch accounts instantly.
   - Click **Claims Review** in the top navigation.
   - Inspect Alice's private verification evidence (masked from public view).
   - Click **✓ Approve Ownership**.
5. **Inspect Contact Information Release:**
   - Notice the report status transitions to **Resolved**.
   - Direct handover contact information between Alice and Bob is now unlocked, having been strictly shielded until claim approval!

---

## 1. Problem Statement
Students frequently misplace personal belongings across university lecture halls, libraries, sports facilities, and dining centers. Conventional lost-and-found notice boards suffer from severe drawbacks:
- Students describe the same item using different terms (e.g., *"navy cardholder"* vs *"dark blue leather wallet"*).
- Descriptions are often incomplete or lack standard categorization.
- Ownership verification is vulnerable to fraud or social engineering.
- Personal contact information (phone numbers, personal emails) is frequently exposed on public corkboards or social channels.

---

## 2. Solution Overview
SmartMatch combines **Google Gemini multimodal AI** for structured attribute extraction with a **pure Python deterministic 100-point ranking engine** and a **privacy-preserving ownership verification workflow**:
- **Multimodal AI Extraction:** Analyzes photograph and description simultaneously to extract colors, materials, shapes, brands, and distinctive features into structured JSON validated by Pydantic.
- **Human-in-the-Loop Confirmation:** Extracted attributes are editable suggestions. Students review and confirm attributes before saving.
- **Graceful Manual Fallback:** If Gemini is unreachable or no API key is set, rule-based heuristic extraction activates instantly without blocking report submission.
- **Deterministic 100-Point Matching:** Mathematical, predictable scoring algorithm that ranks candidate pairs with clear score breakdowns and 4-tier tie-breaking.
- **Zero Contact Leakage:** Contact information is protected by default. Submitter emails are masked as `[PROTECTED]` and only released to the finder and claimant after a claim is verified and approved.

---

## 3. Technology Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+), Responsive Grid/Flexbox design, Custom UI System (Plus Jakarta Sans).
- **Backend:** Python 3.11 / 3.14, Flask, Flask-CORS, Flask-JWT-Extended, bcrypt.
- **Database:** MongoDB / PyMongo with automated in-memory MongoMock fallback for seamless offline testing and local evaluation.
- **AI Engine:** Google Gemini API (`gemini-2.5-flash`) via the official `google-genai` Python SDK.
- **Validation:** Pydantic v2.
- **Image Processing:** Pillow (PIL).
- **Testing & CI:** pytest, Flask Test Client, GitHub Actions (`.github/workflows/ci.yml`), bash test runner (`scripts/test.sh`).

---

## 4. System Architecture

```
Browser Client (SPA / MPA)
   ↓  [REST API / JSON / Multipart Form-Data]
Flask Web Server (app/__init__.py)
   ├── Security Headers & CORS Guard
   ├── JWT Authentication (Bearer Tokens)
   ├── Route Controllers (Auth, Reports, Matches, Claims, Admin, Health)
   ├── Application Services (Auth, Report, MatchingEngine, Claim, Contact)
   ├── AI Integration (GeminiClient + Pydantic Schema + Normalizer + Fallback)
   └── Repositories (UserRepository, ReportRepository, MatchRepository, ClaimRepository)
         ↓
   MongoDB Atlas / In-Memory MongoMock + Local/Cloud Upload Storage
```

---

## 5. Deterministic Matching Engine

The core product principle dictates that **Gemini does not decide the final match ranking**. Matching is performed in pure Python using a 100-point scoring model:

| Attribute | Weight | Scoring Rules |
|---|---:|---|
| **Category Compatibility** | 20 | Identical: 20 pts. Generic 'other': 10 pts. Incompatible: 0 pts. |
| **Object Type** | 15 | Identical: 15 pts. Partial/substring: 10 pts. Generic item: 5.25 pts. Conflict: 0 pts. |
| **Brand / Logo** | 15 | Matching brand: 15 pts. Both unbranded/unknown: 7.5 pts. Distinct: 0 pts. |
| **Colour** | 15 | Shared normalized colors: 15 pts. Unknown: 7.5 pts. Conflicting: 0 pts. |
| **Material & Shape** | 10 | Shared material: 5 pts. Shared shape: 5 pts. Neutral: 2.5 pts each. |
| **Distinctive Features** | 15 | Shared keywords (stickers, engravings, scratches, keychains): 15 pts. Neutral: 5-7.5 pts. |
| **Location Proximity** | 5 | Same building: 5 pts. Adjacent/zone: 4 pts. Different campus zone: 2 pts. |
| **Date Proximity** | 5 | Same day: 5 pts. $\le 2$ days: 4.5 pts. $\le 7$ days: 3.5 pts. $\le 14$ days: 2 pts. |
| **Total** | **100** | Clamped to range `[0.0, 100.0]` |

### Deterministic Tie-Breakers:
1. `score` descending.
2. `incident_date` proximity ascending.
3. `created_at` ascending.
4. Stable report `id` ascending.

---

## 6. Security & Privacy Architecture

- **Password Hashing:** Passwords hashed with salted bcrypt (12 rounds).
- **JWT Verification:** Authenticated user identity is always obtained from verified JWT tokens, never trusted from frontend request bodies.
- **Mandatory Photo Validation:** Uploads are strictly validated for MIME type (`image/png`, `image/jpeg`, `image/webp`), size limits (10MB), and byte-level image integrity via Pillow `Image.verify()`.
- **Safe Filenames:** Uploaded files are renamed using UUID hexadecimal tokens (`uuid4().hex`) to prevent path traversal.
- **Privacy Shield:** Submitter emails are masked across all public endpoints (`[PROTECTED — AVAILABLE UPON APPROVED CLAIM]`).
- **Claim Lockout:** Attempt limits prevent brute-force ownership claiming (maximum 3 attempts per claimant before permanent lock).

---

## 7. Local Installation & Setup

### Prerequisites
- Python 3.10+
- pip

### 1. Clone Repository & Setup Environment
```bash
git clone <repository-url>
cd smartmatch
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment variables:
```ini
FLASK_ENV=development
SECRET_KEY=smartmatch-dev-secret-key-32-chars
JWT_SECRET_KEY=smartmatch-jwt-secret-key-32-chars
MONGODB_URI=
# Leave MONGODB_URI empty or 'mock' to use high-performance in-memory MongoMock
# For MongoDB Atlas: mongodb+srv://<user>:<password>@cluster0.mongodb.net/smartmatch

GEMINI_API_KEY=
# Leave empty to test graceful manual fallback, or insert Gemini API key from https://aistudio.google.com/
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Seed Database
```bash
python scripts/seed_database.py
```

### 4. Run Application
```bash
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 8. Automated Testing

SmartMatch includes a comprehensive automated test suite spanning unit, integration, and end-to-end user journeys.

```bash
# Run pytest with concise tracebacks
python -m pytest -v --tb=short

# Run via CI script
bash scripts/test.sh
```

**Test Summary:** 29 automated tests passed (100% pass rate).

---

## 9. Known Limitations & Future Improvements
- **Live Notifications:** Current version surfaces match updates on-demand in the UI; future enhancements will integrate WebSockets or transactional campus emails.
- **Campus Map Integration:** Interactive building floorplans and campus locker dropoff zones.
