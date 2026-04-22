"""
preprocessing_pipeline.py
==========================
Krishna Dairy — Complete Preprocessing Pipeline
Designed to run on every new XLS file upload via FastAPI.

Pipeline Steps:
  1. Accept uploaded XLS (multi-sheet) → merge all sheets → single DataFrame
  2. Map PRODDESC: Akruti garbled Marathi font → English product names
  3. Keep required fields, clean & standardize data
  4. Integrate festival calendar (merge on date)
  5. Save final CSV with absolute output path

Usage (standalone):
    python preprocessing_pipeline.py \
        --input  /absolute/path/to/upload.xls \
        --festivals /absolute/path/to/all_festivals.csv \
        --output /absolute/path/to/final_output.csv

FastAPI usage:
    from preprocessing_pipeline import run_pipeline, PipelineResult
    result: PipelineResult = run_pipeline(
        xls_path="/absolute/path/upload.xls",
        festivals_path="/absolute/path/all_festivals.csv",
        output_path="/absolute/path/output.csv"
    )
"""

import os
import re
import sys
import argparse
import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("KrishnaDairyPipeline")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — edit these as needed
# ─────────────────────────────────────────────────────────────────────────────

# Columns to KEEP from the raw XLS (all others are dropped).
# DC_DATE and PRODDESC are mandatory; add/remove as needed.
REQUIRED_COLUMNS = ["DC_DATE", "PRODDESC", "DC_QTY_IN_UOM"]

# Columns to explicitly DROP if they appear (applied after keeping required cols)
COLUMNS_TO_DROP = ["DC_NO", "SUB_POS_NAME", "GSTIN", "HSN"]

# Final output column rename map
COLUMN_RENAME = {
    "DC_DATE":        "Date",
    "PRODDESC":       "Product",
    "DC_QTY_IN_UOM":  "Quantity",
}

