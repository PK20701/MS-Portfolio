import time
import subprocess
import sys
from pathlib import Path
import logging
from datetime import datetime

from prefect import flow, task, get_run_logger
from requests import get
from requests.exceptions import ConnectionError

# --- Add src to path to allow for imports ---
# This assumes the script is run from the project root (e.g., `python src/orchestrate.py`)
def setup_path():
    project_root = Path(__file__).parent.parent
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

setup_path()

# --- Logger for main execution block ---
def setup_main_logger():
    """Sets up a logger for the __main__ block to log to file and console."""
    log = logging.getLogger('orchestrator_main')
    log.setLevel(logging.INFO)
    
    # Prevent passing logs to the root logger to avoid conflicts with Prefect's logging
    log.propagate = False

    # Avoid adding handlers if they already exist (e.g., in an interactive session)
    if not log.handlers:
        project_root = Path(__file__).parent.parent
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"orchestration_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        
        # File handler - logs everything with a detailed format
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        log.addHandler(fh)

        # Console handler - for user-friendly terminal output with a simpler format
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(ch)
    
    return log

# --- Prefect Tasks ---

@task(name="Get Raw Data", retries=3, retry_delay_seconds=10)
def get_raw_data_task(source: str):
    """
    Runs data generation/ingestion based on the source.
    'synthetic': generates data locally.
    'kaggle': downloads data from Kaggle.
    """
    logger = get_run_logger()
    logger.info(f"Starting raw data acquisition from source: '{source}'")

    if source == "kaggle":
        from data_ingest_kaggle import main as data_ingest_kaggle_main
        logger.info("Downloading Telco Customer Churn data from Kaggle...")
        data_ingest_kaggle_main()
    elif source == "synthetic":
        from generate_csv_data import main as generate_csv_data_main
        logger.info("Generating synthetic customer_accounts.csv...")
        generate_csv_data_main()
    else:
        raise ValueError(f"Unknown data_source: '{source}'. Must be 'synthetic' or 'kaggle'.")

    from generate_api_data import main as generate_api_data_main
    logger.info("Generating interactions.json for mock API...")
    generate_api_data_main()
    logger.info("Raw data generation complete.")

@task(name="Ingest Data", retries=3, retry_delay_seconds=5)
def ingest_data_task():
    """Runs the data ingestion script."""
    logger = get_run_logger()
    logger.info("Starting data ingestion...")
    from ingest import main as ingest_main
    ingest_main()
    logger.info("Data ingestion complete.")

@task(name="Validate Raw Data")
def validate_data_task():
    """Runs the raw data validation script."""
    logger = get_run_logger()
    logger.info("Starting raw data validation...")
    from validate_raw_data import main as validate_raw_data_main
    validate_raw_data_main()
    logger.info("Raw data validation complete.")

@task(name="Prepare Data")
def prepare_data_task():
    """Runs the data preparation script (cleaning, encoding)."""
    logger = get_run_logger()
    logger.info("Starting data preparation...")
    from prepare_data import main as prepare_data_main
    prepare_data_main()
    logger.info("Data preparation complete.")

@task(name="Transform and Store Features")
def transform_data_task():
    """Runs the feature transformation and storage script."""
    logger = get_run_logger()
    logger.info("Starting feature transformation and storage...")
    from transform_and_store import main as transform_and_store_main
    transform_and_store_main()
    logger.info("Feature transformation and storage complete.")

@task(name="Train and Log Models")
def train_models_task():
    """Runs the model training and MLflow logging script."""
    logger = get_run_logger()
    logger.info("Starting model training and logging...")
    from train_model_with_feature_store import main as train_model_main
    train_model_main()
    logger.info("Model training and logging complete.")

# --- Main Pipeline Flow ---

