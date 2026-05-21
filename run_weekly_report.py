import json
import logging
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from cleaning import clean_data
from metrics import build_weekly_summary
from llm_client import generate_weekly_report
from email_client import send_email
from charts import generate_charts

# --- Load private settings from local config (not committed to GitHub) ---

try:
    from config_local import SERVICE_ACCOUNT_FILE, SHEET_ID, WORKSHEET_NAME
except ImportError:
    SERVICE_ACCOUNT_FILE = "YOUR_SERVICE_ACCOUNT_JSON_PATH_HERE"
    SHEET_ID = "YOUR_SHEET_ID_HERE"
    WORKSHEET_NAME = "YOUR_WORKSHEET_NAME_HERE"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# --- Logging setup ---

logging.basicConfig(
    filename="pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def load_raw_data():
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(WORKSHEET_NAME)
        records = worksheet.get_all_records()

        df_raw = pd.DataFrame(records)

        print(f"Raw data loaded: {df_raw.shape[0]} rows, {df_raw.shape[1]} columns")
        print(f"Columns: {df_raw.columns.tolist()}")

        logging.info(f"Raw data loaded successfully: {df_raw.shape[0]} rows, {df_raw.shape[1]} columns")

        return df_raw

    except Exception as e:
        print("CRITICAL ERROR: Could not load Google Sheet.")
        print(type(e).__name__, str(e))

        logging.exception("CRITICAL ERROR: Could not load Google Sheet.")
        raise


def main():
    try:
        logging.info("Pipeline started.")

        print("Step 1: Loading raw data...")
        logging.info("Step 1: Loading raw data...")
        df_raw = load_raw_data()

        print("\nStep 2: Cleaning data...")
        logging.info("Step 2: Cleaning data...")
        df_clean, cleaning_log = clean_data(df_raw)
        logging.info(f"Cleaning completed. Cleaning log: {cleaning_log}")

        print("\nStep 3: Building weekly summary...")
        logging.info("Step 3: Building weekly summary...")
        summary = build_weekly_summary(df_clean)

        with open("summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)

        print("Weekly summary created successfully.")
        print("File saved: summary.json")
        logging.info("Weekly summary created successfully. File saved: summary.json")

        print("\nStep 4: Generating AI report...")
        logging.info("Step 4: Generating AI report...")
        report_text = generate_weekly_report(summary)

        with open("weekly_report_output.txt", "w", encoding="utf-8") as f:
            f.write(report_text)

        print("AI report generated successfully.")
        print("File saved: weekly_report_output.txt")
        logging.info("AI report generated successfully. File saved: weekly_report_output.txt")

        print("\nStep 5: Generating charts...")
        logging.info("Step 5: Generating charts...")
        chart_paths = generate_charts(df_clean, summary)
        logging.info(f"Charts generated successfully: {chart_paths}")

        print("Charts generated successfully.")
        
        print("\nStep 6: Sending HTML email...")
        logging.info("Step 6: Sending HTML email...")
        send_email(report_text, summary, chart_paths)

        print("\nPipeline completed successfully from start to end.")
        logging.info("Pipeline completed successfully from start to end.")

    except Exception as e:
        logging.exception("Pipeline failed.")
        print("\nPipeline failed. Check pipeline.log for details.")
        raise


if __name__ == "__main__":
    main()