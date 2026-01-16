#!/bin/bash

# Companies House Scraper - Setup Script
# This script sets up the Python environment and dependencies

set -e  # Exit on error

echo "🏗️  Companies House Scraper - Setup"
echo "===================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Check for Python 3
echo "📋 Step 1: Checking for Python 3..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Found: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 not found!"
    echo ""
    echo "Please install Python 3 from:"
    echo "  - Homebrew: brew install python3"
    echo "  - Official: https://www.python.org/downloads/"
    exit 1
fi

# Check Python version is 3.7+
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    echo -e "${RED}✗${NC} Python 3.7+ required (found $PYTHON_VERSION)"
    exit 1
fi

# Step 2: Create virtual environment
echo ""
echo "📦 Step 2: Setting up virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists"
fi

# Step 3: Activate virtual environment and install dependencies
echo ""
echo "📚 Step 3: Installing dependencies..."

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}✗${NC} requirements.txt not found!"
    exit 1
fi

# Step 4: Check for .env file
echo ""
echo "🔑 Step 4: Checking configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠${NC}  .env file not found. Creating from template..."
        cp .env.example .env
        echo -e "${YELLOW}⚠${NC}  Please edit .env and add your Companies House API key"
        echo ""
        echo "Get your API key from:"
        echo "  https://developer.company-information.service.gov.uk/"
        echo ""
        echo "Then run: ./run.sh 00000006 --dry-run"
    else
        echo -e "${RED}✗${NC} .env.example not found!"
        exit 1
    fi
else
    # Check if API key is set
    if grep -q "your_api_key_here" .env; then
        echo -e "${YELLOW}⚠${NC}  API key not configured in .env"
        echo ""
        echo "Please edit .env and add your Companies House API key"
        echo "Get your API key from:"
        echo "  https://developer.company-information.service.gov.uk/"
    else
        echo -e "${GREEN}✓${NC} Configuration file exists"
    fi
fi

# Step 5: Verify Python files
echo ""
echo "🔍 Step 5: Verifying installation..."
REQUIRED_FILES=("scraper.py" "api_client.py" "downloader.py" "validators.py")
ALL_FOUND=true

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file not found!"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = false ]; then
    echo -e "${RED}✗${NC} Missing required files!"
    exit 1
fi

# Test imports
echo ""
echo "Testing Python imports..."
if $PYTHON_CMD -c "import validators, api_client, downloader" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} All modules import successfully"
else
    echo -e "${RED}✗${NC} Import errors detected"
    echo "Run: source venv/bin/activate && python3 -c 'import validators, api_client, downloader'"
    exit 1
fi

# Step 6: Create run wrapper
echo ""
echo "📝 Step 6: Creating run script..."
cat > run.sh << 'WRAPPER_EOF'
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
WRAPPER_EOF

chmod +x run.sh
echo -e "${GREEN}✓${NC} Created run.sh wrapper script"

# Deactivate virtual environment
deactivate

echo ""
echo "===================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "===================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Add your API key to .env file:"
echo "   nano .env"
echo ""
echo "2. Test with dry-run:"
echo "   ./run.sh 00000006 --dry-run"
echo ""
echo "3. Run actual download:"
echo "   ./run.sh 00000006"
echo ""
echo "For help:"
echo "   ./run.sh --help"
echo ""
