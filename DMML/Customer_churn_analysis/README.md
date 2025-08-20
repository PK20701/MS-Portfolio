# Customer Churn Prediction Pipeline

This project implements a full end-to-end MLOps pipeline for predicting customer churn. It includes data generation, ingestion, validation, transformation, model training with a feature store, and data versioning. The entire pipeline is orchestrated using Prefect.

## MLOps Components

This project incorporates several MLOps best practices to ensure reproducibility, scalability, and maintainability.

### 1. Feature Store

A lightweight, file-based feature store is implemented to provide a centralized, documented, and versioned source of features for model training.

*   **Registry**: Feature definitions and metadata (e.g., description, source, version) are centrally defined in `src/feature_store.py`. This file acts as the feature registry.
*   **Offline Store**: The final, transformed features are stored in a single Parquet file at `data/transformed/transformed_features.parquet`. This file is the single source of truth for model training.
*   **Retrieval API**: The `get_feature_view()` function in `src/feature_store.py` provides a consistent API to retrieve feature sets for training. The model training script uses this function exclusively to get its data, decoupling it from the physical data source.

### 2. Data Versioning with DVC

This project uses DVC (Data Version Control) to manage and version large data files that are not suitable for Git. This ensures that every Git commit can correspond to a specific, reproducible version of the data.

*   **Workflow**: The pipeline generates raw data which can then be versioned by a developer. The `dvc pull` command allows any user to retrieve the exact version of the data associated with a Git commit, ensuring that pipeline runs are reproducible.
*   **Automation**: While `dvc add` and `dvc push` are manual developer steps, `dvc pull` can be integrated into CI/CD or setup scripts to automate the retrieval of production-ready data.

### 3. Orchestration with Prefect

The entire pipeline is defined and orchestrated using Prefect.

*   **Workflow as Code**: The file `src/orchestrate.py` defines the entire DAG (Directed Acyclic Graph) of tasks, from data generation to model training.
*   **Dependency Management**: Prefect automatically manages the dependencies between tasks, ensuring they run in the correct order.
*   **Portability**: The orchestrator includes a task to automatically install all required Python packages from `requirements.txt`, making the project setup on a new machine seamless.

## Project Structure

```
├── data/
│   ├── raw/          # Raw, immutable data
│   ├── prepared/     # Cleaned and encoded data
│   └── transformed/  # Scaled features (Feature Store)
├── logs/             # Log files for each pipeline step
├── mlruns/           # MLflow experiment tracking data
├── reports/          # Data validation reports
├── src/              # All Python source code
│   ├── __init__.py
│   ├── orchestrate.py  # Main Prefect pipeline orchestrator
│   ├── feature_store.py# Feature definitions and retrieval API
│   └── ...           # Other pipeline scripts
│   ├── ...           # Other pipeline scripts
└── requirements.txt  # Project dependencies
```

## Getting Started

Follow these steps to set up and run the pipeline on a new machine.

### 1. Prerequisites

*   Python 3.8+
*   Git

### 2. Initial Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd Customer_churn_analysis
    ```

2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    The orchestration script handles most dependencies, but you need `prefect` and `dvc` to start.
    ```bash
    pip install -r requirements.txt
    ```

### 3. Data Versioning Setup (DVC)

This project uses DVC to manage data. To get the data required to run the pipeline, you need to configure a DVC remote.

1.  **Initialize DVC** (this has already been done for the project):
    ```bash
    dvc init
    ```

2.  **Configure DVC remote storage**:
    The project is configured to use a local directory as its remote storage. You can set this up as follows:

    ```bash
    # Create a directory for DVC remote storage (e.g., next to your project folder)
    mkdir ../customer-churn-dvc-storage

    # The project's .dvc/config is already set up to use a remote named `myremote`.
    # The command below modifies the URL for `myremote` to point to your new storage directory.
    dvc remote modify myremote url ../customer-churn-dvc-storage
    ```

3.  **Pull the data:**
    Once the remote is configured, pull the versioned data:
    ```bash
    dvc pull
    ```
    This will download the `data/` directory contents tracked by DVC, ensuring you have the correct dataset for the pipeline.

### 4. Running the Pipeline

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

## Viewing Results

*   **Logs**: Check the `logs/` directory for detailed logs from each pipeline step.
*   **MLflow**: Launch the MLflow UI to view experiment runs, parameters, and metrics:
    ```bash
    mlflow ui
    ```
    Then navigate to `http://127.0.0.1:5000` in your browser.
*   **Data Validation Reports**: Open `reports/data_validation_report.html` to see the Evidently AI data validation report.
