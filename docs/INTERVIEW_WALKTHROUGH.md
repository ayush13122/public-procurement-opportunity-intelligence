# 90-Second Project Walkthrough (Interview Notes)

“I built a reproducible public-procurement analysis pipeline using Assam's historical tender data from the Government of India's OGD Platform. The source contained 34,232 records across six annual CSV files and 34 columns. I audited the source, preserved the original rows, created a 21-column analytical dataset, profiled categories and buyers, and generated EDA and business-analysis reports.

A major engineering challenge was that source classifications were broad or occasionally inconsistent with the tender titles. I built a provisional taxonomy workflow, restricted title keyword rules to avoid obvious false positives, created review queues, and added regression tests. I also validated generated business reports against the underlying records, including OCID alignment and category/fiscal-year aggregates.

The dataset is historical and Assam-specific, so I do not treat it as current tender availability or generalize the category mix to all of India. The current release is an analysis foundation; the next phase is a human-reviewed taxonomy, a documented current-tender collection workflow, and a configurable opportunity-fit interface.”

## If asked “What is the business value?”
The analysis helps a supplier understand which procurement categories and buyer organizations appear in the historical records, how complete the public fields are, and which categories may merit further investigation. Any actual bid decision still needs current tender notices, company-specific eligibility, delivery costs, and original documents.

## If asked “Does it predict which tender we can win?”
No. The current version does not estimate win probability or profit. It creates auditable evidence and historical market summaries. The future decision-support module would need company profile inputs and original tender requirements, with uncertain cases routed to manual review.
