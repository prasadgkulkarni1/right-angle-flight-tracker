#!/usr/bin/env python3
"""
Quick diagnostic script for UI issues.
Run this while Flask app is running in another terminal.
"""

import os
import sys

def check_static_files():
    """Check if static files exist and are readable."""
    print("="*60)
    print("1. Checking Static Files")
    print("="*60)

    static_files = ['index.html', 'app.js', 'style.css']
    static_dir = 'static'

    if not os.path.exists(static_dir):
        print(f"❌ ERROR: {static_dir}/ directory not found!")
        return False

    print(f"✓ {static_dir}/ directory exists")

    all_ok = True
    for filename in static_files:
        filepath = os.path.join(static_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            readable = os.access(filepath, os.R_OK)
            status = "✓" if readable else "❌"
            print(f"{status} {filename}: {size} bytes, readable: {readable}")
            if not readable:
                all_ok = False
        else:
            print(f"❌ {filename}: NOT FOUND")
            all_ok = False

    return all_ok

def check_app_config():
    """Check app.py configuration."""
    print("\n" + "="*60)
    print("2. Checking app.py Configuration")
    print("="*60)

    if not os.path.exists('app.py'):
        print("❌ ERROR: app.py not found!")
        return False

    with open('app.py', 'r') as f:
        content = f.read()

    checks = {
        "Flask import": "from flask import Flask",
        "CORS enabled": "CORS(app)",
        "Static folder": "static_folder='static'",
        "Index route": "@app.route('/')",
        "Static route": "@app.route('/static",
        "Host binding": "host='0.0.0.0'"
    }

    all_ok = True
    for check_name, check_str in checks.items():
        if check_str in content:
            print(f"✓ {check_name}: Found")
        else:
            print(f"❌ {check_name}: NOT FOUND")
            all_ok = False

    return all_ok

def check_network():
    """Check network connectivity."""
    print("\n" + "="*60)
    print("3. Checking Network")
    print("="*60)

    import socket

    # Get hostname and IP
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"✓ Hostname: {hostname}")
        print(f"✓ IP Address: {ip_address}")
    except:
        print("❌ Could not resolve hostname")
        return False

    # Check if port 5000 is available or in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5000))
    sock.close()

    if result == 0:
        print("✓ Port 5000 is in use (Flask should be running)")
        return True
    else:
        print("❌ Port 5000 is not in use (Is Flask running?)")
        return False

def test_localhost_resolution():
    """Test if localhost resolves correctly."""
    print("\n" + "="*60)
    print("4. Testing localhost Resolution")
    print("="*60)

    import socket

    try:
        # Test localhost
        localhost_ip = socket.gethostbyname('localhost')
        print(f"✓ localhost resolves to: {localhost_ip}")

        if localhost_ip == '127.0.0.1':
            print("✓ localhost resolution is correct")
            return True
        else:
            print(f"⚠️  localhost resolves to {localhost_ip} (expected 127.0.0.1)")
            return False
    except socket.gaierror:
        print("❌ localhost does not resolve!")
        print("\nFix: Add this to /etc/hosts:")
        print("127.0.0.1       localhost")
        return False

def provide_recommendations():
    """Provide recommendations based on checks."""
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)

    print("\n1. If Flask is not running:")
    print("   python app.py")

    print("\n2. Access the app via:")
    print("   • http://127.0.0.1:5000")
    print("   • http://localhost:5000 (if localhost resolves)")
    print("   • http://YOUR_IP:5000 (check IP above)")

    print("\n3. If UI is blank:")
    print("   • Open browser DevTools (F12 or Cmd+Option+I)")
    print("   • Check Console tab for JavaScript errors")
    print("   • Check Network tab for failed requests (404s)")
    print("   • Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Win)")

    print("\n4. Test static files:")
    print("   curl http://127.0.0.1:5000/static/style.css")
    print("   curl http://127.0.0.1:5000/static/app.js")

    print("\n5. For localhost issues:")
    print("   cat /etc/hosts | grep localhost")
    print("   # Should show: 127.0.0.1       localhost")

def main():
    print("\n" + "="*60)
    print("FLIGHT TRACKER UI DIAGNOSTIC")
    print("="*60)
    print("\nThis script checks common issues with the Flight Tracker UI.")
    print("Make sure Flask is running in another terminal!\n")

    results = []
    results.append(("Static Files", check_static_files()))
    results.append(("App Configuration", check_app_config()))
    results.append(("Network", check_network()))
    results.append(("localhost Resolution", test_localhost_resolution()))

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    all_passed = True
    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False

    provide_recommendations()

    if all_passed:
        print("\n✅ All checks passed!")
        print("\nIf UI is still blank, check browser DevTools Console for errors.")
    else:
        print("\n❌ Some checks failed. See recommendations above.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