@flow(name="Customer Churn End-to-End Pipeline")
def customer_churn_pipeline(data_source: str = "synthetic"):
    """
    Orchestrates the entire customer churn prediction pipeline, from data
    generation to model training, managing the mock API server.

    It is assumed that all dependencies have been installed via `setup.sh`
    before running this pipeline.

    Args:
        data_source (str): 'synthetic' to generate data, or 'kaggle' to download from Kaggle.
    """
    logger = get_run_logger()
    # --- Configure Logging for this Flow Run ---
    # The goal is to send detailed logs to a file and only show warnings on the console.
    # We achieve this by removing Prefect's default handlers and adding our own.
    # The logger from get_run_logger() is a standard library logger, so we use its API.

    # Get the underlying standard library logger instance from the Prefect adapter
    base_logger = logger.logger

    # Clear existing handlers to prevent duplicate logging to the console
    if base_logger.hasHandlers():
        base_logger.handlers.clear()

    # 1. Create and add a new, quieter console handler for WARNINGs and above.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(levelname)-8s | %(name)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    base_logger.addHandler(console_handler)

    # 2. Create and add a file handler to capture all logs (INFO and above).
    log_file_path = Path(__file__).parent.parent / "logs" / f"flow_run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_formatter)
    base_logger.addHandler(file_handler)

    # The logger is now configured. The first message is a warning to ensure it appears on the console.
    logger.warning(f"Console logging is set to WARNING. Detailed logs are in: {log_file_path.name}")
    logger.info(f"Starting the Customer Churn Pipeline with data_source='{data_source}'...")

    api_process = None  # Initialize here to ensure it's available in `finally`
    try:
        # Step 1: Generate all necessary raw data files.
        gen_future = get_raw_data_task.submit(source=data_source)
        # Block until data generation is complete before starting the API server.
        gen_future.wait()

        # --- API Server Management Block ---
        # The API server is only needed for the ingestion step.
        # We will start it, run ingestion, and then shut it down.
        logger.info("Starting mock API server for data ingestion...")
        project_root = Path(__file__).parent.parent
        api_script_path = project_root / "src" / "mock_api.py"
        # Using sys.executable ensures we use the same python interpreter.
        api_process = subprocess.Popen([sys.executable, str(api_script_path)])
        logger.info(f"Mock API server started with PID: {api_process.pid}. Waiting for it to become available...")

        api_url = "http://127.0.0.1:8000/"
        max_retries = 10
        retry_delay = 3  # seconds

        # Robust health check for the API server
        for i in range(max_retries):
            try:
                # Use a timeout to avoid waiting indefinitely
                response = get(api_url, timeout=5)
                if response.status_code == 200:
                    logger.info("Mock API server is up and running.")
                    break
            except ConnectionError:
                logger.info(f"API not yet available. Retrying in {retry_delay}s... (Attempt {i+1}/{max_retries})")
                time.sleep(retry_delay)
        else: # This 'else' belongs to the 'for' loop, it runs if the loop completes without a 'break'
            logger.error("Mock API server failed to start within the timeout period.")
            raise RuntimeError("Could not connect to the mock API server.")

        # Step 2: Ingest data. This is the only step that needs the API.
        ingest_future = ingest_data_task.submit(wait_for=[gen_future])
        # Wait for ingestion to complete before shutting down the API.
        ingest_future.wait()

        # --- End of API Server Management Block ---
        # Terminate the API server now that ingestion is complete.
        logger.info(f"Data ingestion complete. Terminating mock API server (PID: {api_process.pid})...")
        api_process.terminate()
        try:
            api_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("API server did not terminate gracefully after 10s. Killing it.")
            api_process.kill()
        logger.info("Mock API server shut down.")
        api_process = None # Set to None so the `finally` block doesn't try to terminate it again.

        # Step 3: Validate, Prepare, and Transform the data.
        validate_future = validate_data_task.submit(wait_for=[ingest_future])
        prepare_future = prepare_data_task.submit(wait_for=[validate_future])
        transform_future = transform_data_task.submit(wait_for=[prepare_future])

        # Step 4: Train the models.
        train_future = train_models_task.submit(wait_for=[transform_future])

        # Wait for the final task to complete.
        train_future.wait()
        logger.info("Pipeline execution successful.")

    except Exception as e:
        logger.critical(f"Pipeline failed with error: {e}", exc_info=True)
        # Re-raise the exception to make the Prefect flow fail.
        raise
    finally:
        # This `finally` block acts as a safety net. If the API process was
        # started but an error occurred before the planned shutdown,
        # this will ensure it gets terminated.
        if api_process and api_process.poll() is None:
            logger.warning(f"Terminating mock API server (PID: {api_process.pid}) due to an exception...")
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("API server did not terminate gracefully during exception handling. Killing it.")
                api_process.kill()
            logger.info("Mock API server terminated in finally block.")

if __name__ == "__main__":
    # Set up the logger for this execution script
    main_logger = setup_main_logger()

    # This allows running the script with a command-line argument.
    # Example: python src/orchestrate.py kaggle
    source = "synthetic"
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source not in ["synthetic", "kaggle"]:
            main_logger.error(f"Error: Invalid data_source '{source}'. Choose 'synthetic' or 'kaggle'.")
            sys.exit(1)

    try:
        # Run the Prefect flow. It will raise an exception on failure.
        customer_churn_pipeline(data_source=source)
        main_logger.info("\n[SUCCESS] Pipeline finished successfully!")
        main_logger.info("   The generated data, models, and logs are ready.")
        main_logger.info("   You can now manually commit any changes to Git.")
        main_logger.info("   Remember to run 'dvc push' if you want to share the data.")

    except Exception as e:
        # The logger inside the flow already prints details for Prefect errors.
        # This catches the re-raised exception from the flow or other unexpected errors.
        main_logger.critical(f"\n[FAILED] Pipeline execution failed with an unexpected error: {e}", exc_info=True)
        sys.exit(1)