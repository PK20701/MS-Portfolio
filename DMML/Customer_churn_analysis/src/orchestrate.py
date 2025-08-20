import time
import subprocess
import sys
from pathlib import Path

from prefect import flow, task, get_run_logger

# --- Add src to path to allow for imports ---
# This assumes the script is run from the project root (e.g., `python src/orchestrate.py`)
def setup_path():
    project_root = Path(__file__).parent.parent
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

setup_path()

# --- Import main functions from your project scripts ---
try:
    from generate_csv_data import main as generate_csv_data_main
    from data_ingest_kaggle import main as data_ingest_kaggle_main
    from generate_api_data import main as generate_api_data_main
    from ingest import main as ingest_main
    from validate_raw_data import main as validate_raw_data_main
    from prepare_data import main as prepare_data_main
    from transform_and_store import main as transform_and_store_main
    from train_model_with_feature_store import main as train_model_main
except ImportError as e:
    # Provide a more helpful error message
    print("Error: Could not import a required module.", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    print("Please ensure that all required scripts (generate_csv_data.py, ingest.py, etc.) exist in the 'src/' directory and have a 'main()' function.", file=sys.stderr)
    sys.exit(1)

# --- Prefect Tasks ---

@task(name="Check and Install Dependencies")
def check_and_install_dependencies_task():
    """
    Checks if all packages in requirements.txt are installed and installs them if not.
    """
    logger = get_run_logger()
    project_root = Path(__file__).parent.parent
    requirements_path = project_root / "requirements.txt"

    if not requirements_path.exists():
        logger.warning(f"{requirements_path} not found. Skipping dependency check.")
        return

    logger.info("Checking for missing Python packages from requirements.txt...")
    with open(requirements_path) as f:
        # Read requirements, ignoring comments and empty lines
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Use the modern 'importlib.metadata' and 'packaging' libraries
    # to avoid the deprecated 'pkg_resources'.
    from importlib import metadata
    from packaging.requirements import Requirement

    missing_packages = []
    for req_str in requirements:
        try:
            req = Requirement(req_str)
            installed_version = metadata.version(req.name)
            # The 'prereleases=True' argument allows for matching pre-release versions
            # if they are specified in requirements.txt, which is a reasonable default.
            if not req.specifier.contains(installed_version, prereleases=True):
                logger.warning(
                    f"Requirement '{req_str}' has a version conflict. "
                    f"Installed: {installed_version}, Required: {req.specifier}"
                )
                missing_packages.append(req_str)
            else:
                logger.info(f"Requirement '{req_str}' is met.")
        except metadata.PackageNotFoundError:
            logger.warning(f"Requirement '{req_str}' is NOT met (package not found).")
            missing_packages.append(req_str)

    if missing_packages:
        logger.info("Installing missing or conflicting packages...")
        try:
            # Using '-U' to ensure that packages with version conflicts are upgraded.
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "-r", str(requirements_path)])
            logger.info("All required packages installed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install packages from {requirements_path}. Error: {e}")
            raise
    else:
        logger.info("All required packages are already installed.")

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
        logger.info("Downloading Telco Customer Churn data from Kaggle...")
        data_ingest_kaggle_main()
    elif source == "synthetic":
        logger.info("Generating synthetic customer_accounts.csv...")
        generate_csv_data_main()
    else:
        raise ValueError(f"Unknown data_source: '{source}'. Must be 'synthetic' or 'kaggle'.")

    logger.info("Generating interactions.json for mock API...")
    generate_api_data_main()
    logger.info("Raw data generation complete.")

@task(name="Ingest Data", retries=3, retry_delay_seconds=5)
def ingest_data_task():
    """Runs the data ingestion script."""
    logger = get_run_logger()
    logger.info("Starting data ingestion...")
    ingest_main()
    logger.info("Data ingestion complete.")

