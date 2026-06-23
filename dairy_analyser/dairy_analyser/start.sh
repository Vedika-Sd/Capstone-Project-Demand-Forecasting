#!/bin/bash
echo "=== Krishna Dairy Sales Analyser ==="
echo "Installing dependencies..."
pip install -r requirements.txt --break-system-packages -q

echo ""
echo "Starting backend server on http://127.0.0.1:8000"
echo "Open your browser at: http://127.0.0.1:8000"
echo ""
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
