import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_database(db_path: Path, schema_file: Path):
    """
    Sets up the database by executing a schema SQL script.
    This ensures the table structure is explicitly defined and version-controllable.
    
    Args:
        db_path (Path): The path to the SQLite database file.
        schema_file (Path): The path to the .sql file containing the schema definition.
    """
    logger.info(f"Setting up database at {db_path} using schema from {schema_file.name}")
    
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_file}")
        
    try:
        engine = create_engine(f'sqlite:///{db_path}')
        with engine.connect() as connection:
            # The default DB-API for SQLite doesn't support executing multiple
            # statements in a single .execute() call. We need to read the .sql file,
            # split it into individual statements, and execute them one by one.
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            # A transaction ensures that all statements succeed or none do.
            with connection.begin():
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        connection.execute(text(statement))
        logger.info("Database setup successful. 'churn_features' table created.")
    except Exception as e:
        logger.error(f"Failed to set up database: {e}", exc_info=True)
        raise

# This block allows the script to be run standalone for setup or testing.
if __name__ == "__main__":
    # --- Standalone Execution Configuration ---
    
    # Define paths relative to the project root
    project_root = Path(__file__).parent.parent
    LOG_DIR = project_root / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file_path = LOG_DIR / f"database_setup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    
    # Configure logging to route to a file instead of printing to the terminal.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path)
        ]
    )
    
    # Define database and schema paths for standalone run
    db_path = project_root / "data" / "transformed" / "churn_pipeline.db"
    schema_path = project_root / "src" / "database_setup.sql"
    
    # Ensure the directory for the database exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("Running database setup as a standalone script...")
        setup_database(db_path=db_path, schema_file=schema_path)
        print(f"Database setup complete. See log file for details: {log_file_path}")
    except Exception:
        # The logger will have already recorded the exception details to the file.
        print(f"An error occurred during database setup. Check the log file for details: {log_file_path}")