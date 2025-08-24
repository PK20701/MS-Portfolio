import pandas as pd
import os
import logging
from pathlib import Path
from datetime import datetime

# --- Project Root and Paths Configuration ---
# Assumes this script is in a 'src' directory inside the project root
project_root = Path(__file__).parent.parent
INGESTED_DATA_DIR = project_root / "data" / "raw" / "customer_accounts_partitioned"
INTERACTIONS_DATA_DIR = project_root / "data" / "raw" / "interactions_partitioned"
PREPARED_DATA_DIR = project_root / "data" / "prepared"
LOG_DIR = project_root / "logs"

# --- Logger Configuration ---
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Avoid adding handlers if they already exist (e.g., from a previous import)
if not logger.handlers:
    log_file_path = LOG_DIR / f"prepare_data_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

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

def find_latest_data(base_path: Path, file_name: str) -> Path:
    """
    Finds the path to the data file in the most recent ingestion directory.
    Can handle both CSV and JSON files based on the file_name.
    """
    logger.info(f"Searching for latest '{file_name}' in: {base_path}")
    if not base_path.exists():
        raise FileNotFoundError(f"Ingestion directory not found: {base_path}")

    ingestion_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name.startswith("ingest_date=")]
    if not ingestion_dirs:
        raise FileNotFoundError(f"No ingestion partitions found in {base_path}")

    latest_dir = sorted(ingestion_dirs)[-1]
    data_file = latest_dir / file_name
    
    if not data_file.exists():
        raise FileNotFoundError(f"'{file_name}' not found in the latest partition: {latest_dir}")
        
    logger.info(f"Found latest data file at: {data_file}")
    return data_file

