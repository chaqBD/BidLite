# BidLite Test Data

Sample QCS (Quote Comparison Sheet) files for testing BidLite.

All company identifiers, project names, vendor names, and specification codes have been
anonymised. Quantities and unit prices are representative of real-world procurement and
are retained for meaningful analytics demonstration.

## Files

| File | Description |
|---|---|
| `project_alpha_qcs.xlsx` | 25-item LV cable supply package — 6 anonymous bidders |

## How to use

Upload `project_alpha_qcs.xlsx` via **"Upload QCS File"** in the BidLite sidebar,
or run the app with sample data which uses the same underlying figures.

## Anonymisation map

| Original | Anonymised |
|---|---|
| Project name | Project Alpha — LV Power Cable Supply |
| Vendor names | Vendor Alpha … Vendor Zeta (Bidder A–F) |
| AWG cable sizes | IEC metric mm² equivalents |
| NEC/ANSI spec codes (81.09.xx) | Generic spec codes (EL-LV-xx-xxxx) |
| Quantities & unit prices | **Unchanged** (required for analytics fidelity) |

## Format

The Excel file follows the BidLite QCS format:
- Row 2: Bidder header row (contains "BIDDER 1" … "BIDDER 6")
- Row 4: "Pricing Breakdown" section marker
- Rows 5+: Line items — columns: `item_no | description | spec_code | qty | size | unit | [unit_price | definition | total_price] × 6`
