import pandas as pd
from sklearn.preprocessing import StandardScaler
import numpy as np
from sklearn.impute import SimpleImputer
from sqlalchemy import create_engine
import logging
from pathlib import Path
from datetime import datetime
from database_utils import setup_database

# --- Project Root and Paths Configuration ---
project_root = Path(__file__).parent.parent
PREPARED_DATA_DIR = project_root / "data" / "prepared"
TRANSFORMED_DATA_DIR = project_root / "data" / "transformed"
LOG_DIR = project_root / "logs"
SCHEMA_PATH = project_root / "src" / "database_setup.sql"

# --- Logger Configuration ---
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Avoid adding handlers if they already exist (e.g., from a previous import)
if not logger.handlers:
    log_file_path = LOG_DIR / f"transform_and_store_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

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


def transform_and_store_data(input_path: Path, db_path: Path, parquet_path: Path):
    """
    Performs feature engineering, scaling, and loads data into an SQLite database.
    """
    try:
        logger.info(f"Starting data transformation for {input_path}")
        if not input_path.exists():
            raise FileNotFoundError(f"Prepared data file not found at: {input_path}")
        
        df = pd.read_csv(input_path)
        
        if 'customerID' not in df.columns:
            raise ValueError("customerID column is missing from the prepared data.")
            
        # Keep customerID for joining/primary key, but separate from features
        customer_ids = df['customerID']
        features_df = df.drop(columns=['customerID'])

        # --- 1. Feature Engineering ---
        logger.info("Performing feature engineering.")
        
        # Tenure in Years
        features_df['TenureInYears'] = features_df['tenure'] / 12.0
        
        # Number of Additional Services
        # These columns were one-hot encoded in the prepare_data step. 'Yes' is encoded as 1.
        service_cols = [
            'OnlineSecurity_Yes', 'OnlineBackup_Yes', 'DeviceProtection_Yes', 
            'TechSupport_Yes', 'StreamingTV_Yes', 'StreamingMovies_Yes'
        ]
        # Ensure all service columns exist, fill missing with 0
        for col in service_cols:
            if col not in features_df.columns:
                logger.warning(f"Service column '{col}' not found. Assuming 0 for this service.")
                features_df[col] = 0
        
        features_df['NumAdditionalServices'] = features_df[service_cols].sum(axis=1)

        # Monthly-to-Tenure Ratio
        # Add 1 to tenure to avoid division by zero for new customers (tenure=0)
        features_df['MonthlyTenureRatio'] = features_df['MonthlyCharges'] / (features_df['tenure'] + 1)

        # --- 2. Impute and Scale Numerical Features ---
        # Identify numeric columns for processing, excluding the target variable 'Churn'.
        if 'Churn' in features_df.columns:
            numerical_cols = features_df.select_dtypes(include=np.number).columns.tolist()
            numerical_cols.remove('Churn')
        else:
            numerical_cols = features_df.select_dtypes(include=np.number).columns.tolist()

        # Defensive check: Drop columns that are completely empty (all NaN).
        # This can happen if a feature source has no data for the current batch,
        # preventing shape mismatch errors with the imputer/scaler.
        all_nan_cols = [col for col in numerical_cols if features_df[col].isnull().all()]
        if all_nan_cols:
            logger.warning(f"Dropping columns with all NaN values: {all_nan_cols}")
            features_df.drop(columns=all_nan_cols, inplace=True)
            numerical_cols = [col for col in numerical_cols if col not in all_nan_cols]

        # Impute missing values (e.g., in TotalCharges) using the mean.
        # This is a critical step to prevent errors in downstream models.
        logger.info(f"Imputing missing values for columns: {numerical_cols}")
        imputer = SimpleImputer(strategy='mean')
        
        # The fit_transform method returns a NumPy array, which loses column and index
        # information. To prevent assignment errors, we reconstruct a DataFrame with
        # the original index and columns. This is a more robust approach.
        imputed_data = imputer.fit_transform(features_df[numerical_cols])
        features_df[numerical_cols] = pd.DataFrame(
            imputed_data, columns=numerical_cols, index=features_df.index
        )
        logger.info("Missing values imputed successfully.")

        # Scale numerical features
        logger.info("Scaling numerical features.")
        logger.info(f"Columns to be scaled: {numerical_cols}")

        scaler = StandardScaler()
        # We apply the same robust assignment pattern here for consistency.
        scaled_data = scaler.fit_transform(features_df[numerical_cols])
        features_df[numerical_cols] = pd.DataFrame(
            scaled_data, columns=numerical_cols, index=features_df.index
        )
        logger.info("Numerical features scaled successfully.")
        
        # --- 3. Store in SQLite Database ---
        # Re-attach customerID before storing
        final_df = pd.concat([customer_ids, features_df], axis=1)

        logger.info(f"Storing transformed data in SQLite database at {db_path}")
        engine = create_engine(f'sqlite:///{db_path}')
        
        # Append data to the table. The table is created/reset by the setup script.
        final_df.to_sql('churn_features', engine, if_exists='append', index=False, chunksize=1000)
        
        logger.info(f"Successfully transformed and stored {len(final_df)} records in the database.")
        
        # --- 4. Save a copy to a file for other pipeline steps ---
        logger.info(f"Saving a copy of transformed data to Parquet file at {parquet_path}")
        final_df.to_parquet(parquet_path, index=False)
        logger.info("Parquet file saved successfully.")

    except Exception as e:
        logger.critical(f"An error occurred during data transformation: {e}", exc_info=True)
        raise  # Re-raise the exception after logging

def main():
    """Main function to execute the data transformation and storage pipeline."""
    logger.info("--- Starting Data Transformation & Storage Script ---")
    
    prepared_data_path = PREPARED_DATA_DIR / "prepared_churn_data.csv"
    
    # Ensure the output directory exists
    TRANSFORMED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    database_path = TRANSFORMED_DATA_DIR / "churn_pipeline.db"
    parquet_path = TRANSFORMED_DATA_DIR / "transformed_features.parquet"

    # --- Setup Database Schema ---
    # This step ensures the database and table are created with the correct schema
    # before any data is loaded.
    setup_database(db_path=database_path, schema_file=SCHEMA_PATH)

    try:
        transform_and_store_data(
            input_path=prepared_data_path, 
            db_path=database_path,
            parquet_path=parquet_path
        )

        # --- Sample Query to Retrieve Data ---
        logger.info("--- Verifying data from SQLite DB ---")
        engine = create_engine(f'sqlite:///{database_path}')
        sample_query = "SELECT customerID, tenure, Churn FROM churn_features LIMIT 5;"
        # Using read_sql_query is more explicit and robust for executing queries.
        retrieved_data = pd.read_sql_query(sample_query, engine)
        print("\nSample data retrieved from SQLite DB:")
        print(retrieved_data)

    except Exception as e:
        logger.critical(f"An error occurred during the main transformation process: {e}", exc_info=True)

    logger.info("--- Data Transformation & Storage Script Finished ---")


if __name__ == "__main__":
    main()