# Festival CSV must have these two columns (case-insensitive)
FESTIVAL_DATE_COL     = "date"
FESTIVAL_NAME_COL     = "festival"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT MAP: Akruti-garbled Marathi font → English
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_MAP = {
    # Skimmed Milk Powder
    "òç¨îÙÀ òÙðâ¨î ÑððãðÀÜ (±ððÚð)":                       "Skimmed Milk Powder (Cow)",
    "òç¨îÙÀ òÙðâ¨î ÑððãðÀÜ (Ùèøçð)":                      "Skimmed Milk Powder (Buffalo)",

    # Butter
    "±ððÚð ×ð¾Ü  (Ç÷äðó âðð÷Âðó )":                        "Cow Butter (Desi Loni)",
    "±ððÚð ×ð¾Ü (Ç÷äðó âðð÷Âðó) ¦¨çðÑðð÷¾á":              "Cow Butter (Desi Loni) Export",
    "Ùèøçð ×ð¾Ü (Ç÷äðó âðð÷Âðó )":                         "Buffalo Butter (Desi Loni)",

    # Milk
    "Ñððäµð.Òôîâð òªîÙð òÙðâ¨î":                           "Past. Full Cream Milk",
    "òÑßÙðóÚðÙð (Ñððäµð.±ððÚð ÇõÏð)":                     "Premium (Past. Cow Milk)",
    "Ãðð¸ð±ðó (Ñððäµð.¾ð÷ÐÀ ÇõÏð)":                       "Taazgi (Past. Toned Milk)",
    "ÑððäµðÜðýá¸À ç¾ùÂÀÀá ÇõÏð":                           "Pasteurized Standard Milk",
    "èúÇóÚðô¨Ãð ¨îðÁð ç¾òÜâððÚð»ðÀ ÇõÏð":                "Homogenized Sterilized Milk",
    "Úðô¦µð¾ó ¾ð÷ÐÀ ÇõÏð ( ¾÷¾àð Ñðù¨î )":                "UHT Toned Milk (Tetra Pack)",

    # Cream
    "±ððÚð òªîÙð  (¨îµµð÷ ) î":                            "Cow Cream (Raw)",
    "Ùèøçð òªîÙð (¨îµµð÷ )":                                "Buffalo Cream (Raw)",
    "±ððÚð òªîÙð  (ÑððäµðÜðýá¸À )":                        "Cow Cream (Pasteurized)",

    # Ghee
    "çðð¸ðô¨î ( Ùèøçð ) ÃðõÑð":                            "Pure Ghee (Buffalo)",
    "±ððýáµð÷ ÃðõÑð":                                       "Cow Ghee",

    # Lassi
    "âðççðó":                                                "Lassi",
    "¨öîæÂðð âðççðó Ùðû±ðð÷":                               "Krishna Lassi Mango",

    # Paneer
    "ÑðÐðóÜ":                                                "Paneer",
    "ÑðÐðóÜ (LOW FAT)":                                     "Paneer (Low Fat)",

    # Curd / Buttermilk
    "Çèó ( ¨öîæÂðð )":                                      "Curd (Krishna)",
    "Ãðð¨î":                                                 "Buttermilk (Tak)",
    "ò¸ðÜð Ãðð¨î":                                          "Jeera Buttermilk (Tak)",

    # Shrikhand & Chakka
    "åó®ðüÀ  (×ðÇðÙð - òÑðçÃðð )":                         "Shrikhand (Badam-Pista)",
    "¡ðü×ðð   åóï®ðüÀ":                                     "Amba Shrikhand (Mango)",
    "åó®ðüÀ (×ð¾Üç¨îðùµð)":                                "Shrikhand (Butterscotch)",
    "µð¨¨îð":                                                "Chakka (Shrikhand Base)",

    # Basundi
    "×ððçðôüÇó":                                             "Basundi",
    "¨öîæÂðð ×ððçðôüÇó (òçðÃððÒîú Ü×ðÀó)":                "Krishna Basundi (Sitafal)",

    # Krishna Flavoured Milk (Thanda)
    "¨îöæÂðð Òâð÷ãðÀá òÙðâ¨":                              "Krishna Flavoured Milk",
    "ç¾àðù×ð÷Üó  ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨":          "Krishna Thanda Strawberry (Flavoured Milk)",
    "×ð¾Üç¨îðùµð   ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨":         "Krishna Thanda Butterscotch (Flavoured Milk)",
    "Ùðùû±ðð÷ ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨":              "Krishna Thanda Mango (Flavoured Milk)",
    "òÑðçÃðð ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨":               "Krishna Thanda Pista (Flavoured Milk)",
    "µððù¨îâð÷¾ ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨î )":         "Krishna Thanda Chocolate (Flavoured Milk)",
    "¨÷îçðÜ ýáâððÚðµðó ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨î )": "Krishna Thanda Kesar Elaichi (Flavoured Milk)",
    "ÑððÚðÐððÑðâð ¨îöæÂðð  ¿üÀð (Òâð÷ãðÀá òÙðâ¨î )":      "Krishna Thanda Pineapple (Flavoured Milk)",
    "¨îðùÒîó ¨îöæÂðð ¿üÀð (Òâð÷ãðÀá òÙðâ¨î )":            "Krishna Thanda Coffee (Flavoured Milk)",

    # Sweets & Desserts
    "¨öîæÂðð ®ðãðð":                                        "Krishna Khawa (Mawa)",
    "¨öîæÂðð ±ðôâðð×ð ¸ððÙðôÐð":                            "Krishna Gulab Jamun",
    "¨öîæÂðð ýÐçð¾ü¾ ±ðôâðð×ð ¸ððÙðôÐð òÙð¨çð":            "Krishna Instant Gulab Jamun Mix",
    "¨öîæÂðð ¨ôîâÑðó":                                      "Krishna Kulfi",
    "Ñð÷Áð":                                                 "Peda",
    "Ñð÷Áð (±ðôú)":                                         "Peda (Jaggery)",

    # Milk Powder
    "èð÷âð òÙðâ¨î ÑððãðÀÜ ( WMP )":                        "Whole Milk Powder (WMP)",

    # Other
    "SWEEP POWDER":                                          "Sweep Powder",
}


