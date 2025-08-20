import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
import io

# --- Project Root and Paths Configuration ---
project_root = Path(__file__).parent.parent
RAW_DATA_DIR = project_root / "data" / "raw" / "customer_accounts_partitioned"
REPORTS_DIR = project_root / "reports"
LOG_DIR = project_root / "logs"

# --- Logger Configuration ---
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOG_DIR / f"simple_raw_validation_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

def find_latest_ingested_data(base_path: Path) -> Path:
    """
    Finds the path to the data.csv file in the most recent ingestion directory.
    """
    logger.info(f"Searching for ingested data in: {base_path}")
    if not base_path.exists():
        raise FileNotFoundError(f"Ingestion directory not found: {base_path}")

    ingestion_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name.startswith("ingest_date=")]
    if not ingestion_dirs:
        raise FileNotFoundError(f"No ingestion partitions found in {base_path}")

    latest_dir = sorted(ingestion_dirs)[-1]
    data_file = latest_dir / "data.csv"
    
    if not data_file.exists():
        raise FileNotFoundError(f"data.csv not found in the latest partition: {latest_dir}")
        
    logger.info(f"Found latest data file at: {data_file}")
    return data_file

def generate_raw_data_quality_report(df: pd.DataFrame) -> str:
    """
    Performs various data quality checks on a raw DataFrame and returns a text report.
    """
    report_buffer = io.StringIO()

    def write_header(title):
        report_buffer.write(f"\n{'='*60}\n")
        report_buffer.write(f"{title.center(60)}\n")
        report_buffer.write(f"{'='*60}\n\n")

    # --- 1. Basic Information ---
    write_header("1. Basic Information")
    report_buffer.write(f"Number of rows: {df.shape[0]}\n")
    report_buffer.write(f"Number of columns: {df.shape[1]}\n\n")

    # --- 2. Data Types ---
    write_header("2. Data Types")
    report_buffer.write(df.dtypes.to_string())
    report_buffer.write("\n\n")

    # --- 3. Missing Data Check ---
    write_header("3. Missing Data")
    missing_values = df.isnull().sum()
    missing_values = missing_values[missing_values > 0]
    if not missing_values.empty:
        report_buffer.write("Columns with missing values:\n")
        report_buffer.write(missing_values.to_string())
        report_buffer.write("\n")
        if 'TotalCharges' in missing_values:
            report_buffer.write("\nNOTE: Missing values in 'TotalCharges' are expected and handled during data preparation.\n")
    else:
        report_buffer.write("No missing values found.\n")
    report_buffer.write("\n")

    # --- 4. Unique ID Check ---
    write_header("4. Unique Customer ID Check")
    if 'customerID' in df.columns:
        num_duplicate_ids = df.duplicated(subset=['customerID']).sum()
        if num_duplicate_ids > 0:
            report_buffer.write(f"WARNING: Found {num_duplicate_ids} duplicate customerIDs.\n")
        else:
            report_buffer.write("All customerIDs are unique.\n")
    else:
        report_buffer.write("WARNING: 'customerID' column not found.\n")
    report_buffer.write("\n")

    # --- 5. Categorical Data Value Check ---
    write_header("5. Categorical Value Checks")
    categorical_checks = {
        'gender': ['Male', 'Female'],
        'Partner': ['Yes', 'No'],
        'Churn': ['Yes', 'No'],
        'InternetService': ['DSL', 'Fiber optic', 'No'],
        'Contract': ['Month-to-month', 'One year', 'Two year'],
    }
    all_ok = True
    for col, expected_values in categorical_checks.items():
        if col in df.columns:
            unique_vals = df[col].dropna().unique()
            unexpected = set(unique_vals) - set(expected_values)
            if unexpected:
                all_ok = False
                report_buffer.write(f"WARNING: Unexpected values in '{col}': {unexpected}\n")
    if all_ok:
        report_buffer.write("All checked categorical columns contain expected values.\n")
    report_buffer.write("\n")

    return report_buffer.getvalue()

def main():
    """Main function to execute the raw data validation pipeline."""
    logger.info("--- Starting Simple Raw Data Validation Script ---")
    try:
        raw_data_file = find_latest_ingested_data(RAW_DATA_DIR)
        df = pd.read_csv(raw_data_file)
        logger.info(f"Loaded raw data with shape: {df.shape}")
        
        report_content = generate_raw_data_quality_report(df)
        
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_filename = f"raw_data_quality_report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"
        report_path = REPORTS_DIR / report_filename
        report_path.write_text(report_content, encoding='utf-8')
        
        logger.info(f"Raw data quality report successfully generated and saved to: {report_path}")
        print(f"\nRaw data quality report saved to: {report_path}")
        
    except FileNotFoundError as e:
        logger.error(f"A required file or directory was not found. Please check paths. Error: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during raw data validation: {e}", exc_info=True)

    logger.info("--- Simple Raw Data Validation Script Finished ---")

if __name__ == "__main__":
    main()