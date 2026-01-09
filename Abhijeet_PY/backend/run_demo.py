"""
DEMO SCRIPT - For Hackathon Judges
Run this to see all features in action
"""

import subprocess
import sys
import time

print("=" * 70)
print("🎯 HIERARCHICAL RAG SYSTEM - LIVE DEMO")
print("=" * 70)
print()

# Check if database exists
import os
if not os.path.exists("wells_complete_db.pkl"):
    print("⚠️  Database not found. Running indexing first...")
    print("This will take ~4-6 minutes...")
    print()
    subprocess.run([sys.executable, "main.py", 
                   "--index", "Well 1", "Well 2", 
                   "--output", "wells_complete_db.pkl"])
    print()

print("=" * 70)
print("DEMO 1: Simple Parameter Retrieval")
print("=" * 70)
print("Query: 'What is the total vertical depth of Well 1?'")
print()
time.sleep(2)

subprocess.run([sys.executable, "main.py",
               "--database", "wells_complete_db.pkl",
               "--query", "What is the total vertical depth of Well 1?"])

print("\n" + "=" * 70)
print("DEMO 2: Cross-Well Comparison")
print("=" * 70)
print("Query: 'Compare the reservoir pressures between Well 1 and Well 2'")
print()
time.sleep(2)

subprocess.run([sys.executable, "main.py",
               "--database", "wells_complete_db.pkl",
               "--query", "Compare the reservoir pressures between Well 1 and Well 2"])

print("\n" + "=" * 70)
print("DEMO 3: Document Summarization")
print("=" * 70)
print("Query: 'Summarize the key findings from Well 1 completion report'")
print()
time.sleep(2)

subprocess.run([sys.executable, "main.py",
               "--database", "wells_complete_db.pkl",
               "--query", "Summarize the key findings from Well 1 completion report"])

print("\n" + "=" * 70)
print("DEMO 4: Automatic Calculations (NodalAnalysis)")
print("=" * 70)
print("Query: 'Calculate the production capacity for Well 1'")
print()
time.sleep(2)

subprocess.run([sys.executable, "main.py",
               "--database", "wells_complete_db.pkl",
               "--query", "Calculate the production capacity for Well 1"])

print("\n" + "=" * 70)
print("✅ DEMO COMPLETE!")
print("=" * 70)
print()
print("🎯 All Features Demonstrated:")
print("  ✓ Multi-well hierarchical search")
print("  ✓ Semantic similarity matching")
print("  ✓ Cross-well queries")
print("  ✓ Document summarization")
print("  ✓ Automatic parameter extraction")
print("  ✓ NodalAnalysis integration")
print()
print("📊 Try interactive mode:")
print("  python main.py --database wells_complete_db.pkl --interactive")
print()
print("=" * 70)
