# UI Troubleshooting Guide

## Issue: Blank UI / Localhost Not Working

### Quick Fixes

#### 1. localhost Resolution Issue

If localhost isn't working but IP address works:

**Check /etc/hosts:**
```bash
cat /etc/hosts | grep localhost
```

Should contain:
```
127.0.0.1       localhost
::1             localhost
```

**Fix if missing:**
```bash
sudo nano /etc/hosts
# Add the lines above if missing
```

#### 2. Access via IP Address

If localhost doesn't work, use your IP address:

**Find your IP:**
```bash
# macOS
ipconfig getifaddr en0

# Or check all interfaces
ifconfig | grep "inet "
```

**Start app to listen on all interfaces:**
```bash
# Modify app.py line 196 to:
app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
```

Then access via: `http://<your-ip>:5000`

#### 3. Check if Static Files Are Loading

Open browser DevTools (F12 or Cmd+Option+I) and check:

**Console tab:**
- Look for errors loading CSS/JS files
- Common error: "Failed to load resource" for /static/style.css or /static/app.js

**Network tab:**
- Check if CSS and JS files return 200 status
- If they return 404, static routing is broken

**Solution:** I've already added explicit static file routing to app.py

#### 4. Verify Flask is Running Correctly

```bash
# Start the app
python app.py

# Should see:
# 🚀 Flight Tracker Web UI starting...
# 📍 Open http://localhost:5000 in your browser
# * Running on http://127.0.0.1:5000
```

#### 5. Test Static Files Directly

With Flask running, test in a new terminal:

```bash
# Test HTML
curl http://localhost:5000/ | head -20

# Test CSS
curl http://localhost:5000/static/style.css | head -10

# Test JS
curl http://localhost:5000/static/app.js | head -10

# Or via IP
curl http://YOUR_IP:5000/ | head -20
```

All should return content, not 404.

### Common Causes of Blank UI

1. **Static files not loading (404 errors)**
   - Fix: Explicit static route added to app.py
   - Verify: Check browser DevTools Network tab

2. **JavaScript errors**
   - Fix: Check browser Console tab for errors
   - Verify: app.js should load without errors

3. **CORS issues (when accessing via IP)**
   - Fix: CORS is already enabled in app.py
   - Verify: Check console for CORS errors

4. **Port already in use**
   - Fix: Kill existing Flask process
   ```bash
   lsof -ti:5000 | xargs kill -9
   python app.py
   ```

5. **File permissions**
   - Fix: Ensure static files are readable
   ```bash
   ls -la static/
   # All files should be readable (r-- in permissions)
   ```

### Test Script

Run the included test script:
```bash
# Install requests if needed
pip install requests

# Run test
python test_static_serving.py
```

This will:
- Start Flask
- Test root route
- Test CSS loading
- Test JS loading
- Report any issues

### Updated app.py Configuration

The app.py has been updated with explicit static file routing:

```python
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Explicitly serve static files."""
    return send_from_directory('static', filename)
```

This ensures static files are served even if Flask's automatic static routing fails.

### If UI is Still Blank

1. **Hard refresh browser:**
   - Chrome/Firefox: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - Safari: Cmd+Option+R

2. **Clear browser cache**

3. **Check browser console for specific errors**

4. **Try different browser** (Chrome, Firefox, Safari)

5. **Verify all files exist:**
   ```bash
   ls -la static/
   # Should show: index.html, app.js, style.css
   ```

### Access Methods

After starting `python app.py`, you can access via:

1. **localhost** (if working):
   - http://localhost:5000

2. **127.0.0.1**:
   - http://127.0.0.1:5000

3. **Your IP address** (if app running with host='0.0.0.0'):
   - http://192.168.x.x:5000 (replace with your actual IP)

### Next Steps

1. Try accessing via http://127.0.0.1:5000 instead of localhost
2. Check browser DevTools for specific errors
3. Run `python test_static_serving.py` to diagnose
4. If still blank, share the browser console errors
