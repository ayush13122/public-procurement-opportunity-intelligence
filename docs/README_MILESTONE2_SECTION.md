## ML Classifier and AI Tender Document Copilot

This Streamlit project includes two additional pages:

- **ML Tender Category Classifier** — predicts the historical dataset's broad procurement category (Works, Goods or Services) from a tender title using the trained TF-IDF + Logistic Regression model. Run `python src/train_procurement_category_model.py` to generate the model artifact when needed. Scores are not tender-win probabilities.
- **AI Tender Document Copilot** — extracts selectable text from a tender PDF, retrieves relevant page-level evidence using local TF-IDF search, and can draft an answer with page citations when `OPENAI_API_KEY` is configured.

Run:

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m streamlit run app/market_explorer.py
```

The sample file `assets/demo_synthetic_tender_notice.pdf` is fictional and intended only for local testing. It is not an official tender.

For generated answers, copy `.env.example` to `.env`, add an API key, and never commit `.env`. Without an API key, local PDF text extraction and evidence retrieval still work. OCR, live tender-status checking, all-portal scraping, win prediction and profitability prediction are not included.
