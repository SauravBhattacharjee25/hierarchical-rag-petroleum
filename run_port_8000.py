#!/usr/bin/env python3
"""
RAG System Web Server - Port 8000
"""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Import backend modules
from backend import config
from backend.rag_system import HierarchicalVectorDB, EmbeddingModel
from backend.document_processor import process_multiple_wells
from backend.gemini_handler import answer_query
from backend.nodal_integration import process_nodal_query
from backend.borehole_handler import BoreholeHandler

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

vector_db = None
embedding_model = None
database_path = 'wells_complete_db.pkl'

def initialize_system():
    """Initialize the RAG system"""
    global vector_db, embedding_model
    
    print("\n" + "=" * 70)
    print("🚀 INITIALIZING HIERARCHICAL RAG SYSTEM")
    print("=" * 70)
    
    try:
        embedding_model = EmbeddingModel()
        
        if os.path.exists(database_path):
            print(f"\n📂 Loading existing database: {database_path}")
            vector_db = HierarchicalVectorDB.load(database_path, embedding_model)
            print(f"✅ Loaded {len(vector_db.all_chunks)} chunks from {len(vector_db.wells)} wells")
        else:
            print("\n📂 No existing database found. Creating new database...")
            vector_db = HierarchicalVectorDB(embedding_model)
            print("✅ New database created")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/')
def index():
    """Serve the UI"""
    return render_template('rag_ui.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    try:
        image_stats = vector_db.get_image_statistics() if vector_db else {'image_chunks': 0, 'text_chunks': 0}
        
        return jsonify({
            'success': True,
            'total_wells': len(vector_db.wells) if vector_db else 0,
            'total_chunks': len(vector_db.all_chunks) if vector_db else 0,
            'gemini_available': bool(config.GEMINI_API_KEY),
            'image_stats': image_stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/query', methods=['POST'])
def query_database():
    """Handle user query with borehole priority filtering"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        query_mode = data.get('query_mode', 'all')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if vector_db is None or len(vector_db.all_chunks) == 0:
            return jsonify({'error': 'Database is empty. Please upload wells first.'}), 400
        
        # Search for documents
        if query_mode == 'images_only':
            top_docs = vector_db.search_images_only(query, top_k=config.TOP_K)
        elif query_mode == 'text_only':
            top_docs = vector_db.search_text_only(query, top_k=config.TOP_K)
        else:
            top_docs = vector_db.search(query, top_k=config.TOP_K)
        
        if not top_docs:
            return jsonify({
                'success': True,
                'query': query,
                'answer': 'No relevant documents found for your query.',
                'documents': [],
                'has_answer': False
            })
        
        # Apply borehole priority filtering
        annotated_docs = BoreholeHandler.annotate_documents_with_borehole_info(top_docs)
        filtered_docs = BoreholeHandler.filter_by_borehole_priority(annotated_docs)
        
        print(f"\n🔍 Borehole Analysis:")
        print(BoreholeHandler.get_borehole_summary(annotated_docs))
        print(f"\n✅ Using highest priority: {filtered_docs[0]['borehole_type'] if filtered_docs else 'None'}")
        print(f"   Filtered from {len(annotated_docs)} to {len(filtered_docs)} documents\n")
        
        top_docs = filtered_docs
        
        # Generate answer
        nodal_results = None
        if config.GEMINI_API_KEY:
            nodal_results = process_nodal_query(query, top_docs, config.GEMINI_API_KEY)
        
        answer_data = None
        if config.GEMINI_API_KEY:
            answer_data = answer_query(query, top_docs, config.GEMINI_API_KEY, nodal_results)
        
        # Prepare response
        response = {
            'success': True,
            'query': query,
            'query_mode': query_mode,
            'borehole_used': top_docs[0]['borehole_type'] if top_docs else 'Unknown',
            'borehole_priority': top_docs[0]['borehole_priority'] if top_docs else 0,
            'documents': [
                {
                    'rank': doc['rank'],
                    'well': doc['well_name'],
                    'filename': doc['filename'],
                    'similarity': doc['similarity'],
                    'preview': doc['preview'],
                    'is_from_image': doc.get('is_from_image', False),
                    'image_metadata': doc.get('image_metadata', {}),
                    'borehole_type': doc.get('borehole_type', 'Unknown'),
                    'borehole_priority': doc.get('borehole_priority', 0)
                }
                for doc in top_docs
            ],
            'has_answer': answer_data is not None and answer_data.get('success', False),
            'answer': answer_data.get('answer', '') if answer_data else '',
            'nodal_analysis': nodal_results is not None
        }
        
        return jsonify(response)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-well', methods=['POST'])
def upload_well():
    """Handle well folder upload"""
    global vector_db
    
    try:
        well_name = request.form.get('well_name', '').strip()
        files = request.files.getlist('files')
        
        if not well_name:
            return jsonify({'error': 'Well name is required'}), 400
        
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        # Create well folder
        well_folder = os.path.join(app.config['UPLOAD_FOLDER'], well_name)
        os.makedirs(well_folder, exist_ok=True)
        
        # Save files
        saved_files = []
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(well_folder, filename)
                file.save(filepath)
                saved_files.append(filename)
        
        print(f"\n📤 Processing uploaded well: {well_name}")
        print(f"   Files: {len(saved_files)}")
        
        # Process the well
        wells_data = process_multiple_wells([well_folder])
        
        if wells_data:
            vector_db.add_wells(wells_data)
            vector_db.save(database_path)
            
            total_chunks = sum(len(well.documents) for well in wells_data)
            
            return jsonify({
                'success': True,
                'well_name': well_name,
                'files_uploaded': len(saved_files),
                'chunks_created': total_chunks,
                'message': f'Successfully indexed {well_name}'
            })
        else:
            return jsonify({'error': 'Failed to process well data'}), 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🌐 HIERARCHICAL RAG SYSTEM - WEB INTERFACE (PORT 8000)")
    print("=" * 70)
    
    if initialize_system():
        print("\n✅ System ready!")
        print(f"🌐 Open your browser: http://localhost:8000")
        print(f"📊 Database: {len(vector_db.all_chunks) if vector_db else 0} chunks loaded")
        print(f"🤖 Gemini: {'Enabled' if config.GEMINI_API_KEY else 'Disabled'}")
        print("\n" + "=" * 70 + "\n")
        
        app.run(debug=False, host='0.0.0.0', port=8000, use_reloader=False)
    else:
        print("\n❌ Failed to initialize system")
