"""
Simple launcher for the RAG Web Application
"""
import sys
import os

# Get the root directory
root_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(root_dir)

from flask import Flask, request, render_template, jsonify
import io
import sys

# Fix for Windows console Unicode encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Import backend modules
from backend import config
from backend.document_processor import process_multiple_wells
from backend.rag_system import HierarchicalVectorDB, EmbeddingModel
from backend.gemini_handler import answer_query
from backend.nodal_integration import process_nodal_query
from backend.borehole_handler import BoreholeHandler
from werkzeug.utils import secure_filename

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(root_dir, 'frontend', 'templates'),
            static_folder=os.path.join(root_dir, 'frontend', 'static'))

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['UPLOAD_FOLDER'] = os.path.join(root_dir, 'uploaded_wells')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variables
vector_db = None
embedding_model = None
database_path = os.path.join(root_dir, "wells_complete_db.pkl")

def initialize_system():
    """Initialize the RAG system on startup"""
    global vector_db, embedding_model
    
    print("\\n" + "=" * 70)
    print("🚀 Initializing RAG System")
    print("=" * 70)
    
    try:
        # Initialize embedding model
        embedding_model = EmbeddingModel()
        
        # ALWAYS start with empty database for judges
        # This ensures 0 wells on fresh startup
        # Wells will only be added when judges explicitly upload them
        
        # If old database exists, rename it as backup (for reference only)
        if os.path.exists(database_path):
            backup_path = database_path.replace('.pkl', '_backup.pkl')
            if not os.path.exists(backup_path):
                import shutil
                shutil.move(database_path, backup_path)
                print(f"📦 Old database backed up to: {backup_path}")
        
        # Create new empty database
        vector_db = HierarchicalVectorDB(embedding_model)
        print("✅ Started with clean empty database (0 wells)")
        print("   Judges must upload wells via UI to add data")
        
        print("=" * 70 + "\\n")
        return True
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
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
    
    # Get image stats if available
    image_stats = vector_db.get_image_statistics() if hasattr(vector_db, 'get_image_statistics') else {'image_chunks': 0, 'total_images': 0}
    
    return jsonify({
        'success': True,
        'database_loaded': True,
        'total_wells': stats['num_wells'],
        'total_chunks': stats['num_chunks'],
        'wells': stats['wells'],
        'gemini_available': bool(config.GEMINI_API_KEY),
        'image_stats': image_stats
    })

@app.route('/api/query', methods=['POST'])
def query_database():
    """Handle user query"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        query_mode = data.get('query_mode', 'all')  # 'all', 'text_only', 'images_only'
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if vector_db is None or len(vector_db.all_chunks) == 0:
            return jsonify({'error': 'Database is empty. Please upload wells first.'}), 400
        
        # Search for documents based on mode
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
        
        # *** APPLY BOREHOLE PRIORITY FILTERING ***
        # Import and use BoreholeHandler to filter by priority (S2 > S1 > Main Hole)
        # from backend.borehole_handler import BoreholeHandler (Already imported)
        
        # Annotate documents with borehole info
        annotated_docs = BoreholeHandler.annotate_documents_with_borehole_info(top_docs)
        
        # Filter to highest priority borehole only
        filtered_docs = BoreholeHandler.filter_by_borehole_priority(annotated_docs)
        
        # Get borehole summary for logging
        borehole_summary = BoreholeHandler.get_borehole_summary(annotated_docs)
        print(f"\n🔍 Borehole Analysis:")
        print(borehole_summary)
        print(f"\n✅ Using highest priority: {filtered_docs[0]['borehole_type'] if filtered_docs else 'None'}")
        print(f"   Filtered from {len(annotated_docs)} to {len(filtered_docs)} documents\n")
        
        # Use filtered documents for answer generation
        top_docs = filtered_docs
        
        # Check for nodal analysis (only for all or text modes usually, but let's keep it general)
        nodal_results = None
        if config.GEMINI_API_KEY:
            nodal_results = process_nodal_query(query, top_docs, config.GEMINI_API_KEY)
        
        # Generate answer with Gemini
        answer_data = None
        if config.GEMINI_API_KEY:
            # Add context about source type to the prompt if needed
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
            # Add to database
            vector_db.add_wells(wells_data)
            
            # Save database
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
    print("\\n" + "=" * 70)
    print("🌐 HIERARCHICAL RAG SYSTEM - WEB INTERFACE")
    print("=" * 70)
    
    # Initialize system
    if initialize_system():
        print("\\n✅ System ready!")
        print(f"🌐 Open your browser: http://localhost:5000")
        print(f"📊 Database: {len(vector_db.all_chunks) if vector_db else 0} chunks loaded")
        print(f"🤖 Gemini: {'Enabled' if config.GEMINI_API_KEY else 'Disabled (set API key)'}")
        print("\\n" +"=" * 70 + "\\n")
        
        app.run(debug=False, host='0.0.0.0', port=5000)
    else:
        print("\\n❌ Failed to initialize system")
