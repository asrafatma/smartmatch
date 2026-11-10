# SmartMatch — Competition Submission Metadata

## Project Information
- **Project Name:** SmartMatch — AI-Powered Campus Lost & Found Platform
- **Team Name:** SmartMatch Team
- **Repository URL:** [https://github.com/itsas/smartmatch](https://github.com/itsas/smartmatch) <!-- Pending final push -->
- **Live Deployment URL:** [http://127.0.0.1:5000](http://127.0.0.1:5000) <!-- Locally running & verified; cloud URL placeholder: https://smartmatch-campus.onrender.com -->
- **Submission Timestamp:** 2026-11-10T11:51:00+05:00
- **Final Git Commit SHA:** `3c8b53270e5c656ff944cca0411c3bf9e8202aa3`

---

## Evaluation Summary
- **Core Product Principle:** AI is an assistance tool, not an authority.
- **Multimodal AI:** Gemini multimodal API (`gemini-2.5-flash`) via official `google-genai` SDK with Pydantic schema validation and automatic rule-based manual fallback.
- **Matching Engine:** Deterministic 100-point scoring matrix in pure Python with transparent score breakdowns and 4-tier tie-breaking.
- **Ownership Verification:** Private claim evidence with server-side 3-attempt limit lockout.
- **Contact Privacy:** Zero email leakage in public responses; contact details released only upon approved claim.
- **Automated Tests:** 29 passed out of 29 (100% pass rate) spanning unit, integration, and end-to-end journeys.
- **Judge Quick Start:** Documented in `README.md` with 1-click test access.
