#!/usr/bin/env python3
"""Minimal test server to check if Flask runs"""
import sys
import os

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("🔧 TEST SERVER STARTUP")
print("=" * 70)
print(f"CWD: {os.getcwd()}")
print(f"Python: {sys.version}")

try:
    print("\n1️⃣  Importing Flask...")
    from flask import Flask
    print("   ✅ Flask imported")
    
    print("\n2️⃣  Creating Flask app...")
    app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
    print("   ✅ Flask app created")
    
    print("\n3️⃣  Defining routes...")
    
    @app.route('/')
    def index():
        return '<h1>✅ UI is Working!</h1><p>Flask server is running on port 5000</p>'
    
    @app.route('/api/status')
    def status():
        return {'status': 'ok', 'message': 'Server is running'}
    
    print("   ✅ Routes defined")
    
    print("\n4️⃣  Starting server on 0.0.0.0:5000...")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
