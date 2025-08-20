# main.py
import os
import io
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

# --- Project Root and Paths Configuration ---
project_root = Path(__file__).parent.parent
LOG_DIR = project_root / "logs"
DATA_DIR = project_root / "data" / "raw"

# --- Logger Configuration ---
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOG_DIR / f"kaggle_ingest_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def main():
    """
    Downloads the Telco Customer Churn dataset from Kaggle,
    and saves it as 'customer_accounts.csv' in the raw data directory.

    This script can be used as an alternative to `generate_csv_data.py` to
    populate the pipeline with a real-world dataset.
    
    Prerequisites:
    1. Make sure you have the 'kaggle' library installed:
       pip install kaggle

    2. You need to have your Kaggle API key (kaggle.json) set up.
       - Go to your Kaggle account page.
       - Click on 'Create New API Token' in the 'API' section.
       - This will download a 'kaggle.json' file.
       - Place this file in the '~/.kaggle/' directory on your system.
         (For Windows, it's usually 'C:\\Users\\<Your-Username>\\.kaggle\\')
       - Make sure the file has the correct permissions (readable only by you).

    This script will save the data to the 'data/raw' directory.
    """
    try:
        # --- 1. Authenticate with the Kaggle API ---
        api = KaggleApi()
        api.authenticate()
        logger.info("Successfully authenticated with the Kaggle API.")

        # --- 2. Define Dataset Information ---
        # We'll use the popular "Telco Customer Churn" dataset.
        dataset_identifier = "blastchar/telco-customer-churn"
        original_csv_name = "WA_Fn-UseC_-Telco-Customer-Churn.csv"
        final_csv_name = "customer_accounts.csv"  # Standard name for the pipeline

        # Ensure the target data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        download_path = DATA_DIR

        # --- 3. Download the Dataset ---
        logger.info(f"Downloading '{dataset_identifier}' from Kaggle to '{download_path}'...")
        # Use unzip=True to automatically extract the files
        api.dataset_download_files(
            dataset_identifier, path=str(download_path), quiet=False, unzip=True
        )
        logger.info(f"Dataset downloaded and unzipped to '{download_path}'.")

        # --- 4. Rename the file for pipeline consistency ---
        original_file_path = download_path / original_csv_name
        final_file_path = download_path / final_csv_name

        if original_file_path.exists():
            logger.info(f"Renaming '{original_csv_name}' to '{final_csv_name}'...")
            if final_file_path.exists():
                logger.warning(f"'{final_csv_name}' already exists. Overwriting.")
                final_file_path.unlink()
            original_file_path.rename(final_file_path)
            logger.info(f"File successfully renamed to '{final_file_path}'.")
        else:
            logger.error(f"The expected CSV file '{original_csv_name}' was not found in '{download_path}'.")
            return

        # --- 5. Read and display info from the final file ---
        logger.info(f"Reading '{final_csv_name}' to verify...")
        df = pd.read_csv(final_file_path)
        logger.info("Successfully loaded data into DataFrame.")
        logger.info("--- First 5 rows of the Customer Churn Dataset ---")
        logger.info("\n" + df.head().to_string())

        # Capture df.info() output to log it
        buffer = io.StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        logger.info("--- Dataset Info ---")
        logger.info("\n" + info_str)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        logger.error("Please ensure your 'kaggle.json' API key is correctly set up.")


if __name__ == "__main__":
    main()
