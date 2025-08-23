import json
import random
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

try:
    from faker import Faker
    import pandas as pd
except ImportError as e:
    print(f"ERROR: {e}. A required module is not installed.", file=sys.stderr)
    print(f"You are using the Python interpreter at: {sys.executable}", file=sys.stderr)
    print("Please install the missing packages in this environment.", file=sys.stderr)

    is_conda = '.conda' in sys.executable or 'Continuum' in sys.version or 'Anaconda' in sys.version
    if is_conda:
        print("\nIt looks like you're using a Conda environment. You can install the packages with:", file=sys.stderr)
        print("conda install -c conda-forge pandas faker", file=sys.stderr)
    else:
        print("\nYou can install the packages with pip:", file=sys.stderr)
        print(f'"{sys.executable}" -m pip install pandas Faker', file=sys.stderr)

    print("\nIf you are using an IDE like VS Code, ensure you have selected the correct Python interpreter that has these packages installed.", file=sys.stderr)
    sys.exit(1)

# --- Setup Logging ---
# --- Logger Configuration ---
project_root = Path(__file__).parent.parent
LOG_DIR = project_root / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent log messages from being passed to the root logger's handlers
logger.propagate = False

# Avoid adding handlers if they already exist (e.g., from a previous import)
if not logger.handlers:
    log_file_path = LOG_DIR / f"generate_api_data_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Create handlers
    file_handler = logging.FileHandler(log_file_path)
    stream_handler = logging.StreamHandler()

    # Create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# --- Constants ---
# Determine the project root directory (assuming this script is in a 'src' folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'customer_accounts.csv')
OUTPUT_JSON_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'interactions.json')
INTERACTION_TYPES = ['support_call', 'website_visit', 'complaint', 'billing_inquiry', 'service_upgrade']
INTERACTION_WEIGHTS = [0.2, 0.5, 0.1, 0.15, 0.05]

def load_customer_ids(file_path: str) -> List[str]:
    """Loads customer IDs from the specified CSV file."""
    logger.info(f"Loading customer IDs from {file_path}...")
    try:
        df_customers = pd.read_csv(file_path)
        customer_ids = df_customers['customerID'].tolist()
        logger.info(f"Successfully loaded {len(customer_ids)} customer IDs.")
        return customer_ids
    except FileNotFoundError:
        logger.error(f"Error: {file_path} not found. Please run generate_csv_data.py first.")
        sys.exit(1)
    except KeyError:
        logger.error(f"Error: 'customerID' column not found in {file_path}.")
        sys.exit(1)

def generate_interactions(
    customer_ids: List[str],
    num_interactions: int,
    fake_generator: Faker
) -> List[Dict[str, Any]]:
    """Generates a list of synthetic customer interactions."""
    logger.info(f"Generating {num_interactions} interaction records...")
    interaction_data = []
    for _ in range(num_interactions):
        interaction = {
            'customerID': random.choice(customer_ids),
            'interaction_date': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            'interaction_type': random.choices(INTERACTION_TYPES, weights=INTERACTION_WEIGHTS)[0],
            'interaction_details': fake_generator.sentence(nb_words=random.randint(5, 15))
        }
        interaction_data.append(interaction)
    return interaction_data

def save_data_to_json(data: List[Dict[str, Any]], file_path: str) -> None:
    """Saves the provided data to a JSON file."""
    output_dir = os.path.dirname(file_path)
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Saving interaction data to {file_path}...")
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def main():
    """Main function to orchestrate the data generation process."""
    # --- Configuration ---
    NUM_INTERACTIONS = 15000
    RANDOM_SEED = 42  # For reproducibility

    # --- Initialization ---
    random.seed(RANDOM_SEED)
    Faker.seed(RANDOM_SEED)
    fake = Faker()

    # --- Execution ---
    customer_ids = load_customer_ids(RAW_DATA_PATH)
    interaction_data = generate_interactions(customer_ids, NUM_INTERACTIONS, fake)
    save_data_to_json(interaction_data, OUTPUT_JSON_PATH)

    logger.info(f"Successfully generated {NUM_INTERACTIONS} interaction records.")
    logger.info("Sample of generated data:")
    # Use print for the sample for better readability of the JSON structure
    print(json.dumps(interaction_data[:3], indent=4))

if __name__ == "__main__":
    main()