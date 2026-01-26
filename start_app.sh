#!/bin/bash
# Simple script to start the Flight Tracker app with automatic port detection

echo "🔍 Checking port availability..."

# Function to check if port is in use
check_port() {
    lsof -i:$1 > /dev/null 2>&1
    return $?
}

# Try ports in order: 5000, 5001, 8080, 8000
PORTS=(5000 5001 8080 8000)
SELECTED_PORT=""

for port in "${PORTS[@]}"; do
    if ! check_port $port; then
        SELECTED_PORT=$port
        break
    fi
done

if [ -z "$SELECTED_PORT" ]; then
    echo "❌ Ports 5000, 5001, 8080, and 8000 are all in use!"
    echo ""
    echo "Solutions:"
    echo "1. Kill process on port 5000: ./kill_port_5000.sh"
    echo "2. Specify custom port: PORT=3000 python app.py"
    echo "3. Check what's using ports: lsof -i:5000"
    exit 1
fi

if [ "$SELECTED_PORT" != "5000" ]; then
    echo "ℹ️  Port 5000 is in use, using port $SELECTED_PORT instead"
fi

echo "🚀 Starting Flight Tracker on port $SELECTED_PORT..."
echo ""

PORT=$SELECTED_PORT python app.py
