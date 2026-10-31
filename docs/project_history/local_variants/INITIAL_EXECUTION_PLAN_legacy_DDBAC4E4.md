# Execution Plan — Target: 18–21 Days

## Phase 0 — Environment and source feasibility (Days 1–2)
- [x] Set up Python 3.11 virtual environment and required libraries.
- [x] Download and initially audit the Assam procurement ZIP.
- [x] Test the official CPPP active-tender and archive search pages manually.
- [ ] Complete category profiling and review first-pass niche taxonomy.

**Deliverable:** category-profile reports and a reviewed mapping worksheet.

## Phase 1 — Historical data engineering (Days 3–5)
- Validate source schema, IDs, fiscal years, amount parsing, and field coverage.
- Preserve raw source files and create a cleaned analytical table.
- Keep source values and parsed/derived values in separate columns where helpful.
- Create a reusable SQLite database or well-defined CSV tables.

**Deliverable:** reproducible cleaning script, cleaned table, and data-quality report.

## Phase 2 — Current tender sample (Days 6–8)
- Use official public listings/permitted downloads; manually pass CAPTCHA when required.
- Capture a bounded sample of current notices, aiming for 150–300 records only if access permits.
- Save tender ID, title, buyer, dates/deadline, category/niche, value if shown, status, source URL, and collected/checked timestamp.
- Inspect detailed documents only for a small shortlist; do not download every PDF.

**Deliverable:** traceable current tender dataset and collection log.

## Phase 3 — Historical market analysis (Days 9–11)
- Analyze categories, classifications, buyers, fiscal-year patterns, stages and published values where available.
- Highlight missingness and the concentration in Works/civil categories.
- Keep findings within the Assam/time-period scope.

**Deliverable:** reproducible EDA and evidence-backed insights.

## Phase 4 — Company-fit and bid support (Days 12–14)
- Define an explicitly hypothetical supplier profile for demonstrations.
- Separate mandatory eligibility checks from soft fit scoring.
- Add configurable category/capability, location, contract range, deadline and evidence-completeness criteria.
- Use Bid Candidate / Manual Review / No-Bid labels and show reasons.
- Do not estimate win probability without suitable labelled outcomes.

**Deliverable:** scoring logic, unit tests, and sensitivity checks.

## Phase 5 — Streamlit application (Days 15–17)
- Build tabs/pages for Historical Market Explorer, Category Explorer, Current Tender Explorer and Company Fit.
- Include filters, KPI cards, charts, source links, record-level reasons, and CSV export.

**Deliverable:** working local app.

## Phase 6 — Validation and portfolio packaging (Days 18–21)
- Cross-check sampled source records against official pages/documents.
- Test missing fields, invalid deadlines, duplicate records and changed profile settings.
- Finalize README, screenshots, report and interview demo.

**Deliverable:** presentation-ready repository and documented limitations.

## Scope cut rules
If current-source collection is slower than expected, keep a smaller well-verified current sample and still complete the historical analysis/app. Drop advanced ML first; do not drop source provenance, missing-data reporting, scoring explanations, or the distinction between historical and current records.
