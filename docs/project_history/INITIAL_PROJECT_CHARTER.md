> **Historical planning note:** This document captures the initial project plan. Some features described as planned—especially current-tender ingestion or broad scope—are not necessarily implemented in the current release. For the actual current state, use the root `README.md` and `docs/FINAL_PROJECT_STATUS.md`.

---

# Project Charter

## Project title
**Public Procurement Opportunity Intelligence & Bid Strategy Platform**

## Problem statement
Companies reviewing public procurement notices may spend substantial time finding relevant opportunities and checking whether they match the supplier's capabilities, preferred locations, commercial limits, and operational capacity. Historical procurement patterns can help with market understanding, while current notices are needed to identify opportunities that may still be open. These two kinds of data serve different purposes and must be kept distinct.

## Objective
Build a reproducible decision-support application that combines historical procurement-market analysis with a curated set of current public tender listings. It will let a user explore procurement categories, configure a supplier profile, shortlist relevant opportunities, and review an explainable Bid Candidate / Manual Review / No-Bid recommendation.

## Research question
How can public procurement data be converted into reliable market insights and an explainable process for prioritizing current tender opportunities for different supplier profiles?

## Data sources and scope
### Historical dataset
- Source catalog: https://www.data.gov.in/catalog/assam-public-procurement-data
- Downloaded archive contains six fiscal-year CSV files covering 2016–2017 to 2021–2022.
- Initial audited size: 34,232 rows and 34 source columns.
- The original data contains three broad procurement categories (`Works`, `Goods`, `Services`) and 89 detailed classification labels.
- Geographic scope is Assam; do not generalize these results to all of India.

### Current opportunity dataset
- Candidate source: Government of India eProcurement / Central Public Procurement Portal: https://www.eprocure.gov.in/eprocure/app
- Current records will be collected only from accessible listings or permitted downloads, with search/CAPTCHA completed manually where required. No CAPTCHA bypass or unauthorized scraping.
- Working target: 150–300 curated current notice records if feasible within the schedule. Quality and traceability take priority over an arbitrary row count.
- Current notices and Assam historical records will retain separate source, geography, and time-period fields. They may share an analytical niche mapping, but will not be merged as though they represent the same market/time period.

## Target users
1. Business Development professional screening procurement opportunities.
2. Business Analyst studying buyers, categories, values, and market patterns.
3. Data/Analytics professional building a reproducible data pipeline and transparent decision-support tool.

## Planned capabilities
1. Source register and provenance tracking.
2. Data-quality and schema checks, duplicates, missingness, and date/amount parsing.
3. Historical Market Explorer by fiscal year, original category, classification, buyer, stage, and tender value where valid.
4. Reviewable niche taxonomy that preserves original source labels.
5. Current Tender Explorer with search, filters, deadlines, source links, and freshness/last-checked fields.
6. Configurable supplier profile: services/capabilities, regions, preferred value range, and mandatory criteria.
7. Explainable opportunity-fit score, separate from eligibility checks and commercial estimates.
8. Bid Candidate / Manual Review / No-Bid recommendation with supporting reasons and missing-evidence flags.
9. Streamlit application, charts, CSV export, tests, and portfolio documentation.

## Non-goals for the first release
- No claim to predict tender-win probability without suitable outcome labels and leakage-safe validation.
- No automatic bid submission.
- No CAPTCHA bypass or unauthorized scraping.
- No claim that tender value equals profit.
- No claim of confirmed eligibility using only a short listing summary; shortlisted tender documents must be checked.
- No claim that the app is real-time unless reliable refresh is implemented and tested.

## Evaluation criteria
- Retained records have a source URL or documented source provenance.
- Raw data is preserved separately from cleaned data.
- Category mappings are explainable, reviewable, and do not overwrite original labels.
- Duplicate, missing-value, date and amount parsing checks are reported.
- Company-fit scoring is transparent and configurable.
- Mandatory disqualifiers cannot be outweighed by a high fit score.
- Recommendations show both supporting evidence and data gaps.
- Historical and current data are distinguishable by source, time and geography.
- Application runs locally using documented steps.

## Main risks and mitigation
- **Search/CAPTCHA limits:** use accessible lists and permitted downloads; manually verify selected samples and record the collection method.
- **Incomplete listing details:** preserve missing values and send users to official tender documents.
- **Historical-data concentration:** surface the strong Works/civil-construction skew rather than presenting all niches as equally represented.
- **No comparable outcome history:** build descriptive intelligence and rule-based ranking, not unsupported win predictions.
- **Scope creep:** keep the first release to the existing historical dataset plus a bounded current tender sample.
- **Time:** aim for completion in 18–21 days and finish before 30 days.

## Definition of done
A clean repository; category-profiling and cleaning scripts; documented source register; historical analytical reports; curated current tender sample with traceable links; configurable and tested opportunity scoring; functioning local dashboard; a final report/demo; and explicit limitations.