def process_interactions(df_interactions: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the interactions dataframe to create aggregated features per customer.
    """
    logger.info("Processing customer interactions data...")
    
    # Convert interaction_date to datetime
    df_interactions['interaction_date'] = pd.to_datetime(df_interactions['interaction_date'])
    
    # Use a fixed reference date for reproducibility (the day after the latest interaction)
    reference_date = df_interactions['interaction_date'].max() + pd.Timedelta(days=1)
    
    # Aggregate features per customerID
    agg_features = df_interactions.groupby('customerID').agg(
        last_interaction_date=('interaction_date', 'max'),
        total_interactions=('interaction_date', 'count')
    ).reset_index()

    # --- Feature 1: Days since last interaction ---
    agg_features['days_since_last_interaction'] = (reference_date - agg_features['last_interaction_date']).dt.days
    agg_features = agg_features.drop(columns=['last_interaction_date'])

    # --- Feature 2: Counts of each interaction type ---
    interaction_type_counts = pd.crosstab(df_interactions['customerID'], df_interactions['interaction_type']).reset_index()

    # --- Ensure all expected interaction type columns exist ---
    expected_interaction_types = ['billing_inquiry', 'complaint', 'service_upgrade', 'support_call', 'website_visit']
    for col in expected_interaction_types:
        if col not in interaction_type_counts.columns:
            logger.warning(f"Interaction type column '{col}' not found in data. Creating it with all zeros.")
            interaction_type_counts[col] = 0

    # --- Merge all interaction features ---
    logger.info("Merging aggregated interaction features.")
    interactions_final_df = pd.merge(agg_features, interaction_type_counts, on='customerID', how='outer')
    
    logger.info(f"Processed interactions data. Shape: {interactions_final_df.shape}")
    return interactions_final_df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the dataframe by handling missing values in 'TotalCharges'.
    """
    logger.info("Starting data cleaning...")
    df_clean = df.copy()
    
    # The original script had a major error here, attempting to convert all columns
    # to numeric, which would corrupt string-based categorical data.
    # The correct approach is to target only the 'TotalCharges' column.
    
    # Convert 'TotalCharges' to numeric, coercing errors to NaN
    df_clean['TotalCharges'] = pd.to_numeric(df_clean['TotalCharges'], errors='coerce')
    
    # Impute missing 'TotalCharges' with the median of the column
    if df_clean['TotalCharges'].isnull().any():
        num_missing = df_clean['TotalCharges'].isnull().sum()
        median_val = df_clean['TotalCharges'].median()
        df_clean['TotalCharges'].fillna(median_val, inplace=True)
        logger.info(f"Imputed {num_missing} missing values in 'TotalCharges' with median value {median_val:.2f}.")
    else:
        logger.info("No missing values found in 'TotalCharges'.")
        
    logger.info("Data cleaning complete.")
    return df_clean

def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encodes categorical features using binary and one-hot encoding.
    """
    logger.info("Starting feature encoding...")
    df_encoded = df.copy()

    # The original script was missing the column lists for encoding.
    # These have been identified from the data generation script.

    # Binary encoding for columns with two distinct values (plus gender)
    df_encoded['gender'] = df_encoded['gender'].map({'Male': 1, 'Female': 0})
    
    binary_cols = ['Partner', 'Dependents', 'PhoneService', 'PaperlessBilling', 'Churn']
    for col in binary_cols:
        df_encoded[col] = df_encoded[col].map({'Yes': 1, 'No': 0})
    logger.info(f"Applied binary encoding to: gender, {', '.join(binary_cols)}")

    # One-hot encoding for columns with multiple categories
    multi_cat_cols = [
        'MultipleLines', 'InternetService', 'OnlineSecurity', 'OnlineBackup',
        'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies',
        'Contract', 'PaymentMethod'
    ]
    df_encoded = pd.get_dummies(df_encoded, columns=multi_cat_cols, drop_first=True, dtype=int)
    logger.info(f"Applied one-hot encoding to: {', '.join(multi_cat_cols)}")
    
    logger.info("Feature encoding complete.")
    return df_encoded

def main():
    """
    Main function to execute the data preparation pipeline.
    """
    logger.info("--- Starting Data Preparation Script ---")
    try:
        # 1. Find and load the latest data sources
        latest_accounts_file = find_latest_data(INGESTED_DATA_DIR, "data.csv")
        df_accounts = pd.read_csv(latest_accounts_file)
        logger.info(f"Loaded raw accounts data with shape: {df_accounts.shape}")

        latest_interactions_file = find_latest_data(INTERACTIONS_DATA_DIR, "data.json")
        df_interactions = pd.read_json(latest_interactions_file)
        logger.info(f"Loaded raw interactions data with shape: {df_interactions.shape}")

        # 2. Process interactions data to create features
        interactions_features = process_interactions(df_interactions)

        # 3. Merge accounts data with processed interactions data
        logger.info("Merging accounts data with interaction features.")
        df_merged = pd.merge(df_accounts, interactions_features, on='customerID', how='left')
        
        # For customers with no interactions, NaNs will be present. Fill them appropriately.
        interaction_feature_cols = [col for col in interactions_features.columns if col != 'customerID']
        
        # For days_since_last_interaction, NaN means no interaction. A large number is a good imputation.
        # For interaction counts, NaN means 0.
        fill_values = {col: 0 for col in interaction_feature_cols if 'days_since' not in col}
        if 'days_since_last_interaction' in df_merged.columns:
            max_days = df_merged['days_since_last_interaction'].max()
            fill_values['days_since_last_interaction'] = max_days + 365 # Impute with a value a year after the last known interaction
        
        df_merged.fillna(value=fill_values, inplace=True)
        logger.info(f"Data merged. Shape after merge: {df_merged.shape}")

        # 4. Clean and encode the combined dataset
        df_clean = clean_data(df_merged)
        df_processed = encode_features(df_clean)
        
        # 5. Keep customerID for identification
        if 'customerID' not in df_processed.columns:
            logger.warning("customerID column not found in the data.")
        logger.info("Kept 'customerID' column for tracking and database storage.")

        # 5. Save the prepared dataset
        PREPARED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = PREPARED_DATA_DIR / "prepared_churn_data.csv"
        df_processed.to_csv(output_path, index=False)
        
        logger.info(f"Successfully prepared data. Final shape: {df_processed.shape}")
        logger.info(f"Prepared data saved to: {output_path}")

    except FileNotFoundError as e:
        logger.error(f"A required file or directory was not found. Please check paths. Error: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"An unexpected error occurred in the main preparation pipeline: {e}", exc_info=True)
    
    logger.info("--- Data Preparation Script Finished ---")

if __name__ == "__main__":
    main()