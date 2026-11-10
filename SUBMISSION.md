# SmartMatch — Competition Submission Metadata

> Fill in every `<...>` value only after it has been verified (see README → Deployment).
> Do not submit placeholder values.

## Project information

| Field | Value |
|---|---|
| Team Name | `<TEAM_NAME>` |
| Project Name | SmartMatch — AI-Powered Campus Lost & Found Platform |
| Repository URL | `<https://github.com/<user>/<repo>>` |
| Live Deployment URL | `<https://<service>.onrender.com>` (verified from a device outside the dev machine) |
| Submission Timestamp | `<YYYY-MM-DDTHH:MM:SS+05:00>` |
| Final Git Commit SHA | `<output of: git rev-parse HEAD after the final push>` |

## Verification checklist (complete before submitting)

- [ ] `<LIVE_URL>/api/health` returns `"status": "healthy"` and `"database": {"status": "healthy"}`
- [ ] Demo login `alice@campus.edu / student123` works on the live URL
- [ ] GitHub Actions CI run for the final commit is green
- [ ] `git log -p | grep -iE "mongodb\+srv://[^<]|AIza"` returns nothing (no leaked secrets)
- [ ] The SHA above equals `git rev-parse HEAD` and the GitHub repository's latest commit

## Evaluation summary

- **Core principle:** AI is an assistance tool, not an authority.
- **AI:** Gemini multimodal extraction (`google-genai` SDK) → Pydantic validation → user review/edit; manual fallback
  on any AI failure; every call logged in `ai_logs`.
- **Matching:** deterministic 100-point scoring with fixed dictionaries, explanations and stable tie-breaks;
  versioned configuration.
- **Claims:** finder's private clue verified on the server, atomic 3-attempt limit (429), one claim per user per
  item, finder approval required.
- **Privacy:** contact details only for the finder and the approved claimant; private clues never leave the server.
- **Tests:** `bash scripts/test.sh` (unit, integration, end-to-end, organizer acceptance tests; Gemini mocked).
