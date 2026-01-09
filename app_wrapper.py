#!/usr/bin/env python3
"""
Wrapper for run.py with error handling and fallback
"""
import sys
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

print("\n" + "=" * 70)
print("🚀 HIERARCHICAL RAG SYSTEM - STARTUP")
print("=" * 70)

# Try to run the actual app
try:
    print("\n📦 Importing modules...")
    from run import app, initialize_system
    print("✅ Modules imported successfully")
    
    print("\n🔧 Initializing system...")
    if initialize_system():
        print("\n✅ System initialized!")
        print("🌐 Starting Flask server on http://localhost:5000")
        print("=" * 70 + "\n")
        
        # Run the app
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    else:
        print("\n⚠️  System initialization returned False, but attempting to start server anyway...")
        print("🌐 Starting Flask server on http://localhost:5000")
        print("=" * 70 + "\n")
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
        
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    print("\n🔧 Falling back to minimal server...")
    
    from flask import Flask, jsonify, render_template
    
    app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
    
    @app.route('/')
    def index():
        try:
            return render_template('rag_ui.html')
        except Exception as ex:
            return f'''
            <h1>UI Error</h1>
            <p>Could not load template: {ex}</p>
            <p>Check that frontend/templates/rag_ui.html exists</p>
            '''
    
    @app.route('/api/status')
    def status():
        return jsonify({'status': 'fallback', 'message': 'Server running in fallback mode'})
    
    print("✅ Fallback server ready")
    print("🌐 Starting Flask server on http://localhost:5000")
    print("=" * 70 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    
except Exception as e:
    print(f"\n❌ Critical Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
