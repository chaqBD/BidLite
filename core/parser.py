"""
Parses Quote Comparison Sheet (QCS) files — Excel or PDF — into a
normalized list of bid line items ready for embedding and analysis.
"""

import re
import pandas as pd
import pdfplumber
from io import BytesIO
from typing import Optional


BIDDER_COLS = ["A", "B", "C", "D", "E", "F"]


def parse_excel(file: BytesIO) -> pd.DataFrame:
    """Read a QCS Excel workbook and return a normalized DataFrame."""
    xl = pd.ExcelFile(file)
    sheet = xl.sheet_names[0]
    raw = pd.read_excel(file, sheet_name=sheet, header=None)
    return _normalize_raw(raw)


def parse_pdf_text(file: BytesIO) -> pd.DataFrame:
    """Extract line items from a QCS PDF via pdfplumber."""
    rows = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    rows.append(row)
    raw = pd.DataFrame(rows)
    return _normalize_raw(raw)


def _normalize_raw(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristically locate the pricing rows in a raw QCS sheet and return
    a tidy DataFrame with columns:
      item_no, description, spec_code, qty, unit,
      bidder, unit_price, total_price, definition
    """
    records = []

    # Detect header row by searching for "BIDDER 1" or "Bidder Legal Name"
    header_row_idx = None
    for i, row in raw.iterrows():
        row_str = " ".join(str(v) for v in row.values if pd.notna(v))
        if "BIDDER 1" in row_str or "Bidder Legal Name" in row_str:
            header_row_idx = i
            break

    # Detect pricing section by searching for "Pricing Breakdown"
    pricing_start = None
    for i, row in raw.iterrows():
        row_str = " ".join(str(v) for v in row.values if pd.notna(v))
        if "Pricing Breakdown" in row_str:
            pricing_start = i + 1
            break

    if pricing_start is None:
        return pd.DataFrame()

    for i in range(pricing_start, len(raw)):
        row = raw.iloc[i]
        vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]

        # Rows with a numeric item number in col 0 are line items
        item_no_str = vals[0] if vals else ""
        if not re.match(r"^\d+$", item_no_str):
            continue

        item_no = int(item_no_str)
        description = vals[1] if len(vals) > 1 else ""
        spec_code = vals[2] if len(vals) > 2 else ""

        # Qty is typically in col 3; unit in col 5
        try:
            qty = float(re.sub(r"[,$]", "", vals[3])) if vals[3] else None
        except ValueError:
            qty = None
        unit = vals[5] if len(vals) > 5 else ""

        # Each bidder block has: unit_price, definition, total_price
        # Offsets vary by template; we scan pairs of numeric columns after col 5
        bidder_offset_start = 6
        cols_per_bidder = 3  # unit_price, definition, total_price

        for b_idx, bidder in enumerate(BIDDER_COLS):
            offset = bidder_offset_start + b_idx * cols_per_bidder
            if offset + 2 >= len(vals):
                break
            raw_up = re.sub(r"[,$\s]", "", vals[offset])
            raw_tp = re.sub(r"[,$\s]", "", vals[offset + 2])
            definition = vals[offset + 1]

            try:
                unit_price = float(raw_up) if raw_up else None
            except ValueError:
                unit_price = None
            try:
                total_price = float(raw_tp) if raw_tp else None
            except ValueError:
                total_price = None

            records.append({
                "item_no": item_no,
                "description": description,
                "spec_code": spec_code,
                "qty": qty,
                "unit": unit,
                "bidder": bidder,
                "unit_price": unit_price,
                "total_price": total_price,
                "definition": definition,
            })

    return pd.DataFrame(records)


def load_sample_data() -> pd.DataFrame:
    """
    Hard-coded sample data extracted from the Project Bimbi QCS PDF
    covering LV cable line items for all 6 bidders.
    """
    items = [
        # (item_no, description, spec_code, qty, unit)
        (6,  "600V, 1C, #10 AWG, FR-XLPE, XHHW-2",        "81.09.02.004", 186660, "LF"),
        (7,  "600V, 1C, #6 AWG, FR-XLPE, XHHW-2",          "81.09.02.006", 242,    "LF"),
        (8,  "600V, 1C, AL, #2 AWG, FR-XLPE, XHHW-2",      "81.09.02.006", 356,    "LF"),
        (9,  "600V, 1C, #1/0 AWG, FR-XLPE, XHHW-2",        "81.09.02.008", 242,    "LF"),
        (10, "600V, 1C, AL, #1/0 AWG, FR-XLPE, XHHW-2",    "81.09.02.008", 3032,   "LF"),
        (11, "600V, 1C, 250 KCMIL, FR-XLPE, XHHW-2",       "81.09.04.002", 75384,  "LF"),
        (12, "600V, 1C, AL, 250 KCMIL, FR-XLPE, XHHW-2",   "81.09.04.002", 8435,   "LF"),
        (13, "600V, 1C, 350 KCMIL, FR-XLPE, XHHW-2",       "81.09.04.004", 26398,  "LF"),
        (14, "600V, 1C, AL, 350 KCMIL, FR-XLPE, XHHW-2",   "81.09.04.004", 1426,   "LF"),
        (15, "600V, 1C, 500 KCMIL, FR-XLPE, XHHW-2",       "81.09.04.004", 834475, "LF"),
        (16, "600V, 1C, AL, 500 KCMIL, FR-XLPE, XHHW-2",   "81.09.04.004", 13622,  "LF"),
        (17, "600V, 1C, 750 KCMIL, FR-XLPE, XHHW-2",       "81.09.04.006", 16367,  "LF"),
        (19, "600V, 3C w/Gnd, AL, 250 kcmil, Armored",     "81.09.10.022", 14582,  "LF"),
        (20, "600V, 3C w/Gnd, AL, 500 kcmil, Armored",     "81.09.10.022", 9825,   "LF"),
        (22, "600V, 3C w/Gnd, #12 AWG, FR-XLPE/PVC",       "81.09.06.002", 15017,  "LF"),
        (23, "600V, 3C w/Gnd, #10 AWG, XLPE/PVC",          "81.09.06.002", 41145,  "LF"),
        (25, "600V, 3C w/Gnd, #6 AWG, FR-XLPE/PVC",        "81.09.06.004", 13246,  "LF"),
        (27, "600V, 3C w/Gnd, #3 AWG, FR-XLPE/PVC",        "81.09.06.004", 32666,  "LF"),
        (30, "600V, 3C w/Gnd, #1 AWG, FR-XLPE/PVC",        "81.09.06.004", 19466,  "LF"),
        (33, "600V, 3C w/Gnd, #2/0 AWG, XLPE/PVC",         "81.09.06.006", 4910,   "LF"),
        (42, "600V, 1/C, #1/0 AWG, XLPE XHHW-2 Ground",    "81.09.02.008", 24864,  "LF"),
        (43, "600V, 1/C, #2/0 AWG, XLPE XHHW-2 Ground",    "81.09.02.008", 106992, "LF"),
        (44, "Ground Wire, 2/0 Green Insulated THHN",       "81.30.04.002", 107695, "LF"),
        (45, "600V, 1/C, #1 AWG, XLPE XHHW-2 Ground",      "81.09.02.006", 4800,   "LF"),
        (46, "600V, 1/C, #4 AWG, XLPE XHHW-2 Ground",      "81.09.02.006", 3463,   "LF"),
    ]

    # unit prices per bidder [A, B, C, D, E, F]
    unit_prices = {
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

    records = []
    for item_no, desc, spec, qty, unit in items:
        prices = unit_prices.get(item_no, [None] * 6)
        for b_idx, bidder in enumerate(BIDDER_COLS):
            up = prices[b_idx]
            tp = round(up * qty, 2) if up is not None and qty else None
            records.append({
                "item_no": item_no,
                "description": desc,
                "spec_code": spec,
                "qty": qty,
                "unit": unit,
                "bidder": bidder,
                "unit_price": up,
                "total_price": tp,
                "definition": "COST",
            })

    return pd.DataFrame(records)
