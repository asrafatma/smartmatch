# SmartMatch — Requirements Specification

## 1. Product Overview
SmartMatch is a web-based, AI-assisted, privacy-preserving campus lost-and-found management platform. It enables students to report lost and found items with mandatory photographic evidence, leverages Google Gemini multimodal AI to extract structured item attributes, employs a transparent 100-point deterministic ranking engine to match lost and found items, and protects personal contact details through a secure ownership verification workflow.

---

## 2. User Personas

### Persona A: Student Who Lost an Item (Claimant)
- **Profile:** An undergraduate or graduate student who misplaced a valuable item (wallet, laptop, keys, water bottle) between classes or study sessions.
- **Pain Points:** Unsure if anyone picked it up; finds manual notice boards ineffective; reluctant to publicly post private phone numbers or descriptions of confidential contents.
- **Goals:** Quickly submit a lost report with a photo, discover high-confidence candidate matches, verify ownership securely without exposing personal contact details to strangers.

### Persona B: Student / Staff Member Who Found an Item (Finder)
- **Profile:** A student, lecturer, or facilities worker who discovers an unattended item on campus.
- **Pain Points:** Wants to help return the item to its rightful owner but does not want to be harassed or have their personal contact info made public.
- **Goals:** Log the found item with photo and location, inspect incoming ownership claims, review private verification proof, and coordinate a safe handover once verified.

### Persona C: Campus Lost & Found Administrator
- **Profile:** Campus Security or Student Affairs personnel overseeing physical property storage and lost-and-found moderation.
- **Pain Points:** Overwhelmed by vague verbal descriptions and fraudulent claims.
- **Goals:** Oversee all campus reports, inspect AI extraction audit logs, adjudicate contested ownership claims, and maintain campus-wide item auditability.

### Persona D: Competition Judge / Evaluator
- **Profile:** Technical evaluator assessing the software engineering rigor, AI integration, deterministic logic, user experience, and testing depth.
- **Goals:** Rapidly evaluate the system within 5 minutes using 1-click test accounts, submit a report, review deterministic match breakdowns, and verify privacy controls.

---

## 3. Functional Requirements

### Must-Have Requirements (Core MVP)
- [x] **FR-1: User Authentication & Authorization:** Secure registration and login using JWT tokens and bcrypt password hashing. Support for `student` and `admin` roles; public registration can only create students (admin requires a server-side invite code).
- [x] **FR-2: Mandatory Photographic Evidence:** Every lost and found report submission requires a valid photograph (`.png`, `.jpg`, `.jpeg`, `.webp`, up to 5MB) verified by decoding the image and checking its real format (400 PHOTO_REQUIRED, 413 too large, 415 wrong type).
- [x] **FR-3: Multimodal AI Attribute Extraction:** Integration with Gemini API (`gemini-2.5-flash`) via the official `google-genai` Python SDK to extract colors, materials, shapes, brands, and distinctive features into structured JSON validated by Pydantic.
- [x] **FR-4: Human-in-the-Loop Confirmation:** Extracted attributes are presented as editable suggestions that users can refine before saving.
- [x] **FR-5: Graceful Manual Fallback:** If Gemini is unreachable, times out, or no API key is configured, the system automatically engages rule-based heuristic extraction and allows manual attribute confirmation without halting submission.
- [x] **FR-6: Attribute Normalization:** Canonical dictionary-based normalization for colors, materials, shapes, object types, and categories.
- [x] **FR-7: Deterministic 100-Point Matching Engine:** A Python matching algorithm scoring Category (20), Object Type (15), Brand (15), Color (15), Material/Shape (10), Features (15), Location (5), and Date (5).
- [x] **FR-8: Match Explanations & Transparency:** Detailed score breakdowns, matched attribute lists, conflicting attribute lists, and unknown attribute lists.
- [x] **FR-9: Private Ownership Claims Workflow:** Finders set a private clue; claimant answers are verified on the server. Atomic attempt limit (3, then locked with HTTP 429), one claim per user per item, and finder approval of verified claims only.
- [x] **FR-9a: AI Suggestion Review:** `POST /api/reports/analyze` returns editable AI suggestions; users confirm or edit them before the report is saved.
- [x] **FR-9b: Contact Disclosure:** contact details only for the finder and the approved claimant (no admin bypass).
- [x] **FR-10: Contact Privacy Enforcement:** Submitter contact emails are masked in public endpoints (`[PROTECTED]`) and only authorized for direct handover upon approved claim verification.
- [x] **FR-11: Report Lifecycle Management:** Support for report statuses (`active`, `claim_pending`, `under_review`, `resolved`, `inactive`, `closed`). Resolved/closed items are automatically excluded from match rankings.

### Should-Have Requirements
- [x] **FR-12: Full-Text & Multi-Filter Catalog Search:** Case-insensitive search across title, description, and location combined with category and status dropdowns.
- [x] **FR-13: 1-Click Judge Quick Login:** Pre-seeded demo accounts (Alice Student, Bob Finder, Admin) with instant one-click access in the frontend header.
- [x] **FR-14: Admin Moderation Dashboard:** Real-time metrics overview, full report directory, and Gemini AI audit logs.

### Stretch Requirements
- [ ] **FR-15: Automated Email Notifications:** Real-time email notifications when high-scoring matches (>80) are detected or claims are reviewed.
- [ ] **FR-16: Campus Geolocation Pinning:** Interactive campus map showing pickup lockers and security desks.

---

## 4. Non-Functional Requirements

| ID | Requirement | Metric / Target | Status |
|---|---|---|---|
| **NFR-1** | API Response Latency | < 250ms for cached catalog and matching calculations | Verified |
| **NFR-2** | AI Fallback Latency | < 50ms fallback attribute generation when AI offline | Verified |
| **NFR-3** | Password Storage Security | Salted bcrypt with work factor >= 12 | Verified |
| **NFR-4** | Contact Information Leakage | 0% private email leakage in public API responses | Verified |
| **NFR-5** | Deterministic Reproducibility | 100% identical ranking given identical report inputs | Verified |
| **NFR-6** | Automated Test Coverage | Minimum 25 automated tests covering unit, integration, and e2e | 29/29 Passing |
| **NFR-7** | Responsive Accessibility | WCAG AA color contrast, mobile-friendly flexbox/grid layout | Verified |
| **NFR-8** | Zero External Runtime Dependency | High-performance in-memory MongoMock fallback for offline judging | Verified |

---

## 5. Out-of-Scope (Deliberately Excluded from MVP)
- Real-time peer-to-peer chat.
- Biometric facial recognition.
- Machine learning vector embeddings / vector databases (to preserve 100% deterministic, audit-friendly scoring).
- Automated AI ownership approval (prohibited by Core Product Principle: AI is an assistant, not an authority).
