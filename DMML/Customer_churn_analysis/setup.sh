#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting project setup..."

# --- 1. Check for Python 3.8+ ---
echo "🔎 Checking for Python 3.8+..."
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

python3 -c 'import sys; assert sys.version_info >= (3, 8), "Python 3.8+ is required. You have " + sys.version'
echo "✅ Python version check passed."

# --- 2. Create Virtual Environment ---
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    echo "ℹ️ Virtual environment '$VENV_DIR' already exists."
else
    echo "🐍 Creating Python virtual environment in '$VENV_DIR'..."
    python3 -m venv $VENV_DIR
    echo "✅ Virtual environment created."
fi

# --- 3. Install Dependencies ---
echo "📦 Installing dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install --upgrade pip > /dev/null
"$VENV_DIR/bin/pip" install -r requirements.txt
echo "✅ Dependencies installed."

# --- 4. Set up DVC ---
DVC_STORAGE_DIR="../customer-churn-dvc-storage"
echo "💿 Setting up DVC remote storage..."
if [ -d "$DVC_STORAGE_DIR" ]; then
    echo "ℹ️ DVC storage directory '$DVC_STORAGE_DIR' already exists."
else
    mkdir -p "$DVC_STORAGE_DIR"
    echo "✅ Created DVC storage directory at '$DVC_STORAGE_DIR'."
fi

"$VENV_DIR/bin/dvc" remote modify myremote url "$DVC_STORAGE_DIR"
echo "✅ DVC remote 'myremote' configured."

echo "⏬ Pulling data with DVC..."
"$VENV_DIR/bin/dvc" pull -q
echo "✅ Data pulled successfully."

# --- 5. Final Instructions ---
echo ""
echo "🎉 Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "   source $VENV_DIR/bin/activate"
echo ""
echo "Then, you can run the pipeline with:"
echo "   python src/orchestrate.py"