#!/bin/bash

# Companies House Scraper - Run Wrapper
# Automatically activates virtual environment and runs the scraper

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
    exit $?
fi

# Activate virtual environment
source venv/bin/activate

# Run scraper with all arguments passed through
python3 scraper.py "$@"

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

exit $EXIT_CODE
