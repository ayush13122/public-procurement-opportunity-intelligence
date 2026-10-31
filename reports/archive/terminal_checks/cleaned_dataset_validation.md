# Cleaned Dataset Validation

- Input file: `data\processed\assam_procurement_cleaned.csv`
- Rows: 34,232
- Columns: 21
- Unique OCIDs: 34,232
- Duplicate OCID rows: 0

## Broad Category Counts

| category   |   records |
|:-----------|----------:|
| Works      |     28647 |
| Goods      |      4279 |
| Services   |      1306 |

## Top 15 Detailed Classifications

| classification            |   records |
|:--------------------------|----------:|
| Civil Works               |     14733 |
| Civil Works – Roads       |      6020 |
| Civil Works - Building    |      3697 |
| Electrical Works          |      1108 |
| Supply of Materials       |      1087 |
| Miscellaneous Goods       |       904 |
| Construction Works        |       655 |
| Civil Works - Water Works |       613 |
| Miscellaneous Services    |       500 |
| Miscellaneous Works       |       455 |
| Civil Works - Bridges     |       422 |
| Machineries               |       371 |
| Medical Equipments/Waste  |       325 |
| Food Products             |       317 |
| Consultancy               |       316 |

## Tender Value Checks

- positive_values: 30242
- zero_values: 2410
- missing_or_non_numeric: 1580
- negative_values: 0
- median_positive_value: 9998955.0

## Publication Date Checks

- publication_dates_parsed: 34232
- publication_date_rows: 34232
- earliest_publication: 2016-04-10 13:00:00
- latest_publication: 2022-03-31 18:50:00

## Top 10 Fields by Missing Percentage

| column                         |   missing_count |   missing_pct |
|:-------------------------------|----------------:|--------------:|
| tender/documents/id            |           34104 |         99.63 |
| tender/numberOfTenderers       |            2573 |          7.52 |
| tender/value/amount            |            1580 |          4.62 |
| tender/stage                   |             386 |          1.13 |
| ocid                           |               0 |          0    |
| tender/id                      |               0 |          0    |
| tender/externalReference       |               0 |          0    |
| tender/title                   |               0 |          0    |
| tender/mainProcurementCategory |               0 |          0    |
| tender/procurementMethod       |               0 |          0    |
