"""
This script is responsible for inference.

It loads trained models from the MLflow Model Registry, fetches a few sample
records from the transformed data, and makes predictions. The results, including
the predicted churn status, are then logged to both the console and a log file.

This script can be run standalone after the training pipeline has successfully
executed and registered models.
"""
import logging
from pathlib import Path
from datetime import datetime

import mlflow
import pandas as pd

# --- Paths and Constants ---
project_root = Path(__file__).resolve().parents[1]
MLFLOW_TRACKING_URI = (project_root / "mlruns").as_uri()
# We'll use the transformed data as a source for sample records for prediction
TRANSFORMED_DATA_PATH = (
    project_root / "data" / "transformed" / "transformed_features.parquet"
)
LOG_DIR = project_root / "logs"

# --- Logger Configuration ---
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent log messages from being passed to the root logger's handlers
logger.propagate = False

# Avoid adding handlers if they already exist
if not logger.handlers:
    log_file_path = LOG_DIR / f"predict_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

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


def load_sample_data(n_samples: int = 5) -> pd.DataFrame:
    """
    Loads a few sample records for inference.

    Args:
        n_samples (int): The number of samples to load.

    Returns:
        pd.DataFrame: A DataFrame with sample data, ready for prediction.
    """
    try:
        df = pd.read_parquet(TRANSFORMED_DATA_PATH)
        # Drop the target variable if it exists, as we are predicting it
        if "Churn" in df.columns:
            df = df.drop(columns=["Churn", "customerID"])
        return df.head(n_samples)
    except FileNotFoundError:
        logger.error(
            f"Transformed data not found at {TRANSFORMED_DATA_PATH}. "
            "Please run the training pipeline first."
        )
        return pd.DataFrame()  # Return empty dataframe


def predict(model_name: str, model_stage: str, data: pd.DataFrame):
    """
    Loads a model from the MLflow Model Registry and makes predictions.

    Args:
        model_name (str): The name of the registered model.
        model_stage (str): The stage of the model to load (e.g., 'Staging', 'Production').
        data (pd.DataFrame): The data to make predictions on.
    """
    if data.empty:
        logger.warning("Input data is empty. Skipping prediction.")
        return

    try:
        # No need to set this every time in a loop, but it's safe.
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        model_uri = f"models:/{model_name}/{model_stage}"
        logger.info(f"Loading model from stage '{model_stage}' ({model_uri})...")

        loaded_model = mlflow.pyfunc.load_model(model_uri)
        logger.info("Model loaded successfully.")

        predictions = loaded_model.predict(data)
        # Make the prediction column name unique to the model
        data[f"predicted_churn_{model_name}"] = predictions
        logger.info(f"\n--- Prediction Results for {model_name} ---\n%s", data)

    except mlflow.exceptions.MlflowException as e:
        logger.error(
            f"Could not load the model '{model_name}' from the registry. "
            f"Have you run the training pipeline and registered the model?"
        )
        logger.error(f"MLflow Exception: {e}")


if __name__ == "__main__":
    # List of all models that were trained and registered
    MODEL_NAMES = ["LogisticRegression", "RandomForest", "GradientBoostingClassifier"]
    MODEL_STAGE = "Staging"  # Or "Production", "Archived", etc.

    logger.info("Loading sample data for inference...")
    sample_data = load_sample_data()

    if not sample_data.empty:
        # Make a copy of the data for each model to avoid modifying the original
        for model_name in MODEL_NAMES:
            logger.info(f"\n{'='*20} PREDICTING WITH {model_name.upper()} {'='*20}")
            predict(
                model_name=model_name,
                model_stage=MODEL_STAGE,
                data=sample_data.copy(),
            )