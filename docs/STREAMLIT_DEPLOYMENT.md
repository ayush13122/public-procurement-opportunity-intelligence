# Streamlit Community Cloud deployment

## Before deploying

- Confirm `app/market_explorer.py`, `app/market_explorer_data.py`, `app/__init__.py`, and root `requirements.txt` are committed to GitHub.
- The app reads `data/processed/assam_procurement_cleaned.csv` and `reports/assam_record_niche_assignments.csv`; both must be present in the repo.
- Run tests: `python -m pytest tests -q`.
- Run locally from the repository root: `python -m streamlit run app/market_explorer.py`.

## Deploy

1. Open https://share.streamlit.io and sign in with GitHub.
2. Click Create app / New app.
3. Repository: `ayush13122/public-procurement-opportunity-intelligence`.
4. Branch: `main`.
5. Main file path: `app/market_explorer.py`.
6. Advanced settings: select Python 3.11 to match the local project environment.
7. Click Deploy and wait for build/runtime logs.
8. Open the generated `https://....streamlit.app` URL and check filters and charts.
9. Copy the generated app URL into the repository README under `Live demo`, and commit that README update.

## Important scope note

This app is an interactive explorer for historical Assam procurement records only. It is not a current tender feed; niche labels are provisional; tender value is shown without a currency symbol because the unit has not been independently verified; and it does not calculate profit, eligibility, or win probability.
