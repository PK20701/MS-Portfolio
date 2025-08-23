# Customer Churn Prediction Pipeline

This project implements a full end-to-end MLOps pipeline for predicting customer churn. It includes data generation, ingestion, validation, transformation, model training with a feature store, and data versioning. The entire pipeline is orchestrated using Prefect and output can be visualized using UI.

## MLOps Components

This project incorporates several MLOps best practices to ensure reproducibility, scalability, and maintainability.

### 1. Feature Store

A lightweight, file-based feature store is implemented to provide a centralized, documented, and versioned source of features for model training.

*   **Registry**: Feature definitions and metadata (e.g., description, source, version) are centrally defined in `src/feature_store.py`. This file acts as the feature registry.
*   **Offline Store**: The final, transformed features are stored in a single Parquet file at `data/transformed/transformed_features.parquet`. This file is the single source of truth for model training.
*   **Retrieval API**: The `get_feature_view()` function in `src/feature_store.py` provides a consistent API to retrieve feature sets for training. The model training script uses this function exclusively to get its data, decoupling it from the physical data source.

### 2. Data Versioning with DVC

This project uses DVC (Data Version Control) to manage and version large data files that are not suitable for Git. This ensures that every Git commit can correspond to a specific, reproducible version of the data.

*   **Workflow**: When a developer runs the pipeline to generate new raw data, they can use `dvc add` and `dvc push` to version it. This is a manual step.
*   **Automation with Pre-commit Hooks**: This project is configured with `pre-commit` hooks to automate the DVC workflow:
    *   **`dvc-pre-commit`**: When you run `git commit`, this hook automatically runs `dvc add` for any modified DVC-tracked data files. This versions your data and stages the corresponding `.dvc` file for you.
    *   **`dvc-pre-push`**: When you run `git push`, this hook automatically runs `dvc push`, ensuring your versioned data is uploaded to the DVC remote storage.
    *   **`dvc-post-checkout`**: When you `git pull` or `git checkout` a different branch, this hook automatically runs `dvc pull` to sync your local data with the version specified in the commit.
*   **Reproducibility**: This automated workflow ensures that anyone who clones the repository can retrieve the exact version of the data tied to a specific Git commit, making the project setup and pipeline runs highly reproducible.

### 3. Pipeline Orchestration
This project supports two popular orchestration tools, providing flexibility for different environments.

#### Using Prefect (Default)

The primary pipeline is defined using Prefect for its lightweight and Python-native approach, making it ideal for local development and rapid iteration.

*   **Workflow as Code**: The file `src/orchestrate.py` defines the entire DAG (Directed Acyclic Graph) of tasks.
*   **Simplicity**: Prefect allows for a simple, direct execution of the pipeline with a single command.
*   **Portability**: The orchestrator includes a task to automatically install all required Python packages from `requirements.txt`, making the project setup on a new machine seamless.

#### Using Airflow

For more complex scheduling and production-grade environments, an equivalent Airflow DAG is also included.
*   **Production-Ready**: Airflow provides a robust web UI, extensive logging, and powerful scheduling capabilities.
*   **DAG Definition**: The Airflow DAG is defined in `dags/customer_churn_dag.py`. It mirrors the logic in the Prefect flow and is designed to be run within a full Airflow installation.


## Data Sources

The pipeline can run on two different datasets, specified at runtime:

*   **Synthetic Data (default)**:
    *   **Source**: Generated locally by the pipeline scripts (`src/generate_csv_data.py` and `src/generate_api_data.py`).
    *   **Content**: This dataset simulates a realistic customer scenario. It includes:
        *   **Account Information**: Basic customer details like account start date, plan, and monthly charges.
        *   **Customer Interactions**: A stream of interactions such as support calls, website visits, and complaints, fetched from a mock API. An example interaction record looks like this:
            ```json
            {
                "customerID": "4f11d8dc-5cd3-4369-84aa-c1b75ca0c428",
                "interaction_date": "2025-06-21T00:31:14.398957",
                "interaction_type": "support_call",
                "interaction_details": "Agent every development say quality throughout."
            }
            ```

