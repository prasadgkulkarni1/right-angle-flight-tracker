#!/usr/bin/env python3
"""
Test script to verify Flask static file serving.
"""

import requests
import subprocess
import time
import sys

def test_static_serving():
    print("Starting Flask app...")

    # Start Flask in background
    proc = subprocess.Popen(
        ['python', 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for Flask to start
    time.sleep(3)

    try:
        base_url = "http://localhost:5000"

        # Test 1: Root route
        print("\n1. Testing root route (/)...")
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                if len(response.text) > 0:
                    print(f"   Content length: {len(response.text)} bytes")
                    if "Flight Tracker" in response.text:
                        print("   ✅ HTML content looks good")
                    else:
                        print("   ❌ HTML missing expected content")
                else:
                    print("   ❌ Empty response!")
            else:
                print(f"   ❌ Bad status code")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 2: CSS file
        print("\n2. Testing CSS (/static/style.css)...")
        try:
            response = requests.get(f"{base_url}/static/style.css", timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Content length: {len(response.text)} bytes")
                print("   ✅ CSS file served")
            else:
                print(f"   ❌ CSS not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 3: JS file
        print("\n3. Testing JS (/static/app.js)...")
        try:
            response = requests.get(f"{base_url}/static/app.js", timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Content length: {len(response.text)} bytes")
                print("   ✅ JS file served")
            else:
                print(f"   ❌ JS not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    finally:
        print("\nStopping Flask app...")
        proc.terminate()
        proc.wait(timeout=5)
        print("Done!")

if __name__ == "__main__":
    test_static_serving()
