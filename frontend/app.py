"""
Web Application for Hierarchical RAG System
Beautiful UI for querying well data and uploading new wells
"""

from flask import Flask, request, render_template, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import json
from pathlib import Path
import shutil

# Fix for Windows console Unicode encoding
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add backend folder to Python path
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_path)

import config
from document_processor import process_multiple_wells, WellData
from rag_system import HierarchicalVectorDB, EmbeddingModel
from gemini_handler import answer_query
from nodal_integration import process_nodal_query

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['UPLOAD_FOLDER'] = 'uploaded_wells'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variables
vector_db = None
embedding_model = None
database_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wells_complete_db.pkl")

def initialize_system():
    """Initialize the RAG system on startup"""
    global vector_db, embedding_model
    
    print("\n" + "=" * 70)
    print("🚀 Initializing RAG System")
    print("=" * 70)
    
    try:
        # Initialize embedding model
        embedding_model = EmbeddingModel()
        
        # Load database if exists
        if os.path.exists(database_path):
            vector_db = HierarchicalVectorDB.load(database_path, embedding_model)
            print(f"✅ Loaded existing database: {len(vector_db.all_chunks)} chunks")
        else:
            # Create new empty database
            vector_db = HierarchicalVectorDB(embedding_model)
            print("✅ Created new empty database")
        
        print("=" * 70 + "\n")
        return True
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

@app.route('/')
def index():
    """Render main page"""
    return render_template('rag_ui.html')

@app.route('/api/status')
def get_status():
    """Get system status"""
    if vector_db is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    stats = vector_db.get_statistics()
    return jsonify({
        'success': True,
        'database_loaded': True,
        'total_wells': stats['num_wells'],
        'total_chunks': stats['num_chunks'],
        'wells': stats['wells'],
        'gemini_available': bool(config.GEMINI_API_KEY)
    })

@app.route('/api/query', methods=['POST'])
def query_database():
    """Handle user query"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if vector_db is None or len(vector_db.all_chunks) == 0:
            return jsonify({'error': 'Database is empty. Please upload wells first.'}), 400
        
        # Search for documents
        top_docs = vector_db.search(query, top_k=config.TOP_K)
        
        if not top_docs:
            return jsonify({
                'success': True,
                'query': query,
                'answer': 'No relevant documents found for your query.',
                'documents': [],
                'has_answer': False
            })
        
        # Check for nodal analysis
        nodal_results = None
        if config.GEMINI_API_KEY:
            nodal_results = process_nodal_query(query, top_docs, config.GEMINI_API_KEY)
        
        # Generate answer with Gemini
        answer_data = None
        if config.GEMINI_API_KEY:
            answer_data = answer_query(query, top_docs, config.GEMINI_API_KEY, nodal_results)
        
        # Prepare response
        response = {
            'success': True,
            'query': query,
            'documents': [
                {
                    'rank': doc['rank'],
                    'well': doc['well_name'],
                    'filename': doc['filename'],
                    'similarity': doc['similarity'],
                    'preview': doc['preview']
                }
                for doc in top_docs
            ],
            'has_answer': answer_data is not None and answer_data.get('success', False),
            'answer': answer_data.get('answer', '') if answer_data else '',
            'nodal_analysis': nodal_results is not None
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-well', methods=['POST'])
def upload_well():
    """Handle well folder upload"""
    try:
        well_name = request.form.get('well_name', '').strip()
        
        if not well_name:
            return jsonify({'error': 'Well name is required'}), 400
        
        # Create well folder
        well_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(well_name))
        os.makedirs(well_folder, exist_ok=True)
        
        # Save uploaded files
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        saved_files = []
        for file in files:
            if file.filename:
                # Preserve folder structure
                filename = secure_filename(file.filename)
                filepath = os.path.join(well_folder, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                saved_files.append(filename)
        
        # Process the well
        print(f"\n📁 Processing uploaded well: {well_name}")
        wells = process_multiple_wells([well_folder])
        
        if not wells:
            return jsonify({'error': 'Failed to process well data'}), 500
        
        # Add to vector database
        global vector_db
        vector_db.add_wells(wells)
        
        # Save database
        vector_db.save(database_path)
        
        # Get updated stats
        stats = vector_db.get_statistics()
        
        return jsonify({
            'success': True,
            'well_name': well_name,
            'files_uploaded': len(saved_files),
            'chunks_created': len(wells[0].documents),
            'total_chunks': stats['num_chunks'],
            'total_wells': stats['num_wells']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rebuild-database', methods=['POST'])
def rebuild_database():
    """Rebuild database from existing wells"""
    try:
        # Find all well folders
        well_paths = []
        
        # Check default well folders
        if os.path.exists('Well 1'):
            well_paths.append('Well 1')
        if os.path.exists('Well 2'):
            well_paths.append('Well 2')
        
        # Check uploaded wells
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for item in os.listdir(app.config['UPLOAD_FOLDER']):
                item_path = os.path.join(app.config['UPLOAD_FOLDER'], item)
                if os.path.isdir(item_path):
                    well_paths.append(item_path)
        
        if not well_paths:
            return jsonify({'error': 'No wells found to index'}), 400
        
        # Process all wells
        wells = process_multiple_wells(well_paths)
        
        # Create new database
        global vector_db, embedding_model
        vector_db = HierarchicalVectorDB(embedding_model)
        vector_db.add_wells(wells)
        vector_db.save(database_path)
        
        stats = vector_db.get_statistics()
        
        return jsonify({
            'success': True,
            'wells_indexed': len(wells),
            'total_chunks': stats['num_chunks']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🌐 HIERARCHICAL RAG SYSTEM - WEB INTERFACE")
    print("=" * 70)
    
    # Initialize system
    if initialize_system():
        print("\n✅ System ready!")
        print(f"🌐 Open your browser: http://localhost:5000")
        print(f"📊 Database: {len(vector_db.all_chunks) if vector_db else 0} chunks loaded")
        print(f"🤖 Gemini: {'Enabled' if config.GEMINI_API_KEY else 'Disabled (set API key)'}")
        print("\n" + "=" * 70 + "\n")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("\n❌ Failed to initialize system")
