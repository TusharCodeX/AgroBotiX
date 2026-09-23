#!/usr/bin/env bash
echo "========================================================"
echo "  Starting AgriPath Rover Web System on Port 8000..."
echo "========================================================"

# Activate virtualenv if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Launching FastAPI + React UI at http://0.0.0.0:8000"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
