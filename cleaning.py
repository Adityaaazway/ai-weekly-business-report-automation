import os
import re
import pandas as pd
import numpy as np

# This is what clean data must contain
REQUIRED_COLUMNS = [
    "date",
    "channel",
    "orders",
    "revenue",
    "new_customers",
    "returning_customers",
    "top_product_sku",
    "top_product_revenue"
]

VALID_CHANNELS = ["Website", "Amazon", "Instagram"]

# Any known typo/variant -> correct name
CHANNEL_CORRECTIONS = {
    "website": "Website",
    "websit": "Website",
    "WEBSITE": "Website",
    "amazon": "Amazon",
    "amazn": "Amazon",
    "AMAZON": "Amazon",
    "instagram": "Instagram",
    "INSTAGRAM": "Instagram",
    "instagarm": "Instagram",
    "insta": "Instagram",
}


def parse_date_flexibly(val):
    """
    Try to parse any date string into a proper datetime.
    Returns NaT if parsing fails completely.
    """
    if pd.isnull(val) or str(val).strip() == "":
        return pd.NaT

    try:
        return pd.to_datetime(str(val), dayfirst=False, errors="coerce")
    except Exception:
        return pd.NaT


def clean_channel(val):
    """
    Standardize channel names.
    Unknown channels are kept but flagged.
    """
    if pd.isnull(val) or str(val).strip() == "":
        return "UNKNOWN"

    val_stripped = str(val).strip()

    if val_stripped in CHANNEL_CORRECTIONS:
        return CHANNEL_CORRECTIONS[val_stripped]

    title_val = val_stripped.title()
    if title_val in VALID_CHANNELS:
        return title_val

    return f"UNKNOWN({val_stripped})"


def clean_numeric(val, col_name, idx, cleaning_log):
    """
    Strip currency symbols and commas, convert to float.
    Negative values and blanks are treated as 0.
    """
    if pd.isnull(val) or str(val).strip() == "":
        cleaning_log.append({
            "row": idx,
            "column": col_name,
            "issue": "Missing value",
            "original": val,
            "action": "Filled with 0"
        })
        return 0.0

    # Remove ₹, $, commas, spaces
    cleaned = re.sub(r"[₹$,\s]", "", str(val))

    try:
        num = float(cleaned)
    except ValueError:
        cleaning_log.append({
            "row": idx,
            "column": col_name,
            "issue": f"Cannot convert '{val}' to number",
            "original": val,
            "action": "Filled with 0"
        })
        return 0.0

    if num < 0:
        cleaning_log.append({
            "row": idx,
            "column": col_name,
            "issue": f"Negative value ({num})",
            "original": val,
            "action": "Replaced with 0"
        })
        return 0.0

    return num


def clean_data(df_raw, save_output=True, output_path="data/cleaned_data.csv"):
    """
    Main cleaning function.
    Input: raw dataframe
    Output: cleaned dataframe, cleaning log dataframe
    """
    cleaning_log = []

    # Schema check
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df_raw.columns]
    if missing_cols:
        raise ValueError(f"SCHEMA ERROR: These required columns are missing: {missing_cols}")

    df = df_raw.copy()

    # ---------------- Date cleaning ----------------
    original_dates = df["date"].copy()
    df["date"] = df["date"].apply(parse_date_flexibly)

    unparseable = df[df["date"].isna()].index.tolist()
    for idx in unparseable:
        cleaning_log.append({
            "row": idx,
            "column": "date",
            "issue": "Could not parse date",
            "original": original_dates.iloc[idx],
            "action": "Dropped row"
        })

    df = df.dropna(subset=["date"]).reset_index(drop=True)

    today = pd.Timestamp.today().normalize()
    future_mask = df["date"] > today
    future_rows = df[future_mask].index.tolist()

    for idx in future_rows:
        cleaning_log.append({
            "row": idx,
            "column": "date",
            "issue": "Future date detected",
            "original": df.at[idx, "date"],
            "action": "Dropped row"
        })

    df = df[~future_mask].reset_index(drop=True)

    # ---------------- Channel cleaning ----------------
    original_channels = df["channel"].copy()
    df["channel"] = df["channel"].apply(clean_channel)

    changed_mask = original_channels.values != df["channel"].values
    for idx in df[changed_mask].index:
        cleaning_log.append({
            "row": idx,
            "column": "channel",
            "issue": "Channel name corrected",
            "original": original_channels.iloc[idx],
            "action": f"Changed to '{df.at[idx, 'channel']}'"
        })

    # ---------------- Numeric cleaning ----------------
    numeric_columns = [
        "orders",
        "revenue",
        "new_customers",
        "returning_customers",
        "top_product_revenue"
    ]

    for col in numeric_columns:
        df[col] = [clean_numeric(df.at[i, col], col, i, cleaning_log) for i in range(len(df))]

    for col in ["orders", "new_customers", "returning_customers"]:
        df[col] = df[col].astype(int)

    # ---------------- Duplicate removal ----------------
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["date", "channel"], keep="first").reset_index(drop=True)
    dupes_removed = before_dedup - len(df)

    if dupes_removed > 0:
        cleaning_log.append({
            "row": "multiple",
            "column": "date+channel",
            "issue": f"{dupes_removed} duplicate rows found",
            "original": "duplicate",
            "action": "Kept first, removed rest"
        })

    # ---------------- Missing SKU fix ----------------
    sku_missing = (
        df["top_product_sku"].isin(["", None, np.nan]) |
        df["top_product_sku"].astype(str).str.strip().eq("")
    )

    df.loc[sku_missing, "top_product_sku"] = "UNKNOWN_SKU"
    df.loc[sku_missing, "top_product_revenue"] = 0.0

    # ---------------- Final report ----------------
    log_df = pd.DataFrame(cleaning_log)

    print("=" * 55)
    print("DATA CLEANING REPORT")
    print("=" * 55)
    print(f"Raw rows received : {df_raw.shape[0]}")
    print(f"Clean rows output : {len(df)}")
    print(f"Total fixes applied : {len(cleaning_log)}")
    print("=" * 55)

    if len(log_df) > 0:
        summary = log_df.groupby("issue").size().reset_index(name="count")
        print("\nIssues fixed by type:")
        for _, row in summary.iterrows():
            print(f" - {row['issue']:<35} {row['count']} occurrence(s)")

    print("\nCleaned DataFrame sample:")
    print(df.head(3).to_string())
    print(f"\nFinal shape: {df.shape}")

    # Save cleaned CSV
        # Save cleaned CSV only as an optional artifact
    if save_output:
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            df.to_csv(output_path, index=False)
            print("\nCleaned data saved successfully.")
            print(f"File path: {output_path}")
            print(f"Rows saved: {len(df)}")
        except Exception as e:
            print("\nWARNING: Cleaned CSV could not be saved.")
            print(type(e).__name__, str(e))
            print("Continuing pipeline without saving cleaned CSV.")

    return df, log_df
    