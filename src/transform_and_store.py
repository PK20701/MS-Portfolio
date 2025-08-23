import pandas as pd
from sklearn.preprocessing import StandardScaler
import numpy as np
from sqlalchemy import create_engine
import logging
from pathlib import Path
from datetime import datetime

# --- Project Root and Paths Configuration ---
project_root = Path(__file__).parent.parent
PREPARED_DATA_DIR = project_root / "data" / "prepared"
TRANSFORMED_DATA_DIR = project_root / "data" / "transformed"
LOG_DIR = project_root / "logs"

# --- Logger Configuration ---
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Avoid adding handlers if they already exist (e.g., from a previous import)
if not logger.handlers:
    log_file_path = LOG_DIR / f"transform_and_store_{datetime.now().strftime('%Y-%m-%d')}.log"

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

        # --- 2. Feature Scaling ---
        logger.info("Scaling numerical features.")
        # Programmatically identify all numeric columns to be scaled, excluding the target.
        if 'Churn' in features_df.columns:
            numerical_cols = features_df.select_dtypes(include=np.number).columns.tolist()
            numerical_cols.remove('Churn')
        else:
            # This case might occur if the target column has a different name or is not present
            numerical_cols = features_df.select_dtypes(include=np.number).columns.tolist()
        logger.info(f"Columns to be scaled: {numerical_cols}")

        scaler = StandardScaler()
        features_df[numerical_cols] = scaler.fit_transform(features_df[numerical_cols])
        logger.info("Numerical features scaled successfully.")
        
        # --- 3. Store in SQLite Database ---
        # Re-attach customerID before storing
        final_df = pd.concat([customer_ids, features_df], axis=1)

        logger.info(f"Storing transformed data in SQLite database at {db_path}")
        engine = create_engine(f'sqlite:///{db_path}')
        
        # The prompt used 'churn_features' as the table name in the to_sql call
        final_df.to_sql('churn_features', engine, if_exists='replace', index=False, chunksize=1000)
        
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