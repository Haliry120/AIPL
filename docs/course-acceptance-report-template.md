# Course Acceptance Report Template

## 1. Basic Information

- Project name: `AIPLfinal`
- Course: `<fill in>`
- Student: `<fill in>`
- Student ID: `<fill in>`
- Submission date: `<fill in>`
- Runtime environment:
- Frontend: React (`npm run build`)
- Backend: Flask + MongoDB
- Database: MongoDB (`aipl_database`)

## 2. Acceptance Scope

This report verifies the following required capabilities:

1. Data input
2. Data management (create/update/delete)
3. Data analysis and processing
4. Data query
5. Data import/export (CSV acceptable)
6. Data visualization
7. Export of statistical features
8. Security settings
9. Database entities >= 5

## 3. Requirement-by-Requirement Checklist

### 3.1 Data Input

- Result: `Pass`
- Description:
- Users can input learning topics and generate roadmap/resources.
- Users can submit quiz answers, wrong-question notes, and redo answers.
- Evidence (code points):
- `backend/base.py:756` (`/api/roadmap`)
- `backend/base.py:791` (`/api/quiz`)
- `backend/base.py:1279` (`/api/wrong-questions/note`)
- `backend/base.py:1328` (`/api/redo-records`)
- Screenshot points:
- Figure 1: Topic input page (`src/pages/input/topic.js`) with entered topic.
- Figure 2: Quiz submit action page (`src/pages/quiz/quiz.js`).
- Figure 3: Wrong-question note edit and redo submit page (`src/pages/wrong/wrong.js`, `src/pages/redo/redoPlay.js`).

### 3.2 Data Management (Create/Update/Delete)

- Result: `Pass`
- Description:
- Supports user profile update, password change, avatar update, account deletion.
- Supports prompt template create/edit/delete/favorite.
- Prompt templates also support enable/disable and tags, and can take effect at inference time.
- Supports quiz records and wrong/redo record deletion.
- Supports direct return to home after confirmed course cancellation (no extra success popup).
- Evidence (code points):
- `backend/base.py:501` (`PUT /api/user/settings`)
- `backend/base.py:542` (`PUT /api/user/password`)
- `backend/base.py:579` (`POST /api/user/delete-account`)
- `backend/base.py:655`/`668`/`735` (prompt template CRUD)
- `backend/mongodb.py:222` (prompt template persistence)
- `backend/base.py:1084` (`/api/delete-quiz-records`)
- `backend/base.py:1295` (`/api/wrong-questions/delete`)
- `backend/base.py:1378` (`DELETE /api/redo-records/<record_id>`)
- Screenshot points:
- Figure 4: Settings page profile update actions (`src/pages/settings/settings.js`).
- Figure 5: Prompt template add/edit/delete in settings.
- Figure 6: Delete quiz/wrong/redo records UI action and result.

### 3.3 Data Analysis and Processing

- Result: `Pass`
- Description:
- User profile analyzer computes activity, mastery, preferences, effectiveness, and recommendations.
- User-defined prompt templates are injected into model system prompts at runtime (scenario tag match first, fallback to enabled templates).
- Evidence (code points):
- `backend/user_profile.py:14` (`UserProfileAnalyzer`)
- `backend/user_profile.py:49` (`_analyze_learning_activity`)
- `backend/user_profile.py:141` (`_analyze_knowledge_mastery`)
- `backend/user_profile.py:238` (`_analyze_learning_preferences`)
- `backend/user_profile.py:284` (`_analyze_learning_effectiveness`)
- `backend/user_profile.py:333` (`_generate_recommendations`)
- `backend/prompt_injector.py:6` (enabled prompt filtering and scenario matching)
- `backend/prompt_injector.py:75` (system instruction merge)
- `backend/siliconflow_client.py:95` and `backend/siliconflow_client.py:118` (unified injection to `messages[0].content`)
- Screenshot points:
- Figure 7: User profile subject detail page showing computed metrics (`src/pages/userprofile/userprofile.js`).
- Figure 8: API response screenshot from `/api/user-profile/summary`.
- Figure 8-1: Same question before/after enabling prompt template (response style comparison).

### 3.4 Data Query

- Result: `Pass`
- Description:
- Supports query of quiz records, user data, wrong questions, redo records, subject overview/detail.
- Supports online-course (Bilibili) query with keyword refinement and previous/next page navigation.
- Keyword search is re-based on the initial topic + current input each time (no historical keyword accumulation).
- When extra keywords are provided, backend prioritizes videos whose title/description match those keywords.
- Page results are cached on frontend for faster back/forward page rendering; Enter key triggers keyword search.
- Legacy difficulty interaction has been removed; stale `hardnessIndex` local storage is cleaned up.
- Evidence (code points):
- `backend/base.py:1061` (`GET /api/quiz-records`)
- `backend/base.py:1103` (`GET /api/user-data`)
- `backend/base.py:1233` (`GET /api/wrong-questions`)
- `backend/base.py:1364` (`GET /api/redo-records`)
- `backend/base.py:1518` (`GET /api/user-profile/subjects-overview`)
- `backend/base.py:1552` (`GET /api/user-profile/subject-detail`)
- `backend/base.py` (`POST /api/search-bilibili`, supports `extra_keyword/page/refresh`)
- `backend/bilibili_search.py` (page-based Bilibili search)
- `src/pages/roadmap/roadmap.js` (keyword input, Enter trigger, pagination, page cache)
- `src/pages/userprofile/userprofile.js` (detail-mode back button moved next to header actions)
- Screenshot points:
- Figure 9: Subject overview list query with search/sort (`src/pages/userprofile/userprofile.js`).
- Figure 10: Subject detail panel query result.

### 3.5 Data Import and Export (CSV)

