# Record-Level Source Classification Consistency Audit

This audit compares original tender records with generated niche assignments. 
It does not approve, modify, or overwrite any classification.

## Counts
- Raw source rows: **34,232**
- Assignment rows: **34,232**
- Joined rows: **34,232**
- Unique source OCIDs: **34,232**
- Records without a matched suggested niche: **0**
- High-risk source-label records exported: **26**
- Generic-label records eligible for sample review: **2,946**
- Assignment/source field disagreements detected: **0**
- Final review queue rows: **106**

## High-risk source labels

| Original classification | Records |
|---|---:|
| Allotment of Space | 7 |
| Security System | 7 |
| Photostat Services | 3 |
| Entertainment/Musical Instruments | 2 |
| Chemicals/Minerals | 2 |
| Coal | 2 |
| Paddy Transplanter | 1 |
| Multi-crop Thresher | 1 |
| Explosive | 1 |

## Generic labels sampled

| Original classification | Total source records | Sample size |
|---|---:|---:|
| Miscellaneous Goods | 904 | 20 |
| Miscellaneous Services | 500 | 20 |
| Miscellaneous Works | 455 | 20 |
| Supply of Materials | 1,087 | 20 |

## Rules for interpretation
1. Preserve the source's original category and classification.
2. Treat niche suggestions as provisional.
3. A source-label/title conflict is a data-quality signal, not an automatic proof that the title is wrong.
4. Review the actual OCID and title before changing a mapping rule.
5. Do not infer eligibility, profitability, or win probability from category/title alone.
