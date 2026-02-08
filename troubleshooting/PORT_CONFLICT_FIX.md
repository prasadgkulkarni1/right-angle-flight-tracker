# Port 5000 Conflict Fix

## Problem

Port 5000 is being used by macOS ControlCenter (AirPlay Receiver).

```
COMMAND   PID           USER   FD   TYPE   NODE NAME
ControlCe 644 prasadkulkarni   11u  IPv4   TCP *:commplex-main (LISTEN)
```

## Solutions

### Option 1: Use a Different Port (RECOMMENDED)

The easiest solution is to use port 5001 or 8080 instead:

**Quick Start:**
```bash
# Use port 5001
python app.py --port 5001

# Or set environment variable
PORT=5001 python app.py

# Or use port 8080
PORT=8080 python app.py
```

**Access via:**
- http://127.0.0.1:5001
- http://localhost:5001

### Option 2: Disable AirPlay Receiver (macOS)

Permanently disable the macOS service using port 5000:

1. **Open System Settings/Preferences**
2. **Go to:**
   - **macOS Ventura+**: Settings → General → AirDrop & Handoff
   - **macOS Monterey**: System Preferences → Sharing
3. **Uncheck "AirPlay Receiver"**
4. **Restart Terminal**

**Then:**
```bash
python app.py
```

### Option 3: Kill the Process (Temporary)

Kill the process temporarily (it may restart):

```bash
# Quick kill
./kill_port_5000.sh

# Or manually
lsof -ti:5000 | xargs kill -9

# Then start Flask
python app.py
```

⚠️ **Warning**: The ControlCenter process may restart automatically.

## Using Different Ports

### Update app.py (Already Done)

I'll update app.py to support PORT environment variable:

```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Flights Finder Web UI starting on port {port}...")
```

### Usage Examples

```bash
# Default port 5000
python app.py

# Use port 5001
PORT=5001 python app.py

# Use port 8080
PORT=8080 python app.py

# Use port 3000
PORT=3000 python app.py
```

## Checking Port Status

```bash
# Check if port is in use
lsof -i:5000

# Check specific port
lsof -i:5001

# Find available ports
for port in {5000..5010}; do
    lsof -i:$port > /dev/null 2>&1 || echo "Port $port is available"
done
```

## Recommended Solution

**Use port 5001** - it's rarely used and easy to remember:

```bash
PORT=5001 python app.py
```

Then access: **http://127.0.0.1:5001**

## Update Static Files for Different Port

If you use a different port permanently, update the frontend if it has hardcoded API URLs (currently it uses relative URLs, so no change needed).

## Quick Commands

```bash
# 1. Kill any process on 5000 (temporary)
./kill_port_5000.sh

# 2. Or use different port (permanent solution)
PORT=5001 python app.py

# 3. Or disable AirPlay in System Settings
```

Choose the solution that works best for your workflow!