@task(name="Validate Raw Data")
def validate_data_task():
    """Runs the raw data validation script."""
    logger = get_run_logger()
    logger.info("Starting raw data validation...")
    validate_raw_data_main()
    logger.info("Raw data validation complete.")

@task(name="Prepare Data")
def prepare_data_task():
    """Runs the data preparation script (cleaning, encoding)."""
    logger = get_run_logger()
    logger.info("Starting data preparation...")
    prepare_data_main()
    logger.info("Data preparation complete.")

@task(name="Transform and Store Features")
def transform_data_task():
    """Runs the feature transformation and storage script."""
    logger = get_run_logger()
    logger.info("Starting feature transformation and storage...")
    transform_and_store_main()
    logger.info("Feature transformation and storage complete.")

@task(name="Train and Log Models")
def train_models_task():
    """Runs the model training and MLflow logging script."""
    logger = get_run_logger()
    logger.info("Starting model training and logging...")
    train_model_main()
    logger.info("Model training and logging complete.")

# --- Main Pipeline Flow ---

@flow(name="Customer Churn End-to-End Pipeline")
def customer_churn_pipeline(data_source: str = "synthetic"):
    """
    Orchestrates the entire customer churn prediction pipeline, from data
    generation to model training, managing dependencies and the mock API server.

    Args:
        data_source (str): 'synthetic' to generate data, or 'kaggle' to download from Kaggle.
    """
    logger = get_run_logger()
    logger.info(f"Starting the Customer Churn Pipeline with data_source='{data_source}'...")

    # Step 0: Check and install dependencies. This must run first.
    dependencies_future = check_and_install_dependencies_task.submit()

    api_process = None
    try:
        # Step 1: Generate all necessary raw data files. Wait for dependencies.
        gen_future = get_raw_data_task.submit(source=data_source, wait_for=[dependencies_future])

        # Start the mock API server in the background after data is generated.
        # It needs interactions.json to exist.
        logger.info("Starting mock API server in the background...")
        # Use wait_for to ensure data is generated before starting the API
        gen_future.wait() 
        project_root = Path(__file__).parent.parent
        api_script_path = project_root / "src" / "mock_api.py"
        # Using sys.executable ensures we use the same python interpreter.
        api_process = subprocess.Popen([sys.executable, str(api_script_path)])
        logger.info(f"Mock API server started with PID: {api_process.pid}. Waiting a moment for it to initialize...")
        time.sleep(5) # Give the server a few seconds to start up.

        # Step 2: Ingest data. This depends on data generation and the API server.
        ingest_future = ingest_data_task.submit(wait_for=[gen_future])

        # Step 3: Validate, Prepare, and Transform the data.
        validate_future = validate_data_task.submit(wait_for=[ingest_future])
        prepare_future = prepare_data_task.submit(wait_for=[validate_future])
        transform_future = transform_data_task.submit(wait_for=[prepare_future])

        # Step 4: Train the models.
        train_future = train_models_task.submit(wait_for=[transform_future])
        
        # Wait for the final task to complete before shutting down.
        train_future.wait()
        logger.info("Pipeline execution successful.")

    except Exception as e:
        logger.critical(f"Pipeline failed with error: {e}", exc_info=True)
        # Re-raise the exception to make the Prefect flow fail.
        raise
    finally:
        if api_process:
            logger.info(f"Terminating mock API server (PID: {api_process.pid})...")
            api_process.terminate()
            api_process.wait(timeout=10) # Wait for process to terminate
            if api_process.poll() is None:
                logger.warning("API server did not terminate gracefully, killing it.")
                api_process.kill()
            logger.info("Mock API server terminated.")

if __name__ == "__main__":
    # This allows running the script with a command-line argument.
    # Example: python src/orchestrate.py kaggle
    source = "synthetic"
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source not in ["synthetic", "kaggle"]:
            print(f"Error: Invalid data_source '{source}'. Choose 'synthetic' or 'kaggle'.", file=sys.stderr)
            sys.exit(1)
    customer_churn_pipeline(data_source=source)