- Result: `Pass`
- Description:
- Supports exporting user profile statistical features as CSV/JSON.
- Supports importing user profile statistical features from CSV/JSON.
- Evidence (code points):
- `backend/base.py:1699` (`GET /api/user-profile/export`)
- `backend/base.py:1740` (`POST /api/user-profile/import`)
- `backend/base.py:1576` (`_profile_to_csv`)
- `backend/base.py:1655` (`_csv_to_profile`)
- `src/pages/settings/settings.js:656` (import/export UI)
- Screenshot points:
- Figure 11: Click export CSV and saved file in local folder.
- Figure 12: Import the exported CSV on another account and success message.
- Figure 13: Settings summary cards changed after import.

### 3.6 Data Visualization

- Result: `Pass`
- Description:
- Uses chart visualization for progress and trends.
- Evidence (code points):
- `src/pages/profile/profile.js:16` (`Bar` from `react-chartjs-2`)
- `src/pages/profile/profile.js:221` (bar chart render)
- `src/pages/userprofile/userprofile.js:3` (`Line` from `react-chartjs-2`)
- `src/pages/userprofile/userprofile.js:587` (line chart render)
- Screenshot points:
- Figure 14: Progress bar chart in profile page.
- Figure 15: Trend line chart in userprofile detail page.

### 3.7 Statistical Feature Export

- Result: `Pass`
- Description:
- Statistical features are aggregated and exported in structured CSV (`section,key,value`).
- Evidence (code points):
- `backend/base.py:1576` (`_profile_to_csv`)
- `backend/base.py:1609` (`csv.DictWriter`)
- `backend/base.py:1735` (`Content-Type: text/csv`)
- Screenshot points:
- Figure 16: Open exported CSV and show key sections (`learning_activity`, `knowledge_mastery`, etc.).

### 3.8 Security Settings

- Result: `Pass`
- Description:
- JWT authentication with cookie support.
- CORS allowlist and credential mode.
- Password hashing and password verification.
- API rate limiting and security audit log output.
- Evidence (code points):
- `backend/base.py:36` (`CORS(... supports_credentials=True)`)
- `backend/base.py:38`-`47` (JWT secret/algorithm/expiry)
- `backend/base.py:173` (`_set_auth_cookie`)
- `backend/base.py:404` and `backend/base.py:441` (`generate_password_hash` / `check_password_hash`)
- `backend/base.py:63` and `backend/base.py:128` (rate limit rules/enforcement)
- `backend/base.py:97` (`SECURITY_AUDIT` log)
- Screenshot points:
- Figure 17: Login success and authenticated request behavior.
- Figure 18: Settings password update success path.
- Figure 19: Rate-limit message example (if reproduced).

### 3.9 Database Entity Count >= 5

- Result: `Pass`
- Description:
- Actual entities in MongoDB collections: 7.
- Entity list:
- `users`
- `learning_contents`
- `learning_stats`
- `quiz_records`
- `wrong_questions`
- `redo_records`
- `user_profiles`
- Evidence (code points):
- `backend/mongodb.py:23`
- `backend/mongodb.py:24`
- `backend/mongodb.py:25`
- `backend/mongodb.py:26`
- `backend/mongodb.py:27`
- `backend/mongodb.py:28`
- `backend/mongodb.py:32`
- Screenshot points:
- Figure 20: MongoDB collections list screenshot.

## 4. Test Execution Summary

- Frontend build: `npm run build` -> `Compiled successfully`
- Backend syntax check: `python -m py_compile backend/base.py backend/database.py` -> `Pass`
- Core business flow tested:
- Register/login
- Topic input -> roadmap -> quiz
- Wrong-question and redo flow
- Settings prompt CRUD (create/edit/delete/enable/disable/favorite)
- Prompt runtime integration test: `/api/resource-qa` outgoing `system` contains `[User Custom Prompt Templates]`
- Online-course search verification: keyword label shown in result text, keyword is not cumulatively stacked, Enter-to-search works.
- Online-course pagination verification: previous/next page switching, cached pages render quickly when revisited.
- Course-cancel UX verification: after confirmation, data is cleaned and user returns home without additional success alert.
- Legacy difficulty cleanup verification: no "difficulty index" UI remains and stale local key is removed.
- User-profile export/import

## 5. Optional Advanced Design Notes

- The project includes:
- Multi-module data flows (`quiz_records`, `wrong_questions`, `redo_records`, `user_profiles`).
- Cross-page data linkage for profile dashboard and subject detail analysis.
- Account lifecycle management (update, password reset, delete-account cascading cleanup).

## 6. Known Limitations (If Instructor Asks)

- Current import/export scope focuses on user profile statistical features (not full raw business tables).
- For production hardening, CSRF token protection can be further added for cookie-auth write APIs.

## 7. Final Conclusion

- Overall status: `Pass`
- The system meets all listed acceptance requirements:
- Data input
- Data management (CRUD)
- Data analysis/processing
- Data query
- CSV import/export
- Data visualization
- Statistical feature export
- Security settings
- >= 5 database entities

---

## Appendix A. Screenshot Checklist (for quick submission)

1. Topic input page with sample topic entered.
2. Quiz answer submission page.
3. Wrong-question note + redo submission page.
4. Settings page profile update.
5. Prompt CRUD operations.
6. Record deletion operation.
7. User profile summary/detail metrics.
8. Subjects overview query and filter.
9. CSV export success and local file.
10. CSV import success and updated settings summary cards.
11. Profile bar chart screenshot.
12. Subject trend line chart screenshot.
13. Security behavior screenshot (auth or rate limit).
14. MongoDB 7 collections screenshot.

## Appendix B. Fill-In Signature

- Student signature: `<fill in>`
- Reviewer signature: `<fill in>`
- Review date: `<fill in>`