*   **Kaggle Data (`kaggle` parameter)**:
    *   **Source**: The classic Telco Customer Churn dataset from Kaggle.
    *   **Content**: This real-world dataset contains information about a fictional telco company's customers, including demographics, services subscribed to (phone, internet, etc.), account details, and whether they churned.

## Project Structure

```
├── data/
│   ├── raw/          # Raw, immutable data
│   ├── prepared/     # Cleaned and encoded data
│   └── transformed/  # Scaled features (Feature Store)
├── logs/             # Log files for each pipeline step
├── mlruns/           # MLflow experiment tracking data (autogenerated)
├── reports/          # Data validation reports (autogenerated)
├── src/              # All Python source code
│   ├── __init__.py
│   ├── orchestrate.py                # Main Prefect pipeline orchestrator
│   ├── feature_store.py              # Feature definitions and retrieval API
│   ├── generate_csv_data.py          # Generates synthetic customer account data
│   ├── generate_api_data.py          # Generates synthetic customer interaction data for the mock API
│   ├── data_ingest_kaggle.py         # Downloads data from Kaggle
│   ├── mock_api.py                   # A mock API server to simulate fetching real-time data
│   ├── ingest.py                     # Ingests data from all raw sources (CSV, API)
│   ├── validate_raw_data.py          # Validates raw data using Evidently AI
│   ├── prepare_data.py               # Cleans, encodes, and prepares data
│   ├── transform_and_store.py        # Creates features and stores them in the feature store
│   └── train_model_with_feature_store.py # Trains models and logs to MLflow
└── requirements.txt  # Project dependencies
```


## Getting Started

Follow these steps to set up and run the pipeline on a new machine.

### 1. Prerequisites

*   **Git**: To clone the repository.
*   **Bash-compatible shell** (like Git Bash on Windows, or any standard Linux/macOS terminal): To run the setup script.
*   **Python 3.8+**: The setup script will verify this for you.

### 2. Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/PK20701/MS-Portfolio.git
    cd DMML/Customer_churn_analysis
    ```

2.  **Run the setup script:**
    This script automates the entire setup process. It will:
    *   Check for the correct Python version.
    *   Create a virtual environment in `.venv/`.
    *   Install all required packages from `requirements.txt`.
    *   Configure a local DVC remote and pull the versioned data.

    ```bash
    bash setup.sh
    ```

3.  **Activate the virtual environment:**
    After the setup is complete, activate the newly created environment before running the pipeline:
    ```bash
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

### 3. Running the Pipeline

To execute the entire MLOps pipeline, run the orchestration script:

This pipeline can be run with two different data sources by providing a parameter to the main flow:
*   **synthetic** (default): Generates mock data locally.
*   **kaggle**: Downloads the "Telco Customer Churn" dataset from Kaggle.

To run with the default synthetic data:
```bash
python src/orchestrate.py
```

To run with the real-world Kaggle dataset:
```bash
python src/orchestrate.py kaggle
```

This script will:
1.  Generate or download raw data based on the `data_source` parameter.
2.  Ingest and validate it using Evidently AI.
3.  Transform features and update the feature store.
4.  Train the churn prediction model.
5.  Log experiments and metrics to MLflow.

## Viewing Results - Model Experiements

*   **Logs**: Check the `logs/` directory for detailed logs from each pipeline step.
*   **MLflow**: Launch the MLflow UI to view experiment runs, parameters, and metrics:
    ```bash
    mlflow ui
    ```
    Then navigate to `http://127.0.0.1:5000` in your browser.
*   **Data Validation Reports**: Open `reports/data_validation_report.html` to see the Evidently AI data validation report.
Sample - 
![alt text](image-1.png)
## Viewing Results - Orchestrator run

*   **Prefect**: Launch the MLflow UI to view experiment runs, parameters, and metrics:
    ```bash
    prefect server start
    ```
    Check out the dashboard at http://127.0.0.1:4200
    sample - 
    ![alt text](image.png) 