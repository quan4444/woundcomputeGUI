#!/usr/bin/env bash
# Launches the WoundCompute GUI on macOS / Linux.
# Prerequisite: install.sh has been run successfully.
# Usage: bash run.sh

set -euo pipefail

ENV_NAME="wound-compute-gui"

if ! command -v conda >/dev/null 2>&1; then
    echo "ERROR: conda was not found on your PATH."
    echo "Please install Miniconda and run install.sh first."
    exit 1
fi

eval "$(conda shell.bash hook)"

if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "ERROR: conda environment '$ENV_NAME' does not exist."
    echo "Please run:  bash install.sh"
    exit 1
fi

conda activate "$ENV_NAME"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python run_wound_compute_gui.py
