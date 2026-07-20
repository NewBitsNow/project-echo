#!/bin/bash
# =============================================================================
# Project Echo — One-Command Installer
# =============================================================================
# Usage: curl -fsSL https://raw.githubusercontent.com/NewBitsNow/echo-core/main/install.sh | bash
# =============================================================================

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      Project Echo — Installer                               ║"
echo "║      Your digital twin, one command at a time               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# --- Check prerequisites ---
echo "📋 Checking prerequisites..."

# Python 3.11+
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "  ✓ Python $PY_VERSION"
else
    echo "  ✗ Python 3 not found. Install with: brew install python@3.12"
    exit 1
fi

# Hermes Agent
if command -v hermes &>/dev/null; then
    echo "  ✓ Hermes Agent"
else
    echo "  ✗ Hermes Agent not found. Install from: https://hermes-agent.nousresearch.com/docs"
    exit 1
fi

# Git
if command -v git &>/dev/null; then
    echo "  ✓ git"
else
    echo "  ⚠ git not found — install with: brew install git"
fi

# Pip
if python3 -m pip --version &>/dev/null; then
    echo "  ✓ pip"
else
    echo "  ✗ pip not found"
    exit 1
fi

echo ""

# --- Install echo-core ---
echo "📦 Installing echo-core..."
python3 -m pip install -e . 2>&1 | tail -2
echo ""

# --- Run setup wizard ---
echo "🔮 Launching setup wizard..."
echo ""
python3 -c "from echo_core.wizard import main; main()"