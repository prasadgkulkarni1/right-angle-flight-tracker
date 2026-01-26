#!/bin/bash
# Script to kill process using port 5000

echo "🔍 Checking what's using port 5000..."

# Find process ID using port 5000
PID=$(lsof -ti:5000)

if [ -z "$PID" ]; then
    echo "✅ Port 5000 is free - nothing to kill"
    exit 0
fi

echo "📍 Found process(es) using port 5000:"
lsof -i:5000

echo ""
echo "🔪 Killing process(es): $PID"
kill -9 $PID

sleep 1

# Verify it's killed
STILL_RUNNING=$(lsof -ti:5000)
if [ -z "$STILL_RUNNING" ]; then
    echo "✅ Port 5000 is now free!"
    echo ""
    echo "You can now run: python app.py"
else
    echo "❌ Process still running. Try manually:"
    echo "   sudo kill -9 $STILL_RUNNING"
fi
