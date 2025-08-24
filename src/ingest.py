import pandas as pd
import logging
import os
from pathlib import Path
from datetime import datetime
import sys

try:
    import requests
except ImportError:
    print("ERROR: The 'requests' library is not installed.", file=sys.stderr)
    print(f"You are using the Python interpreter at: {sys.executable}", file=sys.stderr)
    is_conda = '.conda' in sys.executable or 'Continuum' in sys.version or 'Anaconda' in sys.version
    if is_conda:
        print("\nYou can install it with: conda install requests", file=sys.stderr)
    else:
        print("\nYou can install it with: pip install requests", file=sys.stderr)
    sys.exit(1)


# --- Project Root Configuration ---
# Assumes this script is in a 'src' directory inside the project root
project_root = Path(__file__).parent.parent

# --- Logger Configuration ---
LOG_DIR = project_root / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Get a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent log messages from being passed to the root logger's handlers,
# which is important when this script is run as part of a larger application
# (like the Prefect pipeline) that configures the root logger.
logger.propagate = False

# To prevent duplicate logs if the script is imported multiple times,
# check if handlers are already present before adding them.
if not logger.handlers:
    log_file_path = LOG_DIR / f"ingestion_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    
    # Create a formatter to define the log message structure
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create a file handler to write log messages to a file
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Create a stream handler to write log messages to the console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# --- Configuration ---
RAW_DATA_DIR = project_root / "data" / "raw"

def ingest_csv_data(file_path: Path, output_dir: Path) -> None:
    """
    Ingests data from a CSV file, saves it to a partitioned directory,
    and logs the process.
    """
    try:
        logger.info(f"Starting ingestion for CSV file: {file_path}")
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found at {file_path}")

        df = pd.read_csv(file_path)
        
        # Create partitioned output path
        ingest_date = datetime.now().strftime('%Y-%m-%d')
        partitioned_path = output_dir / f"ingest_date={ingest_date}"
        partitioned_path.mkdir(parents=True, exist_ok=True)
        
        output_file = partitioned_path / "data.csv"
        df.to_csv(output_file, index=False)
        
        logger.info(f"Successfully ingested {len(df)} rows from {file_path}")
        logger.info(f"Raw data saved to {output_file}")

    except pd.errors.ParserError as e:
        logger.error(f"Failed to parse CSV file {file_path}. Error: {e}", exc_info=True)
    except FileNotFoundError as e:
        logger.error(str(e), exc_info=True)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during CSV ingestion: {e}", exc_info=True)

def ingest_api_data(api_url: str, output_dir: Path) -> None:
    """
    Ingests data from a JSON API, saves it to a partitioned directory,
    and logs the process.
    """
    try:
        logger.info(f"Starting ingestion from API: {api_url}")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = response.json()
        if not data:
            logger.warning(f"API at {api_url} returned no data. Skipping.")
            return

        df = pd.DataFrame(data)

        # Create partitioned output path
        ingest_date = datetime.now().strftime('%Y-%m-%d')
        partitioned_path = output_dir / f"ingest_date={ingest_date}"
        partitioned_path.mkdir(parents=True, exist_ok=True)

        output_file = partitioned_path / "data.json"
        df.to_json(output_file, orient='records', indent=4)

        logger.info(f"Successfully ingested {len(df)} records from {api_url}")
        logger.info(f"Raw data saved to {output_file}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch data from API {api_url}. Is the mock_api.py server running? Error: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during API ingestion: {e}", exc_info=True)

def main():
    """Main function to run the data ingestion process."""
    logger.info("--- Starting Data Ingestion Script ---")

    # --- 1. Ingest Customer Accounts CSV ---
    source_csv_path = RAW_DATA_DIR / "customer_accounts.csv"
    if not source_csv_path.exists():
        logger.error(f"{source_csv_path} not found. Please run generate_csv_data.py first.")
        # In an automated pipeline, this should be a failure.
        raise FileNotFoundError(f"{source_csv_path} not found.")
    else:
        csv_output_dir = RAW_DATA_DIR / "customer_accounts_partitioned"
        ingest_csv_data(file_path=source_csv_path, output_dir=csv_output_dir)

    # --- 2. Ingest Interactions from Mock API ---
    api_url = "http://127.0.0.1:8000/api/interactions"
    api_output_dir = RAW_DATA_DIR / "interactions_partitioned"
    ingest_api_data(api_url=api_url, output_dir=api_output_dir)

    logger.info("--- Data Ingestion Script Finished ---")

if __name__ == "__main__":
    main()
