from __future__ import annotations

import pendulum
import sys
from pathlib import Path
from datetime import timedelta

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.models.variable import Variable
from airflow.models.param import Param

# Define the project root. This makes the DAG portable.
# In a production Airflow setup, you should set an Airflow Variable:
# `customer_churn_project_root` = `/path/to/your/project`
PROJECT_ROOT = Path(Variable.get("customer_churn_project_root", default_var=Path(__file__).parent.parent))
SRC_DIR = PROJECT_ROOT / "src"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# Platform-agnostic path to the virtual environment's Python executable
VENV_PYTHON_EXECUTABLE = "python.exe" if sys.platform == "win32" else "python"
VENV_PYTHON_DIR = "Scripts" if sys.platform == "win32" else "bin"
VENV_PYTHON = PROJECT_ROOT / ".venv" / VENV_PYTHON_DIR / VENV_PYTHON_EXECUTABLE

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="customer_churn_pipeline",
    default_args=default_args,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["mlops", "churn_prediction"],
    params={
        "data_source": Param(
            "synthetic",
            type="string",
            enum=["synthetic", "kaggle"],
            title="Data Source",
            description="Choose 'synthetic' to generate data or 'kaggle' to download from Kaggle.",
        ),
    },
    doc_md="""
    ### Customer Churn Prediction Pipeline

    This DAG orchestrates the end-to-end process for the customer churn prediction model.
    You can select the data source using the 'Trigger DAG w/ config' option in the UI.

    **Note**: For this DAG to run correctly in a production environment, you must:
    1. Run the `setup.sh` or `setup.bat` script to create the virtual environment.
    2. Set an Airflow Variable `customer_churn_project_root` to the absolute path
       of this project directory via the Airflow UI (Admin -> Variables).
    """,
) as dag:
    # --- Task Definitions ---

    # Task 1a: Get the main customer dataset based on the selected data_source.
    get_main_dataset = BashOperator(
        task_id="get_main_dataset",
        bash_command=(
            # This command selects the correct script to run based on the 'data_source' DAG parameter.
            # Note the double curly braces to escape the f-string for Airflow's templating.
            f"if [ '{{{{ params.data_source }}}}' = 'kaggle' ]; then "
            f"  echo 'Downloading data from Kaggle...';\n"
            f"  {VENV_PYTHON} {SRC_DIR}/data_ingest_kaggle.py;\n"
            f"else "
            f"  echo 'Generating synthetic data...';\n"
            f"  {VENV_PYTHON} {SRC_DIR}/generate_csv_data.py;\n"
            f"fi"
        ),
        doc_md="Generates `customer_accounts.csv` (synthetically or from Kaggle).",
    )

    # Task 1b: Generate data for the mock API. This can run in parallel with get_main_dataset.
    generate_api_data = BashOperator(
        task_id="generate_api_data",
        bash_command=f"{VENV_PYTHON} {SRC_DIR}/generate_api_data.py",
        doc_md="Generates `interactions.json` for the mock API.",
    )

    # Task 2: Ingest data by running the mock API and the ingest script.
    # This task encapsulates the logic to start the API, run the client, and shut it down.
    ingest_data = BashOperator(
        task_id="ingest_data",
        bash_command=f"""
            # Ensure API server is killed on exit, even if the script fails.
            trap 'echo "Killing API server PID $API_PID"; kill -s TERM $API_PID || true' EXIT

            echo "Starting mock API server in the background..."
            {VENV_PYTHON} {SRC_DIR}/mock_api.py &
            API_PID=$!
            echo "Mock API server started with PID $API_PID."

            # Allow server to initialize. A better approach would be a health check loop.
            echo "Waiting for API server to initialize..."
            sleep 8

            echo "Running ingest script..."
            {VENV_PYTHON} {SRC_DIR}/ingest.py

            # The trap will handle the cleanup.
            echo "Ingestion complete."
        """,
        doc_md="Starts the mock API, runs the ingest script, and ensures the API is shut down.",
    )

    # Task 3: Validate Raw Data
    validate_data = BashOperator(
        task_id="validate_raw_data",
        bash_command=f"{VENV_PYTHON} {SRC_DIR}/validate_raw_data.py",
        doc_md="Validates raw data.",
    )

    # Task 4: Prepare Data
    prepare_data = BashOperator(
        task_id="prepare_data",
        bash_command=f"{VENV_PYTHON} {SRC_DIR}/prepare_data.py",
        doc_md="Prepares and cleans the data.",
    )

    # Task 5: Transform and Store Features
    transform_and_store = BashOperator(
        task_id="transform_and_store_features",
        bash_command=f"{VENV_PYTHON} {SRC_DIR}/transform_and_store.py",
        doc_md="Applies feature engineering and saves features to the feature store.",
    )

    # Task 6: Train Model
    train_model = BashOperator(
        task_id="train_model",
        bash_command=f"{VENV_PYTHON} {SRC_DIR}/train_model_with_feature_store.py",
        doc_md="Trains the machine learning model.",
    )

    # --- Task Dependencies ---
    # The ingest step depends on both the main dataset and the API data.
    [get_main_dataset, generate_api_data] >> ingest_data

    # The rest of the pipeline flows sequentially.
    ingest_data >> validate_data >> prepare_data >> transform_and_store >> train_model