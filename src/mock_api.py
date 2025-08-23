import json
import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
from pathlib import Path

# --- Logger Configuration ---
project_root = Path(__file__).parent.parent
LOG_DIR = project_root / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a logger for this specific module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent log messages from being passed to the root logger's handlers
logger.propagate = False

# Avoid adding handlers if they already exist (e.g., from a previous import)
if not logger.handlers:
    log_file_path = LOG_DIR / f"mock_api_{datetime.now().strftime('%Y-%m-%d')}.log"

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

# --- Project Root Configuration ---
# Assumes this script is in a 'src' directory inside the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERACTIONS_JSON_PATH = os.path.join(project_root, 'data', 'raw', 'interactions.json')

app = FastAPI(title="Mock Customer Interactions API")

class Interaction(BaseModel):
    customerID: str
    interaction_date: str
    interaction_type: str
    interaction_details: str

# --- Data Loading ---
mock_interactions = []
try:
    with open(INTERACTIONS_JSON_PATH, 'r', encoding='utf-8') as f:
        mock_interactions = json.load(f)
    logger.info(f"Successfully loaded {len(mock_interactions)} interaction records from {INTERACTIONS_JSON_PATH}")
except FileNotFoundError:
    logger.warning(f"{INTERACTIONS_JSON_PATH} not found. API will return an empty list.")
    logger.warning("Please run 'generate_api_data.py' first to create the data.")
except json.JSONDecodeError:
    logger.warning(f"Could not decode JSON from {INTERACTIONS_JSON_PATH}. API will return an empty list.")

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint that provides a welcome message and basic API information.
    """
    return {
        "message": "Welcome to the Mock Customer Interactions API!",
        "api_data_endpoint": "/api/interactions",
        "api_docs": "/docs"
    }

@app.get("/api/interactions", response_model=List[Interaction], tags=["Interactions"])
def get_interactions():
    """Returns a list of recent customer interactions."""
    return mock_interactions

# To run this API: uvicorn mock_api:app --reload

if __name__ == "__main__":
    import uvicorn
    # This allows running the API directly with `python mock_api.py` from the src folder
    # or `python -m src.mock_api` from the project root.
    uvicorn.run("mock_api:app", host="127.0.0.1", port=8000, reload=True)
