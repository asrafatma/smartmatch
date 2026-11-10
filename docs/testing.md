# SmartMatch — Testing Strategy & Verification Guide

## 1. Overview & Test Philosophy
SmartMatch is verified using a multi-tiered automated test suite built on **pytest** and the Flask test client. The testing strategy emphasizes:
1. **Zero External Flakiness:** All tests execute against an isolated in-memory MongoMock database and mock/fallback AI components so continuous integration never fails due to network partitions, third-party API rate limits, or billing quotas.
2. **Deterministic Reproducibility:** Every matching score test verifies the exact numerical outcome and tie-breaking order.
3. **Defense-in-Depth Security:** Explicit negative tests verify that unauthorized users, missing photos, forged roles, and private contact leaks are strictly rejected.

---

## 2. Test Execution Commands

### Running All Automated Tests
```bash
# Execute full test suite with verbose output
python -m pytest -v --tb=short

# Execute via standard bash CI test runner
bash scripts/test.sh
```

### Running Specific Test Suites
```bash
# Unit Tests (Normalizer, Matching Engine, AI Fallback)
python -m pytest tests/unit/ -v

# Integration Tests (Auth, Reports, Claims & Privacy)
python -m pytest tests/integration/ -v

# End-to-End User Journey Tests
python -m pytest tests/e2e/ -v
```

---

## 3. Test Coverage Matrix

| Category | Test File | Scenarios Verified | Status |
|---|---|---|---|
| **Unit** | `tests/unit/test_normalizer.py` | Color canonicalization (`navy` $\to$ `dark_blue`), material synonyms, category validation, object type detection with word boundary regex, attribute deduplication. | 5/5 PASSED |
| **Unit** | `tests/unit/test_matching_engine.py` | Weight matrix sum = 100, obvious pair high score ($\ge 85$), conflicting attributes low score ($< 40$), neutral unknown handling, known pair ranking above distractor. | 5/5 PASSED |
| **Unit** | `tests/unit/test_gemini_fallback.py` | Heuristic fallback keyword extraction, Pydantic `ItemExtractionResult` validation, graceful handling of missing Gemini API key with zero crashes. | 2/2 PASSED |
| **Integration** | `tests/integration/test_auth_routes.py` | Registration (201), duplicate email rejection (400), short password rejection (400), login success (200), invalid credentials (401), JWT protected `/me` endpoint. | 6/6 PASSED |
| **Integration** | `tests/integration/test_report_routes.py` | Mandatory photo requirement (400 if missing), invalid file type rejection (400), successful report creation with photo (201), private contact masking in public responses, unauthorized update rejection (403). | 5/5 PASSED |
| **Integration** | `tests/integration/test_claim_and_privacy.py` | Claim submission against found item (201), self-claim prohibition (400), 3-attempt limit lockout (403), unauthorized review rejection (403), finder claim approval, report status transition to resolved, authorized contact release. | 4/4 PASSED |
| **End-to-End** | `tests/e2e/test_user_journeys.py` | Complete lifecycle: Alice files lost wallet $\to$ Bob files found wallet $\to$ deterministic matching ranks pair #1 ($97.0$) $\to$ Alice claims $\to$ Bob approves $\to$ contact released. Exclusion of resolved reports from matching catalog. | 2/2 PASSED |
| **Total** | | **29 Automated Tests** | **29/29 PASSED** |

---

## 4. High-Value Test Scenario Verification

### 1. Mandatory Photograph Enforcement
- **Requirement:** A valid photograph is strictly required for report submission.
- **Verification:** `tests/integration/test_report_routes.py::test_report_submission_mandatory_photo` sends a multipart request without an `image` payload. Asserted HTTP 400 with `"photograph is mandatory"`.

### 2. Gemini Failure & Graceful Manual Fallback
- **Requirement:** If Gemini is unreachable or no API key is configured, report submission must not fail.
- **Verification:** `tests/unit/test_gemini_fallback.py::test_analyze_handles_missing_api_key_cleanly` unsets `GEMINI_API_KEY`. Report analyzer generates structured heuristic attributes, marks `ai_status = manual`, and logs to `ai_logs`.

### 3. Contact Privacy & Anti-Leakage Shield
- **Requirement:** Real email addresses and phone numbers must never be exposed publicly.
- **Verification:** `tests/integration/test_report_routes.py::test_public_report_masks_private_contact_info` queries public report endpoints and confirms the submitter email is masked as `[PROTECTED — AVAILABLE UPON APPROVED CLAIM]`.
- **Verification:** `tests/integration/test_claim_and_privacy.py::test_claim_review_and_contact_privacy_authorization` confirms contact details are only unlocked for the specific claimant and finder once the claim is approved.

### 4. Known Matching Pair Priority
- **Requirement:** Known matching pairs must rank above unrelated candidates.
- **Verification:** `tests/unit/test_matching_engine.py::test_known_pair_ranks_above_distractor` compares a lost black leather wallet against a matching found wallet and a distractor yellow water bottle. True match scores $\ge 85$ while distractor scores $< 30$.

### 5. Server-Side Claim Attempt Limits
- **Requirement:** Prevent brute-force claiming by locking claims after 3 failed/repeated attempts.
- **Verification:** `tests/integration/test_claim_and_privacy.py::test_claim_attempt_limits_and_lock` attempts 3 successive submissions. The 3rd attempt returns HTTP 403 with `status = locked`.

---

## 5. Judge Evaluation Workflow (Under 5 Minutes)
1. Launch local server: `python run.py`.
2. Open `http://127.0.0.1:5000` in any web browser.
3. Click **👤 Alice (Student / Lost Item)** in the top judge banner.
4. Click **Browse Reports** $\to$ observe the seeded catalog of lost and found items.
5. Click **Black Leather Bifold Wallet** $\to$ inspect the Potential Matches section:
   - Notice the **Found Black Leather Wallet** ranked at **97.0 / 100** ("Strong candidate").
   - Inspect the score breakdown and confirmed matching pills.
6. Click **🔍 Bob (Finder / Found Item)** in the top judge banner.
7. Click **Claims Review** in the navigation bar:
   - Notice the pending claim on the **Honda Car Keys** submitted by Alice.
   - Click **✓ Approve Ownership** $\to$ verify status updates to approved and report resolves.
