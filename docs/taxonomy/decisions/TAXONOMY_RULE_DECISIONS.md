# Taxonomy Rule Decisions

| Observed title pattern | Refined behavior | Reason |
|---|---|---|
| Cruise ferry vessel / barge / speed boat | Transport & Logistics | Vessel construction is not necessarily civil infrastructure |
| Monthly lease/rent of guest house or weigh bridge | Property, Space & Facilities | Rental/space purpose precedes broad bridge matches |
| Office furniture and stationery with a department name | Office & General Supplies | Match supplied product, not contextual department words |
| Routine immunization logistics | Healthcare & Laboratory | Immunization is the substantive domain; logistics is the delivery term |
| Cleaning/desilting city drains | Water, Sanitation & Environmental Services | Infrastructure/environment context should outrank generic housekeeping |
| Coffee-table book on sanitation | Media, Printing & Creative Services | Publication deliverable is primary |
| Road/building/bridge construction phrases | Construction & Civil Infrastructure | Use context-specific civil-construction phrases rather than any occurrence of `construction` |
| LAN | Computer, Network & Electronics only when the standalone token occurs | Prevent substring false positives such as `plant` |
