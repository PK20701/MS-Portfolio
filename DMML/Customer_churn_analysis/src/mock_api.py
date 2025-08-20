import json
import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

# --- Basic Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
