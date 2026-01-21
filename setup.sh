#!/bin/bash
# Automated Setup Script for LinkedIn Scraper (Linux/Mac)
# Run this script to set up the project automatically

echo "============================================"
echo "LinkedIn Scraper - Automated Setup"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

echo "[1/5] Python detected..."
python3 --version
echo ""

# Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created."
fi
echo ""

# Activate virtual environment and install dependencies
echo "[3/5] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""

# Setup .env file
echo "[4/5] Setting up environment file..."
if [ -f ".env" ]; then
    echo ".env file already exists, skipping..."
else
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env file with your LinkedIn credentials"
    echo "File location: $(pwd)/.env"
    echo "Opening editor..."
    ${EDITOR:-nano} .env
fi
echo ""

# Final instructions
echo "[5/5] Setup complete!"
echo ""
echo "============================================"
echo "NEXT STEPS:"
echo "============================================"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Make sure your LinkedIn credentials are saved in .env"
echo "3. Run the scraper with:"
echo "   python scraper.py --profile PROFILE_ID"
echo ""
echo "Example:"
echo "   python scraper.py --profile williamhgates"
echo ""
echo "For help:"
echo "   python scraper.py --help"
echo ""
echo "============================================"
