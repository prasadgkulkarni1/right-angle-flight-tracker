# Quick Start Guide

## The Problem

Port 5000 is being used by macOS ControlCenter (AirPlay Receiver). This is a common issue on macOS Monterey and later.

## ⚡ Quick Solutions

### Solution 1: Auto-Start (Recommended)

Use the smart start script that automatically finds an available port:

```bash
./start_app.sh
```

This will:
- ✅ Check port 5000, 5001, 8080, 8000
- ✅ Automatically use the first available port
- ✅ Start the app immediately

### Solution 2: Manual Port Selection

Choose your own port:

```bash
# Use port 5001
PORT=5001 python app.py

# Use port 8080
PORT=8080 python app.py

# Use any available port
PORT=3000 python app.py
```

### Solution 3: Kill Existing Process

Temporarily free up port 5000:

```bash
./kill_port_5000.sh
python app.py
```

⚠️ Note: ControlCenter may restart and reclaim port 5000

### Solution 4: Disable AirPlay (Permanent)

**macOS Ventura+:**
1. System Settings → General → AirDrop & Handoff
2. Uncheck "AirPlay Receiver"

**macOS Monterey:**
1. System Preferences → Sharing
2. Uncheck "AirPlay Receiver"

Then:
```bash
python app.py
```

## 🎯 Recommended Workflow

**Just run:**
```bash
./start_app.sh
```

The script will automatically find an available port and start your app!

## 📱 Accessing the App

After starting, access via:

- **Default (port 5000)**: http://127.0.0.1:5000
- **Port 5001**: http://127.0.0.1:5001
- **Port 8080**: http://127.0.0.1:8080
- **Custom port**: http://127.0.0.1:YOUR_PORT

## 🔧 Troubleshooting

### Check what's using a port:
```bash
lsof -i:5000
```

### Find available ports:
```bash
for port in {5000..5010}; do
    lsof -i:$port > /dev/null 2>&1 || echo "Port $port is available"
done
```

### View all helper scripts:
```bash
ls -la *.sh
```

## 📚 More Information

- **Detailed port fix**: See [PORT_CONFLICT_FIX.md](PORT_CONFLICT_FIX.md)
- **UI troubleshooting**: See [check_ui_status.md](check_ui_status.md)
- **Diagnostic tools**: Run `python diagnose_ui.py`

## ✅ Success!

Once running, you'll see:
```
🚀 Flight Tracker Web UI starting...
📍 Open http://localhost:5001 in your browser
📍 Or access via http://127.0.0.1:5001
```

Open that URL in your browser and the UI should load!
