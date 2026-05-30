"""
Generate anonymised QCS Excel test data for BidLite.

Rules applied:
  - Project name, vendor names, spec codes → replaced with generic identifiers
  - Cable descriptions: NEC/ANSI AWG naming → IEC metric mm² naming
  - Quantities and unit prices: UNCHANGED (required for analytics fidelity)

Run:
    cd test_data
    python generate_test_data.py
Produces: project_alpha_qcs.xlsx
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Anonymised item catalogue ──────────────────────────────────────────────────
# (item_no, description, spec_code, qty, size_note, unit)
# Description: IEC metric naming instead of NEC/AWG
# Spec code:   EL-LV-XX-XXXX instead of 81.09.XX.XXX
ITEMS = [
    (6,  "0.6/1kV, 1C, 6mm², XLPE/PVC, Type W2",         "EL-LV-01-0001", 186660, "6mm²",  "LM"),
    (7,  "0.6/1kV, 1C, 16mm², XLPE/PVC, Type W2",         "EL-LV-01-0002", 242,    "16mm²", "LM"),
    (8,  "0.6/1kV, 1C, AL, 35mm², XLPE/PVC, Type W2",     "EL-LV-01-0002", 356,    "35mm²", "LM"),
    (9,  "0.6/1kV, 1C, 50mm², XLPE/PVC, Type W2",         "EL-LV-01-0003", 242,    "50mm²", "LM"),
    (10, "0.6/1kV, 1C, AL, 50mm², XLPE/PVC, Type W2",     "EL-LV-01-0003", 3032,   "50mm²", "LM"),
    (11, "0.6/1kV, 1C, 127mm², XLPE/PVC, Type W2",        "EL-LV-02-0001", 75384,  "127mm²","LM"),
    (12, "0.6/1kV, 1C, AL, 127mm², XLPE/PVC, Type W2",    "EL-LV-02-0001", 8435,   "127mm²","LM"),
    (13, "0.6/1kV, 1C, 185mm², XLPE/PVC, Type W2",        "EL-LV-02-0002", 26398,  "185mm²","LM"),
    (14, "0.6/1kV, 1C, AL, 185mm², XLPE/PVC, Type W2",    "EL-LV-02-0002", 1426,   "185mm²","LM"),
    (15, "0.6/1kV, 1C, 240mm², XLPE/PVC, Type W2",        "EL-LV-02-0002", 834475, "240mm²","LM"),
    (16, "0.6/1kV, 1C, AL, 240mm², XLPE/PVC, Type W2",    "EL-LV-02-0002", 13622,  "240mm²","LM"),
    (17, "0.6/1kV, 1C, 400mm², XLPE/PVC, Type W2",        "EL-LV-02-0003", 16367,  "400mm²","LM"),
    (19, "0.6/1kV, 3C+E, AL, 127mm², SWA/PVC Cable",      "EL-LV-03-0001", 14582,  "127mm²","LM"),
    (20, "0.6/1kV, 3C+E, AL, 240mm², SWA/PVC Cable",      "EL-LV-03-0001", 9825,   "240mm²","LM"),
    (22, "0.6/1kV, 3C+E, 4mm², XLPE/PVC, Type M1",        "EL-LV-04-0001", 15017,  "4mm²",  "LM"),
    (23, "0.6/1kV, 3C+E, 6mm², XLPE/PVC, Type M1",        "EL-LV-04-0001", 41145,  "6mm²",  "LM"),
    (25, "0.6/1kV, 3C+E, 16mm², XLPE/PVC, Type M1",       "EL-LV-04-0002", 13246,  "16mm²", "LM"),
    (27, "0.6/1kV, 3C+E, 25mm², XLPE/PVC, Type M1",       "EL-LV-04-0002", 32666,  "25mm²", "LM"),
    (30, "0.6/1kV, 3C+E, 50mm², XLPE/PVC, Type M1",       "EL-LV-04-0002", 19466,  "50mm²", "LM"),
    (33, "0.6/1kV, 3C+E, 70mm², XLPE/PVC, Type M1",       "EL-LV-04-0003", 4910,   "70mm²", "LM"),
    (42, "0.6/1kV, 1C, 50mm², G/Y Earth Cable, Type E1",  "EL-LV-01-0003", 24864,  "50mm²", "LM"),
    (43, "0.6/1kV, 1C, 70mm², G/Y Earth Cable, Type E1",  "EL-LV-01-0003", 106992, "70mm²", "LM"),
    (44, "Earth Wire, 70mm², Green PVC Insulated",         "EL-LV-05-0001", 107695, "70mm²", "LM"),
    (45, "0.6/1kV, 1C, 50mm², G/Y Earth Cable, Type E2",  "EL-LV-01-0002", 4800,   "50mm²", "LM"),
    (46, "0.6/1kV, 1C, 25mm², G/Y Earth Cable, Type E2",  "EL-LV-01-0002", 3463,   "25mm²", "LM"),
]

# Unit prices per bidder [A, B, C, D, E, F] — UNCHANGED
UNIT_PRICES = {
    6:  [0.36, 0.34, 0.36, 0.37, 0.37, 0.42],
    7:  [0.53, 0.83, 0.95, 1.06, 0.96, 0.96],
    8:  [0.37, 0.39, 0.51, 0.42, 0.52, 0.58],
    9:  [1.68, 3.20, 3.07, 3.11, 3.11, 3.83],
    10: [0.95, 0.59, 0.80, 0.67, 0.80, 0.90],
    11: [7.52, 6.88, 7.14, 7.22, 7.21, 8.20],
    12: [1.60, 1.20, 1.59, 1.87, 1.60, 1.78],
    13: [10.41, 10.50, 9.91, 10.02, 10.03, 10.95],
    14: [2.24, 1.69, 2.22, 1.88, 3.11, 2.51],
    15: [13.55, 14.08, 13.94, 14.10, 14.09, 14.89],
    16: [2.90, 2.18, 2.86, 2.14, 2.89, 3.24],
    17: [21.21, 24.07, 26.16, 23.50, 26.44, 23.64],
    19: [7.17, 6.37, 12.17, 7.23, 12.30, 19.74],
    20: [16.60, 10.36, 21.18, 10.19, 21.40, 36.80],
    22: [1.24, 0.85, 1.30, 1.24, 1.31, 2.49],
    23: [1.81, 1.26, 1.69, 1.71, 1.71, 3.67],
    25: [3.94, 2.89, 3.34, 3.75, 3.74, 3.96],
    27: [6.29, 5.54, 6.72, 6.80, 6.80, 7.86],
    30: [10.85, 8.05, 10.09, 10.20, 10.19, 9.91],
    33: [15.43, 11.74, 14.62, 15.08, 15.33, 15.18],
    42: [3.25, 3.20, 3.07, 3.11, 3.11, 3.83],
    43: [4.16, 3.79, 3.95, 4.00, 3.99, 4.66],
    44: [3.45, 3.65, 3.95, 3.43, 3.99, 1.05],
    45: [2.42, 2.48, 2.56, 2.59, 2.60, 3.10],
    46: [1.46, 1.41, 1.43, 1.44, 1.59, 1.52],
}

# Anonymous vendor names
VENDOR_NAMES = [
    "Vendor Alpha Pty Ltd",
    "Vendor Beta Corporation",
    "Vendor Gamma Supply Co.",
    "Vendor Delta Trading",
    "Vendor Epsilon Industries",
    "Vendor Zeta Holdings",
]

# ── Styles ─────────────────────────────────────────────────────────────────────
NAVY   = "0A1628"
TEAL   = "00D4AA"
HEADER = "0D2137"
LIGHT  = "C9D1D9"
WHITE  = "FFFFFF"
YELLOW = "FFF2CC"
GREEN  = "E2EFDA"

def hdr_font(bold=True, color=WHITE, size=10):
    return Font(bold=bold, color=color, size=size)

def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def border():
    thin = Side(style="thin", color="D0D0D0")
    return Border(left=thin, right=thin, top=thin, bottom=thin)

def center():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def left():
    return Alignment(horizontal="left", vertical="center", wrap_text=True)


# ── Build workbook ─────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "QCS - Project Alpha"

# ── Row 1: Project banner ──────────────────────────────────────────────────────
ws.merge_cells("A1:T1")
c = ws["A1"]
c.value = "PROJECT ALPHA — LV POWER CABLE SUPPLY  |  QUOTE COMPARISON SHEET"
c.font = Font(bold=True, color=WHITE, size=13)
c.fill = fill(NAVY)
c.alignment = center()
ws.row_dimensions[1].height = 28

# ── Row 2: Column group labels (with BIDDER 1 … BIDDER 6) ─────────────────────
ws.row_dimensions[2].height = 22
labels_row2 = [
    "Item No.", "Description", "Spec Code", "Qty", "Size", "Unit",
    "BIDDER 1", "", "",
    "BIDDER 2", "", "",
    "BIDDER 3", "", "",
    "BIDDER 4", "", "",
    "BIDDER 5", "", "",
    "BIDDER 6", "", "",
]
for col, val in enumerate(labels_row2, 1):
    c = ws.cell(row=2, column=col, value=val)
    c.font = hdr_font(color=TEAL if val.startswith("BIDDER") else LIGHT)
    c.fill = fill(HEADER)
    c.alignment = center()
    c.border = border()

# ── Row 3: Vendor legal names ──────────────────────────────────────────────────
ws.row_dimensions[3].height = 20
vendor_row = ["", "", "", "", "", ""] + [
    name for name in VENDOR_NAMES for _ in range(3)
]
for col, val in enumerate(vendor_row, 1):
    c = ws.cell(row=3, column=col, value=val)
    c.font = Font(italic=True, color=LIGHT, size=9)
    c.fill = fill(HEADER)
    c.alignment = center()
    c.border = border()

# Merge vendor name cells per bidder (3 cols each)
for b in range(6):
    start_col = 7 + b * 3
    ws.merge_cells(
        start_row=3, start_column=start_col,
        end_row=3, end_column=start_col + 2
    )
    ws.cell(row=3, column=start_col).value = VENDOR_NAMES[b]

# ── Row 4: "Pricing Breakdown" section marker ──────────────────────────────────
ws.merge_cells("A4:T4")
c = ws["A4"]
c.value = "Pricing Breakdown"
c.font = Font(bold=True, color=WHITE, size=10)
c.fill = fill("1A3A5C")
c.alignment = left()
ws.row_dimensions[4].height = 18

# ── Row 4b: Sub-header (Unit Price / Definition / Total Price per bidder) ───────
sub_row = ["", "", "", "", "", ""] + [
    val for _ in range(6) for val in ["Unit Price", "Definition", "Total Price"]
]
for col, val in enumerate(sub_row, 1):
    c = ws.cell(row=5, column=col, value=val)
    c.font = Font(bold=True, color=LIGHT, size=8)
    c.fill = fill("0D2137")
    c.alignment = center()
    c.border = border()
ws.row_dimensions[5].height = 16

# ── Data rows (starting row 6) ────────────────────────────────────────────────
ROW_OFFSET = 6

for r_idx, (item_no, desc, spec, qty, size_note, unit) in enumerate(ITEMS):
    row = ROW_OFFSET + r_idx
    ws.row_dimensions[row].height = 16

    prices = UNIT_PRICES.get(item_no, [None] * 6)

    # Fixed columns
    data = [item_no, desc, spec, qty, size_note, unit]
    bg = GREEN if r_idx % 2 == 0 else WHITE

    for col, val in enumerate(data, 1):
        c = ws.cell(row=row, column=col, value=val)
        c.font = Font(size=9, color="1A1A2E")
        c.fill = fill(bg[1:] if bg.startswith("#") else bg)
        c.border = border()
        c.alignment = left() if col == 2 else center()

    # Bidder price columns
    for b_idx, up in enumerate(prices):
        col_start = 7 + b_idx * 3
        tp = round(up * qty, 2) if up is not None else None

        for sub, val in enumerate([up, "COST", tp]):
            c = ws.cell(row=row, column=col_start + sub, value=val)
            c.font = Font(size=9, color="1A1A2E")
            c.fill = fill(bg[1:] if bg.startswith("#") else bg)
            c.border = border()
            c.alignment = center()
            if sub in (0, 2) and val is not None:
                c.number_format = "#,##0.00"

# ── Column widths ──────────────────────────────────────────────────────────────
col_widths = {
    1: 8,    # Item No
    2: 42,   # Description
    3: 14,   # Spec Code
    4: 10,   # Qty
    5: 8,    # Size
    6: 6,    # Unit
}
for b in range(6):
    base = 7 + b * 3
    col_widths[base]     = 11  # Unit Price
    col_widths[base + 1] = 9   # Definition
    col_widths[base + 2] = 13  # Total Price

for col_idx, width in col_widths.items():
    ws.column_dimensions[get_column_letter(col_idx)].width = width

# Freeze panes below sub-header, after unit column
ws.freeze_panes = "G6"

# ── Totals row ────────────────────────────────────────────────────────────────
total_row = ROW_OFFSET + len(ITEMS)
ws.row_dimensions[total_row].height = 18

ws.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True, size=10, color=WHITE)
ws.cell(row=total_row, column=1).fill = fill(NAVY)
ws.cell(row=total_row, column=1).alignment = center()

for col in range(2, 7):
    c = ws.cell(row=total_row, column=col)
    c.fill = fill(NAVY)
    c.border = border()

for b_idx in range(6):
    col_start = 7 + b_idx * 3
    prices_b = [
        round(UNIT_PRICES[item[0]][b_idx] * item[3], 2)
        for item in ITEMS
        if UNIT_PRICES.get(item[0], [None]*6)[b_idx] is not None
    ]
    total = sum(prices_b)

    for sub in range(3):
        c = ws.cell(row=total_row, column=col_start + sub)
        c.fill = fill(NAVY)
        c.border = border()

    total_cell = ws.cell(row=total_row, column=col_start + 2, value=total)
    total_cell.font = Font(bold=True, color=TEAL, size=10)
    total_cell.fill = fill(NAVY)
    total_cell.alignment = center()
    total_cell.number_format = "#,##0.00"
    total_cell.border = border()

# ── Save ──────────────────────────────────────────────────────────────────────
out = "project_alpha_qcs.xlsx"
wb.save(out)
print(f"Generated: {out}  ({len(ITEMS)} items, 6 bidders)")
print("Totals per bidder:")
for b_idx, name in enumerate(["A","B","C","D","E","F"]):
    t = sum(
        round(UNIT_PRICES[item[0]][b_idx] * item[3], 2)
        for item in ITEMS
        if UNIT_PRICES.get(item[0], [None]*6)[b_idx] is not None
    )
    print(f"  Bidder {name} ({VENDOR_NAMES[b_idx][:20]}): ${t:>14,.2f}")
