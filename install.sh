#!/usr/bin/env bash
# Installer for WoundCompute GUI on macOS / Linux.
# Prerequisite: Miniconda (or Anaconda) installed and on PATH.
# Usage: bash install.sh

set -euo pipefail

ENV_NAME="wound-compute-gui"
PY_VERSION="3.9.13"

if ! command -v conda >/dev/null 2>&1; then
    echo "ERROR: conda was not found on your PATH."
    echo
    echo "Please install Miniconda from:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    echo
    echo "After installing, close and re-open your terminal, then run this"
    echo "script again."
    exit 1
fi

# Make 'conda activate' work inside this non-interactive shell.
eval "$(conda shell.bash hook)"

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Conda environment '$ENV_NAME' already exists. Reusing it."
else
    echo "Creating conda environment '$ENV_NAME' (Python $PY_VERSION)..."
    conda create --name "$ENV_NAME" "python=$PY_VERSION" -y
fi

conda activate "$ENV_NAME"

echo "Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "Installing WoundCompute GUI and dependencies..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python -m pip install -e . --force-reinstall --no-cache-dir

echo
echo "Installation complete."
echo "To launch the GUI, run:  bash run.sh"
