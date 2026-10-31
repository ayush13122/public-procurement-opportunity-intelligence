# Company Bid-Fit Analysis — Milestone 3

## Purpose

This module performs an explainable, rules-based comparison between a user's company profile and facts entered from a tender's official notice/documents. It provides screening support; it is not a machine-learning win predictor, legal eligibility opinion, or profitability model.

## Inputs

### Company profile
- Capability/product/service terms
- Service regions
- Years in business/relevant experience
- Number of similar completed projects
- Annual turnover in full INR
- EMD support capacity in full INR (cash, bank guarantee or approved support, as applicable)
- Certifications/registrations
- User confirmation that the company information is complete

### Tender requirements
- Tender title and official source URL
- Required capability terms and target region
- Minimum experience, similar-project and annual-turnover thresholds (when stated)
- Mandatory certifications and EMD amount (when stated)
- Closing date, when available
- User confirmations that the required criteria were reviewed and the official source/status was checked recently

## Recommendation logic

- **NO-BID**: a hard blocker exists (e.g. mandatory minimum not met, required certification absent, entered EMD capacity below stated EMD, or a past closing date) and the profile, requirements and official source are confirmed.
- **MANUAL REVIEW**: required details are missing/unconfirmed, the tender source is not rechecked, there are ambiguous or soft mismatches, no comparable criterion exists, or the rule-based score is below the Potential Bid threshold.
- **POTENTIAL BID**: no hard blocker is identified, profile and requirements/source confirmations are present, and the rule-based fit score reaches the configured threshold.

## Score

The score is the points earned across criteria entered into the form, normalized by the total weights of criteria that can be assessed. A criterion that is not supplied is not silently assumed to pass. Capability-match weights are based on simple text overlap; geography is a soft signal. Mandatory eligibility failures are shown separately and override a high score only when the user has confirmed the relevant facts.

## Important limitations

1. It uses user-entered values and does not verify them against official tender portals.
2. It does not yet import parsed clauses directly from the AI Copilot; the user manually enters the structured requirements in this milestone.
3. Text overlap is not semantic matching; synonyms and technical/legal equivalents require human review.
4. Turnover thresholds and EMD capacity are compared in full INR. Do not enter values in lakhs/crores without converting to rupees.
5. Estimated tender value is not a profit estimate. No bid-win probability or profitability prediction is produced.
6. A `POTENTIAL BID` is not a legal assurance or guarantee of award. Always verify the latest tender notice and corrigenda on the official source.
7. Form inputs are held in the Streamlit session for the displayed result and are not written to a project database by this module.

## Run

```powershell
python -m pytest tests -q
python -m streamlit run app/market_explorer.py
```

Select **Company Bid-Fit Analysis** in Streamlit's multipage navigation.

## Test coverage

The Milestone 3 test module includes: potential-bid path, mandatory turnover/certification/EMD blockers, expired deadlines with/without verification, unconfirmed company/tender details, missing required company inputs, invalid official URL, soft capability mismatch, no comparable criterion, blank tender title, and negative-value validation.
