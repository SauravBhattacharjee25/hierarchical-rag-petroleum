#!/usr/bin/env python3
"""
Deployment Methods for Hierarchical RAG System
Provides multiple production deployment options
"""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

METHODS = {
    '1': {
        'name': 'Waitress (Pure Python)',
        'cmd': 'waitress-serve --port=8000 --host=0.0.0.0 --threads=4 wsgi:app',
        'desc': 'Simple, pure Python WSGI server (no C dependencies)'
    },
    '2': {
        'name': 'Uvicorn (ASGI)',
        'cmd': 'uvicorn wsgi:app --host 0.0.0.0 --port 8000 --workers 2',
        'desc': 'Fast ASGI server for async Python applications'
    },
    '3': {
        'name': 'Hypercorn (ASGI)',
        'cmd': 'hypercorn wsgi:app --bind 0.0.0.0:8000 --workers 2',
        'desc': 'Pure Python ASGI server'
    },
    '4': {
        'name': 'Gunicorn (WSGI)',
        'cmd': 'gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 --worker-class gthread wsgi:app',
        'desc': 'Battle-tested WSGI server with worker process management'
    },
    '5': {
        'name': 'Flask Development (Debug)',
        'cmd': 'python3 -c "from wsgi import app; app.run(host=\'0.0.0.0\', port=8000, debug=True)"',
        'desc': 'Development server with auto-reload (NOT for production)'
    }
}

def print_menu():
    print("\n" + "=" * 70)
    print("🚀 HIERARCHICAL RAG SYSTEM - DEPLOYMENT OPTIONS")
    print("=" * 70)
    print("\nSelect a deployment method:\n")
    
    for key, method in METHODS.items():
        print(f"{key}. {method['name']}")
        print(f"   {method['desc']}")
        print()

def deploy(method_key):
    if method_key not in METHODS:
        print("❌ Invalid choice")
        return
    
    method = METHODS[method_key]
    
    print("\n" + "=" * 70)
    print(f"🚀 STARTING: {method['name']}")
    print("=" * 70)
    print(f"Command: {method['cmd']}")
    print("=" * 70 + "\n")
    
    try:
        subprocess.run(method['cmd'], shell=True, cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # If method passed as argument
        deploy(sys.argv[1])
    else:
        # Interactive menu
        print_menu()
        choice = input("Enter your choice (1-5): ").strip()
        deploy(choice)
