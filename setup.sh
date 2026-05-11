#!/bin/bash
# Mini Claude Code - One-command setup
set -e

echo "=== Mini Claude Code Setup ==="

# Check for conda
if ! command -v conda &>/dev/null; then
    echo "ERROR: conda not found. Please install Miniconda first."
    exit 1
fi

# Create environment
if conda env list | grep -q "^minicc "; then
    echo "[✓] conda env 'minicc' already exists"
else
    echo "[*] Creating conda environment..."
    conda create -n minicc python=3.13 -y
    echo "[✓] Environment created"
fi

# Install dependencies
echo "[*] Installing Python packages..."
conda run -n minicc pip install -q -r requirements.txt
echo "[✓] Dependencies installed"

# Set up .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[!] Created .env from .env.example — please edit it to add your API key"
else
    echo "[✓] .env already exists"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your DeepSeek API key"
echo "  2. Run: source .env"
echo "  3. Run: python demo.py"