# ─────────────────────────────────────────────────────────────────────────────
# RETURN DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    success: bool
    output_path: str
    rows_input: int = 0
    rows_output: int = 0
    sheets_merged: int = 0
    unmapped_products: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs into one space and strip edges."""
    if not isinstance(text, str):
        return text
    return re.sub(r'\s+', ' ', text).strip()


def _translate_product(value: str, mapping: dict) -> str:
    """
    Map a single PRODDESC value to its English name.
    Tries: exact → whitespace-normalized → stripped → partial substring.
    Returns original value unchanged if no match found.
    """
    if not isinstance(value, str) or not value.strip():
        return value

    # Exact match
    if value in mapping:
        return mapping[value]

    # Normalized whitespace match
    normalized = _normalize_whitespace(value)
    if normalized in mapping:
        return mapping[normalized]

    # Stripped match
    stripped = value.strip()
    if stripped in mapping:
        return mapping[stripped]

    # Partial key-in-value match
    for key, translation in mapping.items():
        if key.strip() in value:
            return translation

    return value  # unmapped — will be flagged in report


def _is_garbled(value: str) -> bool:
    """
    Detect if a string still contains Akruti-garbled characters.
    These are high-codepoint Latin chars that appear when Akruti
    font data is read as Windows-1252 / Latin-1.
    """
    if not isinstance(value, str):
        return False
    garbled_chars = set(
        'òçÙðâÑãÀÜ±×ÇäÒôîÚÃàèåæéêëøùúûü÷ýþßÉÊËÌÍÎÏÐÓÔÕÖ'
        '¨öîæÂðçðôüÇó¸¡åï®ðüÀ¾ÜÑãñÝÙèøçµ³'
    )
    return any(c in garbled_chars for c in value)


def _resolve_path(path: str) -> str:
    """Convert any path to an absolute, normalized path."""
    return os.path.abspath(os.path.normpath(path))


def _validate_file_exists(path: str, label: str) -> None:
    """Raise FileNotFoundError with a clear message if file is missing."""
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{label} not found at path: '{path}'\n"
            f"  → Check the absolute path and ensure the file exists."
        )


def _ensure_output_dir(path: str) -> None:
    """Create parent directories for output path if they don't exist."""
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
        logger.info(f"  Created output directory: {parent}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Load XLS (multi-sheet) → single merged DataFrame
# ─────────────────────────────────────────────────────────────────────────────

def step1_load_and_merge_sheets(xls_path: str) -> tuple[pd.DataFrame, int]:
    """
    Read every sheet in the XLS file, add a 'source_sheet' column,
    and concatenate all sheets into one DataFrame.

    Returns:
        (merged_df, sheet_count)
    """
    logger.info("[ STEP 1 ] Loading XLS and merging all sheets...")
    logger.info(f"  File: {xls_path}")

    try:
        xls = pd.ExcelFile(xls_path, engine="xlrd")
    except Exception as e:
        raise ValueError(
            f"Failed to open XLS file: {e}\n"
            f"  → Ensure the file is a valid .xls or .xlsx format and not password-protected."
        )

    sheet_names = xls.sheet_names
    if not sheet_names:
        raise ValueError("The XLS file contains no sheets.")

    logger.info(f"  Found {len(sheet_names)} sheet(s): {sheet_names}")

    frames = []
    for sheet in sheet_names:
        try:
            df_sheet = xls.parse(sheet_name=sheet, header=0)
            # Strip column name whitespace immediately
            df_sheet.columns = df_sheet.columns.astype(str).str.strip()
            # Tag source sheet for traceability
            df_sheet["_source_sheet"] = sheet
            frames.append(df_sheet)
            logger.info(f"    Sheet '{sheet}': {len(df_sheet):,} rows  ×  {len(df_sheet.columns)} cols")
        except Exception as e:
            logger.warning(f"    Sheet '{sheet}': Could not read — {e}. Skipping.")

    if not frames:
        raise ValueError("No sheets could be read from the XLS file.")

    merged = pd.concat(frames, ignore_index=True, sort=False)
    logger.info(f"  Merged total: {len(merged):,} rows\n")
    return merged, len(frames)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Map PRODDESC — Akruti Marathi font → English
# ─────────────────────────────────────────────────────────────────────────────

def step2_map_products(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    Translate the PRODDESC column from garbled Akruti encoding to English
    product names using PRODUCT_MAP.

    Returns:
        (df_with_translated_products, list_of_unmapped_values)
    """
    logger.info("[ STEP 2 ] Mapping PRODDESC (Akruti Marathi font → English)...")

    if "PRODDESC" not in df.columns:
        logger.warning("  'PRODDESC' column not found — skipping product mapping.")
        return df, []

    original = df["PRODDESC"].copy()
    df["PRODDESC"] = df["PRODDESC"].apply(lambda x: _translate_product(x, PRODUCT_MAP))

    translated_count = (original != df["PRODDESC"]).sum()
    logger.info(f"  Successfully translated: {translated_count:,} rows")

    # Detect any still-garbled values
    unmapped_mask = df["PRODDESC"].apply(_is_garbled)
    unmapped_values = []

    if unmapped_mask.any():
        unmapped_series = df.loc[unmapped_mask, "PRODDESC"].value_counts()
        unmapped_values = list(unmapped_series.index)
        logger.warning(f"  [WARNING] {unmapped_mask.sum():,} rows still have unmapped/garbled PRODDESC.")
        logger.warning("  Add these keys to PRODUCT_MAP and re-run:")
        for val, cnt in unmapped_series.items():
            logger.warning(f"    {cnt:6,}x  {repr(val)}")
    else:
        logger.info("  All PRODDESC values successfully mapped.")

    logger.info("")
    return df, unmapped_values


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Keep required fields, clean & standardize
# ─────────────────────────────────────────────────────────────────────────────

def step3_clean_and_standardize(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    - Drop explicitly unwanted columns
    - Keep only required columns (REQUIRED_COLUMNS)
    - Strip whitespace from all string columns
    - Parse DC_DATE → datetime (YYYY-MM-DD)
    - Cast DC_QTY_IN_UOM → numeric
    - Drop fully null rows and duplicate rows
    - Rename columns to clean names (Date, Product, Quantity)
    - Sort by Date

    Returns:
        (cleaned_df, list_of_warnings)
    """
    logger.info("[ STEP 3 ] Cleaning and standardizing data...")
    warnings = []

    # --- 3a: Drop explicitly unwanted columns ---
    cols_dropped = [c for c in COLUMNS_TO_DROP if c in df.columns]
    if cols_dropped:
        df.drop(columns=cols_dropped, inplace=True)
        logger.info(f"  3a. Dropped unwanted cols: {cols_dropped}")
    else:
        logger.info("  3a. No explicitly unwanted columns found to drop.")

    # --- 3b: Keep only required columns ---
    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_required:
        msg = f"Required columns missing from data: {missing_required}"
        warnings.append(msg)
        logger.warning(f"  3b. WARNING — {msg}")

    available_required = [c for c in REQUIRED_COLUMNS if c in df.columns]
    # Always keep _source_sheet for traceability (will drop before final save)
    keep_cols = available_required + (["_source_sheet"] if "_source_sheet" in df.columns else [])
    df = df[keep_cols].copy()
    logger.info(f"  3b. Kept columns: {available_required}")

    # --- 3c: Strip whitespace from all string columns ---
    str_cols = df.select_dtypes(include="object").columns.tolist()
    for col in str_cols:
        df[col] = df[col].apply(lambda x: _normalize_whitespace(x) if isinstance(x, str) else x)
    logger.info(f"  3c. Whitespace stripped from {len(str_cols)} text column(s).")

    # --- 3d: Parse DC_DATE ---
    if "DC_DATE" in df.columns:
        pre_nulls = df["DC_DATE"].isna().sum()
        df["DC_DATE"] = pd.to_datetime(df["DC_DATE"], infer_datetime_format=True, errors="coerce")
        post_nulls = df["DC_DATE"].isna().sum()
        failed_dates = post_nulls - pre_nulls

        if failed_dates > 0:
            msg = f"{failed_dates:,} rows had unparseable dates and were set to NaT."
            warnings.append(msg)
            logger.warning(f"  3d. WARNING — {msg}")
            # Drop rows where date could not be parsed
            df.dropna(subset=["DC_DATE"], inplace=True)
            logger.warning(f"       Dropped {failed_dates:,} rows with invalid dates.")
        else:
            logger.info(f"  3d. DC_DATE parsed: {df['DC_DATE'].notna().sum():,} rows OK.")

        date_min = df["DC_DATE"].min().date() if not df["DC_DATE"].isna().all() else "N/A"
        date_max = df["DC_DATE"].max().date() if not df["DC_DATE"].isna().all() else "N/A"
        logger.info(f"       Date range: {date_min} → {date_max}")

    # --- 3e: Cast Quantity to numeric ---
    if "DC_QTY_IN_UOM" in df.columns:
        pre_count = len(df)
        df["DC_QTY_IN_UOM"] = pd.to_numeric(df["DC_QTY_IN_UOM"], errors="coerce")
        null_qty = df["DC_QTY_IN_UOM"].isna().sum()
        if null_qty > 0:
            msg = f"{null_qty:,} rows had non-numeric Quantity values — set to NaN."
            warnings.append(msg)
            logger.warning(f"  3e. WARNING — {msg}")
        logger.info(f"  3e. Quantity column cast to numeric. "
                    f"Range: {df['DC_QTY_IN_UOM'].min():.2f} – {df['DC_QTY_IN_UOM'].max():.2f}")

    # --- 3f: Drop fully null rows ---
    rows_before = len(df)
    df.dropna(how="all", inplace=True)
    rows_after = len(df)
    if rows_before - rows_after > 0:
        logger.info(f"  3f. Dropped {rows_before - rows_after:,} fully empty rows.")

    # --- 3g: Drop duplicate rows ---
    rows_before = len(df)
    df.drop_duplicates(inplace=True)
    dupes_removed = rows_before - len(df)
    logger.info(f"  3g. Removed {dupes_removed:,} duplicate rows.")

    # --- 3h: Aggregate to daily per-product totals ---
    # This is essential for time-series forecasting
    rows_before_agg = len(df)
    qty_col = "DC_QTY_IN_UOM" if "DC_QTY_IN_UOM" in df.columns else None

    if "DC_DATE" in df.columns and "PRODDESC" in df.columns and qty_col:
        pre_total = df[qty_col].sum()
        df = (
            df.groupby(["DC_DATE", "PRODDESC"], as_index=False)[qty_col]
            .sum()
        )
        post_total = df[qty_col].sum()
        if abs(pre_total - post_total) > 0.01:
            msg = f"Quantity total mismatch after aggregation: {pre_total:.2f} → {post_total:.2f}"
            warnings.append(msg)
            logger.warning(f"  3h. WARNING — {msg}")
        else:
            logger.info(f"  3h. Daily aggregation: {rows_before_agg:,} → {len(df):,} rows "
                        f"(Qty total preserved: {post_total:,.2f})")

    # --- 3i: Rename columns ---
    rename_map = {k: v for k, v in COLUMN_RENAME.items() if k in df.columns}
    df.rename(columns=rename_map, inplace=True)
    logger.info(f"  3i. Columns renamed: {rename_map}")

    # --- 3j: Sort by Date ---
    if "Date" in df.columns:
        df.sort_values("Date", ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        logger.info(f"  3j. Sorted {len(df):,} rows chronologically.")

    logger.info("")
    return df, warnings


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Integrate festival calendar
# ─────────────────────────────────────────────────────────────────────────────

def step4_merge_festivals(df: pd.DataFrame, festivals_path: str) -> pd.DataFrame:
    """
    Load the festival calendar CSV and left-join it onto the sales data by Date.
    Rows without a festival on that date will have Festival = "" (empty string).

    Festival CSV must have columns: 'date' and 'festival' (case-insensitive).
    """
    logger.info("[ STEP 4 ] Integrating festival calendar...")
    logger.info(f"  Festival CSV: {festivals_path}")

    # Load festival file
    try:
        fest = pd.read_csv(festivals_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        fest = pd.read_csv(festivals_path, encoding="latin-1", low_memory=False)
    except Exception as e:
        raise ValueError(f"Could not load festival CSV: {e}")

    # Normalize column names to lowercase for case-insensitive matching
    fest.columns = fest.columns.str.strip().str.lower()

    missing_fest_cols = []
    if FESTIVAL_DATE_COL not in fest.columns:
        missing_fest_cols.append(FESTIVAL_DATE_COL)
    if FESTIVAL_NAME_COL not in fest.columns:
        missing_fest_cols.append(FESTIVAL_NAME_COL)

    if missing_fest_cols:
        raise ValueError(
            f"Festival CSV is missing required columns: {missing_fest_cols}\n"
            f"  → Expected columns: '{FESTIVAL_DATE_COL}' and '{FESTIVAL_NAME_COL}'.\n"
            f"  → Found columns: {fest.columns.tolist()}"
        )

    # Keep only date and festival columns
    fest = fest[[FESTIVAL_DATE_COL, FESTIVAL_NAME_COL]].copy()

    # Clean festival column — replace 'null' text and strip whitespace
    fest[FESTIVAL_NAME_COL] = (
        fest[FESTIVAL_NAME_COL]
        .astype(str)
        .str.strip()
        .replace({"null": "", "nan": "", "None": ""})
    )

    # Parse dates
    fest[FESTIVAL_DATE_COL] = pd.to_datetime(fest[FESTIVAL_DATE_COL], errors="coerce")
    null_fest_dates = fest[FESTIVAL_DATE_COL].isna().sum()
    if null_fest_dates > 0:
        logger.warning(f"  {null_fest_dates:,} rows in festival CSV have invalid dates — dropped.")
        fest.dropna(subset=[FESTIVAL_DATE_COL], inplace=True)

    # Remove duplicate dates (keep first occurrence)
    before_dedup = len(fest)
    fest.drop_duplicates(subset=[FESTIVAL_DATE_COL], inplace=True)
    if before_dedup != len(fest):
        logger.warning(f"  Removed {before_dedup - len(fest):,} duplicate dates from festival calendar.")

    logger.info(f"  Festival calendar loaded: {len(fest):,} date entries.")
    fest_count = (fest[FESTIVAL_NAME_COL] != "").sum()
    logger.info(f"  Dates with a festival name: {fest_count:,}")

    # Rename festival date column to match sales 'Date' for merge
    fest.rename(columns={FESTIVAL_DATE_COL: "Date", FESTIVAL_NAME_COL: "Festival"}, inplace=True)

    # Left join: every sales row is kept; festival name added where date matches
    if "Date" not in df.columns:
        logger.warning("  'Date' column missing from sales data — skipping festival merge.")
        return df

    before_rows = len(df)
    df = pd.merge(df, fest, on="Date", how="left")

    if len(df) != before_rows:
        logger.warning(
            f"  Row count changed after merge: {before_rows:,} → {len(df):,}. "
            f"Check for duplicate dates in festival CSV."
        )

    # Fill missing festival values with empty string
    df["Festival"] = df["Festival"].fillna("").str.strip()

    matched = (df["Festival"] != "").sum()
    logger.info(f"  Rows matched to a festival: {matched:,} / {len(df):,}")
    logger.info("")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Save final output CSV
# ─────────────────────────────────────────────────────────────────────────────

def step5_save_output(df: pd.DataFrame, output_path: str) -> None:
    """
    Drop the internal traceability column (_source_sheet) if present,
    then save the final DataFrame to CSV with UTF-8-BOM encoding
    (opens correctly in Excel).
    """
    logger.info("[ STEP 5 ] Saving final output...")

    # Drop internal traceability column before saving
    if "_source_sheet" in df.columns:
        df.drop(columns=["_source_sheet"], inplace=True)

    # Format Date column as YYYY-MM-DD string for clean CSV output
    df_save = df.copy()
    if "Date" in df_save.columns:
        df_save["Date"] = pd.to_datetime(df_save["Date"]).dt.strftime("%Y-%m-%d")

    _ensure_output_dir(output_path)
    df_save.to_csv(output_path, index=False, encoding="utf-8-sig")

    file_size_kb = os.path.getsize(output_path) / 1024
    logger.info(f"  Saved: {output_path}")
    logger.info(f"  File size: {file_size_kb:.1f} KB")
    logger.info(f"  Final rows: {len(df_save):,}  |  Columns: {df_save.columns.tolist()}")
    logger.info("")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    xls_path: str,
    festivals_path: str,
    output_path: str,
) -> PipelineResult:
    """
    Run the full preprocessing pipeline.

    Args:
        xls_path      : Absolute path to the uploaded XLS sales file.
        festivals_path: Absolute path to the all_festivals.csv file.
        output_path   : Absolute path where the final processed CSV will be saved.

    Returns:
        PipelineResult dataclass with success flag, stats, warnings, and errors.
    """

    # Resolve all paths to absolute
    xls_path       = _resolve_path(xls_path)
    festivals_path = _resolve_path(festivals_path)
    output_path    = _resolve_path(output_path)

    logger.info("=" * 65)
    logger.info("  Krishna Dairy — Preprocessing Pipeline")
    logger.info("=" * 65)
    logger.info(f"  XLS Input      : {xls_path}")
    logger.info(f"  Festival CSV   : {festivals_path}")
    logger.info(f"  Output         : {output_path}")
    logger.info("=" * 65 + "\n")

    result = PipelineResult(success=False, output_path=output_path)

    try:
        # --- Validate inputs before processing ---
        _validate_file_exists(xls_path, "XLS sales file")
        _validate_file_exists(festivals_path, "Festival calendar CSV")

        # STEP 1: Load XLS + merge all sheets
        df, sheet_count = step1_load_and_merge_sheets(xls_path)
        result.rows_input   = len(df)
        result.sheets_merged = sheet_count

        # STEP 2: Map Marathi Akruti font → English product names
        df, unmapped = step2_map_products(df)
        result.unmapped_products = unmapped

        # STEP 3: Keep required fields, clean, standardize
        df, step3_warnings = step3_clean_and_standardize(df)
        result.warnings.extend(step3_warnings)

        # STEP 4: Merge festival calendar
        df = step4_merge_festivals(df, festivals_path)

        # STEP 5: Save final output
        step5_save_output(df, output_path)

        result.rows_output = len(df)
        result.success = True

        # ── Pipeline Summary ──────────────────────────────────────────────
        logger.info("=" * 65)
        logger.info("  PIPELINE COMPLETE ✓")
        logger.info("=" * 65)
        logger.info(f"  Sheets merged  : {result.sheets_merged}")
        logger.info(f"  Input rows     : {result.rows_input:,}")
        logger.info(f"  Output rows    : {result.rows_output:,}")
        logger.info(f"  Unmapped prods : {len(result.unmapped_products)}")
        logger.info(f"  Warnings       : {len(result.warnings)}")
        logger.info(f"  Output file    : {result.output_path}")
        logger.info("=" * 65 + "\n")

        if result.unmapped_products:
            logger.warning("  Unmapped product keys (add to PRODUCT_MAP):")
            for p in result.unmapped_products:
                logger.warning(f"    {repr(p)}")

    except FileNotFoundError as e:
        result.error = str(e)
        logger.error(f"\n[FILE NOT FOUND]\n{e}")
    except ValueError as e:
        result.error = str(e)
        logger.error(f"\n[VALUE ERROR]\n{e}")
    except Exception as e:
        result.error = f"Unexpected error: {type(e).__name__}: {e}"
        logger.exception(f"\n[UNEXPECTED ERROR]\n{result.error}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI INTEGRATION — paste into your FastAPI app
# ─────────────────────────────────────────────────────────────────────────────
"""
# ── fastapi_app.py ───────────────────────────────────────────────────────────

import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from preprocessing_pipeline import run_pipeline, PipelineResult

app = FastAPI(title="Krishna Dairy Preprocessing API")

# ── Absolute base paths — edit these for your server ─────────────────────────
BASE_DIR        = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR      = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR      = os.path.join(BASE_DIR, "outputs")
FESTIVALS_PATH  = os.path.join(BASE_DIR, "data", "all_festivals.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/preprocess", summary="Upload a sales XLS and run the full pipeline")
async def preprocess_sales_file(file: UploadFile = File(...)):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only .xls / .xlsx files are accepted.")

    # Save upload with a unique name to avoid collisions
    unique_id  = uuid.uuid4().hex[:8]
    xls_path   = os.path.join(UPLOAD_DIR, f"{unique_id}_{file.filename}")
    output_path = os.path.join(OUTPUT_DIR, f"{unique_id}_processed.csv")

    with open(xls_path, "wb") as f:
        content = await file.read()
        f.write(content)

    result: PipelineResult = run_pipeline(
        xls_path=xls_path,
        festivals_path=FESTIVALS_PATH,
        output_path=output_path,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "status":            "success",
        "output_file":       result.output_path,
        "sheets_merged":     result.sheets_merged,
        "rows_input":        result.rows_input,
        "rows_output":       result.rows_output,
        "unmapped_products": result.unmapped_products,
        "warnings":          result.warnings,
    }

@app.get("/download/{filename}", summary="Download a processed CSV")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path, media_type="text/csv", filename=filename)
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Krishna Dairy — Preprocessing Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input", required=True,
        help="Absolute path to the uploaded XLS sales file.\n"
             "Example: /data/uploads/sales_2024.xls"
    )
    parser.add_argument(
        "--festivals", required=True,
        help="Absolute path to the festival calendar CSV.\n"
             "Example: /data/all_festivals.csv"
    )
    parser.add_argument(
        "--output", required=True,
        help="Absolute path where the processed CSV will be saved.\n"
             "Example: /data/outputs/processed_2024.csv"
    )

    args = parser.parse_args()

    result = run_pipeline(
        xls_path=args.input,
        festivals_path=args.festivals,
        output_path=args.output,
    )

    sys.exit(0 if result.success else 1)