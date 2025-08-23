
#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting project setup..."

# --- 1. Check for Python 3.8+ ---
echo "🔎 Checking for a valid Python 3.8+ command..."
PYTHON_CMD=""

# On Windows, the 'py.exe' launcher is the most reliable way to find Python,
# as it bypasses issues with PATH and the Microsoft Store aliases.
# We check for it first. OSTYPE 'msys' is for Git Bash.
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]] && command -v py &>/dev/null; then
    # Prefer 'py -3' to get a Python 3 version, but fall back to just 'py'
    if py -3 --version &>/dev/null; then
        PYTHON_CMD="py -3"
    else
        PYTHON_CMD="py"
    fi
fi

# If 'py' wasn't found, or if not on Windows, fall back to the standard python3/python check.
if [ -z "$PYTHON_CMD" ]; then
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Python could not be found. Please install Python 3.8+ and ensure it's in your PATH."
        echo "   On Windows, it is recommended to install Python from python.org and select 'Add Python to PATH'."
        exit 1
    fi
fi

# Now, perform the definitive version check with the selected command.
# Using 'eval' is a safe way to handle commands that might contain spaces (like "py -3").
if ! eval "$PYTHON_CMD -c 'import sys; exit(0) if sys.version_info >= (3, 8) else exit(1)'"; then
    PYTHON_VERSION=$(eval "$PYTHON_CMD -c 'import sys; print(\".\".join(map(str, sys.version_info[:3])))'")
    echo "❌ Python 3.8+ is required, but version $PYTHON_VERSION was found with the command '$PYTHON_CMD'."
    echo "   Please upgrade your Python installation."
    exit 1
fi

echo "✅ Python version check passed. Using: $(eval $PYTHON_CMD --version)"

# --- 2. Create Virtual Environment ---
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    echo "ℹ️ Virtual environment '$VENV_DIR' already exists."
else
    echo "🐍 Creating Python virtual environment in '$VENV_DIR'..."
    eval "$PYTHON_CMD -m venv $VENV_DIR"
    echo "✅ Virtual environment created."
fi
 
# --- Define the path to the venv executables based on OS ---
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # On Windows (using Git Bash), executables are in Scripts
    VENV_BIN_DIR="$VENV_DIR/Scripts"
else
    # On Linux/macOS, executables are in bin
    VENV_BIN_DIR="$VENV_DIR/bin"
fi
 
# --- 3. Install Dependencies ---
echo "📦 Installing dependencies from requirements.txt..."
# Use python -m pip to be robust, especially on Windows where calling pip.exe directly can cause self-upgrade issues.
# Use -q for quiet install and redirect stderr to keep the log clean.
"$VENV_BIN_DIR/python" -m pip install -q --upgrade pip 2>/dev/null
"$VENV_BIN_DIR/python" -m pip install -q -r requirements.txt
echo "✅ Dependencies installed."

# --- 4. Set up DVC ---
# --- 4. Set up DVC ---
DVC_STORAGE_DIR="../customer-churn-dvc-storage"
echo "💿 Setting up DVC remote storage..."
if [ -d "$DVC_STORAGE_DIR" ]; then
    echo "ℹ️ DVC storage directory '$DVC_STORAGE_DIR' already exists."
else
    mkdir -p "$DVC_STORAGE_DIR"
    echo "✅ Created DVC storage directory at '$DVC_STORAGE_DIR'."
fi

# Get the directory where the script is located (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize Git repo if not already initialized
if [ ! -d "$SCRIPT_DIR/.git" ]; then
    echo "🔧 Initializing Git repository..."
    (cd "$SCRIPT_DIR" && git init -q)
    echo "✅ Git repository initialized."
fi

# Initialize DVC repo if not already initialized
if [ ! -d "$SCRIPT_DIR/.dvc" ]; then
    echo "🔧 Initializing DVC repository..."
    echo "DVC path: $VENV_BIN_DIR/dvc"
    "$VENV_BIN_DIR/dvc" --version
    echo "Running: (cd \"$SCRIPT_DIR\" && \"$VENV_BIN_DIR/dvc\" init --quiet)"
    # Initialize DVC to work with the Git repository.
    DVC_INIT_OUTPUT=$(cd "$SCRIPT_DIR" && "$VENV_BIN_DIR/dvc" init --quiet 2>&1) || {
        echo "❌ DVC initialization failed. Error output:"
        echo "$DVC_INIT_OUTPUT"
        exit 1
    }
    echo "✅ DVC repository initialized."
fi

# Use 'dvc remote add --force' to create the remote if it doesn't exist,
# or update it if it does. This makes the script idempotent.
(cd "$SCRIPT_DIR" && "$VENV_BIN_DIR/dvc" remote add --force myremote "$DVC_STORAGE_DIR")
echo "✅ DVC remote 'myremote' configured."
echo "⏬ Pulling data with DVC..."
(cd "$SCRIPT_DIR" && "$VENV_BIN_DIR/dvc" pull -q)
echo "✅ Data pulled successfully."

# --- 5. Set up pre-commit hook for automatic data versioning ---
echo "⚙️  Setting up pre-commit hook for automatic data versioning..."

# Install pre-commit
"$VENV_BIN_DIR/python" -m pip install -q pre-commit

PRE_COMMIT_CONFIG=".pre-commit-config.yaml"
if [ -f "$PRE_COMMIT_CONFIG" ]; then
    echo "ℹ️ $PRE_COMMIT_CONFIG already exists, skipping creation."
else
    echo "📝 Creating $PRE_COMMIT_CONFIG..."
    # This hook will automatically run `dvc add` on any DVC-tracked files
    # that have been modified before you make a commit.
    # We use the URL without .git as it's more robust against certain Git/tool bugs on Windows.
    cat > "$PRE_COMMIT_CONFIG" << EOL
repos:
-   repo: https://github.com/PK20701/MS-Portfolio.git
    rev: 3.0.0
    hooks:
    -   id: dvc-auto-add
EOL
    echo "✅ Created $PRE_COMMIT_CONFIG"
fi

# Install the git hook into the .git/ directory
"$VENV_BIN_DIR/pre-commit" install
echo "✅ pre-commit hook installed."

# --- 6. Final Instructions ---
echo ""
echo "🎉 Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    echo "   source $VENV_DIR/Scripts/activate"
else
    echo "   source $VENV_DIR/bin/activate"
fi
echo ""
echo "✅ Automatic data versioning is now enabled."
echo "   When you modify a DVC-tracked file and run 'git commit',"
echo "   the changes will be automatically added to DVC and staged for you."
echo ""
echo "To run the pipeline, use: python src/orchestrate.py"