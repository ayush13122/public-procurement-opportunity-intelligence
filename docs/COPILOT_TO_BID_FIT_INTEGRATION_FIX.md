# Copilot-to-Bid-Fit integration fix

This follow-up patch addresses the browser smoke-test findings:

- Preserve reviewed field values along with PDF source/page evidence.
- Add a recovery button to re-apply reviewed values if Streamlit page navigation leaves tender widgets blank.
- Clear stale imported evidence when a different PDF is processed.
- Improve conservative extraction of an unlabeled title below “REQUEST FOR QUOTATION / TENDER NOTICE”, contract location, and table-style GST registration.
- Avoid inferring “network installation” just because “network connectivity” and a separate installation clause both appear.

The new field detections remain candidates, not verified legal requirements. The official URL and the Bid-Fit verification checkboxes remain blank/unchecked. The user must manually fill missing title/region/certifications and verify all evidence